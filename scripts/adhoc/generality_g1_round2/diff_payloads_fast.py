# Purpose: G1 re-review - exact leaf-by-leaf diff of before/after request payloads
# (capture_requests.py output), fast enough for 600 KB strings: line-level alignment,
# then token-level alignment inside each changed line. Prints every differing leaf
# path, its byte delta, and every insertion/deletion/replacement (truncated text).
# Inputs: argv[1] before JSON, argv[2] after JSON. Reviewer helper, 2026-10-30.
import json, re, sys, difflib
B = json.load(open(sys.argv[1])); A = json.load(open(sys.argv[2]))
canon = lambda x: json.dumps(x, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()
TOK = re.compile(r'[A-Za-z0-9_]+|\s+|.', re.S)

def edits(a, b):
    out = []
    la, lb = a.splitlines(True), b.splitlines(True)
    sm = difflib.SequenceMatcher(None, la, lb, autojunk=False)
    for t, i1, i2, j1, j2 in sm.get_opcodes():
        if t == 'equal':
            continue
        x, y = ''.join(la[i1:i2]), ''.join(lb[j1:j2])
        ta, tb = TOK.findall(x), TOK.findall(y)
        sm2 = difflib.SequenceMatcher(None, ta, tb, autojunk=False)
        for t2, p1, p2, q1, q2 in sm2.get_opcodes():
            if t2 != 'equal':
                out.append((t2, ''.join(ta[p1:p2]), ''.join(tb[q1:q2])))
    return out

def walk(a, b, path, out):
    if a == b:
        return
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b:
                out.append((path + '/' + k, 'key only in ' + ('after' if k not in a else 'before'), None)); continue
            walk(a[k], b[k], path + '/' + k, out)
    elif isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        for i, (x, y) in enumerate(zip(a, b)):
            walk(x, y, f'{path}/{i}', out)
    elif isinstance(a, str) and isinstance(b, str):
        ops = edits(a, b)
        out.append((path, f'string {len(a.encode())}->{len(b.encode())} bytes (delta {len(b.encode()) - len(a.encode())}), {len(ops)} edit(s)', ops))
    else:
        out.append((path, f'value {a!r} -> {b!r}', None))

for phase in sorted(set(B['payloads']) | set(A['payloads'])):
    a, b = B['payloads'].get(phase), A['payloads'].get(phase)
    print(f'=== {phase}: {len(canon(a))} -> {len(canon(b))} bytes (delta {len(canon(b)) - len(canon(a))})')
    out = []; walk(a, b, 'payload', out)
    for path, what, ops in out:
        print('  ', path, '|', what)
        for t, x, y in (ops or []):
            print(f'      {t}: before={x[:300]!r}')
            print(f'      {" " * len(t)}  after ={y[:300]!r}')
    print(f'   leaves changed: {len(out)}')
