"""Reconstruct original prompts from complete synthetic science, never old text.

Proof/freeze validation is tested separately. Here source manifests and all
scientific inputs are invented, while layout, indexing, rendering, original
parent selection and persistent instruction generation are real.
"""
from copy import deepcopy
import builtins
import hashlib
import io
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from budgeted_cborg import BudgetStop
from data_sheets_schema import audit_batches, audit_batch_context, profiles
from . import batch_native as runtime, batch_output as output, batch_registration
from .test_batch_runtime import batch
from tests.test_audit_batch_context import staged, proposals as context_proposals


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


@pytest.fixture
def context_checkpoint(batch, staged, tmp_path):
    original = deepcopy(batch.m)
    original.update(render_version=23,
        scientific_contract_transition={'kind': 'frozen_pair_child_navigation_v1'},
        audit_batch_navigation={'kind': 'explicit_child_reads_v1'})
    original['inputs'] = {key: str(path) for key, path in staged['files'].items()}
    original['pinned_files'].update({str(path): digest(path.read_bytes())
                                   for path in staged['files'].values()})
    parent_path = Path(original['parent']['registration'])
    parent = json.loads(parent_path.read_bytes())
    parent['generation']['jobs'][0]['project'] = 'example'
    parent_path.write_text(json.dumps(parent))
    plan_path = tmp_path / 'complete-plan.json'
    plan_path.write_bytes(audit_batches.canonical_bytes(staged['plan']))
    original['pinned_files'][str(plan_path)] = digest(plan_path.read_bytes())
    original['audit_batches'] = output.specification(original, batch.reg,
        worker_total_cap_usd='24', plan_path=plan_path)
    proposal_paths, expected_index, _ = context_proposals(staged)
    for worker in original['audit_batches']['children'][:-1]:
        destination = Path(worker['proposal_path'])
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(proposal_paths[worker['id']].read_bytes())
    row = output.child(original, 'integration')
    system = batch_registration.child_system(original, 'integration').encode()
    index, artifacts, views, _, args = runtime.integration_material(original)
    assert index == expected_index
    for path, raw in views.items():
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    instruction = audit_batch_context.render_integration_context(**args,
        worker_index=index, worker_artifacts=output.worker_artifacts(original),
        row_artifacts=artifacts, audit_batch_navigation='explicit_child_reads_v1').encode()
    # Expectations are captured before every later template/row mutation.
    original['pinned_files'][row['system_prompt']] = digest(system)
    current = {'pinned_files': {row['instruction']: digest(instruction)}}
    source = SimpleNamespace(manifest=original,
        evidence_paths=frozenset({Path(row['instruction'])}))
    root = Path(row['attempt_dir']); root.mkdir(parents=True, exist_ok=True)
    forbidden = [Path(row['system_prompt']), Path(row['instruction']),
                 root / 'context.json', root / 'proposal-index.json',
                 root / 'transcript.jsonl', root / 'control.jsonl',
                 root / 'requests/failed/response.sse', root / 'output/proposal.json']
    for path in forbidden:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b'FORBIDDEN_FAILED_INTEGRATION_BODY')
    return SimpleNamespace(original=original, current=current, source=source,
        row=row, root=root, forbidden=forbidden, system=system,
        instruction=instruction, views=views, staged=staged)


def forbid_old_integration_reads(monkeypatch, fixture):
    """Permit only exact canonical worker-row copies from the old integration."""
    opened = []
    system_path = Path(fixture.row['system_prompt'])
    def protect(function):
        def checked(path, *args, **kwargs):
            if isinstance(path, (str, bytes, os.PathLike)):
                target = Path(os.fsdecode(path)).absolute()
                assert target != system_path and (not target.is_relative_to(fixture.root)
                    or str(target) in fixture.views), (
                    'old integration body was opened instead of reconstructed')
                opened.append(target)
            return function(path, *args, **kwargs)
        return checked
    for module, name in ((builtins, 'open'), (io, 'open'), (os, 'open')):
        monkeypatch.setattr(module, name, protect(getattr(module, name)))
    return opened


