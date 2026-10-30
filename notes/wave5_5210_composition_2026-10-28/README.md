# Wave 5 #5210 composition packet — 2026-10-28

The report-admission branch is composed locally onto the requested A13 packet.
The original full run produced **236 passes and one stale-baseline fixture
failure**. Independent reconstruction explained every changed request byte by
inherited D38 prompt edits. The complete repaired test then passed with all its
original assertions intact. This establishes **237 distinct passing cases
across two named heads**, not one green full-suite run.

No production repair was needed. Claude directs final integration and review;
AGY publishes. No provider calls, GitHub writes, pushes, main merges, owner
worktree changes, or historical-run changes occurred in this task.

## Exact composition and conflict review

| Role | Full commit |
| --- | --- |
| Original #5210 head | `aaa6f5bec2a0c7832d36143c4c7470d51cb8cee4` |
| Incoming A13 packet | `04799422669fb2bd9f571bf8c0800dfc4b0ef008` |
| Common ancestor | `f8c5ac73caba610d40c49aaceddb31ead3590a72` |
| Production composition, ordered parents above | `d72c8085f87f0d6f5b0d83457d2df16f83afb9af` |
| Original full-run source plus retained validator | `dc9ca46701e74e712bf1800fbda8542b84e4c91e` |
| Independent wire-lineage packet | `6452395cc4900f698afebaed1ea17fb79822cb10` |
| Helper/report-only merge, parents `dc9ca4670` and `6452395cc` | `6ff278bbaf0d17e5d00599aca7b52cea8d3ff1e7` |
| Fixture repair and focused tested head | `ad1f950df173f8ed07023faeff612feb32b4dec7` |

Branch: `codex/wave5-5210-composition-20261028`.
Worktree: `/private/tmp/d4d-codex-wave5-5210-20261028`.

The production merge automatically combined `api_runner.py` and
`receipt_completion.py`. **There were no conflict hunks and no manual merge
resolutions.** The protected assets and decision record equal the incoming
A13 bytes. The helper-only evidence merge changes no `src/`, `tests/`, `data/`,
`.claude/`, `.github/` or registration-builder bytes.

Read-only review retained the admission-before-`begin_call` ordering, pending
repair-refresh checkpoint, refusal/recovery behavior, and A13's saved-receipt
compatibility handling. Before the fixture correction, the six #5210
production/test deltas have the same stable patch ID against the old common
ancestor and the incoming A13 parent:
`8b30d8d5e225c05c446e6732fe68233c7ecd5f34`.

## Preserved finding and bounded repair

The full run failed only at the first hash comparison in
`test_chorus_wire_is_byte_identical_to_the_base_and_is_what_was_counted`
(`tests/test_report_admission.py:249` at the original tested head). Its goldens
explicitly described `f8c5ac73c`, but the composed parent contains the D38
prompt spelling/wrapping and pin changes.

The [independent lineage report](../wave5_5210_wire_lineage_2026-10-28/README.md)
reproduces all three old goldens on `f8c5ac73c`, derives the incoming A13 wires
without the admission implementation, and reconstructs every new canonical byte
using only the inherited prompt hunks. The sole changed JSON leaf is
`messages[0].content[2].text`; no other model-facing field differs. This is an
inherited D38 prompt change, not an admission-induced request mutation.

The fixture now names A13 `047994226` and uses those independently derived
hashes. The original three hashes remain under `HISTORICAL_F8_WIRE_SHA256`.
Every test function and assertion remains unchanged, including exact
count-to-dispatch comparison, saved request-hash binding, and the second full
pipeline execution with admission bypassed. No production or protected bytes
changed. The [local finding draft](issue-stale-wire-fixture.md) has no assigned
GitHub issue number; it has not been posted.

The validator also received a narrow provenance repair. The first restricted
`git show --remerge-diff` emitted `error: unable to create temporary object
directory` but returned zero. Its empty stdout is not accepted as proof. The
focused run creates temporary Git objects outside the shared repository,
rejects stderr as well as nonzero status, and records return code zero with
zero stdout/stderr bytes. A successful authorized check also preceded the full
run. This diagnostic did not affect pytest's actual results or source/import
attestation. A [separate local issue draft](issue-remerge-provenance-check.md)
preserves that finding.

