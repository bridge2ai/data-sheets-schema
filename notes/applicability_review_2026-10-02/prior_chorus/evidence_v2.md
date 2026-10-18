# CHORUS evaluation applicability — corrected v2 evidence note, 2026-09-19

**Corrected v2 candidate — pending final exact-byte independent review.** This proposes context for future evaluations of the same independently accepted full/core pair. It is not an evaluation registration, acceptance, score, condition or launch. Audit5 is still separate and active; this directory is not among its readable inputs or output paths. No generated D4D, model reasoning, held-out judgment queue or audit verdict was used as a factual source.

## Correction APPLICABILITY-1

The original `CHORUS_applicability_draft.yaml`, `evidence.md` and `validation.json` remain unchanged. The independent finding is preserved in `independent_review.md` and `independent_review.json`. The first draft omitted explicit OHNLP use at bundle c003 lines 308–310 and imposed an unnecessarily strict exact-release prerequisite on the dataset-level applicability predicate. Its statement that software use was not established is superseded by this candidate, not silently erased.

The webinar explicitly attributes clinical-note extraction and tokenization to the OHNLP toolkit (c003, physical lines 308–310), alongside the dataset context that notes remain local except tokens (lines 245–247). That is direct evidence of software transforming CHORUS data; software applicability is true. Version, uniform use across sites/modalities and particular-release output inclusion remain unestablished. The flattened table's “Planned” at line 324 is not assigned to a column by guess; the draft does not claim completed token distribution from that entry.

Only `processing_software.value` and its evidence changed in the normalized context; the other six declarations are identical. All seven predicates are now true. The changed status is `unknown` → `applicable`, with no proposed exclusion/denominator change because unknown remained applicable. No D4D score was calculated or changed. The independent review resolved all source-rubric applicability rules without computing scores and found the same included items. The normalized context identity nevertheless changes and must be pinned explicitly if this v2 candidate is later approved.

## Proposed declarations

| Predicate | Draft value | Source evidence and scope |
|---|---|---|
| `human_subjects` | true | Project documentation c006, lines 1074–1082, describes patient admissions and clinical data; webinar c003, lines 236–247, describes retrospective hospital admissions. Human-origin data make participant/privacy documentation applicable. This is not a legal determination of human-subjects research status or an assertion of consent/IRB completion. |
| `regulated_access` | true | Webinar c003 line 240 explicitly identifies controlled access; c003–c004 lines 440–455 require a licensing agreement before access. An actual governance restriction is documented. No particular statutory regime or dataset license identifier is inferred. |
| `shared_dataset` | true | Webinar c003 lines 213–221 describes expanded research access, lines 256–258 states dataset use for activities/publications, and lines 440–455 provides access terms. Project site c006 lines 1074–1082 describes a current released dataset. Controlled sharing counts; open download is not required or asserted. |
| `ml_training_dataset` | true, limited to intended model-development use | NIH project abstract c002 lines 45–47 explicitly describes generating data for ML/AI applications and developing ML-derived models, with a separate intended holdout for external validation. This is intended use, not evidence of a released training subset or actual trained model. The webinar's educational “training activities” is not used as model-training evidence. |
| `data_collection` | true | Webinar c003 lines 236–247 explicitly says retrospective data collection; project site c006 lines 1083–1085 describes multimodal collection across hospitals. This does not assert completion of planned targets, all modalities or every site. |
| `data_processing` | true | Webinar c003 lines 245–254 describes OMOP, token handling and imaging de-identification in progress; project site c006 lines 1083–1085 describes ongoing/new standardization. Processing exists; uniformity and completion of each step remain unstated. |
| `processing_software` | true | Webinar c003 lines 308–310 explicitly names the OHNLP toolkit for extraction/tokenization of clinical notes; lines 245–247 supply CHORUS dataset/enclave context. This establishes a software transformation operation. Version, uniformity and particular-release membership remain unestablished; they do not negate dataset-level applicability. |

The source roles and dates matter. The NIH RePORTER text is project-purpose language associated with the 2022 award; its model-development and external-validation claims are plans. The webinar is dated 2025-09-09 (bundle line 74), and its dataset snapshot explicitly says August 2025 (line242). The project site's release snapshot is undated in this bundle. The GitHub organization overview is a historical 2025-11-14 capture (lines1118–1125). The draft does not assert that these are fresh 2026 observations, order undated counts chronologically, or infer completed operations from plans.

All seven predicates are true; none is false. No N/A exclusion is proposed. Current rubric10 E8.4 uses `processing_software`; the semantic definition distinguishes software that transforms data from generic repository availability (`.claude/agents/d4d-rubric10-semantic.md:495`). The explicit OHNLP attribution supplies the evidence missing from the first draft's reasoning. `ml_training_dataset` remains intended model-development use, not an identified released training partition or a completed model. It has no current rubric10/20 source-file `applies_to` assignment. The independent reviewer agrees with all seven declarations at this dataset-level scope; final review must still bind this candidate's exact bytes.

## Source and instrument identity

All citations use one-based inclusive **physical lines** in:
`/private/tmp/d4d-canaries-v10z/data/preprocessed/concatenated/CHORUS_preprocessed.txt`

