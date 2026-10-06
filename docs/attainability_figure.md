# Checked source-state heatmaps

Render one explicit `{capture, report}` sidecar produced by [attainability aggregation](attainability_aggregation.md):

```sh
PYTHONPATH=src python scripts/figures/attainability_heatmap.py \
  --sidecar /path/to/report.attainability.json \
  --output-dir /path/to/new-heatmap-directory
```

The consumer rechecks the complete captured closure with the existing aggregation implementation and requires exact report equality, including JSON value types. It does not reopen the original source, evaluation, policy or rubric files. Changed or unsupported captured implementation identities refuse. Captured integrity is checked; scientific readings and scope decisions are not authenticated.

Color encodes only the declared final source state: supported, partly supported, not stated in source, unknown, or conflict. Each cell separately shows recorded score / maximum, with an em dash for null; N/A and unknown applicability have independent labels. A supported zero and an absent zero therefore remain distinct. Neither is automatically a proven generator omission. The review marker copies only an `absent_positive_scores` finding emitted by aggregation; it is not a hallucination verdict.

Rows with unavailable or zero-eligible aggregate bases remain visible with their item states and reasons. Each row keeps its own ordered roster, maxima, evaluation/policy identities and original fixed, N/A-adjusted and supported-item bases. Different rows are never pooled, ranked, or assigned project/cohort labels from filenames. The default layout has at most four independent panels per page, with ten cells per line. Long visual identifiers are explicitly abbreviated; full item states and reasons are in SVG cell titles and complete JSON/CSV exports.

The new output directory contains:

- `attainability-001.svg`, followed by numbered pages as needed.
- `checked_report.json`: the complete rechecked report, preserving identities, historical bases, evidence and limitations.
- `rows.csv`: every row-level report field except the separately exported item inventory.
- `items.csv`: every item field, row identity/state/reasons, and the existing review-finding marker.
- `manifest.json`: written last on successful publication, with the raw sidecar pin, canonical capture/report pins, selection, renderer/aggregation source pins, Python/Matplotlib versions, limits and output hashes.

Every CSV data cell is a JSON value; parse CSV first and then JSON-decode each cell. This preserves null, zero, booleans, lists and detailed reason objects, and keeps user text separate from spreadsheet formulas. CSV headers are ordinary field names. The original sidecar bytes are preserved at their input path and pinned in the manifest.

The default bounds are a 416 MiB input envelope, 256 rows, 50 items per row, 32 MiB per output artifact, 8 MiB per SVG, and 128 MiB total including the manifest. The existing aggregation limits still apply unchanged. SVG accessible labels have a pre-render budget of half the SVG byte limit. Oversized inputs or products refuse; rows and states are never silently dropped. The Python `Limits` object can lower these ceilings only.

Publication requires a fresh directory under an existing parent. Existing destinations, symlinks, hard links, and paths overlapping selected or consulted captured inputs are refused. The input and implementation files are verified before and after rendering/publication, and output bytes are checked before the complete manifest is written. Failures retain distinguishable partial output; the command never cleans or overwrites it. No existing report command, protected manuscript figure, source annotation, rubric policy, scoring behavior or empirical dataset is changed.

This generic renderer does not resolve human source adjudications, E1.1 route policy, applicability/scope judgments, historical policy joins or permission for an empirical campaign. Synthetic fixtures used to check this software do not establish scientific calibration or measurement results.
