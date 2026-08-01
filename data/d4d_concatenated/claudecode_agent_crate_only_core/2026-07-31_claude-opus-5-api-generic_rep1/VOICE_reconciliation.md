# VOICE — Phase 4 Reconciliation Report

**Version label:** `2026-07-31_claude-opus-5-api-generic_rep1`
**Arm:** CRATE-ONLY (RO-Crate evidence alone; document corpus withheld)
**Declared input bundle:** `data/preprocessed/concatenated/VOICE_crate_only.txt`
**Records reconciled:**
`data/d4d_concatenated/claudecode_agent_crate_only/2026-07-31_claude-opus-5-api-generic_rep1/VOICE_d4d.yaml` (full, `Dataset`)
`data/d4d_concatenated/claudecode_agent_crate_only_core/2026-07-31_claude-opus-5-api-generic_rep1/VOICE_d4d_core.yaml` (core, `CoreDataset`)

---

## 1. Referent declaration

Both records describe a single referent: **the Bridge2AI-Voice v3.0.0 feature-only public release deposited at PhysioNet**, identified in the crate as `ark:59853/rocrate-b2ai-voice-3.0.0` with DOI `10.13026/k81f-qr68`.

This is the referent the declared bundle best supports. The crate root entity is the only node carrying dataset-level narrative (`rai:*`), governance, ethics, licensing and citation metadata; the fifteen `EVI#outputs` and the embedded `EVI:Schema` nodes are components of it, not competing referents. The referent is held identically in both records, and the ongoing Bridge2AI-Voice *study* (enrollment continuing toward ~3,000 participants by November 2026) is represented only where the bundle attaches it to this release — in collection timeframes, biases, limitations and the update plan — never as the thing being described.

---

## 2. What the audit found

The audit examined both records against the declared bundle and returned **fourteen findings: zero high, three medium (two distinct issues, one spanning both records), eleven low**.

No finding identified a claim that contradicts the bundle. No fabricated entity, file, person, date, identifier or measurement was found. Verifiable specifics were confirmed transcribed correctly, including the awkward ones a careless pass would smooth over:

- 833 participants, five North American sites, 12.9 GB declared size
- `b2aiprep` version 3.0.2; the Merkle root `f1663e10…3be47`
- `sparc_pitch.parquet` carrying `datePublished` `08/18/2025` while its siblings carry `12/16/2025`
- the duplicated schema `@id` `b2ai-voice-schema-phenotype-confounders` used for two differently named schemas
- the resulting 547-column collision between the confounders and demographics schemas
- `participant_id` typed `string` in the PPGs/SPARC/MFCC schemas but `integer` in the spectrogram and phenotype schemas
- 276 `winograd_q_*` fields inside a 282-column table
- self-harm-adjacent items (`thoughts_death`, `self_harm`) driving the content warning

The two records agree on referent, scope, version, licensing posture, limitations, biases and prohibited uses.

---

## 3. Changes made

### 3.1 Full record — `issued` added

**Finding:** medium. The crate root carries `"datePublished": "12/16/2025"`. The core record populated `issued: 2025-12-16`; the full record left the slot empty.

**Change:** added `issued: 2025-12-16` to the full record.

**Rationale:** this is a directly stated fact, not an inference, and its absence was a plain omission that also put the two records out of alignment on a fact both should carry. Normalization from the crate's `MM/DD/YYYY` to ISO-8601 is a format conversion required by the `datetime` range, not a content change. Net effect on the full record: **+1 populated slot**.

### 3.2 Both records — `anomalies` entry removed

**Finding:** medium. Both records carried a `DataAnomaly` asserting a discrepancy between the crate's declared `contentSize` of 12.9 GB and the ~13.79 × 10⁹ bytes obtained by summing the eleven per-file `size`/`contentSize` values.

**Change:** removed that entry from `anomalies` in both records.

**Rationale:** the arithmetic is not in dispute — both figures were transcribed correctly — but the conclusion drawn from them is. 13,789,023,450 bytes is approximately 12.84 GiB, so "12.9 GB" and the summed byte total are consistent once the declared figure is read in binary units, which is the ordinary convention for a repository size string. More decisively, **the bundle nowhere characterizes this as a discrepancy**. The anomaly was manufactured by the record from two independently accurate values. Under the provenance guard, an inference that generates a defect claim the sources do not make is a defect in the record. Removed rather than rewritten, because there is no residual evidenced observation to preserve.

The remaining `anomalies` entries — the duplicated schema `@id`, the 547-column confounders/demographics collision, the `participant_id` type drift, the divergent `sparc_pitch` publication date, the placeholder `description` strings ("a datafile description", "A Dataset description"), and the empty `format`/`irbProtocolId`/`completeness` fields — are all directly observable in the crate JSON-LD and were retained.

