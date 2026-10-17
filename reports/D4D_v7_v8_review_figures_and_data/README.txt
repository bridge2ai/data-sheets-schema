D4D semantic review summary

Open D4D_review_summary.html. It embeds all figure images and includes searchable primary review comments.
figures/: 14 figures, each in editable SVG and PNG.
data/: JSON source tables, evidence, hashes, and validation. Ratings include repeats; primary analyses filter rating == 1.

Reproduce on the original machine with Python 3.12, numpy, PyYAML, and Pillow:
  python3 analysis.py
  python3 statistics.py
  python3 build_report.py
The scripts use the original absolute repository/input/output paths. Adjust ROOT and OUT/O to relocate.
The repository must retain its git history so historical source bundles can be recovered.

Scores and issue prose are evaluator judgments. Nine rubric20 Q19 rationales and other documented narrative claims require adjudication. Read the report's methods and qualifications before using results.
