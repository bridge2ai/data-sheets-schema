"""Full-chain saved-input rehearsal, 2026-11-12. Explicit synthetic evidence.
No model/native peer executes; no attempt, capture or word reservation is made.
Production prepare/validate functions remain intact; source defects are findings.
"""
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import sys

from data_sheets_schema import native_shared_contract as c
from data_sheets_schema import native_execution_authority_v2 as authority
from data_sheets_schema import native_execution_registration_v2 as preparation
from data_sheets_schema import native_shared_controller_orchestration as composition
from data_sheets_schema import native_shared_registration_orchestration as registration
from tests.native_shared_fixture import build_native_fixture
from tests.utils.native_synthetic_evidence import runtime_for, bound_permission_for
from tests.utils.native_shared_consumer_scope import command_guidance
from tests.utils.native_u4b_fixtures import bundle_for

ROOT=Path(__file__).resolve().parents[1]
LABEL='SYNTHETIC FULL-CHAIN REHEARSAL; NOT ACTUAL CI, REVIEW, OWNER OR LAUNCH AUTHORITY'
spec=importlib.util.spec_from_file_location('review_adapter_full',ROOT/'scripts/native_packet_review_inputs.py')
adapter=importlib.util.module_from_spec(spec); spec.loader.exec_module(adapter)


def build_chain(root):
    data=build_native_fixture(root,registered_python=sys.executable)
    (root/'SYNTHETIC-NOT-AUTHORITY.txt').write_text(LABEL+'\n')
    results={'scope':LABEL,'completed':[],'reservation_performed':False}
    def save(name,value):
        raw=value if isinstance(value,bytes) else c.canonical(value)
        path=root/(name+'.json'); path.write_bytes(raw)
        results['completed'].append({'document':name,'path':str(path),'bytes':len(raw),'sha256':c.sha(raw)})
        (root/'chain-progress.json').write_bytes(c.canonical(results))
        return path
    try:
        runtime=runtime_for(data,root)
        runtime_path=save('synthetic-final-runtime',runtime)
        with authority.launch_derivations():
            prepared=preparation.prepare_synthetic(data['selection'].registration.pin.path,runtime_path,
                job_id='SYNTHETIC-NOT-AUTHORITY',run_date='2026-11-12',max_draft_checks=3)
            raw=c.canonical(prepared); save('synthetic-preparation',raw)
            verified=preparation.verify_preparer(raw,job_id='SYNTHETIC-NOT-AUTHORITY')
            instruction=root/'instruction.md'; instruction.write_bytes(verified['instruction'].encode())
            composed=composition.compose(raw,instruction_path=instruction)
            comp=save('synthetic-composition',composed)
            selected,run,capture=composition.reconstruct_composition(comp.read_bytes())
            system=root/'system.md'; system.write_text(LABEL+'\n')
            attempt=root/'NEVER-RESERVED-ATTEMPT'; evidence=root/'NEVER-RESERVED-EVIDENCE'
            expected=registration.permission_expectation(runtime,selected,run,
                system.read_bytes().decode()+command_guidance(selected['policy']),attempt/'cli_config',authority.dependency_identity())
            save('synthetic-expectation',expected)
            probe=bound_permission_for(expected,capture.document(),run.bundle.read_bytes())
            save('synthetic-permission-location',{'path':str(probe),'sha256':c.sha(probe.read_bytes()),'scope':LABEL})
            envelope=registration.synthetic_registration(comp,system,permission_probe_path=probe,
                attempt_id=attempt.name,attempt_directory=attempt,evidence_directory=evidence,max_draft_checks=3)
            reg=save('synthetic-registration',envelope)
            value=registration.verified(reg.read_bytes())
            contract=adapter.source_contract(); save('source-contract',contract)
            stamp=datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
            bundle,word=bundle_for(reg.read_bytes(),root/'synthetic-capture',now=stamp)
            bundle=c.strict_json(bundle); word=c.strict_json(word)
            bundle.update(kind=contract['bundle_kind'],version=contract['bundle_version'])
            bundle['owner_statement'].update(kind=contract['terms_kind'],version=contract['terms_version'])
            if contract['sequence_source'] is not None:
                bundle['sequence_script_sha256']=value['dependencies']['base']['package_sources'][contract['sequence_source']]
                bundle['owner_statement']['account_quiet']=True
            source=value['dependencies']['base']['source_commit']; event='workflow_dispatch'
            binding={key:bundle[key] for key in ('registration_sha256','attempt_id','source_commit','dependencies_sha256')}
            ci={**binding,'kind':'d4d_native_execution_ci_v2','version':2,'workflow_event':event,
                'workflow_ref':'refs/heads/SYNTHETIC-NOT-ACTUAL-CI','tested_commit':source,
                'workflow_sha256':preparation._workflow_sha(source,source,event),
                'checks':{name:{'head_sha':source,'status':'completed','conclusion':'success',
                    'details_url':preparation._ci_repository_url()+'/actions/runs/1'}
                    for name in preparation.required_checks(event)}}
            ci_path=save('SYNTHETIC-NOT-ACTUAL-CI',ci)
            bundle_raw=c.canonical(bundle); word['review_sha256']=c.sha(bundle_raw); word['ci_sha256']=c.sha(ci_path.read_bytes())
            review_path=save('synthetic-review',bundle_raw); word_path=save('synthetic-word',word)
            adapter.validate_supplied(reg.read_bytes(),review_path.read_bytes(),word_path.read_bytes())
            results['review_current_validated']=True
            results['status']='registration_and_current_review_validated_no_reservation'
            assert not attempt.exists() and not evidence.exists()
            assert not (root/'synthetic-capture').exists()
            (root/'chain-progress.json').write_bytes(c.canonical(results))
            return dict(data=data,root=root,runtime=runtime,reg=reg,value=value,review=review_path,word=word_path,ci=ci_path,results=results)
    except Exception as exc:
        results.update(status='refused',exception=type(exc).__name__,refusal=str(exc))
        (root/'chain-progress.json').write_bytes(c.canonical(results))
        raise


