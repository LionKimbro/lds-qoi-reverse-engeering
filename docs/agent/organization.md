# Research organization

This repository is organized as a reverse-engineering laboratory for Leonardo
Design Studio (`.LDS`) files. The immediate objective is evidence-backed,
narrow editing support for embedded artwork, drawn text, and drawn-text color;
it is not a speculative complete format specification.

## Documentation locations

- `docs/raw/` contains source material and original project context. Treat its
  contents as reference inputs; do not edit them as part of research.
- `docs/research/` contains durable technical findings about the LDS format:
  fixture observations, experiment reports, confirmed structures, hypotheses,
  and reproduction instructions.
- `docs/agent/` contains process notes for the research agent: organization,
  conventions, decisions about investigative workflow, and lessons about how
  to perform the work safely and reproducibly. It must not be treated as proof
  of a format claim.

`docs/research/artifacts/` is reserved for private/copyrighted artwork inputs,
extracted images, and LDS derivatives. It is intentionally Git-ignored and
must never be committed.

## Evidence conventions

Every format claim should state its confidence level:

- **Confirmed**: reproduced across multiple controlled fixtures or validated by
  a deterministic parser/check.
- **Strong inference**: well-supported by controlled evidence, but not yet
  independently reproduced.
- **Hypothesis**: a testable explanation; never a basis for a mutating tool.
- **Unknown**: not yet investigated or evidence is insufficient.

Research notes should identify the fixtures used, commands or scripts run,
relevant byte offsets/ranges, hashes where practical, and the exact observable
result. Prefer paired fixtures that differ by exactly one intentional change.

## Working rules

- Never alter original LDS or image inputs; experiments write a new output.
- Reject an output path that is the same as its source path.
- Preserve unrelated ZIP members and leave `PREVIEW` unchanged unless evidence
  requires otherwise.
- Record failed experiments as useful negative evidence, including what changed
  and how LDS responded.
- Keep tooling procedural, inspectable, and covered by regression tests once a
  structural behavior is confirmed.
- Distinguish observed bytes from their proposed interpretation. Byte-pattern
  coincidence alone is not sufficient to support a mutation.

## Initial investigation order

1. Inventory existing fixtures and tools without modifying inputs.
2. Inspect LDS ZIP members and locate/validate every embedded QOI stream.
3. Establish byte-level comparison reports for deliberately paired fixtures.
4. Document QOI-adjacent metadata and image-property changes before attempting
   image mutation again.
5. Add controlled text and color fixtures, then identify encodings and record
   layouts before implementing text-oriented mutation.

Each completed experiment should leave both a research note in
`docs/research/` and any reusable workflow guidance in `docs/agent/` when it
would help later investigations.
