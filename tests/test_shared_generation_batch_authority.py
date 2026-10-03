"""Batch-wide captured authority separation (#4361); real selection, no provider."""
import json
import os
from pathlib import Path
import socket

import click
import pytest

from data_sheets_schema import api_runner as api, run_lock, shared_generation as sg
from tests.test_generation_manifest_identity import external  # noqa: F401
from tests.test_shared_generation_cli import (batch, module, registered, roster,
                                             stub_plan)  # noqa: F401


@pytest.fixture(autouse=True)
def offline(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(socket.socket, 'connect', lambda *a, **k: pytest.fail('network forbidden'))
    monkeypatch.setattr(api, 'provider_identity', lambda: {'provider': None, 'base_url': None, 'key_env': None})
    assert Path(api.__file__).resolve().parents[1] == Path(__file__).resolve().parents[1] / 'src'


def specs_for(rows):
    return [module._shared_spec(row['project'], 'baseline', row['label'], None,
        None, None, None, None, module._UNSET, None, 0, 0, 0, None,
        module._capture_shared_registration(row['registration_path'])) for row in rows]


def authority_bytes(path, rows):
    """Include every declared file pin and both registration/roster authorities."""
    paths = {Path(path), *(Path(row['registration_path']) for row in rows)}
    def pins(value):
        if isinstance(value, dict):
            if {'path', 'sha256', 'bytes'} <= value.keys():
                paths.add(Path(value['path']))
            for item in value.values():
                pins(item)
        elif isinstance(value, list):
            for item in value:
                pins(item)
    for row in rows:
        pins(json.loads(Path(row['registration_path']).read_bytes()))
    return {p: p.read_bytes() for p in paths}


def dispatch_traps(monkeypatch):
    seen = {'plan': [], 'lock': [], 'execute': []}
    def plan(spec):
        seen['plan'].append(spec.label)
        return stub_plan(spec)
    def acquire(*args):
        seen['lock'].append(args)
        return Path.cwd() / 'fake-lock'
    def execute(spec):
        seen['execute'].append(spec.label)
        raise AssertionError('dispatch reached: no provider is invoked')
    monkeypatch.setattr(api, 'plan', plan)
    monkeypatch.setattr(api, 'execute', execute)
    monkeypatch.setattr(run_lock, 'acquire', acquire)
    monkeypatch.setattr(run_lock, 'release', lambda *a: None)
    return seen


def collision(base, reg, *, input_run=1, target_run=0, authority='context', shape='report'):
    path, rows = roster(base, reg)
    specs = specs_for(rows)
    target = specs[target_run]
    document = json.loads(Path(rows[input_run]['registration_path']).read_bytes())
    if authority == 'registration':
        raw = sg.canonical(document)
    elif authority == 'config':
        raw = b'models:\n  fixture: {name: synthetic}\n'
    else:
        raw = Path(document['inputs'][authority]['path']).read_bytes()
    output = target.provenance_path if shape == 'provenance_hardlink' else target.report_path
    output.parent.mkdir(parents=True, exist_ok=True)
    if shape in ('hardlink', 'provenance_hardlink'):
        authority_path = base.bundle.parent / f'foreign-{authority}.json'
        authority_path.write_bytes(raw)
        os.link(authority_path, output)
    elif shape == 'symlink':
        destination = output.parent / f'foreign-{authority}.json'
        destination.write_bytes(raw)
        authority_path = base.bundle.parent / f'foreign-{authority}-link.json'
        authority_path.symlink_to(destination)
    elif shape == 'directory':
        authority_path = target.metadata_dir / 'nested' / f'foreign-{authority}.json'
        authority_path.parent.mkdir()
        authority_path.write_bytes(raw)
    else:
        authority_path = output
        authority_path.write_bytes(raw)
    if authority == 'registration':
        # Default output paths may be relative; registration declarations may not.
        document['registration_path'] = str(authority_path.absolute())
        rows[input_run]['registration_path'] = document['registration_path']
    elif authority == 'config':
        document['runtime']['config'] = sg.file_pin(authority_path)
    else:
        document['inputs'][authority] = sg.file_pin(authority_path)
    Path(document['registration_path']).write_bytes(sg.canonical(document))
    path.write_bytes(sg.canonical({'format': 'shared_generation_batch_roster_v1', 'registrations': rows}))
    return path, rows, authority_path, output


@pytest.mark.parametrize('input_run,target_run', [(1, 0), (0, 1)])
@pytest.mark.parametrize('shape', ['report', 'directory', 'hardlink', 'provenance_hardlink', 'symlink'])
def test_context_cannot_be_destroyed_by_either_run(registered, monkeypatch, input_run, target_run, shape):
    base, reg = registered
    path, rows, source, output = collision(base, reg, input_run=input_run, target_run=target_run, shape=shape)
    before = authority_bytes(path, rows)
    seen = dispatch_traps(monkeypatch)
    result = batch(reg, path)
    assert result.exit_code == 1, result.output
    assert seen == {'plan': [], 'lock': [], 'execute': []}, (result.output, seen)
    assert 'run-owned output' in result.output or 'aliases a run output' in result.output
    assert {p: p.read_bytes() for p in before} == before
    if shape in ('report', 'hardlink', 'provenance_hardlink'):
        assert source.samefile(output)


@pytest.mark.parametrize('authority', ['registration', 'config', 'source_manifest'])
@pytest.mark.parametrize('input_run,target_run', [(1, 0), (0, 1)])
def test_complete_foreign_authority_closure_is_protected(registered, monkeypatch, authority, input_run, target_run):
    base, reg = registered
    path, rows, _, _ = collision(base, reg, authority=authority, input_run=input_run, target_run=target_run)
    before = authority_bytes(path, rows)
    seen = dispatch_traps(monkeypatch)
    result = batch(reg, path)
    assert result.exit_code == 1, result.output
    assert seen == {'plan': [], 'lock': [], 'execute': []}, (result.output, seen)
    assert 'run-owned output' in result.output or 'aliases a run output' in result.output
    assert {p: p.read_bytes() for p in before} == before


def test_roster_hardlink_to_later_output_is_protected(registered, monkeypatch):
    base, reg = registered
    path, rows = roster(base, reg)
    target = specs_for(rows)[1].report_path
    target.parent.mkdir(parents=True)
    os.link(path, target)
    before = authority_bytes(path, rows)
    seen = dispatch_traps(monkeypatch)
    result = batch(reg, path)
    assert result.exit_code == 1 and 'aliases a run output' in result.output, result.output
    assert seen == {'plan': [], 'lock': [], 'execute': []}
    assert {p: p.read_bytes() for p in before} == before


def test_actual_schema_closure_hardlink_remains_protected(registered, monkeypatch):
    base, reg = registered
    path, rows = roster(base, reg)
    schema = Path(reg['inputs']['full_schema']['sources'][-1]['path'])
    target = specs_for(rows)[1].report_path
    target.parent.mkdir(parents=True)
    os.link(schema, target)
    before = authority_bytes(path, rows)
    seen = dispatch_traps(monkeypatch)
    result = batch(reg, path)
    assert result.exit_code == 1 and 'aliases a run output' in result.output, result.output
    assert seen == {'plan': [], 'lock': [], 'execute': []}
    assert {p: p.read_bytes() for p in before} == before


def test_current_recheck_rejects_new_alias_without_recapturing(registered):
    base, reg = registered
    path, rows = roster(base, reg)
    specs = specs_for(rows)
    captured_roster = module._shared_roster(path, [(s.project, s.label) for s in specs])
    module._shared_current(specs, captured_roster)
    captures = [sg.capture(s) for s in specs]
    # A private second-run context makes this cross-run-only, not a shared input collision.
    document = captures[1].document()
    private = base.bundle.parent / 'private-context.json'
    private.write_bytes(Path(document['inputs']['context']['path']).read_bytes())
    document['inputs']['context'] = sg.file_pin(private)
    Path(document['registration_path']).write_bytes(sg.canonical(document))
    specs = specs_for(rows)
    captured_roster = module._shared_roster(path, [(s.project, s.label) for s in specs])
    module._shared_current(specs, captured_roster)
    captures = [sg.capture(s) for s in specs]
    before = authority_bytes(path, rows)
    target = specs[0].report_path
    target.parent.mkdir(parents=True)
    os.link(private, target)
    with pytest.raises(click.ClickException, match='aliases a run output'):
        module._shared_current(specs, captured_roster)
    assert all(sg.capture(s) is captured for s, captured in zip(specs, captures))
    assert {p: p.read_bytes() for p in before} == before


def test_batch_rechecks_all_authorities_after_planning_before_lock(registered, monkeypatch):
    base, reg = registered
    path, rows = roster(base, reg)
    specs = specs_for(rows)
    target = specs[0].report_path
    document = json.loads(Path(rows[1]['registration_path']).read_bytes())
    private = base.bundle.parent / 'private-context.json'
    private.write_bytes(Path(document['inputs']['context']['path']).read_bytes())
    document['inputs']['context'] = sg.file_pin(private)
    Path(document['registration_path']).write_bytes(sg.canonical(document))
    before = authority_bytes(path, rows)
    seen = dispatch_traps(monkeypatch)
    def plan(spec):
        seen['plan'].append(spec.label)
        if spec.label == 'shared_rep2':
            target.parent.mkdir(parents=True)
            os.link(private, target)
        return stub_plan(spec)
    monkeypatch.setattr(api, 'plan', plan)
    result = batch(reg, path)
    assert result.exit_code == 1 and 'aliases a run output' in result.output, result.output
    assert seen == {'plan': ['shared_rep1', 'shared_rep2'], 'lock': [], 'execute': []}
    assert {p: p.read_bytes() for p in before} == before


def test_safe_batch_preserves_shared_read_only_authorities(registered, monkeypatch):
    base, reg = registered
    path, rows = roster(base, reg)
    before = authority_bytes(path, rows)
    seen = dispatch_traps(monkeypatch)
    result = batch(reg, path, extra=('--dry-run',))
    assert result.exit_code == 0, result.output
    assert seen == {'plan': ['shared_rep1', 'shared_rep2'], 'lock': [], 'execute': []}
    captured = [sg.capture(s) for s in specs_for(rows)]
    common = set(dict(captured[0].files)) & set(dict(captured[1].files))
    assert str(base.bundle) in common and reg['inputs']['context']['path'] in common
    assert {p: p.read_bytes() for p in before} == before


def test_later_dispatch_rechecks_foreign_authority_after_first_run(registered, monkeypatch):
    from data_sheets_schema import receipt_completion_policy as cp, receipts
    base, reg = registered
    path, rows = roster(base, reg)
    target = specs_for(rows)[0].report_path
    document = json.loads(Path(rows[1]['registration_path']).read_bytes())
    private = base.bundle.parent / 'private-context.json'
    private.write_bytes(Path(document['inputs']['context']['path']).read_bytes())
    document['inputs']['context'] = sg.file_pin(private)
    Path(document['registration_path']).write_bytes(sg.canonical(document))
    before = authority_bytes(path, rows)
    seen, released = [], []
    monkeypatch.setattr(api, 'plan', stub_plan)
    monkeypatch.setattr(run_lock, 'acquire', lambda *a: base.bundle.parent / 'fake-lock')
    monkeypatch.setattr(run_lock, 'release', released.append)
    def execute(spec):
        seen.append(spec.label)
        assert seen == ['shared_rep1'], 'second run must not dispatch after authority aliases output'
        policy = cp.select_policy(spec.render_spec())
        receipt = {'checked': True, 'expected': True, 'instrument': receipts.RERECEIPTS_INSTRUMENT,
            'slots': {'with_receipt': 3, 'receiptable': 3}, 'findings': [],
            'chunks': {'total': 1, 'reviewed': 1}, 'snippets': {'verified': 1},
            cp.BLOCK_KEY: cp.block_identity(policy)}
        checks = {'receipts': receipt, 'pair': {'ran': True, 'errors': 0},
            'report': {'checked': True, 'claims_checked': 1, 'findings': []},
            'grounding': {'checked': True, 'distinct': {'absent': 0}},
            'form': {'checked': True, 'organisational_fragments': 0,
                     'undeclared_prefix_occurrences': 0, 'british_spellings': 0}}
        provenance = base.bundle.parent / 'simulated-result.yaml'
        provenance.write_bytes(sg.canonical({'run': {'project': spec.project}}))
        target.parent.mkdir(parents=True)
        os.link(private, target)
        return {'usage': [], 'skipped': [], 'validation_problems': [], 'checks': checks,
                'outputs': {'provenance': str(provenance)}}
    monkeypatch.setattr(api, 'execute', execute)
    result = batch(reg, path, extra=('--continue-on-error',))
    assert result.exit_code == 1 and 'aliases a run output' in result.output, result.output
    assert 'registered receipt gate passed' in result.output
    assert seen == ['shared_rep1'] and len(released) == 1
    assert {p: p.read_bytes() for p in before} == before
