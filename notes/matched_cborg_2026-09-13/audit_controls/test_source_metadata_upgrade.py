"""Explicit v5 native/Phase4 lineage and authority; synthetic offline inputs only.

The inherited fixture stubs old transcript/accounting checks and Git attestation,
but retains the real preparers, renderers, file pins and registration validators.
No test opens a ledger, claims ownership or constructs a provider.
"""
from copy import deepcopy
import json
from pathlib import Path
import sys

import pytest

BASE = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(BASE), str(BASE / 'native_controls')]
from audit_controls import contract, contract_context, prepare, registration
from audit_controls.test_context_preparation import ancestry, accepted_audit, save
from audit_controls.test_staged_preparation import actual_renderer_history_root
from audit_controls.test_protocol_upgrade import scientific_repositories
from finalization_controls import contract as final_contract, prepare as final_prepare, registration as final_registration
from evaluation_controls import registration as evaluation_registration
from data_sheets_schema import api_runner
import prepare_registration
import run_api_canary

KEY = registration.TRANSITION
BLOCK = {'kind': 'frozen_pair_protocol_v5'}


def select(manifest):
    manifest.update(protocol_version=5, render_version=16)
    manifest[KEY] = deepcopy(BLOCK)


@pytest.mark.parametrize('value', [None, False, True, [], {}, 'frozen_pair_protocol_v5',
                                  {'kind': 'unknown'}, {**BLOCK, 'extra': 1}])
def test_v5_selector_is_strict_at_both_registration_entries(tmp_path, value):
    for kind, validator in [('d4d_native_audit_continuation', registration.validate_registration),
                            (final_registration.KIND, final_registration.validate_registration)]:
        manifest = {'schema_version': 1, 'kind': kind, 'protocol_version': 5,
                    'render_version': 16, KEY: value}
        path = save(tmp_path/'registration.json', manifest)
        with pytest.raises(registration.BudgetStop, match='scientific contract transition'):
            validator(path)
    assert [p.name for p in tmp_path.iterdir()] == ['registration.json']


@pytest.mark.parametrize('changes', [{'protocol_version': 4}, {'render_version': 15},
                                   {'protocol_version': 5.0}, {'render_version': 16.0},
                                   {KEY: {'kind': 'frozen_pair_protocol_v4'}}])
def test_v5_selector_requires_its_exact_version_pair(changes):
    manifest = {KEY: BLOCK, 'protocol_version': 5, 'render_version': 16, **changes}
    with pytest.raises(registration.BudgetStop):
        registration.scientific_contract(manifest)


@pytest.mark.parametrize('value', [None, True, BLOCK])
def test_generation_and_evaluation_reject_transition_presence_before_setup(tmp_path, value):
    manifest = {KEY: value}
    path = save(tmp_path/'registration.json', manifest)
    with pytest.raises(registration.BudgetStop):
        run_api_canary.verify(manifest, path, 'unused')
    with pytest.raises(registration.BudgetStop):
        evaluation_registration.verify_manifest(manifest, path, 'unused')
    assert [p.name for p in tmp_path.iterdir()] == ['registration.json']


@pytest.mark.parametrize('value', [None, 0, 1, 'true', {}])
def test_v5_option_type_rejected_before_destination_creation(tmp_path, value):
    destination = tmp_path/'never-created'
    with pytest.raises(registration.BudgetStop, match='explicit boolean'):
        prepare.prepare(parent_registration=None, parent_overlay=None, parent_job_id=None,
            reconciliation_receipt=None, reconciled_checkpoint=None, destination=destination,
            job_id='unused', repository=tmp_path, source_metadata_evidence=value)
    assert not destination.exists()


def test_version_options_are_mutually_exclusive_before_preparation(tmp_path, monkeypatch):
    destination = tmp_path/'never-created'
    with pytest.raises(registration.BudgetStop, match='mutually exclusive'):
        prepare.prepare(parent_registration=None, parent_overlay=None, parent_job_id=None,
            reconciliation_receipt=None, reconciled_checkpoint=None, destination=destination,
            job_id='unused', repository=tmp_path, source_metadata_evidence=True,
            upgrade_evidence_protocol=True)
    monkeypatch.setattr(sys, 'argv', ['prepare', *sum(([f'--{name}', 'unused'] for name in
        ('parent-registration', 'parent-overlay', 'parent-job-id', 'reconciliation-receipt',
         'reconciled-checkpoint', 'destination', 'job-id')), []),
        '--upgrade-evidence-protocol', '--source-metadata-evidence'])
    monkeypatch.setattr(prepare, 'prepare', lambda **kw: pytest.fail('CLI accepted both instruments'))
    with pytest.raises(SystemExit) as error:
        prepare.main()
    assert error.value.code == 2 and not destination.exists()


def test_generation_renderer_is_explicit_and_default_unchanged():
    parser = prepare_registration.build_parser()
    assert parser.parse_args([]).render_version == 9
    assert parser.parse_args(['--render-version', '16']).render_version == 16


