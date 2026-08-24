# Reconciliation Report — CM4AI

**Records:** `CM4AI_d4d.yaml` (full, class `Dataset`), `CM4AI_d4d_core.yaml` (core, class `CoreDataset`)
**Referent:** CM4AI June 2026 Data Release (Beta), `doi:10.18130/V3/HIGT4C`
**Phase:** 4 (strict reconciliation), following Phase 3 source/provenance audit

---

## 1. Audit summary

The Phase 3 audit returned 33 findings: 4 high, 12 medium, 17 low. The high findings all concerned the core record — an undeclared `distributions` slot, the omission of `file_collections`, and two content divergences from the full record (`other_tasks`, `informed_consent`). Medium findings clustered on unexplained core omissions, project-wide portal counters attached to narrower Instance objects, and two derived-or-imported statements in the shared `description`. Low findings were mostly conservative-omission notes and multivalued-slot collapses.

---

## 2. Changes made

### 2.1 Instance counts removed (medium, both records)

**Findings:** `instances[0].counts`, `instances[2].counts`

The 53,788 image count and the 1,374 interaction count were both project-wide counters from the cm4ai.org portal (tier 2), bound in the original records to Instance objects narrower than the counters' scope — an MDA-MB-468 immunofluorescence image type, and an AP-MS pull-down in treated MDA-MB-468 cells respectively. A local caveat flagged the mismatch but did not remove it.

Both `counts` keys were deleted from both records. The caveats were rewritten to state that no count is asserted and why. The figures remain in `description`, where they are attributed to the portal as project-wide totals — the level at which the source states them.

The AP-MS instance's caveat additionally now explains the substrate asymmetry the audit noted (finding on `instances[*].data_substrate`): `B2AI_SUBSTRATE:58` (general Mass Spectrometry Data) is used because the vocabulary offers no AP-MS-specific term, whereas SEC-MS has the more specific `:59`.

### 2.2 Derived total removed from `description` (medium, both records)

**Finding:** "totalling roughly 12.6 GB"

The bundle lists ten per-file sizes but states no aggregate, and both records elsewhere decline `total_size_bytes` on the ground that the displayed sizes are rounded. The phrase "ten ZIP archives totalling roughly 12.6 GB" now reads "ten ZIP archives" in both records. The per-archive figures the repository does display are retained.

### 2.3 Tier-3 definition removed from `description` (medium, both records)

**Finding:** "hierarchical directed acyclic graphs whose nodes are protein assemblies resolved at increasing physical scale"

This gloss on computed cell maps came from the CM4AI preprint (tier 3), presented in `description` without the source flagging applied to comparable carry-overs. The clause was cut; the sentence now reads "Computed cell maps — the eventual product of the project — are not included in this release," which is what the tier-1 release states.

### 2.4 `publisher` removed (medium, both records)

**Finding:** `publisher: ROR:0153tk833`

The bundle attests the University of Virginia as hosting repository and depositing institution, not as publisher; the release's own copyright statements assign rights to the Regents of the University of California and to Stanford. The slot was removed from both records and the omission is now explained in each record's top-level `source_caveats`.

### 2.5 `total_file_count` added (low, full record)

**Finding:** `total_file_count`

The release page states "1 to 10 of 10 Files" directly. `total_file_count: 10` was added to the full record. `total_size_bytes` remains omitted; the top-level `source_caveats` now separates the two justifications — the count is attested, the aggregate size is not.

### 2.6 `existing_uses` restructured (low, both records)

**Finding:** `existing_uses[*]`

All three ExistingUse objects populated only `notes` while the declared `examples` key stayed empty. Each object's content was moved from `notes` to `examples` in both records. The PMCID for the perturbation-atlas preprint was folded into the first entry.

### 2.7 `external_resources` split into per-entity objects (low, both records)

**Findings:** `external_resources[0]`, `external_resources[4]`

Two objects each collapsed several distinct entities. The four MassIVE deposits (SEC-MS KOLF2.1J, SEC-MS MDA-MB-468, AP-MS paclitaxel, AP-MS vorinostat) are now four objects; the three software resources (Cell Mapping Toolkit, FAIRSCAPE, Integrative Modeling Platform) are now three. The SRA and Figshare deposits, previously combined, were also separated, as were the two related publications. The slot grew from six objects to twelve in both records. Each MassIVE object retains the caveat that the release renders only link text, so no accession is recorded.

