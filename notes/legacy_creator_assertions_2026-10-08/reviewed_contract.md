# Proposed next #4594 slice: preserve author literals in Creator objects

Read-only proposal, 2026-10-08. Inspection baseline: `legacy-updateplan-source` at `bd64f1cd3e5646206da43453e862d8aa0a68f93a`. No application, test, replay, repository edit, or GitHub mutation was performed. Implementation would depend on the UpdatePlan successor, PR #4681, and must resolve the public reporting finding #4684 in actual results and reports. #4594 and #2915 remain open. This proposal does not authorize implementation before the coordinator accepts its reviewed contract.

## Recommendation and current evidence

Implement one explicit default-table route from the selected root's `author` property to `Dataset.creators`. Put complete source text in `Creator.description`; preserve other source values without stringification, dropping keys, resolving references, or manufacturing people. The schema already supports this representation. No PI-role or human-annotation approval is required for this bounded literal-preservation operation.

`Dataset.creators` is an inlined list of `Creator` (`src/data_sheets_schema/schema/data_sheets_schema.yaml:215`). `Creator` inherits `DatasetProperty` (`D4D_Motivation.yaml:86`), whose optional `description` is the default narrative home (`D4D_Base_import.yaml:183`). Creator IDs and PI objects are optional. A `Creator.id` identifies the property, not necessarily the person mentioned by the author assertion. Therefore do not rename a Person's `@id` to `Creator.id`, mint an ID, infer a PI, or reuse `rocrate_normalize._person_to_creator`, which currently makes that rename and can mint organization identifiers under a different contract.

The saved UpdatePlan candidate replay has 330 validator messages for one implementation/order, 1,320 across both builders and both graph orders. Creator errors still account for 212 per implementation/order:

| Retained input | Actual root `author` | Literal units | Explicit reference units | Current Creator errors |
| --- | --- | ---: | ---: | ---: |
| CHORUS | One complete author/affiliation narrative string | 1 | 0 | 1 |
| VOICE | List of 117 strings | 117 | 0 | 117 |
| CM4AI reduced | List of 47 values | 9 | 38 | 47 |
| VOICE provenance | Property absent | 0 | 0 | 0 |
| CM4AI original ZIP member | Same author list as reduced representation | 9 | 38 | 47 |

All 38 CM4AI references are exactly `{"@id": "https://orcid.org/..."}`; each resolves uniquely to a graph entity typed `Person`, with `name`, `identifier` and an affiliation object. This establishes that they are explicit person references, not prose or already constructed Creator-property identifiers. The nine CM4AI strings contain names such as `"Axelsson, U"`; splitting commas would corrupt them. CHORUS is one unsplit narrative including affiliations and line breaks. No retained literal is blank, URI-shaped, or padded; controls must cover those edge cases separately.

The literal slice can address **136 of the 212 Creator messages per implementation/order**, leaving the 76 reference messages intact. Across the 20-run replay that is an expected reduction of 544 repeated validation messages, not 544 people, datasets, source facts, or improved source coverage. Conditional on no other changes, expected remaining message counts are CHORUS 29, VOICE 33, each CM4AI 66, provenance 0: 194 per variant, 776 across the replay. These are predictions for later validation, not newly measured results. All four currently invalid root records must remain refused by the publication gate; the provenance input remains unchanged.

## Closed construction and activation contract

Use a small shared helper, proposed `src/data_sheets_schema/legacy_creators.py`, with `MARKER='creator_author_literals_v1'`, `validate_rows(rows)`, `creator_route(mapping)` and `creator_value(value)`.

Only the recognized marker activates this behavior. Require exactly one marked, covered `creators` row whose source is exactly `author`, and no other covered `creators` route. Reject misplaced, uncovered, duplicate, or competing marker declarations before ignored-row filtering or builder/merger state reset. Validate in both MappingLoader implementations and recheck mutable mappings at the builder/merger boundary, following the existing UpdatePlan route. Unmarked custom tables and arbitrary historical Func text retain their old behavior. Do not broaden `owner/author`, `created_by`, `modified_by`, or `funders`.

