"""List every validated QOI stream embedded in an LDS file's CDOC member."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import zipfile

from ldsqoirev.inspect import decode_qoi, find_qoi_streams


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, help="LDS file to inspect (read-only)")
    args = parser.parse_args()

    with zipfile.ZipFile(args.path) as archive:
        cdoc = archive.read("CDOC")
    streams = find_qoi_streams(cdoc)
    print(f"file: {args.path}")
    print(f"CDOC bytes: {len(cdoc)}")
    print(f"validated QOI streams: {len(streams)}")
    for number, stream in enumerate(streams, start=1):
        _, rgba = decode_qoi(cdoc, stream.offset)
        pixels_sha256 = hashlib.sha256(rgba).hexdigest()
        print(
            f"{number}: offset=0x{stream.offset:x} "
            f"dimensions={stream.width}x{stream.height} "
            f"encoded_bytes={stream.encoded_length} "
            f"rgba_sha256={pixels_sha256}"
        )


if __name__ == "__main__":
    main()
