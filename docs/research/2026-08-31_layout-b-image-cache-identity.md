# Layout B image-cache identity

**Date:** 2026-08-31

## Result

LDS caches the seven linked Layout-B image placements across documents within a
running process. The cache identity is an 8-byte token that occurs once in
each of the eight image groups in the audited Flareon source template.

The source token is:

```text
1d7c993515415832
```

The exact field name in LDS is not yet known; it is called the *shared image
cache key* in this repository. It is an experimentally established behavior,
not an assertion about LDS's internal terminology.

## Controlled collision experiment

Two files were generated from the same template and deliberately retained the
same key, while their sole QOIs contained different artwork:

- `0072__rendered-scrafty__shared-image-key-control.lds` — Scrafty QOI;
- `0082__rendered-weedle__same-image-key-test.lds` — Weedle QOI.

Both contain exactly one QOI and the source key exactly eight times.

Observed behavior, without saving either file:

1. In a fresh LDS process, opening 0072 displayed eight Scraftys.
2. Opening 0082 in that same process displayed Weedle in slot 1 and cached
   Scraftys in slots 2–8.
3. Restarting LDS and opening only 0082 displayed eight Weedles.

This establishes that a copied key causes a cross-file process-local collision.

## Generator rule

Every generated sheet must receive one cryptographically random 8-byte key,
written identically into all eight image groups. The eight placements belong
to one image resource and therefore share the key *within* a sheet; different
output sheets must never share it.

`src/ldsqoirev/layout_b_images.py` now discovers the key structurally rather
than hard-coding the Flareon value: it requires one type-26 envelope followed
by type-10, plus seven type-25 envelopes followed by type-14. In each 40-byte
envelope the final eight bytes must agree; those eight locations receive a new
random value. The one-QOI output and its eight display transforms are otherwise
generated as before.

## Operational validation rule

For any generated LDS, validate by opening it in a fresh LDS process. Do not
save a document while investigating a cache-contaminated session, because LDS
may materialize stale data into the document.
