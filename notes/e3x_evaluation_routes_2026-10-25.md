# E3x evaluation routes: verified engineering and proposed rating registrations

2026-10-25. Refs #5125, #5133, #5131, #5132, #5137 and #5126.

The requested engineering fixes already exist at E2 commit
`052badf4f04c7b1b8c57c20411c04459b3309678`. This follow-up preserves those
implementations and records their coverage. The v8 and native-arm routes below
are **design proposals**, not registrations, owner decisions, scientific
approvals or authorization to score. No provider or native-runtime call is
needed for this review.

## Existing engineering, independently checked

| Request | Existing implementation | Decisive existing coverage |
| --- | --- | --- |
| #5125: consume the registered runner's real output layout | `scripts/audit_evaluation_comparability.py:registered_run` joins `registration.json` to `receipt.json`, reconstructs blinding from original bytes and generation identity, compares `record.yaml` and its registered hash, revalidates every retained rating transcript, and checks exact attempt/session rosters. Explicit CLI input is repeatable `--registered-evaluation ARM=DIR`. | `tests/test_audit_evaluation_comparability.py::test_actual_registered_runner_output_satisfies_only_its_exact_ingestion_tuple`; `::test_alternate_supported_instruments_roundtrip_actual_runner_to_audit`; `::test_registered_join_mutations_are_visible_and_never_accepted` |
| #5133: one identity-aware blinding gate | `evaluation.blind_review_pack.blind_input` delegates to `_identity_blind`; the pack uses that same internal gate and additionally checks identifiers across the whole pack. `evaluation.registered_eval_runner.prepare` calls the public gate with the actual registered arm, project and label. Both implementations are captured before the gate and rechecked. | `tests/test_registered_eval_runner.py::test_runner_uses_actual_registered_arm_and_same_public_gate`; `::test_runner_refuses_ambiguous_or_leaking_source_instead_of_guessing_arm`; `::test_changed_blinding_implementation_refuses_before_mocked_dispatch`; `tests/test_blind_review_pack.py::test_public_gate_is_the_pack_gate_and_reads_no_source_path` |
| #5131: order normalization and fingerprint counts | `registered_eval_runner.blind_record` serializes sorted mapping keys while preserving scientific values and list order. `blind_review_pack._fingerprints` records defined British-form and crate-word occurrence counts only in the private key; these are hints, not a proof of successful blinding. | `tests/test_blind_review_pack.py::test_sorted_review_mapping_preserves_every_scientific_value_and_list_order`; `::test_fingerprint_counts_are_private_defined_hints_not_rewrites` |
| #5132: external private key | `blind_review_pack.build_blind_review_pack` requires `key_output` outside the reviewer directory after path resolution; the CLI requires `--key-output`. Existing destinations are never replaced. | `tests/test_blind_review_pack.py::test_external_key_is_required_by_api_and_cli`; `::test_key_cannot_resolve_inside_reviewer_directory` |
| #5137: bounded short identities | `blind_review_pack.Record` requires at least two non-whitespace arm characters. `_identifier_leaked` uses boundaries outside Unicode letters, numbers and combining marks for identifiers shorter than four characters; longer identifiers retain substring refusal. | `tests/test_blind_review_pack.py::test_short_arm_minimum_length_and_word_boundary_leakage`; `::test_short_arm_inside_unicode_word_preserves_scientific_text`; `::test_short_casefolded_arm_at_existing_boundaries_still_refuses` |

The runner-to-audit tests execute the production `prepare` and `execute`
controllers and ingest the files they actually write. Only the evaluator
subprocess is replaced by a test double that returns invented native-stream
events. Network connection attempts and unmocked runtime calls are refused by
the test fixtures. The three supported instrument cases are rubric10 3.0,
rubric20 3.0 and rubric20 4.0; supporting 4.0 in software does not approve it.

The positive ingestion test explicitly keeps
`comparable_for_final_v10 = false`,
`context_human_review_verified = false` and
`independence_verified = false`. Three distinct reported sessions do not
establish independent evaluators. A validated rating receipt establishes its
recorded software checks, not generation acceptance, source entailment,
scientific applicability approval or authorization for a final comparison.

