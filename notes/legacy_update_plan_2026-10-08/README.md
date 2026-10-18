# Explicit legacy maintenance narratives (#4678)

The existing default legacy `updates` row now selects
`Func=update_plan_narrative_v1`. Both legacy builders use one shared constructor:
root `rai:dataReleaseMaintenancePlan` text becomes
`{"update_details": original_text}`. All text survives, including whitespace,
newlines, Unicode and blank strings. No frequency, date, responsible person or
other unstated fact is inferred.

Both loaders validate this selector before filtering raw TSV rows: it must name
one covered `updates` route with exactly that single source property. Misplaced,
uncovered, duplicate and competing declarations refuse. Builders recheck the
route before replacing previous state. An unmarked custom table retains its
existing behavior; unrelated Func values are not executed or reinterpreted.
The established DOI and root-ID rules remain unchanged.

Dictionaries and other non-text values are copied whole. Unknown keys, arrays,
duplicates, false and zero remain available to the mandatory Dataset gate;
they are not stringified, joined, filtered or reduced to a first element.
Missing/null retains its existing absence behavior. Construction reads only
the selected root; a member value cannot fill a missing root property.

The existing merger policy is unchanged: `updates` uses a non-None primary
value, otherwise the first non-None secondary in the existing order. The
selected whole value and its source provenance survive. No nested object fields
or maintenance narratives are combined. An invalid but present primary is not
skipped in favor of a valid secondary. Detached construction prevents result
mutation from changing the parser's source evidence.

This changes an already counted field's representation. Scoring, ranking,
source order and primary-selection rules remain unchanged. Historic TSV
`Mapping_Type`, `SKOS_Relation` and `Information_Loss` values are retained as
historic declarations; this change does not reapprove `exactMatch` or `none`,
measure scientific fidelity, or increase source coverage. No rows are retired.
The mandatory final-byte publication gate and producer/result contracts remain
unchanged.

## Completed validation

The independently reviewed implementation at
`839091641c87ffc773543d49a74cd7f2e5460a1f`
(tree `8894470e04e60adcf64f0cc5097771986dc499ff`) passed **711 tests**
in sixteen modules, with zero failures, errors or skips. This includes 103 new
constructor tests, 38 independent adversarial cases and the prior 570
DOI/root-ID/publication/API/CLI/integration controls. JUnit records 130.621
seconds; the coordinator recorded 130.95 seconds and fourteen dependency
deprecation warnings. Invocation and commit bindings are coordinator provenance;
JUnit does not itself attest a Git commit or console warning count.

The tested table retains its original CRLF bytes and every historic semantic
label. Removing only the inserted Func marker restores the entire baseline
TSV. Ordinary `git diff --check` therefore flags trailing whitespace on the
modified CRLF row79; the scoped
`git -c core.whitespace=cr-at-eol diff --check` passes. Unrelated table lines
were not normalized to silence that warning.

## Completed five-input comparison

Baseline `f6e13a1e7624d7cdc7e0cf926f62a972c02b2763` already contains the
[root-ID repair and evidence](../legacy_root_identity_2026-10-08/README.md).
The unchanged [parser replay](../parser_root_policy_2026-10-07/replay.py) ran
against that baseline and the tested candidate. The exact executed
[supplement](replay_supplement.py) then prepared each retained record with the
real mandatory Dataset gate and ran actual scorers and mergers. Each arm
completed all twenty records, four ranking groups and eight merge controls,
with no missing controls or infrastructure errors.

The stdlib-only [saved comparator](compare_saved.py) checked full canonical
records, selected roots, original error sequences, complete scores/ranks,
merge content/provenance/statistics, report text and all 28 gate outcomes per
arm. It executes no producer, validator, scorer or merger code.

| Input | Baseline errors | Candidate errors | Gate in both arms |
|---|---:|---:|---|
| CHORUS | 31 | 30 | Refused |
| VOICE | 151 | 150 | Refused |
| CM4AI reduced | 76 | 75 | Refused |
| VOICE provenance | 0 | 0 | Accepted |
| CM4AI original | 76 | 75 | Refused |

Each row is repeated across both implementations and original/reversed graph
order. All sixteen records that contain maintenance text differ only by
`updates: text` becoming `updates: {update_details: text}` with the exact same
text. The four VOICE provenance variants remain unchanged. All original roots,
DOI/ID values and non-updates validation errors are identical. These message
counts are not scientific quality scores or independent source observations.

Individual gate counts remain **four accepted and sixteen refused per arm**.
The four acceptances are variants of one VOICE provenance input. All eight
mixed-roster merges per arm still refuse publication. No unrelated invalid
field was removed or repaired to make a record pass; accepted bytes were
prepared in memory, not published to a corpus.