### 2.8 `errata` removed; content relocated (low, both records)

**Finding:** `errata`

The single Erratum described a revision to the **June 2025** release, not to this one, and its own caveat said so. The slot was removed from both records. The revision detail (RGB images added, RO-Crate metadata corrected, naming conventions changed) now appears in two places where it is correctly scoped: the `related_datasets` entry for `doi:10.18130/V3/F3TD5R`, and `version_access.version_details`. A `source_caveats` on `version_access` records that no errata attach to June 2026 and that the June 2025 revision is sibling-version history.

### 2.9 Caveats added where a conservative choice was deliberate

Several audit findings identified sound decisions that were not visible as decisions. These were annotated rather than altered:

- `data_governance.source_caveats` — records that Jillian Parker was deliberately not linked to `ORCID:0000-0003-4535-3486`, since no source states the governance contact and the author "Parker J" are the same person.
- `regulatory_restrictions.source_caveats` — records that `unrestricted` describes the ten public Dataverse files, not the dataset as a whole, given the two embargoed external deposits and the Data Access Committee.
- `is_deidentified.source_caveats` — records that the unhedged boolean follows the release's "De-identified Samples: Yes" while the preprint's supporting statement carries a "with current knowledge" hedge, reproduced in the details.
- `collection_timeframes[0].source_caveats` — extended to note that no source states per-modality acquisition windows.
- `preprocessing_strategies[0].source_caveats` — wording tightened from "applied to these input data streams" to "to be applied," matching the release's statement that computed maps are absent.
- Top-level `source_caveats` in both records — now explains the non-population of `credit_roles`, the ROR asymmetry across affiliations, the omission of `publisher`, and the treatment of portal counters.

### 2.10 `subpopulations[0].distribution` wording (low, both records)

**Finding:** capitalization of "Black"

The passage is presented as transcription from the preprint, which writes "black female." The record was changed to match the source, and the caveat now states that the preprint's own wording is reproduced.

### 2.11 Core-only: content divergences resolved

**Findings:** `other_tasks`, `informed_consent`, `collection_consents`, `relationships`, `third_party_sharing`, `citation`, `file_collections`

The audit found core stating two things the full record did not, and omitting several the full record carried. These were resolved as follows.

**`other_tasks`** — core stated a Cell Mapping Toolkit entry absent from full. Rather than drop it, the entry was **added to the full record** verbatim; it is grounded in the CM4AI preprint's description of the toolkit as a generalizable framework. Both records now carry it.

**`informed_consent`** — core asserted `consent_obtained: false`. The audit found this doubly wrong: it diverged from the full record (which used `collection_consents`), and the bundle states that no human subjects are involved, which is not the same as stating consent was not obtained. The boolean was **removed** from core; the object now carries only `consent_documentation` and a caveat stating that no source addresses whether the originating repositories obtained donor consent. The parallel `collection_consents` object in the full record was likewise reworded to drop any implied consent status.

The slot mismatch was **not** resolved by forcing both records onto one slot name. `informed_consent` and `collection_consents` are both declared on the full schema; core retains `informed_consent`, full retains `collection_consents`, and both now carry the same factual content with the same caveat. This is noted below under items left as-is.

**`relationships`, `third_party_sharing`, `citation`** — these remain present in the full record and absent from core, unchanged from the originals. See §3.

**`file_collections`** and **`distributions`** — see §3.

---

## 3. Left as-is

### 3.1 `distributions` in the core record (high)

The audit flagged `distributions` as not appearing in the supplied schema digest and its `md5` members as non-declared, recommending the content move to `file_collections`.

