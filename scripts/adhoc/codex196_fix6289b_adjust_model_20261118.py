"""Correct GitHub synthetic-credential masking in F3 node joins, 2026-11-18.
Input/output: the task's model helper. No code-worktree edits.
"""
from pathlib import Path
path = Path(__file__).with_name('codex196_fix6289b_model_20261118.py')
text = path.read_text()
old = "    pending = {}\n    floors = {}\n"
new = """    pending = {}
    floors = {}
    masked_prefix = 'tests/test_native_execution_ci_v2.py::test_repository_configuration_refuses_noncanonical_origin['
    masked_node = masked_prefix + '***github.com/o/r.git]'
    original_node = next(node for node in ordinary if node.startswith(masked_prefix + 'https://user:password'))
    def alias(node):
        return original_node if node == masked_node else node
"""
if old not in text:
    raise ValueError('model anchor differs')
text = text.replace(old, new, 1).replace(
    "Counter(item['node'] for item in row['starts'])", "Counter(alias(item['node']) for item in row['starts'])").replace(
    "Counter(item['node'] for item in row['finishes'])", "Counter(alias(item['node']) for item in row['finishes'])")
path.write_text(text)
