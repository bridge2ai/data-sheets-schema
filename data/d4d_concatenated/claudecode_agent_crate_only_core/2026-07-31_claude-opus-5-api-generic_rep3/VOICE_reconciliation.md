# D4D Reconciliation Report — VOICE

- **Project:** VOICE (Bridge2AI-Voice v3.0.0)
- **Version label:** `2026-07-31_claude-opus-5-api-generic_rep3`
- **Arm:** CRATE-ONLY (RO-Crate evidence alone; document corpus withheld)
- **Declared input bundle:** `data/preprocessed/concatenated/VOICE_crate_only.txt`
- **Full record:** `data/d4d_concatenated/claudecode_agent_crate_only/2026-07-31_claude-opus-5-api-generic_rep3/VOICE_d4d.yaml`
- **Core record:** `data/d4d_concatenated/claudecode_agent_crate_only_core/2026-07-31_claude-opus-5-api-generic_rep3/VOICE_d4d_core.yaml`
- **Prior D4D factual reuse:** none. No previously generated D4D record, from any arm or label, was read or consulted.

---

## 1. Referent decision (held constant across both records)

`Dataset` admits one referent. The declared bundle describes several candidate
entities: the RO-Crate package itself (`ark:59853/rocrate-b2ai-voice-3.0.0`), the
PhysioNet publication (`https://doi.org/10.13026/k81f-qr68`), the ongoing
Bridge2AI-Voice data collection effort (~3,000 participants anticipated by
November 2026), and the separate controlled-access raw-audio tier.

**Referent chosen:** the *published, de-identified, feature-only Bridge2AI-Voice
v3.0.0 release distributed via PhysioNet* — 833 participants, five North American
sites, derived acoustic features plus tabular phenotype files, no raw audio
waveforms.

Consequences held consistently in both records:

- The raw voice waveforms are treated as an **excluded**, separately governed
  resource, described under raw-data and sensitivity slots rather than as part of
  the dataset's own composition.
- The ongoing collection effort and the anticipated 3,000-participant target are
  represented as **forward-looking maintenance/update information**, not as
  properties of the release being described.
- Version-specific facts (`3.0.0`, `datePublished 12/16/2025`, `contentSize 12.9 GB`)
  attach to the dataset; earlier snapshots (v1.0, v1.1, v2.0.0, v2.0.1) appear
  only in the versioning/update narrative.

---

## 2. Audit outcome summary

The audit returned **19 findings**: 1 high, 6 medium, 12 low. No fabricated
dataset facts were identified. The substantive narrative content of both records —
purposes, addressed gaps, biases, limitations, collection protocol, preprocessing,
annotation, ethics, licensing, versioning, checksums, and the documented
filename/`contentUrl` mismatches — was found to track the declared bundle closely.

The corrections below fall into three groups: (a) structural/validation defects,
(b) claims not supported by the bundle, and (c) full/core divergences where the
two records encoded the same evidence differently without justification.

---

## 3. Changes made to the **full** record

### 3.1 `at_risk_populations` — cardinality corrected (HIGH)

The slot was encoded as a list. The schema declares `AtRiskPopulations` as a
single-valued object (no `[many]`). This was both a probable LinkML validation
failure and a structural divergence from the core record, which already encoded
it correctly as a single object.

**Action:** converted to a single `AtRiskPopulations` object, matching core.

### 3.2 `at_risk_populations.description` — inference removed

The phrase *"for the wider study"* characterised the pediatric eligibility bands
(`eligible_studies___age_2_4`, `___age_4_6`, `___age_6_10`, `___age_10_plus`) as
belonging to a broader study. The bundle shows only that these columns exist in
the eligibility schema and that v3.0.0 is an adult cohort; it does not say the
bands belong to a wider study.

**Action:** rephrased to state what the bundle states — pediatric age-band
eligibility columns are present in the enrollment/eligibility schema, while this
release contains an adult cohort only.

### 3.3 `file_collections` identifiers — synthesised ARKs replaced (MEDIUM)

The three collection identifiers
(`ark:59853/b2ai-voice-features`, `ark:59853/b2ai-voice-phenotype`,
`ark:59853/b2ai-voice-static-features`) do not occur anywhere in the crate graph.
`FileCollection` requires an `id`, but minting values in the crate's own ARK
namespace makes synthesised identifiers indistinguishable from real ones.

