"""Issue 6233, 2026-11-14: real worker callback regressions on offline evidence.

Inputs: synthetic public run registration, JSON output path. Reopens genuine
verified admission and calls its fixed _load_live on a worker. No launch,
provider, native binary or reservation. Scratch evidence mutations are restored.
"""
from concurrent.futures import ThreadPoolExecutor
from inspect import isfunction
import hashlib
import json
from pathlib import Path
import sys
from types import MappingProxyType, ModuleType

from data_sheets_schema import native_execution_authority_v2 as authority
from data_sheets_schema import native_execution_registration_v2 as registration
from data_sheets_schema import native_shared_controller_orchestration as controller
from data_sheets_schema import native_shared_callback_orchestration as callbacks
from data_sheets_schema import native_shared_controls_orchestration as controls
from data_sheets_schema import native_shared_selection as selections


def mutation(modules, kind):
    stage = modules['data_sheets_schema.native_shared_stage']
    if kind == 'source':
        path = Path(stage.__file__)
        original = path.read_bytes()
        path.write_bytes(original + b'\n')
        def restore_source():
            path.write_bytes(original)
            assert path.read_bytes() == original
        return restore_source
    if kind == 'limit':
        contract = modules['data_sheets_schema.native_shared_contract']
        original = contract.HARD_LIMITS
        changed = dict(original)
        changed['failure_diagnostics_bytes'] -= 1
        contract.HARD_LIMITS = MappingProxyType(changed)
        return lambda: setattr(contract, 'HARD_LIMITS', original)
    if kind == 'alias':
        original = stage.typed
        changed = ModuleType(original.__name__)
        changed.__dict__.update(vars(original))
        def validator(*args, **kwargs):
            return original.check_worker(*args, **kwargs)
        changed.check_worker = validator
        stage.typed = changed
        return lambda: setattr(stage, 'typed', original)
    if kind == 'default':
        function = stage._Replay._request
        original = function.__defaults__
        function.__defaults__ = (stage.typed,)
        return lambda: setattr(function, '__defaults__', original)
    contract = modules['data_sheets_schema.native_shared_contract']
    function = contract.ArtifactPin.__repr__
    cells = [cell for cell in function.__closure__ or () if isfunction(cell.cell_contents)]
    if not cells:
        raise AssertionError('fixture lacks its real dataclass repr closure')
    cell = cells[0]
    original = cell.cell_contents
    def changed(*args, **kwargs):
        return original(*args, **kwargs)
    cell.cell_contents = changed
    return lambda: setattr(cell, 'cell_contents', original)


def main():
    raw = Path(sys.argv[1]).read_bytes()
    body = json.loads(raw)['registration']
    composition_body = json.loads(body['composition_raw_json'])
    selections.capture(json.loads(composition_body['selection_raw_json'])['registration_path'])
    checked = []
    reads = []
    tool = 2
    monitor = sys.monitoring
    def returned(code, offset, value):
        if code.co_name == '_checked_observations' and code.co_filename.endswith('native_shared_capture.py'):
            checked.append(len(value))
        elif code.co_name in ('read_regular', 'read_live_stream') and hasattr(value, 'captured'):
            reads.append(value.captured.pin)
        else:
            return monitor.DISABLE
    monitor.use_tool_id(tool, 'callback-prefix-regression')
    monitor.register_callback(tool, monitor.events.PY_RETURN, returned)
    monitor.set_events(tool, monitor.events.PY_RETURN)
    report = {'bindings': [], 'bytes': []}
    try:
        with authority.launch_derivations():
            with controls.loaded_controls() as projection:
                execution = registration.verified(raw, classifier_projection=projection)
            composition, spec, selection = controller.reconstruct_composition(
                execution['composition_raw_json'].encode())
            for kind in ('alias', 'default', 'closure', 'limit', 'source', 'bytes'):
                with callbacks.preloaded_callbacks(composition, spec, selection, execution, raw,
                        controller.render.commands(spec)) as resources:
                    with ThreadPoolExecutor(max_workers=1) as worker:
                        def load():
                            return worker.submit(resources.capture._load_live,
                                selection.registration.pin.path, _admission=resources.admission,
                                _catalogs=resources.catalogs).result()
                        first = load()
                        assert first._prefix.reusable
                        reads.clear()
                        repeated = load()
                        assert checked[-1] == 0 and repeated._prefix.reusable
                        assert set(first._prefix.owner.artifacts) <= {(pin.role, pin.path) for pin in reads}
                        assert {'transcript', 'control'} <= {pin.role for pin in reads}
                        report.setdefault('rereads', []).append({'case': kind, 'reads': len(reads),
                            'bytes': sum(pin.bytes for pin in reads),
                            'anchored_artifacts': len(first._prefix.owner.artifacts),
                            'checked_old_observations': checked[-1]})
                        if kind != 'bytes':
                            modules = {m.__name__: m for m in first._prefix.owner.guard.modules}
                            restore = mutation(modules, kind)
                            refusal = None
                            full_count = None
                            try:
                                if kind == 'source':
                                    try:
                                        load()
                                    except ValueError as exc:
                                        refusal = str(exc)
                                    else:
                                        raise AssertionError('changed source was accepted')
                                else:
                                    changed = load()
                                    assert not changed._prefix.reusable
                                    assert checked[-1] == len(changed.observations)
                                    full_count = checked[-1]
                            finally:
                                restore()
                            restored = load()
                            assert not restored._prefix.reusable
                            assert checked[-1] == len(restored.observations)
                            report['bindings'].append({'kind': kind, 'full_observations': full_count,
                                'restored_full_observations': checked[-1], 'reuse_stays_disabled': True,
                                'refusal': refusal})
                        else:
                            targets = {'transcript': first.transcript.path, 'control': first.control.path,
                                'journal': first.history.journal.pin.path,
                                'record': first.history.records[-1].pin.path,
                                'observation': first.observations[-1].pin.path}
                            for item in first.history.artifacts:
                                if item.pin.role == 'response':
                                    targets['response'] = item.pin.path
                                if item.pin.role == 'packet':
                                    targets['stage'] = item.pin.path
                            for role, path in targets.items():
                                target = Path(path)
                                original = target.read_bytes()
                                try:
                                    changed = b' ' + original[1:]
                                    assert changed != original
                                    target.write_bytes(changed)
                                    try:
                                        load()
                                    except ValueError as exc:
                                        refusal = str(exc)
                                    else:
                                        raise AssertionError('changed earlier bytes accepted: ' + role)
                                finally:
                                    target.write_bytes(original)
                                    assert target.read_bytes() == original
                                load()
                                report['bytes'].append({'role': role, 'refusal': refusal,
                                    'restored_sha256': hashlib.sha256(original).hexdigest()})
    finally:
        monitor.set_events(tool, 0)
        monitor.free_tool_id(tool)
    output = Path(sys.argv[2])
    payload = (json.dumps(report, sort_keys=True, indent=2) + '\n').encode()
    output.write_bytes(payload)
    assert output.read_bytes() == payload
    print(json.dumps({'output': str(output), 'sha256': hashlib.sha256(payload).hexdigest(),
                      'result': report}, indent=2))


if __name__ == '__main__':
    main()
