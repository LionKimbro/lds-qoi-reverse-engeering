# Text-length fixtures

**Date:** 2026-08-28

## Fixtures

User-provided text-only LDS files in `lds/`:

| Fixture | Literal drawn text | Text bytes |
| --- | --- | ---: |
| `text-size-01-AAA.lds` | `AAA` | 3 |
| `text-size-02-BBBBBBBBBBBBBBBBBBBBBBBBBBBBBB.lds` | 30 `B` characters | 30 |

Both contain a single centered Arial text item with no embedded QOI streams.

## Confirmed: text value is UTF-8 BOM-prefixed and length-prefixed

Each CDOC contains the text value literally as:

```text
EF BB BF + UTF-8 text bytes + 0D 0A
```

Immediately 20 bytes before the BOM is a little-endian 32-bit length field:

```text
AD 9C 4E 1E  00 00 00 00  0E 00 00 00  [payload_length]  09 00 00 00
C9 00 00 00  00 00 00 00  00 00 00 00  EF BB BF ... 0D 0A
```

| Fixture | Stored `payload_length` | Calculation |
| --- | ---: | --- |
| `AAA` | 8 | 3 BOM bytes + 3 text bytes + 2 CR/LF bytes |
| 30 `B`s | 35 | 3 BOM bytes + 30 text bytes + 2 CR/LF bytes |

This is **confirmed** for UTF-8 ASCII text. A future non-ASCII fixture is
needed to verify that the field is a byte length rather than a character count.

## Confirmed: text content affects a large preceding rendered-data region

The single-text CDOC sizes differ dramatically:

| Fixture | CDOC bytes |
| --- | ---: |
| `AAA` | 1,413 |
| 30 `B`s | 31,020 |

The terminal Font/text configuration has the same shape in both files, but
the `FontSize=` setting occurs at `0x04bc` in the `AAA` file and `0x7848` in
the 30-B file. The material preceding it is therefore content-dependent.

This strongly indicates that LDS serializes substantial rendered glyph outline,
path, or equivalent geometry data in addition to the literal text string. It
means changing only the literal text and its length field is not yet safe: LDS
may retain stale drawn geometry, reject the document, or regenerate it on open.

### Strong evidence of per-glyph serialized geometry

Immediately before the terminal `FontSize=` record, both fixtures contain one
record with the marker `AD 9C 4E 1E`, type-like field `0B 00 00 00`, and a
little-endian payload-length field:

| Fixture | Payload bytes | Exact per-character division |
| --- | ---: | --- |
| `AAA` | `0x02b2` = 690 | 690 / 3 = **230 bytes per A** |
| 30 `B`s | `0x763e` = 30,270 | 30,270 / 30 = **1,009 bytes per B** |

The payload is not visibly separated into three marker-delimited A records;
it appears to be a single compact collection of float-heavy drawing data.
Nevertheless, the exact per-glyph divisibility and the radically different
per-glyph sizes are strong evidence for serialized vector/path-like glyph
geometry rather than a bitmap snapshot. Different glyphs clearly require
different amounts of stored geometry.

## Added transition and glyph-corpus fixtures

The user added the following fixtures after the initial pair:

| Fixture | Text bytes | Type-`0x0B` payload bytes |
| --- | ---: | ---: |
| `text-renders-02-A.lds` | `A` (1) | 258 |
| `text-renders-03-AA.lds` | `AA` (2) | 474 |
| `text-renders-04-AB.lds` | `AB` (2) | 1,266 |
| `text-renders-01-QWERTYUIOPASDFGHJKLZXCVBNMqwertyuiopasdfghjklzxcvbnm.lds` | 52 letters | 24,594 |

The transitions are especially informative:

- adding a second `A` grows the payload by **216 bytes**;
- using `B` as the second glyph instead grows it by **1,008 bytes**.

This confirms that the serialized drawing payload is strongly glyph-dependent.
Direct binary alignment does not produce simple copy-paste glyph slices: because
the text is centered, changing the string also changes positions throughout
the composite geometry. The long alphabet fixture is therefore valuable as a
glyph corpus, but extracting clean glyph definitions will require parsing the
internal path-command format or adding non-centered/aligned transition fixtures.

## Drawing-command encoding discovered in the attempted left-aligned fixtures

