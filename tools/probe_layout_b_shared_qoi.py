"""Create one research LDS that redirects seven Layout-B image links to slot 1.

This is intentionally a narrow probe, not a production writer.  It preserves
the document's single QOI and changes only the first uint32 in its seven
type-25 image-link records to the type-26 reference used by the inline first
image.  The output is never allowed to overwrite an existing file.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import struct
import zipfile

from ldsqoirev.inspect import find_qoi_streams


MARKER = b"\xad\x9cN\x1e"


def redirect_to_first_inline_image(source: Path, output: Path) -> None:
    if output.exists():
        raise FileExistsError(f"refusing to overwrite existing output: {output}")
    with zipfile.ZipFile(source) as archive:
        cdoc = bytearray(archive.read("CDOC"))
        if len(find_qoi_streams(cdoc)) != 1:
            raise ValueError("probe requires exactly one QOI")

        inline_reference: int | None = None
        linked_payload_offsets: list[int] = []
        cursor = 0
        while True:
            marker = cdoc.find(MARKER, cursor)
            if marker < 0:
                break
            cursor = marker + 4
            if marker + 24 > len(cdoc):
                continue
            record_type = struct.unpack_from("<I", cdoc, marker + 8)[0]
            length = struct.unpack_from("<I", cdoc, marker + 12)[0]
            if length != 8:
                continue
            if record_type == 26:
                inline_reference = struct.unpack_from("<I", cdoc, marker + 16)[0]
            elif record_type == 25:
                linked_payload_offsets.append(marker + 16)

        if inline_reference is None or len(linked_payload_offsets) != 7:
            raise ValueError(
                f"expected one type-26 reference and seven type-25 links; got {inline_reference=}, {len(linked_payload_offsets)=}"
            )
        for payload_offset in linked_payload_offsets:
            struct.pack_into("<I", cdoc, payload_offset, inline_reference)

        with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED) as destination:
            for info in archive.infolist():
                data = bytes(cdoc) if info.filename == "CDOC" else archive.read(info.filename)
                copied = zipfile.ZipInfo(info.filename, date_time=info.date_time)
                copied.compress_type = info.compress_type
                copied.comment = info.comment
                copied.extra = info.extra
                copied.internal_attr = info.internal_attr
                copied.external_attr = info.external_attr
                destination.writestr(copied, data)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    redirect_to_first_inline_image(args.source, args.output)
    print(f"wrote {args.output}")


if __name__ == "__main__":
    main()
