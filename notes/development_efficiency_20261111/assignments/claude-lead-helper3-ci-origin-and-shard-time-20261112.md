# Assignment to Codex helper 3: the import-origin CI failures, and making the native tests fit the CI time limit

From the Claude lead, 2026-11-12. You are a fresh session, started in the home directory: first read `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/notes/development_efficiency_20261111/assignments/claude-lead-helper-context-20261112.md` (short names `P`, `E`, `R`, and the rules). Work with absolute paths.

The first full CI run on the native stack (run 42976790438) failed. Two of its causes are yours. The agy workers diagnosed both and are out of usage; you finish the work.

## Where you work

Continue the CI-portability branch in its existing worktree: `E/agy-native-ci-collection-20261112`, branch `agy/native-ci-collection-5875-20261112`, head `ab07c81fe`. It is clean; it is yours now. Scratch and outputs go under `E/scratch-h3-ci-20261112/`.

A copy of the merged tree outside `d4d-executions`, for reproducing what a CI runner sees, is at `/Users/marcin/agent-work/data-sheets-schema/ci-sim-b11931410305` (made by `R/scripts/adhoc/simulate_ci_collection_outside_executions_20261112.sh`). Refresh it from your branch head with that script when you need the current files; do not edit the copy by hand except to run tests.

## Part A: "native controller dependency imported from another origin: prepare_registration" (37 failing test ids)

Read `R/notes/development_efficiency_20261111/handoffs/agy4-native-ci-portability-20261112.md`, Part 2. Its diagnosis: the native controller's source check (`native_attribution_controller_v2.controller_sources`) requires the bare module name `prepare_registration` to be loaded from `notes/matched_cborg_2026-09-13/prepare_registration_v2.py`. In CI, pytest collects the whole `tests` tree in one process, and another test module (the handoff names `tests/test_audit_recall_leak_rendered.py`) has already imported `prepare_registration` from the version 1 path. The check then refuses. Tests run one at a time never see it.

1. **Reproduce it locally in one process**, with the smallest set of test files that shows it, and confirm or correct the diagnosis. Name every test module that leaves a bare `prepare_registration` (or any other name the controller's manifests pin) in `sys.modules`.
2. **Fix it in tests only.** The production check is right to refuse a module from another origin; do not weaken it and do not edit `src/`. The repair belongs where the pollution happens or where the native tests set up: for example, the polluting test loads its module under a private name or removes it afterwards, or the native tests' existing isolation fixture (`isolated_modules` in `tests/test_native_execution_registration_v2.py`) is applied where it is missing. Choose the smallest change that makes the outcome independent of collection order, and say why.
3. **Prove it** in the copy outside `d4d-executions`: the 37 failing ids (they are in `R/notes/development_efficiency_20261111/handoffs/lead-ci-run-42976790438-failures-20261112.json`, class "import origin") pass when their files run in one process together with the polluting files, in both orders.

## Part B: the CI time limit

Read `R/notes/development_efficiency_20261111/handoffs/agy1-native-ci-shard-time-20261112.md` and its JSON. Its findings: 128 native test files have no entry in `utils/ci_test_durations.json` and are scheduled at a 1.6-second fallback while they measured about 11,770 seconds in total; `tests/test_generation_specificity_skill.py` measured 5,918 seconds against a weight of 1,149; shards 5 and 8 were cancelled at 45 minutes. Its conclusion: adding the native weights alone does not fit eight, nine or ten shards.

1. **Check the conclusion** against its data and the partition code (`utils/pytest_shard.py`, `.github/workflows/main.yaml` at your branch head). Say where you agree and where not.
2. **Why did `tests/test_generation_specificity_skill.py` grow five-fold on the native branch?** Find what its 381 cases spend the time on (the scanner re-deriving the same facts per case, more modules to scan, something that should be cached per session). Measure, do not guess. If there is a safe, small change that removes repeated work without changing what any test asserts, describe it with the measurement; do not make it without the lead's word, because the scanner is audited code.
3. **Prepare the weights update** as a commit on your branch: `utils/ci_test_durations.json` with the measured native durations from the run's artifacts (already downloaded under `/Users/marcin/agent-work/data-sheets-schema/ci-run-42976790438/`), produced by the repository's own update tool if it has one. State which files still have no measurement and what weight they get.
4. **Give the options for fitting the limit,** each with its predicted largest shard from the partition code: more shards for pull requests, a longer job limit, splitting the one very long test file, or a combination. The owner decided the present limits (decisions D75 and D81 in STATUS), so this ends as a recommendation for the owner, not as a workflow edit. Do not edit `.github/workflows/`.

## Commits and handoff

One commit for Part A and one for Part B step 3. Handoff: `R/notes/development_efficiency_20261111/handoffs/codex-h3-ci-origin-and-shard-time-20261112.md` with a JSON beside it for the numbers; answer first: is the import-origin class fixed and proven order-independent, what the weights commit contains, why the scanner test is slow, and the options with your recommendation.
