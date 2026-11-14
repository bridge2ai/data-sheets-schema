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


@pytest.mark.parametrize('bound_inputs', [False, True])
@pytest.mark.parametrize('retained_b', [False, True])
@pytest.mark.parametrize('injected', [False, True])
def test_imported_body_refuses_even_with_reviewed_retained_bytes(tmp_path, monkeypatch, bound_inputs, retained_b, injected):
    from data_sheets_schema import native_launch_sequence as loaded_a
    raw = Path(loaded_a.__file__).read_bytes()
    if retained_b:
        raw += b'\n# distinct retained reviewed source B\n'
        p, _ = setup_source(tmp_path, monkeypatch, raw)
    else:
        p = fixture.paths(tmp_path)
    before = {str(path): path.read_bytes() for path in (tmp_path / 'word-state').rglob('*.json')}
    callbacks = []
    if injected:
        monkeypatch.setattr(loaded_a, '_entry_invocation', lambda *args: callbacks.append(args), raising=False)
        # A second global with the trusted validator's name is not accepted
        # either: the body resolves its local import from the trusted entry.
        monkeypatch.setattr(loaded_a, '_require_invocation', lambda *args: callbacks.append(args), raising=False)
        monkeypatch.setattr(loaded_a, '__package__', 'caller_supplied_package')
    inputs = {p[name]: p[name].read_bytes() for name in ('registration', 'review')} if bound_inputs else {}
    with pytest.raises(ValueError, match='live verified entry namespace'):
        loaded_a._run_verified(fixture.argv(p), verified_script=raw, entry_inputs=inputs)
    assert not p['packet-directory'].exists()
    assert not p['output-directory'].exists()
    assert callbacks == []
    assert before == {str(path): path.read_bytes() for path in (tmp_path / 'word-state').rglob('*.json')}


def test_verified_body_cannot_be_reused_after_entry_returns(tmp_path, monkeypatch):
    p = fixture.paths(tmp_path)
    fixture.fake_commands(monkeypatch, p)
    execute = entry.exec
    captured = []
    def retain(code, namespace):
        execute(code, namespace)
        body = namespace['_run_verified']
        def record(args, *, verified_script, entry_inputs):
            captured.append((body, args, verified_script, entry_inputs))
            return body(args, verified_script=verified_script, entry_inputs=entry_inputs)
        namespace['_run_verified'] = record
    monkeypatch.setattr(entry, 'exec', retain)
    assert entry.main(fixture.argv(p)) == 0
    body, args, raw, inputs = captured[0]
    before = {str(path): path.read_bytes() for path in tmp_path.rglob('*') if path.is_file()}
    with pytest.raises(ValueError, match='live verified entry namespace'):
        body(args, verified_script=raw, entry_inputs=inputs)
    assert before == {str(path): path.read_bytes() for path in tmp_path.rglob('*') if path.is_file()}
    assert entry._ACTIVE_INVOCATIONS == {}
