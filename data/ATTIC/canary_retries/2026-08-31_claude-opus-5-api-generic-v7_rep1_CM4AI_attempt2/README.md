# CM4AI production canary, attempt 2 (archived 2026-08-31)

Degraded by proxy instability, not model compliance: full-phase attempt 1
was a header-only dud (998 output tokens in 20s, stop_reason end_turn);
the in-run retry produced only 22,718 output tokens (~8.8k reasoning) vs
attempt 1's 102,980, and every later phase ran on that thin base — 393
populated leaves (vs 427), receipt 93/119 verified with 24 adjacent,
131/361 slots receipted, no validation, no canary verdict. Same evening
as the VOICE 5-attempt stall (#777). Arm paused pending CBORG diagnosis.
