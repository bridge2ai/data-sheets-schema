"""D59/F1-F8 offline measurements and legacy parity, 2026-10-28.

Inputs: retained 10-22a/v8 records, read-only launch-base receipt/transcript,
current source and git 8dd00263a. Outputs: pinned measurement JSON in notes/reviews.
No provider/count_tokens calls, no run writes. Future BC1 responses are explicitly
byte scenarios, never fabricated accepted reviews. Run with the project Python -S -B.
"""
from __future__ import annotations

import ast
from contextlib import ExitStack
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
if not sys.flags.no_site:
    raise SystemExit('Use -S -B to exclude the editable install in the main checkout')
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
sys.path.append(str(Path(sys.executable).parent.parent / 'lib' /
                    f'python{sys.version_info.major}.{sys.version_info.minor}' / 'site-packages'))


def offline(event, args):
    if event in {'socket.connect', 'socket.getaddrinfo', 'socket.sendto'}:
        raise RuntimeError('D59 offline measurement: network forbidden')


sys.addaudithook(offline)
from data_sheets_schema import api_runner as api, shared_generation as sg
from data_sheets_schema import bc1_registration as sizing, bc1_context as context
from data_sheets_schema import bc1_runtime as runtime, bc1_selection as selection, bc1_codec as codec
from data_sheets_schema import receipt_completion as receipts, typed_audit_runtime as legacy
from data_sheets_schema import audit_batches as batches
from data_sheets_schema.schema_snapshot import capture_schema
from scripts import build_api_registrations as builder

BASE = '8dd00263a'
K1 = Path('/private/tmp/d4d-codex-k1-v2-20261026/notes/.local_drafts/k1_v2_a17_primary')
LAUNCH = ROOT.parent / 'launch-base/data/d4d_concatenated/claudecode_api_core'
LABELS = {'CHORUS': '2026-10-22a_claude-opus-5-api-generic-v10_rep1',
          'AI_READI': '2026-09-04g_claude-opus-5-api-generic-v8_rep2',
          'CM4AI': '2026-09-04g_claude-opus-5-api-generic-v8_rep1',
          'VOICE': '2026-09-04f_claude-opus-5-api-generic-v8_rep1'}
OUT = ROOT / 'notes/reviews/bc1_d59_measurements_2026-10-28.json'
SOURCE_PINS = {}


def read(path):
    path = Path(path)
    raw = path.read_bytes()
    SOURCE_PINS[str(path)] = {'bytes': len(raw), 'sha256': sg.sha(raw)}
    return raw


def original(module, name):
    path = Path(module.__file__).relative_to(ROOT)
    raw = subprocess.check_output(['git', 'show', f'{BASE}:{path}'], cwd=ROOT)
    tree = ast.parse(raw)
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
    namespace = dict(module.__dict__)
    exec(compile(ast.Module(body=[node], type_ignores=[]), f'{BASE}:{path}', 'exec'), namespace)
    return namespace[name]


def record(project):
    folder = K1 / project / LABELS[project] / 'a17/source_records'
    files = SimpleNamespace(full=folder / 'original_full.yaml', core=folder / 'original_core.yaml',
                            receipt=folder / 'receipt.yaml')
    for path in vars(files).values():
        read(path)
    files.receipt_result = LAUNCH / LABELS[project] / 'intermediate' / f'{project}_receipt_completion_result.json'
    return files


def captured(reg):
    snap = capture_schema(reg['inputs']['full_schema']['root'], strict=True)
    cap = sizing.capture_inputs(reg, context_raw=read(reg['inputs']['context']['path']), schema_snapshot=snap)
    files = dict(cap.files)
    files.update({name: raw for name, raw in sg.captured_assets().items()})
    if reg['runtime']['config']:
        pin = reg['runtime']['config']
        files[pin['path']] = read(pin['path'])
    for path, raw in cap.files:
        assert read(path) == raw
    for snapshot in (cap.full_schema, cap.core_schema):
        for _name, path, raw in snapshot.sources:
            assert read(path) == raw
    return sg.Capture(cap.registration, tuple(files.items()), cap.full_schema, cap.core_schema)


