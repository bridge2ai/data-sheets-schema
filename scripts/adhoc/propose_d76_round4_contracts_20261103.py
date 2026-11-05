#!/usr/bin/env python3
"""PR #5213: prepare per-candidate source-contract proposals for human review.

2026-11-03. Input: the retained AST inventory JSON. Output: a fresh JSON review
roster; never edits source or supplies runtime exemptions. The separately
approved exact-function sidecar preserves protected source without alteration.
"""
import argparse
import hashlib
import json
from pathlib import Path


GUARDED = {
    'data_sheets_schema.api_runner.RunSpec.base_prompt',
    'data_sheets_schema.api_runner.resolve_prompt',
    'data_sheets_schema.api_runner.build_phase',
    'data_sheets_schema.api_runner.plan',
    'data_sheets_schema.api_runner.execute',
    'data_sheets_schema.native_attribution_registration.registration',
    'data_sheets_schema.native_attribution_registration.write_registration',
}

UNRELATED = {
    'data_sheets_schema.support_judge.render_request':
        'The spec parameter is the already rendered field-specification string, not a RunSpec.',
    'data_sheets_schema.transformation_receipts.validate_spec_against_pair_schema':
        'The spec parameter is a LinkML TransformationSpecification or None, not a generation RunSpec.',
}

API_PRECONDITIONS = {
    'phase_max_tokens': 'The plan/execute admission caller has validated this RunSpec before resolving model/configuration limits; this helper only derives the selected phase cap.',
    'context_blocks': 'The generation/provenance caller supplies the unchanged validated spec or its literal recorded rendering selection before manifest-derived context inspection; these observations do not independently prove consumption.',
    'resolved_prompt_digest': 'The generation/provenance caller has validated the current spec before combining its cached instruction digest with current inputs; hashing cached text is not fresh input admission.',
    'agentic_selected_inputs': 'resolve_prompt has validated this RunSpec before deriving its manifest, bundle and artifact command arguments; this formatter does not admit execution.',
    'native_evidence_instructions': 'The guarded rendering/native-registration caller supplies the unchanged selected spec before deriving native evidence commands; command text is not execution authority.',
    'validation_block': 'When passing a RunSpec, execute or a validated saved-record inspection caller has checked the selected spec before hashing outputs; independent ValidationInputs callers remain artifact-only inspection.',
    'validate_outputs': 'When passing a RunSpec, execute or a validated saved-record inspection caller has checked the selected spec before artifact validation; independent ValidationInputs callers remain artifact-only inspection.',
    'pair_consistency': 'When passing a RunSpec, execute or a validated saved-record inspection caller has checked the selected spec before reading the full/core pair; independent ValidationInputs callers remain artifact-only inspection.',
    'report_claims_block': 'The execute/report-check caller has validated the selected RunSpec before collecting report-claim evidence from its artifacts; this evidence helper does not authorize a request.',
    'report_audit_totals_block': 'The execute/report-check caller has validated the selected RunSpec before reading its audit/report evidence; this check does not authorize provider delivery.',
    'source_metadata_authority': 'The guarded rendering/execution caller has validated the current RunSpec before selected source-metadata authority is read; this helper is subordinate to that input boundary.',
    'source_metadata_block': 'resolve_prompt or the guarded execution path has validated this RunSpec before source-metadata evidence is assembled; the returned block is not a launch gate.',
    'evidence_checks_block': 'The guarded execution/report-check caller has validated this RunSpec before gathering evidence checks over its selected inputs and outputs.',
    'require_evidence_checks': 'execute has validated the current RunSpec before delegating selected evidence-gate checks; this helper does not independently authorize input selection or spending.',
    'require_source_reviews': 'execute has validated the current RunSpec before delegating selected source-review checks; callers must retain its existing output/admission gates.',
    'saved_evidence_checks': 'The execution or saved-record inspection caller has validated its current or literal restored RunSpec before reading saved evidence; saved checks do not independently admit a launch.',
    'grounding_block': 'The guarded execution/provenance caller has validated the current RunSpec before collecting source-grounding evidence; this block does not establish launch authority.',
    'merge_abandoned_rows': 'The guarded execute recovery path has validated this RunSpec and retained journal/ownership admission before merging abandoned accounting rows.',
}

