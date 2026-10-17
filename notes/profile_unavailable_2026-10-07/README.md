# Undefined complete-profile evaluation (#4597)

The unified validator's `complete` profile has no implemented required-field
list. Previously, a validly selected sparse Dataset received 100% coverage
and a passing report because the empty denominator fell through to 100.

The validator now returns an explicit unavailable report after file parsing
and authoritative-root selection succeed. `passed` is false;
`coverage_percentage`, `missing_fields`, `metadata.required_count` and
`metadata.found_count` are null. Metadata identifies
`status: unavailable` and `reason: required_fields_not_defined`. The textual
report says `UNAVAILABLE`, and the standalone CLI returns exit status 1.
This describes a missing evaluation implementation, not a finding that the
dataset is scientifically incomplete.

No complete-profile scientific criteria or applicability decisions are added.
Minimal/basic field lists, thresholds and key-presence behavior are unchanged:
false, null, empty lists and empty strings still count as present fields.
Earlier file/root errors retain precedence. Transformation admission and its
separate mapped-field coverage metric are unchanged. The default combined
validation profile remains basic.

## Validation and replay

The focused tests are `tests/test_rocrate/test_profile_unavailable.py`;
the existing root-policy suite is
`tests/test_rocrate/test_profile_root_policy.py`. Both ran after the source was frozen. Tests cover sparse and richer direct records, graph order and singleton
graphs, false/null/missing fields, parse/root precedence, explicit null metrics,
combined reports, the default basic profile and the standalone CLI. These are
software checks, not scientific labels. **95 tests passed**, with no failures or skips.

The new [replay.py](replay.py) runs all three levels against five real inputs:
CHORUS, VOICE, CM4AI reduced, the original CM4AI ZIP member, and the one-node
VOICE provenance graph. It adds sparse-root/rich-member and unresolved-root
controls, using original and reversed graph order: **42 profile checks per
checkout**. The historical minimal/basic replay and its reports stay intact.

Run this same new script sequentially against baseline `24d688388` and the
reviewed candidate. Each invocation needs a fresh label and external output
directory; the candidate can compare against the saved baseline:

```sh
python -B notes/profile_unavailable_2026-10-07/replay.py \
  --repo /path/to/baseline-checkout \
  --output /private/tmp/profile-unavailable-baseline-24d688388 \
  --label profile-unavailable-baseline-24d688388
python -B notes/profile_unavailable_2026-10-07/replay.py \
  --repo /path/to/candidate-checkout \
  --output /private/tmp/profile-unavailable-candidate-review \
  --label profile-unavailable-candidate-review \
  --compare /private/tmp/profile-unavailable-baseline-24d688388
```

The script records exact validator, selector, requirements and input hashes,
and checks source-file and code hashes again after replay. Source bytes are
copied into the external output directory; the ZIP member is read from a
captured archive in memory and materialized only there. Full JSON reports
retain null metrics, and text reports record the displayed unavailable state.
The comparison retains baseline numeric complete-profile reports alongside
candidate results, verifies identical minimal/basic reports and root errors,
and requires unavailable complete-profile results for valid roots. A mismatch,
exception or source change exits nonzero. No execution or test result is
claimed here before the serialized runs. Publish fresh comparison artifacts
with distinct labels under this note directory after review.

Removing an unjustified percentage is not improved source coverage or a
scientific completeness gain. Historical generation/evaluation outputs and
the retrospective fig09 comparison remain unchanged. Human reviews #2912 and
#2921 remain pending; this engineering fix does not resolve them or #2915's
remaining implementation and publication obligations.

The fresh baseline and candidate replays are complete: **42 checks each**
across the five real sources and two root-selection controls, all three
profiles and both graph orders. All nine comparison checks passed. Valid
complete-profile inputs changed from the unjustified 100%/pass to unavailable
with null metrics; unresolved-root errors and every minimal/basic report are
unchanged. Source hashes before and after agree in both runs. Compact results,
implementation pins and external JUnit/replay digests are in `validation.json`.
The baseline checkout includes the unrelated native diagnostic commit, with
the same profile-validator and root-selector bytes as main `24d688388`.
