# Figure set #2303: content and quality of generated D4D records and their evaluations

Regenerate everything with `python scripts/figures/make_all.py` (matplotlib, from the project
virtualenv). Every figure is an SVG with text kept as text, and every drawn number is exported to a
CSV beside it. The footer of each figure states the record set it was drawn from and the repository
commit at render time. Palette and rules: `scripts/figures/_style.py`.

| Figure | Issue | Script | Record set / basis |
|---|---|---|---|
| fig01_pipeline | #2292 | fig01_pipeline.py | schematic; every box and hash lock traces to the file named in fig01_pipeline.csv |
| fig02_content_coverage | #2293 | fig02_content_coverage.py | 24 reference-rescore API-arm full records (v7 + v8) + 12 agentic-arm records (2026-08-28 claudecode-generic-v6, rep 1-3); direct arm drawn as "no runs" |
| fig03_full_core | #2294 | fig03_full_core.py | the 24 reference-rescore records; cores re-derived with derive_core() and compared with the stored siblings; pair check run without a model |
| fig04_scores | #2295 | fig04_scores.py | reference rescore 2026-09-12 (CBORG runtime): 24 records, 56 accepted ratings from completion_audit.json |
| fig05_item_heatmap | #2296 | fig05_item_heatmap.py | the same 56 ratings; cell = rating 1, repeat-rating disagreement marked |
| fig06_evidence_coverage | #2297 | fig06_evidence_coverage.py | the 24 reference-rescore records: coverage receipts, provenance receipt blocks, chunk manifests at each run's commit, source_manifest.yaml |
| fig07_audit_findings | #2298 | fig07_audit_findings.py | 86 API-runner records with an intermediate audit at HEAD (2026-08-06 to 2026-09-12); categories are keyword rules over finding text (fig07_audit_findings_rules.csv) |
| fig08_support_fitness | #2299 | fig08_support_fitness.py | 24 Claude Code records generated 2026-07-28/31 (generic v1/v2, all four projects) matched to the judgement caches; support verdicts exist for CM4AI v1 only |
| fig09_crate_vs_generation | #2300 | fig09_crate_vs_generation.py | crate mapping reports for CHORUS, CM4AI, VOICE (AI-READI: crate present, no mapper output); generated comparator = reference rescore v8 rep 1 |
| fig10_cost_latency | #2301 | fig10_cost_latency.py | the 24 reference-rescore records: api_usage tokens and seconds; USD is a catalogue estimate, not a settled charge; agentic and direct arms drawn as "not recorded" |
| fig11_issue_taxonomy | #2302 | fig11_issue_taxonomy.py | the 56 accepted ratings: semantic_analysis.issues_detected coded with scripts/figures/issue_codes.csv; consistency_checks per rating |

Conventions shared by the set: instruments and denominators are never pooled (84-point historical
results and version 1.x vs 2.0 instruments stay apart); unknown values are drawn as explicit hollow or
hatched marks; the direct arm appears as registered with no accepted run until one exists.
