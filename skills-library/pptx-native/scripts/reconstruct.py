#!/usr/bin/env python3
"""Build editable PPTX reconstructions from an Agent-authored OfficeCLI command plan."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from collections import Counter
from pathlib import Path
from typing import Any

from reconstruct_audit import (
    PptxAuditError,
    assert_editable_output,
    audit_pptx,
    route_input,
)
from reconstruct_visual import (
    VisualComparisonError,
    compare_render_directories,
)


MIN_OFFICECLI_VERSION = (1, 0, 139)
MUTATING_COMMANDS = frozenset({"add", "set", "remove", "move", "swap", "raw-set"})
NAMED_ADD_TYPES = frozenset(
    {"slide", "shape", "picture", "connector", "chart", "table", "group"}
)
DRAWING_ID_ADD_TYPES = frozenset({"shape", "picture", "connector", "chart", "table"})
ASSET_PROPERTIES = frozenset({"src", "image"})
PRESENTATION_FRAGMENT = "00-presentation.json"
SLIDE_FRAGMENT_PATTERN = re.compile(r"slide-(\d+)\.json$")
SLIDE_REFERENCE_PATTERN = re.compile(r"/slide\[(\d+)\]")
SLIDE_PART_PATTERN = re.compile(r"(?:^|/)ppt/slides/slide(\d+)\.xml$")
RUNTIME_PROBE_PROPERTIES = frozenset(
    {
        ("add", "shape", "wrap"),
    }
)


class ReconstructionError(RuntimeError):
    """Raised when OfficeCLI cannot safely complete a reconstruction."""


def _write_json(path: str | Path, payload: Any) -> Path:
    target = Path(path).expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return target


def _sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).expanduser().resolve().open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json_sha256(payload: Any) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _version_tuple(value: str) -> tuple[int, int, int]:
    match = re.search(r"(?<!\d)(\d+)\.(\d+)\.(\d+)(?!\d)", value)
    if not match:
        raise ReconstructionError(f"Cannot parse OfficeCLI version: {value.strip()}")
    return tuple(int(part) for part in match.groups())


def _officecli_environment() -> dict[str, str]:
    return {
        **os.environ,
        "OFFICECLI_SKIP_UPDATE": "1",
        "OFFICECLI_NO_AUTO_RESIDENT": "1",
        "OFFICECLI_RESIDENT_FLUSH": "each",
    }


def resolve_officecli(executable: str | Path | None = None) -> dict[str, Any]:
    configured = executable or os.environ.get("OFFICECLI_BIN")
    candidate = Path(configured).expanduser() if configured else None
    if candidate is None:
        discovered = shutil.which("officecli")
        candidate = Path(discovered) if discovered else None
    if candidate is None or not candidate.is_file():
        raise ReconstructionError(
            "OfficeCLI is unavailable. The managed runtime must provide the pinned binary."
        )
    candidate = candidate.resolve()
    process = subprocess.run(
        [str(candidate), "--version"],
        check=False,
        capture_output=True,
        text=True,
        env=_officecli_environment(),
    )
    if process.returncode != 0:
        raise ReconstructionError(
            process.stderr.strip() or process.stdout.strip() or "OfficeCLI --version failed."
        )
    version_text = (process.stdout or process.stderr).strip()
    parsed = _version_tuple(version_text)
    if parsed < MIN_OFFICECLI_VERSION:
        minimum = ".".join(str(part) for part in MIN_OFFICECLI_VERSION)
        raise ReconstructionError(
            f"OfficeCLI {version_text} is too old; reconstruction requires >= {minimum} for atomic batch."
        )
    return {
        "path": str(candidate),
        "version": ".".join(str(part) for part in parsed),
        "sha256": _sha256(candidate),
    }


def _run(
    binding: dict[str, Any],
    arguments: list[str],
) -> subprocess.CompletedProcess[str]:
    process = subprocess.run(
        [binding["path"], *arguments],
        check=False,
        capture_output=True,
        text=True,
        env=_officecli_environment(),
    )
    if process.returncode != 0:
        label = " ".join(arguments[:4])
        raise ReconstructionError(
            process.stderr.strip()
            or process.stdout.strip()
            or f"OfficeCLI command failed: {label}"
        )
    return process


def _run_json(
    binding: dict[str, Any],
    arguments: list[str],
    description: str,
) -> dict[str, Any]:
    process = subprocess.run(
        [binding["path"], *arguments],
        check=False,
        capture_output=True,
        text=True,
        env=_officecli_environment(),
    )
    try:
        payload = json.loads(process.stdout)
    except json.JSONDecodeError as exc:
        if process.returncode != 0:
            raise ReconstructionError(
                process.stderr.strip()
                or process.stdout.strip()
                or f"{description} failed with exit code {process.returncode}."
            ) from exc
        raise ReconstructionError(
            f"{description} did not return JSON: {process.stdout.strip()}"
        ) from exc
    if not isinstance(payload, dict):
        raise ReconstructionError(f"{description} returned a non-object JSON payload.")
    if process.returncode != 0 or payload.get("success") is False:
        data = payload.get("data")
        details: dict[str, Any] = {}
        if isinstance(data, dict):
            for key in ("summary", "outputFile"):
                if key in data:
                    details[key] = data[key]
            results = data.get("results")
            if isinstance(results, list):
                failed = next(
                    (item for item in results if isinstance(item, dict) and item.get("success") is False),
                    None,
                )
                if failed is not None:
                    details["firstFailure"] = failed
        if not details:
            details["data"] = data
        raise ReconstructionError(
            f"{description} failed: {json.dumps(details, ensure_ascii=False, separators=(',', ':'))}"
        )
    return payload


def _normalize_validation(payload: dict[str, Any]) -> dict[str, Any]:
    data = payload.get("data")
    if isinstance(data, dict):
        return payload
    if isinstance(data, str) and "no errors" in data.casefold():
        return {**payload, "rawData": data, "data": {"count": 0, "errors": []}}
    raise ReconstructionError(f"OfficeCLI validation returned an unknown payload: {payload}")


def load_command_plan(path: str | Path) -> list[dict[str, Any]]:
    source = Path(path).expanduser().resolve()
    return _load_command_array(source, "officecli-commands.json")


def _load_command_array(source: Path, label: str) -> list[dict[str, Any]]:
    payload = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ReconstructionError(
            f"{label} must be a native OfficeCLI command array, not an envelope."
        )
    if not payload:
        raise ReconstructionError(f"{label} must contain at least one command.")
    if not all(isinstance(command, dict) for command in payload):
        raise ReconstructionError(f"Every command in {label} must be a JSON object.")
    return payload


def _is_external_asset(value: str) -> bool:
    lowered = value.casefold()
    return lowered.startswith(("data:", "http://", "https://"))


def _drawing_id(value: Any, *, command_index: int, required: bool) -> int | None:
    if value is None and not required:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ReconstructionError(
            f"Add command {command_index} requires props.id as a positive integer."
        )
    return value


def _drawing_scope(parent: str) -> str:
    match = SLIDE_REFERENCE_PATTERN.search(parent)
    return f"/slide[{match.group(1)}]" if match else parent


def _assign_drawing_ids(
    commands: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    assembled = copy.deepcopy(commands)
    used_by_parent: dict[str, set[int]] = {}
    for index, command in enumerate(assembled):
        if command.get("command") != "add" or command.get("type") not in DRAWING_ID_ADD_TYPES:
            continue
        parent = command.get("parent")
        props = command.get("props")
        if not isinstance(parent, str) or not isinstance(props, dict):
            continue
        value = props.get("id")
        if value is None:
            continue
        drawing_id = _drawing_id(value, command_index=index, required=True)
        assert drawing_id is not None
        scope = _drawing_scope(parent)
        used = used_by_parent.setdefault(scope, set())
        if drawing_id in used:
            raise ReconstructionError(
                f"Add command {index} reuses drawing props.id {drawing_id} under {scope}."
            )
        used.add(drawing_id)

    assigned: list[dict[str, Any]] = []
    for index, command in enumerate(assembled):
        if command.get("command") != "add" or command.get("type") not in DRAWING_ID_ADD_TYPES:
            continue
        parent = command.get("parent")
        props = command.get("props")
        if not isinstance(parent, str) or not isinstance(props, dict) or props.get("id") is not None:
            continue
        used = used_by_parent.setdefault(_drawing_scope(parent), set())
        drawing_id = 2
        while drawing_id in used:
            drawing_id += 1
        props["id"] = drawing_id
        used.add(drawing_id)
        assigned.append(
            {
                "command": index,
                "parent": parent,
                "type": command.get("type"),
                "name": props.get("name"),
                "id": drawing_id,
            }
        )
    return assembled, assigned


def prepare_command_plan(
    commands: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Apply deterministic mechanical defaults to one native command array."""
    prepared, assigned = _assign_drawing_ids(commands)
    return prepared, {
        "ok": True,
        "mode": "single-command-plan",
        "autoAssignedDrawingIds": assigned,
        "commands": len(prepared),
        "nativeOfficeCLIArray": True,
        "semanticIntermediateRepresentation": False,
    }