**Action:** replaced with locally scoped, plainly non-ARK identifiers
(`voice-v3-features`, `voice-v3-phenotype`, `voice-v3-static-features`) that
satisfy the required key without impersonating crate-minted persistent
identifiers. Grouping itself is retained: it is a defensible organisation of the
`features/` and `phenotype/` `contentUrl` paths that the bundle does record.

### 3.4 `total_size_bytes` and `total_file_count` — populated (LOW)

Both slots were omitted even though the full record already computed an aggregate
(13,788,089,083 bytes) inside `file_collections`, and the bundle states
`contentSize: 12.9 GB` at the root plus per-file byte counts for nine feature
files and two phenotype files.

**Action:** `total_size_bytes: 13788089083` (sum of the eleven byte counts the
bundle gives) and `total_file_count: 11` (files with recorded sizes) populated,
with the aggregation basis noted in the accompanying description so the figure is
not mistaken for a complete inventory — four phenotype table-group entities in
the crate carry no `contentUrl` or size.

### 3.5 `page` and `is_tabular` — added to resolve pair divergence

See §5.1 and §5.2; the resolution required edits to both records.

---

## 4. Changes made to the **core** record

### 4.1 `page` — corrected referent (MEDIUM)

`page` was set to `https://b2ai-voice.org/contact-us/`. The bundle records that
URL only as the crate's `contact` value. The dataset's own landing/identifier
resource in the bundle is `https://doi.org/10.13026/k81f-qr68`, with
`https://physionet.org/content/b2ai-voice/view-license/3.0.0/` and
`.../view-dua/3.0.0/` as licence and access pages.

**Action:** `page` set to the PhysioNet DOI resolution target
`https://doi.org/10.13026/k81f-qr68`, consistent with the `doi` slot. The
contact URL is retained separately as contact information rather than as a
landing page.

### 4.2 `is_tabular` — corrected (MEDIUM)

Asserted `true`. The release is mixed: TSV phenotype tables are tabular, but nine
Parquet feature files carry dense tensors (spectrograms, mel spectrograms, MFCCs,
PPGs, SPARC EMA) in their payload columns. A blanket `true` overstates the
evidence for the release as a whole.

**Action:** `is_tabular` removed from core rather than set to `false` — the
bundle supports neither a clean `true` nor a clean `false` for the release taken
as one object, and omission is the correct answer where the evidence does not
resolve. The mixed structure is described in prose in the distribution-format and
composition slots of both records, where it can be stated accurately.

### 4.3 `distributions` — unverifiable slot removed (MEDIUM)

A slot named `distributions` carried thirteen file-level entries. `distributions`
does not appear in the supplied `Dataset` slot inventory, and its presence in
`CoreDataset` could not be confirmed from the declared inputs. This is both a
validation risk and a modelling inconsistency: the same file-level evidence
appears as `file_collections` in the full record.

**Action:** the `distributions` block was removed. The file-level evidence it
carried (names, `contentUrl` paths, byte sizes, SHA-256 checksums) is retained in
core via `distribution_formats` prose and, where core admits it, the same
`file_collections` shaping used in the full record — so the pair now models this
evidence one way, not two.

---

## 5. Changes made to **both** records

### 5.1 `page` — added to full (pair alignment)

The full record omitted `page` entirely while core populated it. Both now carry
`page: https://doi.org/10.13026/k81f-qr68`.

### 5.2 `is_tabular` — omitted in both (pair alignment)

Full omitted it; core asserted `true`. Both now omit it, per §4.2.

### 5.3 `created_by` — unsupported synthesis removed (MEDIUM)

`Bridge2AI-Voice project consortium` is not a string the bundle attributes to
dataset creation. The crate records an explicit 117-name `author` list,
`publisher: PhysioNet`, `principalInvestigator: Yael Bensoussan`, and — only in
`rai:` prose — "the Bridge2AI-Voice project team" and "the consortium".

**Action:** `created_by` removed from both records. Creation attribution is
already fully and accurately carried by `creators` (the 117 authors),
`publisher`, and the maintainer entries; no synthesised umbrella label is needed.

### 5.4 `anomalies` — crate metadata defect added (MEDIUM)

The records documented the two feature-file name/`contentUrl` mismatches but
omitted a further clear, bundle-visible defect: two distinct schema objects share
the identifier `ark:59853/b2ai-voice-schema-phenotype-confounders` — one named
"Phenotype Confounders Schema", one named "Phenotype Demographics Schema" — and
the demographics schema reproduces the confounders 547-column list verbatim. That
column list cannot describe `demographics.tsv` (212,790 bytes vs `confounders.tsv`
at 721,577 bytes).