Add the marker to the existing default legacy TSV's `creators` row. The current file has 84 CSV-parsed rows including one ignored, blank-property Class header: 83 loaded mappings, of which 82 are covered. This is separate from the 136-row maintained interface ledger and its accepted 43-row snapshot. Preserve historical semantic labels, examples, inverse-map text and validation declarations as historical provenance; the marker's explicit contract must document that it overrides the stale `Type=str` construction. Do not upgrade `closeMatch/minimal` to `exactMatch/none`, or claim that the historical inverse declaration now implements this constructor.

Call `creator_value` before either builder's generic list/person/string branches. Those branches currently leave string lists unconstructed and can discard dictionary identity/affiliation keys. The helper's target is a list of source assertion units:

1. One non-null scalar source value becomes one unit; a source list supplies its immediate units in exact order. An empty source list stays empty. Do not flatten nested lists.
2. A string unit becomes exactly `{"description": original_string}`. Preserve every character, newline, Unicode code point, comma, duplicate and leading/trailing/blank text. Do not classify names, split people, extract affiliations, or assign a `name` heuristically.
3. Every non-string unit is a detached deep copy with its complete shape. Preserve explicit `false`, zero, null inside a list, nested lists, `@id`, `@type`, unknown keys and conflicting properties. No list selection or stringification. Structurally invalid units remain invalid for the real schema gate. Already supplied Creator-shaped dictionaries retain all their keys and values; the constructor does not authenticate their declarations.
4. Existing top-level missing/null behavior remains: builders omit the field when `author` is absent or null. Record that distinction in source evidence; null items inside a present list are not omitted. Do not use truthiness to discard `false`, zero, blank text or empty containers.
5. A plain string is retained as the source's literal text, even if URI-shaped; it is never dereferenced, promoted to any ID, or asserted to be a person's name. JSON-LD reference dictionaries remain reference dictionaries. This compacted-value contract does not expand remote contexts or convert explicitly reference-typed string declarations into entities. General JSON-LD expansion and typed identity placement remain separate work.

Root selection remains `ROCrateParser.require_root_dataset()`/`rocrate_sources.select_root`: explicit descriptor `about`, otherwise conventional root, otherwise unique typed candidate. Root-missing/member-present must not borrow an author list. Duplicate root IDs and conflicting descriptors remain refused. Graph reversal must not change the selected source assertions.

## Marked merge behavior, provenance and counts

For this marker only, both `ROCrateMerger.merge_rocrates` implementations must bypass `FieldPrioritizer._merge_arrays` for `creators`. The existing UNION path deduplicates complex items by string representation. After wrapping, a literal `"Alice"` and a supplied `{"description":"Alice"}` would otherwise collapse; equal names also do not establish one person.

Concatenate each constructed assertion list in the existing primary-then-secondary source order, preserving order within each source and **all duplicates**. No entity matching, name matching, ORCID merging, or deduplication is introduced. No recursive merging of Creator objects. Other fields and unmarked mappings keep their current strategies. The selected primary and source ranking remain unchanged.

Preserve existing field-level `provenance['creators']` for every source with a present, non-null author value. Emit actual selected source names directly for this marked branch; do not pass them through `merge_field`'s replacement of the reserved string `"primary"`, which would misattribute a secondary source literally bearing that name. Supplement the marked-route report using a detached `creator_assertion_sources` ledger on the merger (not an extra Dataset key): merger-input source index/name, processing index, root ID, `author_present`, exact raw author value, and half-open output-unit range. The source index refers to the list actually passed to the merger, which the API may already have ranked; it does not claim to be the caller's pre-ranking index. Processing order is the selected primary followed by remaining indices in their existing order. Each absent, null or empty-list source has `[cursor, cursor]`; `author_present` and raw value preserve their differences. Zero-length ranges are not people or assertion units. The index distinguishes repeated source labels and makes duplicate units traceable without claiming unique people. Feed it through the existing `generate_merge_report`; the API already returns that report. Do not add transformation metadata inside the Dataset. Clear it on reuse, including marked-to-unmarked calls, as with root-identity evidence.

