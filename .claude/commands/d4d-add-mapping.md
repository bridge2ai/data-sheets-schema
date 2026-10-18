Add D4D ↔ RO-Crate / FAIRSCAPE semantic exchange layer mappings for one or more D4D classes.

## When to use

Invoke this skill when:
- A new class or slot has been added to the D4D schema (e.g. `File`, `FileCollection`, `DataSubset`) and needs a mapping to RO-Crate so it shows as "covered" in the exchange layer.
- An existing mapping needs revising (target predicate or target id changed).
- The user asks to "add SSSOM mappings", "update the exchange layer", or names specific classes to map.

The skill produces:
- New SKOS triples in `src/data_sheets_schema/semantic_exchange/d4d_rocrate_skos_alignment.ttl`, the curated input of the exchange layer
- The two comprehensive SSSOM tables, **regenerated** from it: `src/data_sheets_schema/semantic_exchange/d4d_rocrate_sssom_comprehensive.tsv` and `d4d_rocrate_sssom_uri_comprehensive.tsv`
- A new branch + commit + optional PR

No SSSOM row is written by hand. The comprehensive tables are a function of the schema, the TTL, `notes/D4D_MISSING_URI_RECOMMENDATIONS.tsv` and the date, and a drift check fails if the committed tables are not what those inputs produce. The legacy property-level table (`d4d_rocrate_sssom_mapping.tsv`), its subset and the 33-slot URI table were retired (#3884); do not recreate them.

## Inputs

The user names one or more **D4D class names** (e.g. `Dataset`, `DatasetCollection`, `File`, `FileCollection`, `DataSubset`), or slots. They may also specify a target predicate (`exactMatch` / `closeMatch` / `relatedMatch` / `narrowMatch` / `broadMatch`) or particular RO-Crate target IDs.

## Required reading before editing

Always read these BEFORE editing anything:

1. `src/data_sheets_schema/semantic_exchange/d4d_rocrate_skos_alignment.ttl` — the prefix declarations and the existing class-level, class-scoped and slot-level triples.
2. The module docstring of `src/semantic_exchange/generate_comprehensive_sssom.py` — how a slot's row is chosen (TTL first, then the schema's `slot_uri` / `*_mappings`, then the recommendations file, then a no-match row), why a `d4d:` target is not an alignment (#3054), and how a TTL/schema disagreement must be listed in `ACCEPTED_DISAGREEMENTS` or `OPEN_DISAGREEMENTS`.
3. `src/data_sheets_schema/semantic_exchange/d4d_rocrate_sssom_comprehensive.tsv` — the header comment and the rows for the slots you will touch, to see what the table says today.
4. The schema YAML(s) defining each target class — typically:
   - `src/data_sheets_schema/schema/D4D_Base_import.yaml` (NamedThing, Information, common)
   - `src/data_sheets_schema/schema/D4D_FileCollection.yaml` (File, FileCollection)
   - `src/data_sheets_schema/schema/data_sheets_schema.yaml` (Dataset, DatasetCollection)
   - `src/data_sheets_schema/schema/D4D_Core.yaml` (CoreDataset, CoreDistribution, CoreDatasetCollection)

For each class, capture the existing `class_uri`, `exact_mappings`, `close_mappings`, `is_a`, and slot list (incl. `slot_uri` per slot).

## Pre-edit grep (avoid duplicates)

```bash
grep -n "d4d:CLASSNAME\b\|d4d:CLASSNAME_" src/data_sheets_schema/semantic_exchange/d4d_rocrate_skos_alignment.ttl
grep -n "d4d:SLOTNAME\b" src/data_sheets_schema/semantic_exchange/d4d_rocrate_sssom_comprehensive.tsv
```

If a triple already states the right mapping, leave it intact and only add what is missing.

## Mapping decision rubric

For each class, propose a **primary** and, where one exists, a **secondary** triple, grounded in what the schema already declares:

| D4D schema annotation | Default target (predicate `skos:exactMatch`) |
|---|---|
| `class_uri: schema:X` | `schema:X` |
| `class_uri: dcat:X`   | `dcat:X` |
| `exact_mappings: [Y]` | `Y` (if no class_uri) |
| `tree_root: true`     | `schema:Dataset` (RO-Crate root, `@type=["Dataset", "https://w3id.org/EVI#ROCrate"]`) |

Then add a **secondary** `skos:closeMatch` using `close_mappings` from the YAML or a sensible alternative.

Choose the predicate for what the two terms mean, not for convenience:
- `exactMatch` only where the terms are interchangeable. A role or team wrapper (a class that holds a person plus a role) is not `exactMatch schema:Person`; where the target is broader than the D4D term, use `broadMatch`.
- A `d4d:` target is not an alignment (#3054). Map to an external vocabulary or add nothing.
- Do not give a second class `exactMatch` to a target another class already has without saying why.

For **slots** owned by the class (not inherited from `Information`), add one triple per slot whose target is its `slot_uri` or a better external term. Skip inherited Information slots (title/description/doi/...): they already have rows.

## Standard target conventions (RO-Crate / FAIRSCAPE)

| RO-Crate concept | Target ID |
|---|---|
| Root Dataset | `schema:Dataset` (`@type=["Dataset", "https://w3id.org/EVI#ROCrate"]`, `@id="./"`) |
| Catalog (DCAT) | `dcat:Catalog` |
| Distribution / package | `dcat:Distribution` or `schema:DataDownload` |
| Individual file | `schema:MediaObject` |
| Sub-collection (nested Dataset) | `schema:Dataset` (with `@id != "./"`) |
| `hasPart` relationship | `schema:hasPart` |
| Byte size | `dcat:byteSize` or `schema:contentSize` |
| Hash values | `evi:md5`, `evi:sha256` |

## SKOS TTL template

In `src/data_sheets_schema/semantic_exchange/d4d_rocrate_skos_alignment.ttl`, append class-level triples under `# Class-level alignments`:

```turtle
d4d:{ClassName} skos:exactMatch {TARGET_ID} .
d4d:{ClassName} skos:closeMatch {SECONDARY_ID} .
```

and class-scoped slot triples under `# Class-level slot mappings`:

```turtle
d4d:{ClassName}_{slot_name} skos:exactMatch {SLOT_TARGET_ID} .
```

A slot that means the same in every class takes a slot-level triple instead, `d4d:{slot_name} skos:exactMatch {SLOT_TARGET_ID} .`, beside the other slot-level triples.

Confirm the TTL file declares every prefix you reference (`d4d:`, `schema:`, `dcat:`, `evi:`, `rai:`). Add `@prefix dcat: <http://www.w3.org/ns/dcat#> .` etc. if missing.

**What reaches the tables.** The comprehensive tables have one row per schema slot. Slot-level (`d4d:{slot}`) and class-scoped (`d4d:{Class}_{slot}`) triples feed them; a class-level triple (`d4d:{Class}`) is recorded in the TTL only and moves no table row. For a class-level mapping to be visible to schema consumers, also declare it on the class (`class_uri` / `exact_mappings` / `close_mappings`), which is a schema change with its own regeneration steps (see CLAUDE.md).

## Regenerate (mandatory after any TTL edit)

```bash
make gen-sssom-comprehensive gen-sssom-uri-comprehensive
make check-sssom-comprehensive
```

The first writes both tables (today's date in `mapping_date`); the second regenerates them in memory under the committed date and must report no drift. Read the generator's `WARNING:` lines: an unlisted or changed TTL/schema disagreement on a slot you touched means the TTL now contradicts the schema's declarations for it. Either fix the triple, or add the slot to `ACCEPTED_DISAGREEMENTS` (understood) or `OPEN_DISAGREEMENTS` (needs a decision) in `src/semantic_exchange/generate_comprehensive_sssom.py` with the exact TTL and schema pairs and a reason, then regenerate again. The tests fail on an unlisted, changed or stale listing.

No row names a person (#2971): the generator leaves `author_id` empty on every row, and credits itself in `mapping_tool` only on the rows it decided rather than a curated input declared. Never add an ORCID or any other `author_id`, in the tables or in anything that builds rows.

Do not hand-edit the structural table (`data/semantic_exchange/d4d_rocrate_structural_mapping.sssom.tsv`) and do not regenerate it here: it is derived from the schema, carries rows its generator cannot produce, and its drift is pinned by `tests/test_semantic_exchange/test_structural_mapping_drift.py`. A TTL edit does not move it.

## Validation (mandatory)

```bash
poetry run python -c "
import sys; sys.path.insert(0,'src')
from fairscape_integration.utils.sssom_integration import SSSOMIntegration
comp = SSSOMIntegration('src/data_sheets_schema/semantic_exchange/d4d_rocrate_sssom_comprehensive.tsv', verbose=False)
print('Comprehensive:', comp.get_active_implementation(), comp.get_mappings_count())
# Spot-check the slots whose triples you added
for s in ['SLOT1', 'SLOT2']:
    matches = comp.get_mappings_by_subject(f'd4d:{s}')
    assert matches, f'd4d:{s} missing from the comprehensive SSSOM'
    print(f'  d4d:{s} →', [(m['predicate_id'], m['object_id']) for m in matches])
"
poetry run python -m pytest tests/test_semantic_exchange tests/test_fairscape_integration -v
```

A slot's row shows the TTL target only when the TTL wins its precedence; if the spot-check shows another target, the generator docstring says why. All alignment and fairscape tests must pass.

## Branch + commit + PR

Conventional workflow:

```bash
git checkout main && git pull origin main
git checkout -b update_exchange   # or another descriptive name supplied by the user
# ... TTL edits, regeneration, validation ...
git add src/data_sheets_schema/semantic_exchange/d4d_rocrate_skos_alignment.ttl \
        src/data_sheets_schema/semantic_exchange/d4d_rocrate_sssom_comprehensive.tsv \
        src/data_sheets_schema/semantic_exchange/d4d_rocrate_sssom_uri_comprehensive.tsv
# plus src/semantic_exchange/generate_comprehensive_sssom.py if you listed a disagreement
git commit -m "Add SKOS mappings for {CLASSES} in the exchange layer

Brief explanation of the new triples and the reasoning behind primary/secondary targets.
Note any out-of-scope follow-ups (e.g. converter code TODOs)."
git push -u origin {BRANCH}
gh pr create --base main --title "Add SKOS mappings for {CLASSES}" --body "..."
```

The TTL and both regenerated tables go in the same commit: the drift tests fail on a commit that has one without the others.

## Out-of-scope reminders

When opening the PR, **explicitly call out** these as separate follow-ups (do NOT bundle them):

1. **Converter code** in `src/fairscape_integration/d4d_to_fairscape.py` and `fairscape_to_d4d.py`: the converters do not read the SSSOM tables, and their field mapping is written in code, so the mapping layer alone does not change what they emit.
2. **Schema YAML touch-ups** — verify each newly mapped class has matching `class_uri` and/or `exact_mappings` annotations in the YAML so the schema is self-consistent with the TTL. Add them in a small follow-up if needed; a schema change regenerates the merged schema and the comprehensive tables.

## Style and quality bar

- Put a `#` comment above each new group of triples saying **why** that target was chosen — point at the schema's `class_uri` or `exact_mappings`, or at a converter-code path that already produces that structure.
- Use `exactMatch` only for a documented schema-level equivalence; use `closeMatch` for semantic similarity that needs a transformation.
- Do not modify pre-existing triples unless explicitly asked — additive edits only.
- After commit, update anything that quotes the row or triple counts (e.g. the TTL's own `# Alignment Statistics` block, `notes/*`).
