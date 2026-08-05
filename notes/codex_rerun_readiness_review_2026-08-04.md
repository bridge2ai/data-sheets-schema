# Codex review: readiness for the final D4D generation rerun

External review, 2026-08-04. Run through the Codex CLI (`gpt-5.3-codex`), session
`019fcf48-c145-7b41-96f0-f0d9f7d44e89`, 13m 19s, against main at `f0d61d43179f`.

Asked two questions: whether any unmerged branch holds work that must land before
the rerun, and what remains on main to prepare for it. It was given the planned
sequence, the relevant notes, and the open issues, and asked to read the actual
diffs rather than judge branches by name.

**Reproduced verbatim.** File paths are absolute, as the review emitted them.
Two things it reported are worth reading with the environment in mind: it could
not run the full suite (no writable temp directory in its sandbox) and it saw
`gh` unauthenticated, so it took issue and branch state from the GitHub service
rather than local refs. Its git-level findings — merge-bases, patch-ids,
divergence counts — were computed locally and are checkable.

---

## 1. Must land before rerun

**None of the inspected branches must be merged.** Main is at `f0d61d43179f`; no open PR supplies missing generation, schema, selection, canonical-enumeration, or semantic-evaluation functionality.

The plausible branches either contain obsolete schema work or changes already superseded on main. In particular, neither `origin/slot_uris` nor `slot_uris_2_backup` implements the class-level or `schema:`/`dcat:` structural mappings requested by #294. The preparation blockers identified below therefore require new changes on main, not merging an existing branch.

## 2. Stale / can be closed

- `origin/explorer-sync-update` — tip `449431203d73`, merge-base `ecc8012bf3d5`, main/branch divergence `131/19`; its entire current net diff is six path/name edits in `utils/d4d_to_synapse_table.py`, changing old HTML locations and `AI-READI` to `AI_READI`. No generation, schema, or evaluation code remains unique.

- `origin/slot_uris` — tip `343dbf54a448`, merge-base `4322abb025dc`, divergence `158/19`; it has 213 parsed `slot_uri` mappings versus main’s 342, including obsolete conflicts such as `target_dataset: schema:identifier` where main now uses `dcterms:relation`. It contains only older comprehensive SSSOM scripts, not the structural generator capability required by #294.

- `slot_uris_2_backup` — tip `ad732a260e32`, merge-base `9a522ecc928a`, divergence `156/30`; main’s reviewed squash `13c2a00a` is nearly its schema result, while current main has 342 mappings versus the backup’s 276. Against `origin/slot_uris` it is `3/16` commits divergent, so **neither is a strict subset or superset** of the other.

- `fix-curated-mislabel` — tip `8379a85d6448`, merge-base `594b0d582e46`, divergence `124/4`; its four commits (`2b730155`, `681aa3d8`, `893f6c47`, `8379a85d`) are a feature subset/precursor of main squash `999f43ba`, which retains the corrected “not hand-curated” provenance and label-aware evaluation work.

- `unified-cli-constants` — tip `dd67cef0e6db`, merge-base `81800d69ae2f`, divergence `154/15`; its aggregate patch-id exactly equals main commit `84637af7` (`8e074a4bd4071bfb935bb111d0bf1363aa89c880`), and the direct tree diff at that point is empty. It is an exact content subset already on main.

- `origin/d4d/add-ai-readi-flagship-datasheet` — `392806cb`; adds 174 lines to an old extracted YAML/HTML pair, including `data/extracted_by_column/AI_READI/ai_readi_flagship_d4d.yaml`; no source or schema changes.

- `origin/d4d/add-cm4ai-comprehensive-datasheet` — `71c4db53`; adds 38 lines to an old extracted YAML/HTML pair only.

- `origin/d4d/add-cm4ai-consolidated-datasheet` — `021f9449`; adds 279 lines solely to `data/sheets_d4dassistant/cm4ai_d4d.yaml`.

- `origin/d4d/add-cm4ai-datasheet` — `7363339b`; adds 340 lines solely to the same legacy `data/sheets_d4dassistant/cm4ai_d4d.yaml` path.

- `origin/d4d/add-cm4ai-minimal-datasheet` — `ab0a0eeb`; adds 121 lines across a legacy YAML and generated HTML.

- `origin/d4d/add-gene-ontology-datasheet` — `f5895e98`; adds 168 lines solely to `data/sheets_d4dassistant/gene_ontology_d4d.yaml`.

- `origin/d4d/add-hpo-dated-datasheet` — `3fa5efbc`; adds 101 lines to one legacy HPO YAML.

- `origin/d4d/add-human-phenotype-ontology-datasheet` — `ba4d8345`; adds 379 lines across an HPO YAML and generated HTML.

- `origin/d4d/add-phenopackets-datasheet` — `e032574a`; adds 407 lines across one extracted YAML and generated HTML.

- `origin/d4d/add-t2d-datasheet` — `ccfffdf4`; adds 40 lines across one YAML and generated HTML.

- `origin/d4d/add-voice-comprehensive-datasheet` — tip `dad39d71` after `1aa65d13` and `b4db7ce8`; adds 786 lines solely to `data/extracted_by_column/VOICE/b2ai_voice_comprehensive_d4d.yaml`.

- `origin/poster_panels` — `6df5f13280ea`; deletes one DOT line and regenerates `data/poster_assets/figures/fig6_d4d_full.png`, with no executable or schema changes.

- `origin/gh-pages` — `944cfba48f49`, “Deployed 323bb918 with MkDocs 1.5.3”; it has no merge-base with main and consists of generated `index.html` pages and deployment assets. Do not merge it; retain it only if GitHub Pages still deploys from this branch.