NATIVE_PRECONDITIONS = {
    'native_attempt_supervisor.recipe_steps': 'The caller supplies the unchanged spec and matching policy from draft.verified/verified composition, or the identical literal replay restored after exact registration and fixture-hash checks; recipe expansion does not admit an attempt.',
    'native_attempt_supervisor.registration': 'The caller supplies explicit paths/registration bytes; this factory reconstructs selection through verified composition and draft.verified, rather than adopting a caller-supplied RunSpec.',
    'native_attempt_supervisor.verified': 'The caller supplies exact saved registration bytes; reconstruction verifies composition and draft selection before any resulting RunSpec is consumed.',
    'native_attempt_supervisor.supervise': 'The supervisor reconstructs its spec through verified composition/registration and must retain separate freshness and one-attempt checks before reservations or dispatch; callers must not mutate the verified state.',
    'native_attempt_supervisor.read_final': 'The reader reconstructs the selected spec from verified registration/composition before inspecting final evidence; this inspection does not authorize another attempt.',
    'native_attribution_controller.command_policy': 'composition supplies the unchanged literal spec returned by draft.verified and its matching selected instruction file; deriving a command policy does not admit execution.',
    'native_attribution_controller.composition': 'Explicit registration/instruction inputs are verified through draft.verified before constructing composition; no caller-supplied mutable RunSpec is accepted.',
    'native_attribution_controller.verified_composition': 'The caller supplies exact composition bytes; reconstruction and complete re-encoding verify the draft registration before its spec is consumed.',
    'native_attribution_controller.write_composition': 'The selected draft registration is verified and the complete composition re-encoded before publication; no unvalidated mutable RunSpec is accepted.',
    'native_attribution_controller.CallbackAdapter.observe': 'The adapter was initialized from verified composition and callers have kept its spec/state and captured policy unchanged; observe additionally re-verifies the raw composition before processing the event.',
    'native_attribution_controller.CallbackAdapter.report': 'The adapter was initialized from verified composition and callers have kept its spec/state and captured policy unchanged; report re-verifies composition only for a complete result, not unconditionally.',
    'native_attribution_registration.verified': 'The caller supplies literal saved registration bytes; from_render_spec establishes replay origin and the complete guarded registration encoding must match before returning the spec.',
    'native_attribution_registration.command_kind': 'The caller supplies the unchanged spec from verified registration/state and the matching expected command set; this command classifier is not an execution entry.',
    'native_attribution_registration.main': 'Explicit CLI/render-spec input is parsed into a fresh RunSpec or literal replay, then delegated to guarded registration/write_registration before inputs are consumed or output published.',
    'native_attribution_results.capture': 'The selected composition is verified before constructing its CapturedDraft/state, which must remain bound to that exact registration and immutable capture.',
    'native_attribution_results.check_files': 'The caller supplies paths for the verified composition/capture check; the helper obtains its state through capture rather than accepting a mutable RunSpec.',
    'native_attribution_results.main': 'The CLI supplies explicit paths to the verified capture/check flow; it accepts no caller-supplied mutable RunSpec or independent launch authority.',
    'native_execution_gates.capture': 'The caller supplies the selected attempt/authority; replay.capture establishes the verified state and snapshot, which must remain unchanged before sealing execution-gate evidence.',
    'native_supervisor_gates.capture': 'The caller supplies the selected attempt/authority; replay.capture establishes the verified state and snapshot, which must remain unchanged before sealing supervisor-gate evidence.',
    'native_supervisor_gates.receipt_binding': 'The spec, record, registered input mapping and frozen helper belong to the same already verified prepared snapshot; sealed CapturePath access supplies its reads.',
    'native_execution_registration.environment': 'The caller supplies the unchanged spec and selected composition returned together by _selection/draft.verified, with its validated runtime; environment derivation does not admit a launch.',
    'native_execution_registration.permission_expectation': 'The caller supplies the unchanged spec and matching composition from _selection/draft.verified before this helper reads bundle bytes to derive the permission expectation.',
    'native_execution_registration.registration': 'Explicit selection is reconstructed through _selection and the exact saved permission probe is validated before a registration is returned; no mutable RunSpec argument is adopted.',
    'native_execution_registration.verified': 'The caller supplies exact registration bytes; this verifier rederives selection and checks the entire registration before returning it for use.',
    'native_execution_registration.write_registration': 'The selected registration is rederived and verified before publication; callers must retain the existing destination and exclusive-write checks.',
    'native_execution.authorizations': 'The caller has verified raw and its matching value with registration.verified; selected composition is reconstructed as part of the exact authority checks.',
    'native_execution.launch': 'The launch path restores selection through registration.verified and separately enforces authority, freshness and publication gates; verified state must remain unchanged before use.',
    'native_execution.read_final': 'The final reader restores selection through registration.verified and checks its selected final evidence; this read does not authorize another launch.',
    'native_execution.main': 'The CLI restores its selection through registration.verified and retains the separate authority/freshness/publication rules; no caller-supplied mutable RunSpec is accepted.',
    'native_neutral_runtime_v1.main': 'Exact supervisor registration and pinned composition/fixture bytes are verified before locally restoring literal replay; the CLI never accepts a mutable RunSpec object.',
    'native_source_attribution.command_args': 'The guarded rendering/native-registration caller supplies an unchanged constructed or literal-verified spec after the shared input invariant; this helper validates policy axes but not the input binding independently.',
    'native_source_attribution.instructions': 'The guarded rendering/native-registration caller supplies an unchanged constructed or literal-verified spec after the shared input invariant; generated policy instructions are not execution authority.',
}

CONSTRUCTION_PRECONDITIONS = {
    'data_sheets_schema.receipt_completion.registration': 'RunSpec.__post_init__ calls this parser during fresh construction, before origin binding exists; other callers must validate the completed same spec first. It validates selected receipt JSON and condition, without provider delivery.',
    'data_sheets_schema.shared_generation.select': 'RunSpec.__post_init__ calls selection validation during fresh construction, before origin binding exists; consumers of an existing spec must first apply its entry invariant.',
    'data_sheets_schema.shared_generation.capture': 'RunSpec.__post_init__ validates and captures a fresh selection before freezing its origin binding; callers reusing an existing spec must apply the entry invariant before this authority/input capture.',
}

