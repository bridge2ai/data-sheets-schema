# Timing qualification for the reference reports (#1353)

The original CHORUS v8 rep3 rubric20 output records `2026-09-12T15:46:06Z`, outside its retained launcher interval of `2026-09-12T22:46:06.658666+00:00` to `2026-09-12T23:00:36.885219+00:00`. Its terminal narrative says it used a filesystem timestamp after clock commands were denied. The original output and all scoring evidence remain unchanged.

The dated completion reporter now inventories every accepted model timestamp alongside its original successful receipt, with both hashes. It classifies interval consistency without claiming that an in-interval value is independently verified or that an out-of-interval value proves fabrication. Execution times and condition boundaries continue to use launcher receipts. All four derived reports carry the qualification, and `results.json` includes every original timestamp and receipt interval.

This is a report-only change. It does not modify the running scoring manifest, prompts, definitions, permissions, deadline, original outputs or acceptance gates. The general agent-contract issue #667 remains separate from this condition's reporting resolution.

Offline validation passed 14 checks: UTC and offset-equivalent values, an out-of-interval value, naive/missing/invalid metadata, unchanged original bytes, and rejection of altered output/receipt hashes, duplicate/missing bindings, a source from another job, failed receipts, naive launcher times and reversed intervals. Python 3.9 syntax parsing passed. No provider calls were used. The complete 56-rating inventory and final report review remain required after the batch drains.