def test_full_chain_canary(tmp_path):
    case=build_chain(tmp_path/'SYNTHETIC-chain')
    assert case['results']['review_current_validated'] is True


import pytest


@pytest.fixture(scope='module')
def complete_chain(tmp_path_factory):
    # One real reconstruction shared by this cohort; no approved flags cached.
    with authority.launch_derivations():
        yield build_chain(tmp_path_factory.mktemp('full-chain-cohort')/'SYNTHETIC-chain')


def test_source_versions_and_terms(complete_chain):
    case=complete_chain
    contract=adapter.source_contract()
    bundle=c.strict_json(case['review'].read_bytes())
    assert bundle['kind']==contract['bundle_kind']
    assert bundle['version']==contract['bundle_version']
    terms=bundle['owner_statement']
    assert terms['version']==contract['terms_version']
    assert terms['account_quiet'] is True
    assert all(terms[k]==v for k,v in contract['admission_terms'].items())
    assert bundle['sequence_script_sha256']==c.sha((ROOT/contract['sequence_source']).read_bytes())


def test_complete_review_ci_word_admission_without_reservation(complete_chain):
    from data_sheets_schema import native_shared_execution_orchestration as execution
    case=complete_chain
    joined=execution.authorizations(case['reg'].read_bytes(),case['value'],
        review_path=case['review'],ci_path=case['ci'],launch_word_path=case['word'])
    assert joined
    from data_sheets_schema.native_shared_controls_orchestration import loaded_controls
    with loaded_controls(case['value']['dependencies']) as controls:
        admitted=preparation.admit(case['reg'].read_bytes(),review_path=case['review'],
            ci_path=case['ci'],launch_word_path=case['word'],classifier_projection=controls)
    assert all(not path.exists() for path in admitted.reservations)
    (case['root']/'admission-join.json').write_bytes(c.canonical({'scope':LABEL,'review_ci_word_join_validated':True,
        'fresh_admit_validated':True,'future_reservations':[str(path) for path in admitted.reservations],
        'reservation_performed':False}))


