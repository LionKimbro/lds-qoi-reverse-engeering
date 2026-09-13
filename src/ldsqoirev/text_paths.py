"""Decode the evidence-backed LDS type-0x0B text-path payload.

The decoder is intentionally read-only and scoped to the controlled text
fixtures. It exports SVG for visual validation; it does not yet claim a general
LDS text renderer or perform mutation.
"""

from __future__ import annotations

from dataclasses import dataclass
from html import escape
from pathlib import Path
import struct


RECORD_MARKER = b"\xad\x9cN\x1e"
PATH_RECORD_PREFIX = RECORD_MARKER + b"\x00\x00\x00\x00\x0b\x00\x00\x00"
PATH_HEADER_SIZE = 30
PATH_COMMAND_SIZE = 12


@dataclass(frozen=True)
class PathCommand:
    x: float
    y: float
    code: int

    @property
    def base_code(self) -> int:
        return self.code & 0x07

    @property
    def closes_subpath(self) -> bool:
        return bool(self.code & 0x80)


@dataclass(frozen=True)
class TextPath:
    anchor_x: float
    anchor_y: float
    commands: tuple[PathCommand, ...]


def find_text_path(cdoc: bytes) -> TextPath:
    """Decode the sole type-0x0B path record in a controlled text CDOC."""
    offset = cdoc.find(PATH_RECORD_PREFIX)
    if offset < 0:
        raise ValueError("no type-0x0B text-path record found")
    payload_size = struct.unpack_from("<I", cdoc, offset + 12)[0]
    payload_start = offset + 32
    payload_end = payload_start + payload_size
    if payload_end > len(cdoc) or payload_size < PATH_HEADER_SIZE:
        raise ValueError("truncated text-path record")

    payload = cdoc[payload_start:payload_end]
    command_count = struct.unpack_from("<I", payload)[0]
    expected_size = PATH_HEADER_SIZE + command_count * PATH_COMMAND_SIZE
    if expected_size != payload_size:
        raise ValueError(
            f"unexpected path payload size: {payload_size}; expected {expected_size} from command count"
        )
    anchor_x, anchor_y = struct.unpack_from("<ff", payload, 4)
    commands = tuple(
        PathCommand(*struct.unpack_from("<ffI", payload, PATH_HEADER_SIZE + index * PATH_COMMAND_SIZE))
        for index in range(command_count)
    )
    return TextPath(anchor_x, anchor_y, commands)


def svg_path_data(text_path: TextPath) -> str:
    """Convert the observed path-command encoding into SVG path data.

    Observed code bases: 0 = move, 1 = line, and 2/3/3 = cubic Bézier control
    point, control point, endpoint. Other low-bit values are rejected rather
    than guessed.
    """
    output: list[str] = []
    pending_cubic: list[PathCommand] = []
    for command in text_path.commands:
        if command.base_code == 0:
            if pending_cubic:
                raise ValueError("incomplete Bézier sequence before move")
            output.append(f"M {command.x:.8g} {command.y:.8g}")
        elif command.base_code == 1:
            if pending_cubic:
                raise ValueError("incomplete Bézier sequence before line")
            output.append(f"L {command.x:.8g} {command.y:.8g}")
        elif command.base_code in (2, 3):
            pending_cubic.append(command)
            if len(pending_cubic) == 3:
                first, second, endpoint = pending_cubic
                output.append(
                    f"C {first.x:.8g} {first.y:.8g} {second.x:.8g} {second.y:.8g} {endpoint.x:.8g} {endpoint.y:.8g}"
                )
                pending_cubic.clear()
        else:
            raise ValueError(f"unknown path command base code {command.base_code}")
        if command.closes_subpath:
            if pending_cubic:
                raise ValueError("incomplete Bézier sequence before close")
            output.append("Z")
    if pending_cubic:
        raise ValueError("incomplete final Bézier sequence")
    return " ".join(output)


def svg_document(text_path: TextPath, *, fill: str = "#bca886", padding: float = 0.1) -> str:
    """Create a standalone SVG for visual path validation."""
    if not text_path.commands:
        raise ValueError("empty text path")
    min_x = min(command.x for command in text_path.commands) - padding
    max_x = max(command.x for command in text_path.commands) + padding
    min_y = min(command.y for command in text_path.commands) - padding
    max_y = max(command.y for command in text_path.commands) + padding
    width = max_x - min_x
    height = max_y - min_y
    pixel_width = 600
    pixel_height = max(1, round(pixel_width * height / width))
    path = svg_path_data(text_path)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{pixel_width}" height="{pixel_height}" '
        f'viewBox="{min_x:.8g} {min_y:.8g} {width:.8g} {height:.8g}">'
        f'<path fill="{escape(fill, quote=True)}" fill-rule="evenodd" d="{path}"/>'
        "</svg>"
    )


def write_svg_from_cdoc(cdoc: bytes, destination: Path, *, fill: str = "#bca886") -> TextPath:
    """Write only a derived SVG artifact and return its decoded source path."""
    text_path = find_text_path(cdoc)
    destination.write_text(svg_document(text_path, fill=fill), encoding="utf-8", newline="\n")
    return text_path
