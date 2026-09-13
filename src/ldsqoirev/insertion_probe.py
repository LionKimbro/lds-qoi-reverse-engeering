"""Replay one measured CDOC insertion into an exact, fingerprinted base LDS.

This is deliberately a research probe, not a general LDS writer.  It derives
the inserted CDOC bytes from a GUI-created base/reference pair, checks that
the supplied base is byte-identical outside that insertion, and writes only a
new archive.  It keeps the base PREVIEW unchanged; LDS-open validation must
determine whether the application regenerates that derived member.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
from pathlib import Path
import zipfile


@dataclass(frozen=True)
class Insertion:
    """A CDOC byte insertion measured from one controlled pair."""

    offset: int
    suffix_length: int
    payload: bytes


def _read_cdoc(path: Path) -> bytes:
    with zipfile.ZipFile(path) as archive:
        return archive.read("CDOC")


def derive_insertion(base_cdoc: bytes, reference_cdoc: bytes) -> Insertion:
    """Derive an insertion when reference is base with one contiguous splice."""
    prefix = 0
    shared = min(len(base_cdoc), len(reference_cdoc))
    while prefix < shared and base_cdoc[prefix] == reference_cdoc[prefix]:
        prefix += 1

    suffix = 0
    while (
        suffix < len(base_cdoc) - prefix
        and suffix < len(reference_cdoc) - prefix
        and base_cdoc[-1 - suffix] == reference_cdoc[-1 - suffix]
    ):
        suffix += 1

    if base_cdoc[prefix : len(base_cdoc) - suffix] or prefix == len(reference_cdoc):
        raise ValueError("reference is not a pure contiguous CDOC insertion into this base")
    payload_end = len(reference_cdoc) - suffix if suffix else len(reference_cdoc)
    payload = reference_cdoc[prefix:payload_end]
    if not payload:
        raise ValueError("controlled pair contains no insertion")
    return Insertion(prefix, suffix, payload)


def replay_insertion(base: Path, reference: Path, output: Path) -> Insertion:
    """Write a new LDS containing the measured CDOC splice; never overwrite."""
    if output.exists():
        raise FileExistsError(f"refusing to overwrite existing output: {output}")
    base_cdoc = _read_cdoc(base)
    reference_cdoc = _read_cdoc(reference)
    insertion = derive_insertion(base_cdoc, reference_cdoc)
    end = len(base_cdoc) - insertion.suffix_length if insertion.suffix_length else len(base_cdoc)
    reconstructed = base_cdoc[: insertion.offset] + insertion.payload + base_cdoc[end:]
    if reconstructed != reference_cdoc:
        raise AssertionError("internal error: derived splice did not reconstruct reference CDOC")

    with zipfile.ZipFile(base) as source, zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED) as destination:
        for info in source.infolist():
            data = reconstructed if info.filename == "CDOC" else source.read(info.filename)
            copied_info = zipfile.ZipInfo(info.filename, date_time=info.date_time)
            copied_info.compress_type = info.compress_type
            copied_info.comment = info.comment
            copied_info.extra = info.extra
            copied_info.internal_attr = info.internal_attr
            copied_info.external_attr = info.external_attr
            destination.writestr(copied_info, data)
    return insertion


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay a measured LDS CDOC object insertion.")
    parser.add_argument("base", type=Path, help="original, immutable base LDS")
    parser.add_argument("reference", type=Path, help="GUI-produced LDS with one added object")
    parser.add_argument("output", type=Path, help="new derived LDS; must not already exist")
    args = parser.parse_args()
    insertion = replay_insertion(args.base, args.reference, args.output)
    print(
        f"wrote {args.output}\\n"
        f"insertion: offset={insertion.offset} bytes={len(insertion.payload)} "
        f"suffix={insertion.suffix_length}\\n"
        f"payload sha256={hashlib.sha256(insertion.payload).hexdigest()}"
    )


if __name__ == "__main__":
    main()
