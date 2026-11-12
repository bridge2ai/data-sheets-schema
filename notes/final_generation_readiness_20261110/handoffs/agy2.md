# G2 Handoff — Schema Collection-Type Prose & 3.2.1 Release Identity (#2975, #5799, #5800, #5801, #5803)

- **Worker**: `agy2` (Unit `G2`)
- **State**: **COMPLETE — RELEASE BUDGET (0 active tasks/processes; full specificity scan deferred to lead integrated checkout)**
- **Worktree**: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/agy-collection-type-prose-2975-20261110`
- **Branch**: `agy/collection-type-prose-2975-20261110`
- **Base Commit**: `7233f193ad102a8488b31ec7333662c8fefaa996` (schema `3.2.0`)
- **Source & Helper Commit**: `bb88e07621b7d01c0df865a1167c717d7c622a4e` (`bb88e0762`)
- **Final Generated Products Commit (`HEAD`)**: `db7ce7c108cdd9c8106376a145e822ebcceeaee0` (`db7ce7c10`)
- **Scratch Evidence Directory**: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-g2-2975-20261110`

---

## 1. Summary of Completed Work & Commits

1. **Commit `bb88e07621b7d01c0df865a1167c717d7c622a4e` (`7 files changed, 497 insertions(+), 11 deletions(-)`)**:
   - [D4D_FileCollection.yaml](../../../agy-collection-type-prose-2975-20261110/src/data_sheets_schema/schema/D4D_FileCollection.yaml) (`sha256: 26a4ea612b2d456dd623aba2c8b10a89f502cd8c226ffdc3b051c04fe583a965`): aligns `FileCollection.collection_type` description (`lines 135–139`) with its scalar `FileCollectionTypeEnum` declaration (`Primary content classification for this file collection from FileCollectionTypeEnum. Each FileCollection has one collection_type value; represent differently classified file groups as separate FileCollection entries in the dataset's file_collections.`), preserving scalar cardinality, `FileCollectionTypeEnum` members, neutral wording, and consistency with `FileCollection.resources` (`#226`, `#2975`).
   - [data_sheets_schema.yaml](../../../agy-collection-type-prose-2975-20261110/src/data_sheets_schema/schema/data_sheets_schema.yaml), [data_sheets_schema_core.yaml](../../../agy-collection-type-prose-2975-20261110/src/data_sheets_schema/schema/data_sheets_schema_core.yaml), [D4D_Core.yaml](../../../agy-collection-type-prose-2975-20261110/src/data_sheets_schema/schema/D4D_Core.yaml), and [CITATION.cff](../../../agy-collection-type-prose-2975-20261110/CITATION.cff): declare `version: 3.2.1` (`pyproject.toml` package `version = "0.1.0"` untouched).
   - [test_schema_release_identity.py](../../../agy-collection-type-prose-2975-20261110/tests/test_schema_release_identity.py) (`sha256: ade18646815f8fd5a0fdda613186bd9a4bf2662724298cda10f15b2829f451a6`): sets `RELEASE = "3.2.1"`, adds `test_file_collection_type_prose_matches_scalar_declaration`, and updates negative drift mutation literals (`lines 421, 442, 444`) to target `3.2.1` without mutating historical `3.2.0`.
   - [g2_collection_type_release_20261110.py](../../../agy-collection-type-prose-2975-20261110/scripts/adhoc/g2_collection_type_release_20261110.py) (`19,961 B`, `sha256: b8c167f436c11f72dc0ddf97c92687a69541c26c7ce93b3c2f27866737ca6009`): provenance helper incorporating `#5799`, `#5800`, and `#5801` fixes (repository-relative schema input paths, staged JSON-LD context URI relocation to `project/jsonld/data_sheets_schema.context.jsonld`, preserved `.venv/bin` symlink path, before/after full & Core API digest comparison across `neutral` and `bridge2ai`, and refusal on existing staging/receipt paths).
2. **Commit `db7ce7c108cdd9c8106376a145e822ebcceeaee0` (`9 files changed, 1781 insertions(+), 1767 deletions(-)`)**:
   - Materialized `3.2.1` merged schemas (`data_sheets_schema_all.yaml` and `data_sheets_schema_core_all.yaml`), project exports (`data_sheets_schema.py`, `data_sheets_schema.schema.json`, `data_sheets_schema.jsonld` with relocated context, `data_sheets_schema.owl.ttl`), comprehensive SSSOM pair (`d4d_rocrate_sssom_comprehensive.tsv` and `d4d_rocrate_sssom_uri_comprehensive.tsv`), and appended `3.2.1` to [release_history.yaml](../../../agy-collection-type-prose-2975-20261110/src/data_sheets_schema/schema/release_history.yaml) (`sha256: 749d8fe23bcaf50b0773d507956afb3b7764ec40eba950af7868e849cc2f741c`).

---

## 2. Verified `3.2.1` Schema Hashes, API Digests, and SSSOM Note

From `g2_release_3_2_1_receipt.json` (`sha256: 227486ae72fc06431ec2b12044dcbd2e23dd00da318197fc266513fbe3947780`):

