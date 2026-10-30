# E3x × #5096 bounded relocation repair

Offline evaluation repair, begun 2026-10-29 and resumed after a machine reboot.
Validation is in progress; this ledger does not yet claim all acceptance gates pass.

## Inputs and merge record

- Starting branch: `codex/wave7-e3x-fixes-20261029`, `709099dbc2c621b47b0e9d0f401a6a386da5d400`.
- Main merged with `git merge --no-ff origin/main`: `50bc50af678ae5216b3985c340fe1344da26c05e`.
- Merge commit: `28f13294a006eacd5ae3f769b0d74b643cf9d2c0`. No textual conflicts.
  Git automatically composed `notes/arm_comparison.md`, the evaluation resolver,
  and its tests. Other incoming files are inherited from the authorized main merge.
- Repair commit: `3ea09cac3`; generated report refresh: `c0840e780`.
- The complete provisional analysis was read before editing. Its retained Git
  source is `codex/wave7-suite-tools-20261029:notes/reviews/wave7_arm_relocation_provisional_2026-10-29.md`.

The semantic conflict was E3x's universal external-path refusal versus #5096's
supported preprocessed-tail relocation. The composed control reproduced `match`
where the E3x assertion expected `unknown`. A cold focused invocation also exposed
a provenance-import metadata read caught by the trap; warming the #5096 positive
first isolated the semantic assertion. Those pre-reboot logs were lost, so they
are historical observations, not the retained acceptance evidence below.

## Implemented contract and review

`arm_comparison._lexical_relative` preserves already-owned paths before considering
foreign relocation. A foreign absolute path must contain exactly one adjacent
`data/preprocessed` pair; counting precedes normalization so traversal cannot hide
repeated pairs. Its tail maps under the selected root. Both lexical and realpath
containment remain mandatory. Live disk checks and pinned historical-manifest
recovery use the same lexical policy, including the entire prefix of owned paths.

The shared provenance helper is unchanged by the repair. Recorded pins, recovered
bytes, disk identity, and cross-arm identity remain separate evidence. The E3x test
now asserts the supported positive and explicit unknowns for unsupported/ambiguous
inputs. Both ambiguous candidate files deliberately exist with matching bytes;
neither existence nor matching bytes may choose a tail. Separate tests refuse an
ambiguous manifest without historical lookup and preserve owned repeated pairs
through exact Git recovery. The bounded-read traps and #5096 positive are retained.

The renderer and per-record refusal suffix distinguish supported relocation from
unsupported or ambiguous cases. `scripts/arm_comparison.py --no-figures` refreshed
the committed report. The reviewed diff changes only that explanatory paragraph;
all measurements and tables are unchanged. No figures or ratings were produced.
Separate read-only diff review found no additional resolver defect.

## #5213 scratch composition

Temporary merge input: `b6fba59465051230f8082c7c3cdb5c1a05ce3fbf` onto `c0840e780`.
Every textual conflict and its resolution:

| Path | Conflict | Resolution |
|---|---|---|
| `src/data_sheets_schema/evaluation/arm_comparison.py` | Helper documentation, foreign-tail fallback, recovery comment | Retain repaired blob `9fc613b4c14c1fc6d0c7faae8d4179f1dfc6c1a7`. It already includes #5139's shared lexical policy and NUL refusal, plus explicit ambiguity refusal. |
| `scripts/adhoc/preserve_wave5_validation_20261028.py` | Add/add; retained-evidence explanation | Use the packet's reviewed blob `09c84644d1a372e36a2dacaf3b001117cb220e06`. |

Resolved scratch tree: `d70d4926b044489427af70879da670d6affcc952`.
The incoming tests merged automatically; none were dropped.
The post-reboot run of complete `test_arm_comparison.py`,
`test_5139_relative_paths.py`, `test_wave3_5139_review.py`, and
`test_wave3_5139_paths.py` passed **92 tests**, exit **0**, in **171.68 seconds**.
The temporary merge was then aborted. The source, tests, global provenance helper,
API runner, and launcher were verified restored to the repair head. #5213 is not
part of this branch's ancestry.

## Retained validation evidence

Evidence directory: `tmp/e3x-relocation-validation-20261029/` in this worktree,
ignored by Git and persistent across reboot. Pytest basetemp and bytecode remain
under `/private/tmp/d4d-e3x-relocation-20261029/`. The check launcher records HEAD,
interpreter, source/test/helper/workflow/timing hashes, host load, log, JUnit, and
exit status. Provider credentials and proxy variables are unset. The macOS test
sandbox allows loopback fixtures and denies external network connections.

Interpreter: project `.venv/bin/python`, Python **3.13.12**. This is a local serial
execution of CI's partition, not a Python 3.12 CI result. FAIRSCAPE was populated
offline from pinned local Git object `8c80311d7d8b0fadac07dca9567d632103691f48`.
Pre-existing `tests/__pycache__` files date to 2026-10-29 00:01 and were preserved.

The initial post-reboot composition attempt lacked the external basetemp parent:
15 passed and 40 setup errors before interruption. The launcher now creates the
parent. Its one-test canary passed and persisted non-empty log/JUnit plus exit 0
before the complete successful 92-test composition rerun. The failed evidence is
retained as `composition-5213.*`; acceptance evidence is `composition-5213-verified.*`.

Fresh whole-tree collection, complete CI collection, six ordinary PR shards,
four dedicated API lanes, E3x/D52 acceptance, and separate offline CI controls
remain to be recorded here. No push, GitHub operation, provider call, or rating
campaign is authorized. Any unrelated findings will be retained locally for the
lead rather than filed online.
