D4D v8 semantic evaluation summary

Open D4D_v8_summary.html. Its fourteen PNG charts are embedded, so the report
can be read without network access. The folder also contains SVG/PNG figures,
JSON measurement tables, retained v8-only evaluation tables, and scripts.

Scope: 12 v8 datasheets, four datasets, three generation replicates each;
24 primary evaluations (rubric10 and rubric20), 840 rubric item records,
303 original review comments. No new LLM evaluations were run.

Selected plots: replicate score dot plot; rubric20 item heatmap; structural
missingness stacked bars; comment-type heatmap; section concern prevalence;
accuracy/correctness field prevalence; receipt source-family/section coverage;
within-record, within-section source-linked flagged-field-rate contrasts.

Interpretation: Seven rubric20 Q19 evaluations have documented qualifications.
Native correctness/accuracy flags are not adjudicated error counts. Root
presence is not nested completeness or source-backed correctness. Receipts
record declared support, not causation. Source comparisons are descriptive
and use at most three related generations per dataset; no new p-values are
reported. Item-omission sensitivity is not a corrected score.

Reproduce: Python 3 with PyYAML and Pillow. Run analyze_v8.py, then analyze_section_documents.py, then analyze_size_normalization.py, then
build_report.py from any working directory. The measurement script uses the
included v8-only snapshots when present. Rechecking input hashes and measuring
root presence requires the original evaluation and D4D files at the paths in
data/input_audit.json. Those source documents are not copied into this bundle.
The plotting script uses local macOS font paths with fallbacks; rendering can
vary by platform. build_report.py can rebuild using only bundled measurements
and figures. Evaluation, source recovery, and section-mapping provenance are
in input_audit.json, source_recovery.json, and section_mapping.json.

Primary source locations:
/Users/obanks/Downloads/rubric10_semantic/
/Users/obanks/Downloads/rubric20_semantic/
/Users/obanks/data-sheets-schema
Repository evaluation qualifications:
notes/reference_rescore_2026-09-12_cborg_runtime/

Original broader-cohort reports were preserved separately. This bundle is v8
only. Data files keep native issue categories, recommendations, and source
types so readers can inspect and reinterpret them.

Pooled section / input-document profiles (added report section):
Figures 9-11 pool v8 records without dataset panels. Availability-based
comment burden and a selected rubric10 item score are shown separately from
receipt-linked populated-root flag fractions. Each figure displays cell-level
record counts. Native document types and eight grouped families are exported
in section_document_summary.json; record-level cells, source cohorts, and
all 50 included/excluded rubric10 item mappings are separate JSON files.
39 subelements map to one section; this is an analyst-derived partial profile,
not an official section score. Overlapping source cohorts are not independent
comparisons and are not statistically adjusted for dataset.
The standalone build_section_documents.py provides the new HTML fragment.

Size-normalized section update (Figures 12-14):
Score loss / applicable rubric10 points is distinct from share of all lost
points. Unmapped items remain an explicit contribution category. Field flag
rates use three sensitivity denominators: mapped candidate roots, populated
roots, receipt-linked populated roots. Field applicability is not adjudicated.
These counts do not adjust nested section size. Dataset-specific rates,
within-record section-minus-other-section contrasts, leave-one-dataset-out
rates, and native/family source cohorts are in size_*.json. No new inferential
tests are used. build_size_normalization.py builds the new report fragment.
Run validate_section_documents.py and validate_size_normalization.py after
rebuilding the report to check arithmetic, scope, images, and links.
