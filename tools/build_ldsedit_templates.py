"""Build readable Base64 Python source for experimental ldsedit templates."""

from __future__ import annotations

from pathlib import Path
import base64
import zlib

from ldsedit import (
    DEFAULT_PAGE_PALETTE,
    DEFAULT_POS_PALETTE,
    _load_templates,
    _separator,
    _template_prefix,
)


def main() -> None:
    destination = Path(__file__).resolve().parents[1] / "src" / "ldsedit" / "_template_data.py"
    entries: dict[str, bytes] = {}
    for prefix, palette in (("PAGE", DEFAULT_PAGE_PALETTE), ("POS", DEFAULT_POS_PALETTE)):
        templates = _load_templates(palette, prefix)
        for number, template in sorted(templates.items()):
            entries[f"{prefix} {number}"] = template.body
    bridge = _template_prefix(DEFAULT_PAGE_PALETTE, "PAGE")
    separator = _separator(DEFAULT_PAGE_PALETTE, "PAGE")
    entries["__bridge__"] = bridge
    entries["__separator__"] = separator
    lines = [
        '"""Generated Base64/zlib LDS text-object templates; do not hand-edit."""',
        "",
        "TEMPLATES: dict[str, str] = {",
    ]
    for key, value in entries.items():
        encoded = base64.b64encode(zlib.compress(value, level=9)).decode("ascii")
        lines.append(f'    {key!r}: {encoded!r},')
    lines.extend(["}", ""])
    destination.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print(f"wrote {destination} ({destination.stat().st_size} bytes; {len(entries)} keys)")


if __name__ == "__main__":
    main()
