Add D4D ↔ RO-Crate / FAIRSCAPE semantic exchange layer mappings for one or more D4D classes.

## When to use

Invoke this skill when:
- A new class has been added to the D4D schema (e.g. `File`, `FileCollection`, `DataSubset`) and needs SSSOM mappings to RO-Crate so it shows as "covered" in the exchange layer.
- An existing class's mapping needs revising (target predicate or object_id changed).
- The user asks to "add SSSOM mappings", "update the exchange layer", or names specific classes to map.

The skill produces:
- New rows in the **semantic SSSOM** (`src/data_sheets_schema/semantic_exchange/d4d_rocrate_sssom_mapping.tsv`)
- New rows in the **structural SSSOM** (`data/semantic_exchange/d4d_rocrate_structural_mapping.sssom.tsv`)
- Matching SKOS triples in `src/data_sheets_schema/semantic_exchange/d4d_rocrate_skos_alignment.ttl`
- A new branch + commit + optional PR

## Inputs

The user names one or more **D4D class names** (e.g. `Dataset`, `DatasetCollection`, `File`, `FileCollection`, `DataSubset`). They may also specify a target predicate (`exactMatch` / `closeMatch` / `relatedMatch`) or particular RO-Crate target IDs.

## Required reading before editing

Always read these BEFORE editing anything:

1. `src/data_sheets_schema/semantic_exchange/d4d_rocrate_sssom_mapping.tsv` — first 10 lines (header + samples) to confirm the **19-column tab-separated** layout. Columns:
   ```
   d4d_schema_path  subject_id  subject_label  predicate_id  rocrate_json_path  object_id  object_label  mapping_justification  confidence  comment  author_id  mapping_date  subject_source  object_source  mapping_set_id  mapping_set_version  in_rocrate_json  in_pydantic_model  in_interface_mapping
   ```
2. `data/semantic_exchange/d4d_rocrate_structural_mapping.sssom.tsv` — first 5 lines for the **17-column** structural layout. Columns:
   ```
   subject_id  subject_label  subject_category  predicate_id  object_id  object_label  mapping_justification  confidence  subject_source  object_source  d4d_subject_range  subject_multivalued  rocrate_value_type  type_compatible  composition_path  structural_notes  warnings
   ```
3. `src/data_sheets_schema/semantic_exchange/d4d_rocrate_skos_alignment.ttl` — to see the prefix declarations and existing class/slot triples.
4. The schema YAML(s) defining each target class — typically:
   - `src/data_sheets_schema/schema/D4D_Base_import.yaml` (NamedThing, Information, common)
   - `src/data_sheets_schema/schema/D4D_FileCollection.yaml` (File, FileCollection)
   - `src/data_sheets_schema/schema/data_sheets_schema.yaml` (Dataset, DatasetCollection)
   - `src/data_sheets_schema/schema/D4D_Core.yaml` (CoreDataset, CoreDistribution, CoreDatasetCollection)

For each class, capture the existing `class_uri`, `exact_mappings`, `close_mappings`, `is_a`, and slot list (incl. `slot_uri` per slot).

## Pre-edit grep (avoid duplicates)

```bash
grep -n "d4d:CLASSNAME" src/data_sheets_schema/semantic_exchange/d4d_rocrate_sssom_mapping.tsv \
                       src/data_sheets_schema/semantic_exchange/d4d_rocrate_skos_alignment.ttl
grep -n "d4d:CLASSNAME/" data/semantic_exchange/d4d_rocrate_structural_mapping.sssom.tsv
```

If a class-level row already exists with the right mapping, leave it intact and only add what's missing.

## Mapping decision rubric

For each class, propose **two SSSOM rows** (a primary + a secondary), grounded in what the schema already declares:

| D4D schema annotation | Default SSSOM target (predicate `skos:exactMatch`, confidence 1.0) |
|---|---|
| `class_uri: schema:X` | `schema:X` |
| `class_uri: dcat:X`   | `dcat:X` |
| `exact_mappings: [Y]` | `Y` (if no class_uri) |
| `tree_root: true`     | `schema:Dataset` (RO-Crate root, with comment about `@type=["Dataset", "https://w3id.org/EVI#ROCrate"]`) |

Then add a **secondary row** with `skos:closeMatch` (confidence 0.7–0.9) using `close_mappings` from the YAML or a sensible alternative.

