"""#5991 parent/child replacement regressions; no live effects, 2026-11-12."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import pytest
from data_sheets_schema import native_generation as cli
from data_sheets_schema import native_sequence_inputs as pins
from data_sheets_schema import native_subscription_guard as wire
from tests.test_native_review_bundle_v3 import current_evidence, evidence, reword


def arguments(tmp_path,bodies,command='capture-subscription-event'):
    flags=[command]; mapping={}
    for name in pins.BASE:
        path=tmp_path/(name+'.json'); path.write_bytes(bodies.get(name,b'{}'))
        mapping[name]={'path':str(path),'sha256':wire.sha(path.read_bytes())}
        if name!='ci': flags+=['--'+name.replace('_','-'),str(path)]
    flags+=['--output-directory',str(tmp_path/'NEVER-CAPTURED'),'--sequence-inputs',wire.canonical(mapping).decode()]
    return flags,mapping


def test_replacement_with_another_valid_review_set_reaches_no_capture(current_evidence,tmp_path,monkeypatch):
    from data_sheets_schema import native_launch_review as review
    from data_sheets_schema import native_subscription_capture as capture
    raw,bundle,word=current_evidence
    assert review.validate_bundle(raw,bundle,word,require_current=True)['account_quiet'] is True
    b=wire.strict_json(bundle); b['reviews'][0]['reviewer']='Another independent SYNTHETIC reviewer'
    changed,changed_word=reword(b,word)
    assert review.validate_bundle(raw,changed,changed_word,require_current=True)['account_quiet'] is True
    flags,mapping=arguments(tmp_path,{'registration':raw,'review':bundle,'launch_word':word})
    # Parent check completed; replace both documents with the other genuinely
    # accepted bundle/word join immediately before the child's first read.
    Path(mapping['review']['path']).write_bytes(changed)
    Path(mapping['launch_word']['path']).write_bytes(changed_word)
    def forbidden(*a,**kw): pytest.fail('replacement reached a capture/word effect')
    monkeypatch.setattr(capture,'capture_subscription',forbidden)
    monkeypatch.setattr(capture,'activate_capture_word',forbidden)
    with pytest.raises(ValueError,match='sequence input bytes differ from parent digest: review'):
        cli.main(flags)
    assert not (tmp_path/'NEVER-CAPTURED').exists()


@pytest.mark.parametrize('name',pins.BASE)
def test_every_parent_document_is_checked_before_registration_validation(tmp_path,monkeypatch,name):
    flags,mapping=arguments(tmp_path,{})
    Path(mapping[name]['path']).write_bytes(b'{"different":"valid JSON"}')
    from data_sheets_schema import native_shared_registration_orchestration as registration
    monkeypatch.setattr(registration,'verified',lambda *a,**k:pytest.fail('changed input reached verification'))
    with pytest.raises(ValueError,match='sequence input bytes differ from parent digest: '+name):
        cli.main(flags)
    assert not (tmp_path/'NEVER-CAPTURED').exists()


def test_post_preflight_registration_replacement_is_checked_at_actual_read(tmp_path,monkeypatch):
    flags,mapping=arguments(tmp_path,{})
    original=pins.capture_expected
    def swapped(args):
        selected=original(args)
        Path(mapping['registration']['path']).write_bytes(b'{"later":"replacement"}')
        return selected
    monkeypatch.setattr(pins,'capture_expected',swapped)
    with pytest.raises(ValueError,match='sequence input bytes differ from parent digest: registration'):
        cli.main(flags)


def test_engine_checks_recaptured_authority_before_any_reservation(monkeypatch):
    from data_sheets_schema import native_execution_orchestration as engine
    raw={key:wire.canonical({'synthetic':key}) for key in ('review','ci','launch_word')}
    expected={key:wire.sha(body) for key,body in raw.items()}
    changed={**raw,'review':wire.canonical({'synthetic':'other internally shaped review'})}
    contract=SimpleNamespace(kind='d4d_native_shared_attempt',registration=SimpleNamespace(verified=lambda raw:{'runtime':{}}),
        composition=None,authority=None,gates=None,replay=None,shared=None)
    def forbidden(*a,**kw): pytest.fail('replacement reached an effect')
    effects=SimpleNamespace(**{name:forbidden for name in ('file','durable_new','sync_directory','mkdir_durable','signals','now','probe_runtime','expected_runtime_observation','unchanged')},
        sys=None,launch_guard=object(),authorizations=lambda *a,**kw:{'raw':changed})
    monkeypatch.setattr(engine,'_require_launch_profile',lambda *a:None)
    with pytest.raises(ValueError,match='captured launch authority differs from parent digests'):
        engine._launch(b'SYNTHETIC',review_path='unused',ci_path='unused',launch_word_path='unused',
            contract=contract,effects=effects,controls=SimpleNamespace(require_complete=lambda:None),expected_authority_sha256=expected)


def test_actual_capture_manifest_read_is_pinned(tmp_path):
    from data_sheets_schema import native_subscription_capture as capture
    path=tmp_path/'capture.json'; path.write_bytes(b'{"replacement":"saved bytes"}')
    authority=({}, {'quota_capture':{'kind':capture.LEGACY_REQUEST_KIND}}, {}, {})
    with pytest.raises(ValueError,match='capture manifest differs from parent digest'):
        capture._read_capture_records_at_root(path,tmp_path,authority,tmp_path,
            expected_manifest_sha256=wire.sha(b'{"previous":"saved bytes"}'))


@pytest.mark.parametrize('change',['missing','extra','path','digest'])
def test_closed_pin_roster_refuses(tmp_path,change):
    flags,mapping=arguments(tmp_path,{})
    if change=='missing':mapping.pop('ci')
    elif change=='extra':mapping['extra']=mapping['ci']
    elif change=='path':mapping['review']['path']=mapping['ci']['path']
    else:mapping['ci']['sha256']='bad'
    flags[-1]=wire.canonical(mapping).decode()
    with pytest.raises(ValueError,match='sequence input'):
        cli.main(flags)
