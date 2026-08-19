<!-- Saved verbatim. Do not edit the review body: it is evidence of what was
     found on this date, not a living document. Corrections belong in the
     issues filed from it, which are linked below. -->

# Codex review: does the D4D pipeline generalize beyond Bridge2AI?

- **Run:** 2026-08-19, Codex session `01a018cd-adcd-7203-9a7b-e46abdc7e340`
- **Question asked:** find anything hard-coded to specific Bridge2AI Grand
  Challenges (AI_READI, CHORUS, CM4AI, VOICE, VOICE_PEDIATRIC) or to any other
  specific case that would stop the pipeline generalizing to different datasets,
  use cases and domains.
- **Scope:** whole repository — download, preprocessing, concatenation, both
  generation runtimes, prompts and the registry, provenance, evaluation, the
  schema, the Makefile and CI.

## Why this was asked now

The v5 production arm is about to run over four Bridge2AI projects. That arm is
a study; the pipeline underneath it is meant to be reusable. Nothing had ever
checked whether the second claim was true, and a review taken *before* the arm
records the state the arm was run against.

## What it concluded

The single-dataset API path already generalizes: `d4d api run --project NEW
--bundle path --condition generic` works for an arbitrary name, and the GitHub
assistant generates from any named input directory. **Everything around it does
not.** Download, preprocessing, concatenation, batch generation, most of
evaluation, status reporting, the RO-Crate arms and the Make targets all take
their project universe from a hard-coded list, so a new dataset cannot be
onboarded by configuration alone.

Two findings are defects rather than limits, and both are about a record
asserting something untrue:

- provenance always attests the Bridge2AI source manifest as an input, even for
  an external bundle that never came from it;
- evaluation recovers project and method by splitting a key on the first
  underscore, so `AI_READI` is already reported as project `AI`.

## Standing caveat on the rubrics

The review finds the rubrics are not domain-neutral. Read that alongside #177:
`curated` is not a gold standard and this repository has no reference records.
A rubric that rewards biomedical framing and a corpus with no reference are
separate problems that compound.

---

# D4D Pipeline Generalizability Review

## Summary

The pipeline is **not currently configurable end-to-end for an arbitrary new project without code edits**. The strongest exception is the current single-dataset API path: `d4d api run --project NEW --bundle path --condition generic` and the GitHub assistant can generate records for an arbitrary named input directory. Downloading, preprocessing, concatenation, batch generation, most evaluation commands, status/reporting, RO-Crate arms, and Make targets still derive their project universe from hard-coded Bridge2AI lists. Additionally, provenance always records the Bridge2AI source manifest, and the rubrics contain material Bridge2AI/clinical assumptions.

The minimum generalization work is to derive projects and source directories from a supplied manifest; remove `click.Choice(PROJECTS)` from dataset identifiers; pass the manifest through generation, ranking, and provenance; add per-project bundle mapping to batch generation; and make rubric applicability/configuration domain-neutral. The repository itself explicitly presents the four-GC corpus as a major use case, so several study-specific arms and analyses appear intentional, but they should be separated from the reusable pipeline.

Severity labels:

- **Blocker** — blocks the standard command/path for a non-B2AI project.
- **Workaround/quality** — direct invocation, file preparation, flags, or code/config work can bypass it, or output quality is degraded.
- **Cosmetic** — documentation, examples, comments, or naming only.

---

## 1. Download and source scoping

1. [`src/data_sheets_schema/cli/download.py:14`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/data_sheets_schema/cli/download.py:14>), commands `sources`, `preprocess`, `concatenate`, `supplements`, `audit-manifest`, `scope`, and `audit-bundles`

   - Hard-coded assumption: the default source is one fixed Bridge2AI Google Sheet, and every project option is `click.Choice(PROJECTS)`.
   - Effect: a project present only in a new/custom manifest is rejected before the command reads that manifest. This affects downloading, preprocessing, concatenation, manifest auditing, scope checking, and bundle auditing.
   - **Severity: Blocker.**

2. [`src/download/organized_dataset_extractor.py:1124`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/download/organized_dataset_extractor.py:1124>), `main()`

   - Hard-coded value: `--projects` accepts only `AI_READI`, `CHORUS`, `CM4AI`, and `VOICE`; it even omits `VOICE_PEDIATRIC`.
   - Effect: `d4d download sources` always forwards `--projects`, so an arbitrary project and the pediatric project fail in the underlying parser even if the outer CLI or manifest were extended.
   - **Severity: Blocker.**

3. [`src/download/organized_dataset_extractor.py:177`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/download/organized_dataset_extractor.py:177>), `process_spreadsheet()`; [`src/data_sheets_schema/cli/download.py:30`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/data_sheets_schema/cli/download.py:30>)

   - Assumption: sources arrive as URLs in project-named columns of a CSV-exportable spreadsheet.
   - Effect: a dataset described by a directory, catalog API, repository manifest, object store, or other source inventory must first be remodeled into this sheet shape or manually entered in `source_manifest.yaml`. The extractor itself can normalize an unknown column name, but the CLI allowlist prevents reaching that generic behavior.
   - **Severity: Workaround/quality.**

4. [`data/preprocessed/source_manifest.yaml:3`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/data/preprocessed/source_manifest.yaml:3>), [`:110`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/data/preprocessed/source_manifest.yaml:110>), [`:231`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/data/preprocessed/source_manifest.yaml:231>)

   - Hard-coded values: the fixed Bridge2AI sheet, selection history, bundle hashes, scope declarations, and source lists for the five known datasets.
   - Effect: this is expected corpus configuration rather than inherently defective code, but it is also the global default used throughout the pipeline. There is no project catalog/config option selecting another manifest for API generation or provenance, so an external corpus cannot simply supply a parallel manifest end-to-end.
   - **Severity: Workaround/quality.**

