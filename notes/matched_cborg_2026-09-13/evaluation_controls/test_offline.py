"""Exact composite offline receipts; actual presence and mechanical instruments."""
from pathlib import Path
import pytest

from test_source_pair import composite,build
import registration as reg
import offline


def test_exact_pair_presence_and_mechanical_checks_do_not_touch_accounting(composite,monkeypatch):
    prepared=build(composite);path=prepared['registration'];m=reg.read_json(path)
    watched=[composite['state'],Path(composite['phase']['budget']['ledger_path']),path,
             *map(Path,m['pinned_files'])]
    before={str(p):p.read_bytes() for p in watched}
    import continuation_sequence
    monkeypatch.setattr(continuation_sequence,'owned_sequence',lambda *a,**k:pytest.fail('offline checks claimed accounting'))
    target=composite['destination']/'offline_results'
    result=offline.run_checks(path,target)
    assert result['checked'] and result['mechanical_passed']
    assert result['provider_calls']==result['token_count_calls']==0 and not result['accounting_ownership_claimed']
    assert result['input_files']==2 and result['presence_rubric_cells']==4
    assert result['scientific_acceptance'] is False
    for variant in ('full','core'):
        record=reg.read_json(target/(variant+'.json'))
        presence=record['presence']
        assert presence['instrument']['input_sha256']==m['source_pair']['artifacts'][variant]['sha256']
        assert presence['method']==m['method'] and presence['applicability_context']=={}
        assert presence['rubric10_max']==presence['rubric10_fixed_max']
        assert presence['rubric20_max']==presence['rubric20_fixed_max']
        assert presence['rubric10_scores'] and presence['rubric20_scores']
    assert before=={name:Path(name).read_bytes() for name in before}
    assert not Path(m['budget']['ledger_path']).exists() and not Path(m['attempts_dir']).exists()
    with pytest.raises(reg.BudgetStop,match='already exists'):offline.run_checks(path,target)


@pytest.mark.parametrize('damage',['artifact','context','output_overlap','paid_attempt'])
def test_offline_refuses_changed_input_and_unsafe_output(composite,damage):
    prepared=build(composite);path=prepared['registration'];m=reg.read_json(path)
    output=composite['destination']/'offline_results'
    if damage=='artifact':Path(m['source_pair']['artifacts']['full']['path']).write_text('changed\n')
    elif damage=='context':Path(m['context_path']).write_text('{"human_subjects":false}\n')
    elif damage=='output_overlap':output=Path(m['source_pair']['artifacts']['core']['path']).parent
    else:output=Path(m['attempts_dir'])/'offline'
    with pytest.raises((reg.BudgetStop,ValueError)):
        offline.run_checks(path,output)
    assert not (composite['destination']/'offline_results').exists()
