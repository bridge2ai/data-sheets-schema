At reviewed main 7233f193ad102a8488b31ec7333662c8fefaa996, the forward exporter declares RO-Crate 1.2 but emits no root datePublished when neither issued nor datePublished is supplied. The real pinned FAIRSCAPE 1.0.24 Pydantic model accepts that output.

The bounded review fixture is valid Core metadata. Its serialized output lacks datePublished and converter.validate returns true. RO-Crate 1.2 requires this root property, so FAIRSCAPE model validation must not be equated with RO-Crate conformance.

Acceptance:
- Check required RO-Crate metadata separately from Pydantic model validity.
- When the source cannot support a publication date, refuse conformance/publishing or return an explicit incomplete outcome; do not invent a date.
- Add a tiny missing-date negative test and a supplied-date positive test.
- Keep version-specific requirements explicit.

Spec: https://www.researchobject.org/ro-crate/specification/1.2/root-data-entity.html#direct-properties-of-the-root-data-entity
Evidence: notes/schema_review_20261110/exchange_canary.json and validation_core.json.
Related: #160; wrong conformsTo expansion is separately associated with #3025.
Review finding: P2.
