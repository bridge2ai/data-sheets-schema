"""#4354 U1 round 2, 2026-11-06: offline packet composition and bounded checks.
Inputs: local M7/U1 objects and reviewed packet preimages. Outputs: scratch
archives/logs and proposal-only patches. Never writes protected worktree files.
"""
import ast
import copy
import difflib
import hashlib
import io
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-native-u1'
LOCK = ROOT.parent / 'plans/native_quiet_window.lock'
HEAD = '41b7169f6296c69201fc46389082c441e7d7165c'
BASE = '8bc90e93d736d464f98e9eedffee45f0ad8e5d3f'
OUT = ROOT / 'scripts/adhoc/native_u1_packets'
COMPOSED = SCRATCH / ('composed-' + HEAD[:9])
SHARED = 'src/data_sheets_schema/shared_generation.py'
SIDECAR = 'tests/utils/run_spec_boundary_contracts.json'
CHECKER = 'tests/utils/run_spec_boundaries.py'
PINS = 'src/download/prompts/canonical_hashes.yaml'

def quiet():
    if LOCK.exists():
        raise SystemExit('Quiet window active; no heavy work started')

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def run(args, cwd=ROOT, **kwargs):
    return subprocess.check_output(args, cwd=cwd, **kwargs)

def environment(root):
    env = dict(os.environ)
    for key in list(env):
        if key.endswith('_API_KEY') or key in ('ANTHROPIC_AUTH_TOKEN', 'CLAUDE_CODE_OAUTH_TOKEN', 'ANTHROPIC_BASE_URL', 'OPENAI_BASE_URL'):
            del env[key]
    env.update(PYTHONPATH=os.pathsep.join((str(ROOT/'scripts/adhoc/native_u1_offline'), str(root/'src'), str(root))),
               PYTHONPYCACHEPREFIX=str(SCRATCH/'pycache'), TMPDIR=str(SCRATCH), GIT_NO_LAZY_FETCH='1')
    return env

def archive(commit, target):
    quiet()
    target.mkdir()
    raw = run(['git', 'archive', commit])
    with tarfile.open(fileobj=io.BytesIO(raw)) as tar:
        tar.extractall(target, filter='data')
    # Private metadata, read-only local object alternate: needed by the real pin
    # CLI and tests that audit committed blobs. No remote or checkout operation.
    run(['git', 'init', '-q'], target)
    objects = run(['git', 'rev-parse', '--path-format=absolute', '--git-path', 'objects']).decode().strip()
    (target/'.git/objects/info/alternates').write_text(objects+'\n')
    run(['git', 'update-ref', '--no-deref', 'HEAD', commit], target)
    run(['git', 'read-tree', commit], target)

def packet(name, target, new, extra=None):
    old = (ROOT/target).read_bytes()
    patch = ''.join(difflib.unified_diff(old.decode().splitlines(True), new.decode().splitlines(True), fromfile='a/'+target, tofile='b/'+target)).encode()
    (OUT/(name+'.patch')).write_bytes(patch)
    info = dict(status='proposal_only_scratch_validation_not_worktree_approval', target=target,
                base=BASE, u1_prompt_commit=HEAD, preimage_sha256=sha(old), postimage_sha256=sha(new), patch_sha256=sha(patch))
    info.update(extra or {})
    (OUT/(name+'.json')).write_text(json.dumps(info, indent=2)+'\n')
    assert (ROOT/target).read_bytes() == old


