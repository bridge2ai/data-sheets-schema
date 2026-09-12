**Rubric10 semantic scope alignment — 2026-09-11 Pacific (#158)**

The comparison uses main `e42db7229c32e2fea57a23e884277f78115d8195`,
`data/rubric/rubric10.txt`, and the current Dataset schema. The six heading
differences were real, but whole-file field presence overstated alignment:
four of those items omitted part of the source item's evidence scope.

| Item | Prior scope | Revised scope |
|---|---|---|
| E2.2 | Regulatory restrictions, confidentiality, HIPAA and other compliance | Also assess the responsible governance committee's contact information |
| E5.3 | Variables and tabular flag | Also assess dataset split and subpopulation flags |
| E5.5 | Anomalies, sampling and missing-data documentation | Same evidence scope; source heading restored |
| E6.5 | Derivation, release notes and raw sources | Same concepts and source heading; release notes located through current schema paths |
| E8.5 | External resources and conformance | Also assess imputation protocols, including explicit non-use |
| E9.5 | Ethical review and conflicts | Also assess downstream social impacts and mitigations |

The additional fields already appeared in other items. That did not make
them part of these four scores. All fifty item names now match the source
verbatim and every source concept has a declared evidence path under its
own item. Rubric20's twenty names and per-question fields remain aligned;
its definition is unchanged.

**Schema mapping audit**

The source rubric's leaf names are retained as concepts, with these explicit
mappings in the semantic agent. They are not a change to the source rubric
or an instruction to award a point merely for field presence.

| Source or previous spelling | Current evidence location |
|---|---|
| RRID / `rrid` | An RRID value in Dataset `id` |
| `confidentiality_level`, `hipaa_compliant`, `other_compliance` | Members of `regulatory_restrictions` |
| `governance_committee_contact` | `data_governance.committee_contact`; the deprecated regulatory-restrictions member remains accepted for older records |
| `format`, `media_type` | Members of `distribution_formats` or `file_collections.resources` |
| `encoding` | `file_collections.resources.encoding` |
| `vulnerable_populations` | `at_risk_populations` |
| `reidentification_risk` | `participant_privacy.reidentification_risk` |
| `DataSubset.is_data_split`, `DataSubset.is_subpopulation` | `subsets.is_data_split`, `subsets.is_subpopulation` |
| `release_notes` | Release-specific `updates.update_details`, `updates.description` or `notes`; unrelated notes do not qualify |
| `software_and_tools`, bare `used_software` | Software attached to processing properties, or the existing named-tool evidence alternatives under E8.4 |

Ten previous Fields entries could not resolve from Dataset (including
repeated `format` entries). The revised declarations all resolve. The
cross-field rules also now use actual human-subject, consent,
deidentification and funder paths. The low-score ethics example grounds
applicability in E1 and scores other E4 items separately, consistent with
the existing per-item and anti-circular rules.

The existing integer score scale, N/A encoding, denominators, independent
evaluation rule, and E8.3/E8.4 applicability and processing-role thresholds
remain in force. A false split/subpopulation flag is not missing evidence.
Tests cannot establish how consistently a model will apply these rules;
the canary and repeatability ratings still have to be performed.

**Instrument boundary and preservation**

This is an instrument revision, not evidence that earlier scores would be
unchanged. The previous rubric10 definition SHA256 was
`70a50310b9ec717981fc089d8fedb20ea8c3ca3b665870f8d1d2d2573c9fccdd`.
The first alignment manifest was registered after committing the
new definition at `ed07f6952f16438acd9e2f4f9ebd6d9e4de545ab`, with its new
hash and a discriminating check-echo preamble. The new definition SHA256 is
`00b2f03d183d8f9105de8dc10346b2ee67d32376830243f1ec19348ceb8528db`.
The previous manifest is retained byte-for-byte in its registrations directory;
the plan retains that instrument boundary. The review correction below
supersedes this initial alignment registration before any evaluation.

All 24 selected v7/v8 records, 202 prior evaluations, rubric20, rubric
texts and output schemas are preserved. No old score is relabeled as a
result from this definition. The planned cohort remains 48 primary ratings
and 8 additional rubric10 repeatability ratings, beginning with CHORUS v7
rep1 rubric10. No evaluator is run by this change, and no repeatability
estimate or canary success is claimed.

**Verification**

The regression checks compare each item with its source name and fields,
resolve all declared paths, and recreate the original defect by removing
an item's field while leaving it present elsewhere. They also reject a
field mentioned only in an example. Before the fix, the new suite failed
15 checks. Existing schema, semantic-contract, pin and reference-runner
checks are included in the focused validation.

The full evaluation test directory plus agent-pin and reference-runner tests
passed 490 checks locally (excluding corpus walks), with one dependency
deprecation warning.

An offline challenge replay accepts the revised definition's full sentence,
rejects the prior definition, and rejects copying only the preamble. This
tests the stale-definition guard; it is not a live evaluator result.

**Adversarial review**

The first Codex plugin review found two issues, filed as #1283 and #1284.
E6.5 now names the dedicated `updates.update_details` field, with a fixture
where that is the sole source of release history. Funding consistency is
conditional on grant funding and accepts structured awards or awards in
funder descriptions/notes; donated cloud services and device loans do not
require a grant number. The affected alignment, pin and runner tests passed
114 checks after these corrections. The verbatim review is retained in
`notes/rubric10_alignment_codex_review_2026-09-11.txt`.

The current reference manifest pins the corrected definition commit
`f7f235a9706a741f4a02c01211e4d5c948e89b0f` with SHA256
`66ad623121272099bf94535ae5be2163a5f5005fe895d2bf2bf04c4f90e34864`.
Its registration is dated `2026-09-12T02:40:38.941527+00:00`; the previous
alignment manifest is archived byte-for-byte before replacement. The new
offline echo replay and unchanged-input checks are recorded in
`notes/reference_rescore_2026-09-11/rubric10_alignment_review_registration.json`.