def spec_for(reg):
    inputs = reg['inputs']
    return api.RunSpec(**reg['run'], bundle=Path(inputs['bundle']['path']),
        chunk_manifest=Path(inputs['chunk_manifest']['path']),
        manifest=Path(inputs['source_manifest']['path']) if inputs['source_manifest'] else None,
        manifest_line=api.RunSpec.header_for_manifest(Path(inputs['source_manifest']['path'])) if inputs['source_manifest'] else '',
        profile=inputs['profile']['name'], profile_basis=inputs['profile']['basis'],
        condition='generic_v10', render_version=25, shared_generation_version=1,
        api_playbook_version=2, receipt_completion_version=2,
        receipt_completion_registration=sg.canonical(reg['receipt']).decode(),
        shared_generation_registration=sg.canonical(reg).decode(),
        bounded_carry_version=int('bounded_carry' in reg), run_date='2026-10-28',
        provider=reg['runtime']['provider'], runtime=api.RUNTIME,
        out_dir=ROOT / 'notes/reviews/UNWRITTEN_d59_render_destinations')


def metrics(payload):
    raw = sg.canonical(payload)
    room = 1_000_000 - payload['max_tokens']
    return {'wire_bytes': len(raw), 'sha256': sg.sha(raw), 'max_tokens': payload['max_tokens'],
            'room': room, 'tokens_2.48': math.ceil(len(raw) / 2.48),
            'tokens_2.77': math.ceil(len(raw) / 2.77),
            'fits_2.48': math.ceil(len(raw) / 2.48) <= room}


