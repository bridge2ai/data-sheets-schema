"""Select unchanged U3-B API/BC1/S7/typed regression suites, 2026-11-07.

Inputs: committed test paths. Outputs: scratch roster, bounded launcher log.
Each group is a separate quiet-aware, network-denied, two-worker invocation.
"""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-native-u3b'
groups = {
    'api': ('test_api_*.py', 'test_source_heading*.py', 'test_renderer_contract_captures.py'),
    'shared': ('test_shared_generation*.py', 'test_typed_audit*.py', 'test_audit_omission*.py'),
    'bc1': ('test_bc1*.py', 'test_wave7*bc1*.py'),
    'schema': ('test_*schema_snapshot*.py', 'test_native_schema_metadata_reuse.py',
               'test_native_shared_selection.py', 'test_native_u3b_reuse.py',
               'test_cache_dependencies*.py', 'test_schema_cache*.py',
               'test_schema_digest_cache.py', 'test_schema_view.py', 'test_historical_digest_cache.py'),
}
groups['api-short'] = groups['api']
groups['schema-final'] = groups['schema']
groups['api-routing'] = ('test_source_heading_runtime_api.py',)
groups['api-portable'] = ('test_source_heading_runtime_api.py',)
groups['bc1-final'] = groups['bc1']
groups['bc1-base'] = groups['bc1']
groups['bc1-pending-collect'] = groups['bc1']
group = sys.argv[1]
files = sorted({p.relative_to(ROOT).as_posix() for pattern in groups[group]
                for p in (ROOT / 'tests').glob(pattern)})
if group in ('api', 'api-short'):
    files.append('tests/test_download/test_api_runner.py')
if group == 'api-short':
    files.remove('tests/test_source_heading_runtime_api.py')
extra = []
if group == 'api-routing':
    extra = ['-k', 'not test_actual_completed_capture_is_portable_and_refuses_changed_bytes']
elif group == 'api-portable':
    files = ['tests/test_source_heading_runtime_api.py::test_actual_completed_capture_is_portable_and_refuses_changed_bytes']
(SCRATCH / (group + '-roster.txt')).write_text('\n'.join(files) + '\n')
tree = ['--tree', str(SCRATCH / 'base')] if group == 'bc1-base' else []
raise SystemExit(subprocess.call([sys.executable, str(ROOT / 'scripts/adhoc/validate_native_u3b.py'),
    group, *tree, *files, *extra, *sys.argv[2:], '-q', '--tb=short', '--junitxml=' + str(SCRATCH / (group + '.xml'))], cwd=ROOT))
