# Purpose: rerun independent M1-M9 intents against U2 round 3 (#5508), 2026-11-06.
# Inputs: committed HEAD and review mutation definitions. Outputs: isolated scratch logs/results.
import hashlib
import io
import json
import os
from pathlib import Path
import re
import runpy
import signal
import subprocess
import sys
import tarfile
import time
R=Path(__file__).resolve().parents[2]; OUT=R.parent/'scratch-native-u2/r3-mutations3'
LOCK=R.parent/'plans/native_quiet_window.lock'
PY='/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python'
D=runpy.run_path(str(R.parent/'scratch-review-u2-probes/mutation_probe.py'))
PREP,CTRL,SUP=D['PREP'],D['CTRL'],D['SUP']
M=D['MUTATIONS']
M['M0_control']=([],[D['EQ'],D['V2'],'tests/test_native_preparer_v2_boundaries.py'])
M['M9_v2_drops_external_pins']=([(PREP,'    for external in args.external_sources:\n        for path in sorted(external.resolve().rglob("*")):\n            if path.is_file() and "__pycache__" not in path.parts:\n                pins[str(path)] = sha(path)\n','')],[D['EQ']])
names=sys.argv[1:]
assert names
if LOCK.exists():
    raise SystemExit('quiet window: no mutation work started')
OUT.mkdir(exist_ok=True)
S=OUT/'source-final'
if not S.exists():
    S.mkdir()
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip()
    with tarfile.open(fileobj=io.BytesIO(subprocess.check_output(['git','archive',commit],cwd=R))) as archive:
        archive.extractall(S,filter='data')
    subprocess.run(['git','init','-q',str(S)],check=True)
    common=subprocess.check_output(['git','rev-parse','--path-format=absolute','--git-common-dir'],cwd=R,text=True).strip()
    (S/'.git/objects/info/alternates').write_text(str(Path(common)/'objects')+'\n')
    (S/'.git/HEAD').write_text(commit+'\n')
subprocess.run(['git','read-tree','HEAD'],cwd=S,check=True)
for name in names:
    if LOCK.exists():
        raise SystemExit('quiet window: next mutation not started')
    edits,tests=M[name]; originals={}
    if name.startswith(('M3','M4')):
        tests=['tests/test_native_preparer_v2_boundaries.py::test_preparer_refusals']
    try:
        def write(path,text):
            originals.setdefault(path,(S/path).read_text()); (S/path).write_text(text)
        for path,old,new in edits:
            text=(S/path).read_text(); assert text.count(old)==1,(name,path)
            write(path,text.replace(old,new))
        # Refreeze mutated helper bytes so pins cannot masquerade as behavioral coverage.
        if any(path==PREP for path,_,_ in edits):
            path='src/data_sheets_schema/native_controller_sources_v2.json'
            manifest=json.loads((S/path).read_bytes())
            for pin in manifest['modules'].values():
                if pin['path']==PREP: pin['sha256']=hashlib.sha256((S/PREP).read_bytes()).hexdigest()
            write(path,json.dumps(manifest,indent=2)+'\n')
            digest=hashlib.sha256((S/path).read_bytes()).hexdigest()
            write(CTRL,re.sub(r"SOURCES_SHA256 = '[a-f0-9]+'",f"SOURCES_SHA256 = '{digest}'",(S/CTRL).read_text()))
        if any(path==D['DIRECT'] for path,_,_ in edits):
            digest=hashlib.sha256((S/D['DIRECT']).read_bytes()).hexdigest()
            write(SUP,re.sub(r"('prepare_direct': .*?\n        'sha256': ')[a-f0-9]+",lambda m:m[1]+digest,(S/SUP).read_text()))
        env={k:v for k,v in os.environ.items() if not(k.startswith(('ANTHROPIC_','CBORG_','OPENAI_','CLAUDE_')) or k.endswith(('_API_KEY','_AUTH_TOKEN','_ACCESS_TOKEN')))}
        env.update(PYTHONDONTWRITEBYTECODE='1',PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',PYTEST_ADDOPTS='',PYTHONPATH=str(S/'src')+os.pathsep+str(S)+os.pathsep+str(R.parents[1]/'data-sheets-schema/fairscape_models'),UV_OFFLINE='1',PIP_NO_INDEX='1',GIT_NO_LAZY_FETCH='1')
        command=[PY,'-B','-m','pytest','-o','addopts=','-p','no:cacheprovider','-q',*tests,'--basetemp='+str(OUT/(name+'-pytest')),'--junitxml='+str(OUT/(name+'.xml'))]
        assert not (OUT/(name+'-pytest')).exists()
        start=time.monotonic()
        with (OUT/(name+'.log')).open('w') as log:
            child=subprocess.Popen(command,cwd=S,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            try:
                while child.poll() is None:
                    if time.monotonic()-start>=3600: raise TimeoutError()
                    try: child.wait(timeout=60)
                    except subprocess.TimeoutExpired:
                        if LOCK.exists():
                            os.killpg(child.pid,signal.SIGSTOP)
                            while LOCK.exists():
                                time.sleep(60)
                                if time.monotonic()-start>=3600: raise TimeoutError()
                            os.killpg(child.pid,signal.SIGCONT)
            except BaseException:
                os.killpg(child.pid,signal.SIGKILL);child.wait()
                raise
        result={'mutation':name,'returncode':child.returncode,'seconds':time.monotonic()-start,'tests':tests,'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=S,text=True).strip()}
        (OUT/(name+'.json')).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
    finally:
        for path,text in originals.items():
            (S/path).write_text(text)
            assert (S/path).read_bytes()==subprocess.check_output(['git','show','HEAD:'+path],cwd=S)