def downstream(reg, files, build, schema_fn, *, bounded, scenario):
    """Real production phase builder on saved records, explicit future carry bytes."""
    cap = captured(reg)
    with patch.object(sg, 'capture', lambda *_: cap):
        spec = spec_for(reg)
    settings = api._model_settings(spec.condition)
    folder = LAUNCH / LABELS['CHORUS']
    project = reg['run']['project']
    result_path = (files.receipt_result if project == 'CHORUS' else
                   folder / 'intermediate/CHORUS_receipt_completion_result.json')
    outcome = json.loads(read(result_path))
    outcome['journal'] = {'result': {'path': str(result_path), 'sha256': sg.sha(read(result_path))}}
    full, core = read(files.full).decode(), read(files.core).decode()
    reconciled = read(folder / 'intermediate/CHORUS_reconcile_full.yaml' if project == 'CHORUS'
                      else files.full.parent / 'reconciled_full.yaml').decode()
    audit = read(folder / 'intermediate/CHORUS_audit.json').decode()
    report = read(folder / 'CHORUS_reconciliation.md' if project == 'CHORUS'
                  else files.full.parent / 'report.md').decode()
    old_receipt = json.loads(read(folder / 'intermediate/CHORUS_receipt_completion_request.json'))
    if scenario == 'empty_future_floor':
        carry = ''
    elif scenario == 'visible_cap_ascii_scenario':
        carry = 'x' * codec.CARRY_BYTES
    else:
        carry = '\\' * codec.CARRY_BYTES
    output = {}
    with ExitStack() as stack:
        stack.enter_context(patch.object(sg, 'capture', lambda *_: cap))
        stack.enter_context(patch.object(sg, 'assert_current', lambda *_: cap))
        stack.enter_context(patch.object(receipts, 'recover', lambda *_: deepcopy(outcome)))
        stack.enter_context(patch.object(runtime, 'model_carry', lambda *_: carry))
        stack.enter_context(patch.object(context, 'schema_context', schema_fn))
        spec.bind_api_header_values(settings)
        for phase, artifacts in (
            ('full', {}),
            ('reconcile_full', {'Completed full record': full, 'Completed core record': core, 'Audit findings': audit}),
            ('report', {'Original full record': full, 'Original core record': core,
                        'Reconciled full record': reconciled, 'Completed core record': core, 'Audit findings': audit})):
            req = build(spec, phase, carry=artifacts)
            output[phase] = deepcopy(receipts.request_payload(req, settings, {'max_output_tokens': 128000}))
            if phase == 'full':
                # The saved continuation already contains the real full response,
                # actual missing-path inventory and selected receipt policy.
                cont = deepcopy(old_receipt)
                cont['system'] = req.system
                cont['messages'] = deepcopy(req.messages) + deepcopy(old_receipt['messages'][1:])
                if project != 'CHORUS':
                    # V8 has no receipt continuation. Only an explicitly labelled
                    # substitution estimate: own full response + own record/receipt
                    # inventory, retaining the CHORUS requested-path scaffold.
                    cont['messages'][1]['content'] = full
                    inventory = json.loads(cont['messages'][-1]['content'][0]['text'])
                    inventory['record_yaml'] = full
                    inventory['receipt_yaml'] = read(files.receipt).decode()
                    cont['messages'][-1]['content'][0]['text'] = sg.canonical(inventory).decode()
                output[receipts.PHASE] = cont
            if phase == 'report':
                api._append_regate(req, spec, report, [])
                output['report_regate'] = receipts.request_payload(req, settings, {'max_output_tokens': 128000})
        assert output['report'] != output['report_regate']
        if not bounded:
            packet = legacy._prepare_packet_bytes(spec, cap,
                {'original_full': read(files.full), 'original_core': read(files.core)}, read(files.receipt))
            for stage in legacy.roster(packet):
                if stage['phase'] == legacy.INTEGRATION_PHASE:
                    saved = json.loads(read(folder / 'intermediate/CHORUS_typed_audit_4_request.json'))
                    text = next(p['text'] for p in saved['messages'][0]['content']
                                if p['text'].startswith('# Exact typed stage request\n\n'))
                    # Render the observed integration inner bytes; do not invent
                    # accepted worker/omission responses to replay historical checks.
                    with patch.object(legacy, '_inner', lambda *_: json.loads(text.split('\n\n', 1)[1])):
                        _, wire, _ = legacy._build_request_bytes(spec, cap, packet, stage, {}, b'', settings,
                            generation='0' * 32, receipt_carry=receipts._audit_carry(outcome))
                else:
                    _, wire, _ = legacy._build_request_bytes(spec, cap, packet, stage, {}, b'', settings,
                        generation='0' * 32, receipt_carry=receipts._audit_carry(outcome))
                output[stage.get('worker_id', stage['phase'])] = wire
    return output


