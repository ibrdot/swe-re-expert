#!/usr/bin/env python3

from __future__ import annotations

import base64
import json
import os
import struct
import subprocess
import sys
import tempfile
import unittest
import zipfile
import xml.etree.ElementTree as ET
import zlib
from pathlib import Path
from unittest import mock

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from reconstruct import (
    ReconstructionError,
    _compact_build_result,
    _parser,
    assemble_command_fragments,
    build_commands,
    default_build_workspace,
    load_command_plan,
    prepare_command_plan,
    resolve_officecli,
    validate_against_officecli_schema,
    validate_command_plan,
)
from reconstruct_audit import PptxAuditError, assert_editable_output, audit_pptx, route_input
from reconstruct_visual import (
    VisualComparisonError,
    compare_png_renders,
    compare_render_directories,
)


PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


def _write_png(path: Path) -> None:
    path.write_bytes(PNG_1X1)


def _rgba_png(alpha: int) -> bytes:
    raw = b"\x00" + bytes((70, 80, 90, alpha))
    chunks: list[bytes] = []
    for chunk_type, payload in (
        (b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0)),
        (b"IDAT", zlib.compress(raw)),
        (b"IEND", b""),
    ):
        chunks.append(
            struct.pack(">I", len(payload))
            + chunk_type
            + payload
            + struct.pack(">I", zlib.crc32(chunk_type + payload) & 0xFFFFFFFF)
        )
    return b"\x89PNG\r\n\x1a\n" + b"".join(chunks)


def _solid_rgb_png(
    width: int,
    height: int,
    red: int,
    green: int,
    blue: int,
) -> bytes:
    pixel = bytes((red, green, blue))
    raw = b"".join(b"\x00" + pixel * width for _ in range(height))
    chunks: list[bytes] = []
    for chunk_type, payload in (
        (b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)),
        (b"IDAT", zlib.compress(raw)),
        (b"IEND", b""),
    ):
        chunks.append(
            struct.pack(">I", len(payload))
            + chunk_type
            + payload
            + struct.pack(">I", zlib.crc32(chunk_type + payload) & 0xFFFFFFFF)
        )
    return b"\x89PNG\r\n\x1a\n" + b"".join(chunks)


def _officecli_run(arguments: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [os.environ["OFFICECLI_BIN"], *arguments],
        check=True,
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "OFFICECLI_SKIP_UPDATE": "1",
            "OFFICECLI_NO_AUTO_RESIDENT": "1",
            "OFFICECLI_RESIDENT_FLUSH": "each",
        },
    )


def _render_reference(
    commands: list[dict],
    root: Path,
    *,
    width: int,
    height: int,
) -> Path:
    commands_path = root / "reference-commands.json"
    commands_path.write_text(
        json.dumps(commands, ensure_ascii=False),
        encoding="utf-8",
    )
    reference = root / "reference.pptx"
    _officecli_run(["create", str(reference)])
    _officecli_run(
        ["batch", str(reference), "--input", str(commands_path), "--json"]
    )
    renders = root / "source-renders"
    renders.mkdir()
    _officecli_run(
        [
            "view",
            str(reference),
            "screenshot",
            "--page",
            "1",
            "--out",
            str(renders / "slide-01.png"),
            "--screenshot-width",
            str(width),
            "--screenshot-height",
            str(height),
            "--render",
            "html",
        ]
    )
    return renders


