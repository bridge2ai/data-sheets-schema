# RO-Crate Ingestion Study — GC Packages as D4D Generation Input

**Date:** 2026-07-24
**Scope:** CHORUS and CM4AI crates (AI_READI and VOICE links pending)
**Question asked:** where do per-GC RO-Crate packages live, and do they need
preprocessing to be usable?

**Short answer:** CHORUS is usable after dropping one non-schema key. CM4AI needs
four repairs, one of them a genuine upstream data error, plus a ~1300× size
reduction. Neither is blocked; both need a deterministic normalization step.

## 1. Standard location

New: **`data/ro-crate_packages/{PROJECT}/`**, named to match the existing
siblings `data/ro-crate/` (profiles/specs we author) and `data/ro-crate_mapping/`
(mapping tables). Upstream crate data was not previously stored anywhere in the
repo.

```
data/ro-crate_packages/
  crate_manifest.yaml          # DOIs, file ids, sizes, verified md5s
  README.md                    # convention + per-project status
  {PROJECT}/raw/               # bytes as downloaded — never edited
  {PROJECT}/crate/             # extracted archive; gitignored, re-creatable
  {PROJECT}/processed/         # normalized artifacts (d4d rocrate normalize)
```

All five downloaded files were checksum-verified byte-identical against the
upstream Dataverse-reported md5s.

## 2. What was downloaded

| Project | Source | Shape |
|---------|--------|-------|
| CHORUS | `doi:10.18130/V3/XNBOPG` v1.1, published 2026-04-21 | 4 files, standalone, 100 KB |
| CM4AI | `doi:10.18130/V3/HIGT4C` v2.0, published 2026-06-17 | crate nested inside `cm4ai_release_metadata.zip` (1.2 MB → 47 MB extracted) |

CM4AI's crate is **not** a standalone file set. The HIGT4C release has 10 files;
nine are data payloads, three of which are 4–5 GB image archives. Only
`cm4ai_release_metadata.zip` was downloaded. Anyone re-running this should not
naively fetch the whole release — that is ~13.5 GB.

Note that CHORUS having a published Dataverse crate at all is relevant to
`notes/UPSTREAM_SOURCE_DISCREPANCIES.md` §6, which flagged that the input sheet
lists no CHORUS data resource. It does exist; the sheet just does not cite it.

## 3. Both crates ship the same four artifacts

- `ro-crate-metadata.json` — RO-Crate JSON-LD, EVI-typed, with Croissant `rai:`
  fields. Richest D4D-relevant content.
- `ro-crate-linkml.yaml` — **a D4D-shaped LinkML rendering**, declaring
  `conforms_to: D4D Schema` and using our own slot names.
- `ro-crate-datasheet.html` — human-readable "RO-Crate Datasheet" rendering.
- `ai_ready_score.json` — AI-readiness self-assessment across fairness,
  provenance, characterization, pre-model explainability, ethics, sustainability,
  computability.

The `ro-crate-linkml.yaml` file is the headline finding: upstream has already
done the RO-Crate → D4D mapping, so the highest-value input is ~9.5 KB, not the
whole crate.

### D4D-relevant content actually present

**Tested 2026-07-24, and the answer differs by project.** An earlier draft of
this note claimed the crates carry governance/ethics/limitations content absent
from the document corpus. That was asserted from reading the crates, not from
checking the corpora. Checked properly, it holds for CHORUS and fails for CM4AI.

**CM4AI — largely redundant.** Every distinctive phrase in the crate's
`known_limitations`, `known_biases`, `prohibited_uses`, `discouraged_uses`,
`missing_data_documentation`, `ethical_reviews`, and `collection_mechanisms`
appears verbatim in `CM4AI_preprocessed.txt` — "predicted cell maps",
"temporary pre-publication", "not to be used in clinical", "de-identified human
cell lines", and the rest. They trace to
`dataverse_10.18130_V3_{K7TGEM,F3TD5R,HIGT4C}` in the bundle: the crate and the
Dataverse dataset page render **the same underlying metadata record**, and the
Dataverse pages are already cited sources.

**CHORUS — genuinely additive**, and for the complementary reason. Its crate
sits at DOI `XNBOPG`, which the input sheet does not cite (see
`notes/UPSTREAM_SOURCE_DISCREPANCIES.md` §6), so it never entered the corpus.

So the general rule is not "crates add governance content". It is: **a crate adds
content only where its corresponding data-repository record is not already a
cited source.** That is a property of the input sheet's coverage, not of
RO-Crates. Fixing discrepancy §6 by citing `XNBOPG` would shrink CHORUS's crate
delta too.

