# Final-generation handoff reports artifact sizes and route gates inaccurately

Lead review found that G1's handoff table reports sizes of 2167, 1094 and 1697 bytes for the final evidence JSON, JUnit XML and log; the persisted artifacts are 3669, 1081 and 2570 bytes. Its source line counts also describe an earlier draft. Correct or remove stale incidental counts and rely on inspected artifacts.

The plan's final run-ready sentence also mentions native acceptance without qualifying the chosen route. Native-only checks remain required for a native run, but must not become prerequisites for an API-only run. Clarify that each chosen execution route retains its existing applicable gates; this task adds no cross-route gates.

The observed passing test results remain supported by the actual logs. No generation run or readiness certification is implied.
