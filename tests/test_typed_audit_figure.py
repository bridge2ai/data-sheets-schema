"""Actual reconstructed engineering assemblies, never empirical recall labels."""
import copy
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from data_sheets_schema import audit_batches as b, typed_audit as ta, typed_audit_report as base
from data_sheets_schema import typed_audit_figure as figure
from tests.test_typed_audit import supplied, packet, replies, seal

ROOT = Path(__file__).resolve().parents[1]


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def assembly(packet, name):
    count = {'zero':0,'merged':2,'dropped':1,'mixed':3,'role':0}[name]
    workers, omissions, delta, quote = replies(packet,count)
    if name == 'dropped':
        delta['new_findings']=[]
        delta['omission_dispositions'][0].update(action='drop',evidence=[quote])
    elif name == 'mixed':
        delta['new_findings'][0]['omission_candidates'].remove('candidate-2')
        delta['omission_dispositions'][2].update(action='drop',evidence=[quote])
        delta['new_findings'].append({'severity':'low','record':'full','slot':'name',
           'issue':'An omitted claim is missing; prose must not imply a kind.', 'evidence':[quote]})
    elif name == 'role':
        delta['new_findings']=[{'severity':'medium','record':'full','slot':'name','kind':'role_placement',
            'issue':'Missing omitted descriptions; kind remains role_placement.', 'evidence':[quote]}]
    return b.canonical_bytes(seal(packet,workers,omissions,delta))


@pytest.fixture
def selected(tmp_path,packet):
    rows=[]
    for name in ('zero','merged','dropped','mixed','role'):
        path=tmp_path/f'{name}.json';path.write_bytes(assembly(packet,name));rows.append(str(path))
    return rows


def table(path):
    return list(csv.DictReader(path.open()))


def test_one_actual_build_report_and_exact_old_exports_drive_every_artifact(selected,tmp_path,monkeypatch):
    pairs=[(path,Path(path).read_bytes()) for path in selected]
    expected=base.build_report(pairs)
    expected_json=b.canonical_bytes(expected);expected_csv=base.csv_bytes(expected)
    original=base.build_report;calls=[]
    def once(values):
        values=list(values);calls.append(values);return original(values)
    monkeypatch.setattr(base,'build_report',once)
    prepared=figure.prepare(selected)
    assert calls==[pairs]
    assert prepared.checked_payload==expected_json
    # Neither reconstruction nor source/schema reads may be used to derive
    # plot values after preparation. Capture.verify remains an integrity read.
    monkeypatch.setattr(base,'build_report',lambda _:pytest.fail('rebuilt report during rendering'))
    monkeypatch.setattr(ta,'check',lambda _:pytest.fail('rechecked live inputs during rendering'))
    out=tmp_path/'figure';manifest=figure.publish(prepared,out)
    assert (out/'checked_audits.json').read_bytes()==expected_json
    assert (out/'checked_audits.csv').read_bytes()==expected_csv
    assert manifest['checked_base_report']['sha256']==sha(expected_json)
    assert manifest['state']=='complete'
    for name,pin in manifest['artifacts'].items():
        assert sha((out/name).read_bytes())==pin['sha256']
        assert (out/name).stat().st_size==pin['bytes']
    assert json.loads((out/'manifest.json').read_bytes())==manifest
    findings=table(out/'finding_counts.csv');candidates=table(out/'candidate_counts.csv')
    assert len(findings)==5*len(figure.KINDS) and len(candidates)==5
    assert [sum(int(r['count']) for r in findings if int(r['selection_index'])==i) for i in range(5)]==[0,1,0,2,1]
    assert [int(r['candidates']) for r in candidates]==[0,2,1,3,0]
    assert [int(r['retained_candidates']) for r in candidates]==[0,2,0,2,0]
    assert [int(r['dropped_candidates']) for r in candidates]==[0,0,1,1,0]
    assert sum(int(r['count']) for r in findings if r['kind']=='omission')==2
    assert sum(int(r['count']) for r in findings if r['kind']=='untyped')==1
    assert sum(int(r['count']) for r in findings if r['kind']=='role_placement')==1
    assert {r['count_unit'] for r in findings}=={'final_findings'}
    assert {r['count_unit'] for r in candidates}=={'omission_candidates'}
    assert [r['source']['path'] for r in manifest['assemblies']]==selected
    assert [r['lineage'] for r in json.loads(expected_json)['assemblies']]==[r['lineage'] for r in prepared.report()['assemblies']]
    svg=(out/'fig07_typed_audits.svg').read_text()
    assert '<svg' in svg and 'Final finding count' in svg and 'Omission candidate count' in svg
    assert 'untyped' in svg and 'remain unverified' in svg
    assert all(row['identity']['assembly_sha256'][:12] in svg for row in expected['assemblies'])
    assert [(p,Path(p).read_bytes()) for p in selected]==pairs


