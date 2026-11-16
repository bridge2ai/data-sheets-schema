"""Fix expectation origin scope and wrapper fixture for PR 5968, 2026-11-16.
Inputs: assigned source and existing regression. Outputs: bounded source edits.
"""
from pathlib import Path
root = Path(__file__).resolve().parents[2]
p = root / 'scripts/native_canary_saved_step.py'
s = p.read_text()
s = s.replace("        composed, spec, _ = reconstruct_composition(Path(data['composition_path']).read_bytes())\n        runtime = c.strict_json(composed['runtime_raw_json'].encode())", "        composition_raw = Path(data['composition_path']).read_bytes()\n        composed, _, _ = reconstruct_composition(composition_raw)")
s = s.replace("            effective = system + consumer.policy.command_guidance(composed['policy'], classifier_projection=controls)\n            value = consumer.permission_expectation(runtime, composed, spec, effective,", "            # RunSpec origins belong to this verified package lifetime.\n            selected, spec, _, runtime = consumer._selection(\n                composition_raw,\n                preparation_raw=composed['preparation_raw_json'].encode('utf-8'),\n                classifier_projection=controls)\n            if c.canonical(selected) != c.canonical(composed):\n                raise ValueError('permission expectation composition changed during reconstruction')\n            effective = system + consumer.policy.command_guidance(selected['policy'], classifier_projection=controls)\n            value = consumer.permission_expectation(runtime, selected, spec, effective,")
p.write_text(s)
p = root / 'tests/test_native_canary_packet_rehearsal.py'
s = p.read_text().replace("'dependencies':dependencies,'policy':{}}", "'dependencies':dependencies,'policy':{},'preparation_raw_json':'SYNTHETIC PREPARATION'}")
s = s.replace("spec=object(); controls=object(); active=[]; calls=[]", "spec=object(); foreign=object(); controls=object(); active=[]; calls=[]")
s = s.replace("lambda raw:(composed,spec,None)", "lambda raw:(composed,foreign,None)")
s = s.replace("    consumer=SimpleNamespace(policy=SimpleNamespace(command_guidance=guidance),permission_expectation=expectation)", "    def selection(raw, *, preparation_raw, classifier_projection):\n        assert active==['controls','consumer']\n        assert raw==b'SYNTHETIC MOCK' and preparation_raw==b'SYNTHETIC PREPARATION'\n        assert classifier_projection is controls\n        return composed,spec,None,{'scope':'SYNTHETIC'}\n    consumer=SimpleNamespace(policy=SimpleNamespace(command_guidance=guidance),permission_expectation=expectation,\n        _selection=selection)")
p.write_text(s)
p = root / 'tests/test_native_saved_expectation_scope.py'
s = p.read_text()
s = s.replace('import subprocess\n', 'import subprocess\nimport shutil\n\nimport pytest\n')
s = s.replace("def run_packet(tmp_path, project):\n", "def run_packet(tmp_path, project):\n    if shutil.which('sandbox-exec') is None:\n        pytest.skip('offline saved-step regression requires macOS sandbox-exec')\n")
p.write_text(s)
