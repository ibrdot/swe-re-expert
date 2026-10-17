"""GPT Image 2 wrappers via the AI Gateway: gen and edit.

Image generation uses fal's async queue API: submit → poll status → fetch result.
Each HTTP call is sub-second, so nothing on the chain (Cloudflare / ALB / uvicorn)
ever holds a long connection waiting for a 60–240s generation. Submitting only
once (then polling) also avoids the duplicate-billing trap of retrying a
long-running sync request.

Calls go through the sandbox-authenticated app-server proxy:
  POST /internal/fal/queue/{model}                    — submit, returns request_id
  GET  /internal/fal/queue/{model}/requests/{id}/status — cheap status check
  GET  /internal/fal/queue/{model}/requests/{id}      — final result (after COMPLETED)
  POST /internal/fal/files/upload                     — image upload for edit refs

app-server forwards each to ai-gateway with the agent's resolved API key, so
billing and observability hit the same gateway path as the agent's chat-side
Generate tool while keeping this PPT skill on GPT Image 2 for slide typography.

Individual HTTP calls go through `_with_retries`, which handles transient
network errors and rate-limiting with exponential backoff. Once a submit has
returned a request_id, retries happen on the cheap status/result calls only —
never re-submitting (which would re-bill).
"""

import os
import random
import sys
import time
import urllib.request
import hashlib
import json
from pathlib import Path

import httpx

_QUEUE_PATH = "/internal/fal/queue"          # base for submit + status + result
_UPLOAD_PATH = "/internal/fal/files/upload"

DEFAULT_GEN_MODEL = "gpt-image-2"
DEFAULT_EDIT_MODEL = "gpt-image-2/edit"
_ALLOWED_GEN_MODELS = frozenset({DEFAULT_GEN_MODEL})
_ALLOWED_EDIT_MODELS = frozenset({DEFAULT_EDIT_MODEL})

MAX_RETRIES = 3                 # 4 attempts total
BASE_DELAY_SEC = 2              # exponential base for normal errors
RATE_LIMIT_DELAY_SEC = 30       # longer base for rate-limit
JITTER_FRAC = 0.3               # ±30% jitter so parallel callers don't sync

# Per-call HTTP timeouts. Each queue op is sub-second under normal conditions;
# these are network slack and must stay well under any link's idle timeout
# (currently ALB is 60s).
SUBMIT_TIMEOUT_SEC = 30.0
STATUS_TIMEOUT_SEC = 30.0
RESULT_TIMEOUT_SEC = 60.0
UPLOAD_TIMEOUT_SEC = 300.0      # uploads are size-bound, can legitimately be slow

# Polling cadence and hard cap for a single image. fal recommends 2–5s between
# status checks; 10 minutes is enough headroom for the slowest 4K renders while
# preventing a zombie loop if something goes wrong upstream.
POLL_INTERVAL_SEC = 2.0
POLL_TIMEOUT_SEC = 600.0
POLL_PROGRESS_LOG_SEC = 30.0


def _gateway_creds() -> tuple[str, str]:
    """Return (base_url, sandbox_token) or exit with a friendly error."""
    base_url = os.environ.get("APP_SERVER_URL", "").rstrip("/")
    token = os.environ.get("SANDBOX_MCP_TOKEN", "")
    if not base_url:
        print(
            "Error: APP_SERVER_URL not set. This skill must run inside a sandbox.",
            file=sys.stderr,
        )
        sys.exit(1)
    if not token:
        print(
            "Error: SANDBOX_MCP_TOKEN not set. This skill must run inside a sandbox.",
            file=sys.stderr,
        )
        sys.exit(1)
    return base_url, token