### Verification provenance

The prior complete E2 focused result was **473 distinct passes**, tied to
`052badf4f`: 72 comparison, 146 blind-pack, 140 registered-runner and 115 audit
tests. That count is historical evidence from the orchestrator's
`notes/coordination/2026-10-23-codex-n1c-e2-assessment.md` in the primary
checkout, also recorded under `### codex` in its `STATUS.md`. It is not a new
full-suite result. The six implementation/test files named above are unchanged
from that exact Git commit in this E3x tree.

A fresh narrow offline verification passed **67 tests, zero failures, errors
or skips**, in 76.88 seconds (exit 0). It emitted one existing dateutil UTC
deprecation warning. This is a subset of the unchanged routes, not another
473-test run or a full-suite/integrated-stack claim. Independent source and
design review found no material blocker; no production or test file was edited.
`git diff --exit-code 052badf4f --` on the six implementation/test files above
returned 0 both before and after the run.

Interpreter: the primary checkout's `.venv/bin/python`, Python 3.13.12; this
tree's `src` and root were selected explicitly in `PYTHONPATH`. Lockfile SHA256:
`923ad962d2646e1a4be044a76ff6a66abf49c3e10ea87fc85ed3cd523a907e21`;
`pyproject.toml` SHA256:
`bac863ac39cc39d6767627e0a7d8fd085be693555e5220015afbe6aec45c0c8b`.
The lockfile records the selected repository dependency declaration, not a
claim that every installed package was independently reconciled to it here.

Evidence retained at `/private/tmp/d4d-e3x-evidence-20261025/`:

- `routes.xml`: SHA256 `85be469e497dd9b048e4d90c6eb8cd6307ac5304e3bed8629f3a4b0bb9ef2c87`.
- `routes.log`: SHA256 `a943a875b21e5a6daf7cd347ddc006a290a749aff0923c160759d6332c11e012`.

Exact invocation, from `/private/tmp/d4d-codex-e3x-20261025` (line wrapping only):

```sh
PYTHONPATH=/private/tmp/d4d-codex-e3x-20261025/src:/private/tmp/d4d-codex-e3x-20261025 \
PYTHONPYCACHEPREFIX=/private/tmp/d4d-e3x-pycache \
/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python \
  -m pytest -q -p no:cacheprovider \
  --junitxml=/private/tmp/d4d-e3x-evidence-20261025/routes.xml \
  tests/test_audit_evaluation_comparability.py::test_actual_registered_runner_output_satisfies_only_its_exact_ingestion_tuple \
  tests/test_audit_evaluation_comparability.py::test_alternate_supported_instruments_roundtrip_actual_runner_to_audit \
  tests/test_audit_evaluation_comparability.py::test_registered_join_mutations_are_visible_and_never_accepted \
  tests/test_registered_eval_runner.py::test_runner_uses_actual_registered_arm_and_same_public_gate \
  tests/test_registered_eval_runner.py::test_runner_refuses_ambiguous_or_leaking_source_instead_of_guessing_arm \
  tests/test_registered_eval_runner.py::test_changed_blinding_implementation_refuses_before_mocked_dispatch \
  tests/test_blind_review_pack.py::test_public_gate_is_the_pack_gate_and_reads_no_source_path \
  tests/test_blind_review_pack.py::test_sorted_review_mapping_preserves_every_scientific_value_and_list_order \
  tests/test_blind_review_pack.py::test_fingerprint_counts_are_private_defined_hints_not_rewrites \
  tests/test_blind_review_pack.py::test_external_key_is_required_by_api_and_cli \
  tests/test_blind_review_pack.py::test_key_cannot_resolve_inside_reviewer_directory \
  tests/test_blind_review_pack.py::test_short_arm_minimum_length_and_word_boundary_leakage \
  tests/test_blind_review_pack.py::test_short_arm_inside_unicode_word_preserves_scientific_text \
  tests/test_blind_review_pack.py::test_short_casefolded_arm_at_existing_boundaries_still_refuses \
  > /private/tmp/d4d-e3x-evidence-20261025/routes.log 2>&1
```

## #5126: v8 comparator rating route