def install_metadata_authority(manifest, root):
    """A minimal selected-project registry; no dataset-specific scientific facts."""
    source = Path(manifest['inputs']['source_manifest'])
    source.write_text('source_priority:\n  2: [documentation]\nprojects:\n  EXAMPLE:\n'
                      '    - id: protocol\n      source_type: documentation\n'
                      '      processed_file: protocol.txt\n')
    parent = root/'generation.json'
    save(parent, {'generation': {'jobs': [{'id': 'EXAMPLE_parent', 'project': 'EXAMPLE',
        'input_identity': {'source_manifest': {'path': str(source), 'sha256': registration.sha(source)}}}]}})
    manifest['parent'] = {'registration': str(parent), 'job_id': 'EXAMPLE_parent'}
    manifest['pinned_files'][str(parent)] = registration.sha(parent)
    manifest['pinned_files'][str(source)] = registration.sha(source)
    return parent


@pytest.fixture
def metadata_ancestry(ancestry):
    args, example, _, state = ancestry
    source = Path(example['inputs']['source_manifest'])
    source.write_text('source_priority:\n  2: [documentation]\nprojects:\n  EXAMPLE:\n'
                      '    - id: protocol\n      source_type: documentation\n'
                      '      processed_file: protocol.txt\n')
    generation = registration.read_json(args['parent_registration'])
    generation['generation']['jobs'][0]['input_identity']['source_manifest']['sha256'] = registration.sha(source)
    save(args['parent_registration'], generation)
    preserved = {str(p): p.read_bytes() for p in state.parent.rglob('*') if p.is_file()}
    return args, example, preserved, state


@pytest.mark.parametrize('recovery,staged', [(False, False), (True, True)])
def test_actual_preparer_pins_explicit_v5_and_keeps_frozen_pair(metadata_ancestry, tmp_path, recovery, staged):
    args, _, preserved, _ = metadata_ancestry
    path = prepare.prepare(**args, destination=tmp_path/'v5', source_metadata_evidence=True,
        persistent_audit_contract=True, context_recovery=recovery, staged_audit_output=staged)
    m = registration.validate_registration(path)
    assert m[KEY] == BLOCK and (m['protocol_version'], m['render_version']) == (5, 16)
    assert Path(m['inputs']['protocol']).name == 'evidence_protocol_v5.md'
    for filename in registration.versioned_scientific_files(m):
        parent = str(Path(m['parent']['repository'])/'src/data_sheets_schema'/filename)
        assert m['pinned_files'][parent] == registration.sha(parent)
    helper = Path(m['repository'])/'src/data_sheets_schema/source_metadata.py'
    assert m['pinned_files'][str(helper)] == registration.sha(helper)
    instruction = Path(m['job']['instruction']).read_text()
    system = Path(m['job']['system_prompt']).read_text()
    assert 'protocol 5 / renderer 16' in instruction
    assert 'original generation remains renderer 14' in instruction
    assert api_runner.phase_instruction('audit', 16) in instruction
    assert api_runner.evidence_phase_contract('audit', 16) in system
    assert contract_context.enabled(m)
    assert contract.source_metadata_arguments(m, {k: Path(v) for k,v in m['inputs'].items()}) == {
        'source_manifest': Path(m['inputs']['source_manifest']), 'project': 'EXAMPLE'}
    assert set(m['job']['readable_inputs']) >= set(m['inputs'].values())
    assert not Path(m['budget']['ledger_path']).exists()
    assert not Path(m['job']['attempt_dir']).exists()
    assert not (path.parent/'sequence_claim').exists()
    assert preserved == {name: Path(name).read_bytes() for name in preserved}
    plan = registration.read_json(path.parent/'offline_plan.json')
    assert (plan['protocol_version'],plan['render_version'],plan['parent_render_version']) == (5,16,14)
    assert plan['scientific_instrument_unchanged'] is False


def test_phase4_inherits_v5_science_but_not_audit_settings(metadata_ancestry, tmp_path, monkeypatch):
    original = prepare.prepare
    monkeypatch.setattr(prepare, 'prepare', lambda **kw: original(
        **kw, source_metadata_evidence=True, persistent_audit_contract=True))
    accepted, acceptance = accepted_audit(metadata_ancestry, tmp_path/'accepted')
    path = final_prepare.prepare(accepted_audit_registration=accepted, acceptance=acceptance,
        destination=tmp_path/'final', job_id='synthetic_final', repository=metadata_ancestry[0]['repository'])
    m = final_registration.validate_registration(path)
    assert m[KEY] == BLOCK and (m['protocol_version'],m['render_version']) == (5,16)
    assert not {'audit_contract_context','audit_output','native_stall_policy',
                'native_upstream_read_timeout_seconds'} & m.keys()
    assert api_runner.phase_instruction('reconcile_full',16) in Path(m['job']['instruction']).read_text()
    context = final_contract._report_context(m,'description: A sample dataset is planned.\n',
                                           'description: A sample dataset is planned.\n')
    assert api_runner.phase_instruction('report',16) in context
    assert not Path(m['budget']['ledger_path']).exists()
    assert not Path(m['job']['attempt_dir']).exists()
    assert metadata_ancestry[2] == {name: Path(name).read_bytes() for name in metadata_ancestry[2]}
    m.update(protocol_version=4,render_version=15);m[KEY]={'kind':registration.TRANSITION_KIND}
    path.write_text(json.dumps(m))
    with pytest.raises(registration.BudgetStop,match='accepted scientific contract version'):
        final_registration.validate_registration(path)


