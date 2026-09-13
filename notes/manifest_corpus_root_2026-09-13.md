# Manifest-owned corpus roots — 2026-09-13

Issue #1523 completes the external-project path from the profiles and
packaging stages. A conventional source manifest owns its project root;
standalone manifests own their containing directory. Registry bundle/source
paths, chunk mappings, conventional run outputs, receipts, provenance,
run discovery, canonical selection, review-pack inputs and corpus scans use
that same root. Explicit output-directory overrides remain caller-relative.
A caller without a selected manifest does not write into the imported
checkout. Implicit discovery within the checkout retains its main manifest
so archived copies do not silently change the active project.

The generation/evaluation reference artifacts and frozen prompt files are
unchanged. Existing recorded render specs keep their recorded paths and
renderer semantics. New runs use the selected corpus locations. This is a
path-selection boundary, not a new measurement: no production record was
generated or rescored, no definition was quoted by a new evaluator, and no
source download occurred. Both agentic and API arms remain in the overall
completion plan. Evaluation coverage remains presence, API judging, semantic
agent output acceptance, deterministic checks and semantic pair review.

Validation: the initial 100 routing/profile/API checks pass; the broadened
output-guard and CLI/review-pack lanes pass 84 and 65 checks. The final corpus
consumer lane passes 277 tests, plus its corrected Click-context fixture
passes separately. A clean wheel installs with only runtime dependencies:
the six existing acceptance checks pass, and the new ancestor-manifest
acceptance passes after correcting tuple unpacking in its fixture. It creates
chunks, executes the real API runner with a fake client, derives and validates
the pair, discovers both runs and passes strict run/provenance checks from a
nested external directory. Synthetic archive planning remains read-only.

The remaining installed-agentic command and transcript-helper work is #1556.
Independent review and exact-head CI are required before merge.