The current `registered_eval_runner.prepare` accepts a real
`shared_generation_registration_v1` and independently pinned provenance that
binds its output to that registration. Historical v8 records do not acquire
that authority merely by being placed in a newer directory. Preserve this
guard; do not fabricate historical registration or alter original artifacts.

| Option | What it supports | Limit |
| --- | --- | --- |
| Explicit historical-artifact rating mode, recommended if the owner retains v8 | Rate the retained original v8 bytes under the newly selected common evaluator, instrument, context and blinding procedure. | A new rating procedure cannot recover missing generation evidence or make the old and new generation packages experimentally identical. |
| Defer v8 ratings | Complete API/native engineering and current-arm ratings without choosing a historical comparator. | No new v8 comparison claim until the owner chooses a route. |
| New registered comparator generation | Rate a newly generated, explicitly specified baseline under current controls. | This is a new condition with a new label, not a recreation or replacement of historical v8. It also requires separate generation budget and approval. |

Recommend the first option as a separately named, versioned registration mode
after the owner decides the comparator roster. Its frozen inputs should be:

1. Explicit project, historical generation method, label and replicate;
   original full-record path, SHA256 and byte count; independently pinned
   retained provenance and every asserted output identity. Core is a separately
   declared rating target if requested, not an interchangeable copy of full.
2. The source bundle/schema/prompt identities actually available from retained
   evidence. Missing historical registration, control traces or acceptance stay
   explicitly unavailable. Hash agreement alone must not set an acceptance bit.
3. A pinned owner comparator/contrast decision and exclusions, including the
   AI-READI RO-Crate decision under D02/#5042. Historical API-v8 04g records,
   separately labelled no-crate native reruns and a future API rerun cannot
   silently substitute for one another. This document selects none of them.
4. The exact evaluator route/model/runtime/effort, frozen instrument and
   execution adapter, reviewed project-specific applicability context, common
   blinding version, repeat count, per-attempt/aggregate budget and failure
   policy used for the intended comparison.

The implementation should use an explicit historical authority discriminator
and reader. Keep the current API registration parser unchanged. Reuse the same
blinding, rating execution and semantic-validation functions after admission;
retain original and blinded hashes, transcript, rating and receipt pins. The
comparability audit must dispatch by the declared registration format, preserve
the historical evidence gaps and group only like evaluation conditions.
Historical ratings remain intact; new ratings belong in fresh output paths.

The owner still decides whether v8 is included, which exact outputs/contrasts
are included, and whether source-exposure differences permit a package-level
comparison. The frozen instrument selection, its scientific review/calibration
and the human applicability review remain separate gates.

## Proposed E5-direct: Track N native-arm ratings

Recommend a **separate E5-direct registration after N11**. It lets the already
scoped E5b-reg API work proceed and adds native ratings only after the native
generation outputs have their required acceptance evidence. Alternatives are
to expand E5b after N11, delaying that panel, or omit native ratings and make no
native-versus-API rubric claim. The orchestrator's 2026-10-25 plan requests this
design; the recommendation does not itself authorize any option.

Use a new explicit format, for example
`registered_direct_semantic_evaluation_v1`, with
`generation_authority_kind = native_shared_generation_v1`. Keep
`registered_semantic_evaluation_v1` and its API admission behavior unchanged.
The evaluator runtime is a separate choice from the generator runtime:
rating a first-party native generation does not require changing the selected
CBORG evaluator route or inheriting the generator's account, tools or effort.

### Native input and acceptance contract

The registered roster must name `method = claudecode_direct`, renderer 26,
native shared version 1, the default runtime profile (profile1 excluded), and
the exact project/label/replicate/attempt. It must bind these existing artifacts
by SHA256 and byte count:

- Original full output and generation provenance in
  `data/d4d_concatenated/claudecode_direct/<label>/` and
  `claudecode_direct_core/<label>/`; core and report identities remain linked
  evidence even if the rating target is only full.
- Native selection S, composition C, execution registration E, their selected
  source/schema/prompt/runtime identities, and the one-use attempt identity.
- The completed attempt's final/published evidence and full saved reconstruction
  closure, including stage requests/responses, receipt history/origin evidence,
  transcript/control streams, recorder output and the registered gate results.