The user supplied `glyph-left-01-A.lds`, `glyph-left-02-AA.lds`, and
`glyph-left-03-AB.lds`. Their primary text-object anchors are identical:
`(150.77156, 151.45932)` mm. However, their PREVIEW renders remain centered,
and the initial A path coordinates move when the string changes. Thus these
files are still center-aligned in the relevant LDS drawing state; a truly
left-aligned rebuild would remove that coordinate shift.

Despite that, the type-`0x0B` payload has a newly confirmed internal shape:

```text
30-byte header
N × 12-byte drawing commands
```

The first four header bytes are a little-endian command count. Each command is
interpretable as two little-endian float values followed by a 32-bit command
code. The observed counts and payload sizes agree exactly:

| Text | Command count | Payload bytes |
| --- | ---: | ---: |
| `A` | 13 | 30 + (13 × 12) = 186 |
| `AA` | 26 | 30 + (26 × 12) = 342 |
| `AB` | 76 | 30 + (76 × 12) = 942 |

This is **confirmed** as a byte-level record layout. The command-code meanings
are not yet decoded, though observed values (`1`, `2`, `3`, `16`, and
high-bit variants such as `129`, `161`, `163`) are consistent with path
operations and termination/flags. `A` uses 13 commands; the `B` contribution
in `AB` adds 63 commands.

### Alignment semantics and clean matched-anchor control

User clarified LDS alignment behavior: changing an already-centered text item
to left alignment does not move existing glyphs, but changes the direction in
which subsequently added text is laid out. A fresh series was started from a
left-aligned state. The initial `A` had a mismatched `(0, 0)` anchor, then was
correctly rebuilt by saving the matched `AB` fixture and editing it to `A`.

The final control trio has identical anchors and `FontAlign=0`:

```text
glyph-started-left-01-A.lds   A    anchor (151.61499, 151.49849) mm
glyph-started-left-02-AA.lds  AA   anchor (151.61499, 151.49849) mm
glyph-started-left-02-AB.lds  AB   anchor (151.61499, 151.49849) mm
```

In `AA`, the first (left) A outer contour is an exact 9-command byte sequence
match for the single-A outer contour, at command index 9. Its inner-triangle
contour has the same float geometry at command index 22, with only the final
termination flag differing. LDS stores contours grouped by drawing pass rather
than keeping all commands for a glyph contiguous: the right A outer contour is
first, then the left A outer contour, followed by their inner contours.

In `AB`, the A outer contour is recognizably commands 31--39 and the inner
contour commands 56--59, but has tiny `+0.0001`-scale float differences. This
is consistent with a composite-path recalculation and does not invalidate the
decoded command structure.

## ASCII glyph corpus and automatic wrapping

The user supplied a left-aligned ASCII corpus at the matched anchor position:

| Fixture | Literal text bytes | Path commands |
| --- | ---: | ---: |
| `glyph-ascii-01-punct-digits.lds` | 31 | 1,047 |
| `glyph-ascii-02-upper.lds` | 32 | 939 |
| `glyph-ascii-03-lower.lds` | 31 | 1,211 |
| `glyph-ascii-04-space.lds` (`A A`) | 3 | 26 |

The upper- and lower-case strings visibly wrap in LDS, but their literal CDOC
text values contain no inserted newline. This is therefore automatic layout
wrapping, not a separate newline/glyph encoding. Their left-aligned anchors and
`FontAlign=0` settings remain unchanged, so they are still useful for the
glyph corpus and provide future wrap-layout evidence.

`A A` has exactly 26 path commands, the same as `AA`. Thus space adds no path
contours. Comparing matching A contour start coordinates shows the right-hand
A moves from X `3.240` in `AA` to X `3.897` in `A A`, while the left A remains
at X `1.570`. The observed space advance is therefore **0.657 path-coordinate
units** in this Arial fixture.

### Confirmed: type-0x0B paths reconstruct into the rendered glyph outlines

The project’s read-only `text_paths` decoder exports the type-`0x0B` command
stream as SVG using this observed mapping:

- low code bits `0`: move/start;
- low code bits `1`: line;
- code sequence `2`, `3`, `3`: cubic Bézier control 1, control 2, endpoint;
- high bit `0x80`: close current subpath.

