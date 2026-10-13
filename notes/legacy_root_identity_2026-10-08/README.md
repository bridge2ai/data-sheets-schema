# Explicit legacy root identity (#4672)

The default legacy TSV now includes a required `Dataset.id` construction route,
selected by `Func=root_identifier_v1` on one covered `id` row with source
`identifier,@id`. Both legacy implementations use the already selected crate
root. A nonblank scalar `identifier` wins; absent, null or blank text falls back
to root `@id`. Present lists, objects, numbers and booleans refuse before changing
the prior builder or merger result. No identity is invented or borrowed from a
member dataset.

Recognized whole scalar DOIs are written as `doi:` CURIEs. The complete body,
including case and every trailing slash, survives. Other text and ARKs retain
their exact spelling; the ID route does not trim surrounding whitespace. The
separate `Dataset.doi` implementation is unchanged from the reviewed predecessor
`1a98255bb28451500d4864876a16d9c6c2f6b435`, including its suffix-preservation fix
for #4671.

The marker is an explicit selector, never executable TSV code. Unmarked custom
ID and no-ID tables keep their prior construction, reverse lookup and scoring
behavior. Misplaced, uncovered, duplicate or incompatible marked declarations
refuse at table loading, including rows otherwise skipped as headers. The
ordinary `identifier -> doi` reverse mapping wins in either row order.

Merged ID comes only from the configured primary source. Every marked input's
identity is checked before merge state changes; a secondary identity cannot fill
a missing primary identity. The existing merge report records the selected
primary, source properties, original input assertions and differing written IDs.
Those differences do not assert that sources describe the same entity. Required
identity construction is excluded from the scorer's coverage and uniqueness
denominators and from API and CLI source-coverage statistics. Existing ranking,
ties and automatic primary selection therefore retain their prior basis.
Review issue #4674 extended that exclusion to the API result metadata and both
CLI report/stdout consumers; their construction inventories remain separate.

All original default TSV rows are retained. The new row leaves its semantic
mapping, SKOS and information-loss claims unassessed. Successful construction or
literal preservation does not establish `exactMatch`, `none`, scientific source
coverage, or a valid complete Dataset. Missing required identity and remaining
Class/nested-creator/type errors still reach the mandatory publication gate;
legacy API metadata still requires the explicit `dataset_v1` result contract for
Dataset-only publication. Neither another mapper nor a generated identifier is
substituted on failure.

## Completed validation

The reviewed implementation at `180d1028bb25332ff296eafcbfb4533d3f6ee85d`
(tree `a6d85ba51d120b1a41a74e5da4249e17a36dbf7f`) passed **570 tests**
in 14 modules: zero failures, errors or skips, 45.483 seconds in JUnit. The
coordinator recorded 45.52 seconds and 14 dependency deprecation warnings in the
console. Tests include 95 new identity cases and 42 independent adversarial
cases, both real producer paths, custom-table compatibility, malformed identity
refusals, primary-only merging, output preservation, scorer/rank behavior and
API/CLI coverage accounting. JUnit does not itself attest the Git commit or
console warning count; those bindings are coordinator run provenance.

The fresh replay baseline is the DOI-fixed
`f2f1b3f465fa1a06adf150285d2ec1e9083a7839` (production predecessor
`1a98255bb28451500d4864876a16d9c6c2f6b435`). The unchanged historical
[parser replay](../parser_root_policy_2026-10-07/replay.py) produced twenty
records per arm: five retained inputs × two implementations × original/reversed
graph order. The VOICE provenance graph remains a node object. The exact
[replay supplement](replay_supplement.py) then called the real mandatory
`prepare_dataset` gate on those saved records, ranked the five sources and ran
fresh real mergers. All collections completed with their full denominators and
no infrastructure errors or missing rows.

The stdlib-only [saved-evidence comparator](compare_saved.py) checked the complete
canonical records, roots, score dictionaries, rank order, non-ID merge
provenance, identity disclosures, validation messages and saved report text.
It imports no producer or validator code. All twenty candidate records equal
their baseline after removing only the new top-level `id`; every original root
and every remaining validation error is preserved. Both implementations and
graph orders agree.

| Retained input | Constructed ID | Baseline errors | Candidate errors |
|---|---|---:|---:|
| CHORUS | `doi:10.18130/V3/XNBOPG` | 32 | 31 |
| VOICE | `doi:10.13026/k81f-qr68` | 152 | 151 |
| CM4AI reduced | `doi:10.18130/V3/HIGT4C` | 77 | 76 |
| VOICE provenance | `ark:59853/b2ai-voice-dataset-feature-ppgs` | 1 | 0 |
| CM4AI original | `doi:10.18130/V3/HIGT4C` | 77 | 76 |

These counts apply to each implementation/order and are the full retained
validator errors, not a quality score. The mandatory Dataset gate refused all
20 baseline records. It accepted the four candidate versions of **one** VOICE
provenance input and refused the other 16. Accepted bytes were prepared and
hashed in memory; they were not published. Their full record equals the saved
YAML draft, whose serialization has a different byte hash. Prepared byte
contents were not separately retained.

