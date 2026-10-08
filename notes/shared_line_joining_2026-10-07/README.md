# Shared one-break measurement, issue #3644

The measurement script's default one-break column now uses
`attainability.join_matching_lines(..., joins=1)` through `joined_moves`.
Its joinable-break count uses the same module's `joinable_breaks`. The
dictionary-selected split-word column delegates each selected adjacent pair to
that matcher with the original line numbers. No surrounding context or second
break is introduced, even when two selected pairs are adjacent.

The duplicate local crossing matcher and break classifier are removed. The
dictionary, ordinary matching rules, K=2/W=10 certification gate and report
keys remain unchanged. Existing literal controls retain the difference between
`con` / `sent`, boundary-touching `consent` / `from`, and `con` / `sen` / `t`.
Additional controls cover late original line numbers, selected dictionary
splits versus ordinary wraps, and exclusion of neighboring context.

This is an implementation consolidation. It does not select a new scientific
absence reading, receipt coverage policy or nested-value matching rule.
#4397 and #4398 remain policy/specification follow-ups; #2912/#2921 human
reviews remain pending. Historical notes, bundles and attainability files are
preserved.

## Fixed comparison inputs

[panel.json](panel.json) lists the 22 exact path/MD5/SHA-256/byte identities and
their 279 historical provenance memberships from the preserved
[context measurement manifest](../attainability_join_context_2026-10-02.json).
The source manifest SHA-256 is
`1b4be55e6acf998c05349c0fb034f15ece68edcdca0a102e1664c4590e9aea09`.
The word list must hash to
`be41ad97963bf8dabedd5871d5d691596175269d540956b0f9965a885c2bbab9`
and yield 234,456 entries. These memberships describe the historical panel;
the replay does not substitute today's corpus inventory.

The [replay script](replay.py) runs one selected checkout per process. It
requires the exact historical manifest and word list, resolves each bundle
using both recorded hashes, and measures the complete old report fields with
`compare_window=10`, `joins_per_window=2` and no added join context. Missing
versions remain explicit unmeasured rows and fail the run. It compares every
measurement field with the pinned historical result; matching only the
status/lines categories is insufficient.

The script records the selected commit and six focused source-file hashes,
hashes existing bundle files before/after, and rechecks the word list, manifest
and source bytes. Its direct script compilation avoids a cached script `.pyc`;
the recorded sources are not a complete dependency or runtime snapshot.
Only new external report directories are written; both modes protect the
driver checkout as well as their selected input directories. The comparison
command requires the baseline commit and script identity below, the explicitly
pinned candidate script bytes and their continued presence in the driver
checkout. Same-file, copied and swapped report roles refuse. These controls
address adversarial review [#4650](https://github.com/bridge2ai/data-sheets-schema/issues/4650).
It also requires all 22 measured identities in both reports, equal shared source
and dictionary identities, and preserved inputs; it independently compares the
typed measurement fields to each other and to the historical manifest, and
requires the complete rendered Markdown reports to agree byte for byte.

## Commands prepared for serialized validation

These commands have **not been run** for this change. Independent review and
the coordinator's application/test slot must finish first. Run baseline and
candidate sequentially, keeping their outputs separate:

```bash
TASK=/private/tmp/d4d-goal-resume-5sVO4ntI
BASE="$TASK/line-join-baseline"
CANDIDATE="$TASK/line-join-source"
PY=/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python
RUNNER="$CANDIDATE/notes/shared_line_joining_2026-10-07/replay.py"

git clone --no-hardlinks "$CANDIDATE" "$BASE"
git -C "$BASE" switch --detach 8730ba98335392aba539b5c99e0b61918be917ab

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$BASE/src:$BASE" \
  "$PY" -B "$RUNNER" run --repo "$BASE" \
  --output "$TASK/line-join-baseline-results-01"
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$CANDIDATE/src:$CANDIDATE" \
  "$PY" -B "$RUNNER" run --repo "$CANDIDATE" \
  --output "$TASK/line-join-candidate-results-01"
PYTHONDONTWRITEBYTECODE=1 "$PY" -B "$RUNNER" compare \
  --baseline "$TASK/line-join-baseline-results-01/report.json" \
  --candidate "$TASK/line-join-candidate-results-01/report.json" \
  --output "$TASK/line-join-comparison-01"
```

The baseline script SHA-256 at the selected commit is
`56615e0f7ffd371bafaa7bf79dde9565c35cc829f2b95bbfb594d67e69b53fad`.
The reviewed candidate script SHA-256 is
`bd2d3f23c97c6e03eeba1cf32a02e53027710f7794ccfd734ed66061ae42770c`.
This explicit source identity is fixed before measurement; adding evidence in a
later commit does not change it. The candidate commit is recorded as an
observation, while these script bytes identify the reviewed implementation.
The unchanged attainability module SHA-256 is
`b8f9afc15fe6b5a51f36a5c39a85296b25537396651122b335bcd7242012e264`.
The clone's local `origin` is a donor, not a publication remote.

Proposed focused test modules, run from the candidate checkout with
`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`, `PYTHONDONTWRITEBYTECODE=1`, a fresh external
`--basetemp` and `--junitxml`, and `-p no:cacheprovider`:

- `tests/test_measure_unhyphenated_line_splits.py`
- `tests/test_shared_line_join_replay.py`
- `tests/test_attainability.py`
- `tests/test_attainability_join_context.py`
- `tests/test_attainability_check_gate.py`

Validation and actual comparison results are pending. No new performance,
scientific support, calibration or exhaustive absence claim is made.
