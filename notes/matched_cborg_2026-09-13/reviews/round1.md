Reviewed public commit `32b1b6e811bec9e4da10b29780e27359478a954c`.

# Codex Adversarial Review

Target: branch diff against 194fb9ce17edcae3f038605543abc041e9cb9624
Verdict: needs-attention

First CHORUS API canary: not ready. Incomplete streams can release budget reservations. Exact commit reviewed; 373 public pins, 55 extraction hashes, 36 study descriptions and 16 matched source/profile pairs checked. Local-only pins, historical originals and full launcher/SDK execution were not verified. Committed CI and independent-review gates remain pending.

Findings:
- [high] Incomplete streamed responses settle before completeness validation (notes/matched_cborg_2026-09-13/budgeted_cborg.py:184-187)
  ObservedStream.get_final_message() calls finish(), which settles the reservation, before api_runner checks stop_reason. The runner explicitly handles streams with message_stop but no stop_reason as incomplete (api_runner.py:4201–4211). Such a response can retain initial zero or partial output usage, yet the controller marks its charge settled. An in-memory probe reproduced this and admitted another reservation afterward. This violates the unknown-charge stop policy and can undercount cumulative spending.
  Recommendation: Preserve the response but retain its pending reservation until stream completion and a valid terminal stop reason are established. Add an offline SSE regression with message_stop, null stop_reason and partial usage; assert that subsequent admission remains blocked.

Next steps:
- Fix premature settlement and rerun controller and real-SDK offline regressions.
- Regenerate affected pins and preflight evidence, then obtain passing CI and review for that exact registration.
- Before launch, verify local-only pins and historical preservation in the authorized execution checkout. Native agentic/evaluator controls and production costing remain subsequent review steps.

Finding tracked in [#1765](https://github.com/bridge2ai/data-sheets-schema/issues/1765).
