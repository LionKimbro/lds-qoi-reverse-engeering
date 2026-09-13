"""Normalize a controlled numbered-label palette to a shared Y coordinate.

This mutator is intentionally restricted to the supplied PAGE palette shape.
It changes only measured object-bound and path-anchor Y floats, writes a new
archive, and preserves the source PREVIEW (which LDS can regenerate on save).
"""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import struct
import zipfile


MARKER = b"\xad\x9cN\x1e"
OBJECT_Y_OFFSETS = (0x3C, 0x54, 0x5C, 0x64, 0x6C, 0x74)


def _marker_offsets(cdoc: bytes) -> list[int]:
    offsets: list[int] = []
    cursor = 0
    while True:
        offset = cdoc.find(MARKER, cursor)
        if offset < 0:
            return offsets
        offsets.append(offset)
        cursor = offset + 1


def _record_type(cdoc: bytes, offset: int) -> int | None:
    if cdoc[offset + 4 : offset + 8] != b"\0\0\0\0":
        return None
    return struct.unpack_from("<I", cdoc, offset + 8)[0]


def _label_objects(cdoc: bytes, prefix: str) -> list[tuple[int, int, str]]:
    """Return (type-100 offset, type-11 offset, number) for matching labels."""
    literal_pattern = re.compile(rb"\xef\xbb\xbf" + re.escape(prefix.encode("ascii")) + rb" ([0-9]+)\r\n")
    markers = _marker_offsets(cdoc)
    result: list[tuple[int, int, str]] = []
    for match in literal_pattern.finditer(cdoc):
        prior = [offset for offset in markers if offset < match.start()]
        if not prior or _record_type(cdoc, prior[-1]) != 14:
            raise ValueError(f"{prefix} literal is not preceded by a type-14 record")
        path_offset = next((offset for offset in reversed(prior[:-1]) if _record_type(cdoc, offset) == 11), None)
        object_offset = next((offset for offset in reversed(prior[:-1]) if _record_type(cdoc, offset) == 100), None)
        if path_offset is None or object_offset is None or object_offset > path_offset:
            raise ValueError(f"could not find the type-100/type-11 {prefix} object sequence")
        if path_offset + 44 > len(cdoc) or object_offset + 0x78 > len(cdoc):
            raise ValueError(f"truncated {prefix} object record")
        result.append((object_offset, path_offset, match.group(1).decode("ascii")))
    if not result:
        raise ValueError(f"no {prefix} text objects found")
    return result


def normalize_label_y(cdoc: bytes, prefix: str) -> tuple[bytes, float, list[str]]:
    """Move every matching label to the first matching label's Y."""
    result = bytearray(cdoc)
    labels = _label_objects(cdoc, prefix)
    first_object, _, _ = labels[0]
    target_y = struct.unpack_from("<f", cdoc, first_object + 0x3C)[0]
    changed: list[str] = []
    for object_offset, path_offset, label in labels:
        object_y = struct.unpack_from("<f", result, object_offset + 0x3C)[0]
        path_y = struct.unpack_from("<f", result, path_offset + 0x28)[0]
        if abs(object_y - path_y) > 0.0001:
            raise ValueError(f"{prefix} {label}: object/path Y anchors disagree")
        delta = target_y - object_y
        if abs(delta) < 0.000001:
            continue
        for relative_offset in OBJECT_Y_OFFSETS:
            value = struct.unpack_from("<f", result, object_offset + relative_offset)[0]
            struct.pack_into("<f", result, object_offset + relative_offset, value + delta)
        struct.pack_into("<f", result, path_offset + 0x28, target_y)
        changed.append(label)
    return bytes(result), target_y, changed


def write_normalized_palette(source: Path, output: Path, prefix: str = "PAGE") -> tuple[float, list[str]]:
    if output.exists():
        raise FileExistsError(f"refusing to overwrite existing output: {output}")
    with zipfile.ZipFile(source) as archive:
        cdoc = archive.read("CDOC")
        normalized, target_y, changed = normalize_label_y(cdoc, prefix)
        with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED) as destination:
            for info in archive.infolist():
                data = normalized if info.filename == "CDOC" else archive.read(info.filename)
                copied = zipfile.ZipInfo(info.filename, date_time=info.date_time)
                copied.compress_type = info.compress_type
                copied.comment = info.comment
                copied.extra = info.extra
                copied.internal_attr = info.internal_attr
                copied.external_attr = info.external_attr
                destination.writestr(copied, data)
    return target_y, changed


def main() -> None:
    parser = argparse.ArgumentParser(description="Normalize Y coordinates in a controlled numbered-label palette.")
    parser.add_argument("source", type=Path, help="numbered-label palette LDS input")
    parser.add_argument("output", type=Path, help="new LDS output; must not already exist")
    parser.add_argument("--prefix", default="PAGE", help="ASCII label prefix to normalize (default: PAGE)")
    args = parser.parse_args()
    target_y, changed = write_normalized_palette(args.source, args.output, args.prefix)
    print(f"wrote {args.output}")
    print(f"normalized {args.prefix} {', '.join(changed)} to Y={target_y:.6f} mm")


if __name__ == "__main__":
    main()
