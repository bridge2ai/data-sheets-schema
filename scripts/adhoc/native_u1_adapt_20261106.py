"""U1 #4354, 2026-11-06: adapt rejected donor hunks to M7 without protected edits.
Inputs: partially applied reference delta. Outputs: api_runner native branches,
M7 asset pins in native selection, and strict BC1 exclusion in native rendering.
"""
from pathlib import Path
import hashlib
ROOT = Path(__file__).resolve().parents[2]
p = ROOT / 'src/data_sheets_schema/api_runner.py'
s = p.read_text()
def replace(old, new):
    global s
    assert s.count(old) == 1, (old, s.count(old))
    s = s.replace(old, new)
replace('    shared_generation_registration: str | None = None\n', '''    shared_generation_registration: str | None = None
    native_shared_generation_version: int = 0
    native_shared_generation_registration: str | None = None
    _native_shared_generation_capture: Any = field(default=None, init=False, repr=False)
    _native_shared_generation_metadata: bytes | None = field(default=None, init=False, repr=False)
    _native_shared_runtime_capture: Any = field(default=None, init=False, repr=False)
    _native_shared_max_draft_checks: int | None = field(default=None, init=False, repr=False)
''')
replace('if self.condition == "generic_v10" and self.shared_generation_version != 1:', 'if self.condition == "generic_v10" and self.shared_generation_version != 1 and self.native_shared_generation_version != 1:')
start = s.index('        self.manifest = select_manifest(self.project, self.bundle, self.manifest)')
end = s.index('        if self.chunk_manifest is not None:\n            self.chunk_manifest = Path(self.chunk_manifest)', start)
block = s[start:end]
s = s[:start] + '''        if self.native_shared_generation_version == 1 and self._replay_only:
            # Native replay restores captured paths below, without live discovery.
            self._corpus_root = None
        else:
''' + ''.join('    ' + line if line.strip() else line for line in block.splitlines(True)) + s[end:]
replace('        from .shared_generation import select as select_shared\n        select_shared(self)\n', '        if not self.native_shared_generation_version:\n            from .shared_generation import select as select_shared\n            select_shared(self)\n')
replace('        if not self._replay_only:\n            # Retain the construction decision', '        if self.native_shared_generation_version:\n            from .native_shared_render import bind_selection\n            bind_selection(self)\n        if not self._replay_only:\n            # Retain the construction decision')
replace('        if any(k.startswith("receipt_completion_") for k in recorded):', '        if any(k.startswith("native_shared_") for k in recorded):\n            from .native_shared_render import validate_metadata\n            validate_metadata(recorded)\n        if any(k.startswith("receipt_completion_") for k in recorded):')
needle='                   shared_generation_registration=(recorded.get("shared_generation_registration") or {}).get("raw_json"),\n'
replace(needle, needle + '                   native_shared_generation_version=recorded.get("native_shared_generation_version", 0),\n                   native_shared_generation_registration=(recorded.get("native_shared_generation_registration") or {}).get("raw_json"),\n')
replace('        _remember_replay_origin(spec)\n        return spec', '        _remember_replay_origin(spec)\n        if spec.native_shared_generation_version:\n            from .native_shared_render import restore\n            restore(spec, recorded)\n        return spec')
replace('        policy_metadata = {}\n', '        policy_metadata = {}\n        if self.native_shared_generation_version:\n            from .native_shared_render import metadata\n            policy_metadata.update(metadata(self))\n')
needle='        if self.shared_generation_version:\n            from .shared_generation import captured_assets\n'
replace(needle, '        if self.native_shared_generation_version:\n            from .native_shared_selection import capture_assets\n            return [Path(a.pin.role[len("asset:"):]) for a in capture_assets()]\n' + needle)
replace('shared_generation_version: int = 0, bounded_carry_version: int = 0) -> dict[str, Any]:', 'shared_generation_version: int = 0, bounded_carry_version: int = 0, native_shared_generation_version: int = 0) -> dict[str, Any]:')
replace('                native_source_attribution_version, shared_generation_version)\n', '                native_source_attribution_version, shared_generation_version, bounded_carry_version)\n')
replace('    body = prompt_body(spec.base_prompt)\n', '    if getattr(spec, "native_shared_generation_version", 0) or spec.render_version == 26:\n        from .native_shared_render import instruction\n        return instruction(spec)\n    body = prompt_body(spec.base_prompt)\n')
replace('    if phase not in PHASES:\n', '    if getattr(spec, "native_shared_generation_version", 0) or spec.render_version == 26:\n        raise ValueError("native shared generation uses the registered native stage controller")\n    if phase not in PHASES:\n')
start = s.index('def execute(spec:')
pos = s.index('    if spec.condition == "tuned":', start)
s = s[:pos] + '    if getattr(spec, "native_shared_generation_version", 0) or spec.render_version == 26:\n        raise ValueError("native shared generation requires its separate native execution registration")\n' + s[pos:]
p.write_text(s)
p = ROOT / 'src/data_sheets_schema/native_shared_selection.py'
s = p.read_text()
for old, name in [('ec081dbb14049449989c56169de7bcd1563076667818c12b78571b5f15acb2db', 'src/download/prompts/d4d_generic_arm_prompt_v10.md'), ('22a553695536a822e9c7ae877663a9b251c889a6637c637e579c5c6e1c855b2e', '.claude/commands/d4d-uniform-rules-v2.md')]:
    assert s.count(old) == 1
    s = s.replace(old, hashlib.sha256((ROOT / name).read_bytes()).hexdigest())
p.write_text(s)
p = ROOT / 'src/data_sheets_schema/native_shared_render.py'
s = p.read_text().replace("'api_playbook_version', 'receipt_completion_version', 'removal_repair_version'):", "'api_playbook_version', 'receipt_completion_version', 'removal_repair_version',\n                'bounded_carry_version'):")
p.write_text(s)
# Preserve the rejected hunk record as scratch, not source junk.
(ROOT / 'src/data_sheets_schema/api_runner.py.rej').rename(ROOT.parent / 'scratch-native-u1/api_runner.donor-rejects.patch')
