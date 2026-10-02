import json,sys,re,hashlib
from pathlib import Path
import yaml
O=Path('/Users/obanks/Documents/Codex/2026-09-29/r/outputs');ROOT=Path('/Users/obanks/data-sheets-schema');sys.path.insert(0,str(ROOT/'src'));from data_sheets_schema.receipt_sources import run_chunks
S=json.loads((O/'data/followup/sample_selection.json').read_text());audit=json.loads((O/'data/input_audit.json').read_text());links=json.loads((O/'data/source_links.json').read_text());runs={};records={}
for x in audit:
 f=Path(x['file']);m=re.match(r'(.+_v[78]_rep\d+)',f.name);r=m[1];p=Path(x['d4d_file']);assert hashlib.sha256(p.read_bytes()).hexdigest()==x['input_sha256'];records[r]=(p,yaml.safe_load(p.read_text()))
for s in S:
 rid=s['record'];path,data=records[rid]
 if rid not in runs:
  prov=path.parent.parent.parent/(path.parent.parent.name+'_core')/path.parent.name/f"{s['project']}_provenance.yaml";runs[rid]=run_chunks(prov)
 run=runs[rid];ev={'sample_id':s['sample_id'],'record':rid,'d4d_file':str(path),'d4d_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'d4d_fields':{f:data.get(f) for f in s['roots']},'receipt_links':[x for x in links if x['record']==rid and x['root'] in s['roots']],'source_recovery':run['basis']}
 (O/'data/followup'/f"{s['sample_id']}_evidence.json").write_text(json.dumps(ev,indent=2,default=str))
 # Store historical source texts for reproducible evidence review, in work only.
 dest=Path('work/followup')/rid;dest.mkdir(exist_ok=True)
 for cid,txt in run['texts'].items():(dest/f'{cid}.txt').write_text(txt)
 (dest/'manifest.json').write_text(json.dumps(run['manifest'],indent=2))
 print(s['sample_id'],s['record'],list(ev['d4d_fields']))