5. [`data/preprocessed/source_manifest.yaml:195`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/data/preprocessed/source_manifest.yaml:195>), `source_priority`

   - Domain assumption: priority types are research-release/biomedical categories such as `RO-Crate`, `DUA`, `IRB`, `NIH project page`, publication, preprint, and historical release.
   - Effect: domain-specific source types not added to this table receive rank `99` through [`source_priority.py:70`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/data_sheets_schema/source_priority.py:70>) and cannot win a disagreement. The API runner reads this fixed manifest rather than a user-selected one.
   - **Severity: Workaround/quality.**

6. [`data/preprocessed/source_manifest.yaml:612`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/data/preprocessed/source_manifest.yaml:612>), [`organized_dataset_extractor.py:91`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/download/organized_dataset_extractor.py:91>), `promote_canonical_downloads()`

   - Hard-coded shape: `VOICE_PEDIATRIC_source_dir` is stored inside the `projects` mapping alongside actual project lists.
   - Effect: an unfiltered promotion uses every mapping key as a project, then iterates the source-directory string as though it were a list of source records and accesses `entry["raw_file"]`. This can break `make download-sources`, which does not pass a project filter. It also establishes an undocumented metadata-key naming convention for any future dataset sharing another dataset’s corpus.
   - **Severity: Blocker for the unfiltered download path; workaround for individually filtered downloads.**

7. [`src/download/organized_dataset_extractor.py:341`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/download/organized_dataset_extractor.py:341>), `_process_url()`

   - Hard-coded host handlers: NIH RePORTER, bioRxiv/medRxiv, Dataverse, PhysioNet, Health Data Nexus, FAIRhub, GitHub, and Google Drive receive specialized treatment.
   - Effect: other sites fall back to plain HTML extraction, so this is not a total blocker, but JavaScript catalogs, authenticated repositories, APIs, and non-HTML resources outside the recognized hosts are likely to produce incomplete content.
   - **Severity: Workaround/quality.**

8. [`src/download/organized_dataset_extractor.py:879`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/download/organized_dataset_extractor.py:879>) and [`:982`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/download/organized_dataset_extractor.py:982>)

   - Hard-coded behavior: Health Data Nexus and generic DOI handlers save only a small JSON object containing the URL/DOI and never fetch the dataset page or resolve the DOI.
   - Effect: any arbitrary source expressed as a DOI, and any Health Data Nexus source, enters preprocessing without its substantive documentation.
   - **Severity: Workaround/quality.**

9. [`src/download/organized_dataset_extractor.py:51`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/download/organized_dataset_extractor.py:51>), [`src/data_sheets_schema/fetch.py:46`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/data_sheets_schema/fetch.py:46>)

   - Assumption: a usable source contains at least 500 characters/bytes unless overridden per manifest entry.
   - Effect: legitimate short metadata records, compact machine-readable descriptors, or small domain vocabularies fail promotion/fetch unless each source lowers the threshold manually.
   - **Severity: Workaround/quality.**

---

## 2. Preprocessing

1. [`src/download/preprocess_sources.py:21`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/download/preprocess_sources.py:21>) and [`:394`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/download/preprocess_sources.py:394>)

   - Hard-coded value: the default project set is `PROJECTS`, rather than the supplied manifest’s keys.
   - Effect: adding a project only to the manifest does not make an unqualified preprocessing run discover it; `PROJECTS` must also be edited or the project must be passed directly to the script.
   - **Severity: Blocker for config-only onboarding.**

2. [`src/download/preprocess_sources.py:193`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/download/preprocess_sources.py:193>), `preprocess_manifest()`

   - Assumption: raw input for every project is under `input_dir/<project>/`.
   - Effect: the manifest’s `VOICE_PEDIATRIC_source_dir` override is honored only during concatenation, not preprocessing. A second dataset sharing another dataset’s raw corpus cannot be rebuilt through the normal preprocessing command without copying files or changing code.
   - **Severity: Workaround/quality; blocks shared-corpus preprocessing as configured.**

3. [`src/download/preprocess_sources.py:108`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/download/preprocess_sources.py:108>), `extract_source_text()`

   - Hard-coded formats: only TXT, Markdown, JSON, PDF, HTML, and DOCX are accepted.
   - Effect: CSV, TSV, XLSX, XML, YAML, presentation files, images, audio/video, database exports, notebooks, and domain-native formats require external conversion. This is especially inconsistent with [`organized_dataset_extractor.py:396`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/download/organized_dataset_extractor.py:396>), which exports Google Sheets as XLSX that preprocessing then rejects.
   - **Severity: Workaround/quality.**

4. [`src/download/preprocess_sources.py:24`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/download/preprocess_sources.py:24>), `extract_pdf_text()`

   - Assumption: PDF text is directly extractable with `pdfminer`; no OCR or scanned-document detection exists.
   - Effect: image-only reports, scanned forms, and many archival domain documents become empty or fail the 500-character threshold.
   - **Severity: Workaround/quality.**

5. [`src/download/validate_preprocessing_quality.py:169`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/download/validate_preprocessing_quality.py:169>) and [`:371`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/download/validate_preprocessing_quality.py:371>)

   - Hard-coded assumptions: without a manifest, validation only derives expected outputs from PDF and HTML files; defaults are the original four projects, excluding `VOICE_PEDIATRIC`.
   - Effect: TXT, JSON, Markdown, and DOCX preprocessing may go unchecked in fallback mode, and new projects are invisible by default. Manifest mode avoids the format-discovery issue but not the surrounding project defaults.
   - **Severity: Workaround/quality.**