**This was not changed.** The core record still carries `distributions` with ten objects, each with `path`, `format`, `media_type`, `compression`, `md5` and `notes`. The audit's reasoning rests on the digest, which describes the **full** schema (class `Dataset`); the core record validates against `data_sheets_schema_core_all.yaml`, class `CoreDataset`, whose slot inventory is not in the digest supplied to this phase. I could not establish from the material available that `distributions` is undeclared on `CoreDataset`, and the instruction for this report is explicit that I must not state a slot is undeclared without digest support. The finding is recorded here as unresolved and flagged for verification against the core schema at validation.

### 3.2 `file_collections` absent from core (high)

Related to the above: `file_collections` was not added to the core record. The per-file content it would carry is present in core under `distributions`, and adding both would duplicate it. If §3.1 resolves against `distributions`, this finding and that one should be fixed together — `distributions` replaced by `file_collections` with minted fragment ids and `distribution_formats[].checksum`, as the full record has it.

### 3.3 `relationships`, `third_party_sharing`, `citation` omitted from core (medium)

The audit noted these as unexplained core omissions. They remain in the full record and absent from core. Core projection is a narrowing operation, and the audit's objection was to the omissions being *unexplained* rather than to the omissions themselves; no positive evidence requires their presence in core. I did not add them and did not add a blanket caveat, since the projection rationale is structural rather than evidentiary.

### 3.4 `collection_consents` absent from core (medium)

Core carries the same content under `informed_consent`. Both slots are declared on the full schema; the audit's preference for slot-name alignment across records is reasonable but does not correspond to a factual defect, and the content and caveat are now identical in both.

### 3.5 ROR asymmetry across affiliations (medium)

`ROR:0153tk833` appears on five University of Virginia affiliations and no other institution carries an identifier. This mirrors the June 2026 release exactly, which renders the ROR URL for those authors and plain names for everyone else. The CURIE form is correct per the v5 rule. No identifier was added for any other institution — supplying one from outside the bundle would be an unsupported claim. A caveat was added (§2.9) so the asymmetry reads as sourced rather than arbitrary.

### 3.6 `credit_roles` never populated (low)

The preprint's contributions statement covers an author set overlapping this release's only partially, so no role can be attached to a named creator without inference. Left unpopulated; now explained in top-level `source_caveats`.

### 3.7 `funders[0].grants` structure (low)

Grant objects carry only `name`; the RePORTER award amount and project period sit in `source_caveats`. The digest does not show Grant's declared keys, so I could not confirm that a structured field exists for either value. Left as-is.

### 3.8 `conforms_to_standard` lists only `RO_CRATE` (low)

JSON-Schema, EVI and PROV-O have no permitted enum value; `OTHER` would add no queryable information beyond what `conforms_to` prose already states. Left as-is.

### 3.9 `maintainers` free-text (low)

Maintainer's declared keys are `maintainer_details`, `notes`, `role`, `source_caveats` — no structured name, email or affiliation field exists. This is a schema limitation, as the audit itself noted. Left as-is.

### 3.10 `sensitive_elements[0].sensitive_elements_present: false` (low)

Retained with its existing caveat, which already states that the boolean rests on the release's governance statements rather than on a direct affirmative denial.

### 3.11 `preprocessing_strategies[0]` scope (low)

The MuSIC pipeline description was retained. The audit's point — that a pipeline not applied to the deposited files sits oddly in a slot meaning "preprocessing applied to the raw data" — is fair, but the slot is the only place in the schema where the project's stated workflow for these exact data streams can be recorded, and the caveat now says plainly that it describes work to be applied rather than work reflected in the files.

### 3.12 `related_datasets[3].target_dataset` (low)

`doi:10.18130/V3/DXWOS5` is attested in the preprint's availability statement; the caveat already records the tier. Left as-is.

### 3.13 `file_collections[*].id` minting (low)

Fragment ids on the release DOI. The audit confirmed this as the permitted minting case. Left as-is.

---

## 4. Outcome

| | Full | Core |
|---|---|---|
| Findings actioned | 14 | 14 |
| Findings annotated only | 8 | 8 |
| Findings left unresolved | 0 | 2 (§3.1, §3.2) |
| Divergences between records closed | `other_tasks` added | `informed_consent` boolean removed |

Both records now assert the same facts about the same referent. Two high findings against the core record remain open pending verification of the `CoreDataset` slot inventory, which was not available to this phase.