# Purpose: Measure complete and explicit pytest collection and preserve node multiplicities.
# Inputs: historical source/worktree paths explicitly recorded below.
# Outputs: benchmark logs/JSON beside this script (original behavior).
# Serves: #5018 / PR #5025; date: 2026-10-12.
# Historical helper: original body preserved verbatim after this header.
# Paths are session-specific; inspect and adapt before a future run.
# This copy was preserved after the original measurement, not rerun.
import subprocess, os, json, time, hashlib, collections
from pathlib import Path
base = Path(__file__).parent
w = Path('/private/tmp/d4d-performance-instructions-5017-20261012')
python = '/private/tmp/d4d-performance-implementation-20261012/.venv/bin/python'
env = os.environ.copy(); env['PYTHONPATH'] = str(w/'src')+os.pathsep+str(w); env['PYTHONPYCACHEPREFIX']=str(base/'pycache')
rows=[]
for i, (label, target) in enumerate([('explicit','tests/test_ci_sharding.py'),('full','tests'),('full','tests'),('explicit','tests/test_ci_sharding.py')],1):
    args=[python,'-m','pytest',target,'--collect-only','-q','-p','no:cacheprovider','-n0']
    before=time.perf_counter()
    with (base/f'{i}-{label}.log').open('w') as out:
        result=subprocess.run(args,cwd=w,env=env,stdout=out,stderr=subprocess.STDOUT)
    elapsed=time.perf_counter()-before
    raw=(base/f'{i}-{label}.log').read_bytes()
    nodes=[line for line in raw.decode().splitlines() if line.startswith('tests/') and '::' in line]
    counts=collections.Counter(nodes); (base/f'{i}-{label}-nodes.json').write_text(json.dumps(counts,sort_keys=True,indent=2)+'\n')
    row={'index':i,'scope':target,'exit':result.returncode,'elapsed_seconds':elapsed,'occurrences':len(nodes),'distinct_node_ids':len(counts),'log_sha256':hashlib.sha256(raw).hexdigest()};rows.append(row)
    (base/'results.json').write_text(json.dumps(rows,indent=2)+'\n'); print(json.dumps(row),flush=True)
    if result.returncode:break
