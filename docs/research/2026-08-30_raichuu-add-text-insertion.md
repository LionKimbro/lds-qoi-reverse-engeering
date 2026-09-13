# Raichuu sticker sheet: controlled added-text insertion

**Date:** 2026-08-30

## Controlled pair

The user supplied these GUI-created files:

- Base: `C:\lion\code\stickerdb\.stickerdb\exports\raichuu-tail-slap-sticker-sheet__sticker-sheet.lds`
- Reference with added text:
  `C:\lion\code\stickerdb\.stickerdb\exports\raichuu-tail-slap-sticker-sheet__sticker-sheet_w-addl-text.lds`

The reference’s actual literal value is `CODEX IS AWESOME!!!` (three
exclamation marks). It is Arial, `FontSize=2.53999996185303`, and
`FontAlign=0`.

## Confirmed insertion shape

The reference CDOC is the base CDOC with one contiguous **7,925-byte** splice:

```text
base prefix (7,055,207 bytes)
+ inserted text-object region (7,925 bytes)
+ unchanged terminal suffix (28 bytes)
= reference CDOC (7,063,160 bytes)
```

No base CDOC byte is replaced. The insertion starts immediately before the
base’s final 28-byte terminal record. It begins by extending the preceding
sequence, then contains a type-`100` record, a type-`11` vector-path record,
two type-`14` settings/text records, and terminal records.

The new type-`11` payload is 7,506 bytes and declares 623 path commands. Its
stored path-space origin is `(-57.2530403, -108.6415176)`; do not interpret
that pair as a page coordinate without the surrounding transform context.

## Exact replay probe

`src/ldsqoirev/insertion_probe.py` is an intentionally narrow, safe tool. It:

1. derives a contiguous insertion from a base/reference pair;
2. refuses pairs that are not a pure splice;
3. refuses to overwrite output;
4. preserves all base archive members except its reconstructed `CDOC`.

It was run on this pair to create:

`docs/research/artifacts/2026-08-30/raichuu-tail-slap-sticker-sheet__replayed-addl-text.lds`

Its CDOC SHA-256 is
`301f4a16f3fb7879245caa9b79d49ea79f6dc4f2750c398beb185b94909cdf6d`,
which is byte-identical to the GUI-created reference CDOC. This is a confirmed
replay of the document-data insertion.

The replay deliberately retains the base `PREVIEW` member. Its preview is
therefore stale and differs from the GUI reference. Opening this derivative in
LDS was the required validation: the user opened the derivative, confirmed
that `CODEX IS AWESOME!!!` appeared, and saved it as
`raichuu-tail-slap-sticker-sheet__replayed-addl-text_and-then-saved-from-lds.lds`.

This produces a decisive result:

- saved CDOC: byte-for-byte identical to both the replay and the original
  GUI-created reference (same 7,063,160-byte payload and SHA-256);
- saved PREVIEW: byte-for-byte identical to the original GUI-created reference
  (517,573 bytes, SHA-256 prefix `45c9beb0844346767019`);
- the replay's old base preview was replaced by LDS during save.

The insertion is therefore **confirmed structurally accepted by LDS** for this
base/reference pair. No claim of general LDS writing follows yet, but a stale
`PREVIEW` is now known to be safely regenerable by LDS rather than a blocker.

## Append-stream interpretation

For this controlled pair, the evidence strongly supports CDOC behaving as a
sequential, marker-delimited record stream: the entire existing CDOC prefix,
including document/layer header data and all prior object data, is unchanged;
the new object is inserted just before the unchanged 28-byte final terminal
record. No front-of-file count, offset table, or existing-object index was
updated in this addition. The inserted region itself includes the bridge and
termination records necessary to continue the stream.

### Record marker `AD 9C 4E 1E`

`AD 9C 4E 1E` is best described as a **record magic/sentinel**, not as text,
a length, or a checksum. It has the numerical forms `0x1E4E9CAD` (when read
little-endian) and `0xAD9C4E1E` (big-endian), neither of which has an
interpretable ASCII representation.