def test_real_pure_audit_and_final_checks_receive_exact_authority(tmp_path, monkeypatch):
    from audit_controls.test_contract import audit_fixture
    from finalization_controls.test_contract import final_fixture
    seen=[]; original=contract.evidence_assertions.check_files
    def observed(**kw):
        seen.append(kw.copy());return original(**kw)
    monkeypatch.setattr(contract.evidence_assertions,'check_files',observed)
    for name, fixture, checker in [('audit',audit_fixture,contract.validate_audit),
                                   ('final',final_fixture,final_contract.validate_final)]:
        directory=tmp_path/name;directory.mkdir()
        value=fixture(directory);m=value[0] if isinstance(value,tuple) else value
        select(m);install_metadata_authority(m,directory)
        before={p:p.read_bytes() for p in directory.rglob('*') if p.is_file()}
        result=checker(m)
        assert result['passed'],result
        assert seen[-1]['protocol_version']==5 and seen[-1]['project']=='EXAMPLE'
        assert seen[-1]['source_manifest']==Path(m['inputs']['source_manifest'])
        assert before=={p:p.read_bytes() for p in before}


@pytest.mark.parametrize('damage',['unpin_parent','changed_parent','wrong_source_path','wrong_source_hash','empty_project'])
def test_metadata_authority_cannot_drift_from_pinned_parent(tmp_path,damage):
    from audit_controls.test_contract import audit_fixture
    m,_=audit_fixture(tmp_path);select(m);p=install_metadata_authority(m,tmp_path)
    if damage=='unpin_parent':del m['pinned_files'][str(p)]
    elif damage=='changed_parent':p.write_text(p.read_text()+' ')
    else:
        value=registration.read_json(p);job=value['generation']['jobs'][0]
        if damage=='wrong_source_path':job['input_identity']['source_manifest']['path']=str(tmp_path/'elsewhere')
        if damage=='wrong_source_hash':job['input_identity']['source_manifest']['sha256']='0'*64
        if damage=='empty_project':job['project']=''
        p.write_text(json.dumps(value));m['pinned_files'][str(p)]=registration.sha(p)
    with pytest.raises((registration.BudgetStop,ValueError)):
        contract.source_metadata_arguments(m,{k:Path(v) for k,v in m['inputs'].items()})


@pytest.mark.parametrize('version,renderer,block',[(3,14,None),(4,15,{'kind':registration.TRANSITION_KIND})])
def test_old_contracts_do_not_read_metadata_authority(version,renderer,block):
    m={'protocol_version':version,'render_version':renderer}
    if block:m[KEY]=block
    assert contract.source_metadata_arguments(m,{})=={}


def v5_repositories(tmp_path):
    m,accepted=scientific_repositories(tmp_path);select(m)
    for root in [Path(m['parent']['repository']),Path(m['repository'])]:
        for relative in ['src/data_sheets_schema/source_metadata.py','src/download/prompts/evidence_protocol_v5.md']:
            p=root/relative;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('same '+relative)
            m['pinned_files'][str(p)]=registration.sha(p)
    accepted['inputs']['protocol']=str(Path(accepted['repository'])/'src/download/prompts/evidence_protocol_v5.md')
    return m,accepted


def test_source_review_version_change_requires_v5_and_both_pins(tmp_path):
    m,_=v5_repositories(tmp_path)
    changed=Path(m['repository'])/'src/data_sheets_schema/source_review.py'
    changed.write_text('new protocol-5 source review');m['pinned_files'][str(changed)]=registration.sha(changed)
    registration.validate_scientific_identity(m)
    old=deepcopy(m);old.update(protocol_version=4,render_version=15);old[KEY]={'kind':registration.TRANSITION_KIND}
    with pytest.raises(registration.BudgetStop,match='source_review.py'):
        registration.validate_scientific_identity(old)
    for missing in [changed,Path(m['parent']['repository'])/'src/data_sheets_schema/source_review.py']:
        bad=deepcopy(m);del bad['pinned_files'][str(missing)]
        with pytest.raises(registration.BudgetStop,match='implementation changed'):
            registration.validate_scientific_identity(bad)


@pytest.mark.parametrize('relative',['src/data_sheets_schema/source_metadata.py',
    'src/data_sheets_schema/source_review.py','src/data_sheets_schema/anonymous_removals.py',
    'src/download/prompts/evidence_protocol_v5.md'])
def test_phase4_cannot_repin_a_different_accepted_v5_instrument(tmp_path,relative):
    m,accepted=v5_repositories(tmp_path)
    final_registration.validate_scientific_identity(m,accepted)
    p=Path(m['repository'])/relative;p.write_text('different but locally pinned')
    m['pinned_files'][str(p)]=registration.sha(p)
    with pytest.raises(registration.BudgetStop,match='accepted|inherited scientific'):
        final_registration.validate_scientific_identity(m,accepted)
