"""Apply #6015 lifecycle pin/readback repair to this checkout, 2026-11-12.

Input/output: native_execution_orchestration.py. No execution or network.
"""
from pathlib import Path

path = Path(__file__).resolve().parents[2] / 'src/data_sheets_schema/native_execution_orchestration.py'
text = path.read_text()
text = text.replace("final['failure_evidence'] = _failure_evidence(attempt)", """consumed = {**lifecycle_raw, 'registration.json': registration_raw,
                    'started.json': started_raw, 'subscription-guard.json': launch_guard.raw,
                    **{name + '.json': raw for name, raw in authorization['raw'].items()}}
                if prepared is not None:
                    for name in _FAILURE_MEMBERS:
                        body = prepared['snapshot'].raw.get(str(attempt / name))
                        if body is not None:
                            consumed.setdefault(name, body)
                final['failure_evidence'] = _failure_evidence(attempt, consumed=consumed)""")
text = text.replace('def _failure_evidence(attempt):', 'def _failure_evidence(attempt, *, consumed=None):')
text = text.replace('    out = {}\n    for name in _FAILURE_MEMBERS:', '    out = {}\n    consumed = consumed or {}\n    for name in _FAILURE_MEMBERS:')
old = """            out[name] = {'path': path, 'not_kept': type(exc).__name__ + ': ' + str(exc)}
    return out"""
new = """            out[name] = {'path': path, 'not_kept': type(exc).__name__ + ': ' + str(exc)}
        if name in consumed:
            raw = consumed[name]
            pin = {'path': path, 'bytes': len(raw), 'sha256': c.sha(raw)}
            if out[name] != pin:
                pin['changed_after_consumption'] = (
                    out[name].get('not_kept') or 'disk bytes differ from consumed bytes')
            out[name] = pin
    return out"""
assert old in text
text = text.replace(old, new)
text = text.replace('def _read_failure_diagnostic(registration_raw, *, contract, file):',
                    'def _read_failure_diagnostic(registration_raw, *, contract, file, expected_runtime_observation):')
text = text.replace("        c.exact(pin, {'path', 'bytes', 'sha256'}, 'failure evidence pin')", """        extra = {'changed_after_consumption'} if 'changed_after_consumption' in pin else set()
        c.exact(pin, {'path', 'bytes', 'sha256'} | extra, 'failure evidence pin')
        if extra and (type(pin['changed_after_consumption']) is not str or not pin['changed_after_consumption']):
            raise ValueError('failure evidence lacks its post-consumption change reason')""")
needle = "    contract.replay.validate_file_basis(value, result)"
assert text.count(needle) == 1
text = text.replace(needle, """    lifecycle = result.get('lifecycle_artifacts')
    if type(lifecycle) is not dict:
        raise ValueError('failure diagnostic lacks lifecycle identities')
    for name in ('runtime-observation.json', 'keep-awake.json'):
        pin = members[name]
        if ('not_kept' not in pin) != (name in lifecycle):
            raise ValueError('failure evidence and lifecycle membership disagree')
        if name in lifecycle and lifecycle[name] != {'path': pin['path'], 'sha256': pin['sha256']}:
            raise ValueError('failure evidence and lifecycle pins disagree')
    _check_lifecycle(value, result, attempt, file, expected_runtime_observation, completion=False)
""" + needle)
text = text.replace('diagnostic = _read_failure_diagnostic(registration_raw, contract=contract, file=effects.file)',
    'diagnostic = _read_failure_diagnostic(registration_raw, contract=contract, file=effects.file,\n        expected_runtime_observation=effects.expected_runtime_observation)')
start = text.index("    lifecycle = result.get('lifecycle_artifacts')", text.index('def read_final('))
end = text.index("    additional = result.get('additional_report')", start)
block = text[start:end]
helper = '''def _check_lifecycle(value, result, attempt, _file, expected_runtime_observation, *, completion):
    """Apply identical byte-based lifecycle checks to ordinary and failed readback."""
    checks = result['gates']
''' + block + '\n\n'
text = text[:start] + '    _check_lifecycle(value, result, attempt, _file, expected_runtime_observation, completion=completion)\n' + text[end:]
text = text.replace('def read_final(registration_raw,', helper + 'def read_final(registration_raw,')
path.write_text(text)