def _gateway_headers(sandbox_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {sandbox_token}"}


def _parse_size(size_str: str | None) -> dict | str | None:
    """Accept presets like 'landscape_4_3', explicit 'WxH', or None."""
    if not size_str:
        return None
    if "x" in size_str.lower():
        w, h = size_str.lower().split("x")
        return {"width": int(w), "height": int(h)}
    return size_str


def _normalize_model(model: str | None, *, default: str, allowed: frozenset[str]) -> str:
    selected = (model or default).strip()
    if selected.startswith("fal-ai/"):
        selected = selected[len("fal-ai/"):]
    if selected not in allowed:
        supported = ", ".join(sorted(allowed))
        raise RuntimeError(f"Unsupported image model {model!r}. Supported: {supported}")
    return selected


def _atomic_write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f".{path.name}.tmp")
    tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp_path, path)


def _payload_hash(*, model: str, payload: dict) -> str:
    canonical = json.dumps(
        {"model": model, "payload": payload},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _read_queue_state(path: Path, *, model: str, payload: dict) -> str | None:
    if not path.exists():
        return None
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(state, dict):
        return None
    if state.get("model") != model:
        return None
    if state.get("payload_hash") != _payload_hash(model=model, payload=payload):
        return None
    request_id = state.get("request_id")
    if not isinstance(request_id, str) or not request_id:
        return None
    return request_id


def _write_queue_state(path: Path, *, model: str, payload: dict, request_id: str) -> None:
    prompt = payload.get("prompt")
    _atomic_write_json(
        path,
        {
            "model": model,
            "request_id": request_id,
            "payload_hash": _payload_hash(model=model, payload=payload),
            "created_at": int(time.time()),
            "prompt_preview": prompt[:200] if isinstance(prompt, str) else None,
        },
    )


def _clear_queue_state(path: Path | None) -> None:
    if path is None:
        return
    try:
        path.unlink()
    except FileNotFoundError:
        pass


def _download(url: str, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(url, out_path)


def _first_image_url(result: dict) -> str:
    images = result.get("images") or []
    if not images:
        raise RuntimeError(f"No images in result: top-level keys={list(result.keys())}")
    first = images[0]
    if not isinstance(first, dict) or "url" not in first:
        raise RuntimeError(f"First image entry missing url field: {first}")
    return first["url"]


def _classify_failure(exc: Exception) -> tuple[bool, bool]:
    """Return (should_retry, is_rate_limit) for an in-flight call failure.

    4xx other than 429 are permanent — don't burn ~14s of backoff on bad
    auth, bad params, insufficient credits, or model-not-allowed.
    """
    if isinstance(exc, httpx.HTTPStatusError):
        code = exc.response.status_code
        if code == 429:
            return True, True
        if 400 <= code < 500:
            return False, False
        return True, False  # 5xx
    # Network / timeout / DNS / decode errors: retry
    return True, False


def _retry_delay(attempt: int, *, rate_limited: bool) -> float:
    """Exponential backoff with jitter. attempt is 0-indexed."""
    base = RATE_LIMIT_DELAY_SEC if rate_limited else BASE_DELAY_SEC
    delay = base * (2 ** attempt)
    jitter = delay * JITTER_FRAC * (2 * random.random() - 1)
    return max(1.0, delay + jitter)


def _with_retries(label: str, fn, *, max_retries: int = MAX_RETRIES):
    """Run `fn()` with retries. Catches Exception (NOT BaseException — Ctrl-C must propagate)."""
    last_exc: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            return fn()
        except Exception as exc:
            last_exc = exc
            should_retry, rate_limited = _classify_failure(exc)
            if not should_retry or attempt >= max_retries:
                break
            delay = _retry_delay(attempt, rate_limited=rate_limited)
            tag = "rate-limited" if rate_limited else "transient error"
            print(
                f"  [{label}] {tag}: {type(exc).__name__}: {exc} — "
                f"retry {attempt + 1}/{max_retries} in {delay:.1f}s",
                file=sys.stderr,
                flush=True,
            )
            time.sleep(delay)
    raise RuntimeError(
        f"{label} failed after {attempt + 1} attempts. Last error: {last_exc}"
    ) from last_exc


def _post_json(url: str, *, headers: dict, payload: dict, timeout: float) -> dict:
    resp = httpx.post(url, headers=headers, json=payload, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def _get_json(url: str, *, headers: dict, timeout: float) -> dict:
    resp = httpx.get(url, headers=headers, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def _submit_and_wait(
    *,
    model: str,
    payload: dict,
    queue_state_path: Path | None = None,
) -> dict:
    """Submit a fal queue job, poll until COMPLETED, fetch and return the final result.

    Retries are applied per-HTTP-call by `_with_retries`. Once submit returns a
    request_id, we never re-submit — only poll. This eliminates the duplicate-
    billing trap of the old sync path where each user-visible retry re-billed a
    full image generation.
    """
    base_url, token = _gateway_creds()
    headers_json = _gateway_headers(token)
    headers_json["Content-Type"] = "application/json"
    headers_get = _gateway_headers(token)

    request_id = (
        None
        if queue_state_path is None
        else _read_queue_state(queue_state_path, model=model, payload=payload)
    )
    if request_id:
        print(f"[queue] resumed model={model} request_id={request_id}", flush=True)
    else:
        # 1. Submit. Transient errors retry. 4xx don't retry (per _classify_failure)
        #    — but more importantly, a 200 here means fal accepted the job (and
        #    billing is committed): from this point on, no re-submission.
        submit_url = f"{base_url}{_QUEUE_PATH}/{model}"
        submit = _with_retries(
            "queue_submit",
            lambda: _post_json(
                submit_url, headers=headers_json, payload=payload, timeout=SUBMIT_TIMEOUT_SEC
            ),
        )
        if not isinstance(submit, dict):
            raise RuntimeError(f"Submit response was not a JSON object: {type(submit).__name__}")
        request_id = submit.get("request_id")
        if not isinstance(request_id, str) or not request_id:
            raise RuntimeError(f"Submit response missing request_id: {submit}")
        if queue_state_path is not None:
            _write_queue_state(
                queue_state_path,
                model=model,
                payload=payload,
                request_id=request_id,
            )
        print(f"[queue] submitted model={model} request_id={request_id}", flush=True)

    # 2. Poll status. Each call is sub-second; only the wait between calls is
    #    long. Status is the single source of truth for completion — don't infer
    #    from the result endpoint.
    status_url = f"{base_url}{_QUEUE_PATH}/{model}/requests/{request_id}/status"
    started_at = time.monotonic()
    deadline = time.monotonic() + POLL_TIMEOUT_SEC
    next_progress_log_at = started_at
    last_status = None
    while True:
        s = _with_retries(
            "queue_status",
            lambda: _get_json(status_url, headers=headers_get, timeout=STATUS_TIMEOUT_SEC),
        )
        st = s.get("status")
        now = time.monotonic()
        elapsed = int(now - started_at)
        if st == "COMPLETED":
            print(
                f"[queue] completed model={model} elapsed={elapsed}s request_id={request_id}",
                flush=True,
            )
            break
        if st in ("FAILED", "ERROR", "CANCELLED"):
            _clear_queue_state(queue_state_path)
            raise RuntimeError(f"queue failed: {s}")
        if st != last_status or now >= next_progress_log_at:
            print(
                f"[queue] status={st or 'UNKNOWN'} model={model} "
                f"elapsed={elapsed}s request_id={request_id}",
                flush=True,
            )
            last_status = st
            next_progress_log_at = now + POLL_PROGRESS_LOG_SEC
        # IN_QUEUE / IN_PROGRESS / anything else — keep polling
        if now >= deadline:
            raise RuntimeError(
                f"queue polling timed out after {POLL_TIMEOUT_SEC}s "
                f"last_status={st!r} request_id={request_id}"
            )
        time.sleep(POLL_INTERVAL_SEC)

    # 3. Fetch result. Should be quick now that status is COMPLETED.
    result_url = f"{base_url}{_QUEUE_PATH}/{model}/requests/{request_id}"
    result = _with_retries(
        "queue_result",
        lambda: _get_json(result_url, headers=headers_get, timeout=RESULT_TIMEOUT_SEC),
    )
    _clear_queue_state(queue_state_path)
    return result


def gen_image(
    *,
    prompt: str,
    out_path: Path,
    size: str | None = None,
    quality: str = "high",
    model: str = DEFAULT_GEN_MODEL,
    queue_state_path: Path | None = None,
) -> str:
    """Text-to-image via the AI Gateway. Returns the remote URL it was downloaded from."""
    selected_model = _normalize_model(
        model, default=DEFAULT_GEN_MODEL, allowed=_ALLOWED_GEN_MODELS
    )
    payload: dict = {
        "model": f"fal-ai/{selected_model}",
        "prompt": prompt,
        "quality": quality,
        "output_format": "png",
        "num_images": 1,
    }
    parsed = _parse_size(size)
    if parsed is not None:
        payload["image_size"] = parsed

    print(
        f"[gen] model={selected_model} size={size or 'default'} quality={quality}",
        flush=True,
    )
    result = _submit_and_wait(
        model=selected_model,
        payload=payload,
        queue_state_path=queue_state_path,
    )
    url = _first_image_url(result)
    _download(url, out_path)
    print(f"[gen] saved -> {out_path}", flush=True)
    return url


def _upload_file(local_path: Path, *, base_url: str, token: str) -> str:
    """Upload a local file via the gateway and return the resulting fal CDN URL."""
    print(f"[edit] uploading {local_path.name}...", flush=True)

    def _call():
        with local_path.open("rb") as fp:
            resp = httpx.post(
                f"{base_url}{_UPLOAD_PATH}",
                headers=_gateway_headers(token),
                files={"file": (local_path.name, fp, "application/octet-stream")},
                timeout=UPLOAD_TIMEOUT_SEC,
            )
        resp.raise_for_status()
        return resp.json()

    payload = _with_retries("upload", _call)
    if not isinstance(payload, dict):
        raise RuntimeError(f"Upload response was not a JSON object: {type(payload).__name__}")
    file_url = payload.get("file_url") or payload.get("url")
    if not isinstance(file_url, str) or not file_url:
        raise RuntimeError(f"Upload response missing file_url/url: {payload}")
    return file_url


def edit_image(
    *,
    prompt: str,
    refs: list[str],
    out_path: Path,
    size: str | None = None,
    quality: str = "high",
    mask: str | None = None,
    model: str = DEFAULT_EDIT_MODEL,
    queue_state_path: Path | None = None,
) -> str:
    """Image-to-image edit via the AI Gateway. `refs` are local paths or URLs."""
    base_url, token = _gateway_creds()
    selected_model = _normalize_model(
        model, default=DEFAULT_EDIT_MODEL, allowed=_ALLOWED_EDIT_MODELS
    )

    image_urls: list[str] = []
    for ref in refs:
        if ref.startswith(("http://", "https://")):
            image_urls.append(ref)
        else:
            p = Path(ref)
            if not p.exists():
                raise FileNotFoundError(f"Reference not found: {ref}")
            image_urls.append(_upload_file(p, base_url=base_url, token=token))

    payload: dict = {
        "model": f"fal-ai/{selected_model}",
        "prompt": prompt,
        "image_urls": image_urls,
        "quality": quality,
        "output_format": "png",
        "num_images": 1,
    }
    parsed = _parse_size(size)
    if parsed is not None:
        payload["image_size"] = parsed
    if mask:
        if mask.startswith(("http://", "https://")):
            payload["mask_url"] = mask
        else:
            payload["mask_url"] = _upload_file(Path(mask), base_url=base_url, token=token)

    print(
        f"[edit] model={selected_model} refs={len(image_urls)} quality={quality}",
        flush=True,
    )
    result = _submit_and_wait(
        model=selected_model,
        payload=payload,
        queue_state_path=queue_state_path,
    )
    url = _first_image_url(result)
    _download(url, out_path)
    print(f"[edit] saved -> {out_path}", flush=True)
    return url
