At reviewed main 7233f193ad102a8488b31ec7333662c8fefaa996, notes/AI-Readiness/D4D_AI_READINESS_MAPPING.md (dated December 12, 2025) reports 22/26 fully covered and 4/26 partial. Its own summary contains 28 rows, including six partial rows. It cites paper v4; the cited PMID now presents v6, April 24, 2026, with 28 criteria.

The crosswalk also cites paths absent from the current imported schemas, including AccessMethod, LandingPage, Software.software_name and PreprocessingStrategy.preprocessing_description. These are documentation defects, not proof those fields were historically removed.

The November review supplies a 28-ID full/Core matrix at notes/schema_review_20261110/ai_readiness.md. It distinguishes representation from evidence and operational checks. Source-generated JSON Schema accepts an id-only Dataset and CoreDataset, while rejecting an empty object; that does not certify readiness.

Acceptance:
- Preserve the old mapping as a dated artifact and clearly supersede its claims.
- Publish a version-pinned crosswalk with real class/slot paths and separate full/Core scope.
- Replace the unsupported global percentage with criterion-level evidence/status and explicit unknown or inapplicable outcomes.
- Link criterion assessment work to #44 and #23.

Paper: https://pmc.ncbi.nlm.nih.gov/articles/PMC11526931/
Review finding: P2; no schema change is required merely to correct the documentation.
