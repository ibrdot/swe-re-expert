"""Deck: a directory of slides with metadata and auto-numbering.

Metadata reads/writes are protected by an advisory file lock so parallel gen/edit
processes can safely share a deck. Saves are atomic (tmp file + rename) so a
crashed or interrupted writer can never leave deck.json half-written.
"""

import fcntl
import json
import os
import re
import tempfile
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

WORKSPACE_ROOT = Path("/home/user/.workspace")
OUTPUTS_ROOT = WORKSPACE_ROOT / "outputs"
DECK_META_NAME = "deck.json"
DECK_LOCK_NAME = "deck.json.lock"
SLIDE_PATTERN = re.compile(r"^slide-(\d+)\.png$")
SOURCE_URL_PREFIX = "- **source_url**:"

IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp")


class Deck:
    """A deck is a directory under workspace outputs/ containing slide-NN.png files and a deck.json."""

    def __init__(self, name: str, root: Path | None = None) -> None:
        self.name = name
        self.root = (root or OUTPUTS_ROOT) / name
        self.meta_path = self.root / DECK_META_NAME
        self.lock_path = self.root / DECK_LOCK_NAME

    # ------------------------------------------------------------------ paths
    def slide_path(self, slot: int) -> Path:
        return self.root / f"slide-{slot:02d}.png"

    def prompt_path(self, slot: int) -> Path:
        return self.root / "prompts" / f"slide-{slot:02d}.md"

    def queue_job_path(self, slot: int) -> Path:
        return self.root / "queue-jobs" / f"slide-{slot:02d}.json"

    def pptx_path(self) -> Path:
        return self.root / "deck.pptx"

    def html_path(self) -> Path:
        return self.root / "index.html"

    # ---------------------------------------------------------------- listing
    def existing_slots(self) -> list[int]:
        if not self.root.exists():
            return []
        slots = []
        for p in self.root.iterdir():
            m = SLIDE_PATTERN.match(p.name)
            if m:
                slots.append(int(m.group(1)))
        return sorted(slots)

    def next_slot(self) -> int:
        slots = self.existing_slots()
        return (slots[-1] + 1) if slots else 1

    def slide_files(self) -> list[Path]:
        """Ordered slide PNGs. Fall back to any sorted images if naming isn't NN."""
        if not self.root.exists():
            return []
        numbered = sorted(
            (p for p in self.root.iterdir() if SLIDE_PATTERN.match(p.name)),
            key=lambda p: int(SLIDE_PATTERN.match(p.name).group(1)),
        )
        if numbered:
            return numbered
        return sorted(
            p for p in self.root.iterdir()
            if p.is_file() and p.suffix.lower() in IMAGE_EXTS
        )

    # ----------------------------------------------------------------- locking
    @contextmanager
    def _locked(self):
        """Advisory exclusive lock on the deck's metadata. Blocks until acquired."""
        self.root.mkdir(parents=True, exist_ok=True)
        # `a+` creates the lock file if missing; we never read/write its contents,
        # it exists only as the flock handle.
        with open(self.lock_path, "a+") as lf:
            fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lf.fileno(), fcntl.LOCK_UN)

    # --------------------------------------------------------------- metadata
    def load_meta(self) -> dict[str, Any]:
        """Read deck.json. Returns {} if missing or unreadable."""
        if not self.meta_path.exists():
            return {}
        try:
            return json.loads(self.meta_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}

    def source_url_for_slot(self, slot: int) -> str | None:
        """Return the current slot's recorded remote image URL when available."""
        slide_path = self.slide_path(slot)
        prompt_path = self.prompt_path(slot)
        prompt_url = self._source_url_from_prompt(
            prompt_path,
            slide_path=slide_path,
        )
        if prompt_url is not None:
            return prompt_url
        if prompt_path.exists():
            return None

        history = self.load_meta().get("history")
        if not isinstance(history, list):
            return None

        for entry in reversed(history):
            if not isinstance(entry, dict):
                continue
            if entry.get("slot") != slot:
                continue
            source_url = entry.get("source_url")
            if isinstance(source_url, str) and source_url.startswith(
                ("http://", "https://")
            ):
                return source_url
        return None

    def _source_url_from_prompt(self, path: Path, *, slide_path: Path) -> str | None:
        try:
            prompt_mtime_ns = path.stat().st_mtime_ns
            slide_mtime_ns = slide_path.stat().st_mtime_ns
            if slide_mtime_ns > prompt_mtime_ns:
                return None
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            return None

        for line in reversed(lines):
            if not line.startswith(SOURCE_URL_PREFIX):
                continue
            source_url = line[len(SOURCE_URL_PREFIX) :].strip()
            if source_url.startswith(("http://", "https://")):
                return source_url
            return None
        return None

    def _atomic_save(self, meta: dict[str, Any]) -> None:
        """Write deck.json via tmp-file + rename so partial writes never exist on disk.

        Uses tempfile.mkstemp in the same directory so the rename is atomic on
        the same filesystem, and the tmp name is unique per call.
        """
        self.root.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(prefix=".deck-", suffix=".tmp", dir=str(self.root))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(meta, f, ensure_ascii=False, indent=2)
            os.replace(tmp_name, self.meta_path)
        except BaseException:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
            raise

    # kept for backwards-compat in case anything imports it; prefer _atomic_save
    def save_meta(self, meta: dict[str, Any]) -> None:
        self._atomic_save(meta)

    def ensure_meta(self, *, size: str | None, quality: str | None) -> dict[str, Any]:
        """Create deck.json on first use, or update defaults if provided. Locked + atomic."""
        with self._locked():
            meta = self.load_meta()
            if not meta:
                meta = {
                    "name": self.name,
                    "created_at": datetime.now().isoformat(timespec="seconds"),
                    "size": size,
                    "quality": quality,
                    "history": [],
                }
            else:
                if size is not None:
                    meta["size"] = size
                if quality is not None:
                    meta["quality"] = quality
            self._atomic_save(meta)
            return meta

    def append_history(self, entry: dict[str, Any]) -> None:
        """Append one history record. Locked + atomic; safe under concurrent writers."""
        with self._locked():
            meta = self.load_meta()
            meta.setdefault("history", []).append({
                "at": datetime.now().isoformat(timespec="seconds"),
                **entry,
            })
            self._atomic_save(meta)

    def load_slot_notes(self) -> dict[int, str]:
        """Return slot → full prompt-file text for every slot that has a prompts/slide-NN.md."""
        notes: dict[int, str] = {}
        for slot in self.existing_slots():
            p = self.prompt_path(slot)
            if p.exists():
                notes[slot] = p.read_text(encoding="utf-8")
        return notes

    def write_prompt_md(
        self,
        slot: int,
        *,
        cmd: str,
        prompt: str,
        refs: list[str] | None = None,
        size: str | None = None,
        quality: str | None = None,
        model: str | None = None,
        source_url: str | None = None,
    ) -> Path:
        """Persist the full prompt + parameters for one slide to prompts/slide-NN.md.

        This is the human-readable, git-diffable, hand-editable companion to
        deck.json's history. Edit a file here then re-run `ppt edit <deck>
        --slot N` (with the prompt re-loaded from this file) to iterate.
        """
        path = self.prompt_path(slot)
        path.parent.mkdir(parents=True, exist_ok=True)

        lines = [
            f"# Slide {slot:02d}",
            "",
            "## Metadata",
            "",
            f"- **deck**: `{self.name}`",
            f"- **slot**: {slot}",
            f"- **command**: `{cmd}`",
            f"- **generated_at**: {datetime.now().isoformat(timespec='seconds')}",
        ]
        if size:
            lines.append(f"- **size**: `{size}`")
        if quality:
            lines.append(f"- **quality**: `{quality}`")
        if model:
            lines.append(f"- **model**: `{model}`")
        if refs:
            lines.append(f"- **refs**: {', '.join(f'`{r}`' for r in refs)}")
        if source_url:
            lines.append(f"- **source_url**: {source_url}")
        lines += ["", "## Prompt", "", prompt.rstrip(), ""]

        path.write_text("\n".join(lines), encoding="utf-8")
        return path
