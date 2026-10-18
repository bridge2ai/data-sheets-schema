# Purpose: Compare direct pytest, default Make and focused Make collection Counters.
# Inputs: historical source/worktree paths explicitly recorded below.
# Outputs: benchmark logs/JSON beside this script (original behavior).
# Serves: #5018 / PR #5026; date: 2026-10-12.
# Historical helper: original body preserved verbatim after this header.
# Paths are session-specific; inspect and adapt before a future run.
# This copy was preserved after the original measurement, not rerun.
import subprocess, os, json, time, collections, shlex
from pathlib import Path
b=Path(__file__).parent;w=Path('/private/tmp/d4d-performance-iteration-5018-20261012');python='/private/tmp/d4d-performance-implementation-20261012/.venv/bin/python'
env=os.environ.copy();env['PYTHONPATH']=str(w/'src')+os.pathsep+str(w);env['PYTHONPYCACHEPREFIX']=str(b/'pycache')
for name in ('MAKEFLAGS','MFLAGS','MAKEOVERRIDES','PYTEST_PATHS','PYTEST_ARGS'):env.pop(name,None)
make=['make','--no-print-directory','test-python','RUN='+shlex.join([python,'-m']),'PYTEST_ARGS=--collect-only -q -n0']
runs=[('direct-full',[python,'-m','pytest','tests','--collect-only','-q','-n0','-p','no:cacheprovider']),('make-full',make),('make-explicit',make+['PYTEST_PATHS=tests/test_ci_sharding.py'])];rows=[];counters={}
for label,args in runs:
 before=time.perf_counter()
 with (b/(label+'.log')).open('w') as out:r=subprocess.run(args,cwd=w,env=env,stdout=out,stderr=subprocess.STDOUT)
 elapsed=time.perf_counter()-before;nodes=[l for l in (b/(label+'.log')).read_text().splitlines() if l.startswith('tests/') and '::' in l];counter=collections.Counter(nodes);counters[label]=counter
 (b/(label+'-nodes.json')).write_text(json.dumps(counter,sort_keys=True,indent=2)+'\n');row={'scope':label,'exit':r.returncode,'seconds':elapsed,'occurrences':sum(counter.values()),'distinct_node_ids':len(counter)};rows.append(row);print(json.dumps(row),flush=True)
 if r.returncode:raise SystemExit(r.returncode)
assert counters['direct-full']==counters['make-full']
assert counters['make-explicit']=={k:v for k,v in counters['direct-full'].items() if k.startswith('tests/test_ci_sharding.py::')}
prior=json.loads((b.parent/'collection-5018/2-full-nodes.json').read_text());current=dict(counters['direct-full'])
# Compare every unchanged file, retaining occurrence multiplicity. The prior
# instruction worktree has ten new guard cases; this branch has two new modules.
exclude=('tests/test_notes_write_guard.py::','tests/test_focused_test_command.py::','tests/test_term_validator_hook.py::')
assert {k:v for k,v in prior.items() if not k.startswith(exclude)}=={k:v for k,v in current.items() if not k.startswith(exclude)}
result={'runs':rows,'default_make_equals_direct_full_counter':True,'explicit_make_equals_full_subset_counter':True,'unchanged_file_counters_equal_prior_collection':True,'intentional_comparison_exclusions':list(exclude),'runner':'locked Python3.12 via explicit RUN override; normal Poetry command construction separately tested','tests_executed':0};(b/'collection-comparison.json').write_text(json.dumps(result,indent=2)+'\n');print('Complete collection and occurrence joins passed',flush=True)