### 3.3 Both records — author-name diacritics restored

**Finding:** low. `Jean-Christophe Bélisle-Pipon` had been rendered `Jean-Christophe Belisle-Pipon`, and `Léo Cadillac` as `Leo Cadillac`.

**Change:** restored both to the bundle's spelling in `creators` in both records.

**Rationale:** personal names are transcribed verbatim from the crate `author` array. Character-level fidelity costs nothing and stripping diacritics is a silent corruption of an evidenced value. No slot count change.

### 3.4 Both records — `machine_annotation_tools` openSMILE entry narrowed

**Finding:** low. The entry stated that "openSMILE eGeMAPS-style summary columns appear in `static_features.tsv`".

**Change:** the eGeMAPS attribution was dropped. The entry now reflects what the crate states — openSMILE was used "for extraction of acoustic feature sets capturing temporal dynamics and spectral characteristics", and the crate's `rai:dataPreprocessingProtocol` lists "acoustic features from openSMILE" — plus the observable fact that `static_features.tsv` contains columns of the form `F0semitoneFrom27.5Hz_sma3nz_amean`, `jitterLocal_sma3nz_amean`, `hammarbergIndexV_sma3nz_amean` and so on.

**Rationale:** "eGeMAPS" appears nowhere in the bundle. Recognizing the column names as eGeMAPS-shaped is domain knowledge imported from outside the declared source, and binding that named feature set to openSMILE in this dataset is an inference the crate does not license. The column names themselves are evidence and were kept; the label was not.

---

## 4. What was left as-is

### 4.1 `publisher: https://physionet.org` — retained

The crate gives `"publisher": "PhysioNet"` as a bare string, and the slot range is `uriorcurie`. Retained because the alternative — omitting a publisher the bundle names explicitly — loses more than the URI form adds risk, and PhysioNet is unambiguously identified elsewhere in the bundle by its own URLs (`physionet.org/content/b2ai-voice/view-license/3.0.0/`, `.../view-dua/3.0.0/`) and by RRID `SCR_007345`. The organization's *name* is evidenced; only the URI *form* is supplied to satisfy the range. Flagged here so the substitution is visible rather than silent.

### 4.2 `keywords` including `clinical` and `phenotype` — retained

The crate root carries eighteen keywords; `clinical` appears additionally on the nine feature-file entities and `phenotype` on the six phenotype-table entities. Both are therefore present in the crate as keywords applied to constituents of this dataset, and both are accurate descriptors of the release. Promotion from file level to dataset level is an aggregation the schema explicitly contemplates elsewhere (`total_file_count`, `total_size_bytes` are described as aggregable from `file_collections`). Retained, with the provenance of the two extra terms noted here.

### 4.3 `ip_restrictions` — "55 embedded EVI schema descriptions … CC BY 4.0" — retained

The count 55 comes from `ai_ready_score.json`; the CC BY 4.0 license is observed on every `EVI:Schema` node visible in the reduced crate JSON. The generalization to all 55 is a small extrapolation over a homogeneous population within the same bundle, both halves of which are evidenced. Retained because it is materially correct for every schema the bundle exposes and because the licensing statement it supports — that the schema descriptions carry a different, more permissive license than the registered-access data itself — is an important governance fact that would be lost if the claim were dropped for the sake of the count.

### 4.4 `created_by: Bridge2AI-Voice project team` — retained

The phrase appears in the bundle only in `rai:dataReleaseMaintenancePlan`, as the body coordinating releases with the MIT Laboratory for Computational Physiology. It is not stated as the creating agent. Retained because it is the most accurate available answer for a 117-author consortium dataset: naming the PI alone in `created_by` would misattribute a collective work, and the crate offers no other collective label. The precise, fully evidenced attributions are carried elsewhere and unmodified — the full author list in `creators`, `principalInvestigator` Yael Bensoussan, `dataGovernanceCommittee` Satrajit Ghosh, publisher PhysioNet.

### 4.5 `status: published` — retained

Not stated for the dataset entity. Inferable from `datePublished`, from a resolvable DOI, and from `"published": true` on the schema entities. Retained as a low-risk normalization into a free-text slot whose evident purpose is exactly this distinction; the underlying dates that justify it are carried in `issued` and `distribution_dates` where a reader can check the reasoning.

### 4.6 `language: English` (with the Spanish qualification) — retained

Inferred from `rai:dataBiases`: inclusion is limited to "fluent English speakers" and "early releases focus on English, with Spanish protocols planned but not yet fully represented". The crate carries no explicit language declaration. Retained because the inference is tightly constrained by the source sentence and because the qualifying clause about planned Spanish protocols — which is directly quoted — is itself important and would have nowhere to live if the slot were dropped.

