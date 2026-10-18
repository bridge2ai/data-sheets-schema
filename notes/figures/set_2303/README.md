# Figure set #2303: content and quality of generated D4D records and their evaluations

Regenerate everything with `python scripts/figures/make_all.py` (matplotlib, from the project
virtualenv). Every figure is an SVG with text kept as text, and every drawn number is exported to a
CSV beside it. The footer of each figure states the record set it was drawn from and the repository
commit at render time (suffixed `-dirty` when scripts or data had uncommitted changes). Palette and rules: `scripts/figures/_style.py`.

| Figure | Issue | Script | Record set / basis |
|---|---|---|---|
| fig01_pipeline | #2292 | fig01_pipeline.py | schematic; every box and hash lock traces to the file named in fig01_pipeline.csv |
| fig02_content_coverage | #2293 | fig02_content_coverage.py | 24 reference-rescore API-arm full records (v7 + v8) + 12 agentic-arm records (2026-08-28 claudecode-generic-v6, rep 1-3); direct arm drawn as "no runs" |
| fig03_full_core | #2294 | fig03_full_core.py | the 24 reference-rescore records; cores re-derived with derive_core() and compared with the stored siblings; pair check run without a model |
| fig04_scores | #2295 | fig04_scores.py | reference rescore 2026-09-12 (CBORG runtime): 24 records, 56 accepted ratings from completion_audit.json |
| fig05_item_heatmap | #2296 | fig05_item_heatmap.py | the same 56 ratings; cell = rating 1, repeat-rating disagreement marked |
| fig06_evidence_coverage | #2297 | fig06_evidence_coverage.py | the 24 reference-rescore records: coverage receipts, provenance receipt blocks, chunk manifests at each run's commit, source_manifest.yaml |
| fig07_audit_findings | #2298 | fig07_audit_findings.py | 86 API-runner records with an intermediate audit at HEAD (2026-08-06 to 2026-09-12); categories are keyword rules over finding text (fig07_audit_findings_rules.csv) |
| fig08_support_fitness | #2299 | fig08_support_fitness.py | 24 records generated 2026-07-28/31 (generic v1/v2, all four projects; runtime Claude Code, provider recorded as Anthropic, transport not established) matched to the judgement caches; support verdicts exist for CM4AI v1 only, mosaics only where support was judged on the replicate's own value |
| fig09_crate_vs_generation | #2300 | fig09_crate_vs_generation.py | crate mapping reports for CHORUS, CM4AI, VOICE (AI-READI: crate present, no mapper output); generated comparator = reference rescore v8 rep 1 |
| fig10_cost_latency | #2301 | fig10_cost_latency.py | the 24 reference-rescore records: api_usage tokens and seconds; USD is a google-route catalogue estimate, not a settled charge; agentic arm "not recorded"; the disqualified 2026-09-23 direct-arm canary shown separately as a runtime estimate, never pooled |
| fig11_issue_taxonomy | #2302 | fig11_issue_taxonomy.py | the 56 accepted ratings: semantic_analysis.issues_detected coded with scripts/figures/issue_codes.csv (order-driven keyword rules; multi-match rate stated on the figure; evaluator type split shown); category panels use the 48 primary ratings, consistency_checks all 56 |
| fig07_typed_audits | #2358 | fig07_typed_audits.py | 68 Stage 3 validation_audit.yaml files + 68 Stage 6 omission_ledger.yaml files (2026-09-03/04 API runs); structured status enums compared with fig07's keyword rules on the 36 runs that carry both |
| fig09_mapping_revision | #2446 | fig09_mapping_revision.py | pre-#1597 mapping report archive vs post-#1597 mapping reports (CHORUS, CM4AI, VOICE; AI-READI: crate present, no mapper output) against reference rescore v8 rep 1 |
| fig12_replication_stability | #2447 | fig12_replication_stability.py | the 24 reference-rescore API-arm full records (4 projects x v7/v8 x 3 replicates); top-level whole-slot canonical YAML comparison across 119 Dataset slots |
| fig13_inter_rater | #2448 | fig13_inter_rater.py | the 8 rescored jobs from completion_audit.json (rating 1 vs rating 2, rubric10 and rubric20, overall and per rubric element/item) |
| fig14_prompt_v7_v8 | #2449 | fig14_prompt_v7_v8.py | paired v7 vs v8 comparison across the 4 projects on the reference rescore API arm (slot coverage, core derivation, rubric10/20 scores, semantic issue counts) |
| fig15_arm_comparison | #2450 | fig15_arm_comparison.py | API arm (24 reference-rescore records) vs agentic arm (12 claudecode-generic-v6 records) vs direct arm (registered, 0 accepted runs; disqualified 2026-09-23 canary shown unpooled) |
| fig16_scoring_trajectory | #2451 | fig16_scoring_trajectory.py | historical and current rubric10/rubric20 evaluation series across dates and instruments (84-point historical, v1.x, and v2.0 instruments plotted on separate axes, never pooled) |
| fig17_module_balance | #2452 | fig17_module_balance.py | schema slot declarations across root + 12 D4D topical modules compared with populated slots in the 24 reference-rescore records, rubric item coverage, and crate mapping coverage |
| fig18_vocabulary_alignment | #2453 | fig18_vocabulary_alignment.py | comprehensive SSSOM table (301 rows keyed by `subject_id` `d4d:<slot>`) + structural SSSOM table (84 rows, FAIRSCAPE RO-Crate properties and `type_compatible` flags) |
| fig19_source_dependence | #2454 | fig19_source_dependence.py | the 24 reference-rescore records: source-document citation shares in provenance receipts vs source_manifest.yaml sizes and types at each run's commit |
| fig20_attainability | #2365 | fig20_attainability.py | per-project slot attainability across generated records, source manifests, and RO-Crate mapping reports |