If every source omits or nulls author, omit `creators`. If a source explicitly supplies `[]` and no source contributes units, preserve `creators: []` and its source evidence. This deliberately preserves a present empty assertion instead of the old UNION path's conversion to missing. Statistics describe construction: `fields_merged_as_arrays` counts the field once, `total_unique_fields` counts Dataset keys, never authors or distinct people. An empty-field preservation change is not new source coverage.

Do not add/remove scoring rows. The informativeness scorer reads root properties before construction (`informativeness_scorer.py:66–76`), so its coverage, uniqueness, richness, rank and selected primary should remain exactly equal on the fixed five-input roster. Existing single-record API/CLI constructed-field counts also remain unchanged on that roster. Other source shapes can change those construction counts: a reference-only dictionary previously collapsed to `None` may now remain an invalid assertion. Resolve this public ambiguity with the actual result/report contract below; notes alone are insufficient. Do not hide the counterexample by dropping the assertion, executing a shadow legacy transform, excluding the creators route as if author were absent, or claiming improved source coverage.

The mandatory exact-byte Dataset publication gate remains independent of optional validation flags. Unknown `@id`/`@type`, unsupported scalars, and all unrelated failures must still refuse file publication; reports/batches preserve their prepare-all-before-write and protected-input guarantees. No-output draft APIs retain the complete invalid draft and diagnostics. Do not use a different mapper or silently repair other fields to make these examples publishable.

## Required public measurement correction for #4684

The source-grounded counterexample is a sole `creators <- author` route and root `author: {"@id":"https://orcid.org/x"}`. The current generic builder can produce `creators=None`; the marked constructor preserves the reference as an invalid list item. `SemanticTransformer.rocrate_to_d4d` counts non-null constructed values, so its existing `coverage_percentage` can change from 0 to 100 with identical source assertions. Both legacy CLIs instead count output keys, including a `creators` key whose value is null. Preserve these existing numeric rules and make their different bases explicit. Neither rule measures source coverage or validity. This is a static counterexample until its proposed tests run.

### API compatibility fields and explicit basis

Add optional `coverage_basis` and `source_presence` fields to the outer `TransformationResult` dataclass in `src/transformation/transform_api.py`. `rocrate_to_d4d` fills both for either `legacy` or `dataset_v1`, independently of `preserve_provenance`. The default for other/unimplemented result-producing operations can remain null. The old `coverage_percentage` and `unmapped_fields` names and arithmetic remain compatible; do not invent a new source-coverage percentage. For this operation `coverage_basis` is exactly:

```json
{
  "kind": "constructed_field_presence",
  "count_rule": "non_null_mapped_value",
  "numerator": 0,
  "denominator": 1,
  "is_source_coverage": false,
  "is_validation_success": false
}
```

The example numbers are replaced with the actual count and `len(scoring_fields(mapping))`. The count is the existing sum of eligible fields whose constructed value is not null. `unmapped_fields` remains the existing list of eligible fields whose constructed value is absent/null, not a list of absent source facts. The marked root-ID exclusion and ordinary unmarked-ID accounting remain unchanged. With denominator zero the existing percentage stays 0.0, accompanied by numerator/denominator 0 rather than a claim of complete coverage. Do not deduplicate the eligible field list or alter existing custom-table arithmetic in this slice.

The outer basis also qualifies the compatibility copies of `coverage_percentage`/`unmapped_fields` in optional `transformation_metadata`. For the marked Creator route with provenance enabled, add a detached `coverage_basis` beside those metadata numbers too, so a consumer extracting metadata alone retains the definition. In `legacy`, this deliberately extends the existing embedded metadata dictionary; in `dataset_v1`, it extends the existing separate metadata dictionary. It does not add a new top-level Dataset diagnostic or make legacy embedded metadata publishable. Unmarked Dataset drafts and their existing metadata remain structurally identical, apart from their pre-existing timestamps; their numeric rule is disclosed in the new outer result basis. When provenance is disabled, metadata remains null/absent as today but the two outer diagnostics are still present. This is an intentional additive result-envelope change and an explicitly marked metadata extension, requiring exact-envelope tests and documentation; it does not relax the closed Dataset publication schema. The raw `source_presence` measurement always stays outside `data`.

