# Wave 5 task 4: #5213 / #5139 composition

**The relative-path change composes cleanly with current A13/preflight code:
166 focused checks pass.** No source repair or conflict resolution was needed.
This supports historical input lookup and conventional-layout provenance, with
the prior F2 portability limitation retained. It does not certify movable live
registrations, a full-corpus evaluation, launch, or scientific acceptance.

## Exact composition

- Owner head: `68e0fffdfebbe77a6a24a0e086aaf3ebeb1999b5`.
- Incoming current A13/preflight base: `04799422669fb2bd9f571bf8c0800dfc4b0ef008`.
- Merge base: `f8c5ac73caba610d40c49aaceddb31ead3590a72`.
- Two-parent merge: `db1f384e91d78b590373b4b552327b7c7d7efe6b`, with the owner
  head first and incoming A13 head second. The merge used `--no-ff` and stopped
  before committing for inspection. There were no unmerged paths or conflict
  hunks to retain. Git's output was:

```text
Auto-merging src/data_sheets_schema/api_launcher.py
Auto-merging src/data_sheets_schema/api_runner.py
Auto-merging src/data_sheets_schema/provenance.py
Automatic merge went well; stopped before committing as requested
```

- Frozen tested head: `5146ec2ca5dfa0b35c7d8942c719cfae1fff4218`, which adds
  the unchanged prior independent path probes, their historical observation
  helper, and the prior marker-aware validation driver.
- Isolated worktree: `/private/tmp/d4d-codex-wave5-5213-20261028`;
  local branch: `codex/wave5-5213-composition-20261028`.

The six-file #5139 patch relative to its merge base has exactly the same stable
Git patch ID as the composed delta relative to A13:
`893ce2a2b61e97fdf94faa993ed3f8c3339482d0`. Thus the automatic merge preserved
the scoped launcher checkout-root guard, RunSpec/provenance normalization,
historical lookup fix and existing tests. A13's preflight resource/pin checks,
receipt changes, launcher attribution and command parsing remain incorporated.
No reviewed implementation was manually changed.

Protected prompt/hash/shared-generation files, the canonical decision record,
and historical run/archive paths are identical to incoming A13. Changes already
present on that approved incoming base were inherited by the merge, not rewritten.
No existing owner worktree, provider, network, GitHub, push or main merge was used.

## Retained findings and acceptance scope

**F1 remains repaired.** The exact lexical nested path under
`archive-copy/data/preprocessed/...` survives hash-pinned Git recovery. Foreign
absolute paths use the historical tail fallback; symlink escape, traversal and
embedded NUL checks continue to refuse. The six original causal cases pass. The
same cases also appear in the inherited owner tests, so their repeated execution
does not represent additional unique defects.

**F2 remains scope-qualified.** In-checkout RunSpec inputs and conventional-layout
provenance can be relative. Progress input identities, flat-output provenance and
registration pins intentionally remain absolute and owner-bound. The original
scope probe confirms this on the composed code; it does not assert that moving
those records is supported. Narrow the PR/issue completion claim accordingly and
retain or split any portable-locator design work. Do not remove executable/input
authority to make path strings relative. Remote PR wording was not queried.

The unchanged historical probe reads the actual 10-20a and 10-22a CHORUS
provenance blobs from cached Git head
`ada98b56b73b60217ccacf02fef2af4393d6ecae`. Both recorded bundles and pinned
manifests match in this separate checkout; each reconstructs eight chunks.
The respective original provenance byte SHA-256 values remain
`3590ec17006cbbdf2f64f47bd5965b8e3453fe388202853531b289d31a1f36df`
and `c0d336563612b4e2244a1438ba0298bde1ad1a76623e622c2036718a94333eca`.
This read-only compatibility result does not change their assisted/invalid
dispositions. The probe writes only new synthetic temporary outputs and builds
its new registration with `write_to_disk=False`.

## Validation

| Module | Passed |
| --- | ---: |
| `test_5139_relative_paths` | 4 |
| `test_arm_comparison` | 65 |
| `test_api_launcher` | 54 |
| `test_wave3_5139_review` | 6 |
| `test_wave3_5139_paths` | 1 |
| `test_preflight_resource_authority` | 31 |
| `test_wave4_5095_review` | 5 |
| Total | 166 |

Zero failures/errors/skips. One unchanged `corpus` comparison case is explicitly
deselected using `--mark 'not corpus'`, matching the prior focused review scope.
Pytest reports 115.90 seconds; the source-attested driver reports 123.565019 seconds.
All tracked source remained unchanged and before/after imported-source
attestations completed. Python used the physical venv with `.pth` loading and
plugin autoload disabled, removed provider credentials, and offline audit hooks.
Third-party package bytes and arbitrary subprocess network isolation are not
attested. The selected suite is not a claim of full PR CI completion.

The exact executed command, from the frozen worktree, is preserved in
`notes/reviews/wave5_5213_validation_2026-10-28/run-01/plan.json` and
`pytest-command.json`. To reproduce, use a clean worktree at the tested head and
a fresh external result directory:

```sh
/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python -B \
  scripts/adhoc/validate_wave3_20261027.py \
  --output /private/tmp/d4d-wave5-5213-validation-replay \
  --base 04799422669fb2bd9f571bf8c0800dfc4b0ef008 \
  --expect-head 5146ec2ca5dfa0b35c7d8942c719cfae1fff4218 \
  --module test_5139_relative_paths --module test_arm_comparison \
  --module test_api_launcher --module test_wave3_5139_review \
  --module test_wave3_5139_paths --module test_preflight_resource_authority \
  --module test_wave4_5095_review --mark 'not corpus'
```

## Compact retained evidence

Full raw evidence, source inventories, import attestations and synthetic cases
remain at `/private/tmp/d4d-wave5-5213-validation-20261028`. The new packet at
`notes/reviews/wave5_5213_validation_2026-10-28/` retains the compact original
outcome, plan, log, JUnit and bootstrap JSON verbatim. Its manifest records
byte hashes and lengths of the external inventories without embedding them.
This branch adds no new compressed source-inventory archive. Existing A13
evidence is preserved through ancestry.

| Artifact | SHA-256 |
| --- | --- |
| Compact manifest | `05fd0f145c98479a9c4d521b0be2f7cff4a5897c761edc6c550a8cadf375b10b` |
| Outcome | `3720c27bb6df0b7f520923a59354a2324a61fce2beb10387c416d712dc0e0c40` |
| JUnit | `1742cb785d01e81eb26b716e1e2a3b16be490ac8842b8eb1276425219bfc07a8` |
| Compact preservation helper | `e2057f41cc3022202918321e3dd6047e1348581a63f9d133d7f0ae04e7939f05` |

All helpers are retained under `scripts/adhoc/`, including the historical path
probe, validation/common driver, compact preservation helper and its existing
archive-helper dependency. Preserve this exact packet for Claude's review and
AGY's later authorized publication. Merge order remains incoming A13 before this
relative-path change; this packet does not incorporate sibling #5211 or #5210
changes and does not claim their combined composition has been tested here.