@pytest.fixture
def vocabulary_checkpoint(context_checkpoint, tmp_path, monkeypatch):
    """Two real resource-resolver checkouts with equal, invented vocabularies."""
    fixture = context_checkpoint
    roots = [tmp_path / name for name in ('original-checkout', 'current-checkout')]
    relative_pin = Path('src/data_sheets_schema/b2ai_registry_vocabularies.yaml')
    raw = b'vocabularies: {}\n# Identical synthetic profile resource in both checkouts.\n'
    for root in roots:
        pin = root / relative_pin
        pin.parent.mkdir(parents=True)
        pin.write_bytes(raw)
        (root / 'pyproject.toml').write_text('[project]\nname = "data-sheets-schema"\n')
    old_root, new_root = roots
    old_pin, new_pin = [root / relative_pin for root in roots]
    fixture.original.update(repository=str(old_root), profile='bridge2ai')
    fixture.original['pinned_files'][str(old_pin)] = digest(raw)
    fixture.current.update(repository=str(new_root), profile='bridge2ai')
    fixture.current['pinned_files'].update({str(old_pin): digest(raw), str(new_pin): digest(raw)})
    monkeypatch.chdir(old_root)
    assert profiles.BRIDGE2AI.pin_path.absolute() == old_pin
    fixture.system = batch_registration.child_system(fixture.original, 'integration').encode()
    fixture.original['pinned_files'][fixture.row['system_prompt']] = digest(fixture.system)
    index, artifacts, _, _, args = runtime.integration_material(fixture.original)
    fixture.instruction = audit_batch_context.render_integration_context(**args,
        worker_index=index, worker_artifacts=output.worker_artifacts(fixture.original),
        row_artifacts=artifacts, audit_batch_navigation='explicit_child_reads_v1').encode()
    fixture.current['pinned_files'][fixture.row['instruction']] = digest(fixture.instruction)
    monkeypatch.chdir(new_root)
    assert profiles.BRIDGE2AI.pin_path.absolute() == new_pin
    fixture.old_pin, fixture.new_pin = old_pin, new_pin
    return fixture


def test_cross_checkout_vocabulary_preserves_original_locator_and_hash(
        vocabulary_checkpoint, monkeypatch):
    fixture = vocabulary_checkpoint
    original_profile = profiles.BRIDGE2AI
    original_cwd = Path.cwd()
    index, artifacts, _, _, args = runtime.integration_material(fixture.original)
    args['profile'] = fixture.original['profile']  # Deliberately restore the old ambient selection.
    # The unfixed named-profile replay really differs, despite identical bytes:
    # this exercises the resource resolver rather than mocking its selected path.
    plain = audit_batch_context.render_integration_context(**args, worker_index=index,
        worker_artifacts=output.worker_artifacts(fixture.original), row_artifacts=artifacts,
        audit_batch_navigation='explicit_child_reads_v1').encode()
    assert digest(plain) != digest(fixture.instruction)
    old_context = json.loads(fixture.instruction.split(b'\n', 1)[0])
    current_context = json.loads(plain.split(b'\n', 1)[0])
    old_authority = old_context['profile_vocabulary_authority']
    new_authority = current_context['profile_vocabulary_authority']
    assert old_authority == {**new_authority, 'path': str(fixture.old_pin)}
    assert old_authority['path'] != new_authority['path']
    opened = forbid_old_integration_reads(monkeypatch, fixture)
    def forbidden_chdir(*args):
        pytest.fail('reconstruction must not change process working directory')
    monkeypatch.setattr(os, 'chdir', forbidden_chdir)
    assert runtime.verify_checkpoint_context(fixture.current, fixture.source) is None
    assert Path.cwd() == original_cwd
    assert profiles.BRIDGE2AI is original_profile
    assert original_profile.tracks_digest_pin is True
    assert original_profile.pin_path.absolute() == fixture.new_pin
    assert fixture.old_pin in opened and fixture.new_pin in opened
    rebound = runtime._checkpoint_profile(fixture.current, fixture.original)
    assert rebound.pin_path == fixture.old_pin and not rebound.tracks_digest_pin
    assert vars(rebound) == {**vars(original_profile),
                            'vocabulary_pin': fixture.old_pin, 'tracks_digest_pin': False}


def test_historical_context_reconstruction_ignores_third_checkout_vocabulary(
        vocabulary_checkpoint, tmp_path, monkeypatch):
    fixture = vocabulary_checkpoint
    third_root = tmp_path / 'later-evaluation-checkout'
    third_pin = third_root / 'src/data_sheets_schema/b2ai_registry_vocabularies.yaml'
    third_pin.parent.mkdir(parents=True)
    third_pin.write_bytes(b'vocabularies: {}\n# Unrelated later checkout resource.\n')
    (third_root / 'pyproject.toml').write_text('[project]\nname = "data-sheets-schema"\n')
    monkeypatch.chdir(third_root)
    assert profiles.BRIDGE2AI.pin_path.absolute() == third_pin
    opened = forbid_old_integration_reads(monkeypatch, fixture)
    def forbidden_chdir(*args):
        pytest.fail('historical reconstruction must not change process cwd')
    monkeypatch.setattr(os, 'chdir', forbidden_chdir)
    assert runtime.verify_checkpoint_context(fixture.current, fixture.source) is None
    assert fixture.old_pin in opened and fixture.new_pin in opened
    assert third_pin not in opened
    assert Path.cwd() == third_root


