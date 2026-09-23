"""Real offline Phase4 preparation inherits a synthetic accepted allocation."""
from pathlib import Path
import sys

import budget_amendment as amendment
import continuation_sequence as sequence
import test_continuation_sequence as foundation
from . import prepare


def test_phase4_preparer_carries_authority_without_claiming_or_rewriting(tmp_path,monkeypatch):
    prior,_,state=foundation.fixture(tmp_path/'source',amended=True)
    predecessor=prior['budget_sequence']['audit_origin']
    audit_path=Path(predecessor['registration']['path'])
    audit=sequence.read(audit_path)
    audit.update(protocol_version=3,render_version=14,model={'model':'synthetic'},profile='neutral',
        provider_base_url='https://example.invalid',provider_context_policy='synthetic',
        native_runtime={'executable':sys.executable},inputs={})
    audit['job']['attempt_dir']=str(audit_path.parent)
    audit['budget'].update(per_job_attempt_usd={'audit':'40'},
        prices_per_token={'input':'0.000005','output':'0.000025'})
    audit_ref=foundation.save(audit_path,audit)
    ledger_path=Path(predecessor['ledger']['path']);ledger=sequence.read(ledger_path)
    ledger['manifest_sha256']=audit_ref['sha256'];foundation.save(ledger_path,ledger)
    result_path=Path(predecessor['result']['path']);result=sequence.read(result_path)
    result['registration_sha256']=audit_ref['sha256'];result_ref=foundation.save(result_path,result)
    acceptance_path=Path(predecessor['acceptance']['path']);acceptance=sequence.read(acceptance_path)
    acceptance.update(registration_sha256=audit_ref['sha256'],result_sha256=result_ref['sha256'],
                      ledger_sha256=sequence.sha(ledger_path))
    foundation.save(acceptance_path,acceptance)
    owner=sequence.read(state);owner['registration_sha256']=audit_ref['sha256'];foundation.save(state,owner)
    frozen={p:p.read_bytes() for p in (audit_path,ledger_path,result_path,acceptance_path,state,
        *(Path(audit[amendment.KEY][k]['path']) for k in amendment.REFS))}
    # Scientific rendering/code attestation have separate suites. Keep the
    # actual preparer, proof loader, budget/acceptance/sequence checks and pins.
    monkeypatch.setattr(prepare,'render_instruction',lambda m:'Synthetic scientific instruction.\n')
    monkeypatch.setattr(prepare,'required_paths',lambda m:
        amendment.paths(m)|{Path(sequence.__file__).resolve(),*(Path(p) for p in m['inputs'].values())})
    monkeypatch.setattr(prepare,'validate_registration',lambda p:
        sequence._validate(sequence.read(p),Path(p),sequence.sha(p)))
    destination=tmp_path/'prepared-phase4'
    path=prepare.prepare(accepted_audit_registration=audit_path,acceptance=acceptance_path,
        destination=destination,job_id='phase4',repository=Path.cwd(),attempt_cap='20')
    manifest=sequence.read(path)
    assert manifest[amendment.KEY]==audit[amendment.KEY]
    assert manifest['budget']['additional_usd']=='500'
    assert manifest['budget']['per_job_attempt_usd']=={'phase4':'20'}
    assert manifest['budget_sequence']['origin']['registration']==audit[amendment.KEY]['origin_registration']
    assert all(manifest['pinned_files'][audit[amendment.KEY][k]['path']]==audit[amendment.KEY][k]['sha256']
               for k in amendment.REFS)
    assert all(p.read_bytes()==raw for p,raw in frozen.items())
    assert not Path(manifest['budget']['ledger_path']).exists()
    assert not Path(manifest['job']['attempt_dir']).exists()
    assert sequence.read(destination/'preparation.json')['provider_calls']==0
