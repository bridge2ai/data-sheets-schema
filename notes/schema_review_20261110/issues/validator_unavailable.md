At reviewed main 7233f193ad102a8488b31ec7333662c8fefaa996, src/validation/unified_validator.py creates ValidationReport(passed=True) for validate_roundtrip, adds a not-implemented warning and returns it. The RO-Crate semantic path similarly returns the inherited successful report when SHACL is missing or remains a stub. ValidationReport string rendering displays PASS unless metadata.status is unavailable.

This is a source-inspected success-signaling defect, distinct from the larger missing implementation tracked in #136 and #160. No claim is made that a particular production caller has already accepted a bad crate.

Acceptance:
- Represent unavailable/not-run explicitly and prevent it from satisfying a conformance or preservation gate.
- Cover both missing optional dependencies and present-but-unimplemented paths.
- Make aggregate/API/CLI summaries retain the distinction.
- Add small negative tests ensuring unperformed checks cannot be reported as successful.

The complete profile already has an unavailable status that can guide consistent semantics. Do not implement a whole transformation engine just to correct this result contract.
Review: notes/schema_review_20261110/semantic_exchange.md.
Review finding: P2.