All four full score/rank groups match exactly. Ranked-primary controls still
select VOICE; explicit VOICE-provenance-primary controls retain that primary
and take their maintenance text from CHORUS, the first available secondary in
the fixed order. All eight full merge pairs preserve every non-updates value,
source provenance and statistic. No field-count or source-coverage gain occurs.
The eighty root-identity disclosures across both arms remain exactly bound to
their source assertions. Full merge report text matches after replacing only
verified per-arm input paths and observed timestamps. No maintenance object
fields or source plans are combined.

The mixed roster is a software control, not a scientifically combined dataset.
Ranked-primary comparison preserves secondary order; it is not a complete
replay of the CLI's automatic input reordering.

## Evidence and preservation

[validation.json](validation.json) records the tested commit/tree, all nine
changed implementation paths, 46 selected candidate source/test/resource pins,
26 baseline pins, executable/dependency observations, all artifact identities
and compact full comparison results. Raw crates, drafts, private paths and
full report/inventory payloads remain external. Historic DOI and root-ID
evidence was retained unchanged.

The full before/after checkout manifests are byte-identical (4,360,876 bytes),
SHA256 `f51b395993851df2255c49edd84547c5b45cb28776096c5a991c496c6e859d91`.
They cover 9,284 baseline files (447,162,372 bytes) and 9,288 candidate files
(447,193,393 bytes), including hidden and ignored files and modes, excluding
`.git`. New notes are added after these completed runs. The independent reviewer
also rehashed the original current entries, excluding only this active README.
The supplement separately checked 71 saved replay files per arm and selected
80/81 source/history files before and after its execution.

Both supplements reported the optional FAIRSCAPE model import unavailable
(`No module named 'fairscape_models.rocrate'`), as confirmed by the coordinator.
Actual legacy construction, scoring, merging and mandatory Dataset gates
completed. This evidence does not establish that optional integration's
availability. The selected CPython 3.13.12 executable bytes and dependency
versions are recorded; they are not a complete installed-environment or import
cache snapshot. Prepared accepted-byte hashes are observations from execution;
those byte payloads were not separately retained. Complete accepted records
and all refusal messages are compared directly.

## Reproduction with new external outputs

Use separate clean checkouts at the baseline and candidate commits above.
`PYTHON` selects the recorded environment, `NOTES` this evidence directory,
and `EVIDENCE` a fresh directory outside both checkouts. Preserve both complete
source inventories before/after execution. The exact focused test command and
module list are recorded with symbolic paths in `validation.json`.

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$BASELINE/src:$BASELINE" \
  "$PYTHON" -B "$BASELINE/notes/parser_root_policy_2026-10-07/replay.py" \
  --repo "$BASELINE" --output "$EVIDENCE/baseline-replay"
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$CANDIDATE/src:$CANDIDATE" \
  "$PYTHON" -B "$CANDIDATE/notes/parser_root_policy_2026-10-07/replay.py" \
  --repo "$CANDIDATE" --output "$EVIDENCE/candidate-replay"
PYTHONDONTWRITEBYTECODE=1 "$PYTHON" -B "$NOTES/replay_supplement.py" \
  --repo "$BASELINE" --expect-commit f6e13a1e7624d7cdc7e0cf926f62a972c02b2763 \
  --role baseline --replay "$EVIDENCE/baseline-replay" \
  --output "$EVIDENCE/baseline-supplement" \
  --protect-repo "$BASELINE" --protect-repo "$CANDIDATE"
PYTHONDONTWRITEBYTECODE=1 "$PYTHON" -B "$NOTES/replay_supplement.py" \
  --repo "$CANDIDATE" --expect-commit 839091641c87ffc773543d49a74cd7f2e5460a1f \
  --role candidate --replay "$EVIDENCE/candidate-replay" \
  --output "$EVIDENCE/candidate-supplement" \
  --protect-repo "$BASELINE" --protect-repo "$CANDIDATE"
"$PYTHON" -B "$NOTES/compare_saved.py" \
  --baseline "$EVIDENCE/baseline-supplement" \
  --candidate "$EVIDENCE/candidate-supplement" \
  --baseline-replay "$EVIDENCE/baseline-replay" \
  --candidate-replay "$EVIDENCE/candidate-replay" \
  --baseline-commit f6e13a1e7624d7cdc7e0cf926f62a972c02b2763 \
  --candidate-commit 839091641c87ffc773543d49a74cd7f2e5460a1f \
  --output "$EVIDENCE/comparison.json"
```

The historical replay protects only its selected checkout, so preflight all
output paths against both source trees and original artifacts. The supplement
checks both supplied protected checkouts. The comparator writes only a new
sibling file of its four evidence directories; it reads saved payloads and
declarations without following original source/runtime paths. This is local
reproducibility evidence, not authenticated execution.

Only #4678 is addressed. Collection completion, cross-arm agreement and Dataset
validity are separate results. None proves scientific correctness, general
legacy producer validity or improved source coverage. Parent issues
#4594/#2915 remain open, as do pending scientific reviews and other mapping,
identity, precision, file-placement and publication obligations.