Derived SVGs were rasterized and visually checked against the corresponding
LDS previews:

- `glyph-started-left-01-A` reconstructs as a clean outlined `A`, including
  its triangular counter and crossbar;
- `glyph-started-left-02-AB` reconstructs as `AB`, including the curved
  counters of `B`.

This is **confirmed** for the supplied Arial fixtures. The record is therefore
not a rasterized image: it is directly renderable vector path geometry. The
remaining work for arbitrary text replacement is to source or generate the
correct path commands (and retain LDS’s surrounding record invariants).

## Relationship to coordinate fixtures

The earlier `CODEX IS AMAZING` text-grid fixture had a 6,338-byte record per
text object. These length fixtures demonstrate that this size is not globally
fixed: text-object records can be highly content-dependent. The grid result
still confirms coordinate fields **within that fixture family**, but a generic
text replacement operation will need a way to regenerate or safely update the
content-dependent region.

## Centered text color control: black versus red

The user supplied a controlled pair, both visibly centered and both containing
the literal `COLOR TEST` in Arial at the same nominal size:

- `lds/text-color-01-black.lds`
- `lds/text-color-02-red.lds`

Their previews were extracted and visually checked. They are indeed centered
at the same position. The first analysis incorrectly treated two floats in
the type-`0x0B` payload as an absolute page position; this pair disproves that
interpretation. In the black file, the 388 glyph commands are stored in page
coordinates and the payload origin is `(0, 0)`. In the red file, the commands
are local coordinates and the payload origin is `(144.3971558, 151.4593201)`
mm. Adding that origin to each red command produces the black geometry within
`0.00034` mm (float serialization noise), and every command code is identical.

This provides a useful normalization rule for analysis: the two payload floats
are a **path-space origin/translation**, not invariably a document anchor.
They must be applied before comparing geometry across files.

Outside the path payload, the pair has a particularly clean four-byte color
change at CDOC offset `0x174`:

| File | Stored bytes | 32-bit little-endian value | Observed rendering |
| --- | --- | --- | --- |
| black | `00 00 00 FF` | `0xFF000000` | opaque black |
| red | `00 00 FF FF` | `0xFFFF0000` | opaque red |

This is **confirmed as an ARGB-like packed color field** for this simple text
object (`0xAARRGGBB` when read as a little-endian 32-bit word; byte order in
the file is BGRA). The nearby fields are bounds and path-origin data, so the
exact owning record type still needs naming; however, the byte-level color
mapping itself is now directly controlled and visually validated.

## Next experiments

### Near-term writer objective: add one fixed text object

The agreed intermediate target is a copy-only transformation:

```text
input.lds  ->  input-with-codex-is-awesome.lds
```

It will add a single fixed, newly created text object whose literal value is
`CODEX IS AWESOME!`, before attempting arbitrary text replacement. This scope
is deliberately narrow: supported page size, font/style, and placement can be
fixed initially.

The supplied ASCII corpus contains every visible glyph needed by the phrase
(`A`--`Z`, space, and `!`). It proves availability of the component outlines,
but does not by itself prove how to compose them into a fresh LDS object:
contours are serialized by drawing pass rather than glyph order, and the
surrounding object record includes IDs, bounds, links, and terminators.

The required controlled fixture pair is a base document and the *same document
after one GUI-created `CODEX IS AWESOME!` object is added at a documented
position*. Their CDOC difference will expose the complete insertion delta,
including layer membership and fresh-object metadata. We can then first replay
that insertion into a byte-identical copy of the base document, and only after
an LDS-open validation attempt to port the fixed object to the supported
document family.

1. Obtain that add-one-object control pair, ideally with an otherwise simple
   text-only page and a known, non-overlapping position.
2. Identify all insertion-related CDOC segments, counters, IDs, and object
   references from the pair; write a copy-only experimental inserter that
   refuses any non-matching base fingerprint.
3. Open its output in LDS and compare its preview/save result to the
   GUI-produced reference. Promote the inserter only if this succeeds.
4. Expand from the exact base fingerprint to a narrow document family, then
   investigate deriving the phrase's geometry from the ASCII corpus.
5. Continue same-character-count/different-glyph, repeated-glyph, and
   non-ASCII tests for eventual general text editing.