No new merged coverage percentage is introduced: the current merge dictionaries do not measure one, and any optional/null numeric coverage field remains not measured, never converted to zero or a fabricated percentage. Both `merge_rocrates` return envelopes add the outer `source_presence` key: legacy retains `d4d`/`merge_report`, and `dataset_v1` retains `format`/`data`/`transformation_metadata`/`merge_report`. Existing merge Dataset and metadata keys remain unchanged. The shared merge report carries the same source-presence facts. `batch_transform_rocrates` inherits both diagnostics through each ordinary transformation result, retaining prepare-all-before-publication behavior.

### Raw author measurement, independent of construction and optional provenance

Add `author_source_presence(mapping, parsers, source_names, primary_index=0)` and a shared text renderer to `legacy_creators.py`. The measurement uses the already selected root and original `author` value, never the constructed Creator objects. It is available for **marked and unmarked** mappings when there is exactly one covered `creators` row with source exactly `author`. An absent, different, or competing route yields `status="not_measured"`, an explicit reason (`no_covered_creators_route`, `different_source_property`, or `multiple_covered_creators_routes`) and an empty sources list. It does not interpret arbitrary custom selectors or refuse a previously accepted unmarked mapping merely because the diagnostic cannot measure it. Recognized malformed markers are still refused by the separate constructor admission checks.

For an admitted measurement the detached result is:

```json
{
  "format": "legacy_author_source_presence_v1",
  "status": "measured",
  "reason": null,
  "target": "creators",
  "source_property": "author",
  "root_scope": "selected_root",
  "sources": [
    {
      "source_index": 0,
      "processing_index": 0,
      "source_name": "selected-source",
      "selected_primary": true,
      "root_id": "./",
      "author_present": true,
      "nonnull": true,
      "immediate_assertion_units": 1,
      "raw_value": {"@id": "https://orcid.org/x"}
    }
  ]
}
```

The not-measured form retains the same top-level keys, with its explicit reason and empty `sources`; it does not assert that the source lacks author information. `author_present` means key membership in the selected root. `nonnull` means present and not null. Missing or top-level null has zero units; a list has its exact immediate length, including duplicate/null/nested-list items; any other non-null value has one unit, including false, zero, empty string or a dictionary. These are assertion units, never people, unique facts, validation successes or matched Creator identities. `raw_value` is a deep copy; missing versus null is distinguished by `author_present`. No list flattening or per-item omission occurs.

For a single API call pass its existing `source` label (including `"dict"` for a dictionary input); never disclose a generated temporary filename as its source label. For merges, indices refer to the actual parser list passed after optional ranking, and rows follow primary-then-secondary processing order with explicit `processing_index`. Preserve actual source names, including repeated names and the literal `"primary"`. The single-source selected-primary flag indicates its construction position, not scientific authority. Marker mode and constructed output ranges are deliberately absent from this raw measurement, so marked/unmarked runs with the same source order have exactly equal `source_presence`. The separate marked `creator_assertion_sources` ledger supplies output ranges where they exist; do not infer them for unmarked transformations.

Both mergers retain this measurement as detached state, with a deep-copy getter for API use, and reset it for each operation. Compute it from validated roots before constructing/merging values; do not reconstruct it from formatted reports or metadata. The single API computes it while its parser is available, before a temporary dictionary-input file is cleaned up. Each caller/report receives detached copies so mutations cannot alter parser input, merger state, other results, or the marked output ledger.

### Actual CLI and report consumers

Update these maintained paths; do not change unrelated historical evidence or informativeness-scoring algorithms:

