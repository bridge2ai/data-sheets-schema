# Assignment to Codex helper 2: CI failures that point at the merged cache repair

From the Claude lead, 2026-11-13. Short names and rules are in `claude-lead-helper-context-20261112.md` beside this file. This comes after `claude-lead-helper2-three-failure-cases-20261112.md`.

CI on the integrated head `8760de5efe88b5af62e9d77e6335fa7e248017b6` (run 43349937412; inventory `R/notes/development_efficiency_20261111/handoffs/lead-ci-run-43349937412-failures-20261113.json`) failed with 112 ids; shards 1, 5 and 8 were cancelled at the 45-minute limit, so more may be hidden. The head is the lead's merge of your cache repair `e079e2f3a` onto `672057484` (the merge of helper 3's stack onto `6561dac3c`). Three groups point at the cache repair:

- `tests/test_native_permission_probe.py`, 8 ids: `ValueError: PYSTOW_HOME must be the registered attempt helper-cache` (raised in `native_helper_cache.py:32`): the probe's fixtures or the probe path do not supply the declared cache variable.
- `tests/test_native_lexical_ancestry.py`, 6 ids: `test_actual_reservations_preserve_physical_checks_and_first_errors` now raises where it returned, or raises `KeyError` where `ValueError` is expected: probably the cache directory's creation inside the reservation path.
- `tests/test_direct_keep_awake.py`, 2 ids: `json.decoder.JSONDecodeError: Extra data: line 1 column 4` in `test_real_legacy_launcher_keeps_guards_and_receipts`: attribution unknown.

1. Confirm each by running the failing file at `672057484` and at `8760de5ef` in a CI-like export outside every `d4d-executions` path.
2. For those that are yours, fix them on `codex/native-helper-cache-home-20261112`, one commit per cause, without weakening what any test asserts and without relaxing the HOME guard or the reservation's physical checks. For a production refusal that is right and a fixture that is wrong, fix the fixture and say so.
3. Tell the lead which failures are not yours, with the evidence.

**Then Case C of your previous assignment is released** (added by the lead at 03:05Z). The owner's decision D143 stands: two registered sets of run limits, the canary's ($90, 21,600 s) and one production set ($400, 43,200 s). The lead had recommended changing it to one set, and has withdrawn that recommendation: under one set the canary would become the stratum's frozen reference, so any repair the canary reveals would end the stratum, whereas with two sets the canary is a shakedown and repairs can go in before the CHORUS reference pilot. Write Case C as specified there, after the CI fixes above, on its own branch from the published head.

Bounds and handoff as before: offline; nothing pushed; no GitHub write; protected files unchanged. Update `R/notes/development_efficiency_20261111/handoffs/codex-h2-public-path-proof-20261112.md` with a section for this, answer first.