For **slots** owned by the class (not inherited from `Information`), add one row per slot using its `slot_uri` as `object_id`. Skip inherited Information slots (title/description/doi/...) — they're already mapped via the existing `Dataset.*` rows.

## Standard target conventions (RO-Crate / FAIRSCAPE)

| RO-Crate concept | Target ID |
|---|---|
| Root Dataset | `schema:Dataset` (+ comment: `@type=["Dataset", "https://w3id.org/EVI#ROCrate"]`, `@id="./"`) |
| Catalog (DCAT) | `dcat:Catalog` |
| Distribution / package | `dcat:Distribution` or `schema:DataDownload` |
| Individual file | `schema:MediaObject` |
| Sub-collection (nested Dataset) | `schema:Dataset` (with `@id != "./"`) |
| `hasPart` relationship | `schema:hasPart` |
| Byte size | `dcat:byteSize` or `schema:contentSize` |
| Hash values | `evi:md5`, `evi:sha256` |

## Row template (semantic SSSOM, 19 columns)

```
{ClassName}.{ClassName}\td4d:{ClassName}\t{ClassName}\tskos:exactMatch\t@graph[?@type='{TYPE}']\t{TARGET_ID}\t{TARGET_LABEL}\tsemapv:ManualMappingCuration\t{CONF}\t{COMMENT}\thttps://orcid.org/0000-0000-0000-0000\t{ISO_DATE}\thttps://w3id.org/bridge2ai/data-sheets-schema/\t{TARGET_NS}\td4d-rocrate-alignment-v1\t1.0\t{IN_ROCRATE}\t{IN_PYDANTIC}\t{IN_IFACE}
```

Slot rows use `subject_id = d4d:{ClassName}.{slot_name}` and follow the same column count.

## Row template (structural SSSOM, 17 columns)

```
d4d:{ClassName}/{slot_name}\t{slot_name}\t{ClassName}\tskos:exactMatch\t{TARGET_ID}\t{TARGET_LABEL}\tsemapv:StructuralMapping\t{CONF}\td4d:data_sheets_schema\trocrate:fairscape\t{D4D_RANGE}\t{MULTIVALUED}\t{ROC_VALUE_TYPE}\t{TYPE_COMPATIBLE}\t{COMPOSITION_PATH}\t{NOTES}\t{WARNINGS}
```

Structural file is **slot-level only** — do not add class-level rows there.

## SKOS TTL template

In `src/data_sheets_schema/semantic_exchange/d4d_rocrate_skos_alignment.ttl`, append under `# Class-level alignments`:

```turtle
d4d:{ClassName} skos:exactMatch {TARGET_ID} .
d4d:{ClassName} skos:closeMatch {SECONDARY_ID} .
```

For slot-level, append under a `# Class-level slot mappings` block:

```turtle
d4d:{ClassName}_{slot_name} skos:exactMatch {SLOT_TARGET_ID} .
```

Confirm the TTL file declares every prefix you reference (`d4d:`, `schema:`, `dcat:`, `evi:`, `rai:`). Add `@prefix dcat: <http://www.w3.org/ns/dcat#> .` etc. if missing.

## Helper script

For mechanical row-appending, use `/tmp/add_exchange_rows.py` as a starting point. The structure is:

```python
def sem_row(d4d_path, subj_id, subj_label, pred, json_path, obj_id, obj_label,
            confidence, comment, obj_src, in_rocrate="true", in_pydantic="true",
            in_iface="false"):
    return "\t".join([d4d_path, subj_id, subj_label, pred, json_path, obj_id,
                      obj_label, "semapv:ManualMappingCuration", str(confidence),
                      comment, "https://orcid.org/0000-0000-0000-0000",
                      "{TODAY}", "https://w3id.org/bridge2ai/data-sheets-schema/",
                      obj_src, "d4d-rocrate-alignment-v1", "1.0",
                      in_rocrate, in_pydantic, in_iface])

def str_row(subj_id, subj_label, subj_cat, pred, obj_id, obj_label, confidence,
            d4d_range, mv, roc_type, type_compat, composition_path="",
            notes="", warnings=""):
    return "\t".join([subj_id, subj_label, subj_cat, pred, obj_id, obj_label,
                      "semapv:StructuralMapping", str(confidence),
                      "d4d:data_sheets_schema", "rocrate:fairscape", d4d_range,
                      str(mv), roc_type, str(type_compat), composition_path,
                      notes, warnings])
```

(Replace `{TODAY}` with `datetime.date.today().isoformat()`.)

## Validation (mandatory)

