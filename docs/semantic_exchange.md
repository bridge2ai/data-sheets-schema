# Semantic Exchange Layer (D4D ↔ RO-Crate / FAIRSCAPE)

The **Semantic Exchange Layer** is the canonical SKOS + SSSOM mapping that lets a [D4D-Core](d4d_core.md) datasheet round-trip through RO-Crate, FAIRSCAPE EVI, schema.org, DCAT, and Croissant RAI. It is the cross-system interoperability contract for D4D.

## Artifacts

All semantic-exchange artifacts live under two directories:

### `src/data_sheets_schema/semantic_exchange/`

The **canonical source** of the exchange layer.

| File | Format | Description |
|---|---|---|
| [`d4d_rocrate_skos_alignment.ttl`](https://github.com/bridge2ai/data-sheets-schema/blob/main/src/data_sheets_schema/semantic_exchange/d4d_rocrate_skos_alignment.ttl) | Turtle | Authoritative SKOS triples — `skos:exactMatch`, `skos:closeMatch`, `skos:relatedMatch`, `skos:narrowMatch`, `skos:broadMatch` (100+ class- and slot-level alignments) |
| `d4d_rocrate_sssom_uri_comprehensive.tsv` | SSSOM | URI-level variant covering all D4D attributes (generated) |
| `d4d_rocrate_sssom_comprehensive.tsv` | SSSOM | Comprehensive label-level mapping for every D4D attribute (generated) |

Both comprehensive tables are generated, never hand-edited: a change to the schema, to the SKOS TTL or to the recommendations file below regenerates them in the same commit, and `make check-sssom-comprehensive` fails until it does. The legacy property-level table (`d4d_rocrate_sssom_mapping.tsv`), its interface-only subset and the 33-slot URI table were retired in #3884: nothing read them and they had no drift check; the property-level table, never regenerated, had also fallen 70 TTL triples behind. Their last versions are in git history.

The two comprehensive tables also read [`notes/D4D_MISSING_URI_RECOMMENDATIONS.tsv`](https://github.com/bridge2ai/data-sheets-schema/blob/main/notes/D4D_MISSING_URI_RECOMMENDATIONS.tsv), the URI suggestions for slots without a curated mapping. A suggestion withdrawn after review keeps its row with `suggested_uri` and `confidence` cleared and the reason in `review_note`, and is read as no suggestion; see [`notes/D4D_URI_COVERAGE_REPORT.md`](https://github.com/bridge2ai/data-sheets-schema/blob/main/notes/D4D_URI_COVERAGE_REPORT.md). A slot with no mapping from any source is written in SSSOM's no-match form, `skos:exactMatch sssom:NoTermFound` under `semapv:UnspecifiedMatching`, with its status (`free_text`, `novel_d4d`, `unmapped`) in `mapping_status`.

### `data/semantic_exchange/`

sssom-py-compatible variants and analysis docs.

| File | Description |
|---|---|
| [`d4d_rocrate_structural_mapping.sssom.tsv`](https://github.com/bridge2ai/data-sheets-schema/blob/main/data/semantic_exchange/d4d_rocrate_structural_mapping.sssom.tsv) | 17-column structural SSSOM (sssom-py compatible) — typed/range/multivalued metadata for every mapped slot |
| `d4d_rocrate_structural_mapping_summary.md` | Human-readable summary of the rows the structural generator produces: each justification group's row count and its first 10 rows only (17 of 155), so not a listing of them — rendered from its regenerated rows, not from the committed structural TSV, which carries rows regeneration does not produce (see the folder's `README.md`) |
| `STRUCTURAL_MAPPING_ANALYSIS.md` | How the structural mapping is produced (mapping strategies, type-compatibility rules) and checked (`make check-sssom-structural`); states no counts |
| `uri_mapping_recommendations.md` | URI-level mapping rationale and edge-case decisions |
| `README.md` | Per-file conventions and column documentation |

## Generators

[`src/semantic_exchange/`](https://github.com/bridge2ai/data-sheets-schema/tree/main/src/semantic_exchange) contains the regen scripts:

| Script | Make target | Purpose |
|---|---|---|
| `generate_comprehensive_sssom_uri.py` | `make gen-sssom-uri-comprehensive` | URI variant for all attributes |
| `generate_comprehensive_sssom.py` | `make gen-sssom-comprehensive` | Label-level variant for all attributes |
| `generate_structural_mapping.py` | `make gen-sssom-structural` | sssom-py-compatible structural SSSOM; not run by `make gen-sssom-all` (see below) |
| `add_module_column.py`, `add_slot_uris.py`, `implement_uri_mappings.py` | — | One-shot maintenance helpers |

Regenerate the comprehensive pair and check it for drift:

```bash
make gen-sssom-comprehensive gen-sssom-uri-comprehensive
make check-sssom-comprehensive
```

The structural mapping carries rows its generator cannot produce, listed with their reasons as `KNOWN_UNDERIVABLE` in `generate_structural_mapping.py` (#294). Rewriting the table with `make gen-sssom-structural` drops those rows, so `make gen-sssom-all` regenerates only the comprehensive pair and `make clean-sssom` deletes only that pair (#3967). `make check-sssom-structural` compares the table and its summary with what the generator writes, allowing for those rows, and names any of them a rewrite dropped, to restore from git before committing; `python src/semantic_exchange/generate_structural_mapping.py --help` states exactly what it compares (#4076).

## Validation

```bash
poetry run pytest tests/test_semantic_exchange tests/test_fairscape_integration -v
```

These tests check column counts, required-column presence, sssom-py parseability, and consistency between the SKOS triples and the SSSOM rows.

## Adding a new mapping

When a D4D class or slot joins the exchange layer, follow the [`/d4d-add-mapping`](https://github.com/bridge2ai/data-sheets-schema/blob/main/.claude/commands/d4d-add-mapping.md) Claude Code skill. The workflow:

1. Pick the SKOS predicate (`exactMatch` / `closeMatch` / `relatedMatch` / `narrow|broadMatch`) using the rubric in the skill. A `d4d:` target is not an alignment (#3054).
2. Append the triples to `d4d_rocrate_skos_alignment.ttl`: slot-level (`d4d:<slot>`) or class-scoped (`d4d:<Class>_<slot>`) triples feed the comprehensive tables; class-level triples are recorded in the TTL only.
3. Update `class_uri` / `exact_mappings` / `slot_uri` annotations on the schema YAML if missing (a schema change has its own regeneration steps).
4. Regenerate the comprehensive pair with `make gen-sssom-comprehensive gen-sssom-uri-comprehensive` and commit both tables with the TTL.
5. Run `make check-sssom-comprehensive` and the validation tests above.

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
