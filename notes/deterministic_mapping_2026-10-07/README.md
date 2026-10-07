# Root-scoped deterministic D4D replay — 2026-10-07

Published from code commit `d6364e58ba77fa975ce594096b11301cd55a68b3`:

- [Static-map label `2026-10-07_ourmap-v3`](../../data/d4d_concatenated/rocrate_static_map/2026-10-07_ourmap-v3/manifest.json): CHORUS, CM4AI and VOICE.
- [Upstream-normalized label `2026-10-07_deterministic-v2`](../../data/d4d_concatenated/rocrate_mapped/2026-10-07_deterministic-v2/manifest.json): CHORUS and CM4AI.
- [Revised fig09](../figures/fig09_mapping_revision_2026-10-07/fig09_crate_vs_generation.png) and [its input/artifact manifest](../figures/fig09_mapping_revision_2026-10-07/manifest.json), comparing these new static records with historical generic-v8 replicate 1.

Every published record passed an actual LinkML validation. All eight prior deterministic-label files retain their exact hashes. Existing figure artifacts and protected worktrees were preserved.

The static mapper now reads the selected crate root, using the metadata descriptor's `about` reference in all three replayed crates. A child Dataset cannot supply a missing root property. This corrects real outputs: CM4AI loses `page` and `download_url`, and VOICE loses `download_url`, because those earlier values came from members. Their removal is a scope correction, not evidence that those source assertions disappeared.

| Static project | Working schema validation | Top-level slots | Added slots | Removed slots |
|---|---|---:|---|---|
| CHORUS | PASS | 34 | `data_governance`, `human_subject_research` | None |
| CM4AI | PASS | 43 | `data_governance`, `human_subject_research` | `page`, `download_url` |
| VOICE | PASS | 47 | `data_governance`, `human_subject_research`, `imputation_protocols` | `download_url` |

The mapping ledger preserves all **136 original rows: 85 active, 19 retired and 32 deferred**. These are execution dispositions, not coverage or quality scores. Runtime reports retain inactive rows and account for the root identifier separately; filled-row totals must not be divided by a reduced active-row denominator and presented as a quality gain. Slot counts above include the root identifier and describe this replay only.

Source sidecars preserve assertions and their scope, including member assertions that no longer populate the root. Governance literals enter `DataGovernance.description` without turning a named person into a committee. Human-subject fields retain labeled statements; explicit Yes/No values can support a boolean, while exemption text, an IRB name or a protocol ID does not establish approval or compliance. Imputation reads the canonical and legacy properties without silently choosing between conflicting assertions. Parent placement requires explicit Dataset typing and rejects known identity ambiguity and cycles.

These routes leave semantic mapping and information-loss claims unassessed. A preserved source assertion, a successful schema validation and a scientifically supported claim are different forms of evidence. Historical declarations retained on other rows remain subject to [#4039](https://github.com/bridge2ai/data-sheets-schema/issues/4039).

## Replay evidence and reproduction

The completed replay summary records **five successful record validations**: static CHORUS, CM4AI and VOICE, plus upstream-normalized CHORUS and CM4AI. Reversing the actual graph order left all three static records unchanged. The integration suite passed 474 tests. After final review fixes, 102 focused tests passed, and 95 run-discovery/corpus checks passed after publication; a fresh replay again validated all five records without changes to record contents. The manifests separately retain successful validation commands, output and exact published-record hashes.

To reproduce, use an isolated checkout of the code commit above. The working static records can be replayed with `d4d rocrate map --project PROJECT`; upstream records use `d4d rocrate normalize --project PROJECT`. For CM4AI, read only `cm4ai_release_metadata/ro-crate-metadata.json` and `cm4ai_release_metadata/ro-crate-linkml.yaml` from the committed `raw/cm4ai_release_metadata.zip` into that isolated checkout's CM4AI `raw/` directory. Check the archive and member hashes against [the extraction bindings](cm4ai-input-bindings.json); the archive itself is unchanged.

Publish with `scripts/publish_deterministic_label.py` using an unused label, explicit `--method`, repeated `--project` arguments, and `--code-commit`. Render with `scripts/figures/fig09_mapping_revision.py`, explicit packages/static-records directories, `notes/reference_rescore_2026-09-12_cborg_runtime/manifest.json`, an unused output directory and the same code commit. These tools refuse overwriting a completed label or figure directory.

Static sidecars bind the actual five mapper component hashes. Label `code_commit` identifies publication code. The upstream normalizer has no producer-code sidecar; its manifest states that limitation explicitly, while [the retained replay/check receipts](validation.json) record this session's successful fresh normalization. No generative `method_core` or scientific score was invented.

Exact working-record hashes are below. Published records receive new headers and have separate hashes in their manifests.

| Working record | SHA-256 |
|---|---|
| static / CHORUS | `4c89011a146778ff628f1b02dcedc170c605cee0a712179c2138307bde854ee8` |
| static / CM4AI | `ba9f27964ec5a4c8fa55351c6dea86e769a2200f75860626576170d1a14643cc` |
| static / VOICE | `d3569d00027fae07a26facf9256d63978b0f13ab5853e5d7ac73bae9ec6d52f4` |
| upstream / CHORUS | `5042bbab16ce7bf5ba63f28d5c51781ae4985e968389c886a14ea4ac2704a576` |
| upstream / CM4AI | `88d5f5307814b1f4c5ef42cad866a35da9d53c591cc22d3d1a6260ea03f2f2eb` |

## Evaluation holds and remaining decisions

The figure compares the new root-scoped static records with fixed historical v8 replicate-1 records. It is a retrospective record-overlap comparison, not an evaluation of current generation quality or a scientific support score. `generated_only` does not establish source absence. Complete source observations are provided separately in the figure CSV and mapping sidecars.

AI-READI remains held under [#3357](https://github.com/bridge2ai/data-sheets-schema/issues/3357). Human review of applicability annotations under [#2912](https://github.com/bridge2ai/data-sheets-schema/issues/2912) and audit-recall annotations/matching decisions under [#2921](https://github.com/bridge2ai/data-sheets-schema/issues/2921) remains pending before scoring; engineering proceeds without substituting AI review for those decisions.

Deferred policy work remains linked to [#4039](https://github.com/bridge2ai/data-sheets-schema/issues/4039), [#4449](https://github.com/bridge2ai/data-sheets-schema/issues/4449), [#4046](https://github.com/bridge2ai/data-sheets-schema/issues/4046) and [#4047](https://github.com/bridge2ai/data-sheets-schema/issues/4047). This replay does not resolve those issues or authorize guessed identities, untyped relationships, or unsupported scientific interpretations.

The review loop filed and addressed [#4582](https://github.com/bridge2ai/data-sheets-schema/issues/4582), [#4583](https://github.com/bridge2ai/data-sheets-schema/issues/4583) and [#4584](https://github.com/bridge2ai/data-sheets-schema/issues/4584). Integration of this standalone revision into the held figure set remains explicitly tracked by [#4385](https://github.com/bridge2ai/data-sheets-schema/issues/4385). Parent [#2915](https://github.com/bridge2ai/data-sheets-schema/issues/2915) remains open for disposition of its linked follow-ups.
