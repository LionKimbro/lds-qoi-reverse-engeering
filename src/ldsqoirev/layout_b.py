"""Evidence-backed inspection of the common scripted Layout-B structure.

This module reports candidate color slots only. It deliberately does not edit
them: the LDS record semantics still need an open-in-LDS validation fixture.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


LAYOUT_B_TEXT = b"Layout B"
STANDARD_PREFIX_COLOR_OFFSET = 0x5ED
SOURCE_COLOR_AFTER_NAME = 118
PNG_NAME = re.compile(rb"[ -~]+\.png")


@dataclass(frozen=True)
class LayoutBColorSlot:
    offset: int
    rgba_bytes: bytes
    source_name: str | None

    @property
    def hex(self) -> str:
        return self.rgba_bytes.hex(" ")


def find_layout_b_color_slots(cdoc: bytes) -> list[LayoutBColorSlot]:
    """Find repeated color-like slots in a standard scripted Layout-B CDOC.

    Returns an empty list when the expected terminal text record or source-name
    layout is absent. The bytes are reported in on-disk order; channel ordering
    is intentionally not interpreted here.
    """
    if cdoc.find(LAYOUT_B_TEXT) != len(cdoc) - 74:
        return []
    if len(cdoc) < STANDARD_PREFIX_COLOR_OFFSET + 4:
        return []
    if cdoc[STANDARD_PREFIX_COLOR_OFFSET + 3] != 0xFF:
        return []

    slots = [
        LayoutBColorSlot(
            STANDARD_PREFIX_COLOR_OFFSET,
            cdoc[STANDARD_PREFIX_COLOR_OFFSET : STANDARD_PREFIX_COLOR_OFFSET + 4],
            None,
        )
    ]
    for match in PNG_NAME.finditer(cdoc):
        offset = match.end() + SOURCE_COLOR_AFTER_NAME
        if offset + 4 > len(cdoc):
            continue
        name = match.group().decode("utf-8", "replace")
        slots.append(LayoutBColorSlot(offset, cdoc[offset : offset + 4], name))
    return slots
