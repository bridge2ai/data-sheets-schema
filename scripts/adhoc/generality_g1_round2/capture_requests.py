# Purpose: G1 fix-round re-review - capture the CHORUS v10 shared-generation-v1 API
# request payloads offline, for a byte-exact before/after comparison: full,
# reconcile_full, report (carries from the archived 10-22a CHORUS intermediates),
# the typed-audit omission request and every typed-audit worker request (runtime's
# own pure packet/wire constructors; no ledger, run directory or provider).
# Inputs: argv[1] output JSON, argv[2] fixture dir (same absolute path at base and head).
# Run from the worktree root; the worktree must sit at the same absolute path for both
# captures. Outputs: canonical JSON {payloads: {name: payload}, errors, registration_sha256}.
# Reviewer helper (independent of codex's generality_review_bytes_20261029.py), 2026-10-30.
import copy, hashlib, json, os, sys
from pathlib import Path
from scripts import build_api_registrations as builder
from data_sheets_schema import api_runner as api, shared_generation as sg, receipt_completion as rc
from data_sheets_schema import typed_audit_runtime as runtime

out, fixture = Path(sys.argv[1]), Path(sys.argv[2])
fixture.mkdir(parents=True, exist_ok=True)
# P4a finding 1, 2026-10-30: retain the reviewer's builders/carries; add receipt
# continuation and the offline report variants. Archive reads stay in the caller.
carry_dir = Path(os.environ['G1_ARCHIVE'])
reg = builder.build_registration('CHORUS', '2026-10-30_g1-rereview-proof',
        registration_path=fixture / 'registration.json', partition='chorus', write_to_disk=False)
raw = sg.canonical(reg)
Path(reg['registration_path']).write_bytes(raw)
inputs = reg['inputs']
spec = api.RunSpec(**reg['run'], bundle=Path(inputs['bundle']['path']),
        chunk_manifest=Path(inputs['chunk_manifest']['path']), manifest=Path(inputs['source_manifest']['path']),
        condition='generic_v10', render_version=25, shared_generation_version=1,
        shared_generation_registration=raw.decode(), api_playbook_version=2,
        receipt_completion_version=2, receipt_completion_registration=sg.canonical(reg['receipt']).decode(),
        profile=inputs['profile']['name'], profile_basis=inputs['profile']['basis'],
        run_date='2026-10-30', out_dir=fixture / 'unused-output', provider=reg['runtime']['provider'])
settings = api._model_settings(spec.condition)
spec.bind_api_header_values(settings)
t = lambda n: (carry_dir / ('CHORUS_' + n)).read_text(encoding='utf-8')
carries = {
  'full': {},
  'reconcile_full': {'Completed full record': t('full.yaml'), 'Audit findings': t('audit.json')},
  'report': {'Audit findings': t('audit.json'), 'Original full record': t('full.yaml'),
             'Original core record': t('core.yaml'), 'Reconciled full record': t('reconcile_full.yaml'),
             'Completed core record': t('reconcile_core.yaml')},
}
doc = {'registration_sha256': hashlib.sha256(raw).hexdigest(), 'payloads': {}, 'errors': {},
       'audit_limits': reg.get('audit_limits'), 'schema_version_in_registration': None}
doc['registration'] = reg
requests = {}
for phase, carry in carries.items():
    try:
        request = api.build_phase(spec, phase, carry=carry)
        requests[phase] = request
        cap = api.phase_max_tokens(spec, phase, 128000)
        doc['payloads'][phase] = rc.request_payload(request, settings, {'max_output_tokens': cap})
    except Exception as exc:
        doc['errors'][phase] = f'{type(exc).__name__}: {exc}'[:2000]