## Validation and distinct-case accounting

| Module | Original full run | Focused repaired run | Distinct passing cases |
| --- | ---: | ---: | ---: |
| `test_download.test_api_runner` | 156 passed | Not selected | 156 |
| `test_usage_ledger` | 59 passed | Not selected | 59 |
| `test_report_admission` | 21 passed, 1 failed | Affected case passed | 22 |
| **Total** | **236 passed, 1 failed** | **1 passed** | **237** |

Both runs had zero skips/errors and 12 existing Pydantic deprecation warnings.
Both source/import checks passed. The full run took 3961.82 seconds in pytest
(3983.899230582989 driver seconds); the focused run took 244.38 seconds
(250.3476891659957 driver seconds). These are functional run diagnostics, not
host benchmarks.

`scripts/adhoc/summarize_wave5_5210_validation_20261028.py` verifies the disjoint
case identities, preserves the original failure, checks that production/data/
protected/decision scopes are unchanged between tested heads, and confirms that
the fixture's entire AST apart from the two named golden assignments is
unchanged. Only the rerun case consumes the changed current-golden constant.
Its result is [coverage.json](coverage.json). No full-suite rerun was needed
for this fixture-only correction.

Full command, from the clean worktree at `dc9ca4670`:

```sh
/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python -B \
  scripts/adhoc/validate_wave5_report_admission_20261028.py \
  --output /private/tmp/d4d-wave5-5210-full-20261028 \
  --expect-head dc9ca46701e74e712bf1800fbda8542b84e4c91e \
  --base 04799422669fb2bd9f571bf8c0800dfc4b0ef008 \
  --module test_download.test_api_runner --module test_usage_ledger \
  --module test_report_admission
```

For the focused run, use head `ad1f950df173f8ed07023faeff612feb32b4dec7`,
fresh output `/private/tmp/d4d-wave5-5210-wire-fixed-20261028`, and add
`--wire-only`. The selected node remains the complete original CHORUS test;
its three admitted phases and bypassed control all execute. Reproduction
requires fresh output paths; existing evidence is never overwritten.

## Persisted evidence and publication boundary

Complete raw results remain in those two external directories. The committed
`validation/` packet preserves logs, JUnit, outcomes, plans, invocation and
bootstrap records verbatim. Its manifest hashes the complete external
source/origin inventories instead of adding multi-megabyte copies to the PR.
All new helper scripts are retained under `scripts/adhoc/`. The independent
parent/control derivations and their reversible byte comparison are included
via the helper/report-only merge. No inherited evidence was rewritten.

| Artifact | SHA-256 |
| --- | --- |
| Compact validation manifest | `80ac4afd98045e520627745a0ec441312a7c574b99c4301450a4528e0061ca19` |
| Distinct-case coverage | `919791edbfd0756e8357239cbc677b758ef4dbdf0b0a92b59ffb4d12b3be69d7` |
| Original full outcome | `91a94c849f16d3d368857a7a1b0063e3c9302f485d77627c6d17d2e7013a55ed` |
| Original full log | `0a6bcc4e4556d6d3483d2751890811af4407baf8971885365f770d2afb1c6d46` |
| Original full JUnit | `300637f08667298818e1000e88e0cfbe12f58fa01d847964918150a7d5fcff6d` |
| Focused outcome | `c5f16887e38b10c795d0c1650468b9ab0efd831696cabe13d0b10ea9b0867f77` |
| Focused log | `16bebc9f0810d3aad22bb11c2f41130d5dfdb6ea79386ef509f1259a86d7d950` |
| Focused JUnit | `325305f8bf5629112a26b72aa23a1aaffa36b0615b073182e592b030a58ea9b7` |
| Independent reversible wire comparison | `0e952e20c5830ce19d4720e7d05767479952a78c629c5f64b87c53a9cc8159ef` |

Dependency bytes are not attested. Python network/command guards do not claim
OS-wide isolation. These mocked pipelines establish neither route capacity nor
scientific acceptance. This packet targets the exact assigned A13 parent;
AGY's subsequent composition onto a newer #5158 head still requires review and
CI. The [PR-description draft](pr-description.md) and two issue drafts are local
handoff material only. No generation, scoring, publication or branch deletion
is authorized by these test results.
