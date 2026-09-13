# Experiment index

Every newly delivered LDS experiment uses a four-digit prefix.  Numbers are
monotonic and allocated in blocks of ten so related follow-ups can be grouped
without making the order ambiguous.  Source files are never renamed or
modified; a numbered entry may point to an external source path.

| Prefix | Status | Purpose / file |
|---|---|---|
| 0000 | source | `C:\lion\code\stickerdb\.stickerdb\exports\sumi-flareon-sticker-sheet__sticker-sheet.lds` — designated black-label Flareon template; one QOI, visually audited as Flareon. |
| 0001 | source | `C:\lion\code\stickerdb\.stickerdb\exports\weedle__sticker.png` — Weedle input artwork, hash audited. |
| 0010 | superseded | One-QOI direct replacement from 0000. It proved only the upper-left slot follows the inline QOI; LDS rendered Lillipup in the other seven. |
| 0020 | evidence only | LDS-saved mixed Weedle document. It contains two QOIs and proves the later seven slots use separately resolved linked-image state. |
| 0030 | validated after LDS restart | One-QOI shared-reference probe. After restarting LDS (which cleared stale image state from the prior session), it rendered Weedle in all eight slots. The earlier Lillipup observation was session-state contamination, not a persistent file result. |
| 0040 | source | Numbered byte-for-byte copy of the designated Flareon source template for the independent Scrafty experiment. |
| 0041 | source | Numbered byte-for-byte copy of `scrafty__sticker.png`. |
| 0042 | validated in fresh LDS | One-QOI direct Scrafty render from 0040 + 0041. Its decoded QOI pixels exactly match 0041. A pre-existing LDS process showed slot 1 as Scrafty and slots 2–8 as stale Flareon; a fresh LDS process showed all eight as Scrafty. This establishes process-local renderer cache contamination for linked image objects. |
| 0050 | source | Numbered byte-for-byte copy of 0040 for the cache-key probe. |
| 0051 | source | Numbered byte-for-byte copy of 0041 for the cache-key probe. |
| 0052 | current validation | One-QOI Scrafty render from 0050 + 0051, then the shared 8-byte candidate image-cache token was changed in all eight image groups: `1d7c993515415832` → `68e880490130374a`. |
| 0060 | source | Numbered byte-for-byte copy of the Flareon source for the cross-file cache-identity test. |
| 0061 | source | Numbered byte-for-byte copy of the Weedle input artwork. |
| 0062 | current validation | One-QOI Weedle render from 0060 + 0061, with a distinct shared candidate image-cache token in all eight image groups: `1d7c993515415832` → `806b4102e878e296`. |
| 0070 | source | Numbered Flareon source copy for the deliberate shared-identity control. |
| 0071 | source | Numbered Scrafty input copy for the deliberate shared-identity control. |
| 0072 | control | One-QOI Scrafty sheet. It retains the original shared candidate token `1d7c993515415832` exactly eight times. |
| 0080 | source | Numbered Flareon source copy for the deliberately colliding Weedle sheet. |
| 0081 | source | Numbered Weedle input copy for the deliberately colliding Weedle sheet. |
| 0082 | current validation | One-QOI Weedle sheet. It deliberately retains the same token as 0072, `1d7c993515415832` exactly eight times, while its QOI is Weedle. Open 0072 then 0082 in one LDS process; then restart LDS and open only 0082. Do not save either file during the test. |
| 0100 | final demonstration | Charmeleon Layout B generated directly from the Sumi Flareon template. One QOI; fresh shared image-cache key `5b2fe3107b7677c6`. |
| 0101 | final demonstration | Scrafty Layout B generated directly from the Sumi Flareon template. One QOI; fresh shared image-cache key `ebc8452e71d083bc`. |
| 0102 | final demonstration | Weedle Layout B generated directly from the Sumi Flareon template. One QOI; fresh shared image-cache key `d32d811dd0215dfc`. |
| 0103 | final demonstration | Lillipup Layout B generated directly from the Sumi Flareon template. One QOI; fresh shared image-cache key `c59f49ca663ba4d3`. |

## Naming rule

Use `NNNN__short-semantic-description.ext`, for example:

`0030__weedle__one-qoi-shared-reference__experimental.lds`

The next related Weedle probes would be `0031`, `0032`, and so on. A new
experiment family starts at the next ten (`0040`, then `0050`). Files without
a numeric prefix are legacy artifacts; consult this index instead of treating
their filenames as ordering information.
