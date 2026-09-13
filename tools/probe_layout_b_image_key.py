"""Replace a candidate shared 8-byte Layout-B image-cache token (research only)."""

from __future__ import annotations

import argparse
import secrets
from pathlib import Path
import zipfile

from ldsqoirev.inspect import find_qoi_streams


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--old", required=True, help="existing 8-byte token, as 16 hex digits")
    parser.add_argument("--new", help="replacement 8-byte token, as 16 hex digits; random when omitted")
    args = parser.parse_args()

    old = bytes.fromhex(args.old)
    new = bytes.fromhex(args.new) if args.new else secrets.token_bytes(8)
    if len(old) != 8 or len(new) != 8:
        raise ValueError("tokens must each be exactly 8 bytes")
    if args.output.exists():
        raise FileExistsError(f"refusing to overwrite existing output: {args.output}")

    with zipfile.ZipFile(args.source) as archive:
        cdoc = archive.read("CDOC")
        if len(find_qoi_streams(cdoc)) != 1:
            raise ValueError("probe requires exactly one QOI")
        occurrences = cdoc.count(old)
        if occurrences != 8:
            raise ValueError(f"expected the old token exactly 8 times, found {occurrences}")
        changed = cdoc.replace(old, new)
        with zipfile.ZipFile(args.output, "x", compression=zipfile.ZIP_DEFLATED) as destination:
            for info in archive.infolist():
                data = changed if info.filename == "CDOC" else archive.read(info.filename)
                copied = zipfile.ZipInfo(info.filename, date_time=info.date_time)
                copied.compress_type = info.compress_type
                copied.comment = info.comment
                copied.extra = info.extra
                copied.internal_attr = info.internal_attr
                copied.external_attr = info.external_attr
                destination.writestr(copied, data)
    print(f"wrote {args.output}")
    print(f"replaced shared token {old.hex()} -> {new.hex()} in {occurrences} image groups")


if __name__ == "__main__":
    main()
