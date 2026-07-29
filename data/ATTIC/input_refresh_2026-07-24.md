# Current-release input refresh: 2026-07-24

Follow-up to `input_cleanup_2026-07-23.md`. That audit established that no
distinct historical document was missing from the active corpus, but left three
current-release gaps open: the active inputs described older releases than the
ones the projects now publish. This refresh closes all three additively — no
existing source was replaced or removed.

## Gaps closed

| GC | Gap | Resolution |
| --- | --- | --- |
| AI_READI | Documentation source pointed at dataset v2.0.0 | Added `dataset_documentation_v3` (`https://docs.aireadi.org/docs/3/about`) |
| CM4AI | Current HIGT4C release existed only as a `verification_url` | Added `june_2026_dataverse_release` (`doi:10.18130/V3/HIGT4C`) |
| VOICE | PhysioNet source stopped at 3.0.0 | Added `physionet_3_1_0` (`https://physionet.org/content/b2ai-voice/3.1.0/`) |

Active source counts moved from 29 to 32: AI_READI 7→8, CHORUS 4, CM4AI 9→10,
VOICE 9→10.

## Evidence

### AI_READI

`https://docs.aireadi.org/docs/3/about` returns HTTP 200 and its version
selector defaults to `Dataset v3.0.0`, with v2.0.0 and v1.0.0 offered as older
versions. The page states it documents v3.0 of the dataset and was last updated
2026-06-04. Extraction yields 4,334 characters, comparable to the 4,434 of the
retained v2 page.

The v2 entry is kept because the input sheet still selects it and it remains the
documentation for the v2.0.0 release. Both entries now carry curation notes
saying which is current.

### CM4AI

The Dataverse record for `doi:10.18130/V3/HIGT4C` is fully server-rendered and
extracts to 27,433 characters, comparable to the sibling B35XWX (27,505),
F3TD5R (29,240), and K7TGEM (29,080) records. Official Dataverse API metadata
confirms:

- publication date `2026-06-17`
- latest version `2.0`, state `RELEASED`, release time `2026-07-15T20:28:19Z`
- 10 files, including the three MDA-MB-468 immunofluorescence archives
  (untreated, paclitaxel, vorinostat), APMS and mass-spec archives for KOLF2 and
  MDA-MB-468, two perturb-seq KOLF2 archives, and `cm4ai_release_metadata.zip`

This is the processed current-release record the 2026-07-23 audit noted was
absent. The sheet-selected October 2025 `K7TGEM` release is retained and now
marked as superseded upstream.

### VOICE

`https://physionet.org/content/b2ai-voice/3.1.0/` returns HTTP 200, published
2026-05-01, and extracts to 41,682 characters. It reports 833 participants
across five North American sites and a release-notes entry describing 3.1.0 as
a minor update over 3.0.0: no new participants, additional data for some
participants, repaired parquet files, new audio-quality and per-audio metadata
files, back-filled validated diagnosis information, and some phenotype file
reorganization and gold-standard variable renaming.

This resolves the internal inconsistency in the prior VOICE bundle, where
`docs_b2ai-voice_org_row10.txt` announced "B2AI-Voice v3.1.0 adult dataset ...
now available" while the newest PhysioNet source present was 3.0.0. The 1.1 and
3.0.0 captures are retained; 3.0.0 is now marked as superseded upstream.

## Pipeline state

Raw artifacts were fetched with the pipeline user agent and stored under
`data/raw/{PROJECT}/` using the dated non-sheet naming convention already used
for curated supplements:

- `AI_READI/docs_aireadi_org_docs-3_2026-07-24.html`
- `CM4AI/dataverse_10.18130_V3_HIGT4C_2026-07-24.html`
- `VOICE/physionet_b2ai-voice_3.1.0_2026-07-24.html`

`make preprocess-sources` processed 32 canonical sources with 0 errors,
`make validate-preprocessing` passed with 0 problematic files, 0 missing
outputs, and 0 unexpected outputs, and `make concat-preprocessed` rebuilt all
four project bundles.

## Remaining caveats

- The upstream discrepancies themselves are not resolved: the Bridge2AI GC
  Input Documents sheet still selects AI-READI docs v2, CM4AI `K7TGEM`, and
  PhysioNet 3.0.0. The manifest now records both the sheet selection and the
  current release, with curation notes stating which to prefer. Fixing the
  sheet is an upstream action.
- Current VOICE documentation also advertises a `v1.1.0 pediatric` dataset
  alongside the v3.1.0 adult dataset. That is a distinct dataset rather than a
  newer version of an active source, so it was out of scope here and no
  pediatric source has been added.
- The NIH RePORTER co-investigator roster limitation from the 2026-07-23 audit
  is unchanged.
- No D4D records were regenerated. `data/d4d_concatenated/` and
  `data/d4d_individual/` still reflect the pre-refresh bundles.