def main():
    read(ROOT.parent / 'plans/reviews/bc1_fit_calibration_claude_2026-10-28.md')
    old_build = original(api, 'build_phase')
    old_schema = original(context, 'schema_context')
    old_render = original(runtime, 'render_request')
    old_sizing = original(sizing, 'size_inputs')
    old_prepare = original(builder, 'prepare_registration')
    options = dict(project='CHORUS', label='offline_d59', partition='chorus',
                   registration_path=ROOT / 'notes/reviews/UNWRITTEN_d59_registration.json')
    parent, parent_outputs, _ = builder.prepare_registration(**options)
    if sys.argv[1:] == ['--pin-code-and-schema']:
        result = json.loads(OUT.read_bytes())
        captured(parent)
        result['source_pins'].update(SOURCE_PINS)
        result['bc1_contract'] = selection.contract_identity()
        for path, pin in result['source_pins'].items():
            raw = Path(path).read_bytes()
            assert pin == {'bytes': len(raw), 'sha256': sg.sha(raw)}, path
        OUT.write_bytes(sg.canonical(result) + b'\n')
        print('Pinned and rechecked the complete schema closures and BC1 source contract.', flush=True)
        return
    if sys.argv[1:] == ['--complete-project-estimates']:
        result = json.loads(OUT.read_bytes())
        chorus = result['CHORUS']
        result['other_projects'] = project_estimates(parent,
            {'own_plan_scenarios': chorus['totals']}, chorus['typed'])
        result['source_pins'].update(SOURCE_PINS)
        for path, pin in result['source_pins'].items():
            raw = Path(path).read_bytes()
            assert pin == {'bytes': len(raw), 'sha256': sg.sha(raw)}, path
        OUT.write_bytes(sg.canonical(result) + b'\n')
        print('Completed own-record downstream estimates without repeating unchanged CHORUS renders.', flush=True)
        return
    before_parent, before_outputs, _ = old_prepare(**options)
    assert sg.canonical(parent) == sg.canonical(before_parent)
    assert parent_outputs == before_outputs
    files = record('CHORUS')
    nonbc1_before = downstream(parent, files, old_build, old_schema, bounded=False, scenario='empty_future_floor')
    nonbc1_after = downstream(parent, files, api.build_phase, context.schema_context, bounded=False, scenario='empty_future_floor')
    assert nonbc1_before.keys() == nonbc1_after.keys()
    parity = {}
    for phase in nonbc1_before:
        assert sg.canonical(nonbc1_before[phase]) == sg.canonical(nonbc1_after[phase]), phase
        parity[phase] = metrics(nonbc1_after[phase])
    print('Legacy registration and all rendered phase bodies are byte-identical.', flush=True)
    reg = deepcopy(parent)
    reg['bounded_carry'] = selection.registration_block(fan_in=2)
    reg['audit_limits'] = builder.resolve_audit_limits('CHORUS', 'chorus', bounded_carry_version=1)
    cap = captured(reg)
    args = dict(sizing_record=files, context_raw=read(reg['inputs']['context']['path']), schema_snapshot=cap.full_schema)
    with patch.object(context, 'schema_context', old_schema), patch.object(runtime, 'render_request', old_render):
        before = old_sizing(reg, **args)
    wires = []
    after = sizing.size_inputs(reg, **args, payload_sink=lambda row, raw: wires.append((row, raw)))
    try:
        sizing.check_sizing_record(reg, after)
        gate = 'ACCEPTED'
    except ValueError as exc:
        gate = str(exc)
    by_old = {(sg.canonical(r['stage']), r['scenario']): r for r in before['rows']}
    typed = []
    for row, raw in wires:
        old = by_old.get((sg.canonical(row['stage']), row['scenario']))
        typed.append({**row, **metrics(json.loads(raw)),
                      'before_bytes': old['wire_bytes'] if old else None,
                      'before_tokens_2.48': math.ceil(old['wire_bytes'] / 2.48) if old else None,
                      'before_tokens_2.77': math.ceil(old['wire_bytes'] / 2.77) if old else None})
    totals = {}
    for scenario in after['own_plan_scenarios']:
        rows = [r for r in typed if r['scenario'] in ('captured_record', scenario)]
        totals[scenario] = {**after['own_plan_scenarios'][scenario],
            'tokens_2.48': sum(r['tokens_2.48'] for r in rows),
            'tokens_2.77': sum(r['tokens_2.77'] for r in rows)}
    ordinary = []
    for scenario in ('empty_future_floor', 'visible_cap_ascii_scenario', 'visible_cap_escaped_bound'):
        pre = downstream(reg, files, old_build, old_schema, bounded=True, scenario=scenario)
        post = downstream(reg, files, api.build_phase, context.schema_context, bounded=True, scenario=scenario)
        for phase in pre:
            ordinary.append({'phase': phase, 'scenario': scenario, 'before': metrics(pre[phase]), 'after': metrics(post[phase])})
    print('CHORUS typed and downstream renders complete; measuring other project substitutions.', flush=True)
    projects = project_estimates(parent, after, typed)
    # Recheck every file read through this helper, including ignored run evidence.
    for path, pin in SOURCE_PINS.items():
        raw = Path(path).read_bytes()
        assert pin == {'bytes': len(raw), 'sha256': sg.sha(raw)}, path
    result = {'baseline_commit': BASE, 'source_pins': SOURCE_PINS, 'bc1_contract': selection.contract_identity(),
        'protected_shared_generation_sha256': sg.sha(read(ROOT / 'src/data_sheets_schema/shared_generation.py')),
        'calibration': sizing.calibration(), 'registration_parity': {'equal': True,
            'bytes': len(sg.canonical(parent)), 'sha256': sg.sha(sg.canonical(parent))},
        'non_bc1_request_parity': parity, 'CHORUS': {'typed': typed, 'totals': totals,
            'allowance': reg['audit_limits']['aggregate_input_tokens'], 'gate': gate,
            'receipt_carry': after['receipt_completion_carry'], 'downstream': ordinary},
        'other_projects': projects,
        'limitations': ['Exact bytes of concrete rendered scenarios, not unobserved future BC1 responses.',
            'Downstream continuation uses the saved full response/inventory; future audit carry has floor/ASCII/escaped-cap scenarios.',
            'Regate uses saved 10-22a report plus an empty contradiction list (none saved for 10-22a).',
            'No actual provider token counts; integration admission uses 1.75, rounded conservatively below measured 1.755.',
            'No launchable registration or run directory was written.']}
    OUT.write_bytes(sg.canonical(result) + b'\n')
    print(json.dumps({'output': str(OUT), 'gate': gate, 'totals': totals}, indent=2), flush=True)