def _command_slide_references(command: dict[str, Any]) -> set[int]:
    references: set[int] = set()
    for key in ("path", "parent", "from", "to", "before", "after"):
        value = command.get(key)
        if isinstance(value, str):
            references.update(int(match) for match in SLIDE_REFERENCE_PATTERN.findall(value))
    props = command.get("props")
    if isinstance(props, dict):
        for key in ("from", "to"):
            value = props.get(key)
            if isinstance(value, str):
                references.update(int(match) for match in SLIDE_REFERENCE_PATTERN.findall(value))
    part = command.get("part")
    if isinstance(part, str):
        part_match = SLIDE_PART_PATTERN.search(part)
        if part_match:
            references.add(int(part_match.group(1)))
    return references


def assemble_command_fragments(
    directory: str | Path,
    *,
    allow_raw_set: bool = False,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Concatenate native per-slide arrays and assign deterministic drawing IDs."""
    root = Path(directory).expanduser().resolve()
    if not root.is_dir():
        raise ReconstructionError(f"Command fragment directory does not exist: {root}")
    presentation_path = root / PRESENTATION_FRAGMENT
    if not presentation_path.is_file():
        raise ReconstructionError(
            f"Command fragments require {PRESENTATION_FRAGMENT}."
        )

    unknown_json: list[str] = []
    slide_paths: list[tuple[int, Path]] = []
    for path in sorted(root.glob("*.json")):
        if path.name == PRESENTATION_FRAGMENT:
            continue
        match = SLIDE_FRAGMENT_PATTERN.fullmatch(path.name)
        if not match:
            unknown_json.append(path.name)
            continue
        slide_number = int(match.group(1))
        canonical_name = f"slide-{slide_number:02d}.json"
        if path.name != canonical_name:
            raise ReconstructionError(
                f"Slide fragment '{path.name}' must use canonical name '{canonical_name}'."
            )
        slide_paths.append((slide_number, path))
    if unknown_json:
        raise ReconstructionError(
            "Unexpected JSON fragment(s): " + ", ".join(unknown_json)
        )
    if not slide_paths:
        raise ReconstructionError("Command fragments require at least slide-01.json.")
    slide_paths.sort(key=lambda item: item[0])
    actual_numbers = [number for number, _ in slide_paths]
    expected_numbers = list(range(1, len(slide_paths) + 1))
    if actual_numbers != expected_numbers:
        raise ReconstructionError(
            "Slide fragments must be contiguous from slide-01.json; found "
            + ", ".join(path.name for _, path in slide_paths)
            + "."
        )

    presentation = _load_command_array(presentation_path, PRESENTATION_FRAGMENT)
    for index, command in enumerate(presentation):
        if command.get("command") != "set" or command.get("path") != "/":
            raise ReconstructionError(
                f"{PRESENTATION_FRAGMENT} command {index} must be a presentation set on path '/'."
            )

    merged = copy.deepcopy(presentation)
    fragment_files = [PRESENTATION_FRAGMENT]
    fragment_counts: dict[str, int] = {PRESENTATION_FRAGMENT: len(presentation)}
    for slide_number, path in slide_paths:
        label = path.name
        fragment = _load_command_array(path, label)
        first = fragment[0]
        expected_name = f"slide-{slide_number:02d}"
        props = first.get("props")
        if (
            first.get("command") != "add"
            or first.get("type") != "slide"
            or first.get("parent") != "/"
            or not isinstance(props, dict)
            or props.get("name") != expected_name
        ):
            raise ReconstructionError(
                f"{label} must start with add slide parent '/' and props.name '{expected_name}'."
            )
        for index, command in enumerate(fragment[1:], start=1):
            if command.get("command") == "add" and command.get("type") == "slide":
                raise ReconstructionError(f"{label} command {index} adds an extra slide.")
            references = _command_slide_references(command)
            if not references:
                raise ReconstructionError(
                    f"{label} command {index} is not scoped to /slide[{slide_number}]."
                )
            if references != {slide_number}:
                found = ", ".join(str(item) for item in sorted(references))
                raise ReconstructionError(
                    f"{label} command {index} crosses slide scope; expected {slide_number}, found {found}."
                )
        merged.extend(copy.deepcopy(fragment))
        fragment_files.append(label)
        fragment_counts[label] = len(fragment)

    assembled, assigned = _assign_drawing_ids(merged)
    preflight = validate_command_plan(
        assembled,
        allow_raw_set=allow_raw_set,
        require_drawing_ids=True,
    )
    return assembled, {
        "ok": True,
        "directory": str(root),
        "files": fragment_files,
        "fragmentCommandCounts": fragment_counts,
        "autoAssignedDrawingIds": assigned,
        "commands": len(assembled),
        "slides": preflight["slides"],
        "nativeOfficeCLIArray": True,
        "semanticIntermediateRepresentation": False,
    }


def validate_command_plan(
    commands: list[dict[str, Any]],
    *,
    allow_raw_set: bool = False,
    require_drawing_ids: bool = True,
) -> dict[str, Any]:
    """Validate reconstruction invariants without duplicating OfficeCLI's property schema."""
    if not commands:
        raise ReconstructionError("The OfficeCLI command plan is empty.")

    slide_count = 0
    command_types: Counter[str] = Counter()
    add_types: Counter[str] = Counter()
    asset_paths: set[str] = set()
    stable_names: dict[tuple[str, str], int] = {}
    drawing_ids: dict[tuple[str, int], int] = {}
    presentation_size: dict[str, str] = {}
    for index, command in enumerate(commands):
        verb = command.get("command")
        if not isinstance(verb, str) or not verb:
            raise ReconstructionError(f"Command {index} is missing a string 'command'.")
        if verb not in MUTATING_COMMANDS:
            allowed = ", ".join(sorted(MUTATING_COMMANDS))
            raise ReconstructionError(
                f"Command {index} uses unsupported reconstruction verb '{verb}'. Allowed: {allowed}."
            )
        command_types[verb] += 1
        if verb == "raw-set" and not allow_raw_set:
            raise ReconstructionError(
                f"Command {index} uses raw-set. Query structured OfficeCLI help first, "
                "then pass --allow-raw-set only when no structured operation can preserve the feature."
            )
        props_value = command.get("props")
        if verb in {"add", "set"} and not isinstance(props_value, dict):
            raise ReconstructionError(
                f"{verb.capitalize()} command {index} is missing object 'props'."
            )
        if isinstance(props_value, dict):
            for key in ASSET_PROPERTIES:
                value = props_value.get(key)
                if not isinstance(value, str) or not value or _is_external_asset(value):
                    continue
                asset = Path(value).expanduser()
                if not asset.is_absolute():
                    raise ReconstructionError(
                        f"Command {index} property '{key}' must use an absolute asset path."
                    )
                if not asset.is_file():
                    raise ReconstructionError(
                        f"Command {index} references a missing asset: {asset}"
                    )
                asset_paths.add(str(asset.resolve()))

        if verb == "set" and command.get("path") == "/":
            assert isinstance(props_value, dict)
            for key in ("slideWidth", "slideHeight"):
                value = props_value.get(key)
                if isinstance(value, str) and value.strip():
                    presentation_size[key] = value

        if verb != "add":
            continue
        element_type = command.get("type")
        parent = command.get("parent")
        props = command.get("props")
        if not isinstance(element_type, str) or not element_type:
            raise ReconstructionError(f"Add command {index} is missing a string 'type'.")
        if not isinstance(parent, str) or not parent:
            raise ReconstructionError(f"Add command {index} is missing a string 'parent'.")
        if not isinstance(props, dict):
            raise ReconstructionError(f"Add command {index} is missing object 'props'.")
        add_types[element_type] += 1

        if element_type == "slide":
            if parent != "/":
                raise ReconstructionError(f"Slide add command {index} must use parent '/'.")
            slide_count += 1

        if element_type in NAMED_ADD_TYPES:
            name = props.get("name")
            if not isinstance(name, str) or not name.strip():
                raise ReconstructionError(
                    f"Add command {index} for {element_type} requires a stable props.name."
                )
            name_key = (parent, name)
            if name_key in stable_names:
                first_index = stable_names[name_key]
                raise ReconstructionError(
                    f"Add commands {first_index} and {index} reuse stable name '{name}' under {parent}."
                )
            stable_names[name_key] = index

        if element_type in DRAWING_ID_ADD_TYPES:
            drawing_id = _drawing_id(
                props.get("id"),
                command_index=index,
                required=require_drawing_ids,
            )
            if drawing_id is not None:
                scope = _drawing_scope(parent)
                id_key = (scope, drawing_id)
                if id_key in drawing_ids:
                    first_index = drawing_ids[id_key]
                    raise ReconstructionError(
                        f"Add commands {first_index} and {index} reuse drawing props.id "
                        f"{drawing_id} under {scope}."
                    )
                drawing_ids[id_key] = index

    if slide_count == 0:
        raise ReconstructionError("The command plan must add at least one slide to the blank PPTX.")
    missing_dimensions = [
        key for key in ("slideWidth", "slideHeight") if key not in presentation_size
    ]
    if missing_dimensions:
        raise ReconstructionError(
            "The command plan must explicitly set presentation "
            + " and ".join(missing_dimensions)
            + " on path '/'."
        )

    return {
        "ok": True,
        "commands": len(commands),
        "slides": slide_count,
        "commandTypes": dict(sorted(command_types.items())),
        "addTypes": dict(sorted(add_types.items())),
        "presentationSize": presentation_size,
        "localAssets": sorted(asset_paths),
        "rawSetAllowed": allow_raw_set,
        "officecliSchemaAuthority": True,
    }


def _path_element(path: str) -> str:
    if path == "/":
        return "presentation"
    segments = [segment for segment in path.split("/") if segment]
    if not segments:
        raise ReconstructionError(f"Cannot infer OfficeCLI element from path: {path}")
    match = re.match(r"([A-Za-z][A-Za-z0-9_-]*)", segments[-1])
    if not match:
        raise ReconstructionError(f"Cannot infer OfficeCLI element from path: {path}")
    return match.group(1)


def _schema_subject(command: dict[str, Any], command_index: int) -> tuple[str, str] | None:
    verb = command.get("command")
    props = command.get("props")
    if verb not in {"add", "set"} or not isinstance(props, dict):
        return None
    if verb == "add":
        element = command.get("type")
        if not isinstance(element, str) or not element:
            raise ReconstructionError(
                f"Add command {command_index} is missing a string 'type'."
            )
        return verb, element
    path = command.get("path")
    if not isinstance(path, str) or not path:
        raise ReconstructionError(f"Set command {command_index} is missing a string 'path'.")
    return verb, _path_element(path)


def _query_shape_wrap(
    binding: dict[str, Any],
    pptx: Path,
    *,
    expected: bool,
) -> bool:
    payload = _run_json(
        binding,
        [
            "query",
            str(pptx),
            'shape[name="wrap-probe"]',
            "--json",
        ],
        "OfficeCLI shape.wrap capability probe readback",
    )
    data = payload.get("data")
    if not isinstance(data, dict):
        return False
    results = data.get("results")
    if not isinstance(results, list) or len(results) != 1:
        return False
    result = results[0]
    if not isinstance(result, dict):
        return False
    shape_format = result.get("format")
    return isinstance(shape_format, dict) and shape_format.get("wrap") is expected


def _probe_shape_wrap_add(
    binding: dict[str, Any],
) -> bool:
    """Verify add shape.wrap when machine-readable help omits it."""
    with tempfile.TemporaryDirectory(prefix="pptx-native-officecli-probe-") as tmp:
        probe = Path(tmp) / "shape-wrap.pptx"
        _run(binding, ["create", str(probe)])
        add_commands = [
            {
                "command": "add",
                "parent": "/",
                "type": "slide",
                "props": {"layout": "blank", "name": "probe-slide"},
            },
            {
                "command": "add",
                "parent": "/slide[1]",
                "type": "shape",
                "props": {
                    "name": "wrap-probe",
                    "text": "wrap probe",
                    "x": "0px",
                    "y": "0px",
                    "width": "32px",
                    "height": "16px",
                    "wrap": False,
                },
            },
        ]
        _run_json(
            binding,
            [
                "batch",
                str(probe),
                "--commands",
                json.dumps(add_commands, separators=(",", ":")),
                "--json",
            ],
            "OfficeCLI shape.wrap add capability probe",
        )
        return _query_shape_wrap(binding, probe, expected=False)


def validate_against_officecli_schema(
    commands: list[dict[str, Any]],
    binding: dict[str, Any],
) -> dict[str, Any]:
    """Validate every add/set prop against the installed OfficeCLI help schema."""
    schemas: dict[tuple[str, str], dict[str, Any]] = {}
    runtime_probe_results: dict[tuple[str, str, str], bool] = {}
    used_runtime_properties: set[tuple[str, str, str]] = set()
    checked_commands = 0
    checked_properties = 0
    for index, command in enumerate(commands):
        subject = _schema_subject(command, index)
        if subject is None:
            continue
        verb, element = subject
        if subject not in schemas:
            schemas[subject] = _run_json(
                binding,
                ["help", "pptx", verb, element, "--json"],
                f"OfficeCLI schema help for pptx {verb} {element}",
            )
        schema = schemas[subject]
        properties = schema.get("properties")
        if not isinstance(properties, dict):
            raise ReconstructionError(
                f"OfficeCLI schema for pptx {verb} {element} has no properties object."
            )
        allowed: set[str] = set()
        for canonical, descriptor in properties.items():
            if not isinstance(canonical, str) or not isinstance(descriptor, dict):
                continue
            if descriptor.get(verb) is not True:
                continue
            allowed.add(canonical)
            aliases = descriptor.get("aliases")
            if isinstance(aliases, list):
                allowed.update(alias for alias in aliases if isinstance(alias, str))
        props = command["props"]
        unsupported = sorted(key for key in props if key not in allowed)
        probe_candidates = {
            (verb, element, key)
            for key in unsupported
            if (verb, element, key) in RUNTIME_PROBE_PROPERTIES
        }
        if probe_candidates:
            wrap_add = ("add", "shape", "wrap")
            if wrap_add in probe_candidates and wrap_add not in runtime_probe_results:
                runtime_probe_results[wrap_add] = _probe_shape_wrap_add(binding)
            verified_candidates = {
                candidate
                for candidate in probe_candidates
                if runtime_probe_results.get(candidate) is True
            }
            used_runtime_properties.update(verified_candidates)
            unsupported = [
                key
                for key in unsupported
                if (verb, element, key) not in verified_candidates
            ]
        if unsupported:
            raise ReconstructionError(
                f"Command {index} uses unsupported pptx {verb} {element} propert"
                f"{'y' if len(unsupported) == 1 else 'ies'}: {', '.join(unsupported)}."
            )
        checked_commands += 1
        checked_properties += len(props)
    return {
        "ok": True,
        "officecli": binding,
        "schemasQueried": [
            {"verb": verb, "element": element}
            for verb, element in sorted(schemas)
        ],
        "checkedCommands": checked_commands,
        "checkedProperties": checked_properties,
        "runtimeProbedProperties": [
            {"verb": verb, "element": element, "property": property_name}
            for verb, element, property_name in sorted(used_runtime_properties)
        ],
        "rawSetSchemaChecked": False,
    }


def _render_slides(
    binding: dict[str, Any],
    pptx: Path,
    output_dir: Path,
    slide_count: int,
    width: int,
    height: int,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    for stale in output_dir.glob("slide-*.png"):
        stale.unlink()
    started = time.perf_counter()
    paths: list[str] = []
    for slide_number in range(1, slide_count + 1):
        target = output_dir / f"slide-{slide_number}.png"
        _run(
            binding,
            [
                "view",
                str(pptx),
                "screenshot",
                "--page",
                str(slide_number),
                "--out",
                str(target),
                "--screenshot-width",
                str(width),
                "--screenshot-height",
                str(height),
                "--render",
                "html",
            ],
        )
        if not target.is_file():
            raise ReconstructionError(f"OfficeCLI did not render slide {slide_number}.")
        paths.append(str(target))
    return {
        "renderer": "officecli-html",
        "independentViewer": False,
        "slideCount": slide_count,
        "width": width,
        "height": height,
        "paths": paths,
        "seconds": time.perf_counter() - started,
    }


def _atomic_publish(source: Path, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    adjacent = output.parent / f".{output.name}.reconstruct-{uuid.uuid4().hex}.tmp"
    try:
        shutil.copy2(source, adjacent)
        os.replace(adjacent, output)
    finally:
        adjacent.unlink(missing_ok=True)


def default_build_workspace(output_path: str | Path) -> Path:
    output = Path(output_path).expanduser().resolve()
    return output.parent / f".{output.name}.reconstruction"


def build_commands(
    commands: list[dict[str, Any]],
    *,
    source_render_directory: str | Path,
    output_path: str | Path,
    workspace: str | Path | None = None,
    officecli_bin: str | Path | None = None,
    allow_raw_set: bool = False,
    assembly: dict[str, Any] | None = None,
    screenshot_width: int = 2048,
    screenshot_height: int = 1152,
) -> dict[str, Any]:
    started = time.perf_counter()
    output = Path(output_path).expanduser().resolve()
    commands, direct_preparation = prepare_command_plan(commands)
    if assembly is None:
        assembly = direct_preparation
    runtime = (
        Path(workspace).expanduser().resolve()
        if workspace is not None
        else default_build_workspace(output)
    )
    source_renders = Path(source_render_directory).expanduser().resolve()
    if not source_renders.is_dir():
        raise ReconstructionError(
            f"Source render directory does not exist: {source_renders}"
        )
    runtime.mkdir(parents=True, exist_ok=True)

    preflight_started = time.perf_counter()
    preflight = validate_command_plan(commands, allow_raw_set=allow_raw_set)
    binding = resolve_officecli(officecli_bin)
    schema_validation = validate_against_officecli_schema(commands, binding)
    commands_path = _write_json(runtime / "officecli-commands.json", commands)
    preflight_seconds = time.perf_counter() - preflight_started

    temporary = runtime / f"officecli-reconstruction-{uuid.uuid4().hex}.pptx"
    try:
        create_started = time.perf_counter()
        _run(binding, ["create", str(temporary)])
        create_seconds = time.perf_counter() - create_started

        batch_started = time.perf_counter()
        batch = _run_json(
            binding,
            ["batch", str(temporary), "--input", str(commands_path), "--json"],
            "OfficeCLI reconstruction atomic batch",
        )
        batch_seconds = time.perf_counter() - batch_started
        batch_data = batch.get("data")
        rolled_back = batch.get("atomicRolledBack") is True or (
            isinstance(batch_data, dict) and batch_data.get("atomicRolledBack") is True
        )
        if rolled_back:
            raise ReconstructionError("OfficeCLI rolled back the reconstruction batch.")

        validation_started = time.perf_counter()
        validation = _normalize_validation(
            _run_json(
                binding,
                ["validate", str(temporary), "--json"],
                "OfficeCLI validation",
            )
        )
        validation_seconds = time.perf_counter() - validation_started
        validation_count = int(validation.get("data", {}).get("count", 0))
        if validation_count:
            raise ReconstructionError(
                f"OfficeCLI generated {validation_count} OpenXML validation error(s)."
            )

        audit_started = time.perf_counter()
        expected_slides = int(preflight["slides"])
        temporary_audit = audit_pptx(temporary)
        assert_editable_output(temporary_audit, expected_slides)
        audit_seconds = time.perf_counter() - audit_started

        diagnostics_started = time.perf_counter()
        inspect = _run_json(
            binding,
            ["get", str(temporary), "/", "--depth", "3", "--json"],
            "OfficeCLI reconstruction inspect",
        )
        issues = _run_json(
            binding,
            ["view", str(temporary), "issues", "--json"],
            "OfficeCLI reconstruction issues",
        )
        stats = _run_json(
            binding,
            ["view", str(temporary), "stats", "--json"],
            "OfficeCLI reconstruction stats",
        )
        _write_json(runtime / "officecli-inspect.json", inspect)
        _write_json(runtime / "officecli-validation.json", validation)
        _write_json(runtime / "officecli-issues.json", issues)
        _write_json(runtime / "officecli-stats.json", stats)
        diagnostics_seconds = time.perf_counter() - diagnostics_started

        preview = _render_slides(
            binding,
            temporary,
            runtime / "preview",
            expected_slides,
            screenshot_width,
            screenshot_height,
        )
        visual_started = time.perf_counter()
        try:
            visual_comparison = compare_render_directories(
                source_renders,
                runtime / "preview",
                expected_slides,
            )
        except VisualComparisonError as exc:
            raise ReconstructionError(
                f"Visual fidelity comparison could not run: {exc}"
            ) from exc
        _write_json(
            runtime / "visual-comparison.json",
            visual_comparison.to_dict(),
        )
        visual_seconds = time.perf_counter() - visual_started
        if not visual_comparison.passed:
            failed_slides = ", ".join(
                f"{item.slide}={item.normalized_mae:.2%}"
                for item in visual_comparison.slide_details
                if not item.passed
            )
            if not failed_slides:
                failed_slides = "none above the per-slide limit"
            raise ReconstructionError(
                "Visual fidelity gate failed: "
                f"average {visual_comparison.average_normalized_mae:.2%} "
                f"(limit {visual_comparison.average_limit:.2%}); "
                f"maximum {visual_comparison.maximum_normalized_mae:.2%} "
                f"(per-slide limit {visual_comparison.slide_limit:.2%}); "
                f"failed slides: {failed_slides}."
            )
        publish_started = time.perf_counter()
        _atomic_publish(temporary, output)
        final_audit = audit_pptx(output)
        assert_editable_output(final_audit, expected_slides)
        publish_seconds = time.perf_counter() - publish_started
    finally:
        temporary.unlink(missing_ok=True)

    report: dict[str, Any] = {
        "ok": True,
        "backend": "officecli",
        "officecli": binding,
        "pptx": str(output),
        "pptxSha256": _sha256(output),
        "commandPlanSha256": _json_sha256(commands),
        "commandsPath": str(commands_path),
        "slides": preflight["slides"],
        "commandCount": preflight["commands"],
        "commandTypes": preflight["commandTypes"],
        "combinedAtomicBatch": True,
        "assembly": assembly,
        "preflight": preflight,
        "schemaValidation": schema_validation,
        "batch": batch,
        "validation": validation,
        "audit": final_audit.to_dict(),
        "stats": stats,
        "issues": issues,
        "preview": preview,
        "visualComparison": visual_comparison.to_dict(),
        "sourceOfTruth": "officecli-command-plan-until-delivery",
        "crossViewerFidelityVerified": False,
        "warnings": [
            "OfficeCLI issues are diagnostic; inspect every screenshot at full size, especially CJK wrap=false titles.",
            "The visual gate compares supplied source renders with OfficeCLI HTML renders; it is a regression floor, not small-detail or independent-viewer proof.",
            "OfficeCLI HTML screenshots are same-stack evidence. PowerPoint/WPS fidelity is not verified.",
            "After delivery or external edits, treat the PPTX as source of truth and do not rebuild from a stale command plan.",
        ],
        "timingsSeconds": {
            "preflight": preflight_seconds,
            "create": create_seconds,
            "atomicBatch": batch_seconds,
            "validation": validation_seconds,
            "externalAudit": audit_seconds,
            "diagnostics": diagnostics_seconds,
            "preview": preview["seconds"],
            "visualComparison": visual_seconds,
            "publish": publish_seconds,
            "total": time.perf_counter() - started,
        },
    }
    report_path = runtime / "build-report.json"
    report["report"] = str(report_path)
    _write_json(report_path, report)
    return report


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Execute an Agent-authored OfficeCLI reconstruction command plan."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    audit = subparsers.add_parser("audit-pptx", help="Classify a PPTX as flattened, native, or mixed.")
    audit.add_argument("input")

    assemble = subparsers.add_parser(
        "assemble",
        help="Assemble native per-slide OfficeCLI arrays into officecli-commands.json.",
    )
    assemble.add_argument("--fragments", required=True)
    assemble.add_argument("--out", required=True)
    assemble.add_argument("--officecli-bin")
    assemble.add_argument("--allow-raw-set", action="store_true")

    validate = subparsers.add_parser(
        "validate", help="Validate reconstruction invariants for an OfficeCLI command plan."
    )
    validate_source = validate.add_mutually_exclusive_group(required=True)
    validate_source.add_argument("--commands")
    validate_source.add_argument("--fragments")
    validate.add_argument("--officecli-bin")
    validate.add_argument("--allow-raw-set", action="store_true")

    build = subparsers.add_parser(
        "build", help="Build the OfficeCLI command plan as an editable PPTX."
    )
    build_source = build.add_mutually_exclusive_group(required=True)
    build_source.add_argument("--commands")
    build_source.add_argument("--fragments")
    build.add_argument("--source-renders", required=True)
    build.add_argument("--out", required=True)
    build.add_argument(
        "--workspace",
        help="Optional diagnostics directory. Defaults beside --out.",
    )
    build.add_argument("--officecli-bin")
    build.add_argument("--allow-raw-set", action="store_true")
    build.add_argument("--screenshot-width", type=int, default=2048)
    build.add_argument("--screenshot-height", type=int, default=1152)
    return parser


def _load_command_source(
    args: argparse.Namespace,
) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    fragments = getattr(args, "fragments", None)
    if fragments:
        return assemble_command_fragments(
            fragments,
            allow_raw_set=args.allow_raw_set,
        )
    return prepare_command_plan(load_command_plan(args.commands))


def _run_command(args: argparse.Namespace) -> dict[str, Any]:
    if args.command == "audit-pptx":
        audit = audit_pptx(args.input)
        return {"ok": True, "route": route_input(audit), "audit": audit.to_dict()}

    commands, assembly = _load_command_source(args)
    if args.command == "build":
        return build_commands(
            commands,
            source_render_directory=args.source_renders,
            output_path=args.out,
            workspace=args.workspace,
            officecli_bin=args.officecli_bin,
            allow_raw_set=args.allow_raw_set,
            assembly=assembly,
            screenshot_width=args.screenshot_width,
            screenshot_height=args.screenshot_height,
        )

    preflight = validate_command_plan(commands, allow_raw_set=args.allow_raw_set)
    binding = resolve_officecli(args.officecli_bin)
    schema_validation = validate_against_officecli_schema(commands, binding)
    if args.command == "assemble":
        output = _write_json(args.out, commands)
        return {
            "ok": True,
            "commandsPath": str(output),
            "commandPlanSha256": _json_sha256(commands),
            "assembly": assembly,
            "preflight": preflight,
            "schemaValidation": schema_validation,
        }
    if args.command == "validate":
        return {
            "ok": True,
            "assembly": assembly,
            "preflight": preflight,
            "schemaValidation": schema_validation,
        }
    raise ReconstructionError(f"Unknown reconstruction command: {args.command}")


def _compact_build_result(result: dict[str, Any]) -> dict[str, Any]:
    batch_data = result.get("batch", {}).get("data", {})
    audit = result.get("audit", {})
    compact = {
        key: result[key]
        for key in (
            "ok",
            "backend",
            "officecli",
            "pptx",
            "pptxSha256",
            "commandPlanSha256",
            "commandsPath",
            "slides",
            "commandCount",
            "commandTypes",
            "combinedAtomicBatch",
            "preflight",
            "assembly",
            "schemaValidation",
        )
        if key in result
    }
    compact.update(
        {
            "batchSummary": batch_data.get("summary"),
            "validation": result.get("validation", {}).get("data"),
            "auditSummary": {
                key: audit.get(key)
                for key in (
                    "slides",
                    "flattened_slides",
                    "native_slides",
                    "mixed_slides",
                    "media_files",
                )
            },
            "stats": result.get("stats", {}).get("data"),
            "issues": result.get("issues", {}).get("data"),
            "preview": result.get("preview"),
            "visualComparison": result.get("visualComparison"),
            "sourceOfTruth": result.get("sourceOfTruth"),
            "crossViewerFidelityVerified": result.get("crossViewerFidelityVerified"),
            "warnings": result.get("warnings"),
            "timingsSeconds": result.get("timingsSeconds"),
            "report": result.get("report"),
        }
    )
    return compact


def main() -> int:
    args = _parser().parse_args()
    try:
        result = _run_command(args)
    except (ReconstructionError, PptxAuditError, OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1
    console_result = _compact_build_result(result) if "batch" in result else result
    print(json.dumps(console_result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
