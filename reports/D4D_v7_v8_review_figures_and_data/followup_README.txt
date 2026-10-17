D4D follow-up analysis, 2026-09-30

Open D4D_review_followup.html. It embeds 10 new figures and includes 32 evidence-review cases.
The original report, original scores, and original figure files remain unchanged.

New figures: 15 through 24, each SVG and PNG.
New data: data/followup/, including evidence excerpts and manually authored assistant assessments.
Plan: followup_plan.txt. Source repository was not modified.

Reproduce quantitative analyses and figures:
  python3 followup_scripts/analyze_followup.py
  python3 followup_scripts/build_followup_report.py
Run with Python 3.12 plus numpy, PyYAML, and Pillow. Scripts retain the original absolute output/repository paths; edit O/ROOT/D to relocate.
The analysis expects original data/*.json and data/followup/sample_assessments.json, both bundled.
Assessment decisions are explicit in adjudicate_sample.py; running it reproduces the saved decisions rather than conducting an independent review.
prepare_evidence.py and source_search.py document evidence extraction and use work/followup relative to the original workspace. Some current-release excerpts were subsequently added after targeted inspection; the final, hash-labeled evidence JSON files are the retained review record.
Source recovery requires the original repository and git history.

Do not interpret the 32-comment sample as a population error-rate estimate. No human gold standard or exhaustive source-availability audit was created.