| Consumer | Required output contract |
| --- | --- |
| `src/transformation/transform_api.py`, legacy CLI transform summary | Replace `Coverage` with `Constructed-field presence (non-null mapped values)`; state that this is not source coverage or validation. Render the raw-author measurement. Keep validation status separate. |
| Same API CLI, `dataset_v1` transform/batch/merge JSON | Existing `asdict`/merge serialization exposes the additive fields directly. Keep stdout valid JSON and existing progress redirection; no extra prose on this route. |
| Same API CLI, legacy batch and merge summaries | Render per-result/per-source raw-author measurements using the same helper; batch results retain their individual construction bases. Do not invent a merged percentage. |
| `src/fairscape_integration/cli.py`, transform report and console | Relabel existing key count and percentage `Constructed-field presence (output keys; null-valued keys included)`; preserve the numerator, denominator and marked-ID exclusion. Add the raw-author measurement to the report and a concise console disclosure, independent of optional provenance. |
| `.claude/agents/scripts/rocrate_to_d4d.py`, `render_transformation_report` and final single/merge summary | Apply the same output-key basis to the existing counts; label `len(dataset)` separately as constructed Dataset keys. Add the single or merger raw-author measurement. Change the existing claim that adding mappings improves `D4D coverage` to the precise fact that it adds mapping routes; no source-evidence gain is asserted. |
| Both `rocrate_merger.py` implementations, `generate_merge_report` | Add the raw-author measurement for marked and unmarked exact routes, and the marked output-range ledger separately. Label existing field statistics as constructed Dataset fields; no global source percentage or person count. |

The text renderer includes route status/reason plus per-source presence, non-null state, immediate-unit count and exact raw-value evidence (JSON-escaped in reports so newlines are preserved without ambiguous record boundaries). Console summaries can omit the full raw text but must state that their unit counts measure raw source assertions, not people or successful schema construction. Existing optional report switches still control report creation; the diagnostic does not create extra files, bypass a failed publication gate, or authorize partial batch publication. The successful-result fields remain available from no-output draft APIs even when the draft is invalid.

The two different constructed-field count rules are not silently unified. Informativeness ranking continues to inspect raw root properties under its existing scoring contract, and mapping statistics remain declarations about table routes. Changing prose around those distinct values must not change their arithmetic or imply that a one-route author diagnostic measures the whole source.

## Acceptance controls and bounded replay

- Real packaged and hidden MappingLoaders/builders: marker admission, invalid/duplicate marker before ignored-row skip, changed mutable route before resetting prior output, unmarked custom compatibility, and arbitrary historical Func labels inert.
- Complete literal preservation: one CHORUS-like multiline narrative; comma-containing names; Unicode; blank and padded strings; duplicate names; URI-looking text kept only as literal description. Assert no `id`, `name`, PI, affiliation or CRediT fields are invented.
- Mixed units: text plus pure `@id` references, typed Person dictionaries, valid supplied Creator dictionaries, unknown/conflicting keys, false/zero/null/nested lists. Preserve positions, types and deep detachment. Retain invalid units rather than choosing or dropping them.
- Root controls: graph reversal; root missing author while a member supplies it; conflicting descriptors and duplicate roots; missing/null versus empty/false. No referenced Person lookup, network resolution or name matching.
- Real marked mergers: two identical strings remain two units; one literal and one supplied description object remain separate; nonstring/invalid units survive; nonzero primary index and auto-ranked ordering; explicit empty list versus absence; zero-length and populated source ranges; repeated source labels and a secondary literally named `"primary"`; report evidence and marked-to-unmarked reuse. Unmarked UNION behavior and all other fields remain byte/structurally equal.
- Real API/CLI and mandatory publisher: a minimal valid record with literals can publish after actual schema validation; references and unsupported units refuse while preserving existing destination/report/source sentinels; a later invalid batch member prevents all publication. Exercise both draft result contracts without weakening legacy metadata refusal.
- Public metrics regression for #4684: run the same pure-`@id` root through marked/unmarked exact author routes, both API result contracts and both provenance settings. Assert the old/new numeric construction counterexample explicitly, equal detached `source_presence`, basis numerator/denominator and non-null count rule, and invalid draft preservation. Marked provenance metadata must carry its own detached basis; unmarked metadata and Dataset data retain their historical structure. Mutating an outer/metadata basis or raw author list/dictionary must not affect its peer, parser, another batch result, or the marked merge ledger. Missing/null/empty-list/false/zero/blank controls must produce distinct presence/unit facts.
- Exercise exact custom-route diagnostics: no creators mapping, a different source property, and multiple unmarked covered creators rows remain behavior-compatible and report `not_measured`, not source absence. Recognized malformed marked routes still refuse. Preserve existing root-ID exclusion and custom-ID arithmetic, and explicitly assert zero-denominator construction basis without source-completeness claims.
- Actual API CLI `dataset_v1` JSON must retain the complete additive schema for transform/batch/merge; legacy CLI and both report/console paths must label the correct non-null-value versus output-key basis, keep validation separate, and render route-level source facts. Use the real hidden report renderer to inspect a null-valued constructed key; the mandatory publisher still refuses invalid file output. Test both merger reports, primary-index/auto-ranked index semantics, repeated names and `not_measured` on reuse. Update exact expected envelopes in `test_legacy_envelope_adversarial.py` and related contract tests rather than weakening them to subset comparisons.
- Fixed five-input baseline/candidate replay: same pins, both builders, original/reversed graphs; only `creators` values change. Expect the literal wrapper counts above, preserve all 76 reference errors per variant and every unrelated error, and compare actual gate outcomes, field counts, source-presence counts, scoring/ranking, selected primary, merge source order and report statistics. Mixed-roster merge remains engineering evidence, not scientific publication. Preserve every baseline/historical artifact and label.

