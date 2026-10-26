# Native D38 pin alignment — bounded validation, 2026-10-26

Refs #5170 and #4354. The committed checker exited **0** at frozen source **`bea065c9a1070a9dbb08f6a7b2b39523ea4d9337`**. Its result is `positive_projection_and_three_exact_refusals_verified`, with scope **`composed_offline_asset_closure`**. The unchanged evidence is preserved in [native_n2_d38_validation_2026-10-26](native_n2_d38_validation_2026-10-26/).

| Authority | Exact commit |
|---|---|
| Checked native source | `bea065c9a1070a9dbb08f6a7b2b39523ea4d9337` |
| Native source before pin rotation | `fbf885213db040f5cbd19f742cdb7de76fd3382c` |
| Reviewed D38 target | `f73764e0685f436a07e802766e16030572d29a18` |
| Commit that authored the selected D38 asset bytes | `6a0f8acfed6d58fac8747d891b8a05975534a5c5` |
| Historical checker/support recovery source | `db0573d96bb16ee32d3537ea0a9ad0ca607e355a` |

Only `src/data_sheets_schema/native_shared_selection.py` changed in production relative to the native base, with exactly two hash replacements:

| Asset | Previous SHA256 | D38 SHA256 |
|---|---|---|
| `src/download/prompts/d4d_generic_arm_prompt_v10.md` | `95511eeea60e5112c630c28bcc342f132d14efcf0d5485bbf26f3e81a0f4cc99` | `ec081dbb14049449989c56169de7bcd1563076667818c12b78571b5f15acb2db` |
| `.claude/commands/d4d-uniform-rules-v2.md` | `cbf7e9f53e97a1d7dd953507308825e3c835daabcb8f6ee0a6a5dcd8bb9a048f` | `22a553695536a822e9c7ae877663a9b251c889a6637c637e579c5c6e1c855b2e` |

The protected `shared_generation.py`, canonical hash registry and prompt assets were not edited. The installed native checkout intentionally retains its old prompt files; positive validation therefore uses an explicit composition rather than pretending those new assets are installed.

The checker captured **13 assets**: **10 ordinary assets** from a fresh composed resource directory, plus **3 omission-inventory assets** adjacent to the committed native module. Only the two rotated assets came from the reviewed D38 target; their bytes also match the stated asset-authoring commit. It verified every actual read path, captured byte count and SHA256. The complete reviewed R9 excerpt is **4,433 bytes** and appears verbatim **once** in the projected factual rules.

Each negative case produced `ValueError` with the exact expected boundary:

| Case | Exact refusal |
|---|---|
| Stale installed native checkout | `selected native asset bytes changed: .claude/commands/d4d-uniform-rules-v2.md` |
| Composed directory with only the old generic prompt substituted | `selected native asset bytes changed: src/download/prompts/d4d_generic_arm_prompt_v10.md` |
| Composed directory with only the old uniform rules substituted | `selected native asset bytes changed: .claude/commands/d4d-uniform-rules-v2.md` |

The report records unchanged source and observed-file inventory, with `src` Git tree `012ed74ed1d82b1ddc7af93bf909f0f900f12b41`. Imports used Python 3.13.12 with `-S -P -B`, a single declared checkout source root, explicit existing dependency paths without executing site/`.pth` files, and pre/post proof of committed project-source and namespace origins. Installed dependency bytes are not authenticated. Copying these four artifacts and adding this note occurred after validation; no production code changed during preservation.

The actual invocation, from `/private/tmp/d4d-codex-n2-d38-20261026`, was:

```bash
PYTHONPATH=/private/tmp/d4d-codex-n2-d38-20261026/src \
PYTHONPYCACHEPREFIX=/private/tmp/d4d-n2-d38-validation-20261026/evidence/aligned/unused-import-cache \
/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python -S -P -B \
  scripts/adhoc/native_n2_d38_alignment_20261026.py \
  --tree /private/tmp/d4d-codex-n2-d38-20261026 \
  --expect-head bea065c9a1070a9dbb08f6a7b2b39523ea4d9337 \
  --evidence /private/tmp/d4d-n2-d38-validation-20261026/evidence \
  --tag aligned \
  > /private/tmp/d4d-n2-d38-validation-20261026/alignment.log 2>&1
```

That destination is retained evidence; any future repetition requires a fresh destination/tag and its matching fresh unused-cache path. The checker itself was committed before execution, SHA256 `dd713b905bfc89c308fbdea1f98b38202bb21aa3908b1dae45e929ad1c2ee199`. Its exact recovered support helpers and their hashes are listed in the report.

The preserved files were copied unchanged from the invocation's output and verified byte-for-byte:

| Artifact | SHA256 |
|---|---|
| [report.json](native_n2_d38_validation_2026-10-26/report.json) | `a474f8dec69e1eae888ae00436fbddaf8e5ca3fb2e0529304f77404d1c950a8e` |
| [projected-rules.txt](native_n2_d38_validation_2026-10-26/projected-rules.txt) | `c8bc7c9602646f4d7fb93fffcf64fddb8c58ac71f32ce1a85a9484c2024abee7` |
| [reviewed-r9.txt](native_n2_d38_validation_2026-10-26/reviewed-r9.txt) | `d9f7884a03f0480d1ab610118f32850e2d98008fcd67fb51a16a4b7b7ca79a4d` |
| [alignment.log](native_n2_d38_validation_2026-10-26/alignment.log) | `2b1ee3401a608d56906a116f9c87ea45a99b8d00065b0869b82326f1ce9e1dc2` |

This check exercised native asset capture and factual-rule projection only. It did not produce a full instruction, selection registration, execution, canary or provider request. It establishes neither acceptance of an installed target nor full-runtime, context-capacity or scientific-equivalence acceptance. Earlier full-suite results remain evidence for their pre-rotation source and prompts; they have not been transferred to the new D38 prompt by this check.
