"""Profile consumed integration stage with invented three-worker history.

Inputs: output directory. Outputs: profiles, metrics and immutable fixture pickle.
Variant advance assignment, 2026-11-15; no runtime or model launch.
"""
import cProfile
from dataclasses import asdict, replace
import json
from pathlib import Path
import pickle
import pstats
import sys
import time
from types import SimpleNamespace

from tests import test_native_shared_stages as f
from tests.test_typed_audit import supplied, replies

out = Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=True)


def consume(case, decision, raw):
    selection, execution, phase1, history = case
    response = f.artifact('response', decision.response.path, raw)
    base = len(history.observations) + 2
    read = f.artifact('observation', selection.role('observations_root') + f'/{base:06d}.json',
        f.c.canonical({'fixture': 'settled complete read', 'request': f.c.pin_dict(decision.request.pin)}))
    wrote = f.artifact('observation', selection.role('observations_root') + f'/{base+1:06d}.json',
        f.c.canonical({'fixture': 'first settled write', 'response': f.c.pin_dict(response.pin)}))
    history = replace(history, artifacts=history.artifacts + (response,), observations=history.observations + (read, wrote))
    payload = {'cursor': asdict(decision.cursor),
        'request_sha256': f.c.strict_json(decision.request.raw, max_bytes=selection.bounds()['max_request_bytes'])['request_sha256'],
        'response': f.c.pin_dict(response.pin), 'read_observation': f.c.pin_dict(read.pin),
        'response_observation': f.c.pin_dict(wrote.pin)}
    records, journal = f.stage.append_records(selection, execution, history, (('response_consumed', f.c.canonical(payload)),))
    return selection, execution, phase1, f.append(history, records, journal)


inputs = supplied.__wrapped__(out)
case = f.case.__wrapped__(inputs, SimpleNamespace(param={
    'full': b'name: Example\ndescription: Existing description.\nissued: 2026-10-05\n',
    'bounds': {'max_paths_per_worker': 1, 'max_workers': 3, 'max_submissions': 6}}))
data = None
if len(sys.argv) > 2 and sys.argv[2] == 'variant':
    from tests.native_shared_omission_fixture import build_native_fixture
    data = build_native_fixture(out / 'variant', registered_python=sys.executable)
    (out / 'fixture-data.pickle').write_bytes(pickle.dumps(data))
    print('Variant fixture built and persisted.', flush=True)
    selection = data['selection']
    def at(role, raw):
        return f.artifact(role, selection.role(role), raw)
    runtime = f.artifact('runtime', str(data['runtime_path']), data['runtime_path'].read_bytes())
    execution = replace(case[1], selection_sha256=selection.registration.pin.sha256,
                        runtime_declaration=runtime, runtime_declaration_sha256=runtime.pin.sha256)
    phase1 = replace(case[2], full=at('phase1_full', data['full_raw']),
                     original_receipt=at('phase1_receipt', data['receipt_raw']),
                     seal=at('phase1_seal', b'{"fixture":"sealed full/receipt"}'))
    history = replace(case[3], records=(), artifacts=(), observations=(),
        journal=at('journal', f.stage.journal_bytes(selection_sha256=selection.registration.pin.sha256,
            execution_sha256=execution.execution.pin.sha256, attempt_id=execution.attempt_id, records=())))
    entries = (
        ('genesis', f.c.canonical({'execution': f.c.pin_dict(execution.execution.pin), 'started': f.c.pin_dict(execution.started.pin)})),
        ('session_bound', f.c.canonical({'binding': f.c.pin_dict(execution.binding_artifact.pin), 'init_observation': f.c.pin_dict(execution.init_observation.pin)})),
        ('phase1_sealed', f.c.canonical({'seal': f.c.pin_dict(phase1.seal.pin), 'full': f.c.pin_dict(phase1.full.pin),
            'original_receipt': f.c.pin_dict(phase1.original_receipt.pin), 'observation': f.c.pin_dict(phase1.full_seal_observation.pin)})))
    records, journal = f.stage.append_records(selection, execution, history, entries)
    case = selection, execution, phase1, f.append(history, records, journal)
decision = f.stage.prepare_next(*case)
case = (*case[:3], f.publish(case[3], decision))
decision = f.stage.prepare_next(*case)
raw = f.receipt_answer(case) if data is None else data['response_for'](decision.request.raw)
consumed = consume(case, decision, raw)
transition = f.stage.check_response(*consumed, decision.request.raw, raw)
assert transition.disposition == 'checked'
case = (*consumed[:3], f.append(consumed[3], transition.records_to_append, transition.predicted_journal,
    tuple(pub.artifact for pub in transition.publications)))
print('Receipt completed.', flush=True)
wait = f.stage.prepare_next(*case)
case = (*case[:3], f.publish(case[3], wait))
if data is None:
    case = f.add_core(case)
else:
    selection, execution, phase1, history = case
    phase1 = replace(phase1, core=at('phase1_core', data['core_raw']),
        core_seal=at('core_seal', b'{"fixture":"core sealed"}'),
        core_seal_observation=f.artifact('observation', '/neutral/core-observation.json', b'{"fixture":"core helper"}'))
    payload = {'seal': f.c.pin_dict(phase1.core_seal.pin), 'core': f.c.pin_dict(phase1.core.pin),
               'observation': f.c.pin_dict(phase1.core_seal_observation.pin)}
    records, journal = f.stage.append_records(selection, execution, history, (('core_sealed', f.c.canonical(payload)),))
    case = selection, execution, phase1, f.append(history, records, journal)
metrics = []
while True:
    decision = f.stage.prepare_next(*case)
    if data is None:
        packet = f.stage._Replay(*case).run().packet
        workers, omission, delta, _ = replies(packet, 2)
        raw = workers[decision.cursor.target_id] if decision.cursor.kind == 'worker' else f.c.canonical(
            omission if decision.cursor.kind == 'omission' else delta)
    else:
        raw = data['response_for'](decision.request.raw)
    case = (*case[:3], f.publish(case[3], decision))
    decision = f.stage.prepare_next(*case)
    consumed = consume(case, decision, raw)
    name = decision.cursor.kind + '-' + str(decision.cursor.ordinal)
    if decision.cursor.kind == 'integration':
        (out / 'consumed-integration.pickle').write_bytes(pickle.dumps((consumed, decision.request.raw, raw)))
    profile = cProfile.Profile()
    wall, cpu = time.monotonic(), time.process_time()
    profile.enable()
    transition = f.stage.check_response(*consumed, decision.request.raw, raw)
    profile.disable()
    row = {'stage': name, 'records': len(consumed[3].records),
           'wall_seconds': time.monotonic() - wall, 'cpu_seconds': time.process_time() - cpu,
           'disposition': transition.disposition}
    metrics.append(row)
    print(json.dumps(row), flush=True)
    profile.dump_stats(str(out / (name + '.prof')))
    with (out / (name + '.txt')).open('w') as stream:
        pstats.Stats(profile, stream=stream).sort_stats('cumulative').print_stats(45)
    (out / 'metrics.json').write_text(json.dumps(metrics, indent=2))
    assert transition.disposition == 'checked'
    if decision.cursor.kind == 'integration':
        break
    updated = f.append(consumed[3], transition.records_to_append, transition.predicted_journal,
                       tuple(pub.artifact for pub in transition.publications))
    case = (*consumed[:3], updated)
