At reviewed main 7233f193ad102a8488b31ec7333662c8fefaa996, D4DToFairscapeConverter reads the Creator wrapper's name when building author. The current schema uses Creator.principal_investigator containing a Person.

A bounded offline export of creators: [{principal_investigator: {id: https://example.org/person/a, name: Example Scientist}}] emits author: Unknown. The original fixture is valid under current CoreDataset JSON Schema. A separate full Dataset control containing the same Creator structure also validates; that control was not separately converted. Both schemas import the same Creator definition.

This differs from #4088, which concerns the reverse FAIRSCAPE-to-D4D direction.

Acceptance:
- Resolve the current nested Person identity and name rather than silently substituting Unknown.
- Define deterministic handling for teams, multiple creators and legacy wrapper names.
- Preserve source identifiers where the supported output contract allows, or explicitly report limitations.
- Add one small schema-valid forward regression fixture and a negative/ambiguous case.

Source: src/fairscape_integration/d4d_to_fairscape.py, creator extraction around lines 175-190; schema D4D_Motivation.yaml around lines 86-126.
Evidence: notes/schema_review_20261110/exchange_canary.json, validation_core.json, validation_full.json.
Review finding: P2; the review changes no converter.
