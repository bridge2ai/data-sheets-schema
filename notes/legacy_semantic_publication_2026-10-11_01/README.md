# Legacy semantic TSV publication evidence, 2026-10-11

This directory retains the exact outputs of five successful CLI publications from producer commit `ffc4ca922723caa620af2e32a31ad538bc5a5ac9` (tree `be88ffebf9c55bcf28d6602d66414ba2725df6fe`). The release label is `2026-10-11_legacy-semantic-default-4932-v1`; the method is `legacy_semantic_tsv` and the disposition policy is `root_default_route_dispositions_v1`.

The five input forms are CHORUS, VOICE, CM4AI reduced, VOICE provenance, and CM4AI original. They are software input forms, not five independent datasets. Each form has its exact Dataset YAML, complete route-disposition sidecar, report, and raw input JSON. CM4AI original retains its complete 12,242,926-byte source and 13,033,881-byte sidecar, including evidence outside the projected Dataset. No field, source text, or repeated list unit was removed to reduce these files.

The merged implementation in PR #4938 and the saved publication run support the bounded software contract in #4932. The five actual CLI processes exited successfully, with no forced process cleanup. The completed independent audit, 22 publication controls, dual-runtime 2,273-case validation receipts, merge/CI evidence, and actual plugin review are retained under `provenance/`. The earlier publication03 verifier failure is also retained: its first CLI exited successfully, but the verifier rejected different YAML escaping and wrapping. The corrected serialization oracle was independently specified from the unchanged CLI contract (#4943); prior failed receipts have not been relabeled as passes.

## Local verification and relocation

From any checkout containing this directory, run:

```sh
python3 -I -B notes/legacy_semantic_publication_2026-10-11_01/verify.py --repository . --release notes/legacy_semantic_publication_2026-10-11_01
```

The stdlib-only verifier checks every listed artifact's size and SHA-256, the five full raw-source/sidecar/Dataset joins, and the copied schema and mapping snapshots. It also joins the producer and label to the actual publication receipt and checks the historical-to-local aliases addressed by #4944. It does not regenerate records, rerun schema validation, or authenticate scientific assertions. A Git commit/review binds the manifest; the manifest is not a cryptographic signature against coordinated alteration of both evidence and its declared hashes.

`manifest.json` uses repository-relative paths with `path_base: repository_root`. `relocation-index.json` maps the old execution/acquisition locators to these local artifacts, including original-input aliases. The original sidecars, reports, and execution receipts retain their historical absolute paths byte for byte. Those old paths are retrospective provenance, not locations that must exist after relocation. Exact schema and semantic mapping snapshots are included so verification does not depend on later changes to the current repository's schema or mapping table. Log bytes are unchanged, but their copied filenames end in `.txt` so repository ignore rules do not hide them.

The byte-exact historical publisher harness and configurations are evidence, not a turnkey portable executor. Their old interpreter, checkout, and prior evidence paths remain historical. The bound enabled configuration is stored outside the disabled harness directory. Some historical receipts reference larger prior replay bundles retained outside this release; the current five full input/sidecar sets are complete. The standalone verifier uses only this directory. The package-builder controls and metadata-validation receipt provide separate relocation/integrity checks, not new product runs.

## Scope retained

This release adds evidence files and a local metadata verifier. It does not register a new generation method, replace `rocrate_static_map` or `rocrate_mapped`, or rerender figure 09. Existing figure 09 remains a retrospective comparison against the declared historical generic-v8 records. Its limitations and original denominators remain in force: the 136 static rules and 81 legacy ranking rows are different scopes; retired rows are not coverage. Whole-text retention does not establish `exactMatch` or lossless mapping, and this publication does not adjudicate scientific roles, fidelity, or adoption.

The producer commit above remains distinct from the later commit that delivers this evidence directory. Parent issues #4594, #2915 and #4385 retain their broader generation, coverage, and comparison obligations. Held adoption/scientific decisions are unchanged. This directory contains no native-owner diagnostic evidence.