After appending rows, run:

```bash
poetry run python -c "
import sys; sys.path.insert(0,'src')
from fairscape_integration.utils.sssom_integration import SSSOMIntegration
sem = SSSOMIntegration('src/data_sheets_schema/semantic_exchange/d4d_rocrate_sssom_mapping.tsv', verbose=False)
print('Semantic:', sem.get_active_implementation(), sem.get_mappings_count())
struct = SSSOMIntegration('data/semantic_exchange/d4d_rocrate_structural_mapping.sssom.tsv', verbose=False)
print('Structural:', struct.get_active_implementation(), struct.get_mappings_count())
# Spot-check the new class subjects
for c in ['CLASS1', 'CLASS2']:
    matches = sem.get_mappings_by_subject(f'd4d:{c}')
    assert matches, f'd4d:{c} missing from semantic SSSOM'
    print(f'  d4d:{c} →', [m['object_id'] for m in matches])
"
poetry run python -m pytest tests/test_semantic_exchange tests/test_fairscape_integration -v
```

The semantic file uses non-SSSOM-standard columns and falls back to the custom reader (`impl=custom`); the structural file should pass `sssom-py` (`impl=sssom-py`). All existing alignment + fairscape tests must continue to pass.

## Branch + commit + PR

Conventional workflow:

```bash
git checkout main && git pull origin main
git checkout -b update_exchange   # or another descriptive name supplied by the user
# ... edits ...
poetry run python -m pytest tests/test_semantic_exchange tests/test_fairscape_integration
git add src/data_sheets_schema/semantic_exchange/d4d_rocrate_sssom_mapping.tsv \
        data/semantic_exchange/d4d_rocrate_structural_mapping.sssom.tsv \
        src/data_sheets_schema/semantic_exchange/d4d_rocrate_skos_alignment.ttl
git commit -m "Add SSSOM mappings for {CLASSES} in the exchange layer

Brief explanation of new rows and the reasoning behind primary/secondary targets.
Note any out-of-scope follow-ups (e.g. converter code TODOs).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
git push -u origin {BRANCH}
gh pr create --base main --title "Add SSSOM mappings for {CLASSES}" --body "..."
```

## Out-of-scope reminders

When opening the PR, **explicitly call out** these as separate follow-ups (do NOT bundle them):

1. **Converter code** in `src/fairscape_integration/d4d_to_fairscape.py:292-295` and `fairscape_to_d4d.py:289-292` — `TODO`s about traversing `FileCollection.resources` to emit RO-Crate `File` entities. The mapping layer alone is not enough; converter code needs separate updates.
2. **Generated comprehensive variants** — `*_comprehensive*.tsv` and `*_uri*.tsv` are produced by scripts in `src/semantic_exchange/` (`generate_sssom_mapping.py`, `generate_structural_mapping.py`, etc.). Those scripts may not auto-discover newly added classes; running `make gen-sssom-all` may overwrite hand-curated rows. Skip regen unless the generators have been updated to handle the new classes.
3. **Schema YAML touch-ups** — verify each newly mapped class has matching `class_uri` and/or `exact_mappings` annotations in the YAML so the schema is self-consistent with the SSSOM. Add them in a small follow-up if needed.

## Reference: a complete walkthrough

A worked example (PR #147) added six class-level + six slot-level rows for `Dataset`, `DatasetCollection`, `File`, `FileCollection`. The diff is the canonical template:

- `git show 9efcac84 -- src/data_sheets_schema/semantic_exchange/d4d_rocrate_sssom_mapping.tsv`
- `git show 9efcac84 -- data/semantic_exchange/d4d_rocrate_structural_mapping.sssom.tsv`
- `git show 9efcac84 -- src/data_sheets_schema/semantic_exchange/d4d_rocrate_skos_alignment.ttl`

## Style and quality bar

- Every new row's `comment` field should explain **why** that target was chosen — point at the schema's `class_uri` or `exact_mappings`, or at a converter-code path that already produces that structure.
- Use `confidence: 1.0` only for true `skos:exactMatch` with a documented schema-level mapping; use `0.7–0.9` for `skos:closeMatch` with semantic similarity.
- Keep `mapping_date` current (today, ISO 8601).
- Do not modify pre-existing rows unless explicitly asked — additive edits only.
- After commit, regenerate any docs that quote the row counts (e.g. `data/semantic_exchange/STRUCTURAL_MAPPING_ANALYSIS.md`, `notes/*`).
