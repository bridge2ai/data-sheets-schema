#!/usr/bin/env python3
"""Apply issue 5966 explicit attempt-local PyStow environment wiring, 2026-11-12.
Inputs: selected candidate files. Outputs: reviewed source and fixture changes.
No model/provider/native execution; no protected file edit.
"""
from pathlib import Path
R=Path(__file__).resolve().parents[2]
def change(name,old,new):
 p=R/name;raw=p.read_text();assert raw.count(old)==1,(name,old,raw.count(old));p.write_text(raw.replace(old,new))
p='src/data_sheets_schema/native_shared_runtime_values.py'
change(p,"POLICY_ENV = {", "V2_BASE_ENV_KEYS = BASE_ENV_KEYS | {'PYSTOW_HOME'}\nV2_ENV_REQUIRED = ENV_REQUIRED | {'PYSTOW_HOME'}\nPOLICY_ENV = {")
change(p,'def validate_runtime(value):','def validate_runtime(value, *, helper_cache=False):')
change(p,"    if type(env) is not dict or set(env) - BASE_ENV_KEYS or not ENV_REQUIRED <= set(env):", "    allowed = V2_BASE_ENV_KEYS if helper_cache else BASE_ENV_KEYS\n    required = V2_ENV_REQUIRED if helper_cache else ENV_REQUIRED\n    if type(env) is not dict or set(env) - allowed or not required <= set(env):")
change(p,"    if env['CLAUDE_CODE_DISABLE_1M_CONTEXT'] not in ('0', '1'):", "    if helper_cache:\n        from .native_helper_cache import declared_path\n        declared_path(env)\n    if env['CLAUDE_CODE_DISABLE_1M_CONTEXT'] not in ('0', '1'):")
change(p,'    return validate_runtime(value)\n','    return validate_runtime(value, helper_cache=True)\n')
p='src/data_sheets_schema/native_runtime_profiles.py'
change(p,'set(env) - v.BASE_ENV_KEYS or not v.ENV_REQUIRED <= set(env)', 'set(env) - v.V2_BASE_ENV_KEYS or not v.V2_ENV_REQUIRED <= set(env)')
change(p,"    awake = runtime['keep_awake']", "    from .native_helper_cache import declared_path\n    declared_path(env)\n    awake = runtime['keep_awake']")
p='src/data_sheets_schema/native_shared_registration.py'
change(p,"    return {**runtime['environment'], **POLICY_ENV,", "    from .native_helper_cache import for_attempt\n    cache = for_attempt(runtime['environment'], Path(config_directory).parent)\n    return {**runtime['environment'], **POLICY_ENV, 'PYSTOW_HOME': str(cache),")
change(p,"    protected += [Path(selected['runtime_path']), Path(value['runtime']['executable']['path'])]", "    protected += [Path(selected['runtime_path']), Path(value['runtime']['executable']['path']),\n                  Path(value['runtime']['environment']['HOME'])]\n    from .native_helper_cache import for_attempt\n    for_attempt(value['runtime']['environment'], value['attempt_directory'])")
p='src/data_sheets_schema/native_execution_orchestration.py'
change(p,"                _mkdir_durable(attempt/'cli_config')", "                _mkdir_durable(attempt/'cli_config')\n                if contract.kind == 'd4d_native_shared_attempt':\n                    from .native_helper_cache import create_for_attempt\n                    create_for_attempt(value)")
p='src/data_sheets_schema/native_shared_permissions.py'
change(p,'not set(env) - runtime_values.BASE_ENV_KEYS\n          and runtime_values.ENV_REQUIRED <= set(env)', 'not set(env) - runtime_values.V2_BASE_ENV_KEYS\n          and runtime_values.V2_ENV_REQUIRED <= set(env)')
change(p,"    _path(env['HOME'])", "    _path(env['HOME'])\n    from .native_helper_cache import declared_path\n    declared_path(env)")
change(p,"    _need(env['D4D_PROFILE'] == selection['inputs']['profile']['name'], 'environment profile differs')", "    from .native_helper_cache import for_attempt\n    for_attempt(runtime['environment'], _path(env['CLAUDE_CONFIG_DIR']).parent)\n    _need(env['D4D_PROFILE'] == selection['inputs']['profile']['name'], 'environment profile differs')")
change(p,"if key in ('CLAUDE_CONFIG_DIR', 'D4D_LAUNCH_INSTRUCTION') and value.startswith('/')", "if key in ('CLAUDE_CONFIG_DIR', 'D4D_LAUNCH_INSTRUCTION', 'PYSTOW_HOME') and value.startswith('/')")
p='src/data_sheets_schema/native_permission_probe.py'
change(p,'if key in ("CLAUDE_CONFIG_DIR", "D4D_LAUNCH_INSTRUCTION") and value.startswith("/")', 'if key in ("CLAUDE_CONFIG_DIR", "D4D_LAUNCH_INSTRUCTION", "PYSTOW_HOME") and value.startswith("/")')
for p in ['tests/native_shared_fixture.py','tests/native_shared_omission_fixture.py']:
 change(p,"'HOME': str(root),", "'HOME': str(root / 'runtime-home'),\n            'PYSTOW_HOME': str(root / 'native-attempt' / 'helper-cache'),")
change('tests/utils/native_synthetic_evidence.py',"'HOME': str(home), 'CLAUDE_SECURESTORAGE_CONFIG_DIR': '',", "'HOME': str(home), 'PYSTOW_HOME': str(root / 'native-attempt' / 'helper-cache'),\n            'CLAUDE_SECURESTORAGE_CONFIG_DIR': '',")
change('tests/test_native_synthetic_profiles.py',"'environment': {'PATH': '/usr/bin:/bin', 'HOME': str(home),", "'environment': {'PATH': '/usr/bin:/bin', 'HOME': str(home),\n            'PYSTOW_HOME': str(root / 'attempt' / 'helper-cache'),")
