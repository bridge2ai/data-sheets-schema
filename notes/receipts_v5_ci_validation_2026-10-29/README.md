# Receipts v5 CI follow-up for #5364

The production fix is commit `49052c75d248264380903aaa661f86d50e8f69da`, on top
of `93edcc76c`. The complete ledger is [validation.json](validation.json).

The rejected expression was `any(...)` over `_QTY_UNIT_RE.finditer(source_text)`
in `verify_tool_receipt`'s `unit_convert` branch. The scanner treated the
generator-bound regex match as a projected receiving object and could not
classify the effect of its `.group()` calls. An explicit loop now evaluates the
same predicates in the same order, sets `observed`, and breaks at the first
match. Empty-input behavior and short-circuiting are preserved. This follows
the existing explicit regex loop used elsewhere in the receipt parser.

The scanner and its configuration are unchanged, including against the pinned
main comparison. Other regex iteration sites remain intact. Both the complete
scanner module and the full CLI scan accept the revised code. The read-only
review of the production diff and validation helpers found no further code
issues; no additional production changes were made.

| Completed scope | Modules | Passed | Skipped |
| --- | ---: | ---: | ---: |
| Complete specificity scanner module, final rerun | 1 | 357 | 0 |
| v5 acceptance suite | 19 | 899 | 19 |
| Other receipt/scanner and required neutrality modules | 61 | 3,218 | 1 |
| CI native phase-history module | 1 | 28 | 0 |
| Total, excluding duplicate diagnostic runs | 82 | 4,502 | 20 |

All final module executions exited zero. The related suite includes the full
18-case API-routing module and all four cases CI normally isolates in dedicated
jobs. The resources skip requires a symlinked `.venv`, which this worktree does
not have. No timing failure required an isolated retry.

The module inventory includes ignored files in its search for receipt/scanner
references under `tests/`, plus the skill's three required neutrality modules.
The native phase-history module invokes the receipt checker in CI's separate
notes lane. Other notes modules that only classify receipt-command text are
outside this implementation coverage claim.

The refreshed scan uses the requested `origin/main` baseline commit
`49dd8f0eb7d9a6a349fd3bab8749804786ddb82b`. Scanner bytes match between the two
trees. Both scans exited 1 for existing violations; neither exited 2.

| Category | Main hits | Head hits | Model-facing, both | With reason, both |
| --- | ---: | ---: | ---: | ---: |
| Grand Challenge project | 1,079 | 1,079 | 322 | 403 |
| Program | 2,477 | 2,478 | 2,374 | 2,368 |
| Biomedical/clinical | 1,688 | 1,689 | 1,393 | 1,348 |

There are **96 violations in each tree and zero new findings**. The comparison
retains duplicate finding counts and ignores only relocated line/end-line
positions. See [scan_comparison_resumed.json](scan_comparison_resumed.json).
At final verification, the shared local `origin/main` ref had advanced to
`50bc50af678ae5216b3985c340fe1344da26c05e`. The comparison remains pinned to the
requested `49dd8f0eb`; this task performed no fetch or remote-ref update.

All four original inertness scopes were rerun against A13
`148c869dde865915221db847b2e89f15f319b365`, after rebuilding the baseline and
saved canary inputs from local Git objects and verifying one-record canaries.
Their durable raw evidence survived the reboot and was rehashed afterward;
production source and tests have not changed since those runs.

| Inertness scope | Result |
| --- | --- |
| Corpus: 54 records, 48 checked, 36 snapshots | Identical normalized bytes; SHA-256 `52b997f6f75365ac7d80400ddf7aca145f062f0c3edff82b76dccecd84fa7ed7` |
| Report: 335 records, 325 checked in each v7/v8 mode | Identical normalized bytes; SHA-256 `c659ce494b0545a077abcae29a593ad0dff572a1cbb9ab99f25370ce91c65018` |
| Both saved CHORUS request/result scopes | Identical normalized bytes; SHA-256 `830eb7055ba303dc03ee40352b61552d0ca1308a82f93a5a18aebe5a3f07f3d6` |
| Four registered assembly identity keys | Identical `v10_sg1_r25`, `r24_rc1`, `r8_rc1`, and `descriptor_v1` identities |

Normalization replaces only each checkout's absolute path with `<TREE>`. The
assembly ledger also preserves the previously documented N11 routing identity
difference outside those four identity keys. The first CHORUS scope matches its
saved terminal result `_2.json`, as in the prior comparison. Details are in
[inertness/inertness.json](inertness/inertness.json).

Whole-tree `pytest --collect-only -q` was run after the reboot and exited 2 with
17 historical/environment collection errors. CI's `tests/` collection exited
zero with **20,475 tests**. Using the workflow's exact `utils.pytest_shard`
options selected **3,807 tests in 99 modules for shard 4/6** and **4,257 tests in
96 modules for shard 6/6**. Complete shard execution is not claimed. The
collection errors and unchanged affected paths are recorded in
[collection_issue_draft.md](collection_issue_draft.md); the draft was not filed
because this task is offline.

Validation used the existing local Python **3.13.12** environment; CI specifies
Python **3.12**. Tests ran serially in this real worktree, with provider keys
removed, network/live-command guards, pytest scratch and JUnit output outside
the checkout, and caches disabled or redirected outside it. The local FAIRSCAPE
submodule was populated from existing objects at its exact gitlink pin.

The offline adapter admits only the exact temporary echo-only `claude --version`
fixture used by the tests. It checks the owned scratch path, exact arguments,
and complete script bytes. Installed agent commands remain forbidden. Its
passing one-test canary preceded the resumed module batch.

Historical diagnostics are preserved separately from final counts:
`causal_before.log` reproduces the original ConfigError; `scanner_harness_failure`
records an initial JUnit-placement hygiene error despite passing assertions;
`resume_fixture_canary` records the original guard rejecting the inert version
fixture; and `related.log` is the interrupted pre-reboot attempt. Final related
results are the complete `related_00` through `related_60` logs/XML and
[related_checkpoints.json](related_checkpoints.json). The final scanner result is
`scanner_resumed`; the earlier successful scanner run is retained as history.
The original causal traceback retains three trailing-space lines emitted by
pytest. The complete whitespace check reports only those raw-log lines;
authored source and documentation pass the whitespace check.

The runner is `scripts/adhoc/validate_receipts_v5_ci_20261029.py`, invoked through
the existing `-S -B` environment bootstrap. Its `collect`, `checkpointed_related`,
`offline_related`, `rescan`, `verify_surviving`, and `summarize` phases retain the
commands and hashes. `selected scanner_resumed
tests/test_generation_specificity_skill.py` performs the final complete scanner
rerun. Checkpoint reuse requires matching receipt-source bytes and a completed,
passing execution; the final ledger also verifies the complete module roster.

No protected source, decision record, workflow, STATUS file, run directory, or
`data/ATTIC/` content was changed. No push, GitHub command, provider call, or
outbound network call was performed.
