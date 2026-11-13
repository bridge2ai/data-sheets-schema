#!/usr/bin/env python3
"""Combine committed D143 source with separately committed cache fixtures offline.
Inputs two local branches; output private export/manifest for final regression.
No source/protected mutation, publication or model invocation. 2026-11-13.
"""
from pathlib import Path
import hashlib,json,subprocess,tarfile
W=Path(__file__).resolve().parents[2];E=W.parent;C=E/'codex-native-helper-cache-home-20261112';S=E/'scratch-h2-run-limits-20261113';O=S/'composition';T=O/'tree'
def git(root,*args):return subprocess.check_output(['/usr/bin/git',*args],cwd=root).decode().strip()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
base=git(W,'rev-parse','HEAD');cache=git(C,'rev-parse','HEAD')
O.mkdir();T.mkdir();git(T,'init','-q')
(T/'.git/objects/info/alternates').write_text(git(W,'rev-parse','--path-format=absolute','--git-path','objects')+'\n')
git(T,'update-ref','HEAD',base)
git(T,'sparse-checkout','set','--cone','.claude','.github','src','tests','utils','scripts','notes','docs','project','config','configs','examples','linkml_mappings','data/rubric','data/preprocessed','data/_wcrate','data/ro-crate_packages','data/d4d_concatenated')
git(T,'read-tree','-mu','HEAD')
fixtures=['tests/test_native_u4b_runtime.py','tests/test_native_u4b_probe_sequence.py']
for p in fixtures:(T/p).write_bytes((C/p).read_bytes())
git(T,'add','--',*fixtures)
commit=git(T,'commit-tree',git(T,'write-tree'),'-p',base,'-m','Offline D143 plus separately committed cache fixture repairs')
git(T,'update-ref','HEAD',commit)
config=T/'.git/config';original=config.read_bytes();(O/'git-config-original').write_bytes(original)
git(T,'config','--local','d4d.ciRepositoryUrl','https://github.com/bridge2ai/data-sheets-schema.git')
with tarfile.open(S/'fairscape.tar') as stream:stream.extractall(T/'fairscape_models',filter='data')
protected=['src/data_sheets_schema/shared_generation.py','src/data_sheets_schema/api_runner.py','src/download/prompts/canonical_hashes.yaml','tests/utils/run_spec_boundary_contracts.json']
record={'status':'composed_not_tested','tree':str(T),'composition_commit':commit,'source_base':base,'cache_fixture_head':cache,
 'fixture_paths':fixtures,'fixture_sha256':{p:sha(T/p) for p in fixtures},'config_original_sha256':hashlib.sha256(original).hexdigest(),'config_configured_sha256':sha(config),
 'packets':[{'path':p,'postimage_sha256':sha(T/p)} for p in protected]}
for p in protected:assert (T/p).read_bytes()==(W/p).read_bytes()
(O/'composition.json').write_text(json.dumps(record,indent=2)+'\n');print(commit)