## 3. Remaining prep on main

Registration and basic reachability are already satisfied: `VOICE_PEDIATRIC` is present in [projects.py](/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/data_sheets_schema/constants/projects.py:25), `generic_v3` is registered in [api_runner.py](/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/data_sheets_schema/api_runner.py:50), and a source-level dry run successfully planned all five projects under `generic_v3`.

1. **Resolve the experiment/evaluation scope mismatch before spending calls.** [generic_v3_analysis_plan.md](/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/notes/generic_v3_analysis_plan.md) specifies the four-project, three-replicate v2-versus-v3 comparison; [NEXT_TASKS.md](/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/NEXT_TASKS.md) says `VOICE_PEDIATRIC` should be generated once under the winning condition because it has no v1/v2 baseline. Also, five selected projects × full/core × two rubrics equals **20**, not 12, semantic evaluations. Decide and record whether pediatric is outside the comparison and which projects the 12 evaluations cover. This is the blocking part of #287.

2. **Repair rubric20 semantic evaluation before running it.** The canonical [rubric20.txt](/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/data/rubric/rubric20.txt:493) has 17 numeric questions, three pass/fail questions, Q20 “Bias Documentation and Responsible AI Alignment,” and an 88-point maximum. In contrast:

   - [.claude/agents/d4d-rubric20-semantic.md](/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.claude/agents/d4d-rubric20-semantic.md:406) still has the former pass/fail “Interlinking Across Platforms” Q20 and repeatedly calculates an 84-point maximum.
   - [rubric20_semantic_schema.json](/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/download/prompts/rubric20_semantic_schema.json:65) enforces `const: 84`.
   - [D4D_Evaluation_Summary.yaml](/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/data_sheets_schema/schema/D4D_Evaluation_Summary.yaml:472) describes rubric20 as max 84.
   - [rubric20_output_format.json](/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/download/prompts/rubric20_output_format.json:13) is also stale at 84.

   Align these files with the canonical rubric and add a test comparing semantic-agent question text/types and denominators directly to `data/rubric/rubric20.txt`. Existing scoring tests only cover scripts and the non-semantic system prompt, which is why this survived #275’s correction.

3. **Make the five-project CLI invocation explicit and reproducible.** [cli/api.py](/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/data_sheets_schema/cli/api.py:158) still defaults to `AI_READI,CHORUS,CM4AI,VOICE` and its help text omits pediatric. Either update the default/help from the project registry or freeze the complete explicit `--projects` argument in the runbook. The explicit five-project dry run works today.

4. **Predeclare the VOICE selection-failure policy.** [test_enum_alias_normalisation.py](/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/tests/test_enum_alias_normalisation.py:88) intentionally leaves invalid `related_to` values uncorrected, and `NEXT_TASKS.md` records this as a likely VOICE failure mode. Decide whether a failed candidate is discarded, regenerated unchanged, or handled through a separately documented correction. Do not silently modify generic-v3’s prompt: its one-rule delta is part of the preregistered comparison.

5. **Separate the paid rerun from existing workspace artifacts.** This checkout is currently not clean: twelve root-level `D4D_*.yaml` files are untracked, and the `aurelian` submodule is dirty/ahead with untracked download directories. Preserve, relocate, or intentionally record those artifacts before generating so they cannot be mistaken for rerun outputs.

6. **Run the full verification suite in a writable environment after the semantic fixes.** Current provenance is healthy: source invocation of `d4d runs check --strict` reports `131 run(s) checked, 49 subject, 0 failing`; canonical enumeration currently returns six paths for AI_READI, CHORUS, and CM4AI, with VOICE and VOICE_PEDIATRIC correctly reported missing. Re-run all 1,114 tests plus the new semantic-parity tests, then repeat the five-project `generic_v3` dry run.

7. **Use this issue disposition for this rerun:**

   - Blocking/pre-rerun decision: #287’s corpus/scope arithmetic and the rubric20 semantic inconsistency associated with the historical #275 transition.
   - Deferrable: #242’s 434-call legacy re-judge, because the planned workflow does not rerun judge agreement; #286’s archived summaries, provided fresh results remain separately labeled; #294’s SSSOM structural generator; and #297’s string-versus-inline-object limitation.
   - Already completed: #258 and #262 are closed; #275 is closed for the 84→88 scoring correction, although it did not update the semantic prompt files.
   - Issue state is stale: #306 remains open, but `d4d runs canonical --paths-only` is implemented on main by `4ac9d45b`.

## 4. Open questions / could not verify

- The intended evaluation corpus remains ambiguous: “12 evaluations” is consistent with three canonical projects, while selecting all five projects creates 20 full/core × rubric evaluations. This must be answered before execution.

- `gh auth status` reported an invalid CLI token. Live issue and branch state was obtained through the connected GitHub service, but I could not independently refresh the local remote-tracking refs with `git fetch` in this read-only workspace.

- I could not reproduce the full claimed 1,114-test run. A targeted run produced 50 passing tests and 60 passing subtests; four cases failed solely because `tempfile.TemporaryDirectory` could not obtain a writable temporary directory under this sandbox.

- The installed `d4d` executable is absent in this environment, although the `pyproject.toml` entry point exists and invoking the CLI directly from `src/` successfully exercised `generic_v3`, all five project bundles, strict checks, and canonical enumeration.

- The supplied “main is clean” state does not match this checkout’s present status because of the untracked root YAMLs and dirty `aurelian` submodule; I did not alter or remove them.

Codex session ID: 019fcf48-c145-7b41-96f0-f0d9f7d44e89
Resume in Codex: codex resume 019fcf48-c145-7b41-96f0-f0d9f7d44e89
