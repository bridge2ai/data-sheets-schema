Adversarial review of G3 commit `36d9bb25b`, `docs/final-generation-acceptance.md`, found non-executable operator commands.

At lines 112–118 the typed-audit examples use unsupported arguments. In pinned `typed_audit.py:575–604`, every command requires `--output`; `check` requires `--assembly`; `check-integration` requires `--packet`, repeated `--worker ID=PATH`, `--omission-response` and `--integration-response`. The proposed `--packet-dir` and `check --report/--record/--bundle/--chunk-manifest` forms do not exist.

Revise the checklist against actual command parsers. Prefer a short set of verified commands and links to the existing typed-audit workflow rather than copying a generic command catalog. No new tests, CLI features or generation gates are requested.

Completed review also confirmed: `d4d api status` takes no project/label options (`cli/api.py:1512–1513`), contrary to guide line 24. `review pack` and `review check` exist, but an independent reviewer must populate `PROJECT_review.yaml` between them (`cli/review.py:149–151`). The guide must not imply that generating a pack creates an accepted review.
