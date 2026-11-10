At reviewed main 7233f193ad102a8488b31ec7333662c8fefaa996, docs/d4d_core.md says Core to/from RO-Crate is lossless and every Core slot is externally SKOS-aligned. These assurances exceed the current evidence.

The canonical comprehensive table has explicit no-match rows for multiple names retained in Core. Some of those slots do have separate broad external annotations; the defect is the blanket canonical-alignment claim, not absence of all annotations.

There are multiple distinct routes: full-to-Core projection, static RO-Crate-to-Dataset mapping, finite FAIRSCAPE converters, and unfinished unified transformations. Updating SSSOM does not automatically update the hand-written converter. A Core-valid tiny fixture passed through the generic forward converter loses its distributions/BIDS declaration. A supported Core input contract has not been established, so this is a route-boundary finding, not a demonstrated regression of a supported Core-specific converter.

Acceptance:
- State supported input class, direction, target version, preservation scope and intentional losses for each route.
- Remove or qualify blanket lossless/external-alignment assertions.
- Explicitly support Core distributions or refuse unsupported Core input.
- Demonstrate any promised inverse with schema-valid fixtures and field/identity/cardinality checks.

Review: notes/schema_review_20261110/semantic_exchange.md, exchange_static.json, exchange_canary.json and validation_core.json.
Related acceptance work: #160 and #136. Review finding: P2.
