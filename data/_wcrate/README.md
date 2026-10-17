# With-crate AI_READI results (#5042)

From 2026-08-12 (#540) to 2026-10-14 (#5042), AI_READI's document bundle, `data/preprocessed/concatenated/AI_READI_preprocessed.txt`, included the AI-READI release-3.0.0 RO-Crate as one of its source documents (`ro_crate_metadata`). No other project's document bundle contained a crate.

On 2026-10-14 the owner ruled that generation runs read no RO-Crate content. Crates are the input of the separate with-crate and crate-only arms only. #5042 removed the crate from AI_READI's corpus. The other ten documents are byte-identical, and the bundle's md5 went from `d22b61a9…` to `1a58ad7b…`; see `bundle_hash_history` in `data/preprocessed/source_manifest.yaml`.

This folder keeps the results of every AI_READI record generated from a bundle that contained the crate. That is 30 records:
- 26 under `claudecode_agent`: v4 to v7, 2026-08-13 to 2026-09-01;
- 4 under `claudecode_api`: v8, 2026-09-04f rep1 and 2026-09-04g rep1–3.

For each record the folder holds four byte-identical copies, laid out as `AI_READI/<method>/<label>/`:
- the full datasheet (`AI_READI_d4d.yaml`);
- the derived core (`AI_READI_d4d_core.yaml`);
- the provenance record;
- the reconciliation report.

`index.yaml` gives, for each copy, the original path, sha256 and size, and the bundle md5 its record read.

**The originals stay where they were**, under `data/d4d_concatenated/`, together with their receipts, reviews, intermediates and evaluations. They remain the evidence, and their provenance records already pin the bundle they read.

**This folder sits outside `data/d4d_concatenated/` on purpose.** `runs.discover()` and the corpus tests walk that tree for `*_provenance.yaml`, so copies inside it would be counted as duplicate records. Nothing in the code reads this folder.

To check a copy against its original:

```bash
shasum -a 256 data/_wcrate/AI_READI/claudecode_api/2026-09-04g_claude-opus-5-api-generic-v8_rep2/AI_READI_d4d.yaml \
             data/d4d_concatenated/claudecode_api/2026-09-04g_claude-opus-5-api-generic-v8_rep2/AI_READI_d4d.yaml
```