Verified absent from CHORUS's 36 KB bundle: `rai:dataBiases`
(referral bias, MNAR missingness, documentation bias), `rai:dataLimitations`,
`rai:maintenancePlan`, `rai:intendedUseCases`, `rai:conditionsOfAccess`,
`rai:personalSensitiveInformation`, `ethicalReview`, `irb` (MGB IRB, protocol
`#2022P000707`), `humanSubjectExemption`, `confidentialityLevel` (HL7:2V),
`deidentified`, `fdaRegulated`, `contentSize` (1.2 TB), `completeness` ("Interim
release with partial data… No DICOM images are included"), and the DUA URL.
Only bare topic mentions overlap (HIPAA, DUA, NIST, OMOP, WFDB); none of the
structured content is present.

## 4. Conformance test against our own schema

Validated with `linkml-validate -s data_sheets_schema_all.yaml -C Dataset`.

**CHORUS — passes after one deletion.** The only failure is a non-schema
top-level key `bytes` (1319413953331, the byte count matching `contentSize:
1.2 tb`). Drop it and:

```
No issues found
```

That is the entire preprocessing requirement for CHORUS.

**CM4AI — four repairs required.**

1. **Non-schema top-level keys**: `bytes`, `format`, `encoding`.
2. **`compression` is mis-populated and violates the enum.** It contains
   `['.d', '.d directory group', '.tsv', '.xml', 'TSV', 'csv', 'executable',
   'fastq.gz', 'h5', 'h5ad', 'image/jpeg', 'pdf', 'unknown']` — file *formats*,
   not compression codecs. D4D permits only
   `gzip|bzip2|zip|tar|xz|lzma|compress`. See §5 — this is an upstream bug, not
   a mapping artifact on our side.
3. **`creators` / `created_by` are unresolved references.** Both are 47-entry
   lists in which 38 entries are ORCID-only objects (`{"@id":
   "https://orcid.org/…"}`) carrying no name. `created_by` additionally mixes 9
   plain name strings with 38 such objects, so it fails the string/null range.
   **All 38 ORCIDs resolve inside the crate's own graph** — `ro-crate-metadata.json`
   contains exactly 38 `Person` entities with `name` and `affiliation`. So the
   fix is a deterministic in-crate join, no external lookup:

   ```
   https://orcid.org/0000-0003-4060-7360 -> Clark, T    | University of Virginia
   https://orcid.org/0000-0003-4535-3486 -> Parker, J   | University of California, …
   https://orcid.org/0000-0003-4647-3877 -> Al Manir, S | University of Virginia
   ```

4. **Size reduction of `ro-crate-metadata.json`.** It is 12.2 MB but holds only
   62 entities; ~11.9 MB is per-file inventory. The three image sub-crates carry
   `hasPart` lists of **18,789** entries and `EVI#outputs` of **17,849** entries.
   The descriptive payload — name, description, `rai:*`, citation, completeness —
   is a few KB. For generation input, `hasPart`/`outputs` should collapse to
   counts, format distributions, and total sizes.

   For comparison: CHORUS's `ro-crate-metadata.json` is 20 KB with 4 entities and
   empty `hasPart` on its sub-crates.

Also excluded from generation input: the per-modality `ro-crate-preview.html`
files (up to 11.8 MB each, ~46 MB total). They are file listings, not prose.

## 5. Upstream data-quality issues found

Belongs with the CM4AI crate producers, not the input sheet.

1. **`compression`, `format`, and `encoding` hold three byte-identical copies of
   the same 13-item format list**, and `distribution_formats` holds the same 13
   values as `{description: …}` objects. Only `distribution_formats` is
   semantically correct. `compression` is populated with values that cannot be
   compression codecs (`pdf`, `image/jpeg`, `unknown`). This reads as one
   vocabulary being written into four slots.
2. **38 of 47 `creators` carry no name** — ORCID references only. The names exist
   elsewhere in the same file, so any consumer that does not perform the join
   sees an author list that is 81% empty.
3. **Mixed date formats within the CHORUS crate** (minor). The package writes
   `datePublished: 2026-04-03` but `releaseDate: 03/04/2026`, and the EHR
   sub-crate uses `datePublished: 03/04/2026`. The citation ("Apr. 2026") and
   Dataverse both confirm April, so `03/04/2026` is DD/MM — but a consumer
   assuming MM/DD reads March 4. Recommend ISO 8601 throughout.

## 6. Normalizer — built and run

Implemented as `src/data_sheets_schema/rocrate_normalize.py`, exposed as
**`d4d rocrate normalize`**, covered by 12 tests in
`tests/test_rocrate/test_normalize.py`. Both crates now pass
`linkml-validate -C Dataset`.

Outputs land in `{PROJECT}/processed/`, one per fork of the with-crate arm:

| Output | Consumer |
|--------|----------|
| `{PROJECT}_crate_d4d.yaml` | deterministic fork — schema-valid D4D record |
| `{PROJECT}_crate_metadata_reduced.json` | de novo fork — crate JSON-LD, inventories collapsed |
| `{PROJECT}_crate_changes.md` | audit trail of every transformation |

Results:

| | CHORUS | CM4AI |
|---|---|---|
| Changes applied | 2 | 21 |
| Validation | PASS | PASS |
| Metadata reduction | none needed (20 KB) | 12,242,926 → 159,257 bytes (77×) |

Sanity check on the remap: CM4AI's `bytes` → `total_size_bytes` yields 21.9 TB
against the 21.4 TB that cm4ai.org advertises, and CHORUS's yields 1.32 TB
against its own `contentSize: 1.2 tb`. Both consistent.

Re-running over unchanged inputs produces byte-identical outputs (verified by
checksum), so the artifacts are reproducible rather than run-dependent.

### One judgment call worth knowing about

`Creator.affiliations` has range `Organization`, whose `id` is a **required
identifier** — but the crates name affiliations without identifying them
("University of Virginia", no ROR). Dropping the affiliation would discard a
real fact; minting a ROR or GRID id would fabricate one. The normalizer instead
mints a deterministic, obviously-local `urn:d4d:org:university-of-virginia`,
logs it as `mint-surrogate-id`, and states in the report that it carries no
external authority. 12 such surrogates were minted for CM4AI. If you would
rather drop affiliations entirely, that is a one-line change.

## 7. Recommendation for the paired generation runs

The with-crate / without-crate comparison is worth running, but §3's redundancy
test sets the expectation, and it is **not symmetric across projects**:

- **CHORUS should show a real delta.** Its crate content is verifiably absent
  from the document corpus.
- **CM4AI should show close to none.** Its crate restates the Dataverse release
  pages already in the corpus. Treat it as a near-null control rather than a
  second positive case — and if it *does* show a large delta, suspect the
  measurement before believing the result.

Stating this in advance matters: with two projects and opposite predictions, an
aggregate "crates help / crates don't" number would be meaningless.

Proposed normalization step, to write `{PROJECT}/processed/`:

1. Resolve non-schema top-level keys against `Dataset`'s 94 induced slots
   (SchemaView), rather than a hand-maintained list. Two different outcomes:
   - `bytes` **remaps to `total_size_bytes`** (present, range `integer`). It
     carries a real fact — CHORUS's 1319413953331 is the 1.2 TB figure — and
     must not simply be dropped.
   - `format` and `encoding` are **dropped as redundant**: both are absent from
     the schema and both duplicate values already carried by
     `distribution_formats`. No fact is lost.
2. Drop `compression`. It is invalid twice over: the slot is single-valued with
   range `CompressionEnum` (`gzip|bzip2|zip|tar|xz|lzma|compress`), and CM4AI
   supplies a 13-item list of *file formats*. Re-deriving codecs from extensions
   would be inference about files we have not inspected, so drop and log.
3. Join ORCID creator references against the crate's `Person` entities. Note the
   transform is a **rename, not a strip**: `creators` has range `Creator`, whose
   `id` slot is a `uriorcurie`, so `{"@id": "https://orcid.org/…"}` becomes
   `{id: "https://orcid.org/…", name: …, affiliations: […]}` with the name and
   affiliation recovered from the graph. The earlier prototype stripped `@id`
   and discarded the ORCID; that was wrong.
4. Emit a reduced `ro-crate-metadata.json` with `hasPart`/`EVI#outputs`
   summarized to counts, format distributions, and total bytes.
5. Re-validate each result with `linkml-validate -C Dataset`.

**Provenance caution.** `ro-crate-linkml.yaml` is already a D4D-shaped record. It
is upstream-authored, not one of our generated outputs, so it is legitimate
evidence under `.claude/agents/d4d-provenance-guard.md`. But it is close enough
to a finished D4D record that the with-crate arm risks becoming a
copy-through rather than an extraction. Worth deciding explicitly whether the
with-crate arm consumes the crate's LinkML rendering, only
`ro-crate-metadata.json`, or both — the three make quite different experiments.

## 8. Open

- AI_READI and VOICE crate URLs pending.
- `{PROJECT}/processed/` normalization is **built and run** for CHORUS and
  CM4AI (§6); it will need re-running once the AI_READI and VOICE crates land.
- Whether crate-derived sources join `source_manifest.yaml` or stay a parallel
  input set (currently the latter, via `crate_manifest.yaml`).