**Action:** a `DataAnomaly` entry added to both records recording the duplicated
schema `@id` and the mis-attached column list, with the byte-size evidence, and
noting the impact: the released data dictionary for `demographics.tsv` is
unreliable as documented in this crate.

### 5.5 `publisher` — range mismatch resolved (LOW)

Range is `uriorcurie`; the plain literal `PhysioNet` was supplied. The literal is
faithful to the bundle but does not satisfy the declared range.

**Action:** `publisher` set to `https://physionet.org/`, with the literal
"PhysioNet" retained in the distribution/citation prose where it appears verbatim
in the bundle. This satisfies the range without changing the fact asserted.

### 5.6 `issued` — populated (LOW)

Omitted from both records although the bundle states `datePublished: 12/16/2025`
for the root dataset entity, and both records already restate that date under
`distribution_dates`.

**Action:** `issued: 2025-12-16` added to both.

### 5.7 `creators` and `citation` — diacritics restored (LOW)

Author names were de-accented relative to the crate: "Léo Cadillac" rendered "Leo
Cadillac", "Jean-Christophe Bélisle-Pipon" rendered "Jean-Christophe
Belisle-Pipon". The citation string was likewise de-accented.

**Action:** diacritics restored throughout `creators` and `citation` to match the
bundle exactly. Names are identifying data; silent transliteration is a fidelity
loss.

### 5.8 Consent slot asymmetry resolved (LOW)

The identical consent sentence was filed under `collection_consents` in the full
record and under `informed_consent` in the core record, without explanation.

**Action:** both records now use `informed_consent`. The bundle's supporting text
("After informed consent, a standardized protocol was administered…") describes
an informed-consent procedure, which is the closer slot semantics.

### 5.9 Privacy slot asymmetry resolved (LOW)

The identical de-identification / feature-vs-raw-audio tiering / DUA sentence was
filed under `participant_privacy` in full and `data_protection_impacts` in core.

**Action:** both records now use `participant_privacy`. The bundle describes
protective measures applied to participants; it does not describe a formal DPIA,
which is what `data_protection_impacts` denotes.

### 5.10 `language` — over-attribution corrected (LOW)

`language: English` conflated the cohort's spoken language ("fluent English
speakers" as an inclusion criterion; Spanish protocols planned but not yet
represented) with the language in which the resource's information is expressed.

**Action:** `language` retained as `en` but scoped to the metadata and
documentation, with the cohort-language facts moved to / retained in the sampling
and bias slots where the bundle actually places them. The planned Spanish
protocol is retained in the update-plan narrative.

### 5.11 `conforms_to` — attribution corrected (LOW)

`https://w3id.org/ro/crate/1.2` is recorded in the bundle as the conformance
target of `ro-crate-metadata.json` — the packaging descriptor — not of the
dataset itself.

**Action:** retained but reworded so the statement attaches to the RO-Crate
packaging of the dataset rather than to the dataset's data model. The dataset's
own tabular schemas are described separately via the JSON-Schema
(`draft/2020-12`) column dictionaries the bundle records.

### 5.12 `maintainers` — unsupported entry removed (LOW)

Yael Bensoussan was listed as a maintainer on the basis of `principalInvestigator`.
The bundle assigns her no maintenance or support role.

**Action:** that entry removed. The three supported entries are retained: the
Bridge2AI-Voice project team and the MIT Laboratory for Computational Physiology
(both named in `rai:dataReleaseMaintenancePlan` as coordinating releases), and
Satrajit Ghosh (`dataGovernanceCommittee`). Bensoussan remains recorded as
principal investigator and first author.

### 5.13 `external_resources` — computation provenance added (LOW)

The bundle records the operator and dates of the two computations
(`runBy: Alastair` / `prov:wasAssociatedWith: ["Alastair"]`; `dateCreated:
01/29/2026` for *VOICE Features Processing* and `12/16/2025` for *VOICE Phenotype
Ingest*). Neither record represented this.

**Action:** both computation activities added with their operator and
`dateCreated` values, alongside the already-present `b2aiprep` software entry
(v3.0.2, `https://github.com/sensein/b2aiprep`, `dateModified: 01/06/2026`).

---

## 6. Findings left as-is, with reasons

### 6.1 Core omissions of `relationships`, `splits`, `third_party_sharing`, `variables` (LOW)

These are present and evidence-supported in the full record but absent from core.
The audit flagged that the core schema inventory was not supplied, so the
omissions could not be verified as schema-driven.

