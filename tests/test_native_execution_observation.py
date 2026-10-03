"""No native subprocess: explicit fake results exercise the private observation."""
from copy import deepcopy
import json
from types import SimpleNamespace

import pytest
from data_sheets_schema import native_execution as execute


def observation_case(tmp_path):
    executable=tmp_path/'fake-not-executed';executable.write_bytes(b'fixture bytes only');executable.chmod(0o700)
    auth={'loggedIn':True,'authMethod':'claude.ai','apiProvider':'firstParty','subscriptionType':'synthetic'}
    value={'runtime':{'executable':{'path':str(executable),'version':'synthetic-v1'},'auth':auth},
           'environment':{'EXPLICIT':'test-only'},'working_directory':str(tmp_path)}
    return value,auth


def test_runtime_probe_uses_exact_env_and_filters_secrets_without_calling_native(tmp_path,monkeypatch):
    value,auth=observation_case(tmp_path);calls=[]
    def fake(argv,**kwargs):
        calls.append((argv,kwargs))
        return SimpleNamespace(stdout=b'synthetic-v1\n' if argv[-1]=='--version' else json.dumps({
            **auth,'unrecognized_credential':'SECRET-MUST-NOT-BE-RETAINED'}).encode())
    monkeypatch.setattr(execute.subprocess,'run',fake)
    out=execute._probe_runtime(value)
    assert out['checked'] and out['passed']
    assert out['auth']==auth and 'SECRET' not in json.dumps(out)
    assert [c[0][1:] for c in calls]==[['--version'],['auth','status','--json']]
    assert all(c[1]['env']==value['environment'] and c[1]['cwd']==value['working_directory']
               and c[1]['timeout']==30 and c[1]['check'] is True for c in calls)


@pytest.mark.parametrize('change',['logged_out','bool_alias','provider','subscription','missing','duplicate','nonfinite',
                                  'version','version_non_utf8','auth_non_mapping'])
def test_observed_auth_or_version_mismatch_is_not_a_pass(tmp_path,monkeypatch,change):
    value,auth=observation_case(tmp_path);body=deepcopy(auth);version=b'synthetic-v1\n'
    if change=='logged_out':body['loggedIn']=False
    elif change=='bool_alias':body['loggedIn']=1
    elif change=='provider':body['apiProvider']='different'
    elif change=='subscription':body['subscriptionType']='different'
    elif change=='missing':del body['authMethod']
    elif change=='version':version=b'foreign-v2\n'
    elif change=='version_non_utf8':version=b'\xff'
    raw=json.dumps(body).encode()
    if change=='duplicate':raw=b'{"loggedIn":true,"loggedIn":true}'
    elif change=='nonfinite':raw=b'{"loggedIn":NaN}'
    elif change=='auth_non_mapping':raw=b'[]'
    def fake(argv,**kwargs):return SimpleNamespace(stdout=version if argv[-1]=='--version' else raw)
    monkeypatch.setattr(execute.subprocess,'run',fake)
    with pytest.raises(ValueError):execute._probe_runtime(value)
