# Generality G1 round 2: P4a findings 1, 4 and 5 (2026-10-30)

Base: `55c7b94b838eb500888055da5a47acf2ee9e2e15`. Implementation head: `d67aeaafe5e13ebee4d02e1164ec01f128e448ce`.
This report's later evidence-only commit does not change any captured runtime input.

## Method and limits

Offline CHORUS shared-generation-v1, renderer 25, playbook 2, receipt policy 2;
the same `chorus` partition and `2026-10-30_g1-rereview-proof` registration label
as the independent re-review. Canonical bytes use `shared_generation.canonical`
(sorted keys, compact separators, UTF-8). No provider, token counting endpoint,
run directory, ledger, canonical pin or archive was written.

The reviewer's `capture_requests.py` and `diff_payloads_fast.py` are retained in
`scripts/adhoc/generality_g1_round2/`; capture is extended for the missing phases.
Both versions run in the **same** `.g1-round2-evidence/snapshot` path, with the
same fixture path. The base materializes tracked runtime inputs from local Git;
the head uses the corresponding worktree files, whose committed hashes are
checked here. Archived 2026-10-22a CHORUS intermediates are read from their original location.
Absolute path lengths differ from the prior review, so absolute totals differ;
within this experiment all locations are fixed. `unused-output` does not exist
after either capture, and both error dictionaries are empty.

Receipt completion uses `receipt_completion.build_request` on archived
`CHORUS_receipt_completion_inputs.json` (SHA256
`c6e95136fb168adefa296e06cfeac55e9057d1fc96dedad011db405231280fec`). Record, receipt, manifest, bundle and
assistant response are held fixed. The preceding full request's system,
messages and cached blocks, schema capture, receipt registration identity and
output cap are rebuilt at each revision, as the runtime does. An unchanged
archived transcript alone would measure historical replay rather than the new
condition. No new assistant output is synthesized.

Both report variants use the runtime's `build_phase('report')` path.
`report_regate` also uses `_append_regate` with the archived report and a fixed
empty contradiction list. `report_after_repair` uses the fixed archived reconciled
record carries. These measure renderer bytes offline, not a claim that a
repair/regate was triggered or that a provider accepted these requests.

## Complete phase table

| Phase | Base bytes | Head bytes | Delta | Status |
|---|---:|---:|---:|---|
| `full` | 227,890 | 228,025 | +135 | measured |
| `full_receipt_completion` | 306,441 | 306,576 | +135 | measured |
| `reconcile_full` | 467,263 | 467,587 | +324 | measured |
| `report` | 589,829 | 590,153 | +324 | measured |
| `report_after_repair` | 589,829 | 590,153 | +324 | measured |
| `report_regate` | 751,068 | 751,392 | +324 | measured |
| `typed_audit_omission` | 598,497 | 598,875 | +378 | measured |
| `typed_audit_worker:worker_0001` | 353,386 | 353,386 | +0 | measured |
| `typed_audit_worker:worker_0002` | 352,447 | 352,636 | +189 | measured |
| `typed_audit_worker:worker_0003` | 346,581 | 346,581 | +0 | measured |
| `typed_audit_integration` | — | — | +189 expected | Responses from every worker and omission are required; unavailable in this offline capture. Same Instance schema context. |
| `repair_full` | — | — | — | Not applicable: no validation-failure repair request in the selected fixed carries. |
| `full_readdress` | — | — | — | Not applicable: no new receipt-path correction is invoked in this capture. |
| `core`, `reconcile_core`, `repair_core` | — | — | — | Not applicable: deterministic derivations, no provider request. |
| legacy `audit` | — | — | — | Not applicable: shared-v1 uses the typed worker/omission/integration roster above. |

The full/receipt +135 digest insertion is **record-independent**. The schema
context's +189 description component appears where the record has an **Instance
owner**, including when `data_substrate` is absent. A worker retains this
description for each worker assigned a **`data_substrate` leaf**. The worker
number is specific to this packet, not a rule for future records. Omission
contains the description twice (outer schema context and inner typed request).
Fixed-width schema/binding hash substitutions contribute zero net bytes.
Actual later-phase sizes and worker rosters remain record-dependent.

## Finding 4: schema and derived artifacts

Only the first sentence in `D4D_Composition.yaml` changes from G1's prior head:

> Type or format of data (e.g., raw text, images): an EDAM Data or Format term or an IANA media type, written as a CURIE with the schema's declared `EDAM` or `mediatypes` prefix, when the documents supply one; or a term from the selected profile's pinned standards registry.

