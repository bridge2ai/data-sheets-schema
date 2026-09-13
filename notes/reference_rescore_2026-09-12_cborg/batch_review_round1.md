# Codex Adversarial Review

Target: branch diff against ffd5b8636
Verdict: needs-attention

Do not ship: Ctrl-C breaks the promised draining and evidence retention.

Findings:
- [medium] [P2] Isolate workers from foreground interrupts (scripts/reference_rescore_cborg_batch.py:175-176)
  Workers inherit the controller’s foreground process group, so Ctrl-C interrupts every worker. The frozen runner catches only Exception; KeyboardInterrupt bypasses candidate copying and receipt writing while cleaning its temporary workspace (reference_rescore.py:522–550). Up to four paid attempts can therefore lose candidate files and finish without receipts instead of draining. Four synthetic workers and an in-memory execution of the frozen runner reproduced this behavior.
  Recommendation: Launch workers with start_new_session=True. Handle controller interruption by stopping new launches, draining active workers, and recording the stopped result.

Next steps:
- Add an offline process-group SIGINT test verifying worker completion and evidence retention.


Recorded as #1341. No scheduler pilot or fill had started. The correction requires a new registered scheduler hash, offline interruption tests and a fresh review before its one-rating pilot.
