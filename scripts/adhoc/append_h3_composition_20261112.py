#!/usr/bin/env python3
"""Append own committed changes to authorized scratch composition, 2026-11-12.
Inputs explicit own commit; output updated clean private HEAD and receipt history.
Never edits protected files or shared Git refs/config. Refuses patch conflicts.
"""
import argparse
import importlib.util
import json
from pathlib import Path
E=Path('/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions')
W=E/'codex-native-packet-builder-20261112'
spec=importlib.util.spec_from_file_location('packets',E/'codex-native-main-integration-20261112/scripts/adhoc/native_g07_packets_20261112.py')
h=importlib.util.module_from_spec(spec); spec.loader.exec_module(h)
p=argparse.ArgumentParser(); p.add_argument('commit'); a=p.parse_args()
out=E/'scratch-h3-packet-builder-20261112/composition-a'; tree=out/'tree'
record=json.loads((out/'composition.json').read_bytes())
assert h.git('rev-parse','HEAD',cwd=tree).decode().strip()==record['composition_commit']
assert not h.git('status','--porcelain',cwd=tree).strip()
commit=h.git('rev-parse',a.commit,cwd=W).decode().strip()
patch=h.git('diff','--binary',commit+'^',commit,cwd=W)
changed=h.git('diff','--name-only',commit+'^',commit,cwd=W).decode().splitlines()
assert not set(changed)&{row['path'] for row in record['packets']}
path=out/(commit+'.patch'); h.write(path,patch)
h.git('apply','--index','--check',str(path),cwd=tree)
h.git('apply','--index',str(path),cwd=tree)
new_tree=h.git('write-tree',cwd=tree).decode().strip()
parent=h.git('commit-tree',new_tree,'-p',record['composition_commit'],'-m','Offline own-helper increment '+commit,cwd=tree).decode().strip()
h.git('update-ref','--no-deref','HEAD',parent,cwd=tree)
record['applied'].append({'commit':commit,'patch_sha256':h.sha(patch),'private_commit':parent})
h.write(out/('composition-before-'+commit+'.json'),(out/'composition.json').read_bytes())
record.update(composition_commit=parent,composition_tree=new_tree)
(out/'composition.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({'commit':commit,'composition_commit':parent,'patch_sha256':h.sha(patch)}))
