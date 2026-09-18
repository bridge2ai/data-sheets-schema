"""Exact-file Phase 4 checks and bounded closing-repair behavior, without providers."""
import copy
import hashlib
import json
from pathlib import Path
import sys

import pytest

from audit_controls.test_contract import audit_fixture
from data_sheets_schema import source_review
from . import contract


SCHEMA = """id: https://example.org/{name}
name: {name}
prefixes:
  linkml: https://w3id.org/linkml/
imports:
  - linkml:types
default_range: string
classes:
  CoreDistribution: {{}}
  FileCollection: {{}}
  File: {{}}
  {cls}:
    tree_root: true
    attributes:
      description:
        range: string
      conforms_to_class:
        range: string
        annotations:
          'd4d:perRecord': true
      conforms_to_schema:
        range: string
        annotations:
          'd4d:perRecord': true
"""


def final_fixture(tmp_path):
    manifest, audit = audit_fixture(tmp_path)
    old_audit = Path(manifest['job'].pop('audit_path'))
    frozen = tmp_path / 'inputs' / 'accepted_audit.json'
    old_audit.rename(frozen)
    manifest['inputs']['audit'] = str(frozen)
    for key, cls in [('full_schema', 'Dataset'), ('core_schema', 'CoreDataset')]:
        Path(manifest['inputs'][key]).write_text(SCHEMA.format(name=key, cls=cls))
    job = manifest['job']
    job.update(id='EXAMPLE_finalize')
    for key, name in [('full_path', 'full.yaml'), ('core_path', 'core.yaml'), ('report_path', 'report.md')]:
        job[key] = str(Path(job['output_dir']) / name)
    manifest['python'] = sys.executable
    manifest['pinned_files'] = {path: hashlib.sha256(Path(path).read_bytes()).hexdigest() for path in manifest['inputs'].values()}
    full = Path(job['full_path'])
    full.write_text('description: The service is planned.\n')
    from data_sheets_schema.derive_core import core_text
    from data_sheets_schema.d4d_pair_consistency import load_pair_schema
    pair = load_pair_schema(Path(manifest['inputs']['full_schema']), Path(manifest['inputs']['core_schema']))
    Path(job['core_path']).write_text(core_text(full, pair, phase4_complete=True)[0])
    write_report(manifest)
    return manifest


def report_payload(manifest):
    full = Path(manifest['job']['full_path']).read_text()
    inv = source_review.inventory(full, 'final_full')
    return {'claims': [], 'source_review': {'artifact': 'final_full', 'sha256': inv['sha256'],
        'values': [{'path': '/description', 'claims': [{
            'text': 'The service is planned.', 'verdict': 'supported', 'attributed_to': ['protocol.txt'],
            'claim_status': 'planned', 'source_status': 'planned',
            'evidence': [{'source': 'protocol.txt', 'chunk': 'c001', 'quote': 'The service is planned.'}],
            'reason': 'The complete source states planned status.'}]}]}}


def write_report(manifest, *, payload=None, disposition='changed'):
    payload = report_payload(manifest) if payload is None else payload
    Path(manifest['job']['report_path']).write_text(
        '# Reconciliation\n\n## Claims\n\nNo slots were removed.\n\n'
        '## Semantic review\n\nNo collections, files, quantities or releases in this fixture; reviewed: consistent.\n\n'
        '## Evidence assertions\n\n```json\n' + json.dumps(payload) + '\n```\n\n'
        '## Dispositions\n\n| slot | disposition | record | reason |\n| --- | --- | --- | --- |\n'
        f'| `description` | {disposition} | both | Qualified the service status. |\n')


@pytest.fixture
def quick_validators(monkeypatch):
    # Real evidence/source-review, projection/pair, grounding and report checkers
    # still run. The subprocess schema/term validators have a separate real test.
    monkeypatch.setattr(contract, '_run_validator', lambda *a, **kw: {'checked': True, 'passed': True, 'findings': []})