Bundle SHA-256: `27625709112a7b7796f4e778fcc33df9f908ba95e47dbc0b6e23a535cacc237c` (1,698 lines, 35,920 bytes). Chunk manifest SHA-256: `ec9d81c54758d9db78ccc98a0a1de01643d224255f11f183cfebc2cfd793108a` at the same frozen tree's `data/preprocessed/chunks/CHORUS_chunks.yaml`. Chunk boundaries relevant here: c002 19–54; c003 55–454; c004 455–854; c006 1032–1112; c007 1113–1512; c008 1513–1698.

The bundle's own source metadata names NIH RePORTER project 10472824 (lines24–29), the AIM-AHEAD cohort 2 webinar (lines60–65), chorus4ai.org project documentation (lines1037–1042), and the chorus-ai GitHub historical overview (lines1118–1123). These are existing captured documents; no web fetch/download was made for this draft.

Audit5 registration SHA-256: `61e37130b7836ecb1f03c8647689852efefd478fa290916957b0b28516296d59`. Its explicit profile is `bridge2ai`, also selected by frozen source manifest line 4; source-manifest SHA-256 `13758a83de3a0d13b367bf21623fbcac611e599c81a9612143bb6987de89abe6`. The profile controls study vocabulary/instrument configuration; it is not evidence of any applicability predicate. No predicate was inferred from the CHORUS/Bridge2AI name.

Context implementation: `src/data_sheets_schema/evaluation_context.py`, SHA-256 `e27856877cac196034cad20ca5429906afb6d85fce28d5eaf10b24ab14d0878e`, context version `d4d-evaluation-context-1`, from merged commit `2c342124d099a761c8edd3b330cde4c3c4cf0386`. It permits exactly the seven predicate names, each a boolean/null or value/evidence mapping. Missing predicates and explicit null remain unknown and applicable. There is no separate class key in this YAML contract.

## Full/core use and review gate

Use the **same reviewed context file/hash** for the future accepted `Dataset` full record and `CoreDataset` core record, since these describe the same underlying dataset. Their classes, exact input hashes and complete class schemas belong in their separately registered evaluation jobs. Do not add `class_name`, `profile`, `status` or a `Dataset` wrapper as extra applicability YAML keys; the strict normalizer rejects them. Draft status is in comments and this note.

This does not certify the actual future records' class identities or composition. The preparer must verify them after final-pair acceptance. An explicit Dataset/CoreDataset retains its component resources within that dataset; a declared collection follows the existing every-member/minimum-per-item policy. Do not infer collection scope from this context or score an arbitrary first resource. If the accepted evaluation target changes to a distinct subset with different predicates, review and register a new context instead of silently reusing this draft.

Independent review must check the predicate meanings, source/date/scope support and the intended-use qualification on `ml_training_dataset`. If the reviewer requires that predicate to mean an identified released training partition, it should remain null until such a partition is evidenced; do not invent one. The OHNLP evidence supports software applicability without requiring exact release attribution; unspecified version, uniformity and output membership remain qualifications, not false/N/A gates. Do not revise context after seeing favorable/unfavorable scores without declaring an instrument change. Once approved, pin the exact context bytes and normalized digest in the future schema-v2 evaluation registration. The old draft and evidence note should remain preserved.

## Cheap offline validation

The following exact read-only context-contract command can be rerun from the reviewed checkout. It parses this draft, checks duplicate keys, rejects unknown predicate names/types and computes its normalized identity. It does not load a generated record, score, open a ledger or contact a provider.

```bash
cd /private/tmp/d4d-audit-budget-exception
PYTHONPATH=src /Users/marcin/Library/Caches/pypoetry/virtualenvs/data-sheets-schema-KeX3bMFJ-py3.13/bin/python -B - <<'PYTHON'
from pathlib import Path
from data_sheets_schema.evaluation_context import PREDICATES, load_context, context_digest, applicability
from data_sheets_schema.duplicate_keys import duplicate_keys_in
p = Path('/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/notes/matched_cborg_2026-09-14_v10d/.local_drafts/v10z_registration/evaluation_applicability_preparation_2026-09-19/CHORUS_applicability_draft_v2.yaml')
assert not duplicate_keys_in(p)
context = load_context(p)
assert set(context) == PREDICATES
print('context contract: PASS')
print('normalized SHA256:', context_digest(context))
for key in sorted(context):
    print(key, applicability(key, context).status)
PYTHON
```

Validation result: PASS. Draft file SHA-256 `c20d016a74e5850bf8e6eb9a04ac86f6ed086f6de862b6f1c92cdcfcefe9f26e`; normalized context SHA-256 `9dbc7a148f43e37b20867fa933bf82cb36f8976ebc0a7faaef71dd52c766bc43`. The adjacent `validation_v2.json` records unchanged source and implementation hashes, all seven applicable statuses and the offline boundary. The actual audit5 file policy rejects Reads of the draft, note and validation report; no model-visible input or live condition was changed. This was cheap schema/shape and identity validation only; no implementation test suite or score computation was run.


Preserved original review SHA-256: `a86f5eda5e18ed41dcbb7db9d784de1efdea5adbeb30aaa64013643e6cab258b` (`independent_review.json`). The source bundle, chunk/source manifests, context implementation, profile implementation and profile vocabulary identities are exactly those in the first validation report; the revision adds no new source or instrument code.
