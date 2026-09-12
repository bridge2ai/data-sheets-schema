# Codex Adversarial Review

Target: branch diff against c335c2ec1
Verdict: needs-attention

Do not ship: one P2 launch race remains. Synthetic SIGINT/SIGTERM draining probes passed; all 309 checked hashes match, archived originals and canary evidence are preserved, and HEAD remains 7ed6a76ec.

Findings:
- [medium] [P2] Make stop observation and worker launch mutually exclusive (scripts/reference_rescore_cborg_batch.py:187-191)
  A signal can set stop_signal after the guard passes, including during command(job_id), yet Popen proceeds unconditionally. Read-only synthetic probes reproduced this for both SIGINT and SIGTERM: stop_signal was set before Popen entered, but another worker launched and completed. The isolated worker never checks the controller's stop state, so this can start another paid rating after an observed stop. Existing interruption tests signal only after all four workers are active.
  Recommendation: Prepare launch arguments before the final stop check, then serialize stop handling with dequeue/spawn. Add deterministic tests delivering each signal between the current guard and Popen, requiring the job to remain unlaunched.

Next steps:
- Fix the launch race, refresh the scheduler registration hash, and rerun boundary and process-group interruption tests.


Recorded as #1342. No scheduler model calls had occurred. The correction requires refreshed registration and review before the planned pilot.