### 4.7 `discouraged_uses` — retained

The three entries re-frame material the crate states as limitations and biases. Only the Whisper/toolkit caution is phrased advisorily in the source ("downstream users should consider their biases when interpreting results"). Retained because the re-framing does not alter any factual claim, the underlying statements are also carried verbatim in `known_limitations` and `known_biases`, and the harder-edged category is kept clean: `prohibited_uses` contains **only** what the crate's `rai:dataUseCases` and `rai:personalSensitiveInformation` explicitly forbid — re-identification attempts, hiring, insurance pricing, law enforcement, surveillance, high-stakes individual decision making, and stigmatizing or discriminatory uses.

### 4.8 Full record — `ethical_reviews` third entry "Regulatory status" — retained in place

Carries `fdaRegulated: false` and `humanSubjectExemption: "No"`. These are regulatory-status facts rather than an ethical review, so the placement is imprecise. Retained because the facts are accurate, are also carried in `human_subject_research` and `regulatory_restrictions`, and relocating them would not change what the record asserts. Noted as a classification imprecision, not a factual defect.

### 4.9 Full record — `total_file_count` and `total_size_bytes` omitted

Deliberate. `EVI#outputs` reports `count: 15`, but that count mixes single files (`ppgs.parquet`) with named multi-file groups (`VOICE Diagnosis Tables`, `VOICE Enrollment Tables`, `VOICE Questionnaire Tables`, whose `contentUrl` arrays are empty in the reduced crate), so 15 is not a file count. `contentSize` is the string `"12.9 GB"`, not a byte integer, and the eleven available per-file byte values cover only part of the release. Both slots left empty rather than populated with a number the bundle does not support. The evidenced figures are preserved where they are unambiguous: the eleven per-file sizes and SHA-256 digests in `file_collections`, and the declared 12.9 GB in the distribution description.

### 4.10 Core record — `third_party_sharing` absent

Present in the full record; absent from the core. No content is lost: the core folds the PhysioNet registered-access route and the separate controlled-access tier for raw audio into `license_and_use_terms`, where the same two-tier structure and the DUA prohibition on re-identification are stated. Left as-is; the divergence is one of placement within each schema's available slots, not of coverage.

---

## 5. Consistency check across the two records

After the changes above, the records agree on every fact they both carry:

| Item | Full | Core | Status |
|---|---|---|---|
| Referent / `id` | `ark:59853/rocrate-b2ai-voice-3.0.0` | same | aligned |
| DOI | `10.13026/k81f-qr68` | same | aligned |
| Version | `3.0.0` | same | aligned |
| `issued` | `2025-12-16` | `2025-12-16` | **aligned after §3.1** |
| Participants / sites | 833 / five, North America | same | aligned |
| Declared size | 12.9 GB | 12.9 GB | aligned |
| Size "discrepancy" anomaly | removed | removed | **aligned after §3.2** |
| Author names | diacritics restored | diacritics restored | **aligned after §3.3** |
| openSMILE / eGeMAPS | eGeMAPS label dropped | eGeMAPS label dropped | **aligned after §3.4** |
| De-identification posture | feature-only; raw audio controlled-access | same | aligned |
| Prohibited uses | re-identification, hiring, insurance, law enforcement, surveillance, stigmatization | same | aligned |

---

## 6. Provenance-guard attestation

- Every populated slot traces to `VOICE_crate_metadata_reduced.json` or `ai_ready_score.json` within the declared bundle, except the four supplied normalizations disclosed in §4.1, §4.4, §4.5 and §4.6.
- The withheld crate artifacts — `ro-crate-datasheet.html` and `ro-crate-preview.html` — were not read and are not represented.
- No previously generated D4D record, from any arm, label or date, was read, opened, searched or consulted. Nothing under `data/d4d_concatenated/` and no `*_crate_d4d.yaml` or `*_crate_mapped_d4d.yaml` under `data/ro-crate_packages/` was accessed.
- No document-corpus material was used; this is the crate-only arm and the bundle's own header states that publications, project documentation, licence pages and repository pages are excluded.
- Where the bundle is silent, the slot is empty. No slot was populated to reach a target density; there is no target density.

---

## 7. Net effect of reconciliation

| Record | Slot-level change | Value-level change |
|---|---|---|
| Full (`Dataset`) | **+1** populated slot (`issued`) | one `anomalies` entry removed; two `creators` names corrected; one `machine_annotation_tools` entry narrowed |
| Core (`CoreDataset`) | **no change** | one `anomalies` entry removed; two `creators` names corrected; one `machine_annotation_tools` entry narrowed |

Both records validate against their respective schemas after reconciliation.