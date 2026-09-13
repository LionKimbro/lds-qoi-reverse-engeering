Create a new, separate project focused on reverse engineering the Leonardo Design Studio (.LDS) file format.

Project objective

The goal is not to completely document every part of LDS. The goal is to gather enough reliable structural knowledge to support three practical editing operations:

1. Replace embedded PNG artwork.
2. Replace text in drawn text items.
3. Replace the color of drawn text items.

The project should prioritize evidence, controlled experiments, reversible tooling, and incremental understanding over premature claims of a complete format specification.

What is currently understood

An `.lds` file appears to be a ZIP archive. In the sample file examined so far, the archive contained two members:

- `CDOC`
- `PREVIEW`

`PREVIEW` appears to be a preview or rendered-image member, but its exact relationship to `CDOC` has not yet been established.

`CDOC` is a binary document-content member. Its complete internal format is not known. It contains binary structures and at least one embedded QOI image stream.

Important confirmed QOI facts

The QOI streams can be recognized by the four-byte magic signature:

    qoif

A QOI header consists of:

- 4-byte magic: `qoif`
- 4-byte big-endian width
- 4-byte big-endian height
- 1-byte channel count: 3 or 4
- 1-byte colorspace: 0 or 1

The pixel instruction stream follows the header. The stream produces exactly:

    width × height

pixels.

A valid QOI stream ends with the required eight-byte marker:

    00 00 00 00 00 00 00 01

Therefore, a QOI stream can be located inside `CDOC` without knowing its enclosing LDS field structure:

1. Search for `qoif`.
2. Parse the QOI header.
3. Decode instructions until the declared number of pixels has been produced.
4. Verify the eight-byte end marker.
5. The resulting byte range is the exact QOI stream boundary.

This means the embedded QOI itself is self-delimiting, at least at the QOI layer.

Sample-file observations

The known sample LDS file was:

    tarot_umbreon_50cyan_50contrast_-10bright.lds

It was a ZIP archive with:

- `CDOC`: approximately 2.1 MB uncompressed
- `PREVIEW`: approximately 536 KB uncompressed

The examined `CDOC` contained one valid QOI stream:

- offset: `0x129F`
- dimensions: `832 × 1248`
- channels: 4, RGBA
- colorspace: 0
- encoded size: approximately 2.07 MB

The bytes immediately surrounding the QOI appear to contain other binary fields, but their meanings are not yet known.

A naive experiment replaced the embedded QOI with a newly encoded QOI generated from a PNG with different dimensions. The resulting ZIP remained readable by our own extractor, but Leonardo Design Studio did not successfully accept or display the result. This suggests that one or more of the following may exist:

- additional image-dimension metadata outside the QOI header;
- object bounds or transform metadata;
- indexes or references;
- checksums or hashes;
- length fields;
- document-level consistency data;
- a required relationship between `CDOC` and `PREVIEW`;
- another undocumented validation rule.

Do not assume that the failure proves an index exists. Determine this experimentally.

Reverse-engineering strategy

Build tooling that can compare controlled LDS files byte-for-byte and structurally.

The strongest evidence should come from LDS files that differ in exactly one intentional way. Ask the user to create fixture files such as:

- one object versus two objects;
- one image at different pixel dimensions;
- the same image placed at different X/Y positions;
- the same image with different scale;
- rotated versus unrotated image;
- flipped versus unflipped image;
- different opacity;
- different brightness, contrast, or color adjustments;
- one text item with different text;
- one text item with a different font size;
- one text item with a different font;
- one text item with a different text color;
- one text item with different alignment;
- one text item moved to a different position;
- hidden versus visible item;
- deleted item versus empty item;
- one text item versus two text items;
- a document with the same visible result but different object organization.

For every fixture, collect:

- original LDS file hash;
- ZIP member names;
- ZIP compression methods;
- member sizes and compressed sizes;
- `CDOC` and `PREVIEW` hashes;
- all `qoif` signature offsets;
- all valid QOI boundaries;
- QOI dimensions, channels, colorspace, and encoded lengths;
- byte differences between paired files;
- contiguous changed regions;
- repeated patterns;
- candidate length fields;
- candidate offsets or pointers;
- candidate text encodings;
- candidate color encodings;
- candidate floating-point, fixed-point, or integer coordinate values.

Develop comparison tools that can answer questions such as:

- Does changing image dimensions alter only the QOI header, or also surrounding fields?
- Does changing object position alter a small repeated coordinate field?
- Does changing text alter a UTF-8, UTF-16, UTF-16LE, UTF-16BE, or other encoded region?
- Are text lengths stored explicitly?
- Are string fields null-terminated, length-prefixed, padded, or enclosed by delimiters?
- Does changing text length shift later content, or does it occupy a fixed-size field?
- Does changing text color alter four bytes, three bytes, floating-point values, or a larger color structure?
- Are colors stored as RGBA, ARGB, BGRA, premultiplied values, floats, or normalized values?
- Does `PREVIEW` change when only `CDOC` content changes?
- Is `PREVIEW` required for Leonardo to open the document?
- Does Leonardo regenerate `PREVIEW` when the file is opened?
- Are there checksums or hashes tying `CDOC`, `PREVIEW`, or internal records together?
- Are offsets absolute, relative to a segment, or absent?
- Are records delimited, length-prefixed, indexed, or a mixture?

Practical editing targets

The project should eventually support narrow, evidence-backed mutations:

1. Image replacement

   Replace one embedded QOI stream with a QOI stream encoded from a supplied PNG. Preserve the PNG’s native dimensions unless experiments prove that LDS requires another behavior. Rebuild the enclosing binary structures if necessary. Do not resize silently.

2. Text replacement

   Locate a specific drawn text item and replace its text while preserving its surrounding object properties, position, font, and style. Handle changes in text length safely.

3. Text-color replacement

   Locate a specific drawn text item and replace only its color representation while preserving the text and other properties.

Do not implement these mutations based solely on byte-pattern coincidence. Each mutation should be supported by fixture comparisons and regression tests.

Safety requirements

- Never modify the original LDS file.
- Never modify the original PNG file.
- Always write experimental results to a new LDS path.
- Reject an output path equal to the source path.
- Preserve unrelated ZIP members whenever possible.
- Preserve `PREVIEW` unchanged initially unless experiments demonstrate that it must be regenerated.
- Keep a byte-level backup or source hash for every experiment.
- Clearly distinguish confirmed facts, strong inferences, weak hypotheses, and unknowns.
- Do not claim that a format feature is understood until it has been reproduced across multiple controlled fixtures.

Expected deliverables

- A small Python research toolkit.
- LDS/ZIP inspection commands.
- CDOC hex and binary-difference inspection tools.
- QOI detection, decoding, and encoding tools.
- Fixture-comparison reports.
- A growing evidence log.
- A hypotheses document with confidence levels.
- Reproducible experiments.
- Regression tests for every confirmed structural discovery.
- Eventually, narrowly scoped image, text, and text-color replacement operations.

Use simple, inspectable procedural code. Keep the project distinct from the existing LDS QOI Extractor application. The existing extractor may be reused as a reference for ZIP handling and QOI parsing, but this new project should be organized as a reverse-engineering laboratory rather than as a finished end-user extractor.