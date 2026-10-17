#!/usr/bin/env python3
"""Read-only OOXML package audit for editable reconstruction routing and output checks."""

from __future__ import annotations

import posixpath
import re
import struct
import xml.etree.ElementTree as ET
import zipfile
import zlib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


PML = "http://schemas.openxmlformats.org/presentationml/2006/main"
RML = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL = "http://schemas.openxmlformats.org/package/2006/relationships"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"


@dataclass(frozen=True)
class SlideAudit:
    slide: int
    shapes: int
    pictures: int
    visible_pictures: int
    transparent_pictures: int
    image_fill_shapes: int
    connectors: int
    groups: int
    tables: int
    charts: int
    text_runs: int
    full_slide_picture_only: bool
    picture_targets: tuple[str, ...]
    transparent_picture_targets: tuple[str, ...]


@dataclass(frozen=True)
class DeckAudit:
    path: str
    slides: int
    flattened_slides: int
    native_slides: int
    mixed_slides: int
    media_files: int
    slide_details: tuple[SlideAudit, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class PptxAuditError(ValueError):
    """Raised when a path is not a readable PPTX OOXML package."""


def _slide_number(name: str) -> int:
    match = re.search(r"slide(\d+)\.xml$", name)
    if not match:
        raise PptxAuditError(f"Not a slide XML path: {name}")
    return int(match.group(1))


def _relationship_targets(zf: zipfile.ZipFile, slide_number: int) -> dict[str, str]:
    rel_path = f"ppt/slides/_rels/slide{slide_number}.xml.rels"
    if rel_path not in zf.namelist():
        return {}
    root = ET.fromstring(zf.read(rel_path))
    return {
        relationship.attrib["Id"]: relationship.attrib.get("Target", "")
        for relationship in root.findall(f"{{{PKG_REL}}}Relationship")
    }


def _resolve_slide_target(target: str) -> str | None:
    if not target or "://" in target:
        return None
    return posixpath.normpath(posixpath.join("ppt/slides", target))


def _paeth(left: int, above: int, upper_left: int) -> int:
    estimate = left + above - upper_left
    left_distance = abs(estimate - left)
    above_distance = abs(estimate - above)
    upper_left_distance = abs(estimate - upper_left)
    if left_distance <= above_distance and left_distance <= upper_left_distance:
        return left
    if above_distance <= upper_left_distance:
        return above
    return upper_left


def _fully_transparent_png(payload: bytes) -> bool:
    """Return true only for supported, provably all-alpha-zero PNG images."""
    if not payload.startswith(b"\x89PNG\r\n\x1a\n"):
        return False
    offset = 8
    width = height = bit_depth = color_type = interlace = None
    compressed = bytearray()
    while offset + 12 <= len(payload):
        length = struct.unpack(">I", payload[offset : offset + 4])[0]
        chunk_type = payload[offset + 4 : offset + 8]
        chunk_start = offset + 8
        chunk_end = chunk_start + length
        if chunk_end + 4 > len(payload):
            return False
        chunk = payload[chunk_start:chunk_end]
        if chunk_type == b"IHDR":
            if len(chunk) != 13:
                return False
            width, height, bit_depth, color_type, _, _, interlace = struct.unpack(
                ">IIBBBBB", chunk
            )
        elif chunk_type == b"IDAT":
            compressed.extend(chunk)
        elif chunk_type == b"IEND":
            break
        offset = chunk_end + 4
    if (
        not width
        or not height
        or bit_depth != 8
        or color_type not in {4, 6}
        or interlace != 0
        or not compressed
    ):
        return False
    bytes_per_pixel = 2 if color_type == 4 else 4
    stride = width * bytes_per_pixel
    try:
        raw = zlib.decompress(bytes(compressed))
    except zlib.error:
        return False
    if len(raw) != height * (stride + 1):
        return False

    previous = bytearray(stride)
    alpha_offset = bytes_per_pixel - 1
    cursor = 0
    for _ in range(height):
        filter_type = raw[cursor]
        cursor += 1
        encoded = raw[cursor : cursor + stride]
        cursor += stride
        decoded = bytearray(stride)
        for index, value in enumerate(encoded):
            left = decoded[index - bytes_per_pixel] if index >= bytes_per_pixel else 0
            above = previous[index]
            upper_left = previous[index - bytes_per_pixel] if index >= bytes_per_pixel else 0
            if filter_type == 0:
                predictor = 0
            elif filter_type == 1:
                predictor = left
            elif filter_type == 2:
                predictor = above
            elif filter_type == 3:
                predictor = (left + above) // 2
            elif filter_type == 4:
                predictor = _paeth(left, above, upper_left)
            else:
                return False
            decoded[index] = (value + predictor) & 0xFF
        if any(decoded[index] for index in range(alpha_offset, stride, bytes_per_pixel)):
            return False
        previous = decoded
    return True


def _audit_slide(
    zf: zipfile.ZipFile,
    slide_name: str,
    package_names: set[str],
    transparency_cache: dict[str, bool],
) -> SlideAudit:
    number = _slide_number(slide_name)
    root = ET.fromstring(zf.read(slide_name))
    relationships = _relationship_targets(zf, number)
    picture_targets: list[str] = []
    transparent_picture_targets: list[str] = []
    for picture in root.findall(f".//{{{PML}}}pic"):
        blip = picture.find(f".//{{{A_NS}}}blip")
        if blip is None:
            continue
        relationship_id = blip.attrib.get(f"{{{RML}}}embed")
        if relationship_id and relationship_id in relationships:
            target = relationships[relationship_id]
            picture_targets.append(target)
            resolved = _resolve_slide_target(target)
            if resolved in package_names and resolved not in transparency_cache:
                transparency_cache[resolved] = _fully_transparent_png(zf.read(resolved))
            if resolved is not None and transparency_cache.get(resolved, False):
                transparent_picture_targets.append(target)

    shape_nodes = root.findall(f".//{{{PML}}}sp")
    shapes = len(shape_nodes)
    pictures = len(root.findall(f".//{{{PML}}}pic"))
    transparent_pictures = len(transparent_picture_targets)
    visible_pictures = pictures - transparent_pictures
    image_fill_shapes = sum(
        shape.find(f"./{{{PML}}}spPr/{{{A_NS}}}blipFill") is not None
        for shape in shape_nodes
    )
    connectors = len(root.findall(f".//{{{PML}}}cxnSp"))
    groups = len(root.findall(f".//{{{PML}}}grpSp"))
    tables = len(root.findall(f".//{{{A_NS}}}tbl"))
    text_runs = len(root.findall(f".//{{{A_NS}}}t"))
    charts = sum(1 for target in relationships.values() if "../charts/" in target)
    flattened = (
        visible_pictures + image_fill_shapes == 1
        and shapes == image_fill_shapes
        and connectors == 0
        and groups == 0
        and tables == 0
        and charts == 0
        and text_runs == 0
    )
    return SlideAudit(
        slide=number,
        shapes=shapes,
        pictures=pictures,
        visible_pictures=visible_pictures,
        transparent_pictures=transparent_pictures,
        image_fill_shapes=image_fill_shapes,
        connectors=connectors,
        groups=groups,
        tables=tables,
        charts=charts,
        text_runs=text_runs,
        full_slide_picture_only=flattened,
        picture_targets=tuple(picture_targets),
        transparent_picture_targets=tuple(transparent_picture_targets),
    )


def audit_pptx(path: str | Path) -> DeckAudit:
    source = Path(path).expanduser().resolve()
    if not source.is_file():
        raise PptxAuditError(f"PPTX does not exist: {source}")
    try:
        with zipfile.ZipFile(source) as zf:
            names = set(zf.namelist())
            if "[Content_Types].xml" not in names or "ppt/presentation.xml" not in names:
                raise PptxAuditError(f"Not a PowerPoint OOXML package: {source}")
            slide_names = sorted(
                (name for name in names if re.fullmatch(r"ppt/slides/slide\d+\.xml", name)),
                key=_slide_number,
            )
            transparency_cache: dict[str, bool] = {}
            details = tuple(
                _audit_slide(zf, name, names, transparency_cache)
                for name in slide_names
            )
            media_files = sum(
                name.startswith("ppt/media/") and not name.endswith("/") for name in names
            )
    except zipfile.BadZipFile as exc:
        raise PptxAuditError(f"Unreadable PPTX ZIP package: {source}") from exc

    flattened_count = sum(item.full_slide_picture_only for item in details)
    native_count = sum(
        not item.full_slide_picture_only
        and item.visible_pictures == 0
        and item.image_fill_shapes == 0
        for item in details
    )
    mixed_count = len(details) - flattened_count - native_count
    return DeckAudit(
        path=str(source),
        slides=len(details),
        flattened_slides=flattened_count,
        native_slides=native_count,
        mixed_slides=mixed_count,
        media_files=media_files,
        slide_details=details,
    )


def route_input(audit: DeckAudit) -> str:
    if audit.slides and audit.flattened_slides == audit.slides:
        return "reconstruct"
    if audit.native_slides or audit.mixed_slides:
        return "edit-existing"
    return "unsupported"


def assert_editable_output(audit: DeckAudit, expected_slides: int) -> None:
    errors: list[str] = []
    if audit.slides != expected_slides:
        errors.append(f"expected {expected_slides} slides, found {audit.slides}")
    flattened = [str(item.slide) for item in audit.slide_details if item.full_slide_picture_only]
    if flattened:
        errors.append("full-slide-picture-only output slides: " + ", ".join(flattened))
    if errors:
        raise PptxAuditError("Editable reconstruction audit failed: " + "; ".join(errors))
