"""Issue 5966 real dependency import, fresh caches and unchanged HOME refusal."""
from copy import deepcopy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest
from data_sheets_schema import native_helper_cache as cache
from data_sheets_schema import native_runtime_profiles as profiles
from data_sheets_schema import native_shared_runtime_values as values
from tests.test_native_synthetic_profiles import runtime


def reserved(runtime, root, name='attempt'):
    runtime=deepcopy(runtime)
    attempt=root/name;attempt.mkdir()
    runtime['environment']['PYSTOW_HOME']=str(attempt/'helper-cache')
    return {'runtime':runtime,'attempt_directory':str(attempt),'environment':dict(runtime['environment'])}


def test_real_term_validator_import_leaves_home_empty(runtime, tmp_path):
    value=reserved(runtime,tmp_path)
    path=cache.create_for_attempt(value)
    env={**value['environment'], 'PYTHONDONTWRITEBYTECODE':'1', 'PYTHONSAFEPATH':'1'}
    script=Path(__file__).parent/'fixtures/native_shared_execution/import_term_validator_cache.py'
    result=subprocess.run([sys.executable,'-P','-B',str(script)],env=env,cwd=tmp_path,
                          capture_output=True,text=True,timeout=120)
    assert result.returncode==0,result.stderr
    census=json.loads(result.stdout)
    assert census['HOME']==[] and 'README.md' in census['PYSTOW_HOME'] and 'oaklib' in census['PYSTOW_HOME']
    assert (path/'README.md').stat().st_size>0
    assert profiles.require_synthetic(value['runtime'])==value['runtime']


def test_previous_environment_reproduces_home_refusal(runtime,tmp_path):
    value=reserved(runtime,tmp_path)
    env={key:val for key,val in value['environment'].items() if key!='PYSTOW_HOME'}
    env.update(PYTHONDONTWRITEBYTECODE='1',PYTHONSAFEPATH='1')
    script=Path(__file__).parent/'fixtures/native_shared_execution/import_term_validator_cache.py'
    result=subprocess.run([sys.executable,'-P','-B',str(script)],env=env,cwd=tmp_path,
                          capture_output=True,text=True,timeout=120)
    assert result.returncode==0,result.stderr
    assert (Path(env['HOME'])/'.data/README.md').stat().st_size>0
    with pytest.raises(ValueError,match='HOME must contain no'):
        profiles.require_synthetic(value['runtime'])


def test_cache_is_exclusive_and_fresh_for_each_attempt(runtime,tmp_path):
    first=reserved(runtime,tmp_path,'one');one=cache.create_for_attempt(first)
    (one/'prior-data').write_text('Never reusable')
    with pytest.raises(FileExistsError):cache.create_for_attempt(first)
    second=reserved(runtime,tmp_path,'two');two=cache.create_for_attempt(second)
    assert two!=one and list(two.iterdir())==[]
    first['environment']['PYSTOW_HOME']=str(two)
    with pytest.raises(ValueError,match='differs'):cache.create_for_attempt(first)


def test_cache_rejects_existing_empty_directory_and_symlink(runtime,tmp_path):
    value=reserved(runtime,tmp_path);path=Path(value['environment']['PYSTOW_HOME'])
    path.mkdir()
    with pytest.raises(FileExistsError):cache.create_for_attempt(value)
    other=reserved(runtime,tmp_path,'other');Path(other['environment']['PYSTOW_HOME']).symlink_to(path)
    with pytest.raises(FileExistsError):cache.create_for_attempt(other)


def test_home_guard_still_refuses_any_entry(runtime):
    (Path(runtime['environment']['HOME'])/'innocent-cache').mkdir()
    with pytest.raises(ValueError,match='HOME must contain no'):
        profiles.require_synthetic(runtime)


@pytest.mark.parametrize('target',['HOME','HOME_CHILD','HOME_PARENT','OTHER_ATTEMPT'])
def test_cache_cannot_overlap_home_or_escape_its_attempt(runtime,tmp_path,target):
    value=reserved(runtime,tmp_path);home=Path(runtime['environment']['HOME'])
    selected={'HOME':home,'HOME_CHILD':home/'cache','HOME_PARENT':home.parent,'OTHER_ATTEMPT':tmp_path/'elsewhere'/'helper-cache'}[target]
    value['runtime']['environment']['PYSTOW_HOME']=str(selected)
    with pytest.raises(ValueError):cache.create_for_attempt(value)


def test_production_and_synthetic_require_same_explicit_cache(runtime):
    for synthetic in (True,False):
        changed=deepcopy(runtime)
        if not synthetic:
            changed.update(model='explicit-production-model',provider='firstParty',limits_basis='declared production fixture')
            changed['auth'].update(loggedIn=True,authMethod='claude.ai',apiProvider='firstParty',subscriptionType='fixture')
        values.validate_runtime_v2(changed)
        changed['environment'].pop('PYSTOW_HOME')
        with pytest.raises(ValueError,match='environment'):values.validate_runtime_v2(changed)


def test_model_file_tools_cannot_read_or_write_helper_cache(runtime,tmp_path):
    value=reserved(runtime,tmp_path);path=cache.create_for_attempt(value)
    (path/'README.md').write_text('cache content')
    root=Path(__file__).parents[1]
    controls=root/'notes/matched_cborg_2026-09-13/native_controls'
    previous=list(sys.path);sys.path[:0]=[str(controls),str(controls.parent)]
    try:
        spec=importlib.util.spec_from_file_location('cache_test_file_policy',controls/'native_file_policy.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        access=module.FileAccess({'readonly_lookups':{'repository':str(root),'inputs':[],
            'output_directories':[str(tmp_path/'outputs')]}},config_root=tmp_path/'cli_config')
        for tool in ('Read','Write'):
            assert access.classify(tool,{'file_path':str(path/'README.md'),'content':'tamper'})[0]=='not_prescribed'
    finally:sys.path[:]=previous
