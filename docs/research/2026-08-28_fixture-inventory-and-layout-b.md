# Fixture inventory and initial Layout-B text finding

**Date:** 2026-08-28

## Scope

Read-only inspection of user-provided LDS fixture directories:

- `D:\projects\bookmarks`
- `D:\projects\stickers\25_sticker-sheets`

No source fixtures were modified.

## Confirmed: archive shape

All 170 sticker-sheet files inspected are ZIP archives containing exactly two
deflated members, in this order:

1. `CDOC`
2. `PREVIEW`

The initial bookmark scan found 12 LDS files with the same member pattern.
The first recursive inventory displayed 11 because it did not match an
upper-case extension consistently; later `Path.glob('*.lds')` found 12. Future
inventories must match extensions case-insensitively.

## Confirmed: QOI signature distribution

`CDOC` contains at least one `qoif` signature in every sticker-sheet fixture.

- 168 sticker sheets contain one raw `qoif` occurrence.
- 2 sticker sheets contain two raw `qoif` occurrences:
  - `cute_dragon_purple.lds` at `0x6ec5` and `0x122fb2`
  - `misc_jinx_zaun.lds` at `0xa09` and `0xe3bc9`

The project inspector decoded and validated all four streams in those two
files. The second stream in both is exactly `1024 x 256`, RGBA, colorspace 0,
and encoded length `145,903`.

| Fixture | QOI 1 | QOI 2 |
| --- | --- | --- |
| `cute_dragon_purple.lds` | `992 x 1056`, 985,217 bytes | `1024 x 256`, 145,903 bytes |
| `misc_jinx_zaun.lds` | `1024 x 434`, 873,004 bytes | `1024 x 256`, 145,903 bytes |

All 12 initially scanned bookmark fixtures had one validated QOI stream. Their
QOI dimensions vary; this is consistent with distinct hand-laid artwork and
does not yet identify layout metadata.

## Confirmed: PREVIEW is PNG; visual role established for one two-QOI fixture

The sampled `PREVIEW` members begin with the PNG signature and an IHDR declaring
`600 x 600`, RGBA. In `cute_dragon_purple.lds`, derived renderings establish
the following visible content:

- QOI 1 (`992 x 1056`) is a purple dragon illustration.
- QOI 2 (`1024 x 256`) is a horizontal Gyarados illustration.
- `PREVIEW` is a rendered 600x600 sheet with six rotated purple-dragon
  stickers and two horizontal Gyarados stickers at the bottom.

This is **confirmed for this fixture** and supports the user description of the
common eight-sticker arrangement. It does not establish that every second QOI
or every PREVIEW has the same role.

Derived, non-source artifacts are retained under
`docs/research/artifacts/2026-08-28/` for repeatable visual inspection.

## Strong inference: Godzilla natural layout-comparison pair

The following two files contain byte-identical embedded artwork, making them a
useful natural comparison pair even though they were not created as a
single-variable controlled experiment:

- `sumi_monsters_godzilla.lds`
- `sumi__monsters_godzilla__B.lds`

Their sole QOI streams are both `1696 x 2528`, 7,259,627 bytes, and have SHA-256
`bf9bfb5043bc87d91b4c52657cfa23b7a6c9167ba7348e43ca8033a0b2f6fbc7`.
Both previews visibly contain the same eight Godzilla stickers and the Layout-B
label, but their placements differ subtly. This means the comparison can
separate image bytes from at least some layout/object-record differences.

Both CDOCs contain the asset filename `sumi__monsters_godzilla.png` exactly
eight times after the QOI stream. The occurrences form fixed-stride sequences:

| Fixture | First filename offset | Record-to-record stride |
| --- | ---: | ---: |
| `sumi_monsters_godzilla.lds` | `0x6ed1df` | 2,033 bytes |
| `sumi__monsters_godzilla__B.lds` | `0x6ed868` | 2,561 bytes |

The individual image-object record layout is therefore not yet stable across
the two files. The filename repetition, count of eight, fixed stride within
each file, and visible eight-sticker preview together are strong evidence that
these are repeated placed-image object records. Coordinate-field locations
remain **unknown** until repeated records are aligned and tested against an
intentional position-only fixture.

### Candidate placement field (hypothesis)