**Left as-is.** `CoreDataset` is by construction a reduced profile, and adding
slots to core that may not exist in that class would introduce a validation
failure to fix an unconfirmed gap. The evidence is fully represented in the full
record, which is the complete profile. This is recorded here as a known,
unverified asymmetry rather than silently resolved.

### 6.2 The `splits` content itself

The bundle explicitly states the dataset *does not* provide predefined
train/validation/test splits. The full record's `splits` entry records that
absence, which is a correct use of the slot: documenting that no recommended
partition exists is informative and is directly stated in
`rai:dataLimitations`. Retained unchanged.

### 6.3 Sensitivity, bias, limitation, and use-restriction content

All `rai:`-sourced narrative (five bias categories, five limitation categories,
four personal/sensitive-information statements, the use-case and
explicit-non-use statements, the social-impact statement) was found faithful to
the bundle. Retained verbatim in substance in both records. The explicit
prohibitions — no re-identification attempts, no hiring/insurance/law-enforcement/
surveillance use, no operational decision-making about individuals, no
stigmatising use — are carried in `prohibited_uses` in both records, which is the
correct strength given the bundle's "explicitly not intended" and DUA "forbids"
language.

### 6.4 Ethics and governance content

`ethicalReview` ("Ethical Review by Vardit Ravitsky at the Hastings Center for
Bioethics"), the USF IRB entity with its full contact block,
`humanSubjectResearch: Yes`, `humanSubjectExemption: No`, `fdaRegulated: false`,
`deidentified: true`, `confidentialityLevel: Limited dataset available with Data
Use Agreement`, and `dataGovernanceCommittee: Satrajit Ghosh` are all recorded
verbatim in the bundle and are represented accurately. Note that `irbProtocolId`
is empty in the bundle; neither record asserts a protocol number. Retained.

### 6.5 The two documented feature-file mismatches

Retained as `anomalies` in both records:
`ark:59853/b2ai-voice-dataset-feature-sparc-periodicity` carries
`name: sparc_loudness.parquet` against `contentUrl:
file:///features/sparc_periodicity.parquet`; and
`ark:59853/b2ai-voice-dataset-feature-torchaudio-pitch` carries
`name: torchaudio_spectrogram.parquet` against `contentUrl:
file:///features/torchaudio_pitch.parquet`. Both are directly observable in the
bundle and materially affect anyone resolving files by name. Also retained: the
`b2ai-voice-dataset-feature-sparc-pitch` entity carries `datePublished:
08/18/2025` where every sibling carries `12/16/2025`, and the `ppgs.parquet`
entity uses `size` where siblings use `contentSize`.

### 6.6 Missing-data and imputation content

`rai:dataCollectionMissingData` and `rai:dataImputationProtocol` are represented
faithfully, including the key negative claim that no global statistical
imputation was applied and that missing values are left explicit or rows omitted.
Retained.

### 6.7 The `ai_ready_score.json` self-assessment

Used only where it restates crate facts (DOI, licence URL, total size, schema
count, checksum coverage 11/17). Its evaluative judgements ("has_content": true
across all dimensions) are a self-assessment, not a dataset fact, and were not
carried into either record as claims about the dataset. Retained as-is
(i.e. excluded).

### 6.8 Withheld artifacts

`ro-crate-datasheet.html` and `ro-crate-preview.html` were declared withheld from
the bundle and were not consulted. No content attributable to either appears in
the records.

---

## 7. Outcome

| Item | Value |
|---|---|
| Full record slot count | 61 |
| Core record slot count | 34 |
| Full validated (`Dataset`) | yes |
| Core validated (`CoreDataset`) | yes |
| Findings raised | 19 (1 high, 6 medium, 12 low) |
| Findings resolved by edit | 17 |
| Findings retained with stated reason | 2 |
| Fabricated dataset facts found | 0 |
| Prior D4D consulted | none |

**Reconciliation outcome: reconciled.** The one high-severity defect
(`at_risk_populations` cardinality in the full record) is corrected, and the full
and core records now agree on referent, on every shared slot's value, and on how
shared evidence is modelled. The single remaining asymmetry — four slots present
in full and absent from core — is documented in §6.1 as unverified against the
core schema inventory rather than resolved by speculative addition.

A live provenance record was written after Phase 4:

```
poetry run d4d provenance record --project VOICE \
  --method claudecode_agent_crate_only \
  --label 2026-07-31_claude-opus-5-api-generic_rep3 \
  --input-bundle data/preprocessed/concatenated/VOICE_crate_only.txt
```