---

## 3. Concatenation and corpus shape

1. [`src/data_sheets_schema/cli/download.py:111`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/data_sheets_schema/cli/download.py:111>)

   - Hard-coded value: `d4d download concatenate --project` is a `click.Choice(PROJECTS)`.
   - Effect: a correctly preprocessed project declared only in the manifest cannot be concatenated through the supported CLI.
   - **Severity: Blocker.**

2. [`src/download/concatenate_documents.py:15`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/download/concatenate_documents.py:15>), `files_from_manifest()`

   - Assumption: every canonical processed artifact is a `.txt` file in one project directory.
   - Effect: structured artifacts cannot remain structured through concatenation, and a project distributed across multiple source roots requires copying or the special single-source-directory override. Normalizing everything to text also discards file-type semantics unless they survive in embedded headers.
   - **Severity: Workaround/quality.**

3. [`src/data_sheets_schema/schema/data_sheets_schema.yaml:118`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/data_sheets_schema/schema/data_sheets_schema.yaml:118>), [`src/download/prompts/d4d_generic_arm_prompt_v5.md:177`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/download/prompts/d4d_generic_arm_prompt_v5.md:177>)

   - Shape assumption: one project bundle produces one `Dataset` record with one referent.
   - Effect: a catalog, benchmark suite, collection of peer datasets, multi-table data product with independently publishable components, or project covering several releases/cohorts must be split manually or represented as nested `resources`. This appears intentional in the current schema/prompt design, but it is a limitation for arbitrary “project” scopes.
   - **Severity: Workaround/quality; intentional documented scope.**

---

## 4. D4D extraction — agentic and API paths

1. [` .claude/commands/d4d-agent.md:27`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.claude/commands/d4d-agent.md:27>) and [`:92`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.claude/commands/d4d-agent.md:92>)

   - Hard-coded values: exact four-project inventory, source counts/sizes/files, and a generation loop over `AI_READI`, `CM4AI`, `VOICE`, and `CHORUS`.
   - Effect: the default agentic command ignores arbitrary projects and `VOICE_PEDIATRIC`; a user must explicitly rewrite the task with exact external bundle/output paths.
   - **Severity: Blocker for its default all-project mode; manual workaround for a specifically named project.**

2. [` .claude/commands/d4d-full-core.md:1`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.claude/commands/d4d-full-core.md:1>), [`:12`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.claude/commands/d4d-full-core.md:12>), [`:59`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.claude/commands/d4d-full-core.md:59>)

   - Hard-coded assumptions: defaults to the original four GCs and fixed `{PROJECT}_preprocessed.txt` plus the global Bridge2AI manifest.
   - Effect: an arbitrary project can plausibly be named explicitly, but only if its files have already been placed in the expected repository layout; there is no manifest-selected external path.
   - **Severity: Workaround/quality.**

3. [` .claude/agents/d4d-provenance-guard.md:58`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.claude/agents/d4d-provenance-guard.md:58>)

   - Hard-coded evidence boundary: allowed inputs are the repository’s fixed concatenated path, global manifest, and repository schemas.
   - Effect: a legitimate external manifest or source hierarchy is technically outside the stated agentic allowlist unless copied into those paths or the instructions are adapted.
   - **Severity: Workaround/quality.**

4. [`src/data_sheets_schema/cli/api.py:36`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/data_sheets_schema/cli/api.py:36>), `_spec()` and `_require_bundle()`

   - Current generalized behavior: a project is a free string, and an unknown project works when `--bundle` is supplied.
   - Remaining assumption: known projects alone receive conventional bundle resolution; external projects cannot declare a custom manifest or bundle mapping in configuration.
   - Effect: single-dataset generic API generation works, but it is an isolated entry point rather than an end-to-end onboarding mechanism.
   - **Severity: Workaround/quality.**

5. [`src/data_sheets_schema/cli/api.py:273`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/data_sheets_schema/cli/api.py:273>), `batch_cmd()`

   - Hard-coded value: default projects are `AI_READI,CHORUS,CM4AI,VOICE`; batch mode has no per-project `--bundle` option.
   - Effect: external projects can be named only if their bundle already matches the selected arm’s fixed filename pattern under `data/preprocessed/concatenated/`.
   - **Severity: Blocker for arbitrary bundle locations; workaround by copying/renaming files.**

6. [`src/data_sheets_schema/cli/api.py:13`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/data_sheets_schema/cli/api.py:13>) and [`constants/methods.py:73`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/data_sheets_schema/constants/methods.py:73>)

   - Hard-coded arms: baseline, de novo with RO-Crate, crate-only, and Healthsheet-only; Healthsheet is AI-READI-only and crate-only explicitly lists CHORUS/CM4AI/VOICE.
   - Effect: arbitrary evidence variants or domain-specific structured metadata types require code edits. The baseline remains usable; these appear to be intentionally Bridge2AI-specific experimental arms.
   - **Severity: Workaround/quality; intentional study scope.**

7. [`src/data_sheets_schema/healthsheet.py:23`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/data_sheets_schema/healthsheet.py:23>)

   - Hard-coded values: AI-READI FAIRhub input path, output name, and emitted `Project: AI_READI`.
   - Effect: another Healthsheet-like structured source cannot use this builder without code changes.
   - **Severity: Workaround/quality; intentional AI-READI-only experiment.**