try:
    inputs_path = carry_dir / 'CHORUS_receipt_completion_inputs.json'
    inputs = json.loads(inputs_path.read_bytes())
    doc['receipt_archived_inputs_sha256'] = hashlib.sha256(inputs_path.read_bytes()).hexdigest()
    # Rebuild the current initial request, preserving the archived assistant
    # response, record, receipt, bundle and manifest. Replaying the archived
    # transcript verbatim measures history, not the changed condition.
    full = requests['full']
    inputs['transcript'].update(system=full.system, cached_blocks=copy.deepcopy(full.cached_blocks),
                                messages=copy.deepcopy(full.messages))
    inputs['schema'] = rc.schema_capture(spec)
    inputs['registration'] = rc.registration_identity(spec)
    inputs['max_output_tokens'] = reg['receipt']['max_output_tokens']
    request, _ = rc.build_request(inputs)
    doc['payloads'][rc.PHASE] = rc.request_payload(request, settings, reg['receipt'])
except Exception as exc:
    doc['errors'][rc.PHASE] = f'{type(exc).__name__}: {exc}'[:2000]
try:
    # _regenerate_report uses build_phase('report') for both usage phases.
    # The archive has no repair/regate outcomes: fixed archived report carries
    # and an empty contradiction list exercise the renderer without inventing
    # model responses or claiming that a repair/regate actually happened.
    request = api.build_phase(spec, 'report', carry=carries['report'])
    cap = api.phase_max_tokens(spec, 'report', 128000)
    doc['payloads']['report_after_repair'] = copy.deepcopy(
        rc.request_payload(request, settings, {'max_output_tokens': cap}))
    api._append_regate(request, spec, t('report.md'), [])
    doc['payloads']['report_regate'] = rc.request_payload(request, settings, {'max_output_tokens': cap})
except Exception as exc:
    doc['errors']['report_variants'] = f'{type(exc).__name__}: {exc}'[:2000]
try:
    captured = sg.assert_current(spec)
    originals = {'original_full': t('full.yaml').encode(), 'original_core': t('core.yaml').encode()}
    result_raw = (carry_dir / 'CHORUS_receipt_completion_result.json').read_bytes()
    outcome = json.loads(result_raw)
    receipt_raw = outcome['receipt_yaml'].encode() if 'receipt_yaml' in outcome else (
        carry_dir.parent / 'CHORUS_coverage_receipt.yaml').read_bytes()
    recorded_result_path = ('data/ATTIC/d4d_concatenated_archived/claudecode_api_core/'
                            '2026-10-22a_claude-opus-5-api-generic-v10_rep1/intermediate/'
                            'CHORUS_receipt_completion_result.json')
    outcome['journal'] = {'result': {'path': recorded_result_path,
                                    'sha256': hashlib.sha256(result_raw).hexdigest(), 'bytes': len(result_raw)}}
    carry = rc._audit_carry(outcome)
    packet = runtime._prepare_packet_bytes(spec, captured, originals, receipt_raw)
    doc['packet_sha256'] = packet['sha256']
    for stage in runtime.roster(packet):
        if stage['phase'] == runtime.INTEGRATION_PHASE:
            continue  # needs worker/omission responses; not capturable offline
        name = stage['phase'] + ('' if 'worker_id' not in stage else ':' + str(stage['worker_id']))
        try:
            _, payload, _ = runtime._build_request_bytes(spec, captured, packet, stage, {}, None, settings,
                generation='offline-byte-proof', receipt_carry=carry)
            doc['payloads'][name] = payload
        except Exception as exc:
            doc['errors'][name] = f'{type(exc).__name__}: {exc}'[:2000]
except Exception as exc:
    doc['errors']['typed_audit'] = f'{type(exc).__name__}: {exc}'[:2000]
out.write_bytes(sg.canonical(doc))
for name, payload in doc['payloads'].items():
    b = sg.canonical(payload)
    print(name, len(b), hashlib.sha256(b).hexdigest())
print('errors', doc['errors'])
assert not spec.out_dir.exists()
assert not doc['errors'], doc['errors']
assert doc['payloads']['report_after_repair'] == doc['payloads']['report']