For the first seven filename-anchored records in each Godzilla file, one
little-endian IEEE-754 float varies in a compact three-value pattern:

| Fixture | Relative byte offset from filename | Values by record |
| --- | ---: | --- |
| `sumi_monsters_godzilla.lds` | `+1264` | 21.6187, 21.6187, 109.5684, 109.5684, 109.5684, 197.4724, 197.4724 |
| `sumi__monsters_godzilla__B.lds` | `+1696` | 21.6234, 21.6234, 109.5731, 109.5731, 109.5731, 197.4766, 197.4766 |

The three clusters are consistent with a grid-axis coordinate, and the small
between-file shift is visually plausible given the preview placement change.
However, the record ordering and field semantics are not established, so this
remains a **hypothesis**. It must be checked with a true position-only fixture
before it informs any coordinate mutation.

## Confirmed: literal `Layout B` text field

The ASCII byte sequence `Layout B` occurs once in `CDOC` for 35 of the 170
sticker sheets. No UTF-16LE or UTF-16BE occurrence was found.

For every one of those 35 files:

- the text begins at `CDOC length - 74`;
- it is preceded immediately by UTF-8 BOM bytes `EF BB BF`;
- its fixed local suffix is `Layout B 0D 0A AD 9C 4E 1E FC 03 00 00 04 00 00 00
  00 00 00 00 4A 00 00 00 00 00`;
- the 48 preceding bytes were identical in four independently sampled files,
  including `FontKern=0` and several little-endian-looking integer fields.

Example, from `NEW_sumi_dedenne__B.lds`, `CDOC[0x6698b9:0x669909]`:

```text
0a 46 6f 6e 74 4b 65 72 6e 3d 30 0d 0a ad 9c 4e 1e
00 00 00 00 0e 00 00 00 0d 00 00 00 4e 00 00 00 c9
00 00 00 00 00 00 00 00 00 00 00 ef bb bf 4c 61 79
6f 75 74 20 42 0d 0a ad 9c 4e 1e fc 03 00 00 04 00
00 00 00 00 00 00 4a 00 00 00 00 00
```

This is strong evidence that a final CDOC record holds the visible Layout-B
label, but the field boundaries, length semantics, text style mapping, and
whether any supporting metadata exists elsewhere are **not yet confirmed**.
Do not mutate the field yet.

Across four sampled Layout-B files, the final `FontSize=` setting starts at
`CDOC length - 203`, `FontName=` at `CDOC length - 176`, and the label at
`CDOC length - 74`. Thus the final 203 bytes are a stable composite region
containing text style settings, binary fields, a BOM-prefixed text value, and a
binary suffix. The exact text-value field boundary is still not proven.

The `Layout B` cohort includes all four `NEW_sumi_*__B` files; various
`pg10`--`pg12` and `pg11` B-designated files; the `sumi__monsters_*__B` and
`sumi__one-piece_*__B` groups; `sumi_monsters_godzilla.lds`; and
`Untitled.lds`. It does not include every file whose filename has a similar
layout suffix, so filenames are not authoritative metadata.

## Confirmed: replay-generated final text region is nearly invariant

User-provided provenance: the Layout-B sheets were produced by a script that
replays mouse input through the Leonardo Design Studio GUI. Geometry and sizing
are therefore expected to be largely shared; text-color selection may be
imperfect in some runs.

Comparison of the final 203-byte text/style composite region across all 35
Layout-B CDOCs found exactly two variants:

- 34 files have an identical region (SHA-256 prefix `b4426269534b25e5`).
- `sumi_monsters_godzilla.lds` differs from that region at exactly two
  one-byte positions, relative to the 203-byte region: `+110` (`42` instead of
  `4e`) and `+155` (`3e` instead of `4a`).

This confirms unusually high replay consistency for this terminal region. It
does **not** yet show that those two bytes represent color; they may be text
object geometry or another property. If a visible color discrepancy exists
among otherwise equal Layout-B labels, the color field may be outside this
terminal region. The next comparison should target a pair explicitly labelled
by the user as having different rendered label colors.

## Strong inference: repeated opaque color field tracks Layout-B label color

User identified this contrast pair as having different rendered `Layout B`
text colors:

- `pg03_2_sumi_arcanine__B.LDS`
- `pg12_8_sumi_oddish__B.LDS`

