#!/usr/bin/env python3
"""Compose committed issue 5966 branch with verified protected packets, offline.
Input: local HEAD and helper-1 g07-c postimages. Output: private scratch tree,
config backup and composition receipt; no branch protected edits. 2026-11-12.
"""
from pathlib import Path
import importlib.util,json,tarfile
W=Path(__file__).resolve().parents[2];E=W.parent;S=E/'scratch-h2-cache-gaps-20261113'
spec=importlib.util.spec_from_file_location('cache_packets',W/'scripts/adhoc/native_g07_packets_20261112.py')
h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
base=h.git('rev-parse','HEAD',cwd=W).decode().strip()
# Pending test changes are copied and pinned below; production comes from HEAD.
packet_base=E/'scratch-native-main-integration-20261112/g07-c'
raw=(packet_base/'packet-hashes.json').read_bytes();rows=json.loads(raw)['packets']
for row in rows:
 assert h.sha((packet_base/'packets'/(row['name']+'.postimage')).read_bytes())==row['postimage_sha256']
 assert h.sha(h.git('show',base+':'+row['path'],cwd=W))==row['main_sha256']
out=S/'composition';out.mkdir();tree=out/'tree';tree.mkdir()
h.git('init','-q','--object-format=sha1',cwd=tree)
objects=h.git('rev-parse','--path-format=absolute','--git-path','objects',cwd=W).decode().strip()
h.write(tree/'.git/objects/info/alternates',(objects+'\n').encode())
h.git('update-ref','--no-deref','HEAD',base,cwd=tree)
h.git('sparse-checkout','set','--cone',*h.SPARSE,cwd=tree);h.git('read-tree','-mu','HEAD',cwd=tree)
for row in rows:(tree/row['path']).write_bytes((packet_base/'packets'/(row['name']+'.postimage')).read_bytes())
h.git('add','--',*(row['path'] for row in rows),cwd=tree)
tree_sha=h.git('write-tree',cwd=tree).decode().strip()
commit=h.git('commit-tree',tree_sha,'-p',base,'-m','Offline issue 5966 four-packet proof composition',cwd=tree).decode().strip()
h.git('update-ref','--no-deref','HEAD',commit,cwd=tree)
config=tree/'.git/config';before=config.read_bytes();h.write(config.with_name('config.bak-h2-cache-20261112'),before)
h.git('config','--local','d4d.ciRepositoryUrl','https://github.com/bridge2ai/data-sheets-schema.git',cwd=tree)
link=h.git('ls-tree',base,'fairscape_models',cwd=W).decode().split();archive=out/'fairscape.tar'
h.git('archive','--format=tar','--output='+str(archive),link[2],cwd=E.parent/'data-sheets-schema/fairscape_models')
target=tree/'fairscape_models';target.mkdir(exist_ok=True)
with tarfile.open(archive) as stream:stream.extractall(target,filter='data')
record={'status':'composed_not_tested','candidate':'ba1f56e4a9460fe87c1e0ea3cb35ed2d7405cfa0','repair_commit':base,
 'composition_commit':commit,'composition_tree':tree_sha,'tree':str(tree),'packets':rows,
 'packet_manifest_sha256':h.sha(raw),'config_original_sha256':h.sha(before),'config_configured_sha256':h.sha(config.read_bytes()),'config_restore_pending':True}
print(out/'composition.json',h.save(out/'composition.json',record))
# Issue 6030 pending tests only; retain their exact source identities in the receipt.
paths=['tests/test_native_helper_cache.py','tests/native_helper_cache_assertions.py',
       'tests/test_native_shared_results.py','tests/test_native_shared_execution.py']
for path in paths:(tree/path).write_bytes((W/path).read_bytes())
record['pending_test_sha256']={path:h.sha((tree/path).read_bytes()) for path in paths}
h.save(out/'pending-tests.json',record)