MEMBER_PRECONDITIONS = {
    'profile_obj': 'The RunSpec is under construction or its caller has validated the current binding before profile lookup; this property is not generation admission.',
    'profile_selection': 'The RunSpec is under construction or its caller has validated the current binding before presenting the selected profile and basis.',
    'header_for_manifest': 'The constructor or validated rendering caller supplies the selected manifest path; this static helper formats metadata without reading inputs or authorizing execution.',
    'is_agentic': 'The caller is constructing the RunSpec or has validated it before route selection; this property only classifies stored fields.',
    'writes_receipt': 'The caller is constructing the RunSpec or has validated it before receipt-route selection; this property only classifies stored fields.',
    'from_render_spec': 'The caller supplies a literal saved renderer specification for inspection; this factory validates/restores it and establishes replay origin, which never authorizes execution.',
    'api_header_values': 'The caller has validated this RunSpec before observing or freezing request settings; recorded replay headers remain literal inspection data.',
    'bind_api_header_values': 'The planning or execution caller has validated this RunSpec before this method reads selected policy/shared authority and binds request settings.',
    'manifest_used': 'The caller is constructing the RunSpec or has validated it before consuming the selected manifest/header declaration; this property only classifies stored fields.',
    'input_identity': 'The planning/execution caller has validated the RunSpec immediately before hashing its selected inputs and shared authority; this method is not an independent admission gate.',
    'render_spec': 'The caller has validated the current RunSpec or is inspecting a genuine literal replay before serializing its rendering selection; serialization never authorizes execution.',
    'instruction': 'Consumers must validate the same RunSpec before using cached instruction text with current inputs; uncached rendering checks the invariant, while the cached text remains inspectable evidence.',
    'output_root': 'The caller is constructing the RunSpec or has validated it before using derived output locations; deriving a path does not authorize writes.',
    'full_path': 'The caller is constructing the RunSpec or has validated it before using the full-output location; deriving a path does not authorize writes.',
    'core_path': 'The caller is constructing the RunSpec or has validated it before using the core-output location; deriving a path does not authorize writes.',
    'report_path': 'The caller is constructing the RunSpec or has validated it before using the report location; deriving a path does not authorize writes.',
    'metadata_dir': 'The caller is constructing the RunSpec or has validated it before using the metadata directory; deriving a path does not authorize writes.',
    'provenance_path': 'The caller is constructing the RunSpec or has validated it before using the provenance location; deriving a path does not authorize writes.',
    'prompt_files': 'The rendering/provenance caller has validated the current RunSpec before enumerating selected prompt assets; this list is not independent input or launch admission.',
}