The files have the same QOI offset (`0x0f5a`), same QOI dimensions
(`1696 x 2528`), and equal non-QOI prefix/tail lengths. After excluding the
QOI byte range, only 94 bytes differ:

- eight 8-byte runs, strongly consistent with different source-asset identity;
- nine 3-byte runs, one in the prefix and one in each of the eight repeated
  placement structures.

Each 3-byte run is immediately followed by `FF`, giving these candidate values:

| Fixture | Stored bytes at CDOC `0x05ed` |
| --- | --- |
| Arcanine | `93 B8 D1 FF` |
| Oddish | `B4 D6 EC FF` |

The same four bytes occur at the corresponding location of all eight repeated
post-QOI structures. Across the 34 standard-structure Layout-B files, this
field has a distinct nonzero `.. .. .. FF` value in every file. This pattern,
combined with the user-identified rendered color difference, is strong
evidence that this is an opaque color field associated with the replay-created
label/style rather than a QOI-pixel property.

The channel order is **not confirmed**. If it is RGBA, the two values are pale
blue shades; if it is BGRA, they are tan shades, visually more plausible for
the sampled previews. A same-art, color-only GUI fixture is still required to
promote this field mapping to confirmed and establish ordering.

`sumi_monsters_godzilla.lds` has a different surrounding prefix structure and
does not use the standard `0x05ed` location; do not apply this fixed offset to
that outlier.

### Refined hypothesis: final repeated slot carries the rendered label color

For the seven standard-layout files whose eight repeated source strings are
`layout-this.png`, the color-like field is at relative offset `+133` from each
source-string start. In the contrast pair it is:

```text
Arcanine:  93 B8 D1 FF  (first seven records), 00 00 00 FF (eighth/final record)
Oddish:    B4 D6 EC FF  (all eight records)
```

The black final Arcanine value matches its visibly dark/gray Layout-B label,
whereas the Oddish final value matches its visibly light tan label when read
as BGRA (`#ECD6B4`). This makes the final repeated slot the best current
candidate for the text-color state. The repeated record’s exact semantic
boundary remains unknown; do not assume that replacing only the final copy is
valid without an LDS-open validation fixture.

### Cohort-wide repetition pattern

For 34 standard-structure Layout-B files, the prefix color-like value at
`CDOC[0x05ed:0x05f1]` has either eight or nine total occurrences in the CDOC:

- **Nine occurrences**: one pre-QOI copy and all eight post-QOI placed-record
  copies have the same opaque value. Examples include Oddish, Dedenne, Piplup,
  Mimikyu, Togepi, and Zorro.
- **Eight occurrences**: one pre-QOI copy and only seven post-QOI copies match;
  the eighth/final post-QOI slot has another value, often `00 00 00 FF`.
  Examples include Arcanine, Jirachi, Gardevoir, Espeon, and the Godzilla-B
  sheet.

The source filename immediately preceding each post-QOI copy varies by file,
but the candidate field is consistently 129--167 bytes after that filename
(the difference tracks filename length). Thus this is a record-relative field,
not a universal post-QOI offset.

This occurrence-count split is strong evidence for the reported GUI replay
color-picker behavior: a successful style selection is propagated through all
eight repeated records; a failed or defaulted final state leaves the last slot
with a different color. It is still an inference about the record semantics,
not authorization to patch copies independently.

## Tooling added

`python -m ldsqoirev PATH...` now performs a read-only LDS inspection and
returns file/member hashes, ZIP metadata, and fully validated QOI boundaries.
Its QOI boundary detection is based on header validation, instruction parsing
to exactly `width * height` pixels, and the required eight-byte QOI end marker.

## Next experiments

1. Obtain a controlled pair where only the final drawn text changes (including
   one string-length change). This will establish the enclosing record and any
   length/index updates.
2. Compare a controlled pair with only text color changed to locate candidate
   color representation without conflating artwork variation.
3. Decode/render `PREVIEW` and the repeated `1024 x 256` QOI to determine
   their visible roles.
4. Produce QOI summaries for the standard Layout-B cohort using an optimized
   bulk scanner; the first full validation pass was computationally expensive,
   so raw signature enumeration was used for the initial 170-file census.
