# Purpose: Compare exact old/new notes_listing ASTs on retained path sets.
# Inputs: historical source/worktree paths explicitly recorded below.
# Outputs: benchmark logs/JSON beside this script (original behavior).
# Serves: #5019 / PR #5025; date: 2026-10-12.
# Historical helper: original body preserved verbatim after this header.
# Paths are session-specific; inspect and adapt before a future run.
# This copy was preserved after the original measurement, not rerun.
import ast, hashlib, json, os, time
from pathlib import Path
source = Path('/private/tmp/d4d-performance-instructions-5017-20261012/tests/conftest.py')
old_source = Path('/private/tmp/d4d-performance-timings-5016-20261012/tests/conftest.py')
def extract(path):
    tree = ast.parse(path.read_text())
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'notes_listing')
    scope = {'os': os}
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(path), 'exec'), scope)
    return scope['notes_listing']
old, new = extract(old_source), extract(source)
results = {}
for label, root in [('primary', Path('/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/notes')), ('clean_worktree', source.parents[1] / 'notes')]:
    rows, values = [], []
    for mode, fn in [('old', old), ('new', new), ('new', new), ('old', old)]:
        before = time.perf_counter(); value = fn(root); elapsed = time.perf_counter() - before
        digest = hashlib.sha256(b'\0'.join(os.fsencode(p) for p in sorted(value))).hexdigest()
        rows.append({'mode':mode, 'seconds':elapsed, 'paths':len(value), 'paths_digest':digest}); values.append(value)
    results[label] = {'runs':rows, 'all_equal':all(v == values[0] for v in values), 'scope':'os.walk default behavior; ignored and hidden entries included, directory links listed but not traversed; metadata only'}
output = {'old_source_sha256':hashlib.sha256(old_source.read_bytes()).hexdigest(), 'new_source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(), 'method':'Extract exact function AST only, alternating old/new/new/old serially; no whole conftest import', 'results':results, 'limits':['Primary tree may have concurrent writers; compare path digests before attributing differences.', 'Filesystem warm-cache effects and host load can affect elapsed times; no CI speedup inference.']}
Path(__file__).with_name('benchmark.json').write_text(json.dumps(output,indent=2)+'\n')
print(json.dumps(output))
