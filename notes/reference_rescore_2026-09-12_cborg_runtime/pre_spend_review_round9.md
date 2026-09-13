# Codex Adversarial Review

Target: branch diff against 8f2f327cb
Verdict: needs-attention

Block on one P2: the CLI hash gate can validate a different executable from the one launched.

Findings:
- [medium] [P2] Check the CLI using the runner’s effective PATH (scripts/reference_rescore_cborg_batch.py:198-202)
  The gate resolves claude using the scheduler’s PATH, but reference_rescore.py:517–518 prepends the Python executable directory before the adapter resolves claude again. If that directory contains another claude, the pinned binary passes verification while the adapter selects the other executable. A version mismatch consumes the reviewed retry by creating another failed attempt; matching version text permits an executable with different bytes to reach os.execve. An in-memory probe reproduced the selection mismatch.
  Recommendation: Resolve and hash claude using the runner’s effective PATH before attempt creation, rejecting any shadowing of the registered binary. Add an offline regression with conflicting executables in the pinned and Python directories.

Next steps:
- Align executable resolution and rerun the offline scheduler checks.
