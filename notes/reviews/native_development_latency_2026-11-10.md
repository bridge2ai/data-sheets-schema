# Native D4D development latency and canary strategy

Yes—the development loop has become too expensive. CHORUS is not the immediate problem. We’ve accumulated integration and verification work around generation, and we’re repeatedly running expensive tests before their prerequisites work.

What changed: earlier local synthetic native runs completed in about 3–4 minutes. Today’s integrated path adds or reconciles source verification, schema reconstruction, permissions, subscription freshness, reservation, and replay checks. Several layers repeat the same expensive work: one public launch performs 13 execution-registration verifications and 84 selection rebuilds. The current tests spend 10–11 minutes, then fail before generation starts. These are different implementations, so that comparison isn’t a controlled performance benchmark. [Profiling evidence](/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/plans/reviews/native_u3k_2026-11-09.md:89)

There’s also a measurement complication: profiling increased fixture CPU about 4×, and the overhead of another test observer remains unresolved. We should isolate that before prescribing another large runtime redesign.

CHORUS remains a reasonable first real canary. The current failing test already uses a fictional dataset with eight short source lines and one chunk, with no model calls. Shrinking CHORUS won’t fix the expensive checks that precede dispatch. CHORUS should test realistic generation after this tiny integration case works. [Current fixture](/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-native-u1u3/tests/native_shared_fixture.py:114)

CI is slow, although I haven’t established a new regression. Recent successful runs took [31 minutes on a PR](https://github.com/bridge2ai/data-sheets-schema/actions/runs/42734850581) and [55 minutes on main](https://github.com/bridge2ai/data-sheets-schema/actions/runs/42676577740). Test execution dominates; main also experienced scheduling delays.

The local feedback loop is particularly revealing:

| Local test group | Time |
|---|---:|
| 554 execution tests | 1 minute 50 seconds |
| 8 reservation tests | 30 minutes |
| 5 lifecycle tests | 31 minutes |

Nine failures in those last two groups stopped at freshness before reaching the behavior being tested. That’s about an hour spent largely rediscovering a known prerequisite failure. Our orchestration is contributing to the delay. [Cohort evidence](/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/plans/reviews/native_u3k_2026-11-09.md:322)

I recommend smaller, explicitly gated work units:

1. Measure the observer overhead, using a matched diagnostic with unchanged correctness checks.
2. Fix one boundary: the tiny fixture must reach reservation within the existing freshness window. Test ordering and changed-input refusals with cheap fixtures.
3. Verify that boundary with the real schema, then run one genuine synthetic completion and one injected failure.
4. Run affected cohorts once those prerequisites pass. Mark dependent cases blocked meanwhile; don’t repeatedly execute them against the same known failure.
5. Run full CI at a stable integration checkpoint, followed by the authorized CHORUS canary.

The immediate priority should be a cheap, passing admission-to-reservation test, followed by removing measured redundant work. More whole-suite runs or a smaller CHORUS corpus won’t solve the present bottleneck.

## Native agentic generation versus API generation

Native agentic generation shouldn’t inherently be slower than API generation. We haven’t yet measured a comparable live run showing that it is. The slowdown we’ve observed is in our native adapter and its tests, before a model starts.

“Native” here means driving the Claude Code agent rather than calling the model API directly. Both ultimately use a remote model. Claude Code can add agent turns, tool calls and subprocess overhead, but that hasn’t been measured as today’s bottleneck.

Our current native path repeatedly reconstructs and verifies schemas, registrations and execution permissions. Its synthetic tests make zero model calls, yet take minutes and exhaust the freshness window. That identifies a software/testing problem, not slow native inference.

There are two separate comparisons:

- Adapter overhead: how long until the first model request? This is where we currently have demonstrated problems.
- Generation performance: how long to produce an accepted D4D, including tool use and corrections? We don’t yet have a comparable native measurement.

So I should correct the implication: we have built a slow native launch/test path; we have not established that native agentic generation itself is slower than API generation. Fixing that overhead should precede conclusions about which approach is faster.
