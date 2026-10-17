#!/usr/bin/env python3
"""Dependency-free PNG comparison for reconstruction visual regression gates."""

from __future__ import annotations

import re
import struct
import zlib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
SLIDE_RENDER_PATTERN = re.compile(r"slide-(\d+)\.png$")
DEFAULT_AVERAGE_MAE_LIMIT = 0.08
DEFAULT_SLIDE_MAE_LIMIT = 0.15


class VisualComparisonError(ValueError):
    """Raised when source and output renders cannot be compared safely."""


@dataclass(frozen=True)
class SlideVisualComparison:
    slide: int
    source: str
    output: str
    width: int
    height: int
    normalized_mae: float
    passed: bool


@dataclass(frozen=True)
class DeckVisualComparison:
    source_directory: str
    output_directory: str
    slides: int
    average_normalized_mae: float
    maximum_normalized_mae: float
    average_limit: float
    slide_limit: float
    passed: bool
    slide_details: tuple[SlideVisualComparison, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


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


def _png_chunks(payload: bytes) -> list[tuple[bytes, bytes]]:
    if not payload.startswith(PNG_SIGNATURE):
        raise VisualComparisonError("Visual comparison requires PNG slide renders.")
    chunks: list[tuple[bytes, bytes]] = []
    offset = len(PNG_SIGNATURE)
    while offset + 12 <= len(payload):
        length = struct.unpack(">I", payload[offset : offset + 4])[0]
        chunk_type = payload[offset + 4 : offset + 8]
        chunk_start = offset + 8
        chunk_end = chunk_start + length
        if chunk_end + 4 > len(payload):
            raise VisualComparisonError("PNG chunk exceeds the render payload.")
        chunks.append((chunk_type, payload[chunk_start:chunk_end]))
        offset = chunk_end + 4
        if chunk_type == b"IEND":
            break
    return chunks


def _decode_png_rgb(path: str | Path) -> tuple[int, int, bytes]:
    source = Path(path).expanduser().resolve()
    chunks = _png_chunks(source.read_bytes())
    header = next((payload for kind, payload in chunks if kind == b"IHDR"), None)
    if header is None or len(header) != 13:
        raise VisualComparisonError(f"PNG render has no valid IHDR: {source}")
    width, height, bit_depth, color_type, compression, filtering, interlace = struct.unpack(
        ">IIBBBBB", header
    )
    if (
        not width
        or not height
        or bit_depth != 8
        or color_type not in {0, 2, 4, 6}
        or compression != 0
        or filtering != 0
        or interlace != 0
    ):
        raise VisualComparisonError(
            f"Unsupported PNG render format for {source}: "
            f"bitDepth={bit_depth}, colorType={color_type}, interlace={interlace}."
        )
    channels = {0: 1, 2: 3, 4: 2, 6: 4}[color_type]
    stride = width * channels
    compressed = b"".join(payload for kind, payload in chunks if kind == b"IDAT")
    if not compressed:
        raise VisualComparisonError(f"PNG render has no image data: {source}")
    try:
        raw = zlib.decompress(compressed)
    except zlib.error as exc:
        raise VisualComparisonError(f"PNG render cannot be decompressed: {source}") from exc
    if len(raw) != height * (stride + 1):
        raise VisualComparisonError(f"PNG render has unexpected row data: {source}")

    decoded_rows: list[bytearray] = []
    previous = bytearray(stride)
    cursor = 0
    for _ in range(height):
        filter_type = raw[cursor]
        cursor += 1
        encoded = raw[cursor : cursor + stride]
        cursor += stride
        decoded = bytearray(stride)
        for index, value in enumerate(encoded):
            left = decoded[index - channels] if index >= channels else 0
            above = previous[index]
            upper_left = previous[index - channels] if index >= channels else 0
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
                raise VisualComparisonError(
                    f"PNG render uses unsupported filter {filter_type}: {source}"
                )
            decoded[index] = (value + predictor) & 0xFF
        decoded_rows.append(decoded)
        previous = decoded

    rgb = bytearray(width * height * 3)
    target = 0
    for row in decoded_rows:
        for offset in range(0, stride, channels):
            if color_type == 0:
                red = green = blue = row[offset]
                alpha = 255
            elif color_type == 2:
                red, green, blue = row[offset : offset + 3]
                alpha = 255
            elif color_type == 4:
                red = green = blue = row[offset]
                alpha = row[offset + 1]
            else:
                red, green, blue, alpha = row[offset : offset + 4]
            if alpha != 255:
                inverse = 255 - alpha
                red = (red * alpha + 255 * inverse + 127) // 255
                green = (green * alpha + 255 * inverse + 127) // 255
                blue = (blue * alpha + 255 * inverse + 127) // 255
            rgb[target : target + 3] = bytes((red, green, blue))
            target += 3
    return width, height, bytes(rgb)


def compare_png_renders(
    source_path: str | Path,
    output_path: str | Path,
) -> tuple[int, int, float]:
    source_width, source_height, source_rgb = _decode_png_rgb(source_path)
    output_width, output_height, output_rgb = _decode_png_rgb(output_path)
    if (source_width, source_height) != (output_width, output_height):
        raise VisualComparisonError(
            "Source and output render dimensions differ: "
            f"{source_width}x{source_height} vs {output_width}x{output_height}."
        )
    absolute_error = sum(
        abs(source_value - output_value)
        for source_value, output_value in zip(source_rgb, output_rgb, strict=True)
    )
    normalized_mae = absolute_error / (len(source_rgb) * 255)
    return source_width, source_height, normalized_mae


def _index_slide_renders(directory: str | Path) -> dict[int, Path]:
    root = Path(directory).expanduser().resolve()
    if not root.is_dir():
        raise VisualComparisonError(f"Slide render directory does not exist: {root}")
    indexed: dict[int, Path] = {}
    for path in sorted(root.glob("slide-*.png")):
        match = SLIDE_RENDER_PATTERN.fullmatch(path.name)
        if not match:
            continue
        slide = int(match.group(1))
        if slide in indexed:
            raise VisualComparisonError(
                f"Duplicate source render for slide {slide}: "
                f"{indexed[slide].name}, {path.name}."
            )
        indexed[slide] = path
    return indexed


def compare_render_directories(
    source_directory: str | Path,
    output_directory: str | Path,
    expected_slides: int,
    *,
    average_limit: float = DEFAULT_AVERAGE_MAE_LIMIT,
    slide_limit: float = DEFAULT_SLIDE_MAE_LIMIT,
) -> DeckVisualComparison:
    if expected_slides < 1:
        raise VisualComparisonError("Visual comparison requires at least one slide.")
    if not 0 <= average_limit <= 1 or not 0 <= slide_limit <= 1:
        raise VisualComparisonError("Visual comparison limits must be between 0 and 1.")
    source_renders = _index_slide_renders(source_directory)
    output_renders = _index_slide_renders(output_directory)
    expected = set(range(1, expected_slides + 1))
    if set(source_renders) != expected:
        found = ", ".join(str(item) for item in sorted(source_renders)) or "none"
        raise VisualComparisonError(
            f"Source renders must cover slides 1-{expected_slides}; found {found}."
        )
    if set(output_renders) != expected:
        found = ", ".join(str(item) for item in sorted(output_renders)) or "none"
        raise VisualComparisonError(
            f"Output renders must cover slides 1-{expected_slides}; found {found}."
        )

    details: list[SlideVisualComparison] = []
    for slide in range(1, expected_slides + 1):
        width, height, normalized_mae = compare_png_renders(
            source_renders[slide],
            output_renders[slide],
        )
        details.append(
            SlideVisualComparison(
                slide=slide,
                source=str(source_renders[slide]),
                output=str(output_renders[slide]),
                width=width,
                height=height,
                normalized_mae=normalized_mae,
                passed=normalized_mae <= slide_limit,
            )
        )
    average = sum(item.normalized_mae for item in details) / len(details)
    maximum = max(item.normalized_mae for item in details)
    return DeckVisualComparison(
        source_directory=str(Path(source_directory).expanduser().resolve()),
        output_directory=str(Path(output_directory).expanduser().resolve()),
        slides=expected_slides,
        average_normalized_mae=average,
        maximum_normalized_mae=maximum,
        average_limit=average_limit,
        slide_limit=slide_limit,
        passed=average <= average_limit and all(item.passed for item in details),
        slide_details=tuple(details),
    )
