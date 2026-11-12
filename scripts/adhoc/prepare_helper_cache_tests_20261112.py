#!/usr/bin/env python3
"""Wire current runtime fixtures and isolate issue 5966 offline runner, 2026-11-12.
Inputs: candidate fixtures/runner. Outputs: bounded test tooling and fixture declarations.
"""
from pathlib import Path
R=Path(__file__).resolve().parents[2]
def change(name,old,new):
 p=R/name;raw=p.read_text();assert raw.count(old)==1,(name,old);p.write_text(raw.replace(old,new))
change('src/data_sheets_schema/native_execution_authority_v2.py',"'native_shared_gate_primitives', 'native_shared_runtime_values', 'native_runtime_profiles',", "'native_shared_gate_primitives', 'native_shared_runtime_values', 'native_runtime_profiles', 'native_helper_cache',")
change('src/data_sheets_schema/native_shared_permissions.py',"    from . import native_runtime_profiles as profiles\n    contract, effects = _dependencies()", "    from . import native_runtime_profiles as profiles\n    from . import native_helper_cache as helper_cache\n    contract, effects = _dependencies()")
change('src/data_sheets_schema/native_shared_permissions.py',"('data_sheets_schema.native_runtime_profiles', profiles.__file__),", "('data_sheets_schema.native_runtime_profiles', profiles.__file__),\n                         ('data_sheets_schema.native_helper_cache', helper_cache.__file__),")
change('tests/test_native_execution_registration_v2.py',"'HOME': str(tmp_path.resolve()),", "'HOME': str(tmp_path.resolve() / 'runtime-home'),\n        'PYSTOW_HOME': str(tmp_path.resolve() / 'attempt' / 'helper-cache'),")
change('tests/test_native_u4b_runtime.py',"'HOME': str(root),", "'HOME': str(root / 'runtime-home'),\n                        'PYSTOW_HOME': str(root / 'attempt' / 'helper-cache'),")
change('tests/test_native_shared_permissions.py',"root / 'future-config', authority.dependency_identity())", "root / 'attempt' / 'cli_config', authority.dependency_identity())")
raw=(R/'scripts/adhoc/run_native_g07_tests_20261112.py').read_text()
raw=raw.replace('codex-native-main-integration-20261112','codex-native-helper-cache-home-20261112').replace('scratch-native-main-integration-20261112','scratch-h2-helper-cache-20261112')
(R/'scripts/adhoc/run_helper_cache_tests_20261112.py').write_text(raw)