@pytest.mark.parametrize('override', ['registered_absolute', 'outside_absolute', 'relative_escape'])
def test_declared_vocabulary_overrides_require_exact_registered_mapping(
        vocabulary_checkpoint, tmp_path, monkeypatch, override):
    from data_sheets_schema import schema_digest
    fixture = vocabulary_checkpoint
    value = (fixture.new_pin if override == 'registered_absolute' else
             tmp_path / 'outside-vocabulary.yaml' if override == 'outside_absolute' else
             Path('../current-checkout/src/data_sheets_schema/b2ai_registry_vocabularies.yaml'))
    monkeypatch.setattr(schema_digest, 'VOCABULARY_PIN', value)
    forbid_old_integration_reads(monkeypatch, fixture)
    if override == 'registered_absolute':
        assert runtime.verify_checkpoint_context(fixture.current, fixture.source) is None
    else:
        with pytest.raises(BudgetStop, match='vocabulary authority'):
            runtime.verify_checkpoint_context(fixture.current, fixture.source)


@pytest.mark.parametrize('damage', ['old_bytes', 'new_bytes', 'both_bytes_repinned',
    'old_pin_missing', 'current_old_pin_missing', 'current_new_pin_missing',
    'different_pins', 'unmapped_current_repository', 'different_profile'])
def test_cross_checkout_vocabulary_authority_changes_refuse(
        vocabulary_checkpoint, monkeypatch, damage):
    fixture = vocabulary_checkpoint
    if damage in ('old_bytes', 'new_bytes'):
        path = fixture.old_pin if damage == 'old_bytes' else fixture.new_pin
        path.write_bytes(b'vocabularies: {}\n# Altered vocabulary bytes.\n')
    elif damage == 'both_bytes_repinned':
        raw = b'vocabularies: {}\n# Both copies changed, but frozen context did not.\n'
        for path in (fixture.old_pin, fixture.new_pin):
            path.write_bytes(raw)
            fixture.current['pinned_files'][str(path)] = digest(raw)
        fixture.original['pinned_files'][str(fixture.old_pin)] = digest(raw)
    elif damage == 'old_pin_missing':
        del fixture.original['pinned_files'][str(fixture.old_pin)]
    elif damage == 'current_old_pin_missing':
        del fixture.current['pinned_files'][str(fixture.old_pin)]
    elif damage == 'current_new_pin_missing':
        del fixture.current['pinned_files'][str(fixture.new_pin)]
    elif damage == 'different_pins':
        fixture.current['pinned_files'][str(fixture.new_pin)] = '0' * 64
    elif damage == 'unmapped_current_repository':
        fixture.current['repository'] = str(fixture.old_pin.parent)
    else:
        fixture.current['profile'] = 'neutral'
    forbid_old_integration_reads(monkeypatch, fixture)
    with pytest.raises(BudgetStop, match='vocabulary authority|scientific context'):
        runtime.verify_checkpoint_context(fixture.current, fixture.source)


@pytest.mark.parametrize('template', ['persistent_system', 'scientific_context'])
def test_cross_checkout_vocabulary_does_not_mask_template_drift(
        vocabulary_checkpoint, monkeypatch, template):
    fixture = vocabulary_checkpoint
    module, name = ((batch_registration, 'child_system') if template == 'persistent_system'
                   else (audit_batch_context, 'render_integration_context'))
    render = getattr(module, name)
    monkeypatch.setattr(module, name, lambda *args, **kwargs:
        render(*args, **kwargs) + '\nChanged synthetic duty.\n')
    forbid_old_integration_reads(monkeypatch, fixture)
    with pytest.raises(BudgetStop, match='original integration'):
        runtime.verify_checkpoint_context(fixture.current, fixture.source)


def test_neutral_profile_reconstruction_needs_no_vocabulary_pin(context_checkpoint):
    fixture = context_checkpoint
    assert runtime._checkpoint_profile(fixture.current, fixture.original) is profiles.NEUTRAL


def test_exact_original_locator_context_reconstructs_without_old_body_reads(
        context_checkpoint, monkeypatch):
    fixture = context_checkpoint
    opened = forbid_old_integration_reads(monkeypatch, fixture)
    assert runtime.verify_checkpoint_context(fixture.current, fixture.source) is None
    # Both source documents, every complete proposal and original canonical row
    # locator participate in the independently generated expected context.
    assert b'Second source context remains available.' in fixture.instruction
    assert b'Synthetic source-supported omission' in fixture.instruction
    assert str(fixture.staged['files']['full_schema']).encode() in fixture.instruction
    assert all(str(path).encode() in fixture.instruction for path in fixture.views)
    assert all(Path(worker['proposal_path']) in opened
               for worker in fixture.original['audit_batches']['children'][:-1])
    assert Path(fixture.original['inputs']['protocol']) in opened
    assert b'FORBIDDEN_FAILED_INTEGRATION_BODY' not in fixture.instruction


