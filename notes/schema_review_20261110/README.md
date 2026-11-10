# Current D4D schema: history, AI-readiness and semantic exchange review

Reviewed November 10, 2026 against remote main **`7233f193ad102a8488b31ec7333662c8fefaa996`**, schema **3.2.0**. The comparison treats the requested April/May meeting as the 2026 Bridge2AI meeting period. The exact poster shown and a participant's browser view are not independently established.

**The schema retains its overall scientific scope and has improved governance and standards representation. It has also changed accepted record shapes substantially. It broadly supports the AI-readiness framework, but full alignment is not demonstrated. The semantic exchange layer remains maintained, yet current source and a small validated fixture expose defects that rule out an unqualified claim of complete or lossless RO-Crate exchange.**

This is a review and evidence package. It changes no production schema, mapping, converter, historical datasheet or publication content. Five new findings were filed; existing findings were associated with their open issues. Fixes below are proposed work, not completed implementation.

## What changed since the meeting period

There are three different baselines, and treating them as one would give the wrong comparison:

- **April 10 generation:** four full and four separate Core records at `9912ac2379b1a5b747c6b3941a32a18968dbd07d`.
- **Poster-era schema:** April 28 checkpoint `e141852f532e6a0cea47992ffe9afc0f20a7c6a5`, following poster development beginning April 24. This is a reproducible schema checkpoint, not the exact presentation file.
- **Hosted publication table:** Synapse snapshot 13, created April 25 UTC / April 24 Pacific. Its four HTML rows **exactly match the December 2025 v4 files**, rather than April's regenerated records. Hash comparisons verify the table content. Browser caches and the downstream materialized view remain separate, unverified display layers. [Public snapshot history](https://repo-prod.prod.sagebase.org/repo/v1/entity/syn68885644/version?limit=100&offset=0).

The current publication documentation describes a later v8 cohort generated in September under schema 2.0.0. Rendering it again does not migrate its data to 3.2.0. Publication version, schema version and generation date must remain separate.

| Same-method comparison | April full | Current full | April Core | Current Core |
|---|---:|---:|---:|---:|
| Root fields including inheritance | 94 | 98 | 79 | 84 |
| Classes in imported closure | 78 | 79 | 76 | 77 |
| Enums in imported closure | 17 | 18 | 15 | 16 |
| Enum values | 210 | 242 | 191 | 223 |

Both April schema checkpoints have these same counts. Imported definitions are not all necessarily reachable through the root record. Poster counts used different or undocumented denominators, so they cannot be directly substituted into this table.

No existing class or root field was removed from the compared closures. The new class is `DataGovernance`. Full adds `data_governance`, `conforms_to_standard`, `notes` and `source_caveats`; Core adds these plus `related_datasets`. The principal compatibility changes are:

1. **64 attributes changed from lists to single values:** 63 narrative strings and `FileCollection.collection_type`. Existing arrays may therefore fail current validation.
2. **Person relationships now inline Person objects**, including principal investigators and governance contacts. Bare name strings are not equivalent records.
3. **Organization/Grant identifiers were relaxed**, while DOI validation was tightened. File collections and distribution metadata received more explicit structures.
4. **Governance, data standards and evidence caveats became more expressive.** Serialization format is distinguished from standards such as BIDS, DICOM and OMOP.
5. **Release 3.2 restores list-valued data-use permissions**, allowing DUO modifiers alongside a primary permission. It matches April's list cardinality, but scalar values from intervening 3.0/3.1 records need migration.

Most breaking representation changes began under the 2.0.0 label; 3.0 later established a new release identity. Version strings alone are therefore insufficient historical identifiers. Core generation also changed: April generated it independently; the later workflow derives it from the audited full record. Preserve original historical bytes and create explicitly identified migration derivatives.

Detailed changes, commit chronology, poster evidence, publication hashes and counting definitions: [history.md](history.md).

## Alignment with the AI-readiness preprint