8. [`src/data_sheets_schema/cli/rocrate.py:151`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/data_sheets_schema/cli/rocrate.py:151>) and [`data/ro-crate_packages/crate_manifest.yaml:25`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/data/ro-crate_packages/crate_manifest.yaml:25>)

   - Hard-coded values: RO-Crate normalize/bundle/map/emit commands use `click.Choice(PROJECTS)`, and the package manifest contains only CHORUS, CM4AI, AI_READI, and VOICE.
   - Effect: an arbitrary project’s valid RO-Crate cannot enter the comparison arms through the standard CLI without editing `PROJECTS`.
   - **Severity: Blocker for the RO-Crate experiment path; baseline extraction unaffected.**

9. [`src/download/interactive_d4d_wrapper.py:25`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/download/interactive_d4d_wrapper.py:25>), [`:36`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/download/interactive_d4d_wrapper.py:36>), [`:205`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/download/interactive_d4d_wrapper.py:205>)

   - Hard-coded assumptions: an obsolete OntoGPT schema URL; GC-specific keyword, clinical, filename, and host relevance tests; multiple sources are assumed to describe one dataset.
   - Effect: an unknown project receives no project keywords and is flagged irrelevant; metadata extraction uses a schema outside this repository. The Make target `extract-d4d-individual-gpt5` still invokes this wrapper.
   - **Severity: Workaround/quality.**

10. [`src/download/interactive_d4d_wrapper.py:280`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/download/interactive_d4d_wrapper.py:280>), [`src/download/d4d_agent_wrapper.py:117`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/download/d4d_agent_wrapper.py:117>), [`process_individual_d4d_gpt5.py:62`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/download/process_individual_d4d_gpt5.py:62>)

   - Hard-coded content limits: legacy individual paths truncate text at 10,000 or 50,000 characters; raw PDFs are represented only by their filenames in two wrappers.
   - Effect: facts late in long documentation and substantive PDF contents disappear. This is especially harmful outside the existing curated corpus, where document sizes/formats may differ substantially.
   - **Severity: Workaround/quality.**

11. [`src/download/d4d_agent_wrapper.py:136`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/download/d4d_agent_wrapper.py:136>)

   - Hard-coded skip values: every filename containing `_row2`, `_row3`, or `_row9` is skipped as a presumed duplicate.
   - Effect: any unrelated spreadsheet placing its only valid source on those rows silently loses it.
   - **Severity: Blocker for affected sources in this legacy path.**

12. [`src/download/process_individual_d4d_gpt5.py:239`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/download/process_individual_d4d_gpt5.py:239>) and [`interactive_d4d_wrapper.py:316`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/download/interactive_d4d_wrapper.py:316>)

   - Shape assumption: `_rowN` is stripped before grouping/output naming.
   - Effect: distinct sources with the same base name on different rows collapse to one output; later records are skipped because the output already exists.
   - **Severity: Workaround/quality.**

13. [`src/download/process_concatenated_d4d.py:275`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/download/process_concatenated_d4d.py:275>)

   - Hard-coded filename convention: directory mode discovers only `*_concatenated.txt` and removes `_concatenated` to derive the project.
   - Effect: the current preprocessing stage produces `*_preprocessed.txt`, so this legacy all-files path does not discover its own upstream output.
   - **Severity: Blocker for that legacy batch path.**

---

## 5. Prompt registry, canonical prompts, provenance, and reasoning capture

1. [`src/download/prompts/components/README.md:1`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/download/prompts/components/README.md:1>) and the five files under `components/`

   - Hard-coded values: tuned prompt components exist only for AI_READI, CHORUS, CM4AI, VOICE, and VOICE_PEDIATRIC, containing their exact releases, counts, cohorts, and referent decisions.
   - Effect: generic generation remains available, but tuned generation for another project needs a new component file and canonical pin. This is intentionally a GC-specific experimental condition.
   - **Severity: Workaround/quality; intentional study scope.**

2. [`src/data_sheets_schema/api_runner.py:327`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/data_sheets_schema/api_runner.py:327>) and [`cli/api.py:60`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/data_sheets_schema/cli/api.py:60>)

   - Hard-coded behavior: a tuned run always declares `components/<project>.md` as a required prompt file. Although prompt rendering treats a missing component as empty, the canonical-prompt gate rejects the missing/unpinned file.
   - Effect: an arbitrary project cannot use `--condition tuned` until a file is created and added to the canonical registry.
   - **Severity: Blocker for tuned external runs; generic runs work.**

3. [`src/download/prompts/canonical_hashes.yaml:1`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/download/prompts/canonical_hashes.yaml:1>) and [`api_runner.py:51`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/data_sheets_schema/api_runner.py:51>)

   - Hard-coded values: canonical hashes pin the five GC components; prompt conditions and version-to-file mappings are enumerated in Python as `generic`, versions 2–5, and `tuned`.
   - Effect: new dataset components require registry updates, while a new prompt condition requires code edits rather than configuration alone.
   - **Severity: Workaround/quality.**

4. [`src/data_sheets_schema/cli/api.py:13`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/data_sheets_schema/cli/api.py:13>) and [`api_runner.py:220`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/data_sheets_schema/api_runner.py:220>)

   - Hard-coded value: baseline and de-novo runs always declare `data/preprocessed/source_manifest.yaml` in their resolved instructions.
   - Effect: an external explicit bundle is described as if it came from the Bridge2AI manifest. There is no `--manifest` option to replace or disable it for an external baseline.
   - **Severity: Workaround/quality, with incorrect provenance.**

