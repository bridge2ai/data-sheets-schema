"""Keep literal delimiters inside parameter IDs in F3 JUnit joins, 2026-11-18.
Input/output: task model helper; no source-worktree change.
"""
from pathlib import Path
path = Path(__file__).with_name('codex196_fix6289b_model_20261118.py')
text = path.read_text()
old = """        bits = node.split('::')
        classname = bits[0][:-3].replace('/', '.')
        if len(bits) > 2:
            classname += '.' + '.'.join(bits[1:-1])
        class_lookup[(classname, bits[-1])].add(node)
"""
new = """        filename, tail = node.split('::', 1)
        before, separator, parameters = tail.partition('[')
        parts = before.split('::')
        classname = filename[:-3].replace('/', '.')
        if len(parts) > 1:
            classname += '.' + '.'.join(parts[:-1])
        testname = parts[-1] + separator + parameters
        class_lookup[(classname, testname)].add(node)
"""
if old not in text:
    raise ValueError('join anchor differs')
path.write_text(text.replace(old, new, 1))
