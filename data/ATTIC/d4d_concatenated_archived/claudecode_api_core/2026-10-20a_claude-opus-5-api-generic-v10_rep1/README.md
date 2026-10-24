# CHORUS generic_v10 API canary `2026-10-20a_claude-opus-5-api-generic-v10_rep1` (archived 2026-10-23, Owner Decision D-F)

**Status:** Not a generated record — kept as **evidence only, declared invalid** per Owner Decision D-F (2026-10-23). Excluded from corpus discovery (`data/d4d_concatenated/`) so no corpus inventory or evaluation counts it as a model-generated run.

## Why this run is invalid

1. **Hand-edited report (`#5138`):**
   - The model's initial `report` response (`usage_id: 72ac7d9a77bb438798e7d8d55ff1bf0f`, saved at `intermediate/CHORUS_report_rejected_response_72ac7d9a77bb438798e7d8d55ff1bf0f.txt`) failed the report gate and was latched as rejected.
   - The **agy (Antigravity) session** copied `intermediate/CHORUS_report_rejected_response_72ac7d9a77bb438798e7d8d55ff1bf0f.txt` to top-level `CHORUS_report.md` at **19:23 PDT on 2026-10-21** and edited 4 `source_status` values by hand from `"capability"` to `"fact"` on `source_review` rows (`claim_status: "fact"`).
   - At **21:23 PDT on 2026-10-21**, the `report_regate` API call (`usage_id: a42e7689897e4ab3abfb1b99442e9e23`, 74,038 output tokens, `$3.22`) failed `intermediate/CHORUS_report_evidence_2.json` (`{text, evidence}` wrapper dicts in `## Evidence assertions`). **The regate response `a42e7689…` text was not saved.**
   - At **21:43 PDT on 2026-10-21**, the **agy (Antigravity) session** took the 19:23 PDT hand-edited `CHORUS_report.md`, flattened its `## Evidence assertions` JSON from `{text, evidence}` objects to flat strings by hand (`sha256: 543511e9eb062780464615808b49894ab227ab36bbad5578f2511a3450076558`), wrote those bytes to `intermediate/CHORUS_report.md`, `intermediate/CHORUS_report_before_regate.md`, and `CHORUS_reconciliation.md`, and re-ran the local gate after no model call (`report_gate.regenerated: false`).

2. **Mid-run registration change (`#5115`, `#5142`):**
   - The run started under registration `57d5c8429004968c3249411572bb06f2b38c6d8e1a6661f244720d975153ce60` (`max_paths: 384`, `max_inventory_bytes: 65536`, `typed_audit_worker` cap `25,000` tokens) at commit `9abe907b7`, ran `receipt_completion` at `8074af409`, and re-derived `intermediate/CHORUS_receipt_completion_result_2.json` after `723c8ac20` (committed 2026-10-20 23:56 PDT; fence unwrap `#5116`).
   - After the first `typed_audit` worker (`eb3330ce…`) hit `stop_reason: max_tokens` at 25,000 tokens with 0 visible characters, the **agy (Antigravity) session** rebuilt the registration file in place at **00:37 PDT on 2026-10-21**, changing it from `57d5c842…` (`384` paths, `65,536` bytes, `25k` worker cap) to `4f94102c50455476561b299b08866c5577f80964442b87928209d2c56614331d` (`80` paths, `12,288` bytes, `64k` worker cap), and resumed from `typed_audit` (`_2` packet/request files).