- The exact N11 review/acceptance record and applicable human decisions. An
  external scientific approval record must be named and independently checked;
  a self-asserted `approved` field or a passing runtime gate does not supply it.

Admission should reuse the native lane's frozen result reader and saved
reconstruction obligations (`native_shared_execution.read_final` and
`native_shared_results` in the N2 series). Record the implementation identity
used to check them. Require exact E/C/S joins, successful final artifact and
provenance joins, a settled nonpending attempt, and the applicable receipt,
schema/pair, evidence, recorder and lifecycle gates. A missing capture, failed
or partial attempt, moved alias, changed output or substituted same-byte path
must not qualify by filename. Keep known unassessed provider/scientific claims
unassessed. Do not re-run a provider, create a generation registration, execute
recorded code, or weaken a native guard while importing evaluation inputs.

The current N2 implementation is still being integrated. Before implementing
this adapter, pin its final reviewed head and exact successful output contract;
this design does not certify that N11 or the 900-second acceptance gate passed.

### Shared blinding and evaluator isolation

Apply `blind_review_pack.blind_input` with the actual native run identity, not
an invented API arm. Use the same `identity_aware_sorted_v1` normalization and
leakage checks for API, native and any approved historical ratings. Preserve
scientific text, false/unknown values, lists, source quotations and genuine
dataset provenance. An identity embedded in scientific text needs explicit
review; do not delete it to force admission. Residual style or RO-Crate words
remain possible fingerprints; diagnostic counts stay in the private key.

The evaluator sees the blinded record, frozen rubric/instrument and approved
applicability context through the same no-tools adapter. Generation receipts,
execution traces, paths, arm labels and previous ratings stay outside its
workspace and prompt. Use fresh independent processes and exact bound output
receipts as in E1; retain failed attempts and do not silently retry or replace
them. A native human blind-comparison batch, if selected, must use a separately
approved roster and external private key; E5-direct does not implicitly expand
the current campaign validator or permit its synthetic mode as a workaround.

### Join with API and v8 ratings

Maintain separate keys for generation identity and evaluation condition:

- Generation identity: authority kind, project, method/arm, label, replicate,
  exact original record/provenance hashes, and native attempt identity or
  explicit historical evidence status.
- Rating identity: evaluation registration/receipt hashes, original and
  recomputed blinded hashes, rubric/version and instrument/schema/evidence
  authority pins, normalized applicability-context hash, blinding and adapter
  pins, evaluator route/model/runtime/effort, rating index, session, transcript
  and accepted evaluation hashes.

Extend the audit with an explicit E5-direct reader that recomputes the same
blinded bytes and revalidates retained transcripts instead of trusting receipt
status alone. Duplicate directories, copies and reused sessions must not add
ratings. Different full/core targets, context decisions, instruments, adapters
or runtime conditions remain separate strata. Join matched project/replicate
contrasts only through the owner's frozen roster; differing original hashes
identify different records, not a failed cross-arm join. Keep repeated ratings
within a record distinct from generation replicates.

A common evaluation procedure supports a comparison of the observed generation
packages under that procedure. It does not isolate a causal effect of
agentic execution: the native/API declared differences, generator effort,
source exposure, timing and available historical evidence remain confounds.
The native-versus-API declared-differences document and the v8 contrast decision
must accompany reporting. Software eligibility remains separate from human
scientific acceptance.

### Implementation and decision handoff

After owner decisions, implement the explicit native/historical admission
adapters and versioned formats, then reuse the existing evaluation execution
and output protocol. Add fake-client end-to-end tests from each source adapter
through receipt ingestion; mutation tests must cover E/C/S/output joins,
receipt/transcript disagreement, stale/missing acceptance, identical copies,
full/core swaps, blinding mismatch, context drift and duplicate sessions. Do not
extend API registration admission by catching a parse error and falling back.

Before either route scores, record the owner's roster/contrast decision,
instrument and calibration disposition, named human applicability review,
repeat/budget/failure policy, evaluator route and pinned preparation. E5-direct
also waits on N11 and the separate decision about a native blind-review batch.
No new human decision is inferred here; the existing request to keep human
scientific review pending remains in force.