@pytest.mark.parametrize('damage', ['system_hash', 'system_pin_missing',
    'instruction_hash', 'instruction_pin_missing', 'instruction_not_frozen'])
def test_missing_or_changed_original_prompt_authority_refuses(
        context_checkpoint, monkeypatch, damage):
    fixture = context_checkpoint
    if damage == 'system_hash':
        fixture.original['pinned_files'][fixture.row['system_prompt']] = '0' * 64
    elif damage == 'system_pin_missing':
        del fixture.original['pinned_files'][fixture.row['system_prompt']]
    elif damage == 'instruction_hash':
        fixture.current['pinned_files'][fixture.row['instruction']] = '0' * 64
    elif damage == 'instruction_pin_missing':
        del fixture.current['pinned_files'][fixture.row['instruction']]
    else:
        fixture.source.evidence_paths = frozenset()
    forbid_old_integration_reads(monkeypatch, fixture)
    with pytest.raises(BudgetStop, match='original integration'):
        runtime.verify_checkpoint_context(fixture.current, fixture.source)


@pytest.mark.parametrize('control', ['persistent_system', 'output_operations'])
def test_notes_control_template_drift_refuses_even_with_unchanged_scientific_source(
        context_checkpoint, monkeypatch, control):
    fixture = context_checkpoint
    module, name = ((batch_registration, 'child_system') if control == 'persistent_system'
                    else (output, 'instruction'))
    original = getattr(module, name)
    monkeypatch.setattr(module, name, lambda *args, **kwargs:
        original(*args, **kwargs) + '\nSynthetic changed terminal duty.\n')
    forbid_old_integration_reads(monkeypatch, fixture)
    with pytest.raises(BudgetStop, match='system duties'):
        runtime.verify_checkpoint_context(fixture.current, fixture.source)


def test_dynamic_renderer_drift_refuses_without_old_instruction_read(
        context_checkpoint, monkeypatch):
    fixture = context_checkpoint
    render = audit_batch_context.render_integration_context
    monkeypatch.setattr(audit_batch_context, 'render_integration_context',
        lambda **kwargs: render(**kwargs) + '\nSynthetic omitted duty replacement.\n')
    forbid_old_integration_reads(monkeypatch, fixture)
    with pytest.raises(BudgetStop, match='scientific context'):
        runtime.verify_checkpoint_context(fixture.current, fixture.source)


@pytest.mark.parametrize('damage', ['row_judgment', 'worker_finding'])
def test_complete_worker_content_drift_changes_reconstructed_context(
        context_checkpoint, monkeypatch, damage):
    fixture = context_checkpoint
    path = Path(fixture.original['audit_batches']['children'][0]['proposal_path'])
    value = json.loads(path.read_bytes())
    if damage == 'row_judgment':
        value['source_review']['values'][0]['claims'][0]['reason'] = 'Changed synthetic judgment.'
    else:
        value['findings'][0]['issue'] = 'Changed synthetic finding.'
    path.write_bytes(audit_batches.canonical_bytes(value))
    # Even internally consistent replacement row copies cannot change the
    # frozen original instruction hash. Individual file corruption is separate.
    _, _, fixture.views, _, _ = runtime.integration_material(fixture.original)
    for name, raw in fixture.views.items():
        Path(name).write_bytes(raw)
    forbid_old_integration_reads(monkeypatch, fixture)
    with pytest.raises(BudgetStop, match='scientific context'):
        runtime.verify_checkpoint_context(fixture.current, fixture.source)


def test_canonical_worker_row_copy_drift_refuses(context_checkpoint, monkeypatch):
    fixture = context_checkpoint
    Path(next(iter(fixture.views))).write_bytes(b'{}')
    forbid_old_integration_reads(monkeypatch, fixture)
    with pytest.raises(ValueError, match='row_view_does_not_bind_worker_row'):
        runtime.verify_checkpoint_context(fixture.current, fixture.source)


def test_guard_is_read_only_and_does_not_enter_closure_or_scientific_checker(
        context_checkpoint, monkeypatch):
    fixture = context_checkpoint
    def forbidden(*args, **kwargs):
        pytest.fail('prompt equivalence must not replay worker closures or scientific validation')
    monkeypatch.setattr(output, 'worker_closures', forbidden)
    monkeypatch.setattr(output, 'validate_output', forbidden)
    monkeypatch.setattr(output, '_assembled', forbidden)
    monkeypatch.setattr(output, '_exclusive', forbidden)
    forbid_old_integration_reads(monkeypatch, fixture)
    assert runtime.verify_checkpoint_context(fixture.current, fixture.source) is None