def project_estimates(parent, after, typed):
    """Same measured-component substitution as the independent fit report.

    Production refusals remain recorded, never bypassed to claim exact rendering.
    Each individual planned worker/group/final gets its own explicit estimate.
    """
    def escaped(text):
        return len(sg.canonical(text)) - 2
    def nested(text):
        return escaped(sg.canonical(text).decode()[1:-1])
    parts, plans, results = {}, {}, {}
    for project in LABELS:
        files = record(project)
        full, core, receipt = (read(getattr(files, key)).decode() for key in ('full', 'core', 'receipt'))
        bundle = read(ROOT / f'data/preprocessed/concatenated/{project}_preprocessed.txt').decode()
        manifest = read(ROOT / f'data/preprocessed/chunks/{project}_chunks.yaml').decode()
        ctx = read(ROOT / f'data/omission_contexts/{project.lower()}_omission_context.json').decode()
        plan = batches.make_plan(full, version=2, max_paths=80, max_inventory_bytes=12288,
                                 max_workers=4 if project == 'CHORUS' else 16)
        plans[project] = plan
        parts[project] = {'bundle': nested(bundle), 'full': nested(full), 'core': nested(core),
            'receipt': nested(receipt), 'manifest': nested(manifest), 'context_str': nested(ctx),
            'context_dict': escaped(sg.canonical(json.loads(ctx)).decode()),
            'inventory': escaped(sg.canonical(plan['inventory']).decode())}
        if project == 'CHORUS':
            continue
        reg = deepcopy(parent)
        reg['run']['project'] = reg['inputs']['project'] = project
        for key, path in [('bundle', f'data/preprocessed/concatenated/{project}_preprocessed.txt'),
                          ('chunk_manifest', f'data/preprocessed/chunks/{project}_chunks.yaml'),
                          ('context', f'data/omission_contexts/{project.lower()}_omission_context.json')]:
            reg['inputs'][key] = sg.file_pin(ROOT / path)
        reg['bounded_carry'] = selection.registration_block(fan_in=2)
        reg['audit_limits'] = builder.resolve_audit_limits(project, overrides={'max_paths': 80,
            'max_inventory_bytes': 12288, 'max_workers': 16, 'aggregate_input_tokens': 4000000}, bounded_carry_version=1)
        try:
            cap = captured(reg)
            sizing.size_inputs(reg, sizing_record=files, context_raw=ctx.encode(), schema_snapshot=cap.full_schema)
            refusal = None
        except ValueError as exc:
            refusal = str(exc)
        results[project] = {'production_refusal': refusal, 'workers': len(plan['workers']),
            'basis': 'Estimated substitution, not production render. Historical receipt carry uses CHORUS proxy; unknown own carry and small identity/owner/dictionary differences are excluded.',
            'registered_allowance': None, 'comparison_profile_allowance': 4000000, 'rows': []}
        result = results[project]
        result['downstream_basis'] = ('Production renderer on own original/reconciled records and report, '
            'with explicit future audit carry. CHORUS receipt outcome/count metadata proxy; '
            'receipt continuation is a record/receipt substitution estimate, not an observed v8 call.')
        result['downstream'] = []
        for scenario in after['own_plan_scenarios']:
            payloads = downstream(reg, files, api.build_phase, context.schema_context, bounded=True, scenario=scenario)
            result['downstream'].extend({'phase': phase, 'scenario': scenario, **metrics(payload)}
                                        for phase, payload in payloads.items())
    mults = {'worker': {'bundle': 1, 'full': 2, 'core': 1, 'receipt': 1, 'manifest': 1,
                        'context_str': 1, 'context_dict': 1, 'inventory': 1},
             'integration': {'bundle': 1, 'full': 2, 'core': 1, 'receipt': 1, 'manifest': 1,
                             'context_str': 1, 'context_dict': 1},
             'omission': {'bundle': 1, 'full': 2, 'receipt': 1, 'context_str': 1, 'context_dict': 1}}
    for project, result in results.items():
        deltas = {kind: sum(m * (parts[project][key] - parts['CHORUS'][key]) for key, m in fields.items())
                  for kind, fields in mults.items()}
        workers = plans[project]['workers']
        # The largest CHORUS worker envelope conservatively supplies the fixed tail.
        template = max((r for r in typed if r['stage']['phase'] == runtime.WORKER_PHASE), key=lambda r: r['wire_bytes'])
        labels = [(w['id'], 'worker', template) for w in workers]
        omission = next(r for r in typed if r['stage']['phase'] == runtime.OMISSION_PHASE)
        labels.append(('omission', 'omission', omission))
        for name, kind, base in labels:
            result['rows'].append(estimate_row(name, 'captured_record', kind, base['wire_bytes'] + deltas[kind]))
        for scenario in after['own_plan_scenarios']:
            for index in range(0, len(workers), 2):
                size = min(2, len(workers) - index)
                base = next(r for r in typed if r['scenario'] == scenario and
                            len(r['stage'].get('worker_ids', [])) == size)
                result['rows'].append(estimate_row(f'group-{index // 2 + 1:04}', scenario, 'integration',
                                                  base['wire_bytes'] + deltas['integration']))
            base = next(r for r in typed if r['scenario'] == scenario and r['stage'].get('stage_id') == 'final')
            result['rows'].append(estimate_row('final', scenario, 'integration', base['wire_bytes'] + deltas['integration']))
        result['totals'] = {scenario: {key: sum(r[key] for r in result['rows'] if r['scenario'] in ('captured_record', scenario))
            for key in ('wire_bytes', 'tokens_2.48', 'tokens_2.77', 'calibrated_tokens')}
            for scenario in after['own_plan_scenarios']}
        result['estimated_required_aggregate_allowance'] = max(t['calibrated_tokens'] for t in result['totals'].values())
    return results


def estimate_row(name, scenario, kind, size):
    reserve = 32000 if kind == 'omission' else 64000
    ratio = 1.75 if kind == 'integration' else 2.48
    return {'call': name, 'scenario': scenario, 'wire_bytes': size, 'room': 1000000 - reserve,
            'tokens_2.48': math.ceil(size / 2.48), 'tokens_2.77': math.ceil(size / 2.77),
            'calibrated_tokens': math.ceil(size / ratio)}


if __name__ == '__main__':
    main()
