Lead review found that the initial G4 plan-review draft, `notes/final_generation_readiness_20261110/handoffs/agy4-plan-review.md`, section 4, assigns incorrect descriptions to existing issue IDs, including #5788, #5789, #5790, #4034, #3972, #3025, #4044 and #2973.

For example, #5788 concerns structured creator loss, #5789 concerns missing publication dates, and #5790 concerns unfinished checks reporting success. The draft instead describes unrelated mapping defects. This makes the deferral ledger unreliable even though the overall decision to defer export redesign remains appropriate.

Correct the descriptions against the recorded schema review and actual issue titles before committing or relying on this report. Remove stale assertions about character counts and avoid implying that unexecuted native gates reject an ID-only record. This issue records the review finding; no production schema or runtime fix is requested.