5. [`src/data_sheets_schema/provenance.py:41`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/data_sheets_schema/provenance.py:41>) and [`:1086`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/data_sheets_schema/provenance.py:1086>), `build_record()`

   - Hard-coded value: `SOURCE_MANIFEST` is global and `build_record()` accepts no manifest argument. Whenever `input_verified=True`, it records the Bridge2AI manifest’s path and MD5.
   - Effect: live provenance for an external bundle falsely attests that the Bridge2AI manifest was an input. Even crate/Healthsheet arms whose headers say “manifest not used” still enter this global provenance branch.
   - **Severity: Workaround/quality; serious provenance defect for non-B2AI use.**

6. [`src/data_sheets_schema/api_runner.py:589`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/data_sheets_schema/api_runner.py:589>), `source_ranking_block()`

   - Hard-coded behavior: source ranking is read from the fixed repository manifest, not from the bundle or a `RunSpec` manifest.
   - Effect: external projects receive no ranking block even if their own manifest declares one; conflict resolution quality differs from the Bridge2AI path.
   - **Severity: Workaround/quality.**

7. [`src/download/prompts/shared/d4d_system_prompt.txt:20`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/download/prompts/shared/d4d_system_prompt.txt:20>) and [`shared/d4d_user_prompt_url_mode.txt:17`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/download/prompts/shared/d4d_user_prompt_url_mode.txt:17>)

   - Domain/shape assumptions: the checklist emphasizes train/test/validation splits, grants, IRB, informed consent, privacy, and vulnerable populations; multiple URLs are assumed to describe the same dataset.
   - Effect: non-ML or non-human domains receive irrelevant emphasis, while URLs representing several related datasets/releases can be incorrectly merged.
   - **Severity: Workaround/quality.**

8. [`src/download/prompts/d4d_generic_arm_prompt_v5.md:243`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/download/prompts/d4d_generic_arm_prompt_v5.md:243>)

   - Hard-coded style: all generated prose must use American English.
   - Effect: no structural failure, but it is inappropriate for localized or source-faithful documentation outside the current study.
   - **Severity: Cosmetic.**

9. [`src/data_sheets_schema/reasoning.py:201`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/data_sheets_schema/reasoning.py:201>)

   - Runtime assumption: reasoning capture has special treatment for `Claude Code`; the effort vocabulary exposed by the CLI is fixed to `minimal|low|medium|high`.
   - Effect: this is not dataset-specific and does not block an external dataset, but another runtime/provider may require manual provenance notes or lose provider-specific reasoning metadata.
   - **Severity: Workaround/quality.**

---

## 6. Evaluation — presence-based and LLM rubric-based

1. [`src/data_sheets_schema/cli/evaluate.py:92`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/data_sheets_schema/cli/evaluate.py:92>) and [`:129`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/data_sheets_schema/cli/evaluate.py:129>)

   - Hard-coded values: presence and LLM commands restrict projects to `PROJECTS`; methods are restricted to `METHODS`.
   - Effect: a non-B2AI dataset or a new generation method label cannot be evaluated through the supported CLI.
   - **Severity: Blocker.**

2. [`src/evaluation/evaluate_d4d.py:907`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/evaluation/evaluate_d4d.py:907>), `main()`

   - Hard-coded defaults: projects default to `PROJECTS`; methods default to `curated`, `gpt5`, and `claudecode`.
   - Effect: direct script use can pass an arbitrary `--project`, but unqualified evaluation ignores external projects and current agent/API methods unless explicitly supplied.
   - **Severity: Workaround/quality.**

3. [`src/evaluation/evaluate_d4d.py:204`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/evaluation/evaluate_d4d.py:204>), `_load_d4d_yaml()`

   - Shape assumption: a `DatasetCollection` is unwrapped by evaluating only `resources[0]`.
   - Effect: multi-dataset collections lose every resource except the first from scoring and validation.
   - **Severity: Workaround/quality.**

4. [`src/evaluation/evaluate_d4d.py:631`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/evaluation/evaluate_d4d.py:631>), `generate_summary_report()`

   - Hard-coded values: comparison tables have only `Curated`, `GPT-5`, and `Claude Code`, even though discovery supports newer arms.
   - Effect: external/custom methods can be evaluated but are omitted from the primary comparison table.
   - **Severity: Workaround/quality.**

5. [`src/evaluation/evaluate_d4d_llm.py:378`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/evaluation/evaluate_d4d_llm.py:378>)

   - Hard-coded value: `--project` accepts only the original four GCs, excluding both external projects and `VOICE_PEDIATRIC`.
   - Effect: single-file LLM evaluation cannot be invoked for any other project.
   - **Severity: Blocker.**

6. [`src/evaluation/evaluate_d4d_llm.py:416`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/evaluation/evaluate_d4d_llm.py:416>)

   - Hard-coded discovery: `--all` scans five legacy method directories and only flat `*_d4d.yaml` files.
   - Effect: run-labelled current API/agent outputs and new arms are not discovered recursively.
   - **Severity: Blocker for current run-labelled batch evaluation; workaround with one-file invocation for allowed projects.**

7. [`src/evaluation/evaluate_d4d_llm.py:261`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/evaluation/evaluate_d4d_llm.py:261>), `export_to_csv()` and `export_to_markdown()`

   - Hard-coded naming assumption: result keys are split on the first underscore to recover project and method.
   - Effect: `AI_READI` is parsed as project `AI` and method `READI_...`; any arbitrary project containing underscores is similarly misattributed.
   - **Severity: Workaround/quality.**

