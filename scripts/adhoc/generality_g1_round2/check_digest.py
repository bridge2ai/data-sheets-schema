# Purpose: G1 review (F6) - run `d4d schema check-digest --strict` in-process
# (rebuilds each merged schema from source in a temp dir and compares bytes).
# Inputs: none (worktree root). Output: CLI text and exit code.
# Reviewer helper, generality G1 review (0ba88ba12), 2026-10-29.
from click.testing import CliRunner
from data_sheets_schema.cli import cli
r = CliRunner().invoke(cli, ['schema', 'check-digest', '--strict'])
print(r.output[-4000:]); print('EXIT', r.exit_code)
if r.exception and not isinstance(r.exception, SystemExit): raise r.exception
assert r.exit_code == 0, 'P4a finding 4 requires strict digest synchronization'
