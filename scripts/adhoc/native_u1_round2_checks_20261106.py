"""#4354 U1, 2026-11-06: serial offline acceptance commands and artifact checks.
Inputs: composed archive and M7 Git objects; outputs: round-two scratch evidence.
Each launch uses the same bounded, quiet-aware launcher as the single canary.
"""
from pathlib import Path
import json
import os
import shutil
import subprocess
import sys
from native_u1_round2_20261106 import ROOT, SCRATCH, COMPOSED, BASE, archive, quiet, sha

PYTHON=sys.executable
LAUNCH=ROOT/'scripts/adhoc/native_u1_round2_20261106.py'

def check(name,args,root=COMPOSED):
    quiet()
    code=subprocess.call([PYTHON,str(LAUNCH),'check',str(root),name,*args])
    path=SCRATCH/(name+'.log')
    assert path.is_file() and path.stat().st_size
    return code

def main():
    mode=sys.argv[1]
    pytest=[PYTHON,'-m','pytest']
    if mode=='regressions':
        roster=(SCRATCH/'regression-roster.txt').read_text().splitlines()
        assert len(roster)==66
        return check('r2-api-regressions-retry2',pytest+roster+['-n','2','-vv','--tb=short',
            '--junitxml='+str(SCRATCH/'r2-api-regressions.xml'),'-p','no:cacheprovider'])
    if mode=='focused':
        files=['tests/test_native_shared_'+x+'.py' for x in ('contract','evidence','selection','render')]
        files+=['tests/test_native_schema_metadata_reuse.py','tests/test_native_u1_selector_refusals.py']
        return check('r2-native-focused',pytest+files+['-n','2','-q','-p','no:cacheprovider'])
    if mode=='inventory':
        return check('r2-d76-inventory',pytest+['tests/test_wave7_5213_d76_round4_inventory.py','-n','2','-q','-p','no:cacheprovider'])
    if mode=='collect':
        return check('r2-collection',pytest+['tests','--collect-only','-q','-p','no:cacheprovider'])
    if mode=='pins':
        return check('r2-prompt-check',[PYTHON,'-m','data_sheets_schema.cli','api','prompts','check','--strict'])
    if mode=='scanner':
        return check('r2-scanner',[PYTHON,'.claude/skills/d4d-generation-specificity-audit/scan.py','--report',str(SCRATCH/'r2-scanner.md'),'--json',str(SCRATCH/'r2-scanner.json')])
    if mode=='guards':
        return check('r2-specificity-guards',pytest+['tests/test_generation_specificity_skill.py','tests/test_neutral_generation_schema.py','tests/test_profiles.py','tests/test_external_dataset_onboarding.py','-n','2','-q','-p','no:cacheprovider'])
    if mode=='parity':
        baseline=SCRATCH/('baseline-'+BASE[:9]); archive(BASE,baseline)
        test='tests/test_native_u1_api_parity.py'
        shutil.copyfile(ROOT/test,baseline/test)
        # One fixed fixture namespace makes absolute paths byte-comparable.
        # Override tmp_path with an explicit reusable, per-node directory;
        # fixtures overwrite only their own synthetic input files.
        plugin='scripts/adhoc/native_u1_round2_parity_plugin_20261106.py'
        for tree in (baseline,COMPOSED):
            shutil.copyfile(ROOT/plugin,tree/plugin)
        for label,tree in [('before',baseline),('after',COMPOSED)]:
            os.environ['U1_PARITY_OUTPUT']=str(SCRATCH/('r2-parity-'+label))
            code=check('r2-parity-'+label,pytest+[test,'-p','scripts.adhoc.native_u1_round2_parity_plugin_20261106','-q','-p','no:cacheprovider'],tree)
            if code: return code
        rows=[]
        before=SCRATCH/'r2-parity-before'; after=SCRATCH/'r2-parity-after'
        assert {p.name for p in before.glob('*.txt')}=={p.name for p in after.glob('*.txt')}
        for path in sorted(before.glob('*.txt')):
            a=path.read_bytes(); b=(after/path.name).read_bytes()
            rows.append(dict(condition=path.stem,before_sha256=sha(a),after_sha256=sha(b),bytes_before=len(a),bytes_after=len(b),equal=a==b))
        assert len(rows)==14
        (SCRATCH/'r2-api-render-parity.json').write_text(json.dumps(rows,indent=2)+'\n')
        print('Parity:',sum(r['equal'] for r in rows),'/',len(rows),flush=True)
        return 0 if all(r['equal'] for r in rows) else 1
    raise ValueError(mode)

if __name__=='__main__':
    raise SystemExit(main())
