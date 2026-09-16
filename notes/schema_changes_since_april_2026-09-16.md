**Schema changes since the April 2026 generation — reviewed September 16, 2026**

**The next API and native agentic generation is not ready to be designated final.** The schema has meaningful additions and compatibility changes since April. Current code can prepare both arms, but the latest CHORUS canary stopped during audit, source-quality acceptance remains outstanding, and this review found two issues to settle before freezing the final schema. This report starts the final-release review; it does not admit a paid run.

The detailed [comparison and validation evidence](schema_changes_since_april_2026-09-16/evidence.json) and [reproduction script](schema_changes_since_april_2026-09-16/compare.py) accompany this report. Historical records, schemas, registrations, scores and source downloads were read without alteration.

**Which April version?** Git identifies two useful checkpoints:

| Checkpoint | Exact revision | Meaning |
|---|---|---|
| April 10 generation | [`9912ac237`](https://github.com/bridge2ai/data-sheets-schema/commit/9912ac2379b1a5b747c6b3941a32a18968dbd07d) | Regenerated AI_READI, CHORUS, CM4AI and VOICE full records, and generated four separate core records. |
| April 28 poster checkpoint | [`e141852f5`](https://github.com/bridge2ai/data-sheets-schema/commit/e141852f532e6a0cea47992ffe9afc0f20a7c6a5) | Last poster-era main checkpoint before July development; includes the April 24–28 exchange mappings and renderer guidance. |
| Reviewed current main | [`a9c8bc05f`](https://github.com/bridge2ai/data-sheets-schema/commit/a9c8bc05f1353206733afca207c80085547c1700) | September 16 comparison target, after the CI optimization. |

The April generation was not a separately tagged April release in the repository's published release list. The [0.1.1 release](https://github.com/bridge2ai/data-sheets-schema/releases/tag/0.1.1) was published February 6. Package/release tags, schema versions and generated-D4D condition labels are different identities; this report uses exact commits instead of assigning an invented April version.

Between April 10 and April 28, the effective full/core classes, root fields and enum members did not change. That interval added documentation examples, section/subtitle guidance and mapping refinements: the grantor and license/use-terms properties received D4D-specific URIs with broader external mappings. Those are semantic/documentation changes even though the eight April records still validate. The larger representation changes below occurred after the poster checkpoint.

**Measured schema scope.** Counts resolve imports and inheritance from the source entry points. A root field is one property on `Dataset` or `CoreDataset`; it is not every nested field or an exchange-mapping row.

| Measure | April full | Current full | April core | Current core |
|---|---:|---:|---:|---:|
| Root fields, including inherited fields | 94 | 98 | 79 | 84 |
| Classes in imported schema closure | 78 | 79 | 76 | 77 |
| Enums in imported schema closure | 17 | 18 | 15 | 16 |
| Permissible values across those enums | 210 | 242 | 191 | 223 |
| Declared entry-point schema version | unset | 2.0.0 | unset | unset |

The "current" columns describe `a9c8bc05f`; the release that followed this review declares `3.0.0` on both entry points ([schema release 3.0.0](schema_release_3.0.0_2026-09-16.md), #1874).

Both April checkpoints have the same counts. The new class is `DataGovernance`; no existing class or root field was removed. Full adds `conforms_to_standard`, `data_governance`, `notes` and `source_caveats`. Core adds those four plus `related_datasets`. Nested additions and inherited changes are enumerated in the evidence. Imported-class counts include supporting definitions, not just classes reached by a particular record.

Twenty-two schema-directory files changed: seventeen existing source files, two new supporting schemas, a new digest inventory, and the two generated merged schemas. Comparing parsed source files, including that inventory, gives 375 change entries from April 10 to current. An entry can be an entire added definition or a changed property, so this is an inventory size, not a count of independent features. Large line counts in merged schemas mainly reflect generated expansion and should not be reported as thousands of new fields. The existing “95 fields / 284 attributes” prose describes a different historical exchange inventory and is not interchangeable with the measured root-field counts above.

**Changes that matter to generation and downstream consumers.**

| Change | Practical effect on the new D4Ds |
|---|---|
| Narrative lists became scalar strings. | Sixty-five source attributes lost `multivalued: true`, across generation and evaluation-summary modules. Examples include sampling strategy, preprocessing/cleaning detail, ethics-board detail, license terms, retention and update detail. Generators must use scalar narrative text, often a YAML block scalar; old lists can now fail validation. This is a representation change, not permission to omit documented facts. |
| Organization and grant identifiers became optional. | `Organization` and `Grant` no longer inherit the required identifying field from `NamedThing`; their explicit `id` is recommended. `Grantor` inherits the relaxed organization contract. Missing source identifiers no longer force invented IDs. `FundingMechanism.grantor` and `EthicalReview.reviewing_organization` became strings. |
| Person references became inlined objects. | Principal investigator and contact fields now require a `Person` object, including its required identifier, rather than a bare name/reference string. This covers creator, ethics, license, deprecated governance contact and the new governance contact. A final generator must follow the current shape and identifier guidance. |
| Governance and stewardship became first-class data. | `DataGovernance` adds committee name, members/contact, access review, timing, appeals, stewardship roles and accountable organization. Full and core can carry the object. The old regulatory committee-contact field remains deprecated; it was not silently removed. |
| Distribution properties and data standards became explicit. | `DistributionFormat` gained download URL, serialization format, media type and checksum. Core distributions can retain `conforms_to` and controlled `conforms_to_standard` values. `DataStandardEnum` adds ten standards, distinct from file serializations such as CSV. Dataset/data conformance, metadata-schema conformance and metadata-class conformance are documented separately. |
| Dataset relationships and file collections changed. | The relationship vocabulary adds 22 values and DataCite aliases/mappings for existing values; core now retains typed related datasets. `FileCollection.resources` changed from an ineffective Dataset/union definition to `File`. Its `collection_type` became scalar. Consumers should not infer unchanged nested shapes from unchanged root-field names. |
| Source limitations have a structured place. | `notes` and `source_caveats` propagate through shared classes. These support otherwise unmodeled facts and source contradictions/uncertainty. They do not replace source support for a populated field. Retention incentives and their rationale have separate compensation fields. |
| Identifier, checksum and vocabulary guidance tightened. | DOI strings must match the whole anchored bare-DOI pattern; URL-shaped DOI values no longer pass by substring. ROR, ORCID and DOI prefixes are explicit; B2AI registry prefixes were corrected. The legacy `md5` field remains but is deprecated in favor of `sha256`. `VariableMetadata.unit` accepts strings. Topic guidance explicitly permits GO/MeSH/EFO/NCIT terms alongside registry terms, while substrate guidance retains its distinct scope. |
| Examples and human-readable guidance changed. | April introduced many examples; later changes replaced some real identifier examples with placeholders and clarified representations and allowed term sources. Guidance affects model behavior even when JSON Schema validation is unchanged, so its bytes belong in the generation instrument identity. Residual study-specific schema examples remain, as documented below. |
| Operational schemas and digest history were added. | `d4d_generation_record.yaml` and `d4d_run_telemetry.yaml` describe provenance/accounting contracts, not new fields required in a dataset's full/core YAML. `digest_inventory.yaml` is a digest-to-slot history file, not a LinkML schema. `D4D_Evaluation_Summary.yaml` also changed separately and is not imported by the two generation roots. |

The major compatibility boundary began with [schema 2.0.0 on August 6](https://github.com/bridge2ai/data-sheets-schema/commit/52a0e1732), followed by [remaining narrative scalarization](https://github.com/bridge2ai/data-sheets-schema/commit/4d2232560), [governance](https://github.com/bridge2ai/data-sheets-schema/commit/d740cc15c), [data-standard vocabulary](https://github.com/bridge2ai/data-sheets-schema/commit/ea12521a2), [anchored DOI validation](https://github.com/bridge2ai/data-sheets-schema/commit/9f2339746) and [Person inlining](https://github.com/bridge2ai/data-sheets-schema/commit/816b44025). These later changes retained the `2.0.0` label.

**Compatibility of the actual April outputs.** Validation used the original bytes at April 10, not today's files with the same names. All eight have unique YAML mapping keys and pass both April schemas under the same current compiler. Against current schemas:

| April record | April 10 schema | April 28 schema | Current schema |
|---|---|---|---|
| AI_READI full | pass | pass | 9 errors |
| CHORUS full | pass | pass | 22 errors |
| CM4AI full | pass | pass | 15 errors |
| VOICE full | pass | pass | 3 errors |
| AI_READI core | pass | pass | 2 errors |
| CHORUS core | pass | pass | pass |
| CM4AI core | pass | pass | pass |
| VOICE core | pass | pass | pass |

Counts are top-level JSON Schema validation errors; nested `anyOf` causes are preserved in the evidence. The observed failures are narrative arrays where the current definitions require scalar strings, including arrays nested in ethics, license, retention and update objects. Person inlining and the other compatibility changes remain relevant even though they are not needed to explain these eight records' failures. This check establishes neither factual accuracy nor completeness, and does not retroactively overturn a historical validation verdict.

For example, April accepts `preprocessing_details: ["step one", "step two"]`; current requires scalar text. If migration is needed for tooling, create a separately identified derived copy and retain its source/migration identities. Do not overwrite the April record or silently reuse its score as a current-instrument score.

The generation design also changed independently of the schema: April generated core records separately; the [August 27 change](https://github.com/bridge2ai/data-sheets-schema/commit/1c78625fe) derives core deterministically from the audited full record. Both final arms should therefore produce a full record and its derived core, with pair/derivation checks. Comparing the April independently generated core against a current derived core confounds workflow and schema changes unless the manuscript names both.

**Findings before the final freeze.**

1. [#1874 — Give full/core a distinct release identity](https://github.com/bridge2ai/data-sheets-schema/issues/1874). Full still says `2.0.0` despite later structural changes; core has no declared version. Hashes already distinguish registered instruments, so this is not a hash/provenance collision. A final release needs an explicit compatibility identity, migration notes and regenerated artifacts; the manuscript must name the exact schema revision/hash in addition to a version label.
2. [#1875 — Remove study examples from shared generation schemas](https://github.com/bridge2ai/data-sheets-schema/issues/1875). Under `D4D_PROFILE=neutral`, the native executable playbook still selects merged schemas containing AI-READI title examples and an AI-READI/Bridge2AI-Voice committee description/example. The [offline probe](schema_changes_since_april_2026-09-16/neutral_native_probe.json) confirms the selected paths and bytes. The playbook forbids copying examples as facts, so this is evidence of study content exposure, not a demonstrated hallucination. It nevertheless falls short of the requested shared pipeline without hardcoded GC content. Stable schema namespace URIs identify the schema and should be retained. Related residual agent examples are tracked separately in [#1611](https://github.com/bridge2ai/data-sheets-schema/issues/1611).
3. [#1849 — Interrupted CBORG streams](https://github.com/bridge2ai/data-sheets-schema/issues/1849) remains open. The latest v10p attempt generated an initial full/core pair but stopped before a completed audit; provider “empty success” records do not establish a complete usable response. Accounting has been reconciled. Transport evidence and any upstream explanation are separate from scientific acceptance.
4. [#1815 — Wrong source-document attribution](https://github.com/bridge2ai/data-sheets-schema/issues/1815) and [#1782 — Planned claims reported as current](https://github.com/bridge2ai/data-sheets-schema/issues/1782) remain open pending independent acceptance of a fresh, unchanged canary. Passing schema, pair or lexical receipt checks cannot establish those claims' truth.

The new profile system supports neutral term-source guidance and explicit study vocabularies. That is a real generalization improvement over April and the September 11 review; it is not proof that every active resource is study-free or that an external generation is already accepted. Kids First remains the external biomedical test, with its captured participating-study documentation and the registered metadata/abstract-only limitation for the nominated paper.

**Ordered path to the final candidate.**

1. Resolve the schema identity and active study-content findings; complete the transport investigation/diagnostic work. Review the combined changes and freeze code, full/core schemas and compiler, profiles/vocabularies, prompts/digests, native runtime, source bundles/chunk manifests, CBORG route/settings, output paths and financial controls in a fresh condition. A moving `main`, `latest`, or `2.0.0` label alone is insufficient.
2. Admit one costed CHORUS API canary, review its unchanged original/final full/core pair, audit, source support and qualifiers, receipts, provenance and report. After acceptance, run matched CHORUS native, then Kids First API and native, accepting each before continuing. Keep existing downloads and all stopped/rejected identities; no automatic paid retry is admitted by this report.
3. On accepted outputs, run separately registered evaluation canaries: both semantic rubrics and repeat ratings, both offline presence rubrics, direct API quality, field-agent styles, and applicable grounding, fitness, subtype, provenance, receipt and report checks. Pin definitions and applicability; verify evaluator preamble/check-echo and record quoted definition hashes. One passing rating does not establish repeatability.
4. Cost and register the production cohort for both arms using accepted canary usage. The retained proposal is five Bridge2AI datasets including distinct VOICE_PEDIATRIC, three replicates and two arms, plus Kids First once per arm: 32 full/core pairs. It also proposes 256 rubric ratings and 128 offline presence scores; additional paid styles still need explicit counts and cost. This is a proposed workload, not authorization to exceed existing caps.
5. Publish the accepted cohort under its new version/condition. Preserve April, v7/v8, historical v9 and every later attempt and score. Compare matched evaluation instruments for the manuscript, disclose schema/workflow/source differences, and adjudicate disputed historical judgments separately. A content migration alone cannot supply newly modeled source facts.

The [current continuation plan](matched_cborg_continuation_canaries_2026-09-15.md) and [v10p outcome](matched_cborg_2026-09-15_v10p/CHORUS_api_stopped.md) give the preceding scientific state. The registered native arm uses Claude Code plus repository CLI through CBORG; Aurelian is not an execution dependency. This schema report makes no claim that the final cohort or reference rescore has run.

**Reproduction and limits.** From a checkout containing the three pinned commits, run `PYTHONPATH=src poetry run python notes/schema_changes_since_april_2026-09-16/compare.py`. The script extracts schemas to temporary directories and writes only its evidence JSON. It inventories parsed source changes separately from induced class fields, hashes all schema files and the original records, compiles both roots and performs 24 historical-record validations. It does not load credentials, call a model or download sources.

The recorded toolchain is LinkML 1.9.3, LinkML Runtime 1.9.4, jsonschema 4.25.1 and PyYAML 6.0.2. Using the same compiler isolates schema-definition differences; it does not recreate April's runtime. JSON Schema validators are closed, include class descendants and check formats; YAML dates become ISO strings consistently. This is a structural review, not a full rerun of term validation or semantic source review. Inherited field changes repeat for each affected class and must not be mistaken for independent source edits. The raw-source inventory also covers class/module metadata omitted from induced-field comparisons. The ignored-inclusive content search covered source schema files and the selected native resource paths; corpus archives and unrelated local work were preserved.

The separate [neutral native probe](schema_changes_since_april_2026-09-16/probe_neutral_native.py) runs against the checked-out runtime, rather than extracting historical code: `PYTHONPATH=src poetry run python notes/schema_changes_since_april_2026-09-16/probe_neutral_native.py`. Its schema hashes match the current snapshot in the comparison evidence. Run it at the reviewed revision or an otherwise unchanged runtime to reproduce this finding.
