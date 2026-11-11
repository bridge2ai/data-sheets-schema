"""Fixed capture adapter contracts; synthetic files only, no native fixture."""
import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import sys
import xml.etree.ElementTree as ET

import pytest

ROOT = Path(__file__).resolve().parents[1]
NODE = ('tests/test_native_subscription_capture.py::'
        'test_genuine_registration_read_capture_for_event_rechecks_live_selection_and_stage_root')


@pytest.fixture
def adapter(monkeypatch, tmp_path):
    spec = importlib.util.spec_from_file_location('capture_adapter_test',
        ROOT / 'scripts/adhoc/native_wp1_validation_20261110.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, 'SCRATCH', tmp_path)
    return module


def test_fixed_route_never_becomes_timing_acceptance(adapter):
    assert adapter.KINDS['capture-recheck'] == (NODE, 'monitoring', 900)
    assert 'capture-recheck' in adapter.NO_LEASE_KINDS
    assert 'capture-recheck' not in adapter.CPU_DIAGNOSTIC_KINDS | adapter.QUALIFIED_KINDS
    assert 'tests/test_native_subscription_capture.py' in adapter.REQUIRED_FILES
    classification = adapter.measurement_classification('capture-recheck',
        qualification={'qualification_passed': True, 'cleanup_verified': True},
        certified=True, final_owner=True)
    assert classification == dict(measurement_class='capture_readback_integration_canary',
        host_qualified=False, wall_time_freshness_qualified=False, accepted_quiet_host_timing=False)
    with pytest.raises(ValueError):
        adapter.require_accepted_measurement(dict(kind='capture-recheck', **classification,
            cleanup_verified=True, returncode=0))


def save(path, data):
    path.write_text(json.dumps(data))


def canary(adapter, tmp_path):
    out = tmp_path / 'canary'
    out.mkdir()
    base = dict(kind='canary', manifest_sha256='a' * 64, returncode=0, cleanup_verified=True)
    save(out.with_suffix('.outer.json'), dict(base, timed_out=False))
    save(out.with_suffix('.supervisor.json'), dict(base, forced_cleanup=False,
        sandbox_handoff={'admitted': True}))
    save(out / 'outcome.json', dict(returncode=0, cleanup_verified=True))
    save(out / 'wp1-harness.json', dict(base, node=adapter.CANARY, source_unchanged=True))
    (out / 'pytest.xml').write_text('<testsuite><testcase name="' +
        adapter.CANARY.split('::')[1] + '" /></testsuite>')
    return out


@pytest.mark.parametrize('state', ['matching', 'missing', 'wrong-manifest', 'unclean', 'skipped'])
def test_same_manifest_canary_is_required(adapter, tmp_path, state):
    out = canary(adapter, tmp_path)
    args = SimpleNamespace(kind='capture-recheck', canary_out=out)
    if state == 'missing':
        args.canary_out = None
    elif state == 'unclean':
        value = json.loads(out.with_suffix('.supervisor.json').read_text())
        value['cleanup_verified'] = False
        save(out.with_suffix('.supervisor.json'), value)
    elif state == 'skipped':
        tree = ET.parse(out / 'pytest.xml')
        ET.SubElement(next(tree.iter('testcase')), 'skipped')
        tree.write(out / 'pytest.xml')
    digest = ('b' if state == 'wrong-manifest' else 'a') * 64
    if state == 'matching':
        adapter.require_prerequisite_canary(args, digest)
    else:
        with pytest.raises(ValueError):
            adapter.require_prerequisite_canary(args, digest)


def test_once_claim_survives_failure_and_label_change(adapter, tmp_path):
    out = tmp_path / 'first'
    adapter.capture_recheck_claim(out, 'a' * 64, 'b' * 40, create=True)
    adapter.capture_recheck_claim(out, 'a' * 64, 'b' * 40)
    with pytest.raises(FileExistsError):
        adapter.capture_recheck_claim(tmp_path / 'second', 'a' * 64, 'b' * 40, create=True)
    with pytest.raises(ValueError):
        adapter.capture_recheck_claim(tmp_path / 'second', 'a' * 64, 'b' * 40)
    with pytest.raises(FileNotFoundError):
        adapter.capture_recheck_claim(out, 'c' * 64, 'b' * 40)


def result_files(tmp_path):
    out = tmp_path / 'result'
    out.mkdir()
    save(out / 'wp1-harness.json', dict(kind='capture-recheck', node=NODE,
        manifest_sha256='a' * 64, source_commit='b' * 40,
        invocation_limit_seconds=900, source_unchanged=True))
    xml = ET.Element('testsuite')
    ET.SubElement(xml, 'testcase', name=NODE.split('::')[1],
        classname='tests.test_native_subscription_capture')
    ET.ElementTree(xml).write(out / 'pytest.xml')
    return out


@pytest.mark.parametrize('change', ['none', 'missing', 'malformed', 'zero', 'two', 'name',
    'module', 'failure', 'error', 'skipped', 'manifest', 'source', 'node', 'dirty', 'malformed-harness'])
def test_only_exact_singleton_pass_is_accepted(adapter, tmp_path, change):
    out = result_files(tmp_path)
    path = out / 'pytest.xml'
    if change == 'missing':
        path.unlink()
    elif change == 'malformed':
        path.write_text('<invalid')
    elif change in {'zero', 'two', 'name', 'module', 'failure', 'error', 'skipped'}:
        tree = ET.parse(path)
        case = next(tree.iter('testcase'))
        if change == 'zero':
            tree.getroot().remove(case)
        elif change == 'two':
            ET.SubElement(tree.getroot(), 'testcase', **case.attrib)
        elif change in {'name', 'module'}:
            case.set('name' if change == 'name' else 'classname', 'substitute')
        else:
            ET.SubElement(case, change)
        tree.write(path)
    elif change in {'manifest', 'source', 'node', 'dirty', 'malformed-harness'}:
        path = out / 'wp1-harness.json'
        value = json.loads(path.read_text())
        if change == 'malformed-harness':
            value = []
        else:
            key = {'manifest': 'manifest_sha256', 'source': 'source_commit',
                   'node': 'node', 'dirty': 'source_unchanged'}[change]
            value[key] = False if change == 'dirty' else 'substitute'
        save(path, value)
    if change == 'none':
        adapter.require_capture_recheck_result(out, 'a' * 64, 'b' * 40)
    else:
        with pytest.raises((OSError, ValueError, ET.ParseError)):
            adapter.require_capture_recheck_result(out, 'a' * 64, 'b' * 40)


@pytest.mark.parametrize('mutation', ['none', 'missing-pin', 'source-byte', 'composition-byte'])
def test_contract_binds_capture_test_bytes(adapter, monkeypatch, tmp_path, mutation):
    source, tree = tmp_path / 'source', tmp_path / 'tree'
    source.mkdir(); tree.mkdir()
    pins, blobs = {}, {}
    for name in adapter.REQUIRED_FILES:
        raw = ('synthetic pinned bytes: ' + name).encode()
        blobs[name] = raw
        pins[name] = hashlib.sha256(raw).hexdigest()
        for root in (source, tree):
            target = root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
    head = 'b' * 40
    composition = tmp_path / ('composition-' + head[:12])
    composition.mkdir()
    composition /= 'composition.json'
    save(composition, dict(source_commit=head, kind='native_u3m_private_composition',
                          status='composed_not_tested', worktree=str(tree)))
    manifest = tmp_path / ('wp1-contract-' + head[:12] + '.json')
    captured = 'tests/test_native_subscription_capture.py'
    if mutation == 'missing-pin':
        del pins[captured]
    elif mutation in {'source-byte', 'composition-byte'}:
        ((source if mutation == 'source-byte' else tree) / captured).write_bytes(b'changed')
    save(manifest, dict(kind='native_wp1_measurement', version=1, source_commit=head,
        composition_manifest=str(composition), composition_manifest_sha256=adapter.sha(composition),
        implementation_sha256=pins, interpreter=dict(path=str(Path(sys.executable).resolve()),
            sha256=adapter.sha(Path(sys.executable).resolve()), version=sys.version)))
    monkeypatch.setattr(adapter, 'ROOT', source)
    def git(*args):
        if args == ('rev-parse', 'HEAD'):
            return head.encode()
        if args[0] == 'status':
            return b''
        assert args[0] == 'show'
        return blobs[args[1].split(':', 1)[1]]
    monkeypatch.setattr(adapter, 'git', git)
    monkeypatch.setenv('U3WP1_MANIFEST', str(manifest))
    monkeypatch.delenv('U3WP1_MANIFEST_SHA', raising=False)
    if mutation == 'none':
        assert adapter.contract()[2]['source_commit'] == head
    else:
        with pytest.raises(ValueError, match='implementation'):
            adapter.contract()


def test_existing_cpu_classification_and_comparison_cases(adapter):
    spec = importlib.util.spec_from_file_location('capture_prior_cases',
        ROOT / 'scripts/adhoc/native_wp1_quiet_fixture_20261110.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.cpu_diagnostic_cases(adapter)


@pytest.mark.parametrize('entry', ['outer', 'supervised'])
@pytest.mark.parametrize('state', ['matching', 'missing', 'wrong-manifest'])
def test_both_entry_layers_check_canary_before_launch(adapter, monkeypatch, tmp_path, entry, state):
    out = canary(adapter, tmp_path)
    args = SimpleNamespace(kind='capture-recheck', label='unit', supervised=False,
                          canary_out=None if state == 'missing' else out)
    digest, head = 'a' * 64, 'b' * 40
    if state == 'wrong-manifest':
        digest = 'c' * 64
    manifest = tmp_path / ('wp1-contract-' + head[:12] + '.json')
    save(manifest, {'unit_contract': True})
    selected = tmp_path / ('wp1-' + head[:12] + '-capture-recheck-unit')
    monkeypatch.setattr(adapter, 'arguments', lambda: args)
    monkeypatch.setattr(adapter, 'contract', lambda: (manifest, digest, {'source_commit': head}))
    monkeypatch.setattr(adapter, 'sys', SimpleNamespace(
        flags=SimpleNamespace(no_site=True, safe_path=True), dont_write_bytecode=True,
        path=list(sys.path), executable=sys.executable))
    monkeypatch.setattr(adapter.time, 'monotonic', lambda: 101.0)
    monkeypatch.setenv('U3WP1_STARTED_MONOTONIC', '100.0')
    monkeypatch.setenv('U3WP1_HARD_DEADLINE', '1000.0')
    monkeypatch.setenv('U3WP1_SUPERVISOR_PID', str(adapter.os.getppid()))
    monkeypatch.setenv('U3WP1_MEASUREMENT_CLASS', 'capture_readback_integration_canary')
    monkeypatch.setenv('U3WP1_MANIFEST', str(manifest))
    monkeypatch.delenv('U3WP1_LEASE_FD', raising=False)
    reached = []
    original = adapter.require_canary
    def checked(path, sha):
        reached.append('canary')
        original(path, sha)
    monkeypatch.setattr(adapter, 'require_canary', checked)
    def boundary(*args, **kwargs):
        reached.append('after-canary')
        raise ValueError('unit boundary before subprocess')
    def forbidden(*args, **kwargs):
        pytest.fail('unit tried to spawn a child')
    monkeypatch.setattr(adapter.subprocess, 'Popen', forbidden)
    if entry == 'supervised':
        adapter.capture_recheck_claim(selected, digest, head, create=True)
        monkeypatch.setattr(adapter, 'dependency_site', boundary)
        with pytest.raises(ValueError):
            adapter.supervised_main(args)
    else:
        monkeypatch.setattr(adapter.signal, 'signal', lambda *args: None)
        monkeypatch.setattr(adapter.signal, 'setitimer', lambda *args: None)
        monkeypatch.setattr(adapter, 'dependency_site', lambda: tmp_path)
        monkeypatch.setattr(adapter, 'wp1_helper', lambda name:
            SimpleNamespace(refuse_existing=lambda lock: None))
        monkeypatch.setattr(adapter, '_SandboxHandoff', boundary)
        assert adapter.main() == 125
    assert reached == ([] if state == 'missing' else
                       ['canary', 'after-canary'] if state == 'matching' else ['canary'])
