# Text-grid coordinate fixtures

**Date:** 2026-08-28

## Fixture provenance

User-created controlled LDS files in the repository `lds/` directory:

| Fixture | Intentional content |
| --- | --- |
| `text-grid-01-one.lds` | One centered Arial text item: `CODEX IS AMAZING` |
| `text-grid-02-two.lds` | Copy of the item, positioned 1.5 inches to the right |
| `text-grid-03-four.lds` | Both items copied and positioned 0.5 inches below |

The user reports Arial, 0.100-inch text size, and centered alignment. No image
objects are present, making these clean text-only fixtures.

## Confirmed: text-only CDOC object records are fixed-size in this layout

All three files have ZIP members `CDOC` and `PREVIEW`, no embedded QOI streams,
and one layer. Their uncompressed CDOC sizes are:

| Fixture | CDOC size |
| --- | ---: |
| One text | 6,658 bytes |
| Two texts | 12,996 bytes |
| Four texts | 25,672 bytes |

Each added text item increases CDOC size by exactly **6,338 bytes**. Every CDOC
begins with a 320-byte document header; the remainder divides exactly into
6,338-byte text-object records:

```text
CDOC = 320-byte header + N × 6,338-byte records
```

The four-record fixture has records at CDOC offsets `0x0140`, `0x1a02`,
`0x32c4`, and `0x4b86`.

Each record contains the literal UTF-8 text with BOM and identical terminal
style fields:

```text
FontSize=2.53999996185303
FontName=Arial
FontBold=0
FontItalic=0
FontAlign=1
FontKern=0
﻿CODEX IS AMAZING
```

The text value starts 85 bytes before each record end; the `FontSize=` setting
starts 214 bytes before each record end. This establishes a repeatable,
fixed-size record structure for this specific text-only document family.

## Confirmed: primary X/Y placement fields

Within each 6,338-byte record, the following little-endian IEEE-754 float
fields encode the deliberate relative displacements in **millimetres**:

| Record-relative offset | Intended movement | Stored value |
| ---: | --- | --- |
| `+0x38` | 1.5 inches right | `66 66 18 42` = **38.1** |
| `+0x3c` | 0.5 inches down | `32 33 4b 41` = **12.7** |

Evidence from `text-grid-03-four.lds`, using the original first record as the
baseline:

| Record | `+0x38` X displacement | `+0x3c` Y displacement |
| --- | ---: | ---: |
| 1 (original) | 0.0 | 0.0 |
| 2 (right copy) | 38.1 | 0.0 |
| 3 (lower copy) | 0.0 | 12.7 |
| 4 (lower-right copy) | 38.1 | 12.7 |

This is **confirmed** for the controlled text-grid fixture family. Several
other record bytes also change with the copies, including identifiers and
derived transform/bounds fields; they should not be independently patched.

## Implications

The record segmentation makes text operations substantially more tractable:

- text items are represented by separately appendable fixed-size records in
  this simple document family;
- duplicate text remains literal and independently present in each record;
- placement uses explicit binary floats rather than only opaque transforms;
- standard inch values convert exactly to millimetres in these fields.

This does **not** yet prove the same offsets apply to all LDS text objects,
especially documents containing images, layers, rotations, nonzero original
positions, or other text styling. It is nevertheless the first confirmed
coordinate mapping suitable for regression testing.

## Next experiments

1. A same-document fixture with the text value changed to a longer and then a
   shorter string, preserving all other properties.
2. A same-document fixture where only this text item’s color changes.
3. A fixture moving one text item from a nonzero baseline position, to verify
   whether `+0x38` and `+0x3c` store absolute document coordinates or
   duplicate-operation deltas.