def test_real_final_check_is_pure_and_all_checks_pass(tmp_path):
    manifest = final_fixture(tmp_path)
    before = {p: p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    result = contract.validate_final(manifest)
    assert result['passed'], result
    assert result['checked'] and not result['repairable'] and not result['terminal']
    assert set(result['record_checks']) == {'full_schema', 'full_terms', 'core_schema', 'core_terms', 'pair', 'grounding', 'derivation'}
    assert all(r['passed'] for r in result['source_reviews'].values())
    assert before == {p: p.read_bytes() for p in before}


@pytest.mark.parametrize('damage', ['missing_review', 'stale_hash', 'missing_value', 'rejected_final', 'false_quote', 'wrong_status', 'audit_namespace'])
def test_real_source_or_evidence_failure_is_terminal(tmp_path, quick_validators, damage):
    manifest = final_fixture(tmp_path)
    payload = report_payload(manifest)
    if damage == 'missing_review': payload.pop('source_review')
    elif damage == 'stale_hash': payload['source_review']['sha256'] = '0' * 64
    elif damage == 'missing_value': payload['source_review']['values'] = []
    elif damage == 'rejected_final': payload['source_review']['values'][0]['claims'][0]['verdict'] = 'revise'
    elif damage == 'false_quote': payload['source_review']['values'][0]['claims'][0]['evidence'][0]['quote'] = 'The service is deployed.'
    elif damage == 'wrong_status': payload['source_review']['values'][0]['claims'][0]['claim_status'] = 'completed'
    else:
        path = Path(manifest['inputs']['audit']); audit = json.loads(path.read_text())
        audit['findings'][0]['record'] = 'original_full'; path.write_text(json.dumps(audit))
        manifest['pinned_files'][str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
    write_report(manifest, payload=payload)
    result = contract.validate_final(manifest)
    assert not result['passed'] and not result['repairable'] and result['terminal'], result


def test_ordinary_disposition_finding_allows_one_repair(tmp_path, quick_validators):
    manifest = final_fixture(tmp_path)
    write_report(manifest, disposition='removed')
    result = contract.validate_final(manifest)
    assert result['checked'] and not result['passed'] and result['repairable'] and not result['terminal'], result
    assert result['evidence']['findings'] == []
    assert all(x['passed'] for x in result['source_reviews'].values())
    assert any(x['check'] == 'report_claims' for x in result['findings'])


@pytest.mark.parametrize('role', sorted(contract.INPUTS))
def test_every_inherited_input_pin_checked(tmp_path, quick_validators, role):
    manifest = final_fixture(tmp_path)
    path = Path(manifest['inputs'][role]); path.write_bytes(path.read_bytes() + b'\n')
    result = contract.validate_final(manifest)
    assert result['terminal'] and not result['repairable'] and result['errors']


@pytest.mark.parametrize('damage', ['hardlink', 'symlink', 'duplicate_yaml', 'output_alias', 'outside_output'])
def test_invalid_file_identity_and_mapping_are_terminal(tmp_path, quick_validators, damage):
    manifest = final_fixture(tmp_path); target = Path(manifest['job']['full_path'])
    if damage == 'hardlink': (tmp_path / 'alias.yaml').hardlink_to(target)
    elif damage == 'symlink':
        other = tmp_path / 'other.yaml'; target.rename(other); target.symlink_to(other)
    elif damage == 'duplicate_yaml': target.write_text('description: a\ndescription: b\n')
    elif damage == 'output_alias': manifest['job']['core_path'] = str(target)
    else: manifest['job']['full_path'] = str(tmp_path / 'outside.yaml')
    result = contract.validate_final(manifest)
    assert not result['passed'] and result['terminal'] and result['errors'], result


@pytest.mark.parametrize('which', ['full_path', 'core_path', 'report_path', 'bundle'])
def test_midcheck_changed_or_removed_file_never_passes(tmp_path, monkeypatch, quick_validators, which):
    manifest = final_fixture(tmp_path)
    original = contract.evidence_assertions.check_files
    path = Path(manifest['inputs']['bundle'] if which == 'bundle' else manifest['job'][which])
    def changed(**kwargs):
        out = original(**kwargs)
        path.unlink()
        return out
    monkeypatch.setattr(contract.evidence_assertions, 'check_files', changed)
    result = contract.validate_final(manifest)
    assert not result['passed'] and result['terminal'] and result['errors']


def cli_fixture(tmp_path, monkeypatch):
    manifest = final_fixture(tmp_path)
    path = tmp_path / 'registration.json'; path.write_text(json.dumps(manifest))
    from . import registration
    monkeypatch.setattr(registration, 'validate_registration', lambda p: json.loads(Path(p).read_bytes()))
    monkeypatch.setattr(contract, '_report_context', lambda m, full, core: 'Shared report context fixture: ' + full + core)
    return manifest, path


def call(path, operation, round=None):
    args = ['--registration', str(path), '--operation', operation]
    if round is not None: args += ['--round', str(round)]
    return contract.main(args)


def test_cli_derivation_receipt_current_inventory_and_final_pass(tmp_path, monkeypatch, quick_validators, capsys):
    manifest, path = cli_fixture(tmp_path, monkeypatch)
    full = Path(manifest['job']['full_path']).read_bytes()
    assert call(path, 'derive') == 0
    text = capsys.readouterr().out; receipt = json.loads(text)
    attempt = Path(manifest['job']['attempt_dir'])
    assert (attempt / 'derivations/000001.json').read_text() == text
    assert (attempt / 'current_derivation.json').read_text() == text
    assert json.loads((attempt / 'final_inventory.json').read_text()) == source_review.inventory(full.decode(), 'final_full')
    assert 'inventory' not in receipt
    assert isinstance(receipt['report_context'], dict)
    assert Path(manifest['job']['full_path']).read_bytes() == full
    assert call(path, 'check', 0) == 0
    text = capsys.readouterr().out
    assert (attempt / 'check-0.json').read_text() == text
    assert json.loads(text)['passed']
    assert not (attempt / 'failure.json').exists()
    saved = (attempt / 'check-0.json').read_bytes()
    assert call(path, 'derive') == 1
    assert (attempt / 'check-0.json').read_bytes() == saved
    assert (attempt / 'failure.json').exists()


def test_exactly_one_closing_repair_with_fresh_derivation(tmp_path, monkeypatch, quick_validators, capsys):
    manifest, path = cli_fixture(tmp_path, monkeypatch)
    assert call(path, 'derive') == 0; capsys.readouterr()
    write_report(manifest, disposition='removed')
    assert call(path, 'check', 0) == 0
    first = json.loads(capsys.readouterr().out)
    assert first['repairable'] and not first['terminal'] and not first['passed']
    write_report(manifest)
    assert call(path, 'derive') == 0; capsys.readouterr()
    assert call(path, 'check', 1) == 0
    assert json.loads(capsys.readouterr().out)['passed']
    assert call(path, 'check', 1) == 1


def test_ordinary_failure_on_second_check_is_terminal(tmp_path, monkeypatch, quick_validators, capsys):
    manifest, path = cli_fixture(tmp_path, monkeypatch)
    call(path, 'derive'); capsys.readouterr(); write_report(manifest, disposition='removed')
    call(path, 'check', 0); capsys.readouterr(); call(path, 'derive'); capsys.readouterr()
    assert call(path, 'check', 1) == 1
    result = json.loads(capsys.readouterr().out)
    assert result['terminal'] and not result['repairable']
    assert (Path(manifest['job']['attempt_dir']) / 'failure.json').exists()


@pytest.mark.parametrize('damage', ['no_derive', 'stale_full', 'stale_core', 'stale_inventory', 'round1_first', 'interrupted_check'])
def test_closing_order_and_freshness_are_enforced(tmp_path, monkeypatch, quick_validators, capsys, damage):
    manifest, path = cli_fixture(tmp_path, monkeypatch); attempt = Path(manifest['job']['attempt_dir'])
    if damage != 'no_derive': call(path, 'derive'); capsys.readouterr()
    if damage in {'stale_full', 'stale_core'}:
        target = Path(manifest['job'][damage.removeprefix('stale_') + '_path']); target.write_bytes(target.read_bytes() + b'\n')
    elif damage == 'stale_inventory': (attempt / 'final_inventory.json').write_text('{}')
    elif damage == 'interrupted_check': (attempt / 'check-0.json').write_bytes(b'')
    assert call(path, 'check', 1 if damage == 'round1_first' else 0) == 1
    assert (attempt / 'failure.json').exists()


def test_repair_requires_new_derivation_even_if_only_report_changed(tmp_path, monkeypatch, quick_validators, capsys):
    manifest, path = cli_fixture(tmp_path, monkeypatch)
    call(path, 'derive'); capsys.readouterr(); write_report(manifest, disposition='removed')
    call(path, 'check', 0); capsys.readouterr(); write_report(manifest)
    assert call(path, 'check', 1) == 1
    assert 'fresh derivation' in json.loads(capsys.readouterr().out)['errors'][0]


def test_rejected_source_review_never_repaired_or_overwritten(tmp_path, monkeypatch, quick_validators, capsys):
    manifest, path = cli_fixture(tmp_path, monkeypatch)
    call(path, 'derive'); capsys.readouterr()
    payload = report_payload(manifest); payload['source_review']['values'] = []
    write_report(manifest, payload=payload)
    assert call(path, 'check', 0) == 1; capsys.readouterr()
    attempt = Path(manifest['job']['attempt_dir']); before = (attempt / 'check-0.json').read_bytes()
    assert call(path, 'derive') == 1
    assert (attempt / 'check-0.json').read_bytes() == before


def test_unexpected_derivation_failure_is_preserved_and_terminal(tmp_path, monkeypatch, quick_validators, capsys):
    manifest, path = cli_fixture(tmp_path, monkeypatch)
    monkeypatch.setattr(contract, '_record_checks', lambda *a, **kw: (_ for _ in ()).throw(RuntimeError('checker unavailable')))
    assert call(path, 'derive') == 1
    text = capsys.readouterr().out; attempt = Path(manifest['job']['attempt_dir'])
    assert (attempt / 'derivations/000001.json').read_text() == text
    assert (attempt / 'failure.json').read_text() == text


@pytest.mark.parametrize('raw', ['description: first\ndescription: second\n', 'description: [\n', '[]\n'])
def test_invalid_full_before_report_can_be_corrected_then_derived(tmp_path, monkeypatch, quick_validators, capsys, raw):
    manifest, path = cli_fixture(tmp_path, monkeypatch)
    target = Path(manifest['job']['full_path']); original = target.read_bytes(); target.write_text(raw)
    assert call(path, 'derive') == 0
    failure = json.loads(capsys.readouterr().out)
    assert failure['checked'] and not failure['passed'] and not failure['terminal']
    assert target.read_text() == raw
    target.write_bytes(original)
    assert call(path, 'derive') == 0
    assert json.loads(capsys.readouterr().out)['passed']


def test_ordinary_schema_failure_does_not_enter_projection(tmp_path, monkeypatch, quick_validators, capsys):
    manifest, path = cli_fixture(tmp_path, monkeypatch)
    monkeypatch.setattr(contract, '_one_record_checks', lambda *a: {'schema': {'checked': True, 'passed': False, 'findings': ['wrong shape']}, 'terms': {'checked': True, 'passed': True, 'findings': []}})
    from data_sheets_schema import derive_core
    monkeypatch.setattr(derive_core, 'core_text', lambda *a, **kw: pytest.fail('invalid full entered projection'))
    assert call(path, 'derive') == 0
    result = json.loads(capsys.readouterr().out)
    assert result['checked'] and not result['passed'] and not result['terminal']


def test_helper_lock_cannot_overlap_an_immutable_input(tmp_path, monkeypatch, quick_validators, capsys):
    manifest, path = cli_fixture(tmp_path, monkeypatch)
    lock = Path(manifest['job']['attempt_dir']) / '.helpers.lock'
    lock.write_bytes(b'immutable original')
    manifest['inputs']['receipt'] = str(lock)
    manifest['pinned_files'][str(lock)] = hashlib.sha256(lock.read_bytes()).hexdigest()
    path.write_text(json.dumps(manifest))
    assert call(path, 'derive') == 1
    assert lock.read_bytes() == b'immutable original'


def test_current_derivation_must_equal_preserved_helper_receipt(tmp_path, monkeypatch, quick_validators, capsys):
    manifest, path = cli_fixture(tmp_path, monkeypatch)
    call(path, 'derive'); capsys.readouterr()
    marker = Path(manifest['job']['attempt_dir']) / 'current_derivation.json'
    value = json.loads(marker.read_text()); value['report_context'] = 'changed'; marker.write_text(json.dumps(value))
    assert call(path, 'check', 0) == 1
    assert 'preserved receipt' in json.loads(capsys.readouterr().out)['errors'][0]


def test_normalized_source_boolean_cannot_hide_rejected_raw_review(tmp_path, monkeypatch, quick_validators, capsys):
    manifest, path = cli_fixture(tmp_path, monkeypatch)
    call(path, 'derive'); capsys.readouterr(); write_report(manifest, disposition='removed')
    call(path, 'check', 0); capsys.readouterr()
    marker = Path(manifest['job']['attempt_dir']) / 'check-0.json'
    value = json.loads(marker.read_text()); value['evidence']['source_review_final']['findings'] = [{'detail': 'rejected'}]
    marker.write_text(json.dumps(value))
    assert call(path, 'derive') == 1


@pytest.mark.parametrize('field', ['evidence', 'source_reviews', 'errors', 'checked', 'terminal', 'operation'])
def test_copied_repair_boolean_alone_does_not_admit_second_check(tmp_path, monkeypatch, quick_validators, capsys, field):
    manifest, path = cli_fixture(tmp_path, monkeypatch)
    call(path, 'derive'); capsys.readouterr(); write_report(manifest, disposition='removed')
    call(path, 'check', 0); capsys.readouterr()
    marker = Path(manifest['job']['attempt_dir']) / 'check-0.json'; value = json.loads(marker.read_text())
    value.pop(field); marker.write_text(json.dumps(value))
    assert call(path, 'derive') == 1


def test_parent_renderer_replay_and_complete_report_context(tmp_path):
    from audit_controls.test_contract import rendered_fixture
    audit_manifest, _ = rendered_fixture(tmp_path)
    audit_path = Path(audit_manifest['job']['audit_path'])
    audit_manifest['pinned_files'] = {p: hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in audit_manifest['inputs'].values()}
    accepted = tmp_path / 'accepted.json'; accepted.write_text(json.dumps(audit_manifest))
    manifest = copy.deepcopy(audit_manifest)
    manifest['inputs']['audit'] = str(audit_path)
    manifest['accepted_audit'] = {'registration': {'path': str(accepted), 'sha256': hashlib.sha256(accepted.read_bytes()).hexdigest()}}
    job = manifest['job']; job.update(full_path=str(tmp_path/'full.yaml'), core_path=str(tmp_path/'core.yaml'), report_path=str(tmp_path/'report.md'),
        derive_argv=[sys.executable,'-m','finalization_controls.contract','--operation','derive'],
        check_argv=[[sys.executable,'-m','finalization_controls.contract','--operation','check','--round',str(i)] for i in (0,1)])
    text = contract.render_instruction(manifest)
    assert text == contract.render_instruction(copy.deepcopy(manifest))
    assert contract.api_runner.phase_instruction('reconcile_full',14) in text
    assert Path(manifest['inputs']['original_full']).read_text() in text
    assert Path(manifest['inputs']['original_core']).read_text() in text
    report_context = contract._report_context(manifest, 'description: The service is planned.\n', 'description: The service is planned.\n')
    assert contract.api_runner.phase_instruction('report',14) in report_context
    assert '# Required source-review inventory' in report_context
    assert '# Computed audit counts' in report_context
    assert 'No second repair is permitted' in text
    assert 'Use native Read for every exact listed offset/limit range' in text
    # Every omitted prefix block is literally present in the initial request;
    # every new report block survives byte-for-byte in the suffix.
    carry = contract._carry(manifest)
    with contract._parent_spec(manifest) as spec:
        initial = contract.api_runner.build_phase(spec, 'reconcile_full', carry=carry)
        carry.update({'Reconciled full record': 'description: The service is planned.\n', 'Reconciled core record': 'description: The service is planned.\n'})
        report = contract.api_runner.build_phase(spec, 'report', carry=carry)
    prefix = initial.messages[0]['content'][:-1]
    assert report.messages[0]['content'][:len(prefix)] == prefix
    assert all(block['text'] in text for block in prefix)
    assert all(block['text'] in report_context for block in report.messages[0]['content'][len(prefix):])


@pytest.mark.parametrize('text', ['A' * 25001, ('α𓀀🙂\\\n\t"' * 2000), 'A single line\nwith embedded newlines\n'])
def test_context_frames_are_bounded_lossless_and_have_no_trailing_blank(text):
    lines = contract.context_lines(text)
    assert all(len(line.encode()) <= 1000 for line in lines)
    raw = '\n'.join(lines)
    assert not raw.endswith('\n')
    frames = [json.loads(line) for line in raw.split('\n')]
    assert [f['index'] for f in frames] == list(range(1, len(lines) + 1))
    assert ''.join(f['text'] for f in frames) == text


def test_large_context_is_file_delivered_with_compact_helper_stdout(tmp_path, monkeypatch, quick_validators, capsys):
    manifest, path = cli_fixture(tmp_path, monkeypatch)
    context = ('Exact shared final context.\n' * 15000)
    monkeypatch.setattr(contract, '_report_context', lambda *a: context)
    assert call(path, 'derive') == 0
    printed = capsys.readouterr().out; result = json.loads(printed)
    assert len(printed.encode()) < 12000
    assert 'inventory' not in result and 'Exact shared final context.' not in printed
    delivery = result['report_context']; raw = Path(delivery['path']).read_bytes()
    assert raw[-1:] != b'\n' and hashlib.sha256(raw).hexdigest() == delivery['sha256']
    lines = raw.decode().split('\n')
    assert len(lines) == delivery['line_count']
    assert ''.join(json.loads(line)['text'] for line in lines) == context
    covered = [i for r in delivery['read_ranges'] for i in range(r['offset'], r['offset'] + r['limit'])]
    assert covered == list(range(1, len(lines) + 1))
    assert all(0 < r['limit'] <= 12 for r in delivery['read_ranges'])


@pytest.mark.parametrize('damage', ['bytes', 'trailing_blank', 'symlink', 'hardlink'])
def test_changed_report_context_blocks_closing_check(tmp_path, monkeypatch, quick_validators, capsys, damage):
    manifest, path = cli_fixture(tmp_path, monkeypatch)
    call(path, 'derive'); result = json.loads(capsys.readouterr().out)
    target = Path(result['report_context']['path'])
    if damage == 'bytes': target.write_text('{"index":1,"text":"changed"}')
    elif damage == 'trailing_blank': target.write_bytes(target.read_bytes() + b'\n')
    elif damage == 'hardlink': (tmp_path / 'alias.jsonl').hardlink_to(target)
    else:
        other = tmp_path / 'other.jsonl'; target.rename(other); target.symlink_to(other)
    assert call(path, 'check', 0) == 1
    assert (Path(manifest['job']['attempt_dir']) / 'failure.json').exists()