def test_literal_order_and_raw_canonical_identity_are_not_filename_inference(selected,tmp_path,monkeypatch):
    monkeypatch.chdir(tmp_path)
    raw=Path(selected[1]).read_bytes();parsed=json.loads(raw)
    path=tmp_path/'arbitrary-nonproject-v99.json';path.write_text(json.dumps(parsed,indent=4))
    spellings=['./role.json','arbitrary-nonproject-v99.json','zero.json']
    prepared=figure.prepare(spellings)
    result=prepared.report()
    assert [r['source']['path'] for r in result['assemblies']]==spellings
    assert [r['selection_index'] for r in result['assemblies']]==[0,1,2]
    assert result['assemblies'][1]['source']['sha256']==sha(path.read_bytes())
    assert result['assemblies'][1]['identity']['assembly_sha256']==parsed['sha256']
    assert prepared.selected[0].spelling=='./role.json'
    assert not ({'cohort','project','model','aggregate'} & result.keys())


@pytest.mark.parametrize('mode',['same','whitespace','hardlink'])
def test_canonical_duplicates_are_refused(selected,tmp_path,mode):
    first=Path(selected[1]);second=tmp_path/'second.json'
    if mode=='hardlink':os.link(first,second)
    else:second.write_bytes(first.read_bytes() if mode=='same' else json.dumps(json.loads(first.read_bytes()),indent=1).encode())
    with pytest.raises(ValueError,match='duplicate canonical'):
        figure.prepare([str(first),str(second)])


@pytest.mark.parametrize('kind',sorted(ta.audit_protocol.KINDS-{'omission'}))
def test_every_other_declared_kind_ignores_misleading_prose(tmp_path,packet,kind):
    workers,omissions,delta,quote=replies(packet,0)
    delta['new_findings']=[{'severity':'low','record':'full','slot':'name','kind':kind,
        'issue':'Omission missing omission missing.','evidence':[quote]}]
    path=tmp_path/'assembly.json';path.write_bytes(b.canonical_bytes(seal(packet,workers,omissions,delta)))
    prepared=figure.prepare([path]);findings,_=figure._counts(prepared.report())
    assert {r['kind']:r['count'] for r in findings if r['count']}=={kind:1}


@pytest.mark.parametrize('mutation',['passed','counts','lineage','missing_chunk','source','context'])
def test_edited_success_and_incomplete_or_mismatched_evidence_refuse(tmp_path,packet,mutation):
    value=json.loads(assembly(packet,'merged'))
    if mutation=='passed':value['acceptance']['passed']=False
    elif mutation=='counts':value['acceptance']['finding_counts']['omission']=200
    elif mutation=='lineage':value['lineage']['omission_candidates'][0]['final_finding_ordinal']=99
    elif mutation=='context':
        context=json.loads(ta._unblob(value['packet']['inputs']['context']))
        context['scopes'][0]['release']='99'
        value['packet']['inputs']['context']=ta._blob(b.canonical_bytes(context))
    else:
        omissions=json.loads(ta._unblob(value['omission_response']))
        if mutation=='missing_chunk':omissions['chunks'].pop(0)
        else:omissions['chunks'][1]['candidates'][0]['source']='other.txt'
        value['omission_response']=ta._blob(b.canonical_bytes(omissions))
    value=ta._seal({k:v for k,v in value.items() if k!='sha256'})
    path=tmp_path/'bad.json';path.write_bytes(b.canonical_bytes(value))
    with pytest.raises(ValueError):figure.prepare([path])
    assert not (tmp_path/'figure').exists()


