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
