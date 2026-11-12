#!/usr/bin/env python3
"""G13 map, 2026-11-12: source AST + curated production origins -> JSON/table.
No imports of the production stack, processes, network, or provider calls.
Inputs: this checkout. Outputs: explicit new map directory; never overwrite.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'src/data_sheets_schema'
NOW = 'available now'
MERGED = 'needs the merged source'
PROBE = 'needs a real-binary probe'
OWNER = 'needs an owner act'
REVIEW = 'needs an independent review'


def inp(names, origin, status=NOW):
    return [{'name': n.strip(), 'production_origin': origin, 'status': status} for n in names.split(',')]


def ref(qualified):
    module, name = qualified.split('.')
    path = SRC / (module + '.py')
    tree = ast.parse(path.read_text())
    node = next(n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name)
    return {'function': qualified, 'path': str(path.relative_to(ROOT)), 'line': node.lineno,
            'signature': name + '(' + ast.unparse(node.args) + ')',
            'source_sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def document(name, kind, version, builders, validators, inputs, note=''):
    return dict(document=name, kind=kind, version=version,
                builders=[ref(b) for b in builders], validators=[ref(v) for v in validators], inputs=inputs, note=note)


def source_contracts(documents):
    """Preserve exact closed-key/kind declarations beside the curated origins.

    AST expressions are data, never evaluated. Include constants from consumer
    modules as well as orchestration entrypoints to expose nested wire contracts.
    """
    paths = {r['path'] for d in documents for r in d['builders'] + d['validators']}
    paths.update('src/data_sheets_schema/' + name + '.py' for name in (
        'native_shared_contract', 'native_shared_controller', 'native_shared_runtime_values',
        'native_u4b_policy', 'native_shared_registration', 'native_model_aliases'))
    result = []
    for relative in sorted(paths):
        path = ROOT / relative
        declarations = []
        for node in ast.parse(path.read_bytes()).body:
            if not isinstance(node, ast.Assign):
                continue
            names = [n.id for n in node.targets if isinstance(n, ast.Name)]
            if any(n.endswith(('KEYS', 'KIND', 'VERSION', 'KINDS', 'TERM_VALUES')) for n in names):
                declarations.append({'line': node.lineno, 'declaration': ast.unparse(node)})
        if declarations:
            result.append({'path': relative, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'declarations': declarations})
    return result


def documents():
    return [
      document('Source manifest', 'repository YAML registry', 'no wire version', [], ['registry.load_registry'],
        inp('path', 'data/preprocessed/source_manifest.yaml; explicit caller path') + inp('profile,CHORUS source entries,referent,release,scope', 'manifest declarations'),
        'Existing input; not rewritten. Baseline CHORUS_preprocessed.txt, not crate-only or with-crate.'),
      document('Source bundle', 'UTF-8 concatenated source', 'no wire version', [], ['chunking.validate_manifest_mapping'],
        inp('raw,name', 'data/preprocessed/concatenated/CHORUS_preprocessed.txt; manifest-qualified canonical_name')),
      document('Chunk manifest', 'source-document chunk manifest', 'rule version 2', ['chunking.manifest_from_bytes'], ['chunking.validate_manifest_mapping'],
        inp('raw,name,rule', 'bundle bytes and declared rule in data/preprocessed/chunks/CHORUS_chunks.yaml')),
      document('Omission context', 'omission_context_v1', 1, [], ['native_shared_selection.capture'],
        inp('context', 'data/omission_contexts/chorus_omission_context.json') + inp('context schema', 'installed native prompt asset closure')),
      document('Schema closure', 'SchemaClosureCapture / selection declarations', 1, ['schema_snapshot.capture_schema'], ['native_shared_selection.capture'],
        inp('path,strict', 'explicit full/core schema roots in installed checkout; strict=True') + inp('imports,source bytes', 'local recursive LinkML imports')),
      document('Prompt assets and profile vocabulary', 'CapturedArtifact / selection declarations', 1, ['native_shared_selection.capture_assets', 'profiles.profile_named'], ['native_shared_selection.capture'],
        inp('assets', 'fixed installed native selection ASSET_HASHES') + inp('name,vocabulary', 'explicit bridge2ai; manifest profile; installed b2ai_registry_vocabularies.yaml')),
      document('Receipt policy', 'd4d_native_shared_receipt_policy', 1, [], ['native_shared_contract.parse_receipt_policy'],
        inp('registration_id', 'explicit draft packet identity') + inp('condition,runtime_policy_sha256,receipt_instrument_version,coverage_floor', 'fixed generic_v10 implementation; v4; pending diagnostic_pilot D109'),
        'Assembler writes the declaration; the production parser validates it. This is not N1 ratification.'),
      document('Selection', 'd4d_native_shared_selection', 1, [], ['native_shared_contract.parse_selection', 'native_shared_selection.capture'],
        inp('registration_id,registration_path,run,stage_root', 'explicit CHORUS / baseline / claudecode_direct / draft label and absolute future paths') +
        inp('selection,bounds', 'production descriptor, asset pins and BOUND_CEILINGS') + inp('inputs,receipt_policy', 'above exact repository file pins and policy'),
        'New scripts/build_native_canary_packet.py assembles declarations and calls production validators, never issues authority.'),
      document('Provisional runtime', 'closed runtime mapping; d4d_native_u4b_provisional_runtime_basis', 'runtime has no standalone kind/version; basis v1', [], ['native_u4b_probe_sequence.validate_provisional_runtime'],
        inp('route,model,auxiliary_models,effort,limits_basis', 'registered route/model aliases/high effort; no auxiliary models') +
        inp('executable.path,executable.sha256', 'explicit durable physical binary path and readable bytes; hashing does not execute it') +
        inp('executable.version,executable.init_version', 'actual saved pinned-binary version/init evidence', PROBE) +
        inp('provider,auth,environment,deadline_seconds,budget_guard_usd,keep_awake', 'explicit owner account/host/runtime declarations, no ambient credentials', OWNER) +
        inp('limits', 'provisional declared limits; final values must come from observation', OWNER),
        'No production preparer before observations; never invent auth or version evidence.'),
      document('D117 probe authorization', 'd4d_native_u4b_probe_authorization_v1', 1, [], ['native_u4b_probe_sequence.authorization'],
        inp('owner,authorized_at,word,directory,observation_deadline_seconds,permission_deadline_seconds,provider,permission_protocol', 'owner AUTHORIZE_TWO_SCRIPTED_NATIVE_PROBES; exact local-only protocol and one-use directory', OWNER) +
        inp('provisional_runtime_sha256', 'exact provisional runtime bytes', PROBE)),
      document('Account choice', 'd4d_native_u4_owner_choice', 1, [], ['native_generation._account_choice'],
        inp('decisions,account_label,effort,receipt_instrument', 'owner D105/D106 choice LBL work Claude Max / high / receipts v4', OWNER) +
        inp('subject_sha256,runtime_sha256', 'hash exact runtime, expectation or registration for the particular CLI invocation', PROBE),
        'Choice is not observed auth. Separate choice bytes for each changed subject.'),
      document('Observation manifest and transcript/request', 'd4d_native_u4b_observation_v1', 1, ['native_u4b_probe_sequence.produce_observation', 'native_u4b_probe_sequence.observation_document'], ['native_u4b_probe_sequence.validate_observation'],
        inp('authorization_raw', 'owner D117 file', OWNER) + inp('provisional_runtime,directory', 'declared runtime and authorization directory', OWNER) +
        inp('transcript_raw,request_raw,provider_url,started_at,finished_at,process', 'actual pinned binary observation; saved local provider URL, lifecycle and wire output', PROBE),
        'LIVE producer prohibited in this assignment.'),
      document('Final runtime', 'closed runtime mapping; d4d_native_u4b_runtime_basis', 'runtime v2 / basis v3', ['native_u4b_runtime.prepare_runtime'], ['native_u4b_runtime.validate_prepared_runtime'],
        inp('runtime,updater_source,updater_root', 'explicit runtime plus durable-copy/updater source identities', OWNER) +
        inp('probe_init_path,native_request_path,thinking_setting,thinking_basis,observation_probe_path', 'actual saved observation transcript/request/manifest, verified model limits and thinking', PROBE) +
        inp('admission_policy', 'owner-approved quota windows, freshness, margin, validity and keep-awake terms', OWNER)),
      document('Preparation envelope and instruction', 'd4d_native_shared_preparation_v2', 2, ['native_execution_registration_v2.prepare'], ['native_execution_registration_v2.verify_preparer'],
        inp('selection_path', 'captured selection') + inp('runtime_path', 'final runtime from actual observation', PROBE) +
        inp('job_id,run_date,max_draft_checks', 'explicit registered canary plan', OWNER) +
        inp('dependencies,RunSpec,instruction', 'clean merged protected integration and source closure', MERGED),
        'Instruction is derived by production prepare; preserve exact bytes from its body.'),
      document('Composition', 'd4d_native_shared_callback_composition', '1; authority_version 2', ['native_shared_controller_orchestration.compose'], ['native_shared_controller_orchestration.verified_composition'],
        inp('preparation_raw,instruction_path', 'preparation envelope and its exact instruction bytes', PROBE) + inp('controls,controller_sources', 'merged verified source closure', MERGED)),
      document('System instructions', 'nonblank UTF-8 system text', 'no wire version', [], ['native_shared_registration_orchestration.registration'],
        inp('system_path', 'explicit reviewed system text; effective text adds production command guidance', REVIEW)),
      document('Permission expectation and recipe', 'd4d_native_shared_permission_expected / d4d_native_shared_permission_recipe', 1, ['native_shared_registration.permission_expectation', 'native_shared_permissions.recipe'], ['native_permission_probe.require_u4_expectation'],
        inp('runtime', 'final observed runtime', PROBE) + inp('selected,spec,dependencies', 'verified merged preparation/composition reconstruction', MERGED) +
        inp('effective_system,config_directory', 'reviewed system plus guidance; registered attempt cli_config future path', REVIEW),
        'The new saved-step wrapper reconstructs these internals using production orchestration; this stage is not rehearsed beyond the protected integration stop.'),
      document('Bound permission manifest and sequence completion', 'd4d_native_shared_saved_permission_probe / d4d_native_u4b_probe_sequence_v1', 1, ['native_u4b_probe_sequence.produce_bound_probe'], ['native_u4b_probe_sequence.validate_bound_probe', 'native_shared_permission_orchestration.verify_saved_probe'],
        inp('authorization_raw', 'same owner D117 grant', OWNER) + inp('expected,directory', 'exact expectation and one-use authorized directory', PROBE) +
        inp('seven traces,version evidence,observation manifest', 'pinned binary on scripted loopback provider, saved wire outputs', PROBE),
        'LIVE producer prohibited here; do not use older unbound permission-probe.'),
      document('Execution registration', 'd4d_native_shared_execution_registration_v2', 2, ['native_shared_registration_orchestration.registration'], ['native_shared_registration_orchestration.verified'],
        inp('composition_path,permission_probe_path', 'verified composition and saved bound probe', PROBE) + inp('system_path', 'reviewed explicit system text', REVIEW) +
        inp('attempt_id,attempt_directory,evidence_directory,max_draft_checks,receipt_origin_version', 'explicit registered canary identities/bounds; fresh disjoint paths; origin secondary axis', OWNER) +
        inp('dependencies', 'clean merged committed source; protected files integrated', MERGED)),
      document('Registration-addition commit evidence', 'embedded registration_commit', 'review bundle v2', [], ['native_launch_review._registration_commit'],
        inp('repository,commit,path', 'lead commits exact registration into archival git repository; author date anchors 14-day validity', MERGED)),
      document('CI evidence', 'd4d_native_execution_ci_v2', 2, [], ['native_execution_registration_v2.admit'],
        inp('registration_sha256,attempt_id,source_commit,dependencies_sha256,checks,workflow_event,workflow_ref,workflow_sha256,tested_commit', 'completed required_checks(workflow_event), exact merged source and dependency closure; lead saved CI evidence', MERGED) +
        inp('checks.head_sha,checks.status,checks.conclusion,checks.details_url', 'each exact roster entry must complete successfully at registered source; repository Actions URL', MERGED),
        'Source _authorizations defines the exact wire keys; this map also records function signatures and source hashes.'),
      document('Independent component review documents', 'pinned UTF-8 review documents', 'no wire version', [], ['native_launch_review._review_document'],
        inp('document.path,document.bytes,document.sha256,reviewer,reviewer_kind,author,operator,independent,decision,reviewed_at', 'two genuinely independent Claude and Codex component reviews, excluding author/operator', REVIEW)),
      document('Owner launch terms and quota request', 'd4d_native_owner_launch_terms_v1 / d4d_native_subscription_capture_request_v3', '1 / 3', [], ['native_launch_review.validate_terms'],
        inp('owner,budget_guard_usd,deadline_seconds,max_starting_weekly_utilization,max_starting_five_hour_utilization,max_age_seconds,pre_reservation_margin_seconds,overage,keep_awake,context_mode,quota_capture', 'owner explicit terms consistent with observed runtime and current implementation', OWNER),
        'Adapter isolated in scripts/native_packet_review_inputs.py. Helper2 bundle v3/terms v2 not present on this base.'),
      document('Review bundle', 'd4d_native_execution_review_bundle_v2', 2, [], ['native_launch_review.validate_bundle'],
        inp('registration_sha256,attempt_id,source_commit,dependencies_sha256,registration_commit', 'exact registered bytes and registration-addition commit', MERGED) +
        inp('author,operator,owner_statement', 'declared identities and owner terms', OWNER) + inp('reviews', 'two pinned independent reviews', REVIEW)),
      document('Coded launch word', 'd4d_native_execution_launch_authorization_v2', 2, [], ['native_launch_review.validate_bundle', 'native_execution_registration_v2.admit'],
        inp('owner,authorized_at,word', 'owner AUTHORIZE_ONE_NATIVE_ATTEMPT for exactly one attempt', OWNER) +
        inp('registration_sha256,attempt_id,source_commit,dependencies_sha256,review_sha256,ci_sha256,permission_probe_sha256', 'exact final packet bytes shown to owner', REVIEW)),
      document('Quota capture manifest and event', 'd4d_native_subscription_capture_v1', 1, ['native_subscription_capture.capture_subscription'], ['native_subscription_capture.read_capture'],
        inp('registration_raw,review_bundle_raw,launch_word_raw,directory', 'validated final packet and owner bounded capture request', OWNER) +
        inp('event,transcript,claim,latest capture index', 'actual one paid subscription capture under launch word, saved output and claim store', PROBE),
        'LIVE and reservation-producing. Prohibited in rehearsal; max three does not authorize retries here.'),
      document('Subscription guard', 'd4d_native_subscription_guard', 2, ['native_subscription_capture.current_guard_preparation', 'native_subscription_guard_v2.prepare_guard'], ['native_subscription_guard_v2.load_guard'],
        inp('registration_raw,runtime,launch_word_raw,owner_statement', 'validated registration/owner packet', OWNER) +
        inp('event_raw,captured_at,capture_index,capture_claim_count', 'latest real capture claim and saved manifest; no stale replay', PROBE) +
        inp('maximum_starting_utilization,max_age_seconds,maximum_starting_five_hour_utilization,pre_reservation_margin_seconds,clock', 'explicit owner-approved admission terms; production wall clock', OWNER) +
        inp('guard_sha256', 'hash exact prepared guard bytes'),
        'Prepare through CLI latest-claim context; capture then guard then launch without pause.'),
    ]


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    args.output.mkdir(parents=False, exist_ok=False)
    value = {'scope': 'DRAFT offline G13 map; no authorization or production packet', 'base_commit': '058de60779412150c529e41c86c5cfe9047014da', 'statuses': [NOW,MERGED,PROBE,OWNER,REVIEW], 'documents': documents()}
    value['source_contracts'] = source_contracts(value['documents'])
    (args.output/'map.json').write_text(json.dumps(value, indent=2)+'\n')
    lines = ['# Native canary document map (DRAFT)', '', '| Document; kind/version | Producer → validator | Input | Production origin | Status |', '|---|---|---|---|---|']
    notes = []
    for d in value['documents']:
        producer = ', '.join(x['function'] for x in d['builders']) or 'explicit declaration / existing file'
        validator = ', '.join(x['function'] for x in d['validators'])
        for i in d['inputs']:
            lines.append(f"| {d['document']}; {d['kind']} / {d['version']} | {producer} → {validator} | {i['name']} | {i['production_origin']} | {i['status']} |")
        if d['note']:
            notes += ['', d['document']+': '+d['note']]
    lines += notes
    lines += ['', 'The companion JSON also preserves exact function signatures, source hashes, and AST-transcribed closed-key/kind/version declarations. These are source evidence, not newly issued documents.']
    (args.output/'map.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({'documents':len(value['documents']), 'inputs':sum(len(d['inputs']) for d in value['documents']), 'output':str(args.output)}))

if __name__ == '__main__':
    main()
