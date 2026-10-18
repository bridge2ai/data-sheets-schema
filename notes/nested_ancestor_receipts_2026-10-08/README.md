# Nested ancestor receipt diagnostics (#4397)

The strict nested omission rule remains unchanged: a row becomes a candidate
only when a holder has a verified, resolved receipt on that row or below it.
The opt-in diagnostic exposes the different relation used by receipt coverage:
a receipt on a containing object may cover a nested field or entry without
establishing that the particular information another replicate lacks was
attested. No receipt is newly credited to an omission candidate.

`nested_omission_candidates(records, result, resolved,
ancestor_diagnostics=True)` adds these fields:

- Each row has `ancestor_receipts`, a list of `{holder, target_path,
  receipt_path, snippets}`. Paths use that holder's resolved final record.
  Evidence must have a positive verified snippet count, be a proper ancestor
  under the existing `receipts._covers` relation, and belong to a holder
  without an on/below receipt. A list receipt does not cover its entries.
- Each row has `ancestor_only`, true only for an existing `not_candidate` row
  with such evidence. Commentary has no ancestor evidence. Evidence may remain
  visible on an `unmeasured` row or on a candidate supported by another holder,
  but neither enters this subset.
- `ancestor_only_counts` reports distinct rows by `field` and `entry`, each
  counted once regardless of the number of holders, paths or snippets. These
  are subsets of the corresponding existing `not_candidate` counts.

All original row fields, status counts, denominators and omitted-candidate
counts per replicate are unchanged. Unreadable receipts and unusable snapshots
remain distinct from readable receipts containing no verified paths. Default
calls, including explicit `ancestor_diagnostics=False`, retain the old machine
result shape. The first-level omission instrument is unchanged.

The report API accepts the same opt-in argument on `nested_omission_section`
and `render_markdown`. It adds a supplemental **of not: ancestor-only fields +
entries** column. A group with no readable receipts displays a dash. Omitting
the option preserves the existing report text. The CLI uses the existing new
report route:

```sh
python scripts/arm_comparison.py --ancestor-receipt-diagnostics \
  --no-figures --output /tmp/new-ancestor-report.md
```

This option requires `--output`, `--no-figures` and no `--check`. Existing files
and symlinks are refused. It can accompany an explicit attainability selection;
that selection's existing captured sidecar behavior is retained. No historical
report, figure, receipt, source bundle or generation output is replaced by the
opt-in route. No full report regeneration or new empirical comparison was
performed for this change.

These are deterministic path diagnostics, not scientific support, source
coverage improvement, established omissions or recall measurements. The 17
historical rows cited in #4397 have not been revalidated here. Scalar-list
matching under #4398 and the human annotation/matching decisions under #2921
remain pending; this change grants no approval to score those annotations or
run a generation campaign.

## Validation

The serialized suite passed **236 tests** with zero failures, errors or skips:
25 new diagnostics cases and 211 existing regression cases. JUnit records
221.436 seconds; the coordinator's terminal summary reports 221.50 seconds
and one dateutil dependency deprecation warning. No material finding remained
after independent source review.

| Test module | Passed |
|---|---:|
| `test_nested_ancestor_receipts.py` | 25 |
| `test_replicate_structure.py` | 68 |
| `test_receipts.py` | 50 |
| `test_attainability_aggregation.py` | 53 |
| `test_arm_comparison.py` | 40 |

Tested commit: `baeb92d315c488af25661ac60ceaf98536c37e2c`.
Tested tree: `5d11d690826df39c5938f14f4a7eb613c2b180c7`.
The working tree was clean after the run, before these evidence notes changed.
[validation.json](validation.json) records 13 source/test/dependency declaration
pins, each independently matched against both the tested Git blob and working
bytes. These selected pins are not a complete runtime import closure or an
attestation of installed dependency versions.

Retained external JUnit artifact: `ancestor-diagnostics-tests-01.xml`, 34,387
bytes, SHA256
`bf8b88a65ad2faecb731e32ec555653bad38f1d0cfe010f5874c0d63b7ffbff0`.
Its digest, module counts and outcome nodes were independently checked.
The commit and invocation binding come from the coordinator's frozen-run
record; JUnit itself does not attest source revision or runtime identity.

The suite includes existing corpus-backed regression controls and synthetic
diagnostic/report fixtures. It does not establish a new empirical comparison,
recount the historical 17 rows, regenerate a full report or replay generation.
No historical report or figure was replaced, and the scientific holds above
remain unchanged.
