"""Read-only inspection helpers for Leonardo Design Studio research files."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
from pathlib import Path
import struct
import zipfile


QOI_MAGIC = b"qoif"
QOI_END_MARKER = b"\x00\x00\x00\x00\x00\x00\x00\x01"


@dataclass(frozen=True)
class QoiStream:
    offset: int
    end_offset: int
    width: int
    height: int
    channels: int
    colorspace: int

    @property
    def encoded_length(self) -> int:
        return self.end_offset - self.offset


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def qoi_end_offset(data: bytes, offset: int) -> int | None:
    """Return the byte after a valid QOI stream, or ``None`` if invalid."""
    if offset < 0 or offset + 14 > len(data) or data[offset : offset + 4] != QOI_MAGIC:
        return None
    width, height, channels, colorspace = struct.unpack_from(">IIBB", data, offset + 4)
    if width == 0 or height == 0 or channels not in (3, 4) or colorspace not in (0, 1):
        return None

    target_pixels = width * height
    pixel_count = 0
    cursor = offset + 14
    run_remaining = 0

    while pixel_count < target_pixels:
        if run_remaining:
            run_remaining -= 1
            pixel_count += 1
            continue
        if cursor >= len(data):
            return None
        tag = data[cursor]
        cursor += 1
        if tag == 0xFE:
            cursor += 3
        elif tag == 0xFF:
            cursor += 4
        elif tag & 0xC0 == 0x00:  # QOI_INDEX
            pass
        elif tag & 0xC0 == 0x40:  # QOI_DIFF
            pass
        elif tag & 0xC0 == 0x80:  # QOI_LUMA
            cursor += 1
        else:  # QOI_RUN
            run_remaining = tag & 0x3F
        if cursor > len(data):
            return None
        pixel_count += 1

    if cursor + len(QOI_END_MARKER) > len(data):
        return None
    if data[cursor : cursor + len(QOI_END_MARKER)] != QOI_END_MARKER:
        return None
    return cursor + len(QOI_END_MARKER)


def find_qoi_streams(data: bytes) -> list[QoiStream]:
    streams: list[QoiStream] = []
    search_at = 0
    while True:
        offset = data.find(QOI_MAGIC, search_at)
        if offset < 0:
            return streams
        end_offset = qoi_end_offset(data, offset)
        if end_offset is not None:
            width, height, channels, colorspace = struct.unpack_from(">IIBB", data, offset + 4)
            streams.append(QoiStream(offset, end_offset, width, height, channels, colorspace))
        search_at = offset + 4


def decode_qoi(data: bytes, offset: int = 0) -> tuple[QoiStream, bytes]:
    """Decode one validated QOI stream to RGBA bytes for research rendering."""
    end_offset = qoi_end_offset(data, offset)
    if end_offset is None:
        raise ValueError(f"invalid QOI stream at offset {offset:#x}")
    width, height, channels, colorspace = struct.unpack_from(">IIBB", data, offset + 4)
    stream = QoiStream(offset, end_offset, width, height, channels, colorspace)
    index = [(0, 0, 0, 0)] * 64
    pixel = (0, 0, 0, 255)
    pixels = bytearray()
    cursor = offset + 14
    run = 0

    def hash_pixel(value: tuple[int, int, int, int]) -> int:
        red, green, blue, alpha = value
        return (red * 3 + green * 5 + blue * 7 + alpha * 11) % 64

    for _ in range(width * height):
        if run:
            run -= 1
        else:
            tag = data[cursor]
            cursor += 1
            if tag == 0xFE:
                pixel = (data[cursor], data[cursor + 1], data[cursor + 2], pixel[3])
                cursor += 3
            elif tag == 0xFF:
                pixel = (data[cursor], data[cursor + 1], data[cursor + 2], data[cursor + 3])
                cursor += 4
            elif tag & 0xC0 == 0x00:
                pixel = index[tag]
            elif tag & 0xC0 == 0x40:
                pixel = (
                    (pixel[0] + ((tag >> 4 & 0x03) - 2)) & 0xFF,
                    (pixel[1] + ((tag >> 2 & 0x03) - 2)) & 0xFF,
                    (pixel[2] + ((tag & 0x03) - 2)) & 0xFF,
                    pixel[3],
                )
            elif tag & 0xC0 == 0x80:
                green_delta = (tag & 0x3F) - 32
                deltas = data[cursor]
                cursor += 1
                pixel = (
                    (pixel[0] + green_delta + ((deltas >> 4) - 8)) & 0xFF,
                    (pixel[1] + green_delta) & 0xFF,
                    (pixel[2] + green_delta + ((deltas & 0x0F) - 8)) & 0xFF,
                    pixel[3],
                )
            else:
                run = tag & 0x3F
            index[hash_pixel(pixel)] = pixel
        pixels.extend(pixel)
    return stream, bytes(pixels)


def inspect_lds(path: Path) -> dict[str, object]:
    """Return ZIP and CDOC/QOI facts without changing the source file."""
    source = path.read_bytes()
    result: dict[str, object] = {"path": str(path), "sha256": sha256(source), "file_size": len(source)}
    with zipfile.ZipFile(path) as archive:
        members = []
        cdoc = None
        for info in archive.infolist():
            member_data = archive.read(info)
            members.append(
                {
                    "name": info.filename,
                    "compression_method": info.compress_type,
                    "compressed_size": info.compress_size,
                    "uncompressed_size": info.file_size,
                    "crc32": f"{info.CRC:08x}",
                    "sha256": sha256(member_data),
                }
            )
            if info.filename == "CDOC":
                cdoc = member_data
        result["members"] = members
        if cdoc is not None:
            result["cdoc_size"] = len(cdoc)
            result["cdoc_sha256"] = sha256(cdoc)
            result["qoi_streams"] = [asdict(stream) | {"encoded_length": stream.encoded_length} for stream in find_qoi_streams(cdoc)]
    return result