8. [`data/rubric/rubric20.txt:191`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/data/rubric/rubric20.txt:191>), [`:265`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/data/rubric/rubric20.txt:265>), [`:287`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/data/rubric/rubric20.txt:287>), [`:311`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/data/rubric/rubric20.txt:311>), [`:397`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/data/rubric/rubric20.txt:397>)

   - Hard-coded content: Bridge2AI-Voice disease coverage, Bridge2AI multimodality, PHI examples, AI-READI/CM4AI/CHORUS license rules, Bridge2AI AI-readiness, mandatory Bridge2AI citation behavior, and named `applies_to` lists.
   - Effect: the rubric is not domain-neutral. It rewards biomedical/AI-readiness metadata and can penalize datasets where human-subject, clinical-access, multimodality, grant, or AI-readiness concepts are irrelevant.
   - **Severity: Workaround/quality.**

9. [`src/evaluation/evaluate_d4d.py:312`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/evaluation/evaluate_d4d.py:312>) and [`:454`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/evaluation/evaluate_d4d.py:454>)

   - Hard-coded scoring assumption: presence-based evaluation scores every rubric field and never reads `applies_to`.
   - Effect: non-human datasets receive zeros for ethics/human representation rather than N/A, and an arbitrary project name cannot match the rubric’s named applicability lists anyway.
   - **Severity: Workaround/quality; materially biases cross-domain scores.**

10. [`data/rubric/rubric10.txt:178`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/data/rubric/rubric10.txt:178>) and [`:214`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/data/rubric/rubric10.txt:214>)

    - Domain assumption: regulatory/HIPAA and IRB/data-protection fields are fixed sub-elements in the 50-point score.
    - Effect: the deterministic evaluator lacks N/A handling, so non-human or non-regulated datasets have a lower attainable meaningful score.
    - **Severity: Workaround/quality.**

11. [`src/download/prompts/rubric10_system_prompt.md:30`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/download/prompts/rubric10_system_prompt.md:30>) and [`rubric20_system_prompt.md:30`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/download/prompts/rubric20_system_prompt.md:30>)

    - Hard-coded examples: quality is illustrated almost entirely with specialty clinics, patients, IRB protocols, and clinical recruitment.
    - Effect: LLM-as-judge calibration is biased toward richly documented clinical studies even when evaluating unrelated domains.
    - **Severity: Workaround/quality.**

12. [`src/evaluation/batch_evaluate_concatenated.sh:99`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/evaluation/batch_evaluate_concatenated.sh:99>) and [`batch_evaluate_individual.sh:117`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/evaluation/batch_evaluate_individual.sh:117>)

    - Hard-coded values: original four projects and fixed legacy method arrays.
    - Effect: external projects, pediatric, current run labels, and newer arms are excluded from batch evaluation regardless of files on disk.
    - **Severity: Blocker.**

13. [`scripts/evaluate_all_d4ds_rubric10.py:24`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/scripts/evaluate_all_d4ds_rubric10.py:24>), [`scripts/summarize_rubric10_results.py:130`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/scripts/summarize_rubric10_results.py:130>), [`scripts/summarize_rubric20_results.py:142`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/scripts/summarize_rubric20_results.py:142>)

    - Hard-coded values: four projects and fixed generation methods in inventory and summaries.
    - Effect: arbitrary projects never enter the generated inventory, evaluation plan, or summary tables.
    - **Severity: Blocker for these batch/reporting paths.**

14. [`scripts/batch_evaluate_rubric10_hybrid.py:400`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/scripts/batch_evaluate_rubric10_hybrid.py:400>) and [`batch_evaluate_rubric20_hybrid.py:873`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/scripts/batch_evaluate_rubric20_hybrid.py:873>)

    - Hard-coded parser: underscore-containing names are special-cased only for `AI_READI`; all other keys assume the first underscore separates project and method.
    - Effect: an arbitrary project such as `MY_PROJECT` is reported as project `MY` with a corrupted method name.
    - **Severity: Workaround/quality.**

15. [`src/data_sheets_schema/schema/D4D_Evaluation_Summary.yaml:190`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/data_sheets_schema/schema/D4D_Evaluation_Summary.yaml:190>) and [`:491`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/data_sheets_schema/schema/D4D_Evaluation_Summary.yaml:491>)

    - Hard-coded schema: evaluation summaries require `Bridge2AIProjectEnum`, containing only the original four projects, and `GenerationMethodEnum` contains five legacy methods.
    - Effect: any evaluation artifact validated against this ancillary schema cannot represent an external project, pediatric, or newer arm.
    - **Severity: Blocker for consumers of this evaluation-summary schema; it does not appear to drive the current CSV/Markdown evaluator.**

16. [`src/data_sheets_schema/agreement.py:548`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/data_sheets_schema/agreement.py:548>)

    - Hard-coded default: agreement analysis uses exactly the original four projects.
    - Effect: external projects are excluded unless passed explicitly. Comments document that this is deliberate to preserve the published four-GC analysis and avoid double-counting the shared VOICE corpus.
    - **Severity: Workaround/quality; intentional study-analysis scope.**

---

## 7. `d4d` CLI and constants

1. [`src/data_sheets_schema/constants/projects.py:8`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/data_sheets_schema/constants/projects.py:8>)

   - Hard-coded values: `PROJECTS` contains the five known datasets; `SHARED_CORPUS_GROUPS` contains only the adult/pediatric VOICE pair.
   - Effect: every `click.Choice(PROJECTS)`, default loop, status display, and project-dependent analysis requires a code edit for a new project. Another pair of datasets sharing a corpus cannot declare that relationship through configuration.
   - **Severity: Blocker for config-only onboarding.**

2. [`src/data_sheets_schema/constants/methods.py:7`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/data_sheets_schema/constants/methods.py:7>)

   - Hard-coded values: operational methods include legacy Bridge2AI study arms, including AI-READI Healthsheet and crate variants.
   - Effect: a new generation backend/method is rejected by evaluation CLI choices until this module is edited. Existing generic methods still work for an external dataset.
   - **Severity: Workaround/quality.**

