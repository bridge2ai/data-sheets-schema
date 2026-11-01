# PR #5212 round 4: R2 refused-start diagnostics

Base: `5c407c87fd895dfd1b96b160b48399ec9d1713cb`, 2026-10-28.

Refused-start messages retain the expected/found labels but replace every full
hexadecimal hash with its first eight characters followed by
`…(unverified, not a resume anchor)`. This applies to the refused record and
the raised exception; the original exception context is suppressed in normal
tracebacks. Malformed expected heads and broken-chain diagnostics use the same
boundary. Accepted start/stop records and journal admission rules are unchanged.

The R2 regression captures stdout, stderr, exception text, formatted tracebacks,
and logs, extracts every 64-hex token, and attempts each as the expected resume
head. It also requires that no full hash is emitted. The real-runner d′ test
reproduces the reviewer's 10-22a reset, re-chained latches, and moved checkpoint.
Refusal makes zero dispatches and token-count calls, preserving journal/ledger
bytes. A positive control supplies the forged head directly from test setup and
completes with three scripted dispatches, demonstrating why disclosing it matters.

## Validation

Run with `scripts/adhoc/pr5212_r4_checks_20261028.py` using the existing Python
3.13.12 project environment. Every pytest invocation uses
`--basetemp="$TMPDIR/codex-5212r4-pt"`, disables pytest's cache, and removes
provider keys/base URL from its environment. Test clients are scripted and offline.
Commands, logs, JUnit XML, interpreter identity, lockfile/source hashes, and
source-stability checks are saved per group.
The `pytest.log` files remain local under the existing ignore rules; commands,
structured outcomes, JUnit XML, and parity summaries are committed.

| Final group | Result |
| --- | --- |
| Canary | 1 passed |
| Focused diagnostic checks | 6 passed |
| Latch journal, D41, full 11-module F2 set, R2 regressions | 538 passed (851.80 s) |
| Four routing API cases | 4 passed (2438.87 s) |
| Request parity | 6 passed (142.96 s); 8/8 bodies identical in both event contexts |

The 538-test selection contains all 29 exact F2 nodes listed in
`notes/reviews/pr5212_d55_f2_nodes.txt`. The d′ scenario is included in this count.
The canary and focused checks are repeated within the full selection.
All final groups report zero failures, errors, or skips, and unchanged pinned
source bytes. The two parity summaries are retained under `final/parity/`.

## Retained attempts

- `collection/`: successful collection before execution; 538 core/F2 cases,
  four routing cases, and six parity cases.
- `before/canary/`: the strengthened regression fails on the original code
  because the forged head is printed. These historical failure logs intentionally
  preserve the pre-fix output from a synthetic test fixture.
- `after/canary/`: the same launcher and canary pass after the production fix.
- `after/core-f2/`: interrupted after six test failures: two older assertions
  required the leaked head, and four new CLI cases assumed separate stderr
  capture on Click 8.1. The assertions and capture handling were corrected.
  Production code did not change after the successful canary.
- `final/`: acceptance on the final source/test bytes; earlier attempts do not
  substitute for these results.

Raw JUnit failure output in `before/canary/results.xml` and
`after/core-f2/results.xml` retains pytest's trailing spaces as original evidence.
The source, tests, helper, documentation, and final evidence pass `git diff --check`.

This is scoped offline acceptance, not a full-suite or CI claim. No push, GitHub
operation, provider call, protected file, STATUS.md, decision record, retained
run directory, or data/ATTIC content is part of this change.

A separate read-only diff review checked the refusal boundary, traceback
suppression, CLI capture, replay assertions, and d′ positive control. It found
no additional R2 issue requiring a change.
