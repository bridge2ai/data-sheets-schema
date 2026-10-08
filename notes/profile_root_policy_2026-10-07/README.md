# Authoritative roots in profile evaluation (#4595)

Profile validation now uses the same authoritative root selector as the
maintained mapping/conversion paths. It refuses ambiguous roots before
calculating field presence, and handles a one-node JSON-LD graph as one node.
Direct JSON/YAML records keep their existing behavior. Invalid graphs cannot
fall back to fields on the document wrapper or a child Dataset.

Independent adversarial review found no blocker. The local integration suite
passed **517 tests with no skips**, including descriptor conflicts, unresolved
references, duplicate identities, graph reversal, richer child datasets,
malformed graph values, qualified root types, direct records and the actual
one-node VOICE graph. The standalone script works outside the checkout.
Source hashes remained unchanged during validation.

## Replay

```sh
python -B notes/profile_root_policy_2026-10-07/replay.py \
  --repo . --output /private/tmp/profile-root-review-candidate
```

Run against each checkout with a fresh external directory. The script records
minimal/basic profile reports for five real inputs and two synthetic cases,
in original and reversed graph order: **28 checks per checkout**. It binds
source bytes, archive member, profile requirements and implementation hashes.
The original CM4AI ZIP member is read in memory and materialized only in the
external replay directory. No historical reports, bundles or labels change.

Baseline uses the unchanged validator/selector at
`833c4b4249649e1d61bfd97a5146e0bf2b1fcedd`, identical for this path to base
`e9884669561d54bfe4a56c7dcd06813787cc4187`.

| Input | Baseline basic, original → reversed | Corrected basic, either order |
| --- | ---: | ---: |
| CHORUS | 69.23% → 30.77% | 69.23% |
| VOICE | 84.62% → 23.08% | 84.62% |
| CM4AI reduced | 80.77% → 69.23% | 80.77% |
| CM4AI original | 80.77% → 69.23% | 80.77% |
| VOICE provenance | 11.54% → 11.54% | 11.54% |
| Sparse root after rich child (synthetic) | 30.77% → 7.69% | 7.69% |
| Unresolved descriptor (synthetic) | 30.77% → 7.69% | Refused; no coverage value |

Every candidate report is identical after graph reversal. The synthetic
sparse root has two of eight minimal fields: both orders now report 25%,
where the baseline reported 100% when it selected the richer child first.
The five real inputs keep their original-order reports; the corrected
reversed-order reports now agree with them. Full hashes and report details
are in [validation.json](validation.json). Local logs remain at
`/private/tmp/d4d-4595-profile-root-ce9CdpAX/`.

These percentages measure the existing profile's field-presence rules only.
They are not schema validation, scientific applicability, source coverage or
evidence of improved completeness. Existing presence semantics (including
false/null/empty values) and required-field lists are unchanged. In particular,
the `complete` profile still has no defined required fields: #4597 tracks
that separate defect. #2915 stays open; scientific reviews #2912/#2921 stay
pending. The historical fig09 v8-replicate-1 comparison remains retrospective.
