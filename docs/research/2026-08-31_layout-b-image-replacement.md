# Layout B image replacement prototype

**Date:** 2026-08-31

## Emergency objective

The previous GUI replay workflow for creating Layout B sheets is no longer
usable because its text-window pixel coordinates shifted. The priority is now
a template-backed replacement workflow: preserve a known Layout B document's
eight placements and replace its one embedded artwork image.

## Confirmed standard Layout B image structure

`NEW_sumi_dedenne__B.lds` has one embedded QOI stream in CDOC:

```text
type-10 record (payload length) -> QOI image -> repeated downstream placement records
```

The QOI starts exactly 32 bytes after its type-10 marker record. Its declared
payload length is exactly the encoded QOI length. The standard Dedenne image
is `1696 x 2528`, encoded in 6,696,864 bytes. Later testing showed that this
one image payload governs only the first placement; the other seven carry
additional linked-image state.

## One-QOI prototype (diagnostic only)

`src/ldsqoirev/layout_b_images.py` provides:

- `encode_qoi_rgba(width, height, pixels)`: a QOI encoder;
- `replace_layout_b_image(template, artwork, output)`: a copy-only image
  replacement operation.

The operation accepts a PNG/JPEG/etc. readable by Pillow, preserves its native
pixel width and height, encodes it as QOI, replaces the sole type-10 payload,
and updates only that record's 32-bit declared payload length. It rejects
multiple-QOI layouts and refuses to overwrite an output. It deliberately does
not alter linked-image records, so it changes only the first placement. It is
not a production generator. PREVIEW remains stale until saved in LDS.

## Encoder validation

The Dedenne QOI was decoded to RGBA and re-encoded. The re-encoded stream has
the exact original length and reconstructs the exact original pixels. More
strongly, replacing the Dedenne QOI with this re-encoded version yielded a
CDOC byte-for-byte identical to the original. This confirms that the encoder
matches LDS's observed QOI encoding for this image.

## Differing-aspect-ratio test ready for LDS validation

`pg03_4_zen_pikachu__M.lds` is a **manual-layout** (`M`) sheet, not a Layout B
reference. It is useful solely because its source image is `825 x 1024`,
rather than the standard Layout-B `1696 x 2528`. Its QOI was extracted and
inserted into the Dedenne Layout B template.

The first no-transform-edit trial displayed only the native-size image in each
fixed Layout-B box. This confirms that the QOI dimensions alone do not cause
LDS to scale the artwork. The eight type-100 image-object records contain the
required source-pixel-to-document transform matrix. For an upright slot it is
diagonal; for the two horizontal slots it is an off-diagonal rotation matrix.

The replacer now rescales each matrix *column* inversely to the old/new QOI
source dimensions, retaining the original Layout B destination box size. This
uses the Layout B template's own scale values, not any manual-layout placement
data. The corrected result is:

`docs/research/artifacts/2026-08-31/NEW_sumi_dedenne__B__zen-pikachu-image-autoscaled__experimental.lds`

The output type-10 record now has the exact Zen QOI payload length
`1,493,785`, and the QOI header is `825 x 1024`. Opening it in LDS will test
the corrected image-replacement path, including the rotated bottom pair.

## Repeatable command and artwork handling

The prototype is callable as:

```powershell
$env:PYTHONPATH = 'src'
python -m ldsqoirev.layout_b_images TEMPLATE.LDS ARTWORK.PNG OUTPUT.LDS
```

It refuses to overwrite output, retains native artwork pixels, updates the
QOI payload and the eight display transforms, and leaves PREVIEW stale until
LDS opens/saves the result. `docs/research/artifacts/` is Git-ignored because
it contains private/copyrighted artwork and derived LDS files; it must not be
committed.

## Initial operational batch — superseded

An initial batch was created against four new PNGs in
`C:\lion\code\stickerdb\.stickerdb\exports\`. It created these adjacent
outputs:

- `charmeleon__sticker-sheet__Layout-B.lds` (`1537 x 2291` source image);
- `lillipup__sticker-sheet__Layout-B.lds` (`1696 x 2528`);
- `scrafty__sticker-sheet__Layout-B.lds` (`1696 x 2528`);
- `weedle__sticker-sheet__Layout-B.lds` (`1696 x 2528`).

`scrafty__sticker-sheet__Layout-B.lds` rendered perfectly in LDS. However,
the subsequent Weedle inspection invalidated the batch as a whole: its
upper-left sticker was Weedle while its other seven stickers were the artwork
from the Scrafty artifact, and its retained PREVIEW showed Flareon.

The saved Weedle document proves that the seven later placements are linked to
a separately resolved image resource: after LDS saved the document, CDOC
contained the new Weedle QOI plus a second QOI that is byte-for-byte identical
to the Scrafty output's QOI. This invalidated the initial theory that all eight
placements resolve directly to the one embedded QOI.

Accordingly, the four initial batch files are **test artifacts, not approved
production outputs**. A fresh isolated Weedle test was generated directly
from the requested black-text source:

`C:\lion\code\stickerdb\.stickerdb\exports\weedle__sticker-sheet__Layout-B__from-flareon-template.lds`

It is intentionally a new path; the problematic output was not overwritten.
Its PREVIEW is necessarily still Flareon until LDS saves it, but its sole CDOC
QOI is Weedle and the source template is the requested Flareon file. It is the
next document to validate in LDS before re-running any batch.

## Linked-image discovery

That isolated test revealed that a one-QOI Layout B is still not a complete
eight-image representation. LDS displayed Weedle in the upper-left placement
and Lillipup in the other seven. The byte evidence is now clear:

- the upper-left object uses record type 26 followed by an inline type-10 QOI;
- each other image object uses record type 25 and carries a separate
  `sticker.png` source-name fragment;
- LDS resolves those linked records independently, and on save materializes
  their shared resolved artwork as a second inline QOI.

The earlier one-QOI operation is therefore diagnostic-only and must not be
used for production sheets. `replace_materialized_layout_b_images()` was added
to `src/ldsqoirev/layout_b_images.py`. It accepts an LDS-saved, two-QOI Layout
B and replaces *both* resources with the desired artwork. The first
all-eight-image experiment is:

`C:\lion\code\stickerdb\.stickerdb\exports\weedle__sticker-sheet__Layout-B__all-eight-embedded-experimental.lds`

Its CDOC contains exactly two QOIs, both Weedle (`1696 x 2528`,
`7,364,668` bytes). Its inherited preview remains stale; the open-in-LDS
render is the required validation.

An input audit found no overwritten or mismatched PNG inputs: the four PNGs
have distinct hashes and dimensions, and each corresponding one-QOI output
decodes pixel-for-pixel to its named PNG. The designated Flareon template's
sole QOI was decoded and visually confirmed as Flareon. Therefore the Lillipup
result comes from the seven linked-image records, not a corrupted Flareon QOI.
