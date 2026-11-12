#!/usr/bin/env python3
"""2026-11-12 #5993: bind the reviewed body to one live entry invocation.
Inputs: own branch source/test files; outputs: bounded source and fixture edits.
No commands, native binary, network or registration are executed.
"""
from pathlib import Path

root = Path(__file__).resolve().parents[2]
path = root / 'src/data_sheets_schema/native_launch_entry.py'
text = path.read_text()
text = text.replace("\n\ndef main(argv=None):", '''

_ACTIVE_INVOCATIONS = {}


def _require_invocation(namespace, args, raw, inputs):
    binding = _ACTIVE_INVOCATIONS.pop(id(namespace), None)
    if binding is None or not all(left is right for left, right in
            zip(binding, (namespace, args, raw, inputs))):
        raise ValueError('sequence body requires a live verified entry namespace')


def main(argv=None):''')
text = text.replace("'__package__':'data_sheets_schema','__file__':str(SEQUENCE_PATH)}", "'__package__':'data_sheets_schema','__file__':str(SEQUENCE_PATH),\n               '_entry_invocation':_require_invocation}")
text = text.replace("    return namespace['_run_verified'](args,verified_script=raw,\n        entry_inputs={Path(selected.registration):registration_raw,Path(selected.review):review_raw})", """    inputs={Path(selected.registration):registration_raw,Path(selected.review):review_raw}
    _ACTIVE_INVOCATIONS[id(namespace)]=(namespace,args,raw,inputs)
    try:
        return namespace['_run_verified'](args,verified_script=raw,entry_inputs=inputs)
    finally:
        _ACTIVE_INVOCATIONS.pop(id(namespace),None)""")
path.write_text(text)
path = root / 'src/data_sheets_schema/native_launch_sequence.py'
text = path.read_text().replace('def _run_verified(argv, *, verified_script, entry_inputs):\n', '''def _run_verified(argv, *, verified_script, entry_inputs):
    invocation = globals().get('_entry_invocation')
    if not callable(invocation):
        raise ValueError('sequence body requires a live verified entry namespace')
    invocation(globals(), argv, verified_script, entry_inputs)
''')
path.write_text(text)
path = root / 'tests/test_native_launch_sequence.py'
text = path.read_text().replace('from pathlib import Path\n', 'from pathlib import Path\nimport builtins\n', 1)
text = text.replace('from data_sheets_schema import native_launch_sequence as seq\n', 'from data_sheets_schema import native_launch_sequence as seq\nfrom data_sheets_schema import native_launch_entry as entry\n')
start = text.index('    # Unit tests exercise')
end = text.index('\n\n\n@pytest.fixture', start)
text = text[:start] + '    return entry.main(arguments)' + text[end:]
text = text.replace("    monkeypatch.setattr(seq.subprocess, 'run', refuse)\n", """    monkeypatch.setattr(seq.subprocess, 'run', refuse)
    # Test-only clock substitution AFTER the entry verifies and compiles the
    # real fixture-pinned bytes. Production has no clock/verification bypass.
    def fixture_exec(code, namespace):
        builtins.exec(code, namespace)
        namespace['_utc_now'] = seq._utc_now
    monkeypatch.setattr(entry, 'exec', fixture_exec, raising=False)
""")
text = text.replace('def test_isolated_real_subprocess_uses_only_copied_fake_command(tmp_path):', "@pytest.mark.parametrize('entry_module', ['native_launch_sequence', 'native_launch_entry'])\ndef test_isolated_real_subprocess_uses_only_copied_fake_command(tmp_path, entry_module):")
text = text.replace("bootstrap = 'import sys; sys.path.insert(0, sys.argv.pop(1)); from data_sheets_schema.native_launch_sequence import main; raise SystemExit(main())'", "bootstrap = \"import sys,runpy; sys.path.insert(0,sys.argv.pop(1)); name=sys.argv.pop(1); runpy.run_module(name,run_name='__main__',alter_sys=True)\"")
text = text.replace("str(root / 'src'), *argv(p)]", "str(root / 'src'), 'data_sheets_schema.' + entry_module, *argv(p)]")
path.write_text(text)