The rest of the description and the digest template are unchanged. The sentence
adds 100 bytes to G1's previous description (+189 from step 0).
`make regen-all gen-core-schema gen-sssom-comprehensive gen-sssom-uri-comprehensive`
regenerated the products; 3.1.0's unreleased hashes were updated in release history.
Older release entries are unchanged. The OWL graph has 7,759 triples in each
version, with precisely one definition replacement (7,758 common triples).
The two 301-row SSSOM tables retain identical mappings; only mapping dates and
the substrate-description excerpt change. JSON-LD generation metadata also
reflects regeneration.

- 3.1.0 full merged SHA256: `9a821e6a08e8fe8c6b0e2fd1d4bef9e5d4ee3740722b81ab7620c315287bc8da`.
- 3.1.0 core merged SHA256: `2bb8827c45a4dac40e834064a65c95cfc13d258b129c3aa1b9cbccba9ef624db`.

Registration request-code hashes changed at these paths from step 0:

- `src/data_sheets_schema/api_runner.py`: `814c1d7c9736b6956deb0cb1f964435f928dc9617b4c46b11f1abef6003169da` → `489b7bd38dfb83a14f7ec41708037cab4e1bbeb72d967f843cf2ec55472ba12e`.
- `src/data_sheets_schema/profile_identity.py`: `5fb08098439b17e72b7a9ab5529b2fe0e700d1d3d1fcedc0ecbd8b9c1b5ab3a6` → `496f4c3d623dec5d1e05c65c9299505dd445f1b27a607265413165a54916312a`.
- `src/data_sheets_schema/profiles.py`: `f461414f7e035c5502c4312ea819fcc2b45c4eabb8fef18de8e791fe27061909` → `a36848bfbad70c5a42ad1d8a94b213b8019b222ae686ebd7e12b125782ad67fd`.
- `src/data_sheets_schema/provenance.py`: `e5a1f5acfae1cf544c7f90ef7ecd373a3b4eaac9bf9fcb0eabdbff7d0f103b4e` → `70091bb79bb74904cb20b5458704d21e7278a6c146897e091aed027894684ffe`.

Actual worker assignments (all workers retained):

```json
{
  "typed_audit_worker:worker_0001": {
    "assigned_leaf_count": 35,
    "data_substrate_leaves": []
  },
  "typed_audit_worker:worker_0002": {
    "assigned_leaf_count": 54,
    "data_substrate_leaves": [
      "/instances/3/data_substrate"
    ]
  },
  "typed_audit_worker:worker_0003": {
    "assigned_leaf_count": 9,
    "data_substrate_leaves": []
  }
}
```

## Finding 5: historical code evidence

