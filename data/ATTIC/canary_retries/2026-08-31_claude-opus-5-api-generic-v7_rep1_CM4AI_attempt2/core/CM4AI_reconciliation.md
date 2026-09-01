# CM4AI Reconciliation Report

**Version label:** 2026-08-31_claude-opus-5-api-generic-v7_rep1
**Records:** full (`CM4AI_d4d.yaml`) and core (`CM4AI_d4d_core.yaml`)
**Audit findings:** 18 (1 high, 4 medium, 13 low)
**Findings resolved by change:** 16
**Findings left as-is:** 2

---

## Summary

The audit raised 18 findings against the full record. Sixteen were addressed by
changes carried through to both the full and core records; two were left as-is
with reasoning recorded below. No finding required the record's referent to
change: the subject remains the June 2026 Data Release (Beta),
`doi:10.18130/V3/HIGT4C`, as stated in the original `source_caveats` and retained
in the reconciled version.

---

## Findings resolved by change

### 1. `publisher` set to the dataset's own DOI (high)

**Original (both records):**

```yaml
publisher: doi:10.18130/V3/HIGT4C
```

**Reconciled (both records):**

```yaml
publisher: ROR:0153tk833
```

The dataset cannot be its own publisher. The bundle attests the University of
Virginia Dataverse as the distributing organization, and the June 2026 release's
own creator affiliations supply `ROR:0153tk833` for the University of Virginia,
so the identifier is taken from the evidence rather than supplied from outside
it. `uriorcurie` range satisfied by a declared prefix.

### 2. Accented proper noun altered in quoted citation and creator name (medium)

**Original:** `Belisle-Pipon JC` in both the `citation` string and the
corresponding `creators` entry; `Jean-Christophe Belisle-Pipon` in
`ethical_reviews`.

**Reconciled:** `Bélisle-Pipon JC` in the citation and creator entry;
`Jean-Christophe Bélisle-Pipon` in `ethical_reviews`.

All four Dataverse release records in the bundle write the accented form. The
American-English rule governs composed prose, not quoted citations or proper
nouns; the de-accented spelling was a misapplication of that rule.

### 3. Preprocessing and labeling strategies asserted of data the release excludes (medium)

**Original:** four `preprocessing_strategies` entries and two
`labeling_strategies` entries describing the MuSIC pipeline as applied
processing, with no scoping and no caveat.

**Reconciled:** each of the six entries now opens with an explicit scope —
"Project-level cell map construction pipeline, not applied to the contents of
this release: …" for preprocessing, and "Project-level cell map annotation,
applied to computed cell maps rather than to the files in this release: …" for
labeling — and each carries a `source_caveats` recording that the material comes
from the tier-3 `biorxiv_preprint` while the tier-1
`june_2026_dataverse_release` states that computed cell maps are not included.
The `known_limitations` entry recording that exclusion is unchanged, so the
record is now internally consistent. The `data_annotation_platform: GPT-4` value
on the second labeling entry is retained.

### 4. Bare grant number in a `uriorcurie`-ranged `id` (medium)

**Original:**

```yaml
grants:
- id: 1OT2OD032742-01
  name: "Bridge2AI: Cell Maps for AI (CM4AI) Data Generation Project"
```

**Reconciled:**

```yaml
grants:
- name: "1OT2OD032742-01"
  description: >-
    NIH funding award number for the Bridge2AI Cell Maps for AI (CM4AI) Data
    Generation Project.
```

`id` is declared `uriorcurie` on every object in the digest, and the bundle
supplies no identifier scheme for NIH awards. The award number moves to `name`,
where it is a label rather than a claimed identifier, and the project title moves
to `description`. The `notes` field carrying the RePORTER details is unchanged.

### 5. Byte counts derived from rounded display strings, applied inconsistently (medium)

**Original:** `total_bytes` on seven of ten file collections (e.g. `113300`,
`1100000`, `30200`), omitted on the three image collections displayed in GB; the
core record mirrored this as `bytes`.

**Reconciled:** `total_bytes` removed from all ten collections in the full record
and `bytes` from all ten distributions in the core record. Each description now
records the displayed size in prose — "Dataverse displays the size as 113.3 KB",
"Dataverse displays the size as 3.8 GB" — so the attested figure survives without
presenting a rounded display value as an exact integer. `source_caveats` now
explains the decision. Treatment is uniform across all ten collections.

### 6. Generic image substrate where a specific term exists (low)

**Original:** `data_substrate: B2AI_SUBSTRATE:19` (Image).
**Reconciled:** `data_substrate: B2AI_SUBSTRATE:56` (Immunofluorescence Image).

The vocabulary supplied in the digest offers an exact match for what the bundle
describes.

### 7. Channel composition placed in `label_description` while `label: false` (low)

**Original:** `label: false` with `label_description` describing the four
fluorescence channels.

**Reconciled:** `label_description` removed; the channel description moves into
the instance's `notes`, combined with the protein count. `label: false` retained.

### 8. Missing per-condition protein count (low, supported omission)

**Reconciled:** `counts: 464` added to the immunofluorescence instance, with the
`notes` recording that each of the three MDA-MB-468 collections covers 464
proteins of interest. The figure is attested by the October 2025 and June 2025
release records for the same image sets carried into this release.

### 9. Second Related Publication absent (low, supported omission)

