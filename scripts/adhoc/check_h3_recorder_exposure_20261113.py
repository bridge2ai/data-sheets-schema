"""6065 focused development assertion over the two saved replay snapshots.

Inputs: recorder-replay-02 snapshots. Output: exact changed-artifact inventory,
verified dependent hash pairs and unresolved artifacts. Not an equivalence gate.
Only the specified command edit, supporting environment/source changes and the
expected missing-environment fixture refusal are admitted. 2026-11-13.
"""
from pathlib import Path
import hashlib
import json
import shlex

R = Path(__file__).resolve().parents[2]
OUT = R.parent / 'scratch-h3-recorder-20261113/recorder-replay-02'
paths = [OUT / 'comparison' / (side + '.json') for side in ('left', 'right')]
left, right = [json.loads(p.read_bytes())['artifacts'] for p in paths]
def sha(raw): return hashlib.sha256(raw).hexdigest()
def enc(value): return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(',', ':'))
assert left.keys() == right.keys()
old = left['commands']['recorder']
index = old.index('--render-spec-json')
spec = left['render_spec']
assert spec == right['render_spec']
assert json.loads(old[index + 1]) == spec
new = old[:index] + ['--render-spec-env', 'D4D_RENDER_SPEC', '--render-spec-sha256', sha(enc(spec).encode())] + old[index + 2:]
assert right['commands']['recorder'] == new
assert {k:v for k,v in left['commands'].items() if k != 'recorder'} == {k:v for k,v in right['commands'].items() if k != 'recorder'}
old_line, new_line = shlex.join(old), shlex.join(new)
assert left['instruction'].replace(old_line, new_line) == right['instruction']
substitutions = {old_line: new_line}
def bash_rule(line):
    return 'Bash(' + line.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)') + ')'
# Same lossless Bash-rule codec as the accepted replay aid.
substitutions[bash_rule(old_line)] = bash_rule(new_line)
hashes = {}
def remember(before, after, basis, encoding):
    key, value = sha(before), sha(after)
    if key in hashes:
        assert hashes[key]['right'] == value, 'conflicting dependent hash interpretation'
    else:
        hashes[key] = {'right': value, 'basis': basis, 'encoding': encoding}
def bind(a, b, basis):
    for before, after in ((enc(a).encode(), enc(b).encode()),):
        if before != after: remember(before, after, basis, 'canonical_json')
    if isinstance(a, str) and isinstance(b, str) and a != b:
        remember(a.encode(), b.encode(), basis, 'utf8')
def rewrite(text):
    for before, after in substitutions.items(): text = text.replace(before, after)
    for before, row in hashes.items(): text = text.replace(before, row['right'])
    return text
def same(a, b):
    if type(a) is not type(b): return False
    if enc(a) == enc(b): return True
    if isinstance(a, dict): return a.keys() == b.keys() and all(same(a[k], b[k]) for k in a)
    if isinstance(a, list):
        if a == old and b == new: return True
        return len(a) == len(b) and all(same(x,y) for x,y in zip(a,b))
    if isinstance(a, str):
        if rewrite(a) == b: return True
        # Decode only exact canonical JSON carriers, preserving their encoding.
        try:
            aa, bb = json.loads(a), json.loads(b)
            if enc(aa) == a and enc(bb) == b: return same(aa, bb)
        except (ValueError, TypeError): pass
    return False
verified = {}
support = ['source_code/src/data_sheets_schema/' + name for name in (
    'cli/provenance.py', 'native_shared_permissions.py', 'native_shared_registration.py', 'native_shared_render.py')]
for name in support:
    verified[name] = 'explicitly reviewed supporting implementation change'
    bind(left[name], right[name], name)
for name in ('commands', 'instruction'):
    verified[name] = 'exact recorder command substitution'
    bind(left[name], right[name], name)
before_refusal = {'exit_code': 1, 'stderr': 'Error: --prompt-text-env: D4D_LAUNCH_INSTRUCTION is not set; the launcher sets it to the exact saved launch instruction\n', 'stdout': '', 'uncaught_exception_type': None}
after_refusal = {'exit_code': 1, 'stderr': 'Error: --render-spec-env: D4D_RENDER_SPEC is not set; the launcher supplies the exact registered specification\n', 'stdout': '', 'uncaught_exception_type': None}
assert left['helper_cli/recorder'] == before_refusal and right['helper_cli/recorder'] == after_refusal
verified['helper_cli/recorder'] = 'explicit expected fixture refusal; no successful native26 recorder observation in this replay'
bind(before_refusal, after_refusal, 'helper_cli/recorder')
# Supporting expectation adds exactly the controller-built specification value.
expected = json.loads(enc(left['permission_expectation']))
expected['permission_environment']['D4D_RENDER_SPEC'] = enc(spec)
assert right['permission_expectation']['permission_environment']['D4D_RENDER_SPEC'] == enc(spec)
left_for_check = {**left, 'permission_expectation': expected}
def nodes(a, b, location):
    yield a, b, location
    if isinstance(a, dict) and isinstance(b, dict):
        for key in a.keys() & b.keys(): yield from nodes(a[key], b[key], location + '/' + key)
    elif isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        for i,(x,y) in enumerate(zip(a,b)): yield from nodes(x,y, location + '/' + str(i))
for iteration in range(100):
    previous = (len(hashes), len(verified))
    for name in left:
        for a,b,location in nodes(left_for_check[name], right[name], name):
            if same(a,b): bind(a,b,location)
        if same(left_for_check[name], right[name]): verified.setdefault(name, 'unchanged bytes or only verified command/hash dependencies')
    if previous == (len(hashes), len(verified)): break
remaining = [name for name in left if name not in verified]
model_remaining = [name for name in remaining if name != 'permission_expectation']
helper_exceptions = {side: [{'artifact': key, 'exception': value['uncaught_exception_type']}
    for key, value in artifacts.items() if key.startswith('helper_cli/')
    and value.get('uncaught_exception_type') is not None]
    for side, artifacts in (('left', left), ('right', right))}
unresolved_details = []
def explain(a, b, location):
    if same(a,b): return
    if isinstance(a, dict) and isinstance(b, dict) and a.keys() == b.keys():
        for key in a: explain(a[key], b[key], location + '/' + key)
    elif isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        for i,(x,y) in enumerate(zip(a,b)): explain(x,y,location + '/' + str(i))
    else: unresolved_details.append({'location': location, 'left': a, 'right': b})
for name in remaining: explain(left_for_check[name], right[name], name)
result = {'scope': 'Focused 6065 development assertion, not registration equivalence',
    'checker_sha256': sha(Path(__file__).read_bytes()),
    'snapshots': {p.name: sha(p.read_bytes()) for p in paths}, 'iterations': iteration + 1,
    'unchanged': sum(enc(left[k]) == enc(right[k]) for k in left), 'verified': verified,
    'hash_pairs': hashes, 'unresolved': remaining, 'unresolved_details': unresolved_details,
    'model_unresolved': model_remaining,
    'helper_exceptions': helper_exceptions,
    'captured_bytes_explained': not model_remaining,
    'supporting_unresolved': [name for name in remaining if name == 'permission_expectation'],
    'status': 'explained_model_projection' if not model_remaining and not any(helper_exceptions.values()) else 'hold',
    'recorder_line': new_line, 'recorder_line_characters': len(new_line),
    'previous_recorder_line_characters': len(old_line),
    'instruction_bytes': {'before': len(left['instruction'].encode()), 'after': len(right['instruction'].encode())}}
(OUT / 'exposure-check.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({key: result[key] for key in ('status', 'unchanged', 'unresolved', 'iterations', 'recorder_line_characters')}))
