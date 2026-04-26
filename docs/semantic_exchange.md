# Semantic Exchange Layer (D4D ↔ RO-Crate / FAIRSCAPE)

The **Semantic Exchange Layer** is the canonical SKOS + SSSOM mapping that lets a [D4D-Core](d4d_core.md) datasheet round-trip through RO-Crate, FAIRSCAPE EVI, schema.org, DCAT, and Croissant RAI. It is the cross-system interoperability contract for D4D.

## Artifacts

All semantic-exchange artifacts live under two directories:

### `src/data_sheets_schema/semantic_exchange/`

The **canonical source** of the exchange layer.

| File | Format | Description |
|---|---|---|
| [`d4d_rocrate_skos_alignment.ttl`](https://github.com/bridge2ai/data-sheets-schema/blob/main/src/data_sheets_schema/semantic_exchange/d4d_rocrate_skos_alignment.ttl) | Turtle | Authoritative SKOS triples — `skos:exactMatch`, `skos:closeMatch`, `skos:relatedMatch`, `skos:narrowMatch`, `skos:broadMatch` (100+ class- and slot-level alignments) |
| [`d4d_rocrate_sssom_mapping.tsv`](https://github.com/bridge2ai/data-sheets-schema/blob/main/src/data_sheets_schema/semantic_exchange/d4d_rocrate_sssom_mapping.tsv) | SSSOM (19-col) | Semantic SSSOM with extended columns: `d4d_schema_path`, `rocrate_json_path`, `in_pydantic_model`, `in_rocrate_json`, `in_interface_mapping`, `d4d_module` |
| `d4d_rocrate_sssom_mapping_subset.tsv` | SSSOM (19-col) | Interface-only subset (curated Google-Sheet seed mappings) |
| `d4d_rocrate_sssom_uri_mapping.tsv` | SSSOM | URI-level variant for slots with explicit `slot_uri` |
| `d4d_rocrate_sssom_uri_comprehensive.tsv` | SSSOM | URI-level variant covering all D4D attributes (auto-derived) |
| `d4d_rocrate_sssom_comprehensive.tsv` | SSSOM | Comprehensive label-level mapping for every D4D attribute |

### `data/semantic_exchange/`

sssom-py-compatible variants and analysis docs.

| File | Description |
|---|---|
| [`d4d_rocrate_structural_mapping.sssom.tsv`](https://github.com/bridge2ai/data-sheets-schema/blob/main/data/semantic_exchange/d4d_rocrate_structural_mapping.sssom.tsv) | 17-column structural SSSOM (sssom-py compatible) — typed/range/multivalued metadata for every mapped slot |
| `d4d_rocrate_structural_mapping_summary.md` | Human-readable structural mapping summary |
| `STRUCTURAL_MAPPING_ANALYSIS.md` | Type-compatibility analysis between LinkML ranges and RO-Crate value types |
| `uri_mapping_recommendations.md` | URI-level mapping rationale and edge-case decisions |
| `README.md` | Per-file conventions and column documentation |

## Generators

[`src/semantic_exchange/`](https://github.com/bridge2ai/data-sheets-schema/tree/main/src/semantic_exchange) contains the regen scripts:

| Script | Make target | Purpose |
|---|---|---|
| `generate_sssom_mapping.py` | `make gen-sssom` (full + subset) | Derives the semantic SSSOM from the SKOS TTL + interface CSV |
| `generate_sssom_uri_mapping.py` | `make gen-sssom-uri` | URI-level variant (slots with `slot_uri`) |
| `generate_comprehensive_sssom_uri.py` | `make gen-sssom-uri-comprehensive` | URI variant for all attributes |
| `generate_comprehensive_sssom.py` | `make gen-sssom-comprehensive` | Label-level variant for all attributes |
| `generate_structural_mapping.py` | `make gen-sssom-structural` | sssom-py-compatible structural SSSOM |
| `add_module_column.py`, `add_slot_uris.py`, `implement_uri_mappings.py` | — | One-shot maintenance helpers |

Regenerate everything:

```bash
make gen-sssom-all
```

## Validation

```bash
poetry run pytest tests/test_semantic_exchange tests/test_fairscape_integration -v
```

These tests check column counts, required-column presence, sssom-py parseability, and consistency between the SKOS triples and the SSSOM rows.

## Adding a new mapping

When a new D4D class joins the exchange layer (e.g. `Dataset`, `DatasetCollection`, `File`, `FileCollection` were added as part of PR #147), follow the [`/d4d-add-mapping`](https://github.com/bridge2ai/data-sheets-schema/blob/main/.claude/commands/d4d-add-mapping.md) Claude Code skill. The workflow:

1. Pick the SKOS predicate (`exactMatch` / `closeMatch` / `relatedMatch` / `narrow|broadMatch`) using the rubric in the skill.
2. Append class-level and slot-level rows to the semantic SSSOM and the structural SSSOM.
3. Append matching SKOS triples to `d4d_rocrate_skos_alignment.ttl`.
4. Update `class_uri` / `exact_mappings` annotations on the schema YAML if missing.
5. Regenerate the URI / comprehensive variants with `make gen-sssom-all`.
6. Run the validation tests above.

## Mapping namespaces

| Prefix | URI | Used for |
|---|---|---|
| `schema` | `https://schema.org/` | Most title/description/identifier/temporal slots |
| `dcat` | `http://www.w3.org/ns/dcat#` | Catalog / distribution / byteSize structure |
| `evi` | `https://w3id.org/EVI#` | FAIRSCAPE Evidence: hashes (md5, sha256), formats, sampling, ROCrate root |
| `rai` | `http://mlcommons.org/croissant/RAI/` | Responsible AI: dataCollection, biases, limitations, prohibitedUses |
| `d4d` | `https://w3id.org/bridge2ai/data-sheets-schema/` | D4D-specific terms with no external equivalent |

## Coverage at a glance

- **108** rows in the semantic SSSOM
- **156** rows in the structural SSSOM
- **112** SKOS mapping triples
- **6** SKOS predicates in use (`exactMatch`, `closeMatch`, `relatedMatch`, `narrowMatch`, `broadMatch`, plus class-level alignments)
- **5** target namespaces (schema.org, DCAT, EVI, RAI, d4d-internal)
