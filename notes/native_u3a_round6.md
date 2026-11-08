# U3-A Round 6: R9-3 capture identity

Authority: the 2026-11-08 Round 6 brief and 03:50Z ruling. The supplied
proposal applied without adaptation. The only production change is its local
reader import and two runtime reads in `native_execution_registration_v2.py`.
A's interface, control map, loader and guard are unchanged.

## Local review ledger

Online issues/PRs are forbidden by the explicit offline/no-push brief. Findings
are retained here for later filing; none is silently discarded.

- **R6-A — unstable validation HEAD:** the first full A run overlapped a
  provenance-helper commit. Two tests correctly refused changed dependency
  identity (306 passed, 2 failed). Retain this run as development evidence and
  repeat the complete suite with HEAD fixed. No guard change is warranted.
- **R6-B — probe discoverability:** a C-only probe initially had a `test_`
  basename under `scripts/adhoc`, which would make whole-tree discovery try
  importing absent C modules in A. Renamed it to `probe_`; the snapshot helper
  copies it into a pytest test filename only inside the C snapshot.

## Reproduction and limits

`run_native_u3a_tests_20261107.py` now restricts outputs to the single Round 6
scratch root. It retains source-origin checks, a credential-free environment,
OS network denial, quiet-window cooperation, at most two workers, a 3600-second
deadline and observed descendant cleanup evidence.

`prepare_native_u3a_round6_c_snapshot_20261108.py` archives the locally available
final C commit `d205ceddee386acd4749b779cc18b3e78d094b93`. Only A's exact current
registration source and test tooling are overlaid. C source bytes are unchanged;
the scratch commit binds the real C loader and current package closure. The
probe uses the real `loaded_controls` and verified evidence module, proves the
stale capture's class differs, then calls `verify_preparer -> prepare ->
spec.instruction` with the current exact capture class. Synthetic input fixtures
permit only Git subprocesses. This is preparation identity evidence, not full
C/D admission, native execution, or closure of the protected U1 hook/R9-4.

`run_native_u3a_round6_mutations_20261108.py` retains the original fifteen probes
and matched controls. Resolve all plans first, run MA, inspect its persisted
witnesses, and only then run the remaining probes serially. Each mutation and
restoration is committed in the assigned A worktree. Do not run other A tests
or change HEAD during a probe.

`audit_native_u3a_round6_20261108.py` checks retained outcomes, XML, source and
network witnesses, restoration trees and final production scope. The final
external report is `plans/reviews/native_u3a_2026-11-07.md`, Round 6. All scratch
and basetemps are retained under `scratch-native-u3a-r6`; no cleanup is required
by this round's brief.