def _commands(root: Path) -> list[dict]:
    icon = root / "icon.png"
    _write_png(icon)
    return [
        {
            "command": "set",
            "path": "/",
            "props": {
                "slideWidth": "320px",
                "slideHeight": "180px",
                "title": "OfficeCLI editable reconstruction",
            },
        },
        {
            "command": "add",
            "parent": "/",
            "type": "slide",
            "props": {"layout": "blank", "name": "slide-01", "background": "#F7F3EA"},
        },
        {
            "command": "add",
            "parent": "/slide[1]",
            "type": "shape",
            "props": {
                "id": 2,
                "name": "card",
                "geometry": "roundRect",
                "x": "15px",
                "y": "20px",
                "width": "110px",
                "height": "65px",
                "fill": "#E9DCC8",
                "line": "#8D5A3B",
                "lineWidth": "0.75pt",
                "adj": "adj:val 13846",
            },
        },
        {
            "command": "add",
            "parent": "/slide[1]",
            "type": "shape",
            "props": {
                "id": 3,
                "name": "title",
                "geometry": "rect",
                "x": "24px",
                "y": "30px",
                "width": "120px",
                "height": "35px",
                "fill": "none",
                "line": "none",
                "font": "Arial",
                "size": "18pt",
                "align": "left",
                "valign": "top",
                "autoFit": "normal",
                "color": "#1E1E1E",
                "margin": "0px",
                "text": "战争账单",
            },
        },
        {
            "command": "set",
            "path": "/slide[1]/shape[@name=title]",
            "props": {"font": "Arial", "bold": True},
        },
        {
            "command": "set",
            "path": "/slide[1]/shape[@name=title]",
            "props": {"font": "Courier New", "color": "#A53A2A"},
        },
        {
            "command": "add",
            "parent": "/slide[1]",
            "type": "picture",
            "props": {
                "id": 4,
                "name": "icon",
                "src": str(icon.resolve()),
                "x": "210px",
                "y": "25px",
                "width": "55px",
                "height": "55px",
                "crop": "10,5,10,5",
                "alt": "Circular test icon",
            },
        },
        {
            "command": "add",
            "parent": "/slide[1]",
            "type": "connector",
            "props": {
                "id": 5,
                "name": "rule",
                "shape": "straight",
                "x": "30px",
                "y": "110px",
                "width": "255px",
                "height": "1px",
                "headEnd": "arrow",
                "color": "#8D5A3B",
                "lineWidth": "1.125pt",
            },
        },
        {
            "command": "add",
            "parent": "/slide[1]",
            "type": "connector",
            "props": {
                "id": 6,
                "name": "link",
                "shape": "straight",
                "from": "/slide[1]/shape[@name=card]",
                "to": "/slide[1]/shape[@name=title]",
                "tailEnd": "arrow",
                "color": "#444444",
                "lineWidth": "0.75pt",
            },
        },
    ]


def _write_pptx(
    path: Path,
    slide_xmls: list[str],
    *,
    slide_relationships: dict[int, str] | None = None,
    media: dict[str, bytes] | None = None,
) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr(
            "ppt/presentation.xml",
            "<p:presentation xmlns:p='http://schemas.openxmlformats.org/presentationml/2006/main'/>",
        )
        for number, xml in enumerate(slide_xmls, start=1):
            archive.writestr(f"ppt/slides/slide{number}.xml", xml)
        for number, relationships in (slide_relationships or {}).items():
            archive.writestr(
                f"ppt/slides/_rels/slide{number}.xml.rels",
                relationships,
            )
        for name, payload in (media or {}).items():
            archive.writestr(f"ppt/media/{name}", payload)


PML = "http://schemas.openxmlformats.org/presentationml/2006/main"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
RML = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL = "http://schemas.openxmlformats.org/package/2006/relationships"


def _slide(body: str) -> str:
    return (
        f"<p:sld xmlns:p='{PML}' xmlns:a='{A_NS}' xmlns:r='{RML}'>"
        f"<p:cSld><p:spTree>{body}</p:spTree></p:cSld></p:sld>"
    )


def _picture(relationship_id: str) -> str:
    return (
        "<p:pic><p:blipFill>"
        f"<a:blip r:embed='{relationship_id}'/>"
        "</p:blipFill></p:pic>"
    )


def _relationships(targets: list[str]) -> str:
    relationships = "".join(
        f"<Relationship Id='rId{index}' Target='../media/{target}' Type='image'/>"
        for index, target in enumerate(targets, start=1)
    )
    return f"<Relationships xmlns='{PKG_REL}'>{relationships}</Relationships>"