@pytest.mark.parametrize('raw',[b'{"passed":true}',b'{"format":"checked_typed_audit_report_v1","assemblies":[]}',
                                b'{"findings":[],"summary":"bare audit"}',b'{"a":1,"a":2}',b'{"x":NaN}'])
def test_saved_reports_and_bare_or_ambiguous_audits_are_not_authority(tmp_path,raw):
    path=tmp_path/'not-assembly.json';path.write_bytes(raw)
    with pytest.raises(ValueError):figure.prepare([path])


def test_edited_or_absent_live_schema_is_never_reopened(selected,supplied,tmp_path):
    before=[Path(p).read_bytes() for p in selected]
    supplied['schema_path'].write_text('Not the captured schema')
    supplied['schema_path'].with_name('child.yaml').unlink()
    prepared=figure.prepare([selected[0]])
    assert prepared.report()['assemblies'][0]['acceptance']['passed']
    assert [Path(p).read_bytes() for p in selected]==before


def test_absent_named_schema_and_its_ancestor_are_protected(selected,supplied):
    source=supplied['schema_path'];source.unlink()
    prepared=figure.prepare([selected[0]])
    with pytest.raises(ValueError,match='authority'):figure.publish(prepared,source)
    assert not source.exists()


@pytest.mark.parametrize('alias',['selected','hardlink','symlink','dangling','directory'])
def test_existing_destinations_and_aliases_never_change(selected,tmp_path,alias):
    prepared=figure.prepare([selected[0]]);source=Path(selected[0]);before=source.read_bytes();out=tmp_path/'out'
    if alias=='selected':out=source
    elif alias=='hardlink':os.link(source,out)
    elif alias=='symlink':out.symlink_to(source)
    elif alias=='dangling':out.symlink_to(tmp_path/'absent')
    else:out.mkdir();(out/'keep').write_bytes(b'keep')
    with pytest.raises(ValueError,match='new'):figure.publish(prepared,out)
    assert source.read_bytes()==before
    if alias=='directory':assert (out/'keep').read_bytes()==b'keep'


@pytest.mark.parametrize('replacement',['append','same_bytes_new_inode'])
def test_post_capture_file_drift_refuses_before_reservation(selected,tmp_path,replacement):
    prepared=figure.prepare([selected[0]]);path=Path(selected[0]);raw=path.read_bytes()
    if replacement=='append':path.write_bytes(raw+b'\n')
    else:
        other=tmp_path/'replacement';other.write_bytes(raw);other.replace(path)
    with pytest.raises(ValueError):figure.publish(prepared,tmp_path/'figure')
    assert not (tmp_path/'figure').exists()


def test_render_uses_captured_values_then_refuses_input_drift(selected,tmp_path,monkeypatch):
    prepared=figure.prepare([selected[0]]);path=Path(selected[0])
    def drift(report):
        assert report['assemblies'][0]['counts']['findings']==0
        path.write_bytes(path.read_bytes()+b'\n')
        return b'<svg/>'
    monkeypatch.setattr(figure,'_svg',drift)
    with pytest.raises(ValueError):figure.publish(prepared,tmp_path/'figure')
    assert not (tmp_path/'figure').exists()


