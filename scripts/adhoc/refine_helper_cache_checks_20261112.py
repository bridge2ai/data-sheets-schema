#!/usr/bin/env python3
"""Tighten cache/source disjointness and add per-process offline network witnesses.
Inputs/output: helper-cache branch, issue 5966, 2026-11-12.
"""
from pathlib import Path
R=Path(__file__).resolve().parents[2]
def change(name,old,new):
 p=R/name;raw=p.read_text();assert raw.count(old)==1,(name,old);p.write_text(raw.replace(old,new))
change('tests/test_native_helper_cache.py','sys.path.insert(0,str(controls))','sys.path[:0]=[str(controls),str(controls.parent)]')
change('tests/test_native_synthetic_profiles.py',"    before = values._encoded(old)\n", "    current = deepcopy(old)\n    old['environment'].pop('PYSTOW_HOME')\n    before = values._encoded(old)\n")
change('tests/test_native_synthetic_profiles.py','    assert values._encoded(values.validate_runtime_v2(old)) == before',"    with pytest.raises(ValueError, match='environment'):\n        values.validate_runtime_v2(old)\n    assert values.validate_runtime_v2(current) == current")
change('src/data_sheets_schema/native_shared_registration.py',"    for_attempt(value['runtime']['environment'], value['attempt_directory'])", "    cache = for_attempt(value['runtime']['environment'], value['attempt_directory'])\n    if cache == ROOT or ROOT in cache.parents or cache in ROOT.parents:\n        raise ValueError('helper cache must be outside the source repository')")
change('src/data_sheets_schema/native_shared_permissions.py',"    for_attempt(runtime['environment'], _path(env['CLAUDE_CONFIG_DIR']).parent)", "    cache = for_attempt(runtime['environment'], _path(env['CLAUDE_CONFIG_DIR']).parent)\n    protected_cache = [policy['readonly_lookups']['repository'], *policy['readonly_lookups']['inputs'],\n                       *policy['readonly_lookups']['output_directories'], env['CLAUDE_CONFIG_DIR']]\n    for item in protected_cache:\n        other = _path(item)\n        _need(cache != other and cache not in other.parents and other not in cache.parents,\n              'helper cache overlaps model file authority or source')")
p=R/'scripts/adhoc/run_helper_cache_tests_20261112.py';raw=p.read_text()
old='    custom.write_text("# Native integration test environment; no external site hooks.\\n", encoding="utf-8")'
new='''    network_dir = out / "network-events"
    network_dir.mkdir()
    observer = Path(__file__).with_name('helper_cache_network_witness_20261112.py').read_text()
    custom.write_text("NETWORK_DIRECTORY = " + repr(str(network_dir)) + "\\n" + observer, encoding="utf-8")'''
assert raw.count(old)==1;p.write_text(raw.replace(old,new))