class CommandPlanTests(unittest.TestCase):
    def test_officecli_before_tested_floor_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            executable = Path(tmp) / "officecli"
            executable.write_bytes(b"test binary")
            completed = subprocess.CompletedProcess(
                args=[str(executable), "--version"],
                returncode=0,
                stdout="officecli 1.0.138\n",
                stderr="",
            )
            with mock.patch("reconstruct.subprocess.run", return_value=completed):
                with self.assertRaises(ReconstructionError) as raised:
                    resolve_officecli(executable)

        self.assertIn("requires >= 1.0.139", str(raised.exception))

    def test_native_command_array_preflight_preserves_officecli_commands(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            commands = _commands(root)
            path = root / "officecli-commands.json"
            path.write_text(json.dumps(commands, ensure_ascii=False), encoding="utf-8")
            loaded = load_command_plan(path)
            report = validate_command_plan(loaded)

        self.assertEqual(commands, loaded)
        self.assertEqual(9, report["commands"])
        self.assertEqual(1, report["slides"])
        self.assertEqual({"add": 6, "set": 3}, report["commandTypes"])
        self.assertEqual({"connector": 2, "picture": 1, "shape": 2, "slide": 1}, report["addTypes"])
        self.assertEqual(
            {"slideWidth": "320px", "slideHeight": "180px"},
            report["presentationSize"],
        )
        self.assertTrue(report["officecliSchemaAuthority"])

    def test_single_command_plan_assigns_missing_drawing_ids(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            commands = _commands(Path(tmp))
            for command in commands:
                if command.get("type") in {"shape", "picture", "connector"}:
                    command["props"].pop("id", None)

            prepared, report = prepare_command_plan(commands)

        drawing_ids = [
            command["props"]["id"]
            for command in prepared
            if command.get("type") in {"shape", "picture", "connector"}
        ]
        self.assertEqual([2, 3, 4, 5, 6], drawing_ids)
        self.assertEqual("single-command-plan", report["mode"])
        self.assertEqual(5, len(report["autoAssignedDrawingIds"]))
        self.assertFalse(report["semanticIntermediateRepresentation"])

    def test_build_cli_defaults_workspace_beside_output(self) -> None:
        args = _parser().parse_args(
            [
                "build",
                "--commands",
                "officecli-commands.json",
                "--source-renders",
                "source",
                "--out",
                "editable.pptx",
            ]
        )

        self.assertIsNone(args.workspace)
        self.assertEqual(
            Path("editable.pptx").resolve().parent
            / ".editable.pptx.reconstruction",
            default_build_workspace(args.out),
        )

    def test_fragment_assembler_orders_native_arrays_and_assigns_ids(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            commands = _commands(root)
            for command in commands:
                if command.get("type") in {"shape", "picture", "connector"}:
                    command["props"].pop("id", None)
            fragments = root / "fragments"
            fragments.mkdir()
            (fragments / "00-presentation.json").write_text(
                json.dumps(commands[:1]),
                encoding="utf-8",
            )
            (fragments / "slide-01.json").write_text(
                json.dumps(commands[1:]),
                encoding="utf-8",
            )

            assembled, report = assemble_command_fragments(fragments)

        self.assertEqual(9, len(assembled))
        self.assertEqual("set", assembled[0]["command"])
        self.assertEqual("slide-01", assembled[1]["props"]["name"])
        drawing_ids = [
            command["props"]["id"]
            for command in assembled
            if command.get("type") in {"shape", "picture", "connector"}
        ]
        self.assertEqual([2, 3, 4, 5, 6], drawing_ids)
        self.assertEqual(5, len(report["autoAssignedDrawingIds"]))
        self.assertTrue(report["nativeOfficeCLIArray"])
        self.assertFalse(report["semanticIntermediateRepresentation"])

    def test_fragment_assembler_rejects_gaps_and_cross_slide_references(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "00-presentation.json").write_text(
                json.dumps(
                    [
                        {
                            "command": "set",
                            "path": "/",
                            "props": {"slideWidth": "320px", "slideHeight": "180px"},
                        }
                    ]
                ),
                encoding="utf-8",
            )
            (root / "slide-02.json").write_text(
                json.dumps(
                    [
                        {
                            "command": "add",
                            "parent": "/",
                            "type": "slide",
                            "props": {"name": "slide-02"},
                        }
                    ]
                ),
                encoding="utf-8",
            )
            with self.assertRaises(ReconstructionError) as gap:
                assemble_command_fragments(root)
            self.assertIn("contiguous from slide-01.json", str(gap.exception))

            (root / "slide-02.json").unlink()
            (root / "slide-01.json").write_text(
                json.dumps(
                    [
                        {
                            "command": "add",
                            "parent": "/",
                            "type": "slide",
                            "props": {"name": "slide-01"},
                        },
                        {
                            "command": "set",
                            "path": "/slide[2]/shape[@name=title]",
                            "props": {"text": "wrong slide"},
                        },
                    ]
                ),
                encoding="utf-8",
            )
            with self.assertRaises(ReconstructionError) as scope:
                assemble_command_fragments(root)
        self.assertIn("crosses slide scope", str(scope.exception))

    def test_raw_set_requires_explicit_opt_in(self) -> None:
        commands = [
            {
                "command": "set",
                "path": "/",
                "props": {"slideWidth": "320px", "slideHeight": "180px"},
            },
            {
                "command": "add",
                "parent": "/",
                "type": "slide",
                "props": {"name": "slide-01"},
            },
            {
                "command": "raw-set",
                "part": "ppt/slides/slide1.xml",
                "xpath": "/p:sld",
                "xml": "<p:sld/>",
            },
        ]
        with self.assertRaises(ReconstructionError) as raised:
            validate_command_plan(commands)
        self.assertIn("pass --allow-raw-set", str(raised.exception))
        self.assertTrue(
            validate_command_plan(commands, allow_raw_set=True)["rawSetAllowed"]
        )

    def test_duplicate_drawing_ids_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            commands = _commands(Path(tmp))
            commands[3]["props"]["id"] = 2
            with self.assertRaises(ReconstructionError) as raised:
                validate_command_plan(commands)
        self.assertIn("reuse drawing props.id 2", str(raised.exception))

    def test_installed_schema_rejects_unknown_props(self) -> None:
        schema = {
            "properties": {
                "title": {"set": True, "aliases": ["name"]},
                "readonly": {"set": False},
            }
        }
        with mock.patch("reconstruct._run_json", return_value=schema):
            report = validate_against_officecli_schema(
                [{"command": "set", "path": "/", "props": {"name": "deck"}}],
                {"path": "/managed/officecli", "version": "1.0.140"},
            )
            with self.assertRaises(ReconstructionError) as raised:
                validate_against_officecli_schema(
                    [{"command": "set", "path": "/", "props": {"invented": True}}],
                    {"path": "/managed/officecli", "version": "1.0.140"},
                )
        self.assertEqual(1, report["checkedProperties"])
        self.assertIn("unsupported pptx set presentation property", str(raised.exception))

    def test_runtime_probe_allows_schema_omitted_shape_wrap(self) -> None:
        schema = {
            "properties": {
                "text": {"add": True},
            }
        }
        commands = [
            {
                "command": "add",
                "parent": "/slide[1]",
                "type": "shape",
                "props": {"text": "single line", "wrap": False},
            }
        ]
        with (
            mock.patch("reconstruct._run_json", return_value=schema),
            mock.patch(
                "reconstruct._probe_shape_wrap_add",
                return_value=True,
            ) as probe,
        ):
            report = validate_against_officecli_schema(
                commands,
                {"path": "/managed/officecli", "version": "1.0.142"},
            )
        probe.assert_called_once_with(
            {"path": "/managed/officecli", "version": "1.0.142"}
        )
        self.assertEqual(
            [{"verb": "add", "element": "shape", "property": "wrap"}],
            report["runtimeProbedProperties"],
        )

    def test_unverified_schema_omitted_shape_wrap_is_rejected(self) -> None:
        schema = {
            "properties": {
                "text": {"add": True},
            }
        }
        commands = [
            {
                "command": "add",
                "parent": "/slide[1]",
                "type": "shape",
                "props": {"text": "single line", "wrap": False},
            }
        ]
        with (
            mock.patch("reconstruct._run_json", return_value=schema),
            mock.patch("reconstruct._probe_shape_wrap_add", return_value=False),
            self.assertRaises(ReconstructionError) as raised,
        ):
            validate_against_officecli_schema(
                commands,
                {"path": "/managed/officecli", "version": "1.0.141"},
            )
        self.assertIn("unsupported pptx add shape property: wrap", str(raised.exception))

    def test_declared_shape_wrap_does_not_run_runtime_probe(self) -> None:
        schema = {
            "properties": {
                "text": {"add": True},
                "wrap": {"add": True},
            }
        }
        commands = [
            {
                "command": "add",
                "parent": "/slide[1]",
                "type": "shape",
                "props": {"text": "single line", "wrap": False},
            }
        ]
        with (
            mock.patch("reconstruct._run_json", return_value=schema),
            mock.patch("reconstruct._probe_shape_wrap_add") as probe,
        ):
            report = validate_against_officecli_schema(
                commands,
                {"path": "/managed/officecli", "version": "1.0.143"},
            )
        probe.assert_not_called()
        self.assertEqual([], report["runtimeProbedProperties"])

    def test_command_envelope_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "commands.json"
            path.write_text('{"commands": []}', encoding="utf-8")
            with self.assertRaises(ReconstructionError) as raised:
                load_command_plan(path)
        self.assertIn("native OfficeCLI command array", str(raised.exception))

    def test_read_command_is_rejected_from_mutating_batch(self) -> None:
        with self.assertRaises(ReconstructionError) as raised:
            validate_command_plan([{"command": "view"}])
        self.assertIn("unsupported reconstruction verb 'view'", str(raised.exception))

    def test_slide_and_core_elements_require_stable_names(self) -> None:
        commands = [
            {"command": "add", "parent": "/", "type": "slide", "props": {"name": "slide-01"}},
            {"command": "add", "parent": "/slide[1]", "type": "shape", "props": {}},
        ]
        with self.assertRaises(ReconstructionError) as raised:
            validate_command_plan(commands)
        self.assertIn("shape requires a stable props.name", str(raised.exception))

    def test_local_assets_must_be_absolute_and_exist(self) -> None:
        commands = [
            {"command": "add", "parent": "/", "type": "slide", "props": {"name": "slide-01"}},
            {
                "command": "add",
                "parent": "/slide[1]",
                "type": "picture",
                "props": {"id": 2, "name": "hero", "src": "relative.png"},
            },
        ]
        with self.assertRaises(ReconstructionError) as raised:
            validate_command_plan(commands)
        self.assertIn("absolute asset path", str(raised.exception))

    def test_stable_names_must_be_unique_within_parent(self) -> None:
        commands = [
            {"command": "add", "parent": "/", "type": "slide", "props": {"name": "slide-01"}},
            {
                "command": "add",
                "parent": "/slide[1]",
                "type": "shape",
                "props": {"id": 2, "name": "title"},
            },
            {
                "command": "add",
                "parent": "/slide[1]",
                "type": "picture",
                "props": {
                    "id": 3,
                    "name": "title",
                    "src": "data:image/png;base64,AA==",
                },
            },
        ]
        with self.assertRaises(ReconstructionError) as raised:
            validate_command_plan(commands)
        self.assertIn("reuse stable name 'title'", str(raised.exception))

    def test_command_plan_must_add_a_slide(self) -> None:
        with self.assertRaises(ReconstructionError) as raised:
            validate_command_plan([{"command": "set", "path": "/", "props": {"title": "x"}}])
        self.assertIn("must add at least one slide", str(raised.exception))

    def test_command_plan_requires_explicit_presentation_size(self) -> None:
        commands = [
            {"command": "add", "parent": "/", "type": "slide", "props": {"name": "slide-01"}}
        ]
        with self.assertRaises(ReconstructionError) as raised:
            validate_command_plan(commands)
        self.assertIn("slideWidth and slideHeight", str(raised.exception))

    def test_console_report_keeps_batch_details_on_disk_only(self) -> None:
        compact = _compact_build_result(
            {
                "ok": True,
                "commandPlanSha256": "abc",
                "batch": {
                    "data": {
                        "summary": {"total": 2, "succeeded": 2},
                        "results": [{"index": 0}, {"index": 1}],
                    }
                },
                "audit": {"slides": 1, "flattened_slides": 0},
                "validation": {"data": {"count": 0, "errors": []}},
            }
        )
        self.assertEqual({"total": 2, "succeeded": 2}, compact["batchSummary"])
        self.assertEqual("abc", compact["commandPlanSha256"])
        self.assertNotIn("batch", compact)


class AuditTests(unittest.TestCase):
    def test_audit_routes_flattened_native_and_mixed_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            flattened = root / "flattened.pptx"
            flattened_fill = root / "flattened-fill.pptx"
            native = root / "native.pptx"
            mixed = root / "mixed.pptx"
            _write_pptx(flattened, [_slide("<p:pic/>")])
            _write_pptx(
                flattened_fill,
                [_slide("<p:sp><p:spPr><a:blipFill/></p:spPr></p:sp>")],
            )
            _write_pptx(
                native,
                [_slide("<p:sp><p:txBody><a:p><a:r><a:t>Hello</a:t></a:r></a:p></p:txBody></p:sp>")],
            )
            _write_pptx(mixed, [_slide("<p:pic/><p:sp/>")])

            flat_audit = audit_pptx(flattened)
            fill_audit = audit_pptx(flattened_fill)
            native_audit = audit_pptx(native)
            mixed_audit = audit_pptx(mixed)

        self.assertEqual("reconstruct", route_input(flat_audit))
        self.assertEqual("reconstruct", route_input(fill_audit))
        self.assertEqual("edit-existing", route_input(native_audit))
        self.assertEqual("edit-existing", route_input(mixed_audit))
        with self.assertRaises(PptxAuditError):
            assert_editable_output(flat_audit, 1)

    def test_transparent_placeholder_picture_does_not_hide_flattened_slide(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "flattened-with-placeholder.pptx"
            _write_pptx(
                source,
                [_slide(_picture("rId1") + _picture("rId2"))],
                slide_relationships={
                    1: _relationships(["background.png", "placeholder.png"])
                },
                media={
                    "background.png": _rgba_png(255),
                    "placeholder.png": _rgba_png(0),
                },
            )

            audit = audit_pptx(source)

        detail = audit.slide_details[0]
        self.assertEqual(2, detail.pictures)
        self.assertEqual(1, detail.visible_pictures)
        self.assertEqual(1, detail.transparent_pictures)
        self.assertEqual(("../media/placeholder.png",), detail.transparent_picture_targets)
        self.assertTrue(detail.full_slide_picture_only)
        self.assertEqual("reconstruct", route_input(audit))


class VisualComparisonTests(unittest.TestCase):
    def test_identical_png_renders_pass_with_zero_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.png"
            output = root / "output.png"
            payload = _solid_rgb_png(2, 2, 40, 80, 120)
            source.write_bytes(payload)
            output.write_bytes(payload)

            width, height, normalized_mae = compare_png_renders(source, output)

        self.assertEqual((2, 2), (width, height))
        self.assertEqual(0, normalized_mae)

    def test_black_and_white_renders_fail_the_deck_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            output = root / "output"
            source.mkdir()
            output.mkdir()
            (source / "slide-01.png").write_bytes(
                _solid_rgb_png(2, 2, 0, 0, 0)
            )
            (output / "slide-1.png").write_bytes(
                _solid_rgb_png(2, 2, 255, 255, 255)
            )

            report = compare_render_directories(source, output, 1)

        self.assertEqual(1, report.average_normalized_mae)
        self.assertFalse(report.passed)
        self.assertFalse(report.slide_details[0].passed)

    def test_missing_source_slide_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            output = root / "output"
            source.mkdir()
            output.mkdir()
            (source / "slide-01.png").write_bytes(
                _solid_rgb_png(1, 1, 0, 0, 0)
            )
            (output / "slide-01.png").write_bytes(
                _solid_rgb_png(1, 1, 0, 0, 0)
            )
            with self.assertRaises(VisualComparisonError) as raised:
                compare_render_directories(source, output, 2)

        self.assertIn("must cover slides 1-2", str(raised.exception))


@unittest.skipUnless(os.environ.get("OFFICECLI_BIN"), "OFFICECLI_BIN is required for integration")
class OfficeCLIIntegrationTests(unittest.TestCase):
    def test_build_validate_render_and_stable_edit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            commands = _commands(root)
            for command in commands:
                if command.get("type") in {"shape", "picture", "connector"}:
                    command["props"].pop("id", None)
            source_renders = _render_reference(
                commands,
                root,
                width=960,
                height=540,
            )
            output = root / "editable.pptx"
            report = build_commands(
                commands,
                source_render_directory=source_renders,
                output_path=output,
                officecli_bin=os.environ["OFFICECLI_BIN"],
                screenshot_width=960,
                screenshot_height=540,
            )
            self.assertTrue(output.is_file())
            self.assertEqual(0, report["validation"]["data"]["count"])
            self.assertEqual(0, report["audit"]["flattened_slides"])
            self.assertEqual(1, len(report["preview"]["paths"]))
            self.assertTrue(report["visualComparison"]["passed"])
            self.assertEqual(
                0,
                report["visualComparison"]["average_normalized_mae"],
            )
            self.assertEqual(5, len(report["assembly"]["autoAssignedDrawingIds"]))
            prepared_commands = load_command_plan(report["commandsPath"])
            self.assertEqual(9, len(prepared_commands))
            self.assertTrue(
                all(
                    "id" in command["props"]
                    for command in prepared_commands
                    if command.get("type") in {"shape", "picture", "connector"}
                )
            )
            self.assertEqual(
                default_build_workspace(output),
                Path(report["report"]).parent,
            )
            with zipfile.ZipFile(output) as archive:
                slide_xml = ET.fromstring(archive.read("ppt/slides/slide1.xml"))
            src_rects = [
                node.attrib
                for node in slide_xml.iter(f"{{{A_NS}}}srcRect")
                if node.attrib
            ]
            self.assertIn(
                {"l": "10000", "t": "5000", "r": "10000", "b": "5000"},
                src_rects,
            )
            subprocess.run(
                [
                    os.environ["OFFICECLI_BIN"],
                    "set",
                    str(output),
                    "/slide[1]/shape[@name=title]",
                    "--find",
                    "账单",
                    "--replace",
                    "代价",
                    "--json",
                ],
                check=True,
                capture_output=True,
                text=True,
                env={
                    **os.environ,
                    "OFFICECLI_SKIP_UPDATE": "1",
                    "OFFICECLI_RESIDENT_FLUSH": "each",
                },
            )
            text = subprocess.run(
                [os.environ["OFFICECLI_BIN"], "view", str(output), "text"],
                check=True,
                capture_output=True,
                text=True,
                env={
                    **os.environ,
                    "OFFICECLI_SKIP_UPDATE": "1",
                    "OFFICECLI_RESIDENT_FLUSH": "each",
                },
            ).stdout
            self.assertIn("战争代价", text)

    def test_failed_atomic_batch_does_not_replace_requested_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            commands = _commands(root)
            commands.append(
                {
                    "command": "set",
                    "path": "/slide[99]/shape[1]",
                    "props": {"text": "must roll back"},
                }
            )
            output = root / "existing.pptx"
            output.write_bytes(b"existing-output-must-survive")
            source_renders = root / "source-renders"
            source_renders.mkdir()

            with self.assertRaises(ReconstructionError) as raised:
                build_commands(
                    commands,
                    source_render_directory=source_renders,
                    output_path=output,
                    workspace=root / "runtime",
                    officecli_bin=os.environ["OFFICECLI_BIN"],
                    screenshot_width=960,
                    screenshot_height=540,
                )

            self.assertIn('"atomicRolledBack":true', str(raised.exception))
            self.assertEqual(b"existing-output-must-survive", output.read_bytes())

    def test_failed_visual_gate_does_not_replace_requested_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            commands = _commands(root)
            output = root / "existing.pptx"
            output.write_bytes(b"existing-output-must-survive")
            source_renders = root / "source-renders"
            source_renders.mkdir()
            (source_renders / "slide-01.png").write_bytes(
                _solid_rgb_png(960, 540, 0, 0, 0)
            )

            with self.assertRaises(ReconstructionError) as raised:
                build_commands(
                    commands,
                    source_render_directory=source_renders,
                    output_path=output,
                    workspace=root / "runtime",
                    officecli_bin=os.environ["OFFICECLI_BIN"],
                    screenshot_width=960,
                    screenshot_height=540,
                )

            visual_report = json.loads(
                (root / "runtime" / "visual-comparison.json").read_text(
                    encoding="utf-8"
                )
            )
            preserved_output = output.read_bytes()

        self.assertIn("Visual fidelity gate failed", str(raised.exception))
        self.assertFalse(visual_report["passed"])
        self.assertEqual(b"existing-output-must-survive", preserved_output)


if __name__ == "__main__":
    unittest.main()
