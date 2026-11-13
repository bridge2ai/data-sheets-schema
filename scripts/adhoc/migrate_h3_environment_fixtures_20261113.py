"""Migrate current registration fixtures and CLI to explicit manifest input, 2026-11-13."""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]

def replace(relative, old, new):
    path = ROOT / relative
    text = path.read_text()
    assert old in text, (relative, old)
    path.write_text(text.replace(old, new))

replace('src/data_sheets_schema/cli/prompt.py',
    '@click.option("--job-id",',
    '@click.option("--environment-manifest", required=True, type=click.Path(exists=True, dir_okay=False))\n@click.option("--job-id",')
replace('src/data_sheets_schema/cli/prompt.py',
    'max_draft_checks, run_date, out):', 'max_draft_checks, run_date, out, environment_manifest):')
replace('src/data_sheets_schema/cli/prompt.py',
    'envelope = preparation.prepare(selection, runtime_declaration, job_id=job_id,',
    'envelope = preparation.prepare(selection, runtime_declaration, job_id=job_id,\n            environment_manifest_path=environment_manifest,')
replace('tests/test_native_execution_registration_v2.py',
    '    calls = []\n',
    '    from data_sheets_schema import native_environment_manifest\n    environment_path = tmp_path.resolve() / "environment-manifest.json"\n    native_environment_manifest.write(environment_path)\n    calls = []\n')
replace('tests/test_native_execution_registration_v2.py',
    "'kwargs': {'job_id':", "'kwargs': {'environment_manifest_path': environment_path, 'job_id':")
replace('tests/test_native_execution_registration_v2.py',
    "assert body['kind'] == 'd4d_native_shared_preparation_v2'",
    "assert body['kind'] == 'd4d_native_shared_preparation_v3'")
replace('tests/test_native_execution_registration_v2.py',
    "'kind': registration.EXECUTION_KIND, 'schema_version': 2,",
    "'kind': registration.EXECUTION_KIND, 'schema_version': 3,")
replace('tests/utils/native_execution_carrier_v2.py',
    "'kind': registration.EXECUTION_KIND, 'schema_version': 2,",
    "'kind': registration.EXECUTION_KIND, 'schema_version': 3,")
replace('tests/test_native_shared_execution.py',
    '    with authority.launch_derivations():',
    '    from data_sheets_schema import native_environment_manifest\n    environment_path = parent / "environment-manifest.json"\n    native_environment_manifest.write(environment_path)\n    with authority.launch_derivations():')
replace('tests/test_native_shared_execution.py',
    "job_id='synthetic-native-execution', run_date=",
    "environment_manifest_path=environment_path, job_id='synthetic-native-execution', run_date=")

runner = ROOT / 'scripts/adhoc/run_h3_environment_tests_20261113.py'
source = ROOT / 'scripts/adhoc/run_native_g07_tests_20261112.py'
assert not runner.exists()
runner.write_text(source.read_text().replace('codex-native-main-integration-20261112',
    'codex-native-environment-manifest-20261113').replace('scratch-native-main-integration-20261112',
    'scratch-h3-environment-manifest-20261113'))
