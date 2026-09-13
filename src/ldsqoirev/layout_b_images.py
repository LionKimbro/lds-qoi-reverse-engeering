"""Experimental image replacement helpers for Layout-B LDS documents.

LDS can represent Layout-B's first image as an inline QOI while later slots
remain linked image records.  A one-QOI file is therefore *not* a safe
all-eight template.  The all-resource operation below accepts a document LDS
has already materialized into two inline QOIs and replaces both resources.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import secrets
import struct
import zipfile

from .inspect import QOI_END_MARKER, decode_qoi, find_qoi_streams


QOI_MAGIC = b"qoif"
RECORD_MARKER = b"\xad\x9cN\x1e"


def _hash_pixel(pixel: tuple[int, int, int, int]) -> int:
    red, green, blue, alpha = pixel
    return (red * 3 + green * 5 + blue * 7 + alpha * 11) % 64


def encode_qoi_rgba(width: int, height: int, pixels: bytes, *, colorspace: int = 0) -> bytes:
    """Encode exact RGBA pixels as a valid QOI stream."""
    if width <= 0 or height <= 0 or len(pixels) != width * height * 4:
        raise ValueError("RGBA buffer size does not match image dimensions")
    if colorspace not in (0, 1):
        raise ValueError("QOI colorspace must be 0 or 1")
    output = bytearray(QOI_MAGIC + struct.pack(">IIBB", width, height, 4, colorspace))
    index = [(0, 0, 0, 0)] * 64
    previous = (0, 0, 0, 255)
    run = 0
    count = width * height

    for number in range(count):
        offset = number * 4
        pixel = tuple(pixels[offset : offset + 4])
        if pixel == previous:
            run += 1
            if run == 62 or number == count - 1:
                output.append(0xC0 | (run - 1))
                run = 0
            continue
        if run:
            output.append(0xC0 | (run - 1))
            run = 0

        hashed = _hash_pixel(pixel)
        if index[hashed] == pixel:
            output.append(hashed)
        else:
            index[hashed] = pixel
            red, green, blue, alpha = pixel
            prior_red, prior_green, prior_blue, prior_alpha = previous
            if alpha != prior_alpha:
                output.extend((0xFF, red, green, blue, alpha))
            else:
                red_delta = red - prior_red
                green_delta = green - prior_green
                blue_delta = blue - prior_blue
                if all(-2 <= value <= 1 for value in (red_delta, green_delta, blue_delta)):
                    output.append(0x40 | ((red_delta + 2) << 4) | ((green_delta + 2) << 2) | (blue_delta + 2))
                else:
                    red_green = red_delta - green_delta
                    blue_green = blue_delta - green_delta
                    if -32 <= green_delta <= 31 and -8 <= red_green <= 7 and -8 <= blue_green <= 7:
                        output.extend((0x80 | (green_delta + 32), ((red_green + 8) << 4) | (blue_green + 8)))
                    else:
                        output.extend((0xFE, red, green, blue))
        previous = pixel
    return bytes(output + QOI_END_MARKER)


def _load_rgba_image(path: Path) -> tuple[int, int, bytes]:
    try:
        from PIL import Image
    except ImportError as error:  # pragma: no cover - environment-dependent
        raise RuntimeError("PNG/JPEG input requires Pillow (pip install Pillow)") from error
    with Image.open(path) as image:
        rgba = image.convert("RGBA")
        return rgba.width, rgba.height, rgba.tobytes()


def _refresh_layout_b_image_cache_key(cdoc: bytearray) -> bytes:
    """Discover and replace the shared trailer key in all eight image links.

    An image-link envelope is a 40-byte span beginning with a record marker:
    type-26 for the first inline-QOI image, and type-25 for the seven linked
    images. Its final eight bytes are the shared, process-local LDS cache key.
    The first envelope is immediately followed by a type-10 QOI record; the
    other seven are followed by type-14 records.
    """
    key_offsets: list[int] = []
    record_types: list[int] = []
    cursor = 0
    while True:
        record = cdoc.find(RECORD_MARKER, cursor)
        if record < 0:
            break
        cursor = record + 4
        if record + 52 > len(cdoc):
            continue
        record_type = struct.unpack_from("<I", cdoc, record + 8)[0]
        payload_length = struct.unpack_from("<I", cdoc, record + 12)[0]
        if record_type not in (25, 26) or payload_length != 8:
            continue
        next_record = record + 40
        if cdoc[next_record : next_record + 4] != RECORD_MARKER:
            continue
        next_type = struct.unpack_from("<I", cdoc, next_record + 8)[0]
        if (record_type == 26 and next_type != 10) or (record_type == 25 and next_type != 14):
            continue
        key_offsets.append(record + 32)
        record_types.append(record_type)

    if len(key_offsets) != 8 or record_types.count(26) != 1 or record_types.count(25) != 7:
        raise ValueError(
            "expected one type-26 and seven type-25 Layout-B image-link envelopes; "
            f"found type-26={record_types.count(26)}, type-25={record_types.count(25)}"
        )
    old_keys = {bytes(cdoc[offset : offset + 8]) for offset in key_offsets}
    if len(old_keys) != 1:
        raise ValueError("Layout-B image-link envelopes do not share one cache key")
    new_key = secrets.token_bytes(8)
    for offset in key_offsets:
        cdoc[offset : offset + 8] = new_key
    return new_key


def _preserve_layout_b_display_scale(cdoc: bytearray, old_width: int, old_height: int, new_width: int, new_height: int) -> int:
    """Rescale the eight observed image-object source-pixel scale fields.

    The type-100 records retain their destination bounds. Their floats at
    marker-relative offsets 0x40 and 0x4c convert source pixels into document
    units. Adjusting them inversely to native QOI dimensions preserves the
    displayed Layout-B box size. The two horizontal slots are rotation
    matrices, so both entries associated with each source axis are updated.
    """
    changed = 0
    # One placement record precedes the shared QOI; the other seven follow it.
    cursor = 0
    while True:
        record = cdoc.find(RECORD_MARKER, cursor)
        if record < 0:
            break
        cursor = record + 4
        if record + 138 > len(cdoc):
            continue
        if cdoc[record + 4 : record + 8] != b"\0\0\0\0" or struct.unpack_from("<I", cdoc, record + 8)[0] != 100:
            continue
        if struct.unpack_from("<I", cdoc, record + 12)[0] != 106:
            continue
        stored_width, stored_height = struct.unpack_from("<ff", cdoc, record + 44)
        # Image objects store an effective source extent slightly below the
        # QOI dimensions; text objects do not resemble this pair.
        if abs(stored_width - old_width) > max(20.0, old_width * 0.02) or abs(stored_height - old_height) > max(20.0, old_height * 0.02):
            continue
        a, b, c, d = struct.unpack_from("<ffff", cdoc, record + 64)
        struct.pack_into(
            "<ffff",
            cdoc,
            record + 64,
            a * old_width / new_width,
            b * old_width / new_width,
            c * old_height / new_height,
            d * old_height / new_height,
        )
        changed += 1
    if changed != 8:
        raise ValueError(f"expected eight Layout-B image scale records, found {changed}")
    return changed


def replace_layout_b_image(template: Path, artwork: Path, output: Path) -> bytes:
    """Write a one-QOI Layout B with a new image and a fresh cache identity.

    The original and output must differ. Existing output is never overwritten.
    PREVIEW remains stale until opened and saved in LDS. The eight image groups
    receive one new shared cache key so parallel generated files do not collide
    in an already-running LDS process.
    """
    if output.exists():
        raise FileExistsError(f"refusing to overwrite existing output: {output}")
    with zipfile.ZipFile(template) as source:
        cdoc = source.read("CDOC")
        streams = find_qoi_streams(cdoc)
        if len(streams) != 1:
            raise ValueError(f"expected exactly one embedded QOI stream, found {len(streams)}")
        old_stream = streams[0]
        record = cdoc.rfind(RECORD_MARKER, 0, old_stream.offset)
        if record < 0 or old_stream.offset != record + 32:
            raise ValueError("QOI is not in the expected type-10 record position")
        if struct.unpack_from("<I", cdoc, record + 8)[0] != 10:
            raise ValueError("QOI enclosing record is not type 10")
        old_length = struct.unpack_from("<I", cdoc, record + 12)[0]
        if old_length != old_stream.encoded_length:
            raise ValueError("type-10 payload length does not equal QOI length")

        width, height, rgba = _load_rgba_image(artwork)
        new_qoi = encode_qoi_rgba(width, height, rgba)
        # Decode as an internal validity check before writing any archive.
        decoded, decoded_rgba = decode_qoi(new_qoi)
        if (decoded.width, decoded.height, decoded_rgba) != (width, height, rgba):
            raise AssertionError("QOI round-trip verification failed")

        changed = bytearray(cdoc[: old_stream.offset] + new_qoi + cdoc[old_stream.end_offset :])
        struct.pack_into("<I", changed, record + 12, len(new_qoi))
        _preserve_layout_b_display_scale(
            changed,
            old_stream.width,
            old_stream.height,
            width,
            height,
        )
        cache_key = _refresh_layout_b_image_cache_key(changed)
        with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED) as destination:
            for info in source.infolist():
                data = bytes(changed) if info.filename == "CDOC" else source.read(info.filename)
                copied = zipfile.ZipInfo(info.filename, date_time=info.date_time)
                copied.compress_type = info.compress_type
                copied.comment = info.comment
                copied.extra = info.extra
                copied.internal_attr = info.internal_attr
                copied.external_attr = info.external_attr
                destination.writestr(copied, data)
    return cache_key


def replace_materialized_layout_b_images(template: Path, artwork: Path, output: Path) -> None:
    """Replace both inline image resources in an LDS-materialized Layout B.

    The input must contain exactly two QOI streams: the first image object and
    the shared resource used by the other seven slots.  Both are replaced with
    the same native-pixel artwork, while the eight transform matrices preserve
    their existing physical Layout-B boxes.
    """
    if output.exists():
        raise FileExistsError(f"refusing to overwrite existing output: {output}")
    with zipfile.ZipFile(template) as source:
        cdoc = source.read("CDOC")
        streams = find_qoi_streams(cdoc)
        if len(streams) != 2:
            raise ValueError(f"expected exactly two materialized QOI streams, found {len(streams)}")
        if (streams[0].width, streams[0].height) != (streams[1].width, streams[1].height):
            raise ValueError("materialized image resources have different native dimensions")
        for stream in streams:
            record = cdoc.rfind(RECORD_MARKER, 0, stream.offset)
            if record < 0 or stream.offset != record + 32 or struct.unpack_from("<I", cdoc, record + 8)[0] != 10:
                raise ValueError("QOI is not in the expected type-10 record position")
            if struct.unpack_from("<I", cdoc, record + 12)[0] != stream.encoded_length:
                raise ValueError("type-10 payload length does not equal QOI length")

        width, height, rgba = _load_rgba_image(artwork)
        new_qoi = encode_qoi_rgba(width, height, rgba)
        decoded, decoded_rgba = decode_qoi(new_qoi)
        if (decoded.width, decoded.height, decoded_rgba) != (width, height, rgba):
            raise AssertionError("QOI round-trip verification failed")

        changed = bytearray(cdoc)
        # Work from the end so offsets of earlier records do not move.
        for stream in reversed(streams):
            record = changed.rfind(RECORD_MARKER, 0, stream.offset)
            changed[stream.offset : stream.end_offset] = new_qoi
            struct.pack_into("<I", changed, record + 12, len(new_qoi))
        _preserve_layout_b_display_scale(changed, streams[0].width, streams[0].height, width, height)

        with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED) as destination:
            for info in source.infolist():
                data = bytes(changed) if info.filename == "CDOC" else source.read(info.filename)
                copied = zipfile.ZipInfo(info.filename, date_time=info.date_time)
                copied.compress_type = info.compress_type
                copied.comment = info.comment
                copied.extra = info.extra
                copied.internal_attr = info.internal_attr
                copied.external_attr = info.external_attr
                destination.writestr(copied, data)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create a standard Layout-B LDS by replacing its one embedded artwork image."
    )
    parser.add_argument("template", type=Path, help="existing standard Layout-B .lds template")
    parser.add_argument("artwork", type=Path, help="replacement image (PNG/JPEG/etc.; native dimensions retained)")
    parser.add_argument("output", type=Path, help="new .lds path; must not already exist")
    parser.add_argument("--all-materialized", action="store_true", help="replace both QOIs in an LDS-materialized Layout B")
    args = parser.parse_args()
    operation = replace_materialized_layout_b_images if args.all_materialized else replace_layout_b_image
    cache_key = operation(args.template, args.artwork, args.output)
    print(f"wrote {args.output}")
    if cache_key is not None:
        print(f"new shared image-cache key: {cache_key.hex()}")
    print("PREVIEW is retained from the template; open/save in LDS to regenerate it.")


if __name__ == "__main__":
    main()
