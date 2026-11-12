"""#5990 load-once identity tests; no native command, capture or provider."""
from pathlib import Path
import pytest
from data_sheets_schema import native_launch_entry as entry
from data_sheets_schema import native_subscription_guard as wire
from tests import test_native_launch_sequence as fixture
from tests.test_native_launch_sequence import deny_real_commands


def test_verified_entry_retains_exact_executed_bytes(tmp_path,monkeypatch):
    p=fixture.paths(tmp_path)
    calls=fixture.fake_commands(monkeypatch,p)
    original=entry.SEQUENCE_PATH.read_bytes()
    assert entry.main(fixture.argv(p))==0
    assert len(calls)==3
    assert (p['packet-directory']/'sequence-script.py').read_bytes()==original


def setup_source(tmp_path,monkeypatch,raw):
    p=fixture.paths(tmp_path); script=tmp_path/'sequence.py'; script.write_bytes(raw)
    monkeypatch.setattr(entry,'SEQUENCE_PATH',script)
    reg=wire.strict_json(p['registration'].read_bytes())
    reg['registration']['dependencies']['base']['package_sources'][entry.SEQUENCE_KEY]=wire.sha(raw)
    p['registration'].write_bytes(wire.canonical(reg))
    review=wire.strict_json(p['review'].read_bytes())
    review.update(sequence_script_sha256=wire.sha(raw),registration_sha256=wire.sha(p['registration'].read_bytes()))
    p['review'].write_bytes(wire.canonical(review))
    return p,script


def test_load_a_replace_with_reviewed_b_refuses_before_execution(tmp_path,monkeypatch):
    a=b"raise AssertionError('unreviewed A executed')\n"
    b=b"raise AssertionError('B must not execute from disk reread')\n"
    p,script=setup_source(tmp_path,monkeypatch,b)
    script.write_bytes(a)
    read=wire.read_regular
    def replace_after_read(path,**kwargs):
        raw=read(path,**kwargs)
        if Path(path)==script: script.write_bytes(b)
        return raw
    monkeypatch.setattr(wire,'read_regular',replace_after_read)
    with pytest.raises(ValueError,match='captured sequence bytes'):
        entry.main(fixture.argv(p))
    assert script.read_bytes()==b
    assert not p['packet-directory'].exists()
    assert not (tmp_path/'.native-sequence-starts').exists()
    assert not p['output-directory'].exists()


def test_verified_a_is_executed_and_retained_even_if_disk_becomes_b(tmp_path,monkeypatch):
    # A tiny inert body proves the entry uses one captured string for compile
    # and retention. It does not substitute for the real-body test above.
    a=b"def _run_verified(args, *, verified_script, entry_inputs):\n    return verified_script\n"
    b=b"raise AssertionError('disk replacement executed')\n"
    p,script=setup_source(tmp_path,monkeypatch,a)
    read=wire.read_regular; seen=[]
    def replace_after_read(path,**kwargs):
        raw=read(path,**kwargs)
        if Path(path)==script:
            seen.append(raw); script.write_bytes(b)
        return raw
    monkeypatch.setattr(wire,'read_regular',replace_after_read)
    assert entry.main(fixture.argv(p))==a
    assert seen==[a] and script.read_bytes()==b


def test_entry_requires_both_source_pins_before_any_effect(tmp_path,monkeypatch):
    p=fixture.paths(tmp_path)
    review=wire.strict_json(p['review'].read_bytes()); review['sequence_script_sha256']='0'*64
    p['review'].write_bytes(wire.canonical(review))
    with pytest.raises(ValueError,match='captured sequence bytes'):
        entry.main(fixture.argv(p))
    assert not p['packet-directory'].exists()