The cited PMID currently presents **version 6, April 24, 2026**, with **28 criteria across seven dimensions**. It frames readiness as context-dependent rather than a universal yes/no certificate. [Current preprint and Table 1](https://pmc.ncbi.nlm.nih.gov/articles/PMC11526931/#T1).

The full schema has relevant representation across the framework, and governance is stronger than the old repository mapping suggests. The main limits are:

- **Full and Core are not equivalent evidence containers.** Core lacks the full record's variable dictionary, splits/subsets and ParticipantPrivacy relationship. Importing the corresponding class definitions does not make those fields reachable from CoreDataset.
- **Several areas remain indirect or incomplete:** execution-level transformation provenance, empirical statistical summaries, general QC results, repository suitability and computational environment requirements. Prose and external links can carry evidence, but do not provide uniform typed assessment results.
- **Evidence is optional and its truth is not established by schema validity.** Both current full and Core accept an ID-only record. Empty records fail because an identifier is required. These bounded checks confirm the distinction without implying that permissive metadata schemas are themselves defective.
- **The old coverage percentage is unreliable.** The December 2025 crosswalk reports 22/26 full plus 4/26 partial, while its own table contains 28 rows and six partial rows. It also uses stale or nonexistent field paths. It cannot establish an earlier state of full alignment.

The correct next step is a criterion-aware assessment profile that records applicability, evidence, status, rationale and assessed release. Decide whether Core must carry that evidence itself or link a full evidence package. Avoid making sparse legacy metadata invalid merely to enforce a separate readiness assessment.

The complete current full/Core matrix, exact schema anchors and limitations are in [ai_readiness.md](ai_readiness.md). The report distinguishes fields that can represent a claim from evidence sufficient to support it and operations needed to verify it.

## Semantic exchange and RO-Crate

The canonical exchange artifacts are actively maintained: **301 comprehensive mapping rows**, **165 structural rows**, and **150 SKOS mapping triples**. Of the comprehensive rows, 176 are marked mapped, 84 unmapped, 27 novel D4D, 13 free text and one recommended. These are slot-name counts, not percentages of runtime preservation. Broad/close matches and local URIs do not establish exact semantic equivalence.

Important current problems are independently visible:

- Full `Dataset` is annotated as `dcat:Distribution` / `schema:DataDownload`, while Core uses dataset types. Core also retains several RAI annotations that the canonical TTL already withdrew as nonexistent terms.
- Canonical TTL disagreements remain around identity, hashes and conformance. In a real export, `conformsTo` expands to the wrong Schema.org predicate rather than Dublin Core.
- A **Core-valid tiny fixture** exports the structured creator as `Unknown`, loses source identity, and emits no `datePublished`, despite passing the actual pinned FAIRSCAPE model validation. RO-Crate 1.2 requires the publication date. [RO-Crate 1.2 root requirements](https://www.researchobject.org/ro-crate/specification/1.2/root-data-entity.html#direct-properties-of-the-root-data-entity).
- The same invocation ignores Core distributions/BIDS. This proves that it cannot substantiate lossless Core export; support for Core input in this generic converter has not been established, so this is not labelled a regression of a supported Core-specific route.
- Unified round-trip and SHACL checks are unfinished but can return a successful Boolean. Separate FAIRSCAPE forward and reverse implementations exist; the missing result is a demonstrated, explicitly scoped preservation contract.

Some converter omissions are intentional and accurately reported under a finite 15-field projection contract. That work should be retained. The correction is to identify each route's supported classes, target version and declared losses, then test those guarantees. SSSOM alignment, Pydantic validity, RO-Crate conformance and round-trip preservation are distinct checks.

Detailed source links, measured mapping census, serialized canary output and acceptance steps: [semantic_exchange.md](semantic_exchange.md).

## Findings and proposed implementation order

| Priority | Finding | Tracking |
|---|---|---|
| P2 | Invalid AI-readiness denominator and stale crosswalk paths | New [#5786](https://github.com/bridge2ai/data-sheets-schema/issues/5786) |
| P2 | Unsupported universal Core alignment/lossless claims and unclear Core input boundary | New [#5787](https://github.com/bridge2ai/data-sheets-schema/issues/5787); related #160/#136 |
| P2 | Forward exporter ignores nested Creator Person | New [#5788](https://github.com/bridge2ai/data-sheets-schema/issues/5788) |
| P2 | Model-valid export can omit required RO-Crate date | New [#5789](https://github.com/bridge2ai/data-sheets-schema/issues/5789) |
| P2 | Unimplemented round-trip/SHACL checks return success-shaped reports | New [#5790](https://github.com/bridge2ai/data-sheets-schema/issues/5790) |
| P2 | Full Dataset has distribution/download semantic type | Existing [#4034](https://github.com/bridge2ai/data-sheets-schema/issues/4034) |
| P2 | Core retains nonexistent RAI targets | Existing [#3972](https://github.com/bridge2ai/data-sheets-schema/issues/3972) |
| P2 | Wrong conformance predicate, including observed runtime context | Existing [#3025](https://github.com/bridge2ai/data-sheets-schema/issues/3025) |
| P2 | Source identity loss and undeclared RAI export properties | Existing [#4044](https://github.com/bridge2ai/data-sheets-schema/issues/4044) |
| P2 | Open TTL/schema disagreements on identity, creators, URLs and hashes | Existing [#2973](https://github.com/bridge2ai/data-sheets-schema/issues/2973) |
| P3 | Scalar collection type still described as allowing multiple types | Existing [#2975](https://github.com/bridge2ai/data-sheets-schema/issues/2975) |

Priorities are review judgments, not claims that downstream consumers have already suffered every possible consequence. Existing issues are reused rather than duplicated. Readiness assessment and remaining representational gaps belong with [#44](https://github.com/bridge2ai/data-sheets-schema/issues/44) / [#23](https://github.com/bridge2ai/data-sheets-schema/issues/23); round-trip/conformance acceptance belongs with [#160](https://github.com/bridge2ai/data-sheets-schema/issues/160) / [#136](https://github.com/bridge2ai/data-sheets-schema/issues/136).

Recommended bounded work:

1. Correct assurance documentation and make unavailable validation outcomes explicit. This prevents incomplete checks from being interpreted as proof.
2. Define one supported exchange route, then fix its context, required-root handling, creator and identity preservation. Support Core distributions explicitly or refuse that input contract clearly.
3. Resolve the existing ontology/type disagreements with curator decisions, release changes where required and regenerated canonical mappings.
4. Add a small criterion-aware readiness profile and declare the full/Core evidence boundary. Extend schema structures only where linked external evidence is insufficient.
5. Validate one representative full/Core pair end to end, including a variable, split, privacy statement, provenance link, creator, standard and checksum. Add negative cases and inverse-preservation checks before broad generation or publication.

These steps can use tiny synthetic records. A new expensive D4D generation run is not needed to reproduce the present metadata and exchange defects.

## What was actually checked

Three frozen schema inventories used the same installed toolchain, serially, after the current-snapshot canary. Public snapshot content was read anonymously and compared to Git bytes. The exchange helper's import/census/conversion diagnostic took about **0.668 seconds**; this is not conversion-only timing. Subsequent Core/full schema-validation probes took **1.307 / 1.390 seconds** and each rejected the missing-ID control. No model calls, large test cohorts, production edits, historical-corpus validation batch or full conformance certification ran.

The three component reviews received separate read-only scrutiny before report corrections. Artifacts include raw-value hashes, revision identities, schemas/tool versions, canary input/output and the original-byte comparisons. Publication copies redact email-address strings; local raw evidence is preserved separately. Reproduction helpers are committed with the reports:

- [Historical inventory and publication capture](../../scripts/adhoc/schema_history_review_20261110.py)
- [Static exchange census and forward canary](../../scripts/adhoc/schema_exchange_review_20261110.py)
- [Schema validation controls](../../scripts/adhoc/schema_review_validation_20261110.py)

Exact poster bytes, historical browser rendering, a live bidirectional exchange and release-specific AI-readiness assessments remain unverified. Those limits do not affect the demonstrated current schema deltas or the recorded source/fixture defects.
