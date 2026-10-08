# Legacy Creator assertion preservation

Issues [#4685](https://github.com/bridge2ai/data-sheets-schema/issues/4685), [#4684](https://github.com/bridge2ai/data-sheets-schema/issues/4684), [#4686](https://github.com/bridge2ai/data-sheets-schema/issues/4686), [#4688](https://github.com/bridge2ai/data-sheets-schema/issues/4688), [#4689](https://github.com/bridge2ai/data-sheets-schema/issues/4689) and [#4690](https://github.com/bridge2ai/data-sheets-schema/issues/4690). Implementation baseline: `bd64f1cd3e5646206da43453e862d8aa0a68f93a`, the reviewed UpdatePlan successor subsequently merged by PR #4681. Parent #4594, #2915 and the separate PI-role decision #4449 remain open.

The default legacy TSV now explicitly marks its one `creators <- author` route with `creator_author_literals_v1`. Both real builders wrap each complete string as `Creator.description`; other values are deep-copied intact. The same selected root is used for construction and source evidence. This introduces no people, IDs, affiliations, PI roles, remote reference resolution, name splitting, or semantic-label upgrade.

The full independently reviewed design, including source pins and predicted error counts, is retained in [reviewed_contract.md](reviewed_contract.md), SHA256 `09f30a4e1a242cb82aaa17b6a2224b76c28a2217c22344e406d8336796bf837b`. It is a preimplementation design record, not executed validation evidence. The primary-index refinement below records the subsequent adversarial finding #4686.

## Construction and merge contract

- Exactly one covered, marked `creators <- author` route is allowed. Both loaders check markers before filtering ignored rows. Builders and mergers recheck mutable declarations before resetting state. Unmarked custom mappings and arbitrary historical Func text keep their existing construction.
- Strings retain every character in `description`, including whitespace, newlines and URI-looking text. Lists retain immediate order and duplicate units. Non-string units keep their types and all keys, including false, zero, null inside a list, nested lists and reference objects. No list flattening or key filtering occurs.
- Missing/null root author is omitted; explicit empty lists remain present. Member authors cannot replace missing root assertions. Ambiguous roots still refuse.
- Marked mergers concatenate already constructed units once, in selected-primary then remaining-input order. They do not deduplicate equal strings or dictionaries. An explicitly empty contributing list remains `creators: []` if no source supplies units.
- Marked mergers require an exact integer `primary_index` in `[0, number_of_sources)` before root reads or state changes. Negative, boolean, floating-point and out-of-range indices are refused (#4686). Unmarked historical merge semantics remain unchanged. Their new raw roster normalizes an accepted negative index and visits each selected input once; it does not measure any repeated visits in the historical constructor.
- `get_creator_assertion_sources()` returns a detached marked-only ledger, with raw source facts plus half-open `output_range`. Absent/null/empty sources have zero-length ranges. The list is `None` for unmarked calls, including reuse after a marked call. Contributor names are emitted directly so a source literally named `primary` is not relabeled. Repeated labels remain distinguishable by source index.
- `fields_merged_as_arrays` counts the constructed field once. Dataset key counts and assertion-unit counts never count unique people. The raw-root informativeness scorer and ranking are unchanged.

The TSV still contains 84 CSV-parsed rows, including the ignored Class header: 83 loaded mappings, 82 covered. Only the Creator Func cell changes; original CRLF and other newline bytes are preserved. This table is separate from the maintained interface mapper and its 136-row decision ledger. Its historical `closeMatch`/`minimal` labels are not promoted.

## Public measurements (#4684)

`TransformationResult` adds `coverage_basis` and `source_presence` for both `legacy` and `dataset_v1`, including when `preserve_provenance=False`.

`coverage_percentage` and `unmapped_fields` retain their compatibility names and arithmetic. Their basis is now explicit: `constructed_field_presence`, `non_null_mapped_value`, actual numerator/denominator, `is_source_coverage=False`, and `is_validation_success=False`. The marked-ID exclusion is unchanged. A zero denominator still returns 0.0 with zero numerator/denominator; this does not mean complete coverage.

With marked Creator construction and provenance enabled, optional metadata also contains an independent `coverage_basis` beside its existing numeric copies. Extracting that metadata therefore retains the metric definition. Unmarked data and metadata keep their earlier structure, with the basis available in the outer result. Disabling provenance still disables metadata. `source_presence` is never inserted into Dataset data. Exact-envelope consumers must accept these intentional additive fields; the closed Dataset schema does not change.

Both merge API envelopes additionally return `source_presence` and retain the existing merge report. They do not invent a merged coverage percentage. Batches expose the ordinary per-record diagnostics.

The raw measurement is available for marked **or unmarked** mappings with exactly one covered `creators <- author` route. Other custom or competing routes say `not_measured` with a reason, not author absence. Measured rows disclose selected-root ID, source/processing indices and names, `author_present`, `nonnull`, `immediate_assertion_units` and the exact detached raw value. Missing/null has zero units, a list has its immediate length, and other non-null values have one, including false/zero/blank text. These are source assertions, not unique facts or people. The raw measurement contains no marker mode or constructed ranges, so the same roster compares exactly across marked/unmarked construction.

Source indices refer to the parser list actually passed to the merger, after any API ranking. Processing indices name primary-then-secondary order. `get_source_presence()` returns a detached copy. Reports JSON-escape complete raw text; console summaries may omit that text but retain the measurement basis and counts.

Both legacy CLI/report paths explicitly label their different retained count rule: output-key presence, including null-valued keys. API CLI summaries label non-null mapped values instead. Neither is source coverage or validation success. Validation and the raw author facts are displayed separately. Mapping-table statistics and raw-root ranking retain their distinct existing meanings.

A pure reference assertion can change API construction presence from 0% to 100% when preserved rather than reduced to null. The raw source measurement remains equal, and the resulting unsupported reference still fails the Dataset gate. The meaningful control asserts this exact distinction; it never runs a shadow legacy transformation in production to conceal a changed construction count.

## Publication and retained obligations

File publication still validates exact serialized Dataset bytes with the real schema, independently of optional validators. Unsupported reference/typed units remain visible and invalid. Existing outputs, reports and input files remain protected; a later invalid batch member prevents all publication. The legacy API's embedded metadata remains nonconforming for file publication; `dataset_v1` remains the explicit metadata-separation route. There is no automatic mapper switch or silent field removal.

Requested API output validation selects `Dataset` explicitly for both single and merged results (#4689). `UnifiedValidator.validate_all(..., target_class=None)` keeps its existing generic call and the schema's default class selection; the current schema's tree root is `DatasetCollection`. An explicit keyword selects another D4D class through the existing semantic validator. Raw RO-Crate input validation and the validator's 30-second subprocess bound are unchanged. This repairs the produced-record validation route; it does not disable requested validation or replace the mandatory publication gate.

The completed comparison confirms the predicted literal construction changes for all five retained inputs, both builders and both graph orders. The exact saved result is [comparison.json](comparison.json); the source, test and artifact pins are in [validation.json](validation.json).

| Input | Baseline errors | Candidate errors | Complete literals constructed | Reference errors retained | Dataset gate |
|---|---:|---:|---:|---:|---|
| CHORUS | 30 | 29 | 1 | 0 | Refused |
| VOICE | 150 | 33 | 117 | 0 | Refused |
| CM4AI reduced | 75 | 66 | 9 | 38 | Refused |
| VOICE provenance | 0 | 0 | 0 | 0 | Accepted |
| CM4AI original | 75 | 66 | 9 | 38 | Refused |

The table applies separately to each builder/order: 136 fewer validation messages across its five records, with all 76 reference messages and every unrelated error retained. Across all 20 record runs, both arms have four accepted provenance-only records and 16 refused records. All four complete score/ranking groups match; raw author source facts and all non-Creator record values are unchanged.

All eight mixed-roster merge controls remain refused. They retain 212 immediate assertion units, compared with 165 after the former union deduplication. Their 76 reference errors remain invalid; duplicated source assertions do not count distinct people. Total schema errors change from 216 to 127 for the scorer-selected VOICE primary and from 228 to 139 for the provenance primary. Full non-Creator records/provenance, merge statistics and primary selections match. Complete report differences are limited to the reviewed measurement labels and independently checked author/Creator disclosures, plus captured input paths and generated timestamps. This is a software comparison of mixed inputs, not a scientifically valid merged dataset. Ranked-primary mode retains the original secondary order; it is not a full auto-reordered CLI replay.

References, Person/Organization identity placement, PI selection, other constructors, per-file adapters and semantic labels remain separate work. No historical output is replaced, no rows are retired, and no improved source coverage or scientific acceptance is claimed. Accepted prepared bytes are represented by the supplement's saved byte/hash declarations; the supplement does not retain those serialized bytes for independent reconstruction. Actual CLI publication and refusal behavior is covered separately by the focused tests.

## Validation status

The coordinator's first serialized suite, bound to commit `45fa817cb9a18479800f3539c9205b6e771d7fea`, completed with 846 passed and 7 failed out of 853 tests, with no errors or skips. The preserved `legacy-creator-tests-01.xml` is 193,811 bytes, SHA256 `70870b03f243b257490dc44df2dd5c1097e3496dad1ef7ca835bedf5e3b021e8`, and records 161.053 seconds. The coordinator separately reported 161.14 seconds and 14 dependency deprecation warnings from the console; JUnit does not attest the source binding or warning count.

Six real CLI controls exposed #4689: produced Dataset records were validated against the schema's default `DatasetCollection`, so complete Creator descriptions were rejected. The seventh failure was #4690: an exact merge-envelope test omitted the intentional `source_presence` field. Its corrected expectation keeps exact keys, source-diagnostic equality across result contracts, all existing data/metadata/report checks, and publication assertions. This failed evidence remains distinct from the corrected run.

The corrected candidate `89a9856283c1e5e6ff81758fb423804fdd0a9494` (tree `c50ff4b28634e327d0763ab3cee80d5b5e1d4c2b`) passed **all 886 tests**, with zero failures, errors or skips. The 20-module run includes 91 Creator construction tests, 51 independent adversarial cases, ten validation-target controls, and the existing legacy/profile suites. Saved `legacy-creator-tests-02.xml` is 147,852 bytes, SHA256 `8fd3a6668df63c73e3ff86fc01cf109a710b8ae8fc124add55bdbecafb6b4903`, and records 77.365 seconds. The coordinator separately reported 77.41 seconds and 14 dependency deprecation warnings.

The coordinator subsequently completed the candidate 20-record replay, both supplements and the saved-only comparison. The pre-existing baseline replay is retained unchanged. The optional environment warning, `FAIRSCAPE models not available: No module named 'fairscape_models.rocrate'`, was observed in replay/supplement output; the actual legacy builders, Dataset gate, scorer and merger still ran. No claim of optional FAIRSCAPE model validation is made.

Independent metadata-only checks matched all 30 baseline selected pins to baseline Git blobs and all 52 candidate selected source/test pins to current bytes and tested Git blobs. This includes `src/validation/unified_validator.py` separately from the supplement's narrower 31-file source selection. The complete 21-file tested diff is recorded separately from selected replay-source deltas. All 71 replay pins per arm, 40 individual result files, complete records, raw source disclosures, all 56 gate outcomes and 16 full merge reports were checked without rerunning applications.

The baseline before/after full inventories are identical (9,291 files, 447,277,720 file bytes); the corrected candidate inventories are also identical (9,297 files, 447,375,950 file bytes). Both include hidden/ignored files and permission modes and exclude `.git`. The candidate inventory is 2,182,656 bytes, SHA256 `1ef34614a7ea6284fd7901d6bd5f1bda4ac37af9d544d5ea72a8f5f7c2308cc0`; every candidate entry was independently rehashed before these final notes changed. The baseline inventory equality and selected baseline Git pins were independently checked; this evidence author did not reread the entire baseline working tree.

Runtime disclosure records CPython 3.13.12 and observed PyYAML 6.0.2, LinkML 1.9.3 and linkml-runtime 1.9.4. The actual `linkml-validate` entrypoint identified by the coordinator was independently rehashed after the run: 198 bytes, SHA256 `084b48fea01f3ba0966a0c2de7485c9b1dd5685af4ad26fb2fe5ea4012b582d7`. Its shebang resolves to the same observed Python executable bytes. This qualifies the API subprocess route; it is not an authenticated execution receipt or a complete installed dependency/import snapshot. Public notes omit private host paths.

[replay_supplement.py](replay_supplement.py) and [compare_saved.py](compare_saved.py) are exact copies of the reviewed external utilities used by the coordinator. The latter reads saved evidence only. Full raw records, report bodies and inventories remain external; the bounded comparison result and exact pins are retained here. Only this README and the new final evidence files were added or updated after preservation checks; tested source, tests and mapping bytes remain unchanged.

Independent static review also corrected a CLI test fixture before execution (#4688): the real merge command requires at least two sources. Its control now passes two actual crates and checks both disclosed raw-source rows and the absence of an invented merged percentage. This was a fixture correction, not a production change or an observed test run failure.

Executed focused test modules:

```text
tests/test_rocrate/test_legacy_creators.py
tests/test_rocrate/test_legacy_creators_adversarial.py
tests/test_rocrate/test_legacy_validation_target.py
tests/test_rocrate/test_profile_unavailable.py
tests/test_rocrate/test_legacy_doi.py
tests/test_rocrate/test_legacy_root_identity.py
tests/test_rocrate/test_legacy_root_identity_adversarial.py
tests/test_rocrate/test_legacy_update_plan.py
tests/test_rocrate/test_legacy_update_plan_adversarial.py
tests/test_rocrate/test_legacy_publication.py
tests/test_rocrate/test_legacy_publication_adversarial.py
tests/test_rocrate/test_legacy_result_contract.py
tests/test_rocrate/test_legacy_envelope_adversarial.py
tests/test_rocrate/test_legacy_root_gates.py
tests/test_fairscape_integration/test_d4d_builder.py
tests/test_fairscape_integration/test_mapping_loader.py
tests/test_fairscape_integration/test_rocrate_merger.py
tests/test_fairscape_integration/test_informativeness_scorer.py
tests/test_cli/test_rocrate_transform_mapping.py
tests/test_cli/test_rocrate_transform_mapping_adversarial.py
```

The saved invocation used `PYTHONDONTWRITEBYTECODE=1`, `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`, `PYTHONPATH=src:.`, the selected environment Python `-B -m pytest`, `-q -p no:cacheprovider`, and fresh external `legacy-creator-pytest-02` / `legacy-creator-tests-02.xml` destinations. The exact external command JSON is pinned in `validation.json`, alongside a public symbolic-path command. Commit-to-run attribution and console warnings are coordinator provenance, distinct from JUnit outcomes and independent byte checks. Neither the focused tests nor this five-input comparison resolve the open parent issues.