# Reviewed operation-level proposals supersede the provisional module families.
# They distinguish selecting a new request from preserving an existing delivery.
OPERATION_PRECONDITIONS = {
    'cli.api.check_routing_completed_cmd': 'The caller selects an immutable completed-capture file; recheck_completed reconstructs only its private read-only RunSpec context and does not authorize requests, recovery or provider delivery.',
    'source_heading_completed.recheck_completed': 'The caller supplies the immutable completed-byte closure; decode and exact roster checks precede private replay reconstruction, whose captured context is used only for independent evidence checks and never live admission.',
    'receipt_completion.registration_identity': 'The caller supplies populated receipt selection fields from construction or the same literal completed selection being inspected; this hashes parsed receipt policy and does not admit a request.',
    'receipt_completion.schema_capture': 'With spec=None this captures the current schema; otherwise input_identity supplies the unchanged selected shared spec whose authority is checked here before returning captured schema bytes. No generation is admitted.',
    'receipt_completion.schema_identity': 'The caller satisfies schema_capture\'s selected shared-spec or spec=None preconditions; returning schema identity is evidence capture, not provider admission.',
    'receipt_completion.preflight': 'bind_api_header_values or receipt run supplies the same entry-validated selection and resolved settings before route/policy/output-limit checks; this helper does not dispatch.',
    'receipt_completion.remember_exchange': 'The phase-delivery caller retains the exact already-admitted request, response and usage identity under the same run/ledger owner; save paid evidence before parsing even if input bytes have since drifted.',
    'receipt_completion.recover': 'The recovery caller supplies the same selected owner/registration and any matching historical record; reconstruction verifies pinned inputs, accounted response and current identity before writing recovered results, without making a provider call.',
    'receipt_completion.audit_carry': 'Guarded build_phase or typed request construction supplies the same selected owner with its accepted one-use receipt result; only that complete exact carry may be reused.',
    'receipt_completion.run': 'The API execution caller supplies a D76-admitted selected spec, current full/receipt evidence and the same settings, client and usage ledger; new calls require current admission, while delivered evidence is saved before later validation.',
    'receipt_completion.seal_full': 'The API full-completion caller retains the admitted run after full and receipt outputs are durably published; bind those outputs to their saved transcript without treating sealing as a new request gate.',
    'receipt_completion.resume_guard': 'The API continuation caller supplies the entry-validated same owner and authentic progress or matching completed provenance; a missing durable full boundary must not authorize restarting paid phases.',
    'receipt_completion.require_admission': 'usage_ledger.begin_call supplies its same entry-validated spec and durable receipt intent/seal inside the admission transaction; purchased or restarted phases remain refused.',
    'receipt_completion.require_audit_carry': 'The guarded typed/build-phase caller supplies the accepted one-use result and proposed carry for the same selected run; exact carry validation does not independently admit dispatch.',
    'receipt_completion.recover_delivered': 'The API resume caller supplies the same admitted owner and saved response with exact pending usage identity and complete counters; settle that delivery before recovery without turning it into permission for a fresh generation.',
    'receipts.phase1_snapshot_state': 'The evidence-inspection caller selects the receipt path with its same-run spec or explicit provenance record; classify the verified snapshot bytes and decoding outcome without treating evidence lookup as launch admission.',
    'receipts.phase1_snapshot_read': 'The evidence-inspection caller supplies the receipt path and optional same-run spec or explicit provenance record; retain generation/hash checks and allow historical filename fallback only when no indexed identity exists.',
    'receipts.phase1_snapshot_path': 'The caller satisfies phase1_snapshot_read\'s owner/record preconditions; the returned verified path is an inspection result, and consumers needing exact bytes must use the read operation.',
    'removal_repair.inspect_run': 'The inspection caller supplies the same run/snapshot owner and optional matching provenance record before reading attested originals and current full output; output drift is evidence to report, not new request authority.',
    'removal_repair.output_pins': 'The caller supplies the correct admitted owner\'s full/core paths; this operation reports their current bytes, including changed outputs, rather than admitting new generation.',
    'removal_repair.completion_check': 'The API completion/resume caller supplies the same selected owner, matching record and expected pins; independently compare final evidence without granting authority or silently adopting unusable snapshots.',
    'removal_repair.refresh_outcome': 'The finalization caller retains the admitted owner and prior repair outcome; inspect current evidence while preserving any earlier refusal, without treating this update as fresh-call admission.',
    'removal_repair.run': 'The API repair caller supplies the D76-admitted generation, settings/client and exact original/audit/full/core evidence; retain the one-attempt ledger allowance, persist delivered evidence first, and require unchanged inputs before output publication.',
    'typed_audit_runtime.prepare_packet': 'The typed-audit caller supplies the same D76-admitted selected spec and pinned originals/effective receipt; authority/evidence checks build that registered packet, without independently admitting dispatch.',
    'typed_audit_runtime.build_request': 'The typed-audit caller supplies the same entry-validated selection and registered packet/stage; request derivation must retain exact captured context and receipt carry before later counting and admission.',
    'typed_audit_runtime.recover_delivered': 'The API resume caller retains the admitted owner and complete saved response/usage identities; rebuilding verifies packet/authority and settles accounting without initiating a fresh call.',
    'typed_audit_runtime.recover': 'The recovery caller supplies the same run/selected registration and optional matching record; rebuild exact saved stages/assembly, with attributed audit evidence for terminal recovery, without authorizing retries.',
    'typed_audit_runtime.completion_check': 'The API completion/resume or completed-capture caller supplies the same validated selection and matching record for terminal independent rebuild; the result does not establish scientific approval or authorize new calls.',
    'typed_audit_runtime.resume_guard': 'The API continuation caller supplies the entry-validated selected owner and authentic progress or independently matching completed provenance; missing progress must not authorize restarting admitted stages.',
    'typed_audit_runtime.require_admission': 'usage_ledger.begin_call supplies the same entry-validated spec, current ledger transaction and usage identity; stage admission may be marked only within that transaction.',
    'typed_audit_runtime.require_request': 'The physical-call caller supplies the same prepared stage and exact counted/saved request wire under its admitted owner; context/carry comparison does not authorize independent dispatch.',
    'typed_audit_runtime.run': 'The API audit caller supplies the D76-admitted selected spec, exact phase-one carry and same settings/client/ledger; each registered stage requires current call admission, while raw response evidence must be saved before accounting/validation.',
    'agentic_runtime.instruction_adapter': 'resolve_prompt supplies an unchanged, entry-validated RunSpec before this adapter derives installed-agent command text; formatting commands does not admit a process launch.',
    'cli.api.render_prompt_cmd': 'The command constructs a RunSpec from CLI arguments and checks its input invariant before rendering or writing the selected instruction; it accepts no caller-supplied mutable RunSpec.',
    'cli.api.plan_cmd': 'The command constructs a RunSpec and checks its input invariant before delegation to api_runner.plan; callers must retain that check before policy or phase inspection.',
    'cli.api.run_cmd': 'The command constructs a RunSpec and checks its input invariant before dry-run planning or execution; the delegated API retains ownership, journal and lock ordering.',
    'cli.api.batch_cmd': 'Each constructed RunSpec is checked before batch authority and selected-owner checks; the same checked objects must reach planning/execution without mutation.',
    'cli.provenance.record': 'Explicit CLI paths and instruction evidence are admitted through the recorder identity and full-instruction checks before publication; any constructed or restored spec remains local to that verification, not an execution authority.',
    'cli.provenance.backfill_spec': 'The caller selects a saved provenance record and literal instruction for reconstruction; a locally reconstructed RunSpec is only evidence for a matching render specification, never permission to execute.',
    'cli.review.pack': 'The command selects a saved provenance record and delegates to review_pack.write_pack; any reconstructed RunSpec is literal inspection data and must not authorize generation.',
    'cli.review.disposition': 'The command selects the saved review/provenance artifacts and rebuilds inspection evidence through review_pack; reviewed edits do not turn any reconstructed replay spec into launch authority.',
    'cli.runs.check_cmd': 'The command selects saved runs and invokes request verification; reconstructed RunSpecs are literal historical inspection objects, not generation requests.',
    'output_ownership.require_disjoint_selected_outputs': 'The API batch caller has checked each selected RunSpec before comparing write footprints; it must retain these same selections and perform the existing locked ownership checks before writes.',
    'output_ownership.require_selected_resume_owner': 'The API caller has checked the selected RunSpec before reading ownership evidence, with resume matching the intended launch; ownership checks must also retain their existing position under the coordination lock.',
    'review_pack.instruction_text': 'The caller supplies a saved record and optional captured instruction; reconstruction uses literal replay only to verify instruction evidence, never to admit execution.',
    'review_pack.build_pack': 'The caller selects the provenance and instruction evidence for a review package; instruction_text may reconstruct literal replay, which remains inspection-only throughout this build.',
    'review_pack.write_pack': 'The caller selects the same provenance/instruction evidence passed to build_pack and an authorized review-package destination; package publication does not authorize the reconstructed replay to execute.',
    'runs.verify_request': 'The caller selects a saved request record for verification; this function reconstructs its literal RunSpec and compares request evidence without granting execution authority.',
    'report_claims.phase1_snapshot_with_pin_for': 'When a RunSpec is supplied, the report-check caller has validated that selected spec and matching record before reading its phase-one snapshot; spec=None retains artifact-only inspection and neither mode admits a launch.',
    'shared_generation_resources.resource_paths': 'Construction/capture callers supply the selected specs whose resource names are being discovered; existing-spec consumers must check their entry invariants first. This reads protected resource paths, not a provider or writer admission.',
    'shared_write_footprint.for_run': 'The caller is validating populated RunSpec fields during construction or has checked the completed spec before deriving its output footprint; a footprint alone does not authorize writes.',
    'latch_journal.journal_path': 'The caller supplies the selected run identity during construction, validated inspection or an admitted launch; this path formatter does not validate input binding or authorize a journal write.',
    'latch_journal.override_path': 'The caller supplies the selected run identity during construction, validated inspection or an admitted launch; this path formatter does not authorize an override or a new request.',
    'latch_journal.owned_artifacts': 'For live execution/startup, the caller has checked the selected RunSpec before artifact inventory. The read-only verify_completed_legacy path instead supplies its validated record/root-derived identity projection; neither inventory route authorizes continuation.',
    'latch_journal.start_launch': 'guarded_launch/launch_record has checked the selected spec and retained the expected external head while holding all output locks; this step establishes durable launch ownership before accounting initialization.',
    'latch_journal.pending_launch_paths': 'The ownership/startup caller has checked the selected RunSpec before inspecting unfinished launch evidence; returned paths are only the existing bound coordination exemption, not new launch authority.',
    'latch_journal.before_ledger_write': 'usage_ledger supplies a proposed mutation for the same admitted run and generation; post-delivery writes preserve that owner and prior admission even if input file bytes changed, while this helper verifies immutable journal transitions.',
    'latch_journal.remember_snapshot': 'snapshot_store.record supplies the exact already-delivered bytes and usage identity for the admitted run; preserve that same owner when pinning evidence before the mutable index, without treating this as fresh input admission.',
    'latch_journal.check': 'The startup or physical-attempt caller has already checked the selected RunSpec; this check adds journal/spending validation and must not replace the D76, selected-owner or request-admission gates.',
    'latch_journal.head_sha256': 'The caller supplies the selected validated or admitted run for journal inspection; reading a head does not establish that it was externally retained or authorize using it as the expected launch anchor.',
    'latch_journal.require_launch_head': 'The entry caller has checked the selected RunSpec and supplies an independently retained expected head; preserve this comparison both before acquiring output locks and while holding them.',
    'latch_journal.guarded_launch': 'execute supplies the entry-validated selection, retained expected head and its output-lock acquisition function after startup admission; the same selection must remain unchanged during acquisition and launch recovery.',
    'latch_journal.failure_advice': 'The caller reports a failure for the same selected or admitted run; only an anchor retained on that launch exception may authorize suggested resume syntax, never a newly read or refused head.',
    'latch_journal.launch_record': 'The caller has checked the selected spec and supplies a retained expected head; initialize=True additionally requires all output locks, while stop logging must preserve the admitted launch even on failure.',
    'latch_journal.provenance': 'The provenance caller supplies the same admitted run or validated inspection selection; qualified journal history is evidence only and does not grant permission for another request.',
    'latch_journal.verify_completed_legacy': 'The caller supplies explicit saved-record/evidence roots for the narrow legacy verifier; locally restored RunSpecs remain literal inspection data, with no execution, lock, repair or usage initialization allowed.',
    'snapshot_store.predecessor_generation': 'prepare_usage supplies the entry-validated selected owner before an explicit fresh generation; only that owner\'s current index may be considered as the predecessor.',
    'snapshot_store.activation_intent': 'prepare_usage supplies the entry-validated selected owner before replacing the ledger; capture its exact predecessor bytes before publishing the fresh accounting boundary.',
    'snapshot_store.finish_activation': 'The caller supplies the same admitted run whose ledger contains the durable activation intent; this recovery finishes that recorded initialization and must not invent a new selection or admission.',
    'snapshot_store.activate': 'The generation/recovery caller supplies the same admitted owner and accounting generation, plus its matching prior record; activation establishes that owner\'s snapshot index before phase evidence is published.',
    'snapshot_store.record': 'The response-saving caller supplies delivered bytes and the usage identity from the already-admitted request, retaining its same run/ledger owner; evidence must still be preserved if input file bytes changed during delivery, without authorizing another request.',
    'snapshot_store.read_latest': 'When spec is supplied, the inspection/recovery caller has validated the selected RunSpec and matching record before reading snapshots; spec=None uses portable byte attestation only, and neither route admits a provider call.',
    'snapshot_store.latest': 'The caller satisfies read_latest\'s selected-spec or portable-record preconditions; returning a verified snapshot path does not independently admit input selection or a request.',
    'snapshot_store.require_accounted': 'The resume/completion caller supplies the validated selected run and its matching prior record; surviving snapshot attempts must remain associated with that owner\'s complete accounting.',
    'snapshot_store.require_completed_accounted': 'The completion caller supplies the same validated run and completed record; every surviving call must remain accounted before returning completion, without granting new call authority.',
    'snapshot_store.entries': 'The provenance publisher supplies the same admitted owner whose snapshot index is being reported; retain its generation and verified evidence bytes rather than substituting another run or granting fresh admission.',
    'source_heading_admission.selected': 'The caller is constructing selected fields or operating on an entry-validated/admitted spec; this version predicate only classifies stored selection and does not check the binding.',
    'source_heading_admission.prepare': 'The phase caller has checked the selected RunSpec and established its ledger before passing the exact proposed wire; counting/persisting that proposal still precedes begin_call admission and provider delivery.',
    'source_heading_admission.bind_admission': 'usage_ledger.begin_call supplies the entry-validated selected run, prepared phase/attempt and current ledger transaction; bind only that counted request before the single pending-call write.',
    'source_heading_admission.require_wire': 'The physical-attempt caller supplies the same admitted run, usage identity and exact wire prepared for that request; this association check supplements the existing entry and journal gates.',
    'source_heading_admission.remember_response': 'The delivery caller supplies the exact response and usage identity of the already-admitted request under the same run/ledger owner; saving paid evidence is not a fresh input-binding check or permission for another request.',
    'source_heading_admission.completion_check': 'The completion/recovery caller supplies the same validated selected run and settled accounting; verifying saved count/request associations does not itself admit another provider call.',
    'source_heading_completed.measure_form': 'The selected API completion caller has checked the live v2 RunSpec and its final outputs before this measurement writes instrument evidence into that run\'s ledger; it is not a launch or provider-admission gate.',
    'source_heading_completed.capture_completed': 'The completion/inspection caller has checked the live selected v2 RunSpec before rechecking terminal registration, accounting and artifact closure; capturing that closure must not initiate new provider calls.',
    'source_heading_completed.completed_path': 'The caller supplies the selected run during construction or validated completion inspection; this path formatter alone does not admit completed-capture publication.',
    'source_heading_completed.publish_completed': 'The API completion caller has checked the same live v2 RunSpec before capture_completed rechecks its terminal closure; preserve the final authority/alias checks immediately before publication.',
    'usage_ledger.exclusive_run': 'The execution caller has checked the selected RunSpec and startup ownership/journal conditions before acquiring its output locks; lock acquisition alone never validates input binding or admits a request.',
    'usage_ledger.run_identity': 'The caller supplies populated identity fields during construction, validated inspection or an admitted transaction; this identity projection does not validate inputs or authorize generation.',
    'usage_ledger.identity_is_foreign': 'The caller supplies the selected identity from construction, validated inspection or an admitted run; comparing identity fields does not replace input or ownership admission.',
    'usage_ledger.record_matches': 'The caller supplies the selected identity and candidate record during validated inspection or recovery; matching identity fields does not establish input freshness or authorize continuation.',
    'usage_ledger.ledger_path': 'The caller supplies the selected identity during construction, validated inspection or an admitted transaction; deriving its accounting path does not authorize reads, writes or spending.',
    'usage_ledger.abandoned_journal_path': 'The caller supplies the selected run during validated inspection or an admitted transaction; this path formatter does not authorize an abandoned-attempt write or restart.',
    'usage_ledger.abandoned_journal_offset': 'The recovery/provenance caller supplies the same admitted run whose abandoned-attempt boundary is being read; an absent generation is not authorization to spend.',
    'usage_ledger.recorded_inputs': 'The resume/inspection caller supplies the validated selected run before reading its persisted pins; those pins are historical evidence, not a substitute for checking current inputs before another request.',
    'usage_ledger.pin_inputs': 'The continuation caller has validated the selected RunSpec and established that this same ledger may continue before persisting its input identity; pinning does not authorize an otherwise refused legacy restart.',
    'usage_ledger.require_resolved': 'The resume/request caller has checked the selected RunSpec and its owner before comparing current identity with saved pins or finishing recorded initialization; this is additional accounting admission, not the D76 entry check.',
    'usage_ledger.begin_call': 'The request caller has checked the selected RunSpec, exact request and current ownership before committing intent; retain journal, receipt, repair and source-review gates before any physical attempt.',
    'usage_ledger.validator_refresh': 'The recovery/request caller supplies the same admitted run before reading its durable report-refresh obligation; reading an accepted state does not authorize regeneration of paid work.',
    'usage_ledger.prepare_validator_refresh': 'The guarded repair caller supplies the selected run and exact accepted repair checkpoint after resolved accounting; only that run\'s next report-refresh obligation may be prepared.',
    'usage_ledger.finish_validator_refresh': 'The report-completion caller retains the admitted run and completed usage identity after writing the report and passing source-review gates; this records acceptance, not new request admission.',
    'usage_ledger.removal_repair_attempted': 'The recovery/admission caller supplies the selected validated run before inspecting its durable repair allowance; a missing output does not restore an allowance already spent or admitted.',
    'usage_ledger.require_removal_repair_admission': 'The continuation/request caller supplies the entry-validated selected run and intended phase; durable restoration and report obligations must be satisfied before another permitted request.',
    'usage_ledger.accept_removal_repair': 'The repair-completion caller retains the admitted run and verified delivered repair reading after final bytes/progress pins exist; recording acceptance must not discard or reassign paid evidence.',
    'usage_ledger.finish_removal_report': 'The report-completion caller supplies the same admitted run after its one permitted refresh is accounted and verified; this closes that obligation without admitting another report.',
    'usage_ledger.accepted_removal_outcome': 'The recovery/provenance caller supplies the validated selected run and separately recomputes its current reading; the saved accepted outcome is historical provenance, not fresh acceptance.',
    'usage_ledger.report_regate_attempted': 'The request/recovery caller supplies the selected validated run before inspecting its durable regate allowance; delivered or admitted work remains spent even when output files are absent.',
    'usage_ledger.evidence_refusal': 'The request/provenance caller supplies the same selected run before reading its terminal refusal; an observed refusal must not be treated as permission for another call.',
    'usage_ledger.record_evidence_refusal': 'The evidence-check caller retains the admitted run and exact rejection reading; persist the terminal result under that same owner even when it prevents further input admission.',
    'usage_ledger.record_report_rejection': 'The report-check caller retains the admitted run, exact rejected report hash and any associated usage identity; rejection persistence must not consume or expand request allowance.',
    'usage_ledger.require_source_review_admission': 'The request/continuation caller supplies the entry-validated selected run before checking prior delivered review acceptance; interrupted delivery cannot authorize another call.',
    'usage_ledger.cancel_call': 'The transport-error handler supplies the same admitted run and exact pending usage identity only when no completed response was delivered; cancellation is accounting resolution, not new input admission.',
    'usage_ledger.prepare_usage': 'The execution caller has checked the selected RunSpec and retained startup ownership, expected-head and lock ordering before establishing this generation boundary; the independent legacy refusal remains mandatory before writes.',
    'usage_ledger.generation_id': 'The caller supplies the same selected or admitted run during validated inspection or accounting; reading its generation identifier does not authorize input selection or spending.',
    'usage_ledger.prior_generation_ids': 'The caller supplies the selected or admitted owner before reading its explicitly archived generation history; history cannot authorize adopting unrelated evidence.',
    'usage_ledger.same_generation': 'The completion/snapshot caller supplies the selected validated owner and candidate generation; compatibility of an identifier does not independently admit another request.',
    'usage_ledger.persist_usage': 'The delivery/recovery caller retains the same admitted run and stable usage identity when saving completed counters or later outcomes; paid accounting must survive input-file drift and is not a fresh request authorization.',
    'usage_ledger.append_usage': 'The delivery caller supplies the same admitted run and completed usage row; durable persistence must precede the in-memory append, without requiring fresh input bytes merely to retain paid evidence.',
    'usage_ledger.merge_usage': 'The recovery/provenance caller supplies the validated selected run and its matching recorded rows; merge each surviving usage identity once and do not interpret the merged counters as new admission.',
    'usage_ledger.require_matching_usage': 'The completion/recovery caller supplies the selected validated owner and matching usage rows; stable identifiers cannot excuse contradictory counters or missing completed calls.',
    'shared_generation.identity': 'The constructor or entry-validated existing-spec caller supplies the same selected registration accepted by capture; returning its captured identity does not authorize execution.',
    'shared_generation.assert_current': 'The public rendering/planning/execution entry has checked this existing RunSpec before authority-file reads; this authority drift check supplements, rather than replaces, the shared input-spelling invariant.',
    'shared_generation.preflight': 'The guarded planning/execution caller supplies the same selected spec and resolved settings before checking registration and current authority; offline planning does not prove a credential route or admit delivery.',
    'shared_generation.generation_context': 'The guarded request builder supplies the unchanged selected RunSpec, or the completed verifier supplies its sealed private captured context; returned scope/vocabulary text is evidence, not scientific or launch approval.',
    'shared_generation.require_generation_context': 'The physical-request caller supplies its entry-validated selected spec and proposed messages before admission; require the exact complete captured generation-scope block without granting independent dispatch.',
    'shared_generation.schema_context': 'The guarded builder supplies the same selected RunSpec, or the completed verifier its sealed private captured context, plus the selected record/description paths; schema context does not admit a launch.',
    'shared_generation.require_client': 'The admitted request caller supplies the same entry-validated selected spec and actual adapter before delivery; endpoint agreement supplements existing request and journal admission.',
    'shared_generation.plan': 'api_runner.plan supplies the same entry-validated selected spec and resolved settings before shared preflight/request construction; this plan never authorizes a client call or campaign launch.',
    'shared_generation.memo': 'The caller has validated live authority before cache reuse, or holds the completed verifier\'s sealed captured context; raw_parts and build describe a pure derivation only, never admission, terminal or accounting state.',
    'shared_generation.source_raw': 'The guarded builder supplies the same selected RunSpec, or the completed verifier its sealed captured context; return only that capture\'s source-manifest bytes without new input or launch admission.',
    'shared_generation.source_registry': 'The caller satisfies source_raw\'s live-selection or sealed-context precondition; registry construction uses the captured source manifest and selected project, not independent authority.',
    'shared_generation.digest_text': 'The guarded builder supplies the same selected RunSpec or sealed completed context and selected schema class; cached digest rendering derives solely from captured schema/vocabulary bytes.',
    'shared_generation.marked_bundle': 'The guarded builder supplies the unchanged selected RunSpec or sealed completed context before deriving chunk-marked text from captured bundle/manifest bytes; this derivation is not a launch gate.',
    'shared_generation.core_inventory': 'The guarded builder supplies the selected RunSpec or sealed completed context whose captured core schema is being inspected; memoized slot names do not authorize new input selection.',
    'shared_generation.core_text': 'The API derivation caller supplies the entry-validated selected RunSpec and its current full-output path before authority recheck and core projection; output derivation does not itself admit another provider call.',
    'shared_generation.source_chunks': 'The guarded builder supplies the same selected RunSpec or sealed completed context before reading its captured factual bundle/chunk map; resulting chunks are evidence, not admission.',
    'shared_generation.routing_context': 'The guarded builder supplies the unchanged selected v2 RunSpec or sealed completed context; derive only the checked factual wire from the captured routing closure, not the control archive.',
    'shared_generation.require_routing_context': 'The physical-request caller supplies its entry-validated selected spec and exact proposed messages; checking the captured routing projection supplements request admission and does not grant independent dispatch.',
    'latch_journal.refuse_legacy_execution': 'The public execution entry has checked the selected RunSpec before this combined legacy/evidence inventory; retain its unchanged D68/D69 sequence before launch locks or accounting writes, and do not use it as a replacement D76 gate.',
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inventory', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not args.output.is_absolute() or '..' in args.output.parts or args.output.exists() or args.output.is_symlink():
        raise ValueError('fresh absolute output required')
    if args.output.parent.resolve(strict=True) != args.output.parent:
        raise ValueError('physical output parent required')
    inventory = json.loads(args.inventory.read_text())
    rows = []
    for row in inventory['candidates']:
        identity, module, qualname = row['identity'], row['module'], row['qualname']
        short_module = module.removeprefix('data_sheets_schema.')
        mode, precondition = None, None
        pending = None
        if identity in GUARDED:
            mode = 'guarded'
        elif identity in UNRELATED:
            mode, precondition = 'unrelated', UNRELATED[identity]
        elif identity in CONSTRUCTION_PRECONDITIONS:
            mode, precondition = 'validated-caller', CONSTRUCTION_PRECONDITIONS[identity]
        elif short_module.startswith('native_'):
            precondition = NATIVE_PRECONDITIONS.get(short_module + '.' + qualname)
            mode = 'validated-caller' if precondition else None
            if mode is None:
                pending = 'native candidate needs independent factory/helper call-path classification'
        elif qualname.startswith('RunSpec.'):
            precondition = MEMBER_PRECONDITIONS.get(qualname.removeprefix('RunSpec.'))
            mode = 'validated-caller' if precondition else None
        else:
            precondition = (API_PRECONDITIONS.get(qualname) if short_module == 'api_runner'
                            else OPERATION_PRECONDITIONS.get(short_module + '.' + qualname))
            mode = 'validated-caller' if precondition else None
        if mode is None and pending is None:
            pending = 'unclassified source candidate; no contract may be applied automatically'
        protected = (short_module == 'shared_generation' or
                     identity == 'data_sheets_schema.latch_journal.refuse_legacy_execution')
        rows.append({'identity': identity, 'path': row['path'], 'line': row['line'],
                     'reasons': row['reasons'], 'parameters': row['parameters'],
                     'existing_docstring': row['docstring'], 'proposed_mode': mode,
                     'proposed_precondition': precondition, 'classification_pending': pending,
                     'protected_no_source_edit': protected,
                     'application': 'approved exact-function sidecar; protected source unchanged' if protected else 'approved source docstring only; apply after canary review'})
    result = {'status': 'proposal only; not source acceptance or runtime proof',
              'inventory': str(args.inventory), 'inventory_sha256': sha(args.inventory),
              'producer_sha256': sha(Path(__file__)),
              'candidate_source_sha256': inventory['candidate_source_sha256'], 'candidates': rows,
              'limits': ['source discovery version is recorded by the input inventory; its separate mechanism tests govern completeness',
                         'protected contracts use the explicitly approved exact-function sidecar, never a file-wide waiver',
                         'per-operation caller obligations are documentation, not independent runtime admission evidence',
                         'no source edits are performed by this producer']}
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps({'output': str(args.output), 'sha256': sha(args.output),
                      'rows': len(rows), 'unclassified': sum(row['classification_pending'] is not None for row in rows),
                      'protected': sum(row['protected_no_source_edit'] for row in rows)}, indent=2))


if __name__ == '__main__':
    main()