- **Historical `2.0.0`..`3.2.0` prefix SHA-256 (preserved byte-for-byte)**: `83be0fe4f69a6fc8cfe9154cfd25518190c0648022616e0aa120e60005ddcc42`
- **Measured `3.2.1` schema hashes**:
  - `full_source_sha256`: `3cc458d7554e543fb3684d5718b226e03a64b3c3141d92977d53a0cb9733422d`
  - `full_merged_sha256`: `bc560a3cd5d04c49e95fcbf33fa8ac349171df1a877e7e0882827bd526a95214`
  - `core_source_sha256`: `49044208a00774adaa02d3d0936b2c7d1c01253bd5629a3400c5e99f4c413117`
  - `core_merged_sha256`: `e174a7a6ec1b5eccef5ee4a8b9f8f773f48243c2d6012ff8a1b846b45a40d088`
- **Before/after API `schema_digest` equality (`api_schema_digests_unchanged: true`)**:
  - `neutral.Dataset`: `md5: 94fb1b7b3e8ea42ac151bbe52b5f5f72`, `sha256: 438c9d3aa87fdf8b0560eb2a64aa5063e1bb6705ecf72b6973e3e257cb037360`
  - `neutral.CoreDataset`: `md5: 47c578052bab48144fc2575826aef4c1`, `sha256: c29406f5c8a1693c7d9edcba3c1a2942d16786af9d77239fa6dc7798627d3f6c`
  - `bridge2ai.Dataset`: `md5: c807b62f37e927c5d49addf273957a34`, `sha256: 15dfcb238b8c8b51e84ad7921c928d299ce02d28df55cde855c6dc39bf4aae84`
  - `bridge2ai.CoreDataset`: `md5: f3943c162b41d94850fd60dde7c41ba7`, `sha256: bda503434266ec4be2cdf21c34fae3afa3fec486d3da2ca9c9d242851d696049`
- **Comprehensive SSSOM note**: Both `d4d_rocrate_sssom_comprehensive.tsv` (`sha256: 2a4ba42f1b132b3ec0c66de27af2805d3c5ac78394dbb2e0a4d532e783954cb7`) and `d4d_rocrate_sssom_uri_comprehensive.tsv` (`sha256: 8341d53b5c8745fde60a1ed69479ce298c6e75d2cb3b9323658596e4eb8c5cc5`) pass `--check` with zero drift. Replacing `"description"`-triggering wording on `collection_type` shifts its heuristic `mapping_status` comment from `free_text` to `unmapped` (`free_text: 13 -> 12`, `unmapped: 84 -> 85`), while its `object_id` (`d4d:NoTermFound`) and `predicate_id` (`skos:closeMatch`) are unchanged.

---

## 3. Saved Execution & Test Evidence (`/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-g2-2975-20261110/`)

| File | SHA-256 | Result |
|---|---|---|
| `dry_run.json` | `76de0818d9719a2a17515c6a3b3871ad92d1f8c04a8d5d68ca475fd010acf198` | Pre-build dry-run check passed (`0` errors). |
| `canary-junit.xml` / `canary-pytest.log` | `456e03a848645d9e58f42c79eaa966f2029eea2e038ec8905474c7fb9c5ed863` / `6313ab0794a722f002be8e4e50cd882379789cea993f77744bfddbd5d4d5343a` | Single-node canary `test_full_and_core_declare_the_same_release`: `1 passed in 0.08s`. |
| `execute.log` / `g2_release_3_2_1_receipt.json` | `ab5abb303707ddad2fee339fac651fc0e0493b4cfbec0e461168523888811bcb` / `227486ae72fc06431ec2b12044dcbd2e23dd00da318197fc266513fbe3947780` | Full `3.2.1` build, SSSOM regeneration + `--check`, and before/after API digest equality check passed (`exit 0`). |
| `check-sync-and-digest.log` / `focused-pytest-junit.xml` / `focused-pytest.log` | `02681d7386487caadb8b1028a3767622b29f053c16944e7e39815014592fac6c` / `1f95abe7b81ceebe9b3e7ed509419d32184537a9db145b0aedcaf8e6f5536c3d` / `96225676d36f73648ff2358d5ee2b25dd94903fcbc77a11f0e3adb1b01ad9478` | Preserved initial wrong-`cwd` invocation (`#5803`, `22 passed, 2 failed` when `Path.cwd()` was primary checkout on `3.0.0`). |
| `check-sync-and-digest-worktree.log` | `a207f35379998e0c9d53b532b882c1bfd182591e59184631c8086536845845d0` | Worktree-rooted `check-schema-sync.sh` and `d4d schema check-digest --strict`: `in_sync Dataset digest 94fb1b7b3e8e`, `in_sync CoreDataset digest 47c578052bab` (`exit 0`). |
| `focused-pytest-worktree-junit.xml` / `focused-pytest-worktree.log` | `067222aa6206b9b2fb4e2f6d2b1b18d8b7d77c334ca3e48d50824f0caddf07be` / `0d00d793241d63cd0daadda74b129b5c650baf92fc6bdd5abc0b45ce2c27d0b6` | Worktree-rooted focused suite (`test_schema_release_identity.py`, `test_neutral_generation_schema.py`, `test_report_claims_corpus.py::test_the_release_history_ends_at_the_schema_on_disk`): **`24 passed, 0 failed, 0 errors, 0 skipped in 10.13s`**. |

- **Full-repo specificity scan**: Not started in `G2` (`test_neutral_generation_schema.py` `7/7` passed); deferred to lead's final integrated checkout per lead direction.
- **Runtime budget**: **RELEASED**.