`PROFILES_INTRODUCED_COMMIT` is
`e78e4bb5699af0ecaca28cdc5c328e5c908ae959` (#628/#1302).
Explicit profiles still win. Otherwise locally resolved `repo.commit` ancestry
wins over the execution date: non-descendants read as historical bridge2ai;
profile-aware code reads as neutral. Missing, malformed, shallow-negative or
unavailable ancestry is not silently classified using a date.

The corpus also contains old squashed/deleted commit identities. A missing
object can be established as historical only by an exact `repo.commit` in a
generation or derived provenance record already present in the introduction's
parent tree. This uses immutable retained evidence, not today's record or its
date; a hash merely mentioned in prose is insufficient. There is no per-project
or per-hash exception list. Dates are used only when no commit is recorded.
Records with neither a commit nor a valid date still refuse.

Tests cover old code executed today and `profile_assessment == match`, explicit
profiles, introduction/descendant code with an old date, no-date historical
code, malformed/unresolvable hashes, unavailable checkout, shallow history,
retained generation/derived witnesses and incidental hash mentions. A direct
offline probe also checks the actual `a2a3e157b` with a current date.

The reviewer's 286-record corpus sweep is byte-identical before/after, including
reader results, profile identity, warnings and failure details:
`f02163f3d64bd73a712c9712673010dbe66bc2e80af3d35d9af6f767fced5d92`.

A second probe changes only the date of a real v8 provenance record in memory; the source file is never written. Its full assessment stays unchanged, with no profile-identity findings. Its existing unreproduced digest stays unknown (the synthetic regression separately verifies a digest match):

```json
{
  "source": "data/d4d_concatenated/claudecode_api_core/2026-09-04f_claude-opus-5-api-generic-v8_rep2/CHORUS_provenance.yaml",
  "source_sha256": "fde00d1d09ce32b874e6de4bffebde97b2077a725da670ee3474df0df1cc7eba",
  "commit": "a2a3e157b610177db7c1ced91ca30c15ff5d96b9",
  "current_date": "2026-10-30T12:00:00Z",
  "problems": [],
  "status": "unknown",
  "effective_profile": "bridge2ai",
  "unchanged_assessment": true
}
```

## Validation

Python `3.13.12`; LinkML `1.9.3`; linkml-runtime `1.9.4`. Local serial runs in CI’s tests/ scope (CI itself uses Python 3.12); provider keys unset, network guard/dead proxies, basetemps under d4d-executions.

- `canary-final`: exit 0; {'tests': 26, 'failures': 0, 'errors': 0, 'skipped': 0}; 17.7s.
- `schema-canary`: exit 0; {'tests': 5, 'failures': 0, 'errors': 0, 'skipped': 1}; 7.3s.
- `fixture-canary`: exit 0; {'tests': 137, 'failures': 0, 'errors': 0, 'skipped': 0}; 17.1s.
- `focused-final`: exit 0; {'tests': 1405, 'failures': 0, 'errors': 0, 'skipped': 1}; 1473.8s.
- `collect-final`: exit 0; {'tests': 0, 'failures': 0, 'errors': 0, 'skipped': 0}; 41.0s.
  21050 tests collected in 39.47s; zero collection errors.
- `shard-1`: exit 1; {'tests': 3119, 'failures': 0, 'errors': 24, 'skipped': 12}; 6420.4s.
- `shard-loopback-canary`: exit 0; {'tests': 1, 'failures': 0, 'errors': 0, 'skipped': 0}; 5.3s.
- `shard-loopback`: exit 0; {'tests': 24, 'failures': 0, 'errors': 0, 'skipped': 0}; 46.1s.
- `d4d schema check-digest --strict`: both merged schemas in sync, exit 0.
- `make check-sync check-sssom-comprehensive`: pass; existing alignment warnings remain visible.
- `git diff --check`: pass.

The initial shard had 24 setup errors because the sandbox refused binding the tests’ fake HTTP servers to `127.0.0.1`. No external endpoint was involved. After the shard completed, one selected test was run as a canary outside that socket restriction, then all affected nodes were rerun serially through the same launcher, with provider keys unset and the external socket/DNS guard intact. The canary and all retry nodes passed. The canary also retained its non-empty relocated index, after checking two synthetic deliveries and a captured-only recheck without dispatch. The original shard result above is retained rather than replaced.

Exact retried nodes:

```text
tests/test_evaluation/test_fitness_execution_index.py::test_actual_http_cli_index_relocates_entire_ledger_and_never_dispatches
tests/test_evaluation/test_fitness_execution_index.py::test_failed_transport_or_accounting_cannot_promote_raw_score[http_429]
tests/test_evaluation/test_fitness_execution_index.py::test_failed_transport_or_accounting_cannot_promote_raw_score[truncated]
tests/test_evaluation/test_fitness_execution_index.py::test_failed_transport_or_accounting_cannot_promote_raw_score[unknown_usage]
tests/test_evaluation/test_fitness_execution_index.py::test_real_http_interruption_retains_unknown_and_recovers_only_complete_raw_response[admitted]
tests/test_evaluation/test_fitness_execution_index.py::test_real_http_interruption_retains_unknown_and_recovers_only_complete_raw_response[response]
tests/test_evaluation/test_fitness_execution_index.py::test_real_http_interruption_retains_unknown_and_recovers_only_complete_raw_response[settled]
tests/test_evaluation/test_fitness_execution_index.py::test_portable_index_rechecks_actual_ledger_not_stored_flags[report_flag]
tests/test_evaluation/test_fitness_execution_index.py::test_portable_index_rechecks_actual_ledger_not_stored_flags[unknown_ledger]
tests/test_evaluation/test_fitness_execution_index.py::test_portable_index_rechecks_actual_ledger_not_stored_flags[missing_preceding_settlement]
tests/test_evaluation/test_fitness_execution_index.py::test_portable_index_rechecks_actual_ledger_not_stored_flags[missing_body]
tests/test_evaluation/test_fitness_execution_index.py::test_portable_index_rechecks_actual_ledger_not_stored_flags[unadmitted_gap]
tests/test_evaluation/test_fitness_execution_index.py::test_execution_join_refuses_foreign_descriptor_result_or_report[descriptor]
tests/test_evaluation/test_fitness_execution_index.py::test_execution_join_refuses_foreign_descriptor_result_or_report[standalone_result]
tests/test_evaluation/test_fitness_execution_index.py::test_execution_join_refuses_foreign_descriptor_result_or_report[saved_report]
tests/test_evaluation/test_fitness_execution.py::test_actual_fitness_cli_binding_and_relocated_captured_recheck
tests/test_evaluation/test_fitness_execution.py::test_actual_fitness_strict_rejection_stops_selected_suffix[change0]
tests/test_evaluation/test_fitness_execution.py::test_actual_fitness_strict_rejection_stops_selected_suffix[change1]
tests/test_evaluation/test_fitness_execution.py::test_actual_fitness_strict_rejection_stops_selected_suffix[change2]
tests/test_evaluation/test_fitness_execution.py::test_actual_fitness_strict_rejection_stops_selected_suffix[change3]
tests/test_evaluation/test_fitness_execution.py::test_mixed_success_and_failed_http_retain_assessment_and_usage
tests/test_evaluation/test_fitness_execution.py::test_unknown_cache_usage_cannot_become_accounted_success
tests/test_evaluation/test_fitness_execution.py::test_instrument_swap_and_missing_fitness_identity_refuse
tests/test_evaluation/test_fitness_execution.py::test_captured_ledger_and_admission_cannot_switch_instruments
```

The affected-suite run covered these paths:

```text
tests/test_blind_review_pack.py
tests/test_core_schema_targets.py
tests/test_d4d_full_schema.py
tests/test_d4d_pair_consistency.py
tests/test_digest_isolation.py
tests/test_form_defects.py
tests/test_generality_context.py
tests/test_generality_evaluation.py
tests/test_generality_native_legacy.py
tests/test_generality_profiles.py
tests/test_generality_renderer.py
tests/test_generality_review_followups.py
tests/test_generality_sheet_projects.py
tests/test_generality_substrate.py
tests/test_generality_tuned.py
tests/test_historical_digest.py
tests/test_historical_digest_cache.py
tests/test_historical_profile_identity.py
tests/test_historical_profile_inventory_cache.py
tests/test_neutral_generation_schema.py
tests/test_pair_cli_recorded_digest.py
tests/test_profile_review_r8.py
tests/test_profile_review_r9.py
tests/test_profiles.py
tests/test_receipt_completion_batch_gate.py
tests/test_receipt_completion_policy.py
tests/test_receipt_completion_runtime.py
tests/test_rereceipt_completion.py
tests/test_review_pack.py
tests/test_review_pack_identifier_basis.py
tests/test_review_pack_schema_refresh.py
tests/test_schema_cache.py
tests/test_schema_cache_invalidation.py
tests/test_schema_digest_cache.py
tests/test_schema_event_replay.py
tests/test_schema_release_identity.py
tests/test_schema_semantics.py
tests/test_schema_snapshot_cache.py
tests/test_schema_snapshot_compatibility.py
tests/test_schema_straddle.py
tests/test_schema_sync.py
tests/test_schema_sync_stability.py
tests/test_schema_view.py
tests/test_schema
tests/test_cli/test_schema_cli.py
```

The broader run uses the actual CI shard plugin, ordinary lane 1/6 and checked-in
duration weights, with one serial pytest controller. The schema/profile canary
and fixture canary passed before the larger runs. They verified local selection,
generated-schema assertions and fixture isolation; they do not claim provider
acceptance, concurrency behavior or live credential coverage.
Tests ran against the uncommitted implementation bytes on `f7fedae48`; the
implementation commits were made after acceptance. This report verifies every
captured request-code and schema hash against the committed implementation
before writing.

A separate read-only adversarial pass checked the final production/test diff,
generated-artifact semantic delta and every changed payload leaf. It found no
additional defect. No remote issue, PR, push or merge was attempted (offline).

## Capture identities

- base capture SHA256 `2e965b8a682011149716d47eef529045cfbb896820a7cb9dad5f50e79707fa9f`; registration `5893eddc65c8cc31e9cf0d30fd8db4fab48333953cf316bbd24de31e197a552e`; packet `fd2ea826263f04af63e62958a2628b98c4c9e2ee245e96841e1aac533a936bf1`.
- head capture SHA256 `12456a8fd08438896821bb0b4154f7c086752573099671a13dc3d451912256bc`; registration `94e4c9224a988d917b7c3995ff1c8ac7e15d99715dc72ce9a882802aa56dacfa`; packet `950b4f6a982a05a397ab50b920687cf23d0d5ddbe9ea9162342ab165b3dcea37`.

## Every changed payload leaf

```text
=== full: 227890 -> 228025 bytes (delta 135)
   payload/messages/0/content/0/text | string 45062->45197 bytes (delta 135), 1 edit(s)
      insert: before=''
              after =" a term from EDAM Data, EDAM Format, IANA media types (the source's own identifier, as an IRI or CURIE, when the documents supply one);"
   payload/messages/0/content/6/text | string 30637->30637 bytes (delta 0), 2 edit(s)
      replace: before='1442513'
               after ='1442944'
      replace: before='eb543e1597b29599952359818bc741b0f23eaa3a30e7aa8c63e60212c7bbb92f'
               after ='9a821e6a08e8fe8c6b0e2fd1d4bef9e5d4ee3740722b81ab7620c315287bc8da'
   leaves changed: 2
=== full_receipt_completion: 306441 -> 306576 bytes (delta 135)
   payload/messages/0/content/0/text | string 45062->45197 bytes (delta 135), 1 edit(s)
      insert: before=''
              after =" a term from EDAM Data, EDAM Format, IANA media types (the source's own identifier, as an IRI or CURIE, when the documents supply one);"
   payload/messages/0/content/6/text | string 30637->30637 bytes (delta 0), 2 edit(s)
      replace: before='1442513'
               after ='1442944'
      replace: before='eb543e1597b29599952359818bc741b0f23eaa3a30e7aa8c63e60212c7bbb92f'
               after ='9a821e6a08e8fe8c6b0e2fd1d4bef9e5d4ee3740722b81ab7620c315287bc8da'
   payload/messages/2/content/0/text | string 38448->38448 bytes (delta 0), 1 edit(s)
      replace: before='eb543e1597b29599952359818bc741b0f23eaa3a30e7aa8c63e60212c7bbb92f'
               after ='9a821e6a08e8fe8c6b0e2fd1d4bef9e5d4ee3740722b81ab7620c315287bc8da'
   leaves changed: 3
=== reconcile_full: 467263 -> 467587 bytes (delta 324)
   payload/messages/0/content/0/text | string 45062->45197 bytes (delta 135), 1 edit(s)
      insert: before=''
              after =" a term from EDAM Data, EDAM Format, IANA media types (the source's own identifier, as an IRI or CURIE, when the documents supply one);"
   payload/messages/0/content/8/text | string 114175->114364 bytes (delta 189), 7 edit(s)
      insert: before=''
              after ='or format '
      insert: before=''
              after =': an EDAM Data or Format term or an IANA media type, written'
      insert: before=''
              after =" a CURIE with the schema's declared `EDAM` or `mediatypes` prefix, when the documents supply one; or"
      insert: before=''
              after =" selected profile's"
      replace: before='registry'
               after ='declared'
      replace: before='1442513'
               after ='1442944'
      replace: before='eb543e1597b29599952359818bc741b0f23eaa3a30e7aa8c63e60212c7bbb92f'
               after ='9a821e6a08e8fe8c6b0e2fd1d4bef9e5d4ee3740722b81ab7620c315287bc8da'
   leaves changed: 2
=== report: 589829 -> 590153 bytes (delta 324)
   payload/messages/0/content/0/text | string 45062->45197 bytes (delta 135), 1 edit(s)
      insert: before=''
              after =" a term from EDAM Data, EDAM Format, IANA media types (the source's own identifier, as an IRI or CURIE, when the documents supply one);"
   payload/messages/0/content/14/text | string 127578->127767 bytes (delta 189), 7 edit(s)
      insert: before=''
              after ='or format '
      insert: before=''
              after =': an EDAM Data or Format term or an IANA media type, written'
      insert: before=''
              after =" a CURIE with the schema's declared `EDAM` or `mediatypes` prefix, when the documents supply one; or"
      insert: before=''
              after =" selected profile's"
      replace: before='registry'
               after ='declared'
      replace: before='1442513'
               after ='1442944'
      replace: before='eb543e1597b29599952359818bc741b0f23eaa3a30e7aa8c63e60212c7bbb92f'
               after ='9a821e6a08e8fe8c6b0e2fd1d4bef9e5d4ee3740722b81ab7620c315287bc8da'
   leaves changed: 2
=== report_after_repair: 589829 -> 590153 bytes (delta 324)
   payload/messages/0/content/0/text | string 45062->45197 bytes (delta 135), 1 edit(s)
      insert: before=''
              after =" a term from EDAM Data, EDAM Format, IANA media types (the source's own identifier, as an IRI or CURIE, when the documents supply one);"
   payload/messages/0/content/14/text | string 127578->127767 bytes (delta 189), 7 edit(s)
      insert: before=''
              after ='or format '
      insert: before=''
              after =': an EDAM Data or Format term or an IANA media type, written'
      insert: before=''
              after =" a CURIE with the schema's declared `EDAM` or `mediatypes` prefix, when the documents supply one; or"
      insert: before=''
              after =" selected profile's"
      replace: before='registry'
               after ='declared'
      replace: before='1442513'
               after ='1442944'
      replace: before='eb543e1597b29599952359818bc741b0f23eaa3a30e7aa8c63e60212c7bbb92f'
               after ='9a821e6a08e8fe8c6b0e2fd1d4bef9e5d4ee3740722b81ab7620c315287bc8da'
   leaves changed: 2
=== report_regate: 751068 -> 751392 bytes (delta 324)
   payload/messages/0/content/0/text | string 45062->45197 bytes (delta 135), 1 edit(s)
      insert: before=''
              after =" a term from EDAM Data, EDAM Format, IANA media types (the source's own identifier, as an IRI or CURIE, when the documents supply one);"
   payload/messages/0/content/14/text | string 127578->127767 bytes (delta 189), 7 edit(s)
      insert: before=''
              after ='or format '
      insert: before=''
              after =': an EDAM Data or Format term or an IANA media type, written'
      insert: before=''
              after =" a CURIE with the schema's declared `EDAM` or `mediatypes` prefix, when the documents supply one; or"
      insert: before=''
              after =" selected profile's"
      replace: before='registry'
               after ='declared'
      replace: before='1442513'
               after ='1442944'
      replace: before='eb543e1597b29599952359818bc741b0f23eaa3a30e7aa8c63e60212c7bbb92f'
               after ='9a821e6a08e8fe8c6b0e2fd1d4bef9e5d4ee3740722b81ab7620c315287bc8da'
   leaves changed: 2
=== typed_audit_omission: 598497 -> 598875 bytes (delta 378)
   payload/messages/0/content/3/text | string 114175->114364 bytes (delta 189), 7 edit(s)
      insert: before=''
              after ='or format '
      insert: before=''
              after =': an EDAM Data or Format term or an IANA media type, written'
      insert: before=''
              after =" a CURIE with the schema's declared `EDAM` or `mediatypes` prefix, when the documents supply one; or"
      insert: before=''
              after =" selected profile's"
      replace: before='registry'
               after ='declared'
      replace: before='1442513'
               after ='1442944'
      replace: before='eb543e1597b29599952359818bc741b0f23eaa3a30e7aa8c63e60212c7bbb92f'
               after ='9a821e6a08e8fe8c6b0e2fd1d4bef9e5d4ee3740722b81ab7620c315287bc8da'
   payload/messages/0/content/5/text | string 602->602 bytes (delta 0), 4 edit(s)
      replace: before='b9ec2d48d1d7e16d4f9f17d07234bc8205ae8d62d9967766c4260e1543b44e5e'
               after ='e4badb0f8b84b103f27f197ee05405dde0f81c531015687c54c60a11cce306bf'
      replace: before='195e05e1b91a0bc2701dc9a7d12987a3bb41959179e8e621c1cea54fb82f4f10'
               after ='5cb1b7c065ad896f2ce0de614458be6f58bb99e3b799496833ca65cfb7211ba4'
      replace: before='fd2ea826263f04af63e62958a2628b98c4c9e2ee245e96841e1aac533a936bf1'
               after ='950b4f6a982a05a397ab50b920687cf23d0d5ddbe9ea9162342ab165b3dcea37'
      replace: before='5893eddc65c8cc31e9cf0d30fd8db4fab48333953cf316bbd24de31e197a552e'
               after ='94e4c9224a988d917b7c3995ff1c8ac7e15d99715dc72ce9a882802aa56dacfa'
   payload/messages/0/content/6/text | string 402976->403165 bytes (delta 189), 8 edit(s)
      replace: before='ffb053faa9422e1665df9c618e02f7cc2f1c39f195a5570cd98240fa239402a0'
               after ='9bf034eb350b572980c4a28af39bc1fcdc268b0146b04df98d74c837f1378df0'
      insert: before=''
              after ='or format '
      insert: before=''
              after =': an EDAM Data or Format term or an IANA media type, written'
      insert: before=''
              after =" a CURIE with the schema's declared `EDAM` or `mediatypes` prefix, when the documents supply one; or"
      insert: before=''
              after =" selected profile's"
      replace: before='registry'
               after ='declared'
      replace: before='eb543e1597b29599952359818bc741b0f23eaa3a30e7aa8c63e60212c7bbb92f'
               after ='9a821e6a08e8fe8c6b0e2fd1d4bef9e5d4ee3740722b81ab7620c315287bc8da'
      replace: before='8d35f36e80bc090ace7c1d0a9b389fff5765d51d740f7b366f77ea8677f3e10d'
               after ='d192a51da3fbf63d280fb6dd0b5de65fea096d7777c493488cf82a170636ca93'
   leaves changed: 3
=== typed_audit_worker:worker_0001: 353386 -> 353386 bytes (delta 0)
   payload/messages/0/content/3/text | string 66913->66913 bytes (delta 0), 2 edit(s)
      replace: before='1442513'
               after ='1442944'
      replace: before='eb543e1597b29599952359818bc741b0f23eaa3a30e7aa8c63e60212c7bbb92f'
               after ='9a821e6a08e8fe8c6b0e2fd1d4bef9e5d4ee3740722b81ab7620c315287bc8da'
   payload/messages/0/content/5/text | string 529->529 bytes (delta 0), 3 edit(s)
      replace: before='f7ea5252ce6e26b22d20d238f62feeb3daabe02e4cb53f17e198987e5f5d0fe8'
               after ='39ab0ee91c3aa8abb72dd6a11ffe41ef99c91e42f1b7a6bd977205c0f0c4acc7'
      replace: before='fd2ea826263f04af63e62958a2628b98c4c9e2ee245e96841e1aac533a936bf1'
               after ='950b4f6a982a05a397ab50b920687cf23d0d5ddbe9ea9162342ab165b3dcea37'
      replace: before='5893eddc65c8cc31e9cf0d30fd8db4fab48333953cf316bbd24de31e197a552e'
               after ='94e4c9224a988d917b7c3995ff1c8ac7e15d99715dc72ce9a882802aa56dacfa'
   payload/messages/0/content/6/text | string 210569->210569 bytes (delta 0), 4 edit(s)
      replace: before='fd2ea826263f04af63e62958a2628b98c4c9e2ee245e96841e1aac533a936bf1'
               after ='950b4f6a982a05a397ab50b920687cf23d0d5ddbe9ea9162342ab165b3dcea37'
      replace: before='eb543e1597b29599952359818bc741b0f23eaa3a30e7aa8c63e60212c7bbb92f'
               after ='9a821e6a08e8fe8c6b0e2fd1d4bef9e5d4ee3740722b81ab7620c315287bc8da'
      replace: before='3cda3669b9dd2be7091254ba134597a5b3245133a1a84a989a76db202b8f376d'
               after ='3cbc8a74ef4556c6d9fbdca64d8e2b27c132d2aaf18bed010c7ca9a5e5cf3fad'
      replace: before='c8565a205bdb0153e67f13533ef32596ae7d0ca0e220cc083038e88574f50718'
               after ='81cf2795bbc92bb7cb5275d3f81038c9ba5b5b65e65f9a8ce99c815dfc1419b2'
   leaves changed: 3
=== typed_audit_worker:worker_0002: 352447 -> 352636 bytes (delta 189)
   payload/messages/0/content/3/text | string 65715->65904 bytes (delta 189), 7 edit(s)
      insert: before=''
              after ='or format '
      insert: before=''
              after =': an EDAM Data or Format term or an IANA media type, written'
      insert: before=''
              after =" a CURIE with the schema's declared `EDAM` or `mediatypes` prefix, when the documents supply one; or"
      insert: before=''
              after =" selected profile's"
      replace: before='registry'
               after ='declared'
      replace: before='1442513'
               after ='1442944'
      replace: before='eb543e1597b29599952359818bc741b0f23eaa3a30e7aa8c63e60212c7bbb92f'
               after ='9a821e6a08e8fe8c6b0e2fd1d4bef9e5d4ee3740722b81ab7620c315287bc8da'
   payload/messages/0/content/5/text | string 529->529 bytes (delta 0), 3 edit(s)
      replace: before='c7c6193b40731a96f576da11492c46eee5f634581c6753184bc6fcccba4a5318'
               after ='2c8c98f21051d3e208c6accf769680b43fcde320f0a283301733a0672a2cf05c'
      replace: before='fd2ea826263f04af63e62958a2628b98c4c9e2ee245e96841e1aac533a936bf1'
               after ='950b4f6a982a05a397ab50b920687cf23d0d5ddbe9ea9162342ab165b3dcea37'
      replace: before='5893eddc65c8cc31e9cf0d30fd8db4fab48333953cf316bbd24de31e197a552e'
               after ='94e4c9224a988d917b7c3995ff1c8ac7e15d99715dc72ce9a882802aa56dacfa'
   payload/messages/0/content/6/text | string 210749->210749 bytes (delta 0), 4 edit(s)
      replace: before='fd2ea826263f04af63e62958a2628b98c4c9e2ee245e96841e1aac533a936bf1'
               after ='950b4f6a982a05a397ab50b920687cf23d0d5ddbe9ea9162342ab165b3dcea37'
      replace: before='eb543e1597b29599952359818bc741b0f23eaa3a30e7aa8c63e60212c7bbb92f'
               after ='9a821e6a08e8fe8c6b0e2fd1d4bef9e5d4ee3740722b81ab7620c315287bc8da'
      replace: before='3cda3669b9dd2be7091254ba134597a5b3245133a1a84a989a76db202b8f376d'
               after ='3cbc8a74ef4556c6d9fbdca64d8e2b27c132d2aaf18bed010c7ca9a5e5cf3fad'
      replace: before='e8213cf92b55fc6621b053f4ed9d20b6ccffe3063d86487c74f4bead7c2e4d62'
               after ='6b316501809a90b62d9894c3de955a054e647a672881b2107a70c2adce570e89'
   leaves changed: 3
=== typed_audit_worker:worker_0003: 346581 -> 346581 bytes (delta 0)
   payload/messages/0/content/3/text | string 61571->61571 bytes (delta 0), 2 edit(s)
      replace: before='1442513'
               after ='1442944'
      replace: before='eb543e1597b29599952359818bc741b0f23eaa3a30e7aa8c63e60212c7bbb92f'
               after ='9a821e6a08e8fe8c6b0e2fd1d4bef9e5d4ee3740722b81ab7620c315287bc8da'
   payload/messages/0/content/5/text | string 529->529 bytes (delta 0), 3 edit(s)
      replace: before='706b596b38a8b3d54534776a82e1f077e9dc948102024a3a73d46a4df73e0842'
               after ='d6d990b6d97b87b069b91b9176090e03c1ef9fcce59953adb4efd45da64cd527'
      replace: before='fd2ea826263f04af63e62958a2628b98c4c9e2ee245e96841e1aac533a936bf1'
               after ='950b4f6a982a05a397ab50b920687cf23d0d5ddbe9ea9162342ab165b3dcea37'
      replace: before='5893eddc65c8cc31e9cf0d30fd8db4fab48333953cf316bbd24de31e197a552e'
               after ='94e4c9224a988d917b7c3995ff1c8ac7e15d99715dc72ce9a882802aa56dacfa'
   payload/messages/0/content/6/text | string 209362->209362 bytes (delta 0), 4 edit(s)
      replace: before='fd2ea826263f04af63e62958a2628b98c4c9e2ee245e96841e1aac533a936bf1'
               after ='950b4f6a982a05a397ab50b920687cf23d0d5ddbe9ea9162342ab165b3dcea37'
      replace: before='eb543e1597b29599952359818bc741b0f23eaa3a30e7aa8c63e60212c7bbb92f'
               after ='9a821e6a08e8fe8c6b0e2fd1d4bef9e5d4ee3740722b81ab7620c315287bc8da'
      replace: before='3cda3669b9dd2be7091254ba134597a5b3245133a1a84a989a76db202b8f376d'
               after ='3cbc8a74ef4556c6d9fbdca64d8e2b27c132d2aaf18bed010c7ca9a5e5cf3fad'
      replace: before='bfb7efe03396c4517ea9f7ffba9cf4263d2257177751a754713091f5e8494c16'
               after ='d45bec39168f54aa7a3388d067ad684f9caf9bb2fee40fd7500759c68574e42e'
   leaves changed: 3
```
