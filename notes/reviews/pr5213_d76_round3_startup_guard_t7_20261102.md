# T7: startup guard refusals lack a configured evidence path

Local review issue draft for PR #5213, D76 round 3, 2026-11-02. No GitHub issue
has been created. Status: failing-before evidence captured; minimal observer
repair committed and unchanged contracts pass afterward. Existing evidence
remains unchanged; complete final-candidate validation is separate.

## Finding

At reviewed source `fc055cc5742d99cee34017f7571e73de5ed0a4a5`,
`scripts/adhoc/run_d76_round3_validation_20261102.py:73` calls the observer's
`install_guard()` before importing/running pytest in the controller and before
executing the worker bootstrap. In
`scripts/adhoc/d76_round3_pytest_observer_20261102.py`, `_DENIAL_PATH` is initially
`None` and is assigned only by `pytest_configure`.

If the installed audit callback encounters a prohibited operation during that
startup interval, its captured opener receives `None` instead of a path. It
raises an incidental `TypeError` before writing the denial row, rather than
persisting the refusal and raising the intended offline-guard exception.
The operation still fails; this finding concerns missing denial evidence and
the diagnostic contract, not a demonstrated network bypass or an invalidation
of every prior run. No live operation was attempted for this review.

## Contracts and bounded repair

The eight existing observer I/O contracts configure pytest before triggering
their audit callbacks. Two new contracts in
`scripts/adhoc/test_d76_round3_observer_io_20261102.py` cover the actual earlier
installation order without contacting a provider or network:

- A synthetic prohibited socket audit event before `pytest_configure` must
  persist its exact event/detail row and raise the intended guard refusal,
  without manufacturing phase evidence.
- Allowed local startup events must create neither a denial artifact nor a
  phase journal before configuration.

The repair initializes the absolute, process-specific denial path at import,
before installing the audit hook, and removes its redundant assignment during
pytest configuration. It retains the existing captured opener, on-demand
creation, late-denial persistence, fatal write errors, and unchanged runner
acceptance rules. It creates no empty final denial file on clean startup.

## Captured baseline and remaining validation

At tests-only commit `13128650c586e1d0de46d71c84d6bd30b697b991`, the validation
owner ran the ten contracts against unchanged observer bytes
`50109df46a128456cb0eda3e356b91b6394c747ecee4508c79392c743f13e2b2`:
**9 passed, 1 error**, reported runtime 0.082 seconds. The new startup-denial
case errors at observer line 79 with
`TypeError: expected str, bytes or os.PathLike object, not NoneType`.
The clean-startup control and eight existing contracts pass.

Evidence: `d4d-executions/plans/reviews/pr5213_d76_round3_2026-11-02/observer-contracts-before-t7/unittest.log`,
SHA-256 `943922a9dc129f789e0a2fd48ad0c48640c1a4bbecfff9ba201829bf7c7cdaa2`.
The frozen contract file SHA-256 is
`46805b3fe1e65ad1160cf350c21f7a960c5f478517b83e83ce7227fb2bd02b71`.

After independent review, local repair commit
`b45b15b173def3f110d3a0cb49d47934747207fa` passed the unchanged ten contracts
in 0.078 seconds under the same sandbox and interpreter settings.
After-log SHA-256:
`01e63b905ca272af9d94edfc7600be4b93bfe1d527766fe24ba5d094f945af2f`.
Repaired observer SHA-256:
`1c5e7bcca891f1b348e5ea791e73caa05e79f2982f992fa2102137e864290286`.
The before-log and contract-file hashes above remain unchanged.

This helper evidence does not retroactively fill the startup logging gap in
prior fc055 runs. No full-suite, merge-readiness or GitHub issue-closure claim
is made here. No production behavior or runner acceptance rule was modified.