It is fixed across every inspected CDOC, so it cannot be a per-record checksum
or an offset. In the controlled four-text fixture it appears 29 times; in the
Raichuu reference it appears 98 times. Most occurrences have the shape:

```text
AD 9C 4E 1E | 00 00 00 00 | <u32 record type> | <u32 payload length> | ...
```

For example, observed type values include `100` (object/transform-like), `11`
(the confirmed vector-path payload), and `14` (settings/text-like). A few
header and terminator records use a nonzero second word, so it is not yet safe
to assert one universal record-header grammar. The evidence does establish the
marker as the framing signal used by the CDOC serializer/parser.

This is not yet proof that *all* LDS documents lack indices—some record may
hold relationships or an index within the stream, and other operations could
update it. It is, however, confirmed that adding this object required no
observable update outside the append position in this real sticker-sheet
document.

## Implication

For this exact base fingerprint, we can now construct an LDS whose document
data is exactly the same as the UI-generated “add text” reference, without
copying the reference archive itself. Generalizing requires identifying which
parts of the insertion depend on target document/layer state and generating
the vector path for a new phrase or position.

## Pragmatic variable-label strategy

For the near-term requirement, do **not** build `PAGE 01` through `PAGE 50`
from individual digit paths. Although the ASCII corpus makes that eventual
approach feasible, it would require solving glyph ordering, advances, bounds,
and text-object metadata first.

Instead, use LDS itself as a precompiler: create a controlled label palette
containing complete GUI-generated text objects for the exact values needed:

- `PAGE 01` through `PAGE 50`;
- `POSITION 1` through `POSITION 9`.

Each template must use the intended final font, style, color, page type, and
fixed final position. The writer will select a *complete* known-good object
insertion for each requested label and append it, rather than synthesize a
string or individual glyphs. This is 59 small templates, but it removes the
highest-risk unknown from the first useful production capability.

The most useful input is therefore two GUI-created palette files based on the
same sheet/document family as the intended targets: one with all 50 page
labels and one with all 9 position labels. They may overlap at their final
target positions; overlap is acceptable because the files are a template
corpus, not final artwork. A simple scripted construction is ideal. We will
then map each literal value to its complete marker-delimited object block and
test whether its identity/relationship fields can be safely freshened or are
already append-safe across the selected document family.

### PAGE palette normalization experiment

The user supplied a page-label palette with `PAGE 1` through `PAGE 40`, one
per line. It established a regular coordinate series: every object has X
`26.870121` mm and the Y anchors start at `15.117813` mm, increasing by exactly
`6.35` mm per label.

`src/ldsqoirev/page_palette.py` is a deliberately fixture-scoped mutator that
normalizes each PAGE label to the first label's Y. For each object after
`PAGE 1`, it changes the six confirmed dependent Y/bounds floats in its
type-100 record and the type-11 path-anchor Y; the path commands are local, so
their glyph geometry is untouched.

It produced
`docs/research/artifacts/2026-08-30/raichuu-tail-slap-sticker-sheet__with-pages-normalized-to-one-line.lds`.
All 40 resulting type-100 translations and type-11 anchors read
`15.117813` mm. The CDOC has the same length and only 1,076 bytes differ from
the source. Its PREVIEW intentionally remains unchanged/stale pending an LDS
open-and-save validation.

The user also supplied a `POS 1` through `POS 9` palette. It has the identical
record pattern and `6.35` mm row increment, but a fixed X of `45.920116` mm.
The normalizer was generalized to accept an ASCII prefix and produced
`docs/research/artifacts/2026-08-30/raichuu-tail-slap-sticker-sheet__with-positions-normalized-to-one-line.lds`.
All nine object translations and path anchors now read Y `15.117813` mm. This
output likewise requires an LDS open-and-save validation to refresh its stale
preview.

## Experimental `ldsedit` label API

`src/ldsedit/__init__.py` now provides a deliberately scoped, template-backed
API using the normalized PAGE and POS palettes:

```python
import ldsedit as edit

edit.read(input_path)
edit.attach_page(27)
edit.attach_pos(8)
edit.save(output_path)  # output must not already exist
```

It also supports the fluent equivalent:

```python
edit.read(input_path).attach_page(27).attach_pos(8).save(output_path)
```

The module does not create text or paths. It harvests the selected complete
type-100/type-11/type-14 object sequence from the controlled palette, assigns
fresh sequential record IDs, joins multiple objects with the measured bridge
records, and splices the result into the target CDOC's final terminal record.
It rejects unavailable numbers and will not overwrite output.

An initial derived test was created from the clean Raichuu sticker-sheet base:
`docs/research/artifacts/2026-08-30/raichuu-tail-slap-sticker-sheet__page-27_pos-8__experimental.lds`.
It contains literal `PAGE 27` and `POS 8`, with fresh object IDs 80 and 85
respectively. Its PREVIEW remains stale pending LDS-open validation. This is
the first test of selecting a non-first PAGE object and combining PAGE with
POS; it must be opened and saved in LDS before support is promoted beyond an
experimental claim.

The first generated PAGE-27/POS-8 trial was rejected by LDS. Diagnosis found
that the API had mistakenly derived its initial bridge from an earlier image
object in the palette (`0x3F6`) rather than from the first PAGE object
(`0x3FC`). The rejected derived file was removed. The extractor now scopes that
bridge to the requested label prefix, and the replacement test has the
expected `0x3FC` type-3 bridge, fresh IDs 79--88, and the unchanged final
terminal record.

That replacement was also rejected. Comparing it with the known-good single
GUI text insertion found a second omission: every inserted object must have a
32-byte `0x3FC` type-4 closing record before the final terminal record. The
API now adds this record. Its resulting single-label tails exactly match the
known-good grammar:

```text
type-3 bridge (ID 79)
+ type-100 / type-11 / type-14 / type-14 object records (IDs 80--83)
+ type-4 close (ID 79)
+ final terminal record (ID 1)
```

The regenerated isolated validation files are:

- `...__page-27-only__experimental.lds`;
- `...__pos-8-only__experimental.lds`.

The combined PAGE-27/POS-8 file was regenerated using a type-4 close plus a
type-3 bridge between objects, but it should not be retested until the two
isolated files are accepted. The API remains experimental until that succeeds.

The user opened both regenerated isolated files on 2026-08-30 and confirmed
that LDS accepted each one. This confirms the module can select and attach a
non-first complete template independently from both supplied palettes:

- `PAGE 27` at the normalized PAGE location;
- `POS 8` at the normalized POS location.

The only unvalidated API operation remaining is combining two newly attached
objects in one output. The regenerated combined file has the measured
`type-4 close → type-3 bridge` join sequence and is ready for that final
structural validation.

The user opened the regenerated combined PAGE-27/POS-8 file and confirmed it
worked. The first complete `ldsedit` workflow is therefore **confirmed** for
the supported Raichuu sticker-sheet family: select a non-first PAGE template,
select a non-first POS template, assign fresh IDs, append both records, and
have LDS render/accept the resulting document. Saving in LDS refreshes the
otherwise stale PREVIEW member.

### Self-contained extracted template source

The runtime editor no longer depends on the two full palette `.lds` files.
`tools/build_ldsedit_templates.py` harvests only the selected object bodies,
the append bridge, and the inter-object separator, and generates
`src/ldsedit/_template_data.py`. That file is a reviewable Python dictionary
of 51 Base64-encoded, zlib-compressed strings keyed directly by values such as
`PAGE 27` and `POS 8` (plus `__bridge__` and `__separator__`). `ldsedit`
decodes the selected value at runtime; it does not access anything under
`docs/research/artifacts`.

A regression check confirmed that the Base64-template API produces a CDOC
byte-for-byte identical to the already LDS-validated PAGE-27/POS-8 combined
output. The currently bundled corpus is PAGE 1--40 and POS 1--9; PAGE 41--50
can be added when their palette records are supplied.
