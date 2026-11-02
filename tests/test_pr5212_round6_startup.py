"""#5212 round 6, 2026-11-02: ordered refusals and real process exclusion."""
from dataclasses import replace
import os
from pathlib import Path
import subprocess
import sys

import pytest

from data_sheets_schema import api_runner as api, usage_ledger as ledger
from tests.test_download.test_api_runner import FakeClient, spec
from tests.test_generation_manifest_identity import external  # noqa: F401
from tests.test_shared_generation_cli import registered, roster, batch, module, stub_plan  # noqa: F401
from tests.test_shared_generation_selection import selected_spec
from tests.test_shared_write_footprint import traps
from tests.test_d68_legacy_readonly import tree

pytestmark = pytest.mark.usefixtures('journal_launch_monitor')
ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('resume', [False, True])
@pytest.mark.parametrize('entry', ['execute', 'batch'])
def test_authority_refusal_precedes_unrelated_residue(registered, tmp_path, monkeypatch, entry, resume):
    base, reg = registered
    monkeypatch.setattr(api.RunSpec, 'output_root', property(lambda self: tmp_path / 'root'))
    selected = selected_spec(replace(base, out_dir=None), reg)
    path, rows = roster(base, reg, count=1)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(api, 'provider_identity', lambda: {'provider': None, 'base_url': None, 'key_env': None})
    calls = traps(monkeypatch)
    alias = selected.full_path.with_name(f'.{selected.full_path.name}_api_run.lock')
    alias.parent.mkdir(parents=True, exist_ok=True)
    # A split full-output sibling is in D69's inventory, independently of
    # main's metadata ownership declarations and the planted authority alias.
    residue = alias.parent / f'{selected.project}_unrelated.tmp'
    residue.write_bytes(b'unowned residue\n')
    source = Path(reg['inputs']['context']['path'])
    prelock_trees = []
    if entry == 'execute':
        os.link(source, alias)
    else:
        # Introduce the alias after the batch's planning-time checks, so the
        # final shared startup path itself must preserve main's refusal order.
        def plan(run):
            result = stub_plan(run)
            if not alias.exists():
                os.link(source, alias)
            prelock_trees.append(tree(tmp_path))
            return result
        monkeypatch.setattr(api, 'plan', plan)
        if hasattr(api, '_prelock_checks'):
            real_prelock = api._prelock_checks
            monkeypatch.setattr(api, '_prelock_checks',
                                lambda specs, **kw: real_prelock(specs, **{**kw, 'resume': resume}))
    before = tree(tmp_path)
    if entry == 'execute':
        with pytest.raises(ValueError, match='aliases a run output'):
            api.execute(selected, resume=resume, client=FakeClient())
        assert tree(tmp_path) == before
    else:
        result = batch(reg, path, count=1)
        assert 'aliases a run output' in result.output and result.exit_code != 0, result.output
        assert prelock_trees and tree(tmp_path) == prelock_trees[-1]
    assert calls == []
    alias.unlink()
    monkeypatch.setattr(api, 'plan', stub_plan)
    before = tree(tmp_path)
    if entry == 'execute':
        with pytest.raises(ledger.UsageLedgerError, match='artifacts have no journal'):
            api.execute(selected, resume=resume, client=FakeClient())
    else:
        result = batch(reg, path, count=1)
        message = result.output + str(result.exception)
        assert 'artifacts have no journal' in message and result.exit_code != 0, message
    assert calls == [] and tree(tmp_path) == before


@pytest.mark.parametrize('resume', [False, True])
@pytest.mark.parametrize('same_identity', [False, True])
def test_real_process_sidecar_contention_preserves_relaunch(tmp_path, monkeypatch, subprocess_checkpoint,
                                                         resume, same_identity):
    monkeypatch.setattr(api.RunSpec, 'output_root', property(lambda self: tmp_path / 'root'))
    owner = spec(project='P', label='owner')
    api.execute(owner, client=FakeClient())
    selected = owner if same_identity else replace(owner, label='contender', out_dir=owner.core_path.parent)
    sidecar = dict(ledger.output_locks((owner.core_path,)))[owner.core_path.resolve()]
    inode = sidecar.lstat().st_dev, sidecar.lstat().st_ino
    child = subprocess.Popen([sys.executable, str(ROOT / 'scripts/adhoc/pr5212_lock_fixture_20261102.py'),
                              str(sidecar)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        subprocess_checkpoint(child)
        before = tree(tmp_path)
        client = FakeClient()
        with pytest.raises(ledger.UsageLedgerError, match='already active'):
            api.execute(selected, resume=resume, client=client)
        assert client.messages.calls == []
        observed = tree(tmp_path)
        assert observed.keys() == before.keys()
        for name, prior in before.items():
            # FileLock opens an existing sidecar with O_TRUNC even when the
            # nonblocking flock refuses; empty bytes/inode/mode stay intact,
            # but mtime can change. Every other tree entry stays exact.
            actual = observed[name]
            assert (prior[:2] + prior[3:] == actual[:2] + actual[3:]
                    if name.endswith('_api_run.lock') else prior == actual), name
        assert child.poll() is None and inode == (sidecar.lstat().st_dev, sidecar.lstat().st_ino)
        child.communicate(timeout=15)
        assert child.returncode == 0
    finally:
        if child.poll() is None:
            child.kill()
            child.communicate(timeout=15)
    client = FakeClient()
    api.execute(selected, resume=resume, client=client)
    assert len(client.messages.calls) == (0 if same_identity and resume else 4)


@pytest.mark.parametrize('mode', ['exit', 'deadline'])
def test_checkpoint_failure_reports_exit_and_stderr(tmp_path, subprocess_checkpoint, mode):
    fixture = ROOT / 'scripts/adhoc/pr5212_lock_fixture_20261102.py'
    child = subprocess.Popen([sys.executable, str(fixture), '--' + ('exit' if mode == 'exit' else 'wait')], stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        with pytest.raises(AssertionError, match='exit_status=.*child diagnostic') as caught:
            subprocess_checkpoint(child, timeout=10)
        assert ('exit_status=7' if mode == 'exit' else 'exit_status=None') in str(caught.value)
    finally:
        if child.poll() is None:
            child.kill()
        child.communicate(timeout=15)