Conventions shared by the set: instruments and denominators are never pooled (84-point historical
results and version 1.x vs 2.0 instruments stay apart); unknown values are drawn as explicit hollow or
hatched marks; the direct arm appears as registered with no accepted run until one exists.

## Release-level corpus caveats (#3878)

Several figures summarize the frozen 2026-09-12 CBORG reference rescore (`notes/reference_rescore_2026-09-12_cborg_runtime/`) or its paired v7/v8 API-arm records (`2026-08-30_claude_code_v7_full*` and `2026-09-04f`/`2026-09-04g`). When reading those figures together, keep four corpus-level caveats in mind:

1. **Pre-fix provenance / audit snapshot (`2026-09-04f`/`g`)**: The v8 API-arm records in the frozen reference rescore were generated on 2026-09-04 before later pipeline fixes for receipt source-origin tagging (`#2819`, `#4443`), intermediate-audit vs typed-audit alignment (`#2358`), and RO-Crate mapper regeneration (`#1597`, `#2983`, `#3024`). Figures that inspect receipts (`fig06`, `fig19`), audits (`fig07`, `fig07_typed_audits`), or mappings (`fig09`, `fig09_mapping_revision`, `fig18`) explicitly separate contemporaneous vs post-draft evidence and pre- vs post-revision mapping artifacts rather than retrofitting the frozen generation outputs.
2. **Evaluator-model heterogeneity before the frozen CBORG rescore**: Earlier evaluation runs on disk (`fig08`, `fig16`) mixed Anthropic direct, Claude Code CLI, and CBORG routes and spanned 84-point, v1.x, and v2.0 rubric instruments. Only the 56 accepted ratings in `notes/reference_rescore_2026-09-12_cborg_runtime/completion_audit.json` (`fig04`, `fig05`, `fig11`, `fig13`, `fig14`) come from a single frozen evaluator runtime and model route; historical series (`fig16`) and v1/v2 support-fitness caches (`fig08`) are never pooled with them.
3. **Arm asymmetry (`API` vs `agentic` vs `direct`)**: The API arm has 24 reference-rescore records (4 projects x v7/v8 x 3 replicates), the agentic arm is represented by 12 earlier v6 records (`2026-08-28_claudecode-generic-v6_full_rep1..3`), and the direct arm has 0 accepted full-pipeline runs (with the disqualified 2026-09-23 canary shown only as an unpooled runtime marker in `fig10` and `fig15`). Cross-arm panels (`fig02`, `fig10`, `fig15`) therefore compare cohorts generated under different prompt versions and dates, not a balanced factorial experiment.
4. **Three replicates per group (`n = 3`)**: Each project x prompt cell in the reference rescore has three generation replicates (`rep1`..`rep3`) and at most two evaluation ratings (`rating 1`, plus `rating 2` on the 8 rescored jobs in `fig13`). Medians, IQRs, and agreement counts describe this 24-record archive directly and do not support parametric confidence intervals or population-level reliability claims.

## Top-level vs nested replication scope (#3936)

`fig12_replication_stability` (`fig12_replication_stability.py`) and `fig15_arm_comparison` (`fig15_arm_comparison.py`) intentionally operate at the **top-level Dataset slot** grain (`slot in doc and not empty(doc[slot])`, comparing each slot's whole canonicalized YAML value across the 3 replicates). Because 89 of the 119 Dataset slots (including all 87 slots in the 12 topical D4D modules) are class-valued (`nested`), any single changed sub-field or list-order difference inside a nested object marks the whole top-level slot as differing (`two_agree` or `all_differ`), and identifier alignment is not used at top level because only a minority of nested list items carry an `id` (`134 / 421` on the 24 API-arm records).

For the complementary **sub-slot / nested-path replication analysis** that walks inside class-valued slots and separates comparisons by join basis (`keyed` by `id`/`name`, `position` for singletons or equal-length keyless lists, and `index` when list lengths differ), see [`notes/arm_comparison.md`](../../arm_comparison.md) (`Below the top level (#3337)`), where position-basis comparisons outnumber keyed comparisons on the v7 and v8 API arms (`3,418` and `2,614` position comparisons vs `759` and `1,153` keyed comparisons).

## Bare renders

`bare/` holds the same figures without the title line and footer, as SVG and PNG (PNG
resolution capped so each image stays under 20 megapixels, below Google Docs' 25 MP inline limit).
They are for embedding in a document whose own legend carries the title, the record set and the
rendering commit. They are regenerated by the same `make_all.py` run as the titled SVGs.

