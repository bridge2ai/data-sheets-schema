"""H3 production-prefix evidence, 2026-11-12. Real inputs, offline, no reservations.
Assignment all-project-prefix-and-cross-review; saves metrics and CLI readbacks.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import pytest
from tests.test_native_canary_packet_builder import command
from data_sheets_schema.registry import load_registry
from data_sheets_schema import chunking
ROOT=Path(__file__).resolve().parents[1]

def pin(path):
    raw=path.read_bytes()
    return {'path':str(path),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}

@pytest.mark.parametrize('project',['CM4AI','VOICE','AI_READI','VOICE_PEDIATRIC','CHORUS'])
def test_project_prefix(tmp_path,project):
    reg=load_registry(ROOT/'data/preprocessed/source_manifest.yaml')
    bundle=reg.bundle(project).resolve(); chunks=ROOT/'data/preprocessed/chunks'/f'{project}_chunks.yaml'
    context=ROOT/'data/omission_contexts'/f'{project.lower()}_omission_context.json'
    args=command(tmp_path/'packet')
    for key,value in {'project':project,'bundle':bundle,'chunk-manifest':chunks,'context':context,
                      'registration-id':'DRAFT-OFFLINE-'+project+'-NOT-AUTHORITY'}.items():
        args[args.index('--'+key)+1]=str(value)
    result=subprocess.run(args,cwd=ROOT,text=True,capture_output=True,timeout=240)
    (tmp_path/'builder-process.json').write_text(json.dumps({'command':args,'returncode':result.returncode,'stdout':result.stdout,'stderr':result.stderr},indent=2)+'\n')
    status=json.loads((tmp_path/'packet/status.json').read_bytes())
    raw=bundle.read_bytes(); mapping=chunking.load_manifest(chunks)
    rows=mapping['chunks']; longest=max(rows,key=lambda r:r['bytes'])
    lines=lambda r:r['lines'][1]-r['lines'][0]+1
    checks=[]
    for options in [['download','audit-bundles','--manifest',str(reg.path),'--project',project,'--strict'],
                    ['bundle','chunk','--manifest',str(reg.path),'--project',project,'--check','--strict']]:
        cmd=[sys.executable,'-P','-B','-m','data_sheets_schema.cli',*options]
        got=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True,timeout=240)
        checks.append({'command':cmd,'returncode':got.returncode,'stdout':got.stdout,'stderr':got.stderr})
    evidence={'project':project,'source_commit':subprocess.check_output(['/usr/bin/git','-C',str(ROOT),'rev-parse','HEAD']).decode().strip(),
        'builder':{'command':args,'returncode':result.returncode,'stdout':result.stdout,'stderr':result.stderr,'status':status},
        'bundle':pin(bundle),'bundle_lines':len(raw.decode().splitlines()),'source_documents':len({r['source'] for r in rows if r['source']!='<preamble>'}),
        'manifest_sources':len(reg.sources(project)),'chunk_count':len(rows),'largest_chunk_bytes':longest['bytes'],
        'largest_byte_chunk_lines':lines(longest),'largest_chunk_id':longest['id'],'maximum_chunk_lines':max(map(lines,rows)),
        'oversize_chunks':[r for r in rows if r.get('oversize')], 'chunk_manifest':pin(chunks),
        'omission_context':json.loads(context.read_bytes()),'omission_context_pin':pin(context),'scope':reg.data['scope'][project],
        'source_dir':str(reg.source_dir(project)) if reg.source_dir(project) else None,'profile':reg.data.get('profile'),
        'checks':checks,'outputs':[pin(p) for p in sorted((tmp_path/'packet').iterdir()) if p.is_file()]}
    (tmp_path/'project-evidence.json').write_text(json.dumps(evidence,indent=2)+'\n')
    assert result.returncode in (1,2),result.stdout+result.stderr
    assert not (tmp_path/'never-reserved-attempt').exists()
    if result.returncode==2:
        from data_sheets_schema.native_shared_selection import capture
        assert capture(tmp_path/'packet/selection.json').project==project
        assert status['status']=='dependency_stop'
        assert all((tmp_path/'packet'/name).stat().st_size for name in status['completed'])
    else:
        assert status['status']=='production_refusal'
