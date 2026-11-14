#!/usr/bin/env python3
"""H3 2026-11-12: data-only scope/Kids First evidence; ignored files included.
Inputs assigned worktree data and composed manifest; output own scratch JSON.
"""
import hashlib,json,re,subprocess
from pathlib import Path
import yaml
W=Path(__file__).resolve().parents[2]; S=W.parent/'scratch-h3-packet-builder-20261112'; T=S/'composition-a/tree'
def pin(p): return {'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
manifest=T/'data/preprocessed/source_manifest.yaml'; doc=yaml.safe_load(manifest.read_bytes())
crate=T/'data/ro-crate_packages/crate_manifest.yaml'; crates=yaml.safe_load(crate.read_bytes())
found=[]
# Path.rglob walks hidden/gitignored data too; do not make claims outside this scope.
for p in (W/'data').rglob('*'):
    if p.is_file() and re.search(r'kids.?first',str(p),re.I): found.append(pin(p))
tracked=subprocess.check_output(['/usr/bin/git','-C',str(W),'ls-tree','-r','--name-only','HEAD','data']).decode().splitlines()
value={'manifest':pin(manifest),'projects':[k for k,v in doc['projects'].items() if isinstance(v,(list,dict))],
 'scope':doc['scope'],'crate_manifest':pin(crate),'crate_policies':{k:{f:v.get(f) for f in ('document_corpus','document_corpus_reason')} for k,v in crates['projects'].items()},
 'kids_first':{'search_scope':str(W/'data'),'ignored_and_hidden_included':True,'matching_files':found,
 'tracked_matches':[p for p in tracked if re.search(r'kids.?first',p,re.I)],
 'manifest_mentions':[{'line':i,'text':line} for i,line in enumerate(manifest.read_text().splitlines(),1) if re.search(r'kids.?first',line,re.I)],
 'conclusion':'The selected manifest has no Kids First project/source list or scope declaration. Data contains evaluation and omission contexts, but no declared registration bundle/chunk pair or individual source collection. A registration needs a manifest project with curated source list, declared bundle/chunk mapping, scope/referent and profile agreement; existing omission context alone is insufficient. The context references historical notes outside this data-only inventory; those are not asserted absent or adopted.'}}
(S/'project-input-inventory.json').write_text(json.dumps(value,indent=2)+'\n')
print(S/'project-input-inventory.json')
