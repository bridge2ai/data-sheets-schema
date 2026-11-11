# Review of the proposed post-acceptance optimization

2026-11-11, lead plus independent read-only review. Preliminary handoff SHA256: `87100aa99ee6e489cd1b29fc517d1681ee09846fe73527837203efcf4687d60e`. Native reference89c28; the relevant orchestration/capture files are unchanged at458887.

The four repeated full verification cascades are confirmed. The preliminary B/C implementation is not approved as written. Findings were filed before correction:

- [5836](https://github.com/bridge2ai/data-sheets-schema/issues/5836): a caller-supplied `verified_value` on public capture/context/lease functions would allow self-consistent wire and pins to replace genuine preparation/execution reconstruction. Captured-wire parsers and closed-shape checks cannot establish the missing derivation. Keep public calls fully verifying and reuse private to the same already-verified live invocation. Keep pre-admission `_unchanged` unchanged. The plan also incorrectly compares `_closed_execution`'s None result with the body.
- [5837](https://github.com/bridge2ai/data-sheets-schema/issues/5837): detecting a monkeypatched verifier in production and switching to the old path would keep component tests from exercising the optimized behavior. Remove this fallback; use explicit fixture seams and witnesses of the actual changed path.
- [5838](https://github.com/bridge2ai/data-sheets-schema/issues/5838): plain extraction of the selected-capture helper loses the fresh preparation/source/runtime check after root, journal and slot reads. Preserve that check at the old inner boundary, tied to genuine authority from this invocation; add unchanged and between-boundary mutation witnesses.

AGY3 is assigned to revise the design and implement only the smallest capture-deduplication slice first, on an isolated branch from458887. Preserve the old worker branch/evidence and all protected/scanner files. No additional test runtime while the native monitoring diagnostic owns the slot. Focused source review and a small canary precede broader affected tests. Completion of this slice alone will not close all four cascades or the structural gate.

This work remains separate from final D4D generation prerequisites. No new framework, provider call or generation is authorized by this review.
