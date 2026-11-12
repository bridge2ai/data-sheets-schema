The `FileCollection.collection_type` description encouraged lists even though the declared field accepts one enum value. Correct that instruction and record schema 3.2.1 with synchronized generated products, citation metadata and immutable historical release identities. This does not change accepted cardinalities or enum values.

Add a small full/Core/HTML regression that verifies nested Person and permission shapes, distribution preservation, deliberate Core omissions and full-record immutability. Portable receipt/source-review tests document why component passes do not prove completeness. The operator guide keeps full YAML authoritative and requires independent source review.

Validation:

- 24 focused schema/release/citation/neutrality checks passed in 10.13 seconds; schema synchronization and strict digests passed.
- Integrated positive canary persisted full/Core YAML and HTML/CSS; six focused tests passed in 12.89 seconds.
- All four API schema digests remain unchanged before/after the prose update.
- Specificity audit self-test passed; the global audit exits 1 for nine existing findings tracked in #5582–#5590. Both historical controller files are unchanged. Source review finds those preparers outside the inspected shared API and native v2 routes; this is not a clean global-audit claim.

The plan, review ledger, worker handoffs and compact evidence are in `notes/final_generation_readiness_20261110/`.

Core expansion, bulk migration, new AI-readiness scoring and broader RO-Crate/semantic-export repairs remain outside final-generation prerequisites. Native-only lifecycle gates apply to native runs, not API-only runs. No model calls, generation campaign, publication or release was launched. Native diagnostic wrapper fixes for #5792/#5793 remain on their separate branch; this PR includes only the portable component tests.

Refs #2975. Fixes #5794. Fixes #5795. Fixes #5796. Fixes #5797. Fixes #5798. Fixes #5799. Fixes #5800. Fixes #5801. Fixes #5802. Fixes #5803. Fixes #5804. Fixes #5805. Fixes #5806.

The final generated-product check also passed within its enforced comparison budget: 7,758 OWL triples match after the two exact expected substitutions; both 301-row SSSOM tables have only expected date, collection-type row and status-count changes. Fixes #5807.