3. [`src/data_sheets_schema/cli/utils.py:80`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/data_sheets_schema/cli/utils.py:80>)

   - Hard-coded behavior: detailed status iterates only `PROJECTS` and `METHODS`.
   - Effect: external project directories and custom method directories are invisible in detailed pipeline status.
   - **Severity: Workaround/quality.**

4. [`src/data_sheets_schema/cli/runs.py:334`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/data_sheets_schema/cli/runs.py:334>) and [`:1332`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/data_sheets_schema/cli/runs.py:1332>)

   - Hard-coded behavior: canonical “missing” and label-based redundancy defaults compare against `PROJECTS`.
   - Effect: an external project is not reported as missing/canonical by default and is omitted from label-wide analyses unless named manually.
   - **Severity: Workaround/quality.**

5. [`src/data_sheets_schema/constants/schemas.py:33`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/data_sheets_schema/constants/schemas.py:33>)

   - Domain assumption: the full D4D module set always includes Human, Ethics, Data Governance, and biomedical-oriented modules.
   - Effect: these fields are generally optional, so validation itself remains possible, but prompt/schema inspection always exposes a clinical-heavy vocabulary to the generator.
   - **Severity: Workaround/quality, not a structural blocker.**

---

## 8. Schema-level domain assumptions

1. [`src/data_sheets_schema/schema/D4D_Composition.yaml:45`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/data_sheets_schema/schema/D4D_Composition.yaml:45>)

   - Hard-coded vocabulary: `data_topic` and `data_substrate` use `B2AI_TOPIC` and `B2AI_SUBSTRATE`; descriptions tell generators to omit the field when no Bridge2AI registry term fits.
   - Effect: arbitrary-domain concepts can be lost rather than represented using an external domain vocabulary or prose fallback.
   - **Severity: Workaround/quality.**

2. [`src/data_sheets_schema/schema/D4D_Data_Governance.yaml:61`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/data_sheets_schema/schema/D4D_Data_Governance.yaml:61>) and [`:314`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/data_sheets_schema/schema/D4D_Data_Governance.yaml:314>)

   - Domain assumption: data-use permissions are modeled primarily through GA4GH DUO categories such as health/medical research, disease-specific research, clinical care, genetic studies, and IRB approval.
   - Effect: legal/governance regimes in non-biomedical domains may not fit the structured enum and must fall back to free text or omit structured permission data.
   - **Severity: Workaround/quality.**

3. [`src/data_sheets_schema/schema/data_sheets_schema.yaml:226`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/data_sheets_schema/schema/data_sheets_schema.yaml:226>), [`:423`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/data_sheets_schema/schema/data_sheets_schema.yaml:423>)

   - Domain assumptions: dataset structure is described in ML terms such as train/validation/test splits, while a large top-level section models IRB review, informed consent, at-risk populations, participant privacy, and compensation.
   - Effect: these fields are optional and therefore do not prevent validation, but they contribute to clinical/ML prompt and rubric bias.
   - **Severity: Workaround/quality.**

4. [`src/data_sheets_schema/schema/D4D_Composition.yaml:377`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/data_sheets_schema/schema/D4D_Composition.yaml:377>) and [`D4D_Data_Governance.yaml:105`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/data_sheets_schema/schema/D4D_Data_Governance.yaml:105>)

   - Hard-coded examples/fields: patient data, clinical images, HIPAA Safe Harbor, PHI, IRB, and US health regulations dominate confidentiality/deidentification examples.
   - Effect: mostly calibration bias rather than schema failure; generic legal privilege, GDPR, and other compliance text is also allowed.
   - **Severity: Cosmetic to Workaround/quality, depending on whether generators copy the framing.**

5. Schema identifiers throughout, e.g. [`D4D_Core.yaml:2`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/data_sheets_schema/schema/D4D_Core.yaml:2>)

   - Hard-coded namespace: schema identifiers and prefixes use `w3id.org/bridge2ai`.
   - Effect: external datasets can still instantiate the schema; this identifies the schema publisher rather than restricting dataset identity.
   - **Severity: Cosmetic.**

---

## 9. Makefile and configuration files

1. [`project.Makefile:21`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/project.Makefile:21>)

   - Hard-coded value: `PROJECTS = AI_READI CHORUS CM4AI VOICE`, inconsistent with the Python constants because it omits `VOICE_PEDIATRIC`.
   - Effect: all Make “all projects” targets ignore pediatric and arbitrary manifest projects.
   - **Severity: Blocker for Make-driven config-only onboarding.**

2. [`project.Makefile:24`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/project.Makefile:24>)

   - Hard-coded value: Bridge2AI sheet ID/URL and expected GC columns.
   - Effect: `download-sources` always uses that corpus. `download-sheet SHEET_URL=...` allows another sheet, but still uses the fixed source manifest and project assumptions.
   - **Severity: Workaround/quality.**

3. [`project.Makefile:80`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/project.Makefile:80>) and [`:643`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/project.Makefile:643>)

   - Hard-coded loops: preprocessing, validation, and concatenation use the fixed Make `PROJECTS`; concatenation assumes `individual/<project>` and does not honor the CLI’s source-directory override.
   - Effect: a new manifest entry alone is never processed, and shared-corpus projects cannot rebuild through `make concat-preprocessed`.
   - **Severity: Blocker.**