All four complete score/rank groups are unchanged. The ranking remains VOICE,
CM4AI reduced, CM4AI original, CHORUS, VOICE provenance. Eight real merge pairs
cover that ranked primary and an explicit VOICE provenance primary, across
both implementations/orders. They retain the fixed secondary source order;
this is not a full auto-reordered CLI replay. Non-ID records and provenance
match exactly. Only `fields_from_primary` and `total_unique_fields` increase by
one for the constructed ID; all other statistics match. **This is construction
accounting, not improved source coverage.** All eight mixed merges per arm
still refuse Dataset publication. The mixed roster is a software control, not a
scientific combined dataset.

All forty candidate merge identity disclosures retain the five raw source
assertions, selected primary, property choice and differing written IDs. Merge
report text differs only by the verified disclosure section, ID contribution,
corresponding construction counts and observed timestamp. No identity
agreement or entity equivalence is inferred.

## Evidence and preservation

[validation.json](validation.json) records the tested tree, 43 candidate
source/test/resource pins, 25 baseline source/resource pins, driver and artifact
identities, all error/gate denominators and full compact comparison results.
The complete tested implementation path list also includes API and both CLI
changes for #4674; the comparator's `declared_source_changes` lists only its
narrower selected replay-source deltas.

The full checkout inventories before and after all four executions are byte
identical: SHA256
`6a4d05992df40fa97145b5b8ff68509d3eff474cff1a5a7e5793db8876673529`.
They cover 9,278 baseline and 9,281 candidate actual files, including hidden and
ignored entries except `.git`, with byte identities and modes. The independent
reviewer rechecked those original entries against the saved inventory. This
note and its evidence utilities are added afterward. Historical parser/DOI
results, original input files, the ZIP/member and historical generated outputs
remain unchanged.

The supplement separately verified 71 saved replay files per arm and its selected
79/80 source/history files. Optional FAIRSCAPE model-unavailable warnings were
observed during replay; the actual legacy parser/builders and Dataset gate ran.
This result does not establish availability of that optional integration.
CPython 3.13.12, selected dependency versions and executable byte identity are
recorded; this is not a complete installed-environment or import-cache snapshot.
Full drafts, raw records, report paths and complete inventories remain external.

## Reproduction using fresh external destinations

Set `BASELINE` and `CANDIDATE` to the exact commits above, `PYTHON` to the selected
environment, and `EVIDENCE` to a fresh external directory. Protect both source
checkouts and all original artifacts before using the historical replay, which
only checks its selected checkout. Run each arm in a fresh process, sequentially,
with bytecode writes disabled. The coordinator's focused test command and module
list are retained with symbolic paths in `validation.json`.

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$BASELINE/src:$BASELINE" \
  "$PYTHON" -B "$BASELINE/notes/parser_root_policy_2026-10-07/replay.py" \
  --repo "$BASELINE" --output "$EVIDENCE/baseline-replay"
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$CANDIDATE/src:$CANDIDATE" \
  "$PYTHON" -B "$CANDIDATE/notes/parser_root_policy_2026-10-07/replay.py" \
  --repo "$CANDIDATE" --output "$EVIDENCE/candidate-replay"

PYTHONDONTWRITEBYTECODE=1 "$PYTHON" -B "$NOTES/replay_supplement.py" \
  --repo "$BASELINE" --expect-commit f2f1b3f465fa1a06adf150285d2ec1e9083a7839 \
  --role baseline --replay "$EVIDENCE/baseline-replay" \
  --output "$EVIDENCE/baseline-supplement" \
  --protect-repo "$BASELINE" --protect-repo "$CANDIDATE"
PYTHONDONTWRITEBYTECODE=1 "$PYTHON" -B "$NOTES/replay_supplement.py" \
  --repo "$CANDIDATE" --expect-commit 180d1028bb25332ff296eafcbfb4533d3f6ee85d \
  --role candidate --replay "$EVIDENCE/candidate-replay" \
  --output "$EVIDENCE/candidate-supplement" \
  --protect-repo "$BASELINE" --protect-repo "$CANDIDATE"

"$PYTHON" -B "$NOTES/compare_saved.py" \
  --baseline "$EVIDENCE/baseline-supplement" \
  --candidate "$EVIDENCE/candidate-supplement" \
  --baseline-replay "$EVIDENCE/baseline-replay" \
  --candidate-replay "$EVIDENCE/candidate-replay" \
  --baseline-commit f2f1b3f465fa1a06adf150285d2ec1e9083a7839 \
  --candidate-commit 180d1028bb25332ff296eafcbfb4533d3f6ee85d \
  --output "$EVIDENCE/comparison.json"
```

`NOTES` names this notes directory from the evidence commit; the tested candidate
checkout itself remains at its recorded implementation commit. The comparator
writes only a new sibling file of the four evidence directories. It verifies
saved declarations and payloads without reading original paths; source/runtime
authentication remains outside its claim. Its report normalization is limited
to the explicitly enumerated differences above.

Per-arm collection completion, cross-arm equivalence and Dataset validity are
separate results. None establishes scientific correctness or general legacy
producer validity. No rows were retired and no semantic mapping labels were
upgraded. Parent issues #4594 and #2915 remain open for broader construction,
validation, comparison and publication obligations. Pending human scientific
reviews, applicability, routing and paid-execution decisions remain pending.