@pytest.mark.parametrize('command',['capture-subscription-event','prepare-subscription-guard-v2','launch'])
def test_public_commands_refuse_synthetic_before_any_reservation(complete_chain,command):
    from data_sheets_schema import native_generation as cli
    from data_sheets_schema import native_subscription_guard as wire
    case=complete_chain; root=case['root']; raw=case['reg'].read_bytes()
    choice={'kind':cli.CHOICE_KIND,'version':cli.CHOICE_VERSION,'decisions':['D105','D106'],
        'account_label':cli.ACCOUNT_LABEL,'effort':'high','receipt_instrument':4,
        'subject_sha256':wire.sha(raw),'runtime_sha256':wire.sha(wire.canonical(case['runtime']))}
    choice_path=root/'synthetic-account-choice.json'
    choice_path.write_bytes(c.canonical(choice))
    args=[command,'--registration',str(case['reg']),'--review',str(case['review']),
          '--launch-word',str(case['word']),'--account-choice',str(choice_path)]
    if command=='capture-subscription-event': args+=['--output-directory',str(root/'synthetic-capture')]
    elif command=='prepare-subscription-guard-v2': args+=['--capture',str(root/'NO-CAPTURE.json'),'--output',str(root/'NO-GUARD.json')]
    else: args+=['--ci',str(case['ci']),'--subscription-guard',str(root/'NO-GUARD.json'),'--subscription-guard-sha256','0'*64]
    with pytest.raises(ValueError) as refused: cli.main(args)
    assert any(term in str(refused.value).lower() for term in ('synthetic','first-party','max subscription','firstparty'))
    for target in ('synthetic-capture','NEVER-RESERVED-ATTEMPT','NEVER-RESERVED-EVIDENCE','NO-GUARD.json'):
        assert not (root/target).exists()
    (root/(command+'-refusal.json')).write_bytes(c.canonical({'scope':LABEL,'command':args,'refusal':str(refused.value),'no_gate_stubbed':True,'reservation_performed':False}))


def test_guard_pure_builder_and_latest_capture_refusal(complete_chain):
    from data_sheets_schema import native_subscription_guard_v2 as guard
    from data_sheets_schema import native_subscription_capture as capture
    case=complete_chain; root=case['root']
    terms=c.strict_json(case['review'].read_bytes())['owner_statement']
    now=datetime.now(timezone.utc); stamp=now.isoformat().replace('+00:00','Z')
    event={'type':'rate_limit_event','rate_limit_info':{'status':'allowed','isUsingOverage':False,
        'unifiedWindows':{name:{'status':'allowed','utilization':0.1,'resetsAt':int(now.timestamp())+3600}
                          for name in ('seven_day','five_hour')}}}
    raw=guard.prepare_guard(registration_raw=case['reg'].read_bytes(),runtime=case['runtime'],
        launch_word_raw=case['word'].read_bytes(),event_raw=c.canonical(event),captured_at=stamp,
        maximum_starting_utilization=terms['max_starting_weekly_utilization'],max_age_seconds=terms['max_age_seconds'],
        owner_statement=terms,capture_index=1,capture_claim_count=1)
    (root/'synthetic-unclaimed-guard.json').write_bytes(raw)
    with pytest.raises((ValueError,FileNotFoundError)) as refused:
        with capture.current_guard_preparation(root/'synthetic-capture'/'captures'/c.sha(case['word'].read_bytes())/'capture-1'/'capture.json',registration_raw=case['reg'].read_bytes(),
                review_bundle_raw=case['review'].read_bytes(),launch_word_raw=case['word'].read_bytes()):
            pytest.fail('nonexistent capture accepted')
    (root/'latest-capture-refusal.json').write_bytes(c.canonical({'scope':LABEL,'refusal':str(refused.value),'guard_scope':'pure synthetic guard only; no actual claim or current capture','reservation_performed':False}))
    assert not (root/'synthetic-capture').exists()


def test_timestamp_equality_and_mismatch_refusal(complete_chain):
    from datetime import timedelta
    case=complete_chain; raw=case['reg'].read_bytes()
    module_spec=importlib.util.spec_from_file_location('timestamp_procedure',ROOT/'scripts/native_registration_timestamp.py')
    module=importlib.util.module_from_spec(module_spec); module_spec.loader.exec_module(module)
    repo=case['root']/'synthetic-timestamp-proof'
    evidence=module.archive_synthetic(raw,repo)
    checked=module.verify(raw,evidence)
    start=datetime.fromisoformat(checked['valid_from'].replace('Z','+00:00'))
    different=(start+timedelta(seconds=1)).isoformat().replace('+00:00','Z')
    tree=module.git(repo,'rev-parse','HEAD^{tree}')
    wrong=module.git(repo,'commit-tree',tree,'-m','SYNTHETIC wrong author second; not authority',author_date=different)
    changed={**evidence,'commit':wrong}
    with pytest.raises(ValueError,match='registration commit author date') as refused:
        module.verify(raw,changed)
    (case['root']/'timestamp-results.json').write_bytes(c.canonical({'scope':LABEL,'success':checked,'evidence':evidence,
        'wrong_commit':wrong,'refusal':str(refused.value),'production_date_chosen':False}))