@pytest.mark.parametrize('failure',['interrupted','corrupted','directory_race'])
def test_failed_publication_has_no_complete_manifest_and_preserves_winner(selected,tmp_path,monkeypatch,failure):
    prepared=figure.prepare([selected[0]]);out=tmp_path/'out'
    monkeypatch.setattr(figure,'_svg',lambda _:b'<svg/>')
    original=figure._publish_file
    def bad(fd,name,raw):
        if failure=='interrupted' and name=='checked_audits.csv':raise OSError('injected write failure')
        original(fd,name,raw)
        if failure=='corrupted' and name=='checked_audits.csv':(out/'checked_audits.json').write_bytes(b'corrupted')
    if failure=='directory_race':
        def occupy(_):out.mkdir();(out/'keep').write_bytes(b'keep');return b'<svg/>'
        monkeypatch.setattr(figure,'_svg',occupy)
    else:monkeypatch.setattr(figure,'_publish_file',bad)
    with pytest.raises((ValueError,OSError)):figure.publish(prepared,out)
    assert out.is_dir() and not (out/'manifest.json').exists()
    if failure=='directory_race':assert (out/'keep').read_bytes()==b'keep'
    with pytest.raises(ValueError,match='new'):figure.publish(prepared,out)


def test_actual_cli_outputs_use_the_same_checked_payload(selected,tmp_path):
    out=tmp_path/'figure'
    command=[sys.executable,str(ROOT/'scripts/figures/fig07_typed_audits.py'),
             '--assembly',selected[2],'--assembly',selected[3],'--output-dir',str(out)]
    first=subprocess.run(command,capture_output=True,text=True)
    assert first.returncode==0,first.stderr
    assert json.loads(first.stdout)['assembly_count']==2
    manifest=json.loads((out/'manifest.json').read_bytes());assert manifest['state']=='complete'
    report=json.loads((out/'checked_audits.json').read_bytes())
    assert [r['counts']['findings'] for r in report['assemblies']]==[0,2]
    hashes={p.name:sha(p.read_bytes()) for p in out.iterdir()}
    second=subprocess.run(command,capture_output=True,text=True)
    assert second.returncode==2 and 'must be new' in second.stderr
    assert hashes=={p.name:sha(p.read_bytes()) for p in out.iterdir()}


@pytest.mark.parametrize('mode',['empty','scalar','mapping','limit_count','limit_bytes','per_file'])
def test_existing_bounds_and_explicit_selection_are_preserved(selected,monkeypatch,mode):
    values=selected
    if mode=='empty':values=[]
    elif mode=='scalar':values=selected[0]
    elif mode=='mapping':values={'passed':True}
    elif mode=='limit_count':monkeypatch.setattr(base,'MAX_ASSEMBLIES',1)
    elif mode=='limit_bytes':monkeypatch.setattr(base,'MAX_SELECTED_BYTES',1)
    else:monkeypatch.setattr(ta,'MAX_ASSEMBLY_BYTES',1)
    with pytest.raises(ValueError):figure.prepare(values)


def test_fifo_is_refused_without_waiting(tmp_path):
    if not hasattr(os,'mkfifo'):pytest.skip('POSIX named pipe check')
    path=tmp_path/'fifo';os.mkfifo(path)
    with pytest.raises(ValueError,match='regular file'):figure.prepare([path])


def test_absent_captured_schema_directory_is_not_a_fresh_output(tmp_path):
    authority=tmp_path/'historical-schema';authority.mkdir()
    packet=ta.prepare(**supplied.__wrapped__(authority))
    path=tmp_path/'assembly.json';path.write_bytes(assembly(packet,'zero'))
    retained=tmp_path/'retained-schema'
    authority.rename(retained)
    prepared=figure.prepare([path])
    with pytest.raises(ValueError,match='authority'):
        figure.publish(prepared,authority)
    assert not authority.exists()
    assert (retained/'schema.yaml').is_file() and (retained/'child.yaml').is_file()


def test_independent_parsed_report_copy_cannot_edit_prepared_payload(selected):
    prepared=figure.prepare([selected[1]])
    before=prepared.checked_payload
    editable=prepared.report();editable['assemblies'][0]['counts']['findings']=999
    assert prepared.checked_payload==before
    assert prepared.report()['assemblies'][0]['counts']['findings']==1