def prepare():
    quiet()
    snapshot = {p:(ROOT/p).read_bytes() for p in (SHARED,SIDECAR,CHECKER,PINS)}
    run([sys.executable, 'scripts/adhoc/native_u1_shared_packet_20261106.py'])
    archive(HEAD, COMPOSED)
    pin_tree = SCRATCH / ('pins-' + HEAD[:9])
    archive(HEAD, pin_tree)
    for name in ('generation', 'receipt_policy'):
        quiet()
        path = f'src/download/prompts/native_shared_{name}_v1.md'
        output = run([sys.executable, '-m', 'data_sheets_schema.cli', 'api', 'prompts', 'pin', '--file', path,
                      '--reason', 'Native U1 shared-v1 declared-difference asset (#4354); no API asset rotation.'], pin_tree, env=environment(pin_tree))
        (SCRATCH/f'r2-pin-{name}.log').write_bytes(output)
    import yaml
    before = yaml.safe_load(snapshot[PINS]); new = (pin_tree/PINS).read_bytes(); after = yaml.safe_load(new)
    for key,value in before['files'].items():
        assert after['files'][key] == value
    assert len(after['files']) == len(before['files'])+2
    for name in ('generation', 'receipt_policy'):
        path = f'src/download/prompts/native_shared_{name}_v1.md'
        row = after['files'][path]
        assert row['pinned_at_commit'] == HEAD
        assert sha(run(['git','show',HEAD+':'+path])) == row['sha256']
    packet('canonical_hashes', PINS, new, {'producer':'d4d api prompts pin in private scratch archive', 'existing_pins_unchanged':True})
    run(['git','apply',str(OUT/'shared_generation.patch'),str(OUT/'api_runner_companion.patch')],COMPOSED)
    old = json.loads(snapshot[SIDECAR]); result=copy.deepcopy(old)
    assert len(old['contracts']) == 21 and old['approval']['authorized'] is True
    assert sha(snapshot[CHECKER]) == 'a379e93a0065dc927835b1417cabcb926e33eeb333416c768237bc50d2dc6237'
    updates=[]
    for row in result['contracts']:
        raw = (COMPOSED/row['source_path']).read_bytes()
        nodes=[n for n in ast.parse(raw).body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name==row['identity'].rsplit('.',1)[1]]
        assert len(nodes)==1
        node=nodes[0]; start=min([node.lineno,*[d.lineno for d in node.decorator_list]])
        body=b''.join(raw.splitlines(True)[start-1:node.end_lineno])
        pin=dict(function_start_line=start,function_end_line=node.end_lineno,function_bytes=len(body),function_sha256=sha(body))
        prior={key:row[key] for key in pin}
        changed=prior['function_sha256']!=pin['function_sha256']
        assert changed == (row['identity']=='data_sheets_schema.shared_generation.select')
        assert row['proposed_mode']=='validated-caller' and row['proposed_precondition'].strip()
        row.update(pin)
        updates.append(dict(identity=row['identity'],before=prior,after=pin,body_changed=changed))
    result.setdefault('historical_provenance',{})['pre_native_u1']={k:copy.deepcopy(v) for k,v in old.items() if k not in ('contracts','historical_provenance')}
    result['shared_generation_sha256']=sha((COMPOSED/SHARED).read_bytes())
    result['source_sha256']={p:sha((COMPOSED/p).read_bytes()) for p in (SHARED,'src/data_sheets_schema/latch_journal.py')}
    result['source']=str(COMPOSED)
    result['producer_sha256']=sha(Path(__file__).read_bytes())
    result['native_u1_rebind']=dict(status='proposal only; scratch testing is not protected-file approval',
        baseline_sidecar_sha256=sha(snapshot[SIDECAR]), checker_sha256=sha(snapshot[CHECKER]),
        helper_path=str(Path(__file__).relative_to(ROOT)), helper_sha256=sha(Path(__file__).read_bytes()),
        u1_commit=HEAD, function_pin_updates=updates,
        limits='All 21 identities, modes, preconditions and original approval retained; only select body changes; offsets recomputed; checker unchanged.')
    raw=(json.dumps(result,indent=2,ensure_ascii=False)+'\n').encode()
    packet('run_spec_boundary_contracts',SIDECAR,raw,result['native_u1_rebind'])
    patches=[str(OUT/(name+'.patch')) for name in ('shared_generation','api_runner_companion','canonical_hashes','run_spec_boundary_contracts')]
    run(['git','apply','--check',*patches])
    run(['git','apply',str(OUT/'canonical_hashes.patch'),str(OUT/'run_spec_boundary_contracts.patch')], COMPOSED)
    for name in ('shared_generation','api_runner_companion','canonical_hashes','run_spec_boundary_contracts'):
        meta=json.loads((OUT/(name+'.json')).read_text())
        assert sha((COMPOSED/meta['target']).read_bytes())==meta['postimage_sha256']
    assert snapshot=={p:(ROOT/p).read_bytes() for p in snapshot}
    print('Four packets apply together; exact scratch postimages verified. Protected worktree unchanged.',flush=True)


def check():
    root=Path(sys.argv[2]); name=sys.argv[3]; command=sys.argv[4:]
    quiet()
    logpath=SCRATCH/(name+'.log')
    assert not logpath.exists(), logpath
    with logpath.open('w') as log:
        proc=subprocess.Popen(command,cwd=root,env=environment(root),stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        try:
            code=proc.wait(timeout=3600)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid,signal.SIGTERM); proc.wait(); code=124
        log.write(f'\nU1_CHECK_EXIT={code}\n')
    print(f'{name}: exit {code}; {logpath}',flush=True)
    raise SystemExit(code)

if __name__=='__main__':
    {'prepare':prepare,'check':check}[sys.argv[1]]()