## Held semantic cases and boundaries

- Typed Person/Organization references, ORCID-to-person representation, affiliation identity and Creator-property IDs require a specified identity-bearing representation. The current 38 referenced CM4AI people are explicit and resolvable, but assigning them to `principal_investigator` or renaming their IDs would assert unsupported meaning. Leave their full reference units visible and invalid in this slice.
- The separate PI-role placement decision remains #4449; do not infer PI from authors, reconcile individuals by name, or merge explicit PI and author assertions.
- Remote/general JSON-LD expansion, ambiguous explicit identity declarations, roles and affiliation parsing are not solved by literal preservation.
- Governance, human-subject and imputation adapters belong to the maintained interface mapper's separate implementation. They are not part of this default legacy-table patch.
- Approximate sizes, per-file adapters, other class constructors, source-route conflicts and semantic fidelity labels remain separate #4594/#2915 obligations. Repairing a constructor or retiring a row is not improved source coverage.

## Evidence pins and searches

Saved replay summary: `legacy-updateplan-candidate-replay-01/summary.json`, 236,569 bytes, SHA256 `da409165cba55955c1cbadfacae77c6123e3453c2b06fc52f416569a74446b20`. Source roots were identified by the saved root ID **and** exact canonical root digest, without importing or running the parser/builder.

| Source input | SHA256 |
| --- | --- |
| CHORUS raw crate | `6d0fc1433008a525164154c635b604c98fb620787fbdcb02b87faf9bce643774` |
| VOICE raw crate | `a85057c8d60ed0e10dfac89a733a2ba399c33b7bbc5d291b89b1444dab1901d4` |
| CM4AI reduced | `8f25e9478d1105a008769e25d2a2f67da8475c7218b58946f834ab448dec6610` |
| VOICE provenance | `2cedad47ab225713aca18bd250777fb741a5d5ee639e4b0e9cc63205adb08608` |
| CM4AI original ZIP member | `836376f3a997204b14d4d8d3fba90d967b58cbe20726218c95d861b0cb11e66e` |

Current default TSV: 24,597 bytes, SHA256 `c609e907bbadab5ee502493aa3bee6fd7cf93178792af1e192232910595c1e79`. Full schema: 1,442,513 bytes, SHA256 `eb543e1597b29599952359818bc741b0f23eaa3a30e7aa8c63e60212c7bbb92f`. Maintained interface ledger: 377,128 bytes, SHA256 `37ad5eb1b7026e2e0aaaf17d993752a8d77d447beab704b699814aadec424dfe`.

Ignored/hidden-inclusive searches covered the legacy helper trees, shared legacy modules and relevant tests. No existing `creator_author` marker or Creator-literal constructor was found in those bounded paths. Existing normalization and maintained mapper behavior were inspected and deliberately not imported as a substitute. This is a scoped source assessment, not a claim that no other local work exists.
