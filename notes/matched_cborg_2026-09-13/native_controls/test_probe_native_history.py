"""Pure probe metadata/runtime-selection tests; never starts CLI or network."""
import json
from pathlib import Path
import pytest
import probe_native_history as probe


def test_import_and_case_roster_are_passive():
    assert probe.CLI_VERSION=='2.1.272'
    assert probe.CLI_SHA=='195e24e8e1f9bf46f1eaee72d434a33e18f9f5796f29a6348a00d16c5f8aee75'
    assert probe.CASES==('legacy_quick','selected_slow','selected_reject','selected_cancel','selected_deadline','legacy_slow')


def test_wrong_runtime_refused_before_any_execution(tmp_path,monkeypatch):
    binary=tmp_path/'fake-cli';binary.write_text('invented')
    monkeypatch.setattr(probe.subprocess,'check_output',lambda *a,**k:pytest.fail('unapproved executable'))
    with pytest.raises(ValueError,match='exact pinned runtime'):probe.validate_runtime(binary)


@pytest.mark.parametrize('version',['2.1.272 (Claude Code)','2.1.999 (Claude Code)','2.1.2720 (Claude Code)'])
def test_version_is_checked_on_the_selected_pinned_path(tmp_path,monkeypatch,version):
    binary=tmp_path/'fake-cli';binary.write_text('invented');seen=[]
    monkeypatch.setattr(probe,'sha',lambda path:probe.CLI_SHA)
    def run(argv,**kwargs):seen.append(argv);return version
    monkeypatch.setattr(probe.subprocess,'check_output',run)
    if version.startswith('2.1.272 '):assert probe.validate_runtime(binary)==binary
    else:
        with pytest.raises(ValueError,match='version changed'):probe.validate_runtime(binary)
    assert seen==[[str(binary),'--version']]


def row():
    return {'case':'selected_slow','passed':True,'selected_history_contract':True,'contract':{'version':3},
        'exit_code':0,'error_class':None,'stop_reason_code':'none','tool_executions':1,
        'observer_entered':True,'observer_finished':True,'observer_duration_seconds':4.01,'classifier_calls':1,
        'classification_followed_observer':True,'stop_duration_seconds':5.0,'counts':{'callback':1,'cancel':0,'decision':1},
        'fault_injected_cancel_frames':0,'controller_shutdown_snapshots':[{'unfinished_control_workers':0,'control_shutdown_complete':True}],
        'workers_alive_after_fixture_release':0,'ledger_rows':2,'unsettled_rows':0,'unfinished_proxy_handlers':0,
        'scripted_upstream_calls':2,'real_provider_calls':0,'evidence_sha256':{'transcript.jsonl':'a'*64}}


def test_public_summary_excludes_raw_debug_or_local_paths():
    value=row();value.update(local_root='/private/tmp/synthetic',model_text='PRIVATE MODEL TEXT',raw_request={'private':'body'})
    result=probe.public_summary('1'*40,{'notes/example.py':'b'*64},True,[value])
    encoded=json.dumps(result)
    assert result['passed'] is True and result['provider_calls']==0
    assert '/private/' not in encoded and 'PRIVATE' not in encoded and 'raw_request' not in encoded
    assert result['cases'][0]['observer_duration_seconds']>=4


@pytest.mark.parametrize('name',['/private/tmp/example.py','../example.py'])
def test_public_source_names_cannot_leak_absolute_paths(name):
    with pytest.raises(ValueError,match='relative'):probe.public_summary('1'*40,{name:'a'*64},True,[row()])


def test_changed_source_or_failed_case_cannot_be_passed():
    assert probe.public_summary('1'*40,{},False,[row()])['passed'] is False
    value=row();value['passed']=False
    assert probe.public_summary('1'*40,{},True,[value])['passed'] is False