4. [`project.Makefile:737`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/project.Makefile:737>), [`:805`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/project.Makefile:805>), [`:994`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/project.Makefile:994>)

   - Hard-coded loops: individual, concatenated, agent, and assistant “all” targets iterate only the four Make projects.
   - Effect: arbitrary projects are never generated in batch without editing the Makefile.
   - **Severity: Blocker.**

5. [`project.Makefile:793`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/project.Makefile:793>) and [`:850`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/project.Makefile:850>)

   - Hard-coded obsolete convention: legacy GPT-5/Claude targets expect `<PROJECT>_concatenated.txt`, while `concat-preprocessed` writes `<PROJECT>_preprocessed.txt`.
   - Effect: those extraction targets cannot consume the immediately preceding pipeline output for any project without renaming or target edits.
   - **Severity: Blocker for these legacy Make extraction paths.**

6. [`project.Makefile:1208`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/project.Makefile:1208>), [`:1351`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/project.Makefile:1351>), [`:1440`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/project.Makefile:1440>)

   - Hard-coded values: evaluation targets specify the four original projects and fixed legacy methods.
   - Effect: arbitrary projects, pediatric, and newer API/experimental arms are excluded from standard Make evaluation and summaries.
   - **Severity: Blocker.**

7. [`data/ro-crate_packages/crate_manifest.yaml:25`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/data/ro-crate_packages/crate_manifest.yaml:25>)

   - Hard-coded values: exact package URLs, checksums, layouts, encodings, and reduction rules for the four Bridge2AI crates.
   - Effect: appropriate as experiment configuration, but there is no generic crate-manifest schema/onboarding route exposed independently of `PROJECTS`.
   - **Severity: Workaround/quality; intentional study configuration.**

8. [`about.yaml:1`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/about.yaml:1>)

   - Hard-coded value: a fixed Google Sheet ID/tab set exists here, but it configures LinkML schema generation (`personinfo enums`), not the D4D source corpus.
   - Effect: it does not block arbitrary D4D datasets; the placeholder author and fixed schema-build sheet are repository-template concerns.
   - **Severity: Cosmetic / outside the D4D data pipeline.**

9. [`config.env`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/config.env>)

   - Finding: the file is empty; no dataset-specific value was found.
   - **Severity: No blocker.**

10. [` .github/workflows/d4d-agent.yml:200`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.github/workflows/d4d-agent.yml:200>)

    - Generalized exception: the GitHub assistant discovers any directory under `data/sheets_d4dassistant/inputs/` and calls `d4d api run` with an explicit bundle.
    - Remaining constraint: onboarding still requires placing a TXT/Markdown bundle in that repository path; it bypasses rather than generalizes the download/preprocessing/evaluation stages.
    - **Severity: Workaround/quality.**

---

## 10. Documentation and examples

1. [`CLAUDE.md:48`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/CLAUDE.md:48>) and [`README.md:16`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/README.md:16>)

   - Hard-coded content: workflows and examples consistently use the four Bridge2AI projects; `CLAUDE.md:82` explicitly calls project validation by `click.Choice` a benefit.
   - Effect: reinforces the current closed-project design but does not independently block execution.
   - **Severity: Cosmetic.**

2. Prompt output-format examples such as [`rubric10_output_format.json:33`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/download/prompts/rubric10_output_format.json:33>) and [`rubric20_output_format.json:30`](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/download/prompts/rubric20_output_format.json:30>)

   - Hard-coded examples: Bridge2AI-Voice, PhysioNet, HIPAA, IRB, and NIH grant values.
   - Effect: examples may anchor LLM judgments toward clinical content, but they are not executable project restrictions.
   - **Severity: Cosmetic to Workaround/quality.**

---

## Quick wins

The smallest coherent change set for zero-code onboarding via a manifest would be:

1. Make the manifest the project registry.

   - Replace `PROJECTS`-based defaults and all `click.Choice(PROJECTS)` dataset arguments with free strings validated against the selected manifest.
   - Move source-directory overrides into each project record, e.g. `projects.X.source_dir` and `projects.X.sources`, so metadata keys are never mistaken for project source lists.
   - Derive Make batches from `d4d ... list-projects --manifest ...` or replace the duplicated Make loops with CLI batch commands.

2. Thread `--manifest` through generation and provenance.

   - Add `manifest: Path | None` to `RunSpec` and `build_record()`.
   - Use it for source ranking, resolved prompt headers, provenance hashing, scope checks, and bundle discovery.
   - Record “not used” rather than the Bridge2AI manifest for explicit external bundles that have no manifest.

3. Add batch bundle configuration.

   - Let API batch accept a manifest mapping project → bundle, or repeatable `--project-bundle NAME=PATH`.
   - Make tuned components optional/empty by declaration, while still requiring canonical hashes when a component actually exists.

4. Generalize source ingestion.

   - Make spreadsheet download one optional adapter rather than the primary project registry.
   - Resolve DOI targets, fetch substantive Health Data Nexus content, and provide pluggable handlers/converters.
   - Add CSV/TSV/XLSX/YAML/XML and OCR support, or permit manifest-declared preprocessing commands.

5. Make evaluation applicability explicit.

   - Replace named `applies_to` project lists with predicates such as `human_subjects`, `shared_dataset`, `regulated_access`, and `ml_training_dataset`.
   - Implement N/A in both deterministic and LLM scoring and remove N/A questions from the denominator.
   - Discover projects/methods recursively from records or the supplied manifest; stop parsing identity from underscore-delimited filenames.

6. Separate study-only arms and reports.

   - Keep Healthsheet-only, Bridge2AI crate comparisons, published four-GC agreement defaults, and GC-specific tuned components in a study configuration.
   - Keep the reusable baseline pipeline, generic prompts, provenance, and evaluation free of those project lists.
