"""Propose gate bounds from saved prefix evidence and AST constants, 2026-11-13.

Inputs: all-project prefix handoff and its saved selection files; contract source.
Output: adjacent h3_gate_bounds_20261113.json. No production imports or execution.
Serves helper 3 environment-manifest/gate-schema assignment; lead decides values.
"""
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT.parent / 'codex-development-efficiency-20261111'
INPUT = REPORT / 'notes/development_efficiency_20261111/handoffs/codex-h3-all-project-prefix-and-cross-review-20261112.json'
CONTRACT = ROOT / 'src/data_sheets_schema/native_shared_contract.py'


def pin(path):
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def mapping(name):
    for node in ast.parse(CONTRACT.read_text()).body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
            return ast.literal_eval(node.value.args[0])
    raise ValueError(name)


def file_pins(value):
    if isinstance(value, dict):
        if {'path', 'bytes', 'sha256'} <= value.keys():
            yield {k: value[k] for k in ('path', 'bytes', 'sha256')}
        else:
            for child in value.values():
                yield from file_pins(child)
    elif isinstance(value, list):
        for child in value:
            yield from file_pins(child)


def main():
    source = json.loads(INPUT.read_text())
    projects = []
    for project in source['projects']:
        command = project['builder']['command']
        selection = Path(command[command.index('--output') + 1]) / 'selection.json'
        doc = json.loads(selection.read_text())
        unique = {}
        for item in file_pins(doc):
            previous = unique.setdefault(item['path'], item)
            assert item == previous
        projects.append({
            'project': project['project'], 'bundle_bytes': project['bundle']['bytes'],
            'source_documents': project['source_documents'], 'chunks': project['chunk_count'],
            'largest_chunk_bytes': project['largest_chunk_bytes'],
            'selection': pin(selection),
            'declared_authority_bytes_including_selection': len(selection.read_bytes()) + sum(x['bytes'] for x in unique.values()),
            'largest_declared_pin_bytes': max(x['bytes'] for x in unique.values()),
            'declared_pins': list(unique.values()),
        })
    ceilings, hard = mapping('BOUND_CEILINGS'), mapping('HARD_LIMITS')
    largest = max(p['bundle_bytes'] for p in projects)
    chunks = max(p['chunks'] for p in projects)
    authority = max(p['declared_authority_bytes_including_selection'] for p in projects)
    maxpin = max(p['largest_declared_pin_bytes'] for p in projects)
    values = {
        'max_authority_bytes': 16_000_000,
        'max_evidence_bytes': 256_000_000,
        'max_history_bytes': 48_000_000,
        'max_history_records': 1024,
        'max_input_bytes': 4_000_000,
        'max_inventory_bytes': 2_000_000,
        'max_paths_per_worker': 8192,
        'max_populated_paths': 32768,
        'max_request_bytes': 32_000_000,
        'max_response_bytes': 4_000_000,
        'max_submissions': 128,
        'max_workers': 64,
    }
    reasons = {
        'max_authority_bytes': f'Observed largest declared selection authority is {authority} bytes. Allocate 16MB for that fixed schema/asset closure plus project input; factor {16_000_000/authority:.3f}. New environment pin is not yet in this measurement and must be checked in successor rehearsal.',
        'max_evidence_bytes': 'Planning budget: 32MB mandatory finalization reserve plus 224MB working evidence; 224MB exceeds 64 workers at a mean 3MB saved evidence each (192MB) by 32MB. This is a mean-envelope assumption, not 64 times every per-response maximum.',
        'max_history_bytes': '32MB mandatory finalization reserve plus 16MB working history; at 1023 working rows this allows a mean over 15KB per row before finalization. Individual 4MB record ceiling is not expected for every row.',
        'max_history_records': '64 worker allowance times 12 transition/receipt rows plus 255 additional rows and one finalization row = 1024. This is a planning allowance, not a measured transition count.',
        'max_input_bytes': f'4MB is {4_000_000/largest:.3f} times the largest source bundle ({largest} bytes), and admits all measured declared files (largest {maxpin} bytes). It also admits the fixed 4MB original-full ceiling; equality to that separate hard ceiling is intentional.',
        'max_inventory_bytes': '2MB per worker allows a planning mean of 244 bytes per path at 8192 paths, or 488 bytes per path at half that occupancy. Source bytes do not bound serialized inventory expansion; rehearsal must measure it.',
        'max_paths_per_worker': f'8192 paths permits 256 planning paths per largest source chunk count ({chunks}) with 1024 additional paths: 28*256+1024. Workers actually partition generated output fields, not source chunks; this is a capacity assumption.',
        'max_populated_paths': f'32768 permits 1024 planning generated paths per largest chunk count ({chunks}) with 4096 additional paths: 28*1024+4096. Prefix source evidence cannot establish generated path count.',
        'max_request_bytes': f'32MB exceeds 64 copies of the largest bundle ({64*largest} bytes) by {32_000_000-64*largest} bytes. This conservatively allows repeated source/context plus envelope metadata; actual serialized requests remain to be measured.',
        'max_response_bytes': f'4MB gives {4_000_000/largest:.3f} times the largest bundle size; native typed responses have the stricter 2097152-byte hard limit. Actual generated response lengths are unknown before the model runs.',
        'max_submissions': '64 worker submissions plus three mandatory stage submissions leaves 61 additional submissions within 128. Additional correction/assembly cardinality is a planning allowance, not a measurement.',
        'max_workers': f'64 is the next power-of-two allowance above twice the largest source chunk count ({chunks}): 2*28=56, margin 8. AI_READI has 25 chunks and CHORUS has 8. Worker count is determined by generated populated paths/whole-field packing, so this is only a planning proxy.',
    }
    assert set(values) == set(ceilings) == set(reasons)
    rows = []
    for key in sorted(values):
        assert 0 < values[key] < ceilings[key]
        rows.append({'key': key, 'proposed': values[key], 'ceiling': ceilings[key],
                     'ceiling_headroom': ceilings[key]-values[key], 'derivation': reasons[key]})
    assert values['max_history_bytes'] > hard['finalization_reserve_history_bytes']
    assert values['max_evidence_bytes'] > hard['finalization_reserve_raw_bytes']
    assert values['max_history_records'] > hard['finalization_reserve_history_records']
    assert values['max_submissions'] >= 3
    assert maxpin <= values['max_input_bytes'] and authority <= values['max_authority_bytes']
    result = {
        'status': 'proposal_for_lead_decision_not_measured_execution_guarantee',
        'inputs': [pin(INPUT), pin(CONTRACT)], 'script': pin(Path(__file__)),
        'projects': projects, 'bounds': rows, 'values': values,
        'largest_bundle': {'project': 'AI_READI', 'bytes': largest, 'chunks': 25},
        'largest_chunk_count': {'project': 'CM4AI', 'chunks': chunks},
        'canary_admission': 'All measured CHORUS declared selection files and complete declared authority fit the proposal. Full execution sufficiency is unverified: output inventory, workers, history, request/response and evidence growth require successor rehearsal and canary measurement.',
        'limitations': [
            'Input sizes do not mathematically bound generated populated paths, worker packing, response lengths, or all evidence growth.',
            'Prefix evidence stops before runtime, preparation, composition, permission and execution registration; it does not measure those products.',
            'Environment manifest is new and absent from the historical prefix measurements; check final-format authority totals before registration.',
            'Per-artifact maxima are simultaneous refusal limits, not a guarantee that every artifact can saturate its maximum within aggregate budgets.',
            'No real binary, provider, model, probe, capture, reservation or production module was executed for this proposal.',
        ],
    }
    output = Path(__file__).with_suffix('.json')
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'output': pin(output), 'authority_max': authority, 'largest_pin': maxpin, 'values': values}, sort_keys=True))


if __name__ == '__main__':
    main()
