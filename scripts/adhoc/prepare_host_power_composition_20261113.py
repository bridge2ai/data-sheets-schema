#!/usr/bin/env python3
"""Compose committed issue 5966 branch with verified protected packets, offline.
Input: local HEAD and helper-1 g07-c postimages. Output: private scratch tree,
config backup and composition receipt; no branch protected edits. 2026-11-12.
"""
from pathlib import Path
import importlib.util,json,tarfile
W=Path(__file__).resolve().parents[2];E=W.parent;S=E/'scratch-h2-host-power-20261113'
spec=importlib.util.spec_from_file_location('cache_packets',W/'scripts/adhoc/native_g07_packets_20261112.py')
h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
base=h.git('rev-parse','HEAD',cwd=W).decode().strip()
# Exact pending source paths below are copied and pinned in the private commit.
packet_base=E/'scratch-native-main-integration-20261112/g07-c'
raw=(packet_base/'packet-hashes.json').read_bytes();rows=json.loads(raw)['packets']
for row in rows:
 assert h.sha((packet_base/'packets'/(row['name']+'.postimage')).read_bytes())==row['postimage_sha256']
 assert h.sha(h.git('show',base+':'+row['path'],cwd=W))==row['postimage_sha256']
out=S/'composition';out.mkdir();tree=out/'tree';tree.mkdir()
h.git('init','-q','--object-format=sha1',cwd=tree)
objects=h.git('rev-parse','--path-format=absolute','--git-path','objects',cwd=W).decode().strip()
h.write(tree/'.git/objects/info/alternates',(objects+'\n').encode())
h.git('update-ref','--no-deref','HEAD',base,cwd=tree)
h.git('sparse-checkout','set','--cone',*h.SPARSE,cwd=tree);h.git('read-tree','-mu','HEAD',cwd=tree)
# Protected postimages already exist unchanged in the published candidate.
pending = ['src/data_sheets_schema/native_host_power.py',
 'src/data_sheets_schema/native_launch_sequence.py', 'src/data_sheets_schema/native_execution_orchestration.py',
 'src/data_sheets_schema/native_shared_capture_orchestration.py', 'tests/test_native_host_power.py',
 'tests/test_native_launch_sequence.py', 'tests/test_native_shared_live_capture.py',
 'tests/fixtures/native_host_power/pmset-sleep-20261112.txt', 'docs/native-host-power.md']
for path in pending:
 target=tree/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((W/path).read_bytes())
h.git('add','--',*(row['path'] for row in rows),*pending,cwd=tree)
tree_sha=h.git('write-tree',cwd=tree).decode().strip()
commit=h.git('commit-tree',tree_sha,'-p',base,'-m','Offline issue 6046 four-packet host-power composition',cwd=tree).decode().strip()
h.git('update-ref','--no-deref','HEAD',commit,cwd=tree)
config=tree/'.git/config';before=config.read_bytes();h.write(config.with_name('config.bak-h2-cache-20261112'),before)
h.git('config','--local','d4d.ciRepositoryUrl','https://github.com/bridge2ai/data-sheets-schema.git',cwd=tree)
link=h.git('ls-tree',base,'fairscape_models',cwd=W).decode().split();archive=out/'fairscape.tar'
h.git('archive','--format=tar','--output='+str(archive),link[2],cwd=E.parent/'data-sheets-schema/fairscape_models')
target=tree/'fairscape_models';target.mkdir(exist_ok=True)
with tarfile.open(archive) as stream:stream.extractall(target,filter='data')
record={'status':'composed_not_tested','candidate':'8760de5efe88b5af62e9d77e6335fa7e248017b6','repair_commit':base,'pending_source_sha256':{p:h.sha((W/p).read_bytes()) for p in pending},
 'composition_commit':commit,'composition_tree':tree_sha,'tree':str(tree),'packets':rows,
 'packet_manifest_sha256':h.sha(raw),'config_original_sha256':h.sha(before),'config_configured_sha256':h.sha(config.read_bytes()),'config_restore_pending':True}
print(out/'composition.json',h.save(out/'composition.json',record))
