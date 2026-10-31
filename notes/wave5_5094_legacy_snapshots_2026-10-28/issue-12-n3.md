# Local issue draft 12 / N3: backfill selects the first audit rather than owned phase evidence

Source: Issue 12/N3 in the lead's `2026-10-28-issues-from-pr5094-review.md`. This is a draft label, not a newly assigned GitHub issue number. No GitHub write was performed.

`backfill_checks.compute` at `3f202bd3e320672fed8a49b0c4b82ef7e124a43f` reads `intermediate/{project}_audit.json` directly. A later attested audit can differ, and a legacy ambiguous inventory does not justify selecting the first audit.

The committed VOICE v4 record (`2026-08-13_claude-opus-5-api-generic-v4_rep1`) has audits of 21 and 18 findings; its report states 18. The retained baseline canary at `dfd0b9d4b0932cf6990971db6d70d39109e404af` computes the false mismatch `report states 18 findings; structured audit has 21`. No actual backfill was applied.

Acceptance: use record-aware `snapshot_store.read_latest`, refuse ambiguous/missing/changed/foreign evidence as unmeasured, select the current byte-attested phase without filename guessing, and detect portable-only audits during default computation. Preserve exactly-one-file fallback for old unregistered records only when no ownership or current/previous index is declared. Do not weaken snapshot guards or rewrite historical evidence.

Locally addressed by `94484d0a9fab8c47f54ffe732b5393fe0c502bbe`; tested at `de56f9dd7efc9009704dec2e24cc3378dbb24f32`. The real-record canary and all 100 focused cases pass, including malformed latest bytes with valid attestation, invalid owners/indices, numbered distractors and missing first snapshots. Fresh selection changes are verified without changing stored measurements. Publication and issue-state decisions remain with the lead.