**Reconciled:** a fifth `related_datasets` entry added:

```yaml
- relationship_type: is_described_by
  target_dataset: doi:10.1101/2024.11.03.621734
  name: A PERTURBATION CELL ATLAS OF HUMAN INDUCED PLURIPOTENT STEM CELLS
  notes: >-
    Listed as a Related Publication of the release; Nourreddine S, … PMCID PMC11580897.
```

### 10. `versions_available` collapsed into one prose string (low)

**Original:** a single list item enumerating four releases.
**Reconciled:** five separate entries, one per version, each naming the release,
its version number and (where stated) its DOI. `latest_version_doi` unchanged.

### 11. `distribution_dates` merged into one entry (low)

**Original:** one `DistributionDate` with a single prose `release_dates` string
covering six events.
**Reconciled:** six `DistributionDate` entries — the June 2026 release, the later
image-file publication, and each of the four prior releases.

### 12. Pointer-style `review_details` (low)

**Original:** both `ethical_reviews` entries carried a `review_details` string
stating only that review "is identified in the release record as the
responsibility of named ethics leads", with `contact_person` as a Person object.

**Reconciled:** `review_details` removed from both entries. `contact_person` is
now the scalar name (`Vardit Ravitsky`, `Jean-Christophe Bélisle-Pipon`) and
`notes` records the attested email address and states plainly that the bundle
gives no reviewing body, approval number or determination. `reviewing_organization`
remains unpopulated, now with an explicit reason rather than silently.

### 13. Inferred ORCID on the governance contact (low)

**Original:**

```yaml
committee_contact:
  id: ORCID:0000-0003-4535-3486
  name: Jillian Parker
```

**Reconciled:**

```yaml
committee_contact: Jillian Parker
```

with the attested email `jillianparker@health.ucsd.edu` now recorded in
`data_governance.notes`. The bundle never equates "Jillian Parker" with the
creator listed as "Parker J", so the ORCID linkage was inferred; the attested
email was previously unrecorded and now is.

### 14. Inferred accountable organization (low)

**Original:** `accountable_organization: {name: University of California San Diego}`.
**Reconciled:** slot removed; `data_governance.source_caveats` added, recording
that the bundle names no accountable organization, that copyright sits with the
Regents of the University of California, and that long-term preservation sits
with the University of Virginia Dataverse (recorded under `retention_limit`) —
neither being an accountability assignment.

### 15. Unattested `language` (low)

**Original:** `language: en` in both records.
**Reconciled:** slot removed from both; `source_caveats` records that the record
and its sources are in English but no source states a language for the dataset.

### 16. Depositor recorded only inside a `maintainers` entry (low, supported omission)

**Reconciled:** `created_by: Niestroy, Justin` added to both records, and the
third `maintainers` entry describing the depositor removed. The remaining
maintainer entries were also split: the original second entry combined Swathi
Thaker and Zhandos Sembay in one object; these are now two entries, one per
person, satisfying the one-object-per-entity rule.

### 17. `keywords` missing the Dataverse subject term (low, supported omission)

**Reconciled:** `Medicine, Health and Life Sciences` added to `keywords` in both
records (alphabetically after `MDA-MB-468`), and the `description` now closes
with a sentence recording the Dataverse subject classification.

### 18. Mistyped limitation (low)

**Original:** `limitation_type: integration_limitation` on the entry about
incomplete final form and pre-publication embargo.
**Reconciled:** `limitation_type: temporal_limitation`. The enum offers no
completeness term; embargo and interim status are temporal conditions, not
integration constraints. The limitation text is unchanged.

---

## Findings left as-is

### Creator affiliation conflict for Sali A

Not raised as a defect by the audit, and unchanged. The `creators` entry retains
`University of California San Diego` with the `source_caveats` recording that the
tier-3 `nature_publication` and `biorxiv_preprint` place Andrej Sali at UCSF and
that the tier-1 release metadata was preferred. This is the ranking rule applied
correctly and is left exactly as written.

### Aggregate project counts excluded from slot values

Not raised as a defect, and unchanged. The website's cumulative figures (1,374
protein interactions, 53,788 images, 7,023 proteins, 11,739 genes, 21.4 TB)
remain confined to `source_caveats` rather than being asserted of this release.
The U2OS exclusion reasoning is likewise unchanged.

---

## Other changes not tied to a numbered finding

Two structural repairs were made in passing, both required by the multivalued-slot
rule rather than by an audit finding:

- `external_resources[*].external_resources` — the declared range is multivalued;
  each entry's value is now a single-item list rather than a bare string.
- `creators[Ideker T].principal_investigator` — reduced from a Person object to
  the scalar `Trey Ideker`, consistent with the treatment of `committee_contact`
  and `contact_person` above.

---

## Consistency between records

Every change above is present in both the full and the core record. The two
records agree on: `publisher`, `created_by`, `keywords`, `description`,
`language` (absent from both), `instances`, `known_limitations`,
`ethical_reviews`, `data_governance`, `preprocessing_strategies`,
`labeling_strategies`, `distribution_dates`, `version_access`,
`related_datasets`, `external_resources`, `maintainers`, `funders`,
`source_caveats` and `notes`. File sizes are absent as integers from both, and
present in prose in both. The core record's `# Phase 4 reconciliation: completed`
line is now accurate.