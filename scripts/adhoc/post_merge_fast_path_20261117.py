#!/usr/bin/env python3
"""Offline post-merge Steps 2–6 driver for PR 5968, 2026-11-17.
Inputs: exact local main SHA, explicit production config, saved evidence, existing CLIs.
Outputs: verified step artifacts, resumable dependency stops, review packets and timings.
Dry runs use marked test evidence. No Claude execution, network, GitHub, merge or push.
C20 owner decision, 2026-11-19: select truthful codex_cli/claude or codex_cli/agy packets.
Retained helper copy for the explicit model-label amendment; source gates remain unchanged.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import signal
import stat
import subprocess
import sys
import time
from types import SimpleNamespace

P = Path('/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema')
E = P.parent / 'd4d-executions'
R = E / 'codex-development-efficiency-20261111'
HERE = Path(__file__).resolve()
RUNNER = P / 'scripts/adhoc/run_lane_20261115.py'
BASE_PYTHON = P / '.venv/bin/python'
SUPPORT = E / 'codex-step5e-a1d7-20261116/scripts/adhoc'
RUNBOOK = E / 'plans/native_post_merge_runbook_DRAFT_20261114.md'
HANDOFF = R / 'notes/development_efficiency_20261111/handoffs/codex196-postmerge-fastpath-20261117.md'
PROJECTS = ('CHORUS', 'AI_READI', 'CM4AI', 'VOICE', 'VOICE_PEDIATRIC')
STEPS = ('checkout', 'environment', 'binary-copy', 'probe-prepare', 'register-chorus', 'register-project', 'preflight-all', 'review-packets')
REVIEWER_PAIRS = {'codex-agy': ('codex_cli', 'agy'), 'codex-claude': ('codex_cli', 'claude')}
GATE_NAMES = ('native_registration_pin_gate.py', 'native_registration_validation_worker.py',
    'native_registration_field_gate.py', 'native_registration_fields_v1.json',
    'native_registration_documents.py', 'native_registration_validation_protocol.py',
    'native_registration_production_validator.py')
DEFAULT_SOURCE = Path('/Users/marcin/.local/share/claude/versions/2.1.325')
DEFAULT_BINARY = E / 'native-binary-durable/2.1.325-84590fefe633/claude'


def selected_route():
    project, rep = getattr(A, 'project', 'CHORUS'), getattr(A, 'rep', 1)
    if project not in PROJECTS or type(rep) is not int or rep <= 0:
        raise ValueError('known project and positive integer rep required')
    return project, rep


def route_fields():
    project, rep = selected_route()
    if (project, rep) == ('CHORUS', 1):
        return {}
    return dict(cell_route=dict(project=project, rep=rep, reviewer_pair=getattr(A, 'reviewer_pair', 'codex-agy')))


def require_route_config():
    expected = route_fields()
    if expected:
        if encode(C.get('cell_route')) != encode(expected['cell_route']):
            raise ValueError('selected project/rep route differs from config')
        if selected_route()[0] == 'AI_READI' and getattr(A, 'reviewer_pair', 'codex-agy') != 'codex-agy':
            raise ValueError('AI_READI requires the codex-agy reviewer pair')
    elif 'cell_route' in C and encode(C['cell_route']) != encode(dict(project='CHORUS', rep=1,
                                                     reviewer_pair=getattr(A, 'reviewer_pair', 'codex-agy'))):
        raise ValueError('legacy CHORUS route cannot consume another cell config')


def registration_state():
    project, rep = selected_route()
    return S / ('chorus-registration.json' if not route_fields() else project+'-rep'+str(rep)+'-registration.json')


def actual_reference_hold():
    if not route_fields():
        return 'Offline candidate cohort does not replace the actual CHORUS registration; reviewers must resolve its sizing and real-reference comparison before cell 1.'
    project, rep = selected_route()
    return 'Offline candidate cohort does not replace the actual '+project+' rep'+str(rep)+' registration; reviewers must resolve its sizing and real-reference comparison before the selected cell.'


def verify_actual_project(path):
    if not route_fields():
        return
    body = load(path)['registration']
    prepared = json.loads(body['preparation_raw_json'])['registration']
    selected = prepared['selection']
    assert pin(Path(selected['path'])) == selected, 'actual selection pin differs'
    assert load(Path(selected['path']))['run']['project'] == selected_route()[0], 'actual registration project differs'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()


def write(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    assert path.read_bytes() == raw


def save(path, value):
    write(path, (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False)+'\n').encode())


def load(path):
    return json.loads(path.read_bytes())


def state(path, value):
    """Retain every old state before atomically publishing the latest pointer."""
    raw=(json.dumps(value,sort_keys=True,indent=2,ensure_ascii=False,allow_nan=False)+'\n').encode()
    if path.exists():
        old=path.read_bytes()
        if old==raw: return
        archived=S/'state-history'/path.name/digest(old)
        if not archived.exists(): write(archived,old)
        assert archived.read_bytes()==old
        pending=path.with_name(path.name+'.pending-'+digest(raw)[:12])
        write(pending,raw)
        assert path.read_bytes()==old
        os.replace(pending,path)
    else:
        write(path,raw)
    assert path.read_bytes()==raw


def pin(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError('ordinary file required: ' + str(path))
    raw = path.read_bytes()
    if not raw:
        raise ValueError('empty artifact: ' + str(path))
    return dict(path=str(path), bytes=len(raw), sha256=digest(raw))


def copy_pinned(source, target):
    path=Path(source['path'])
    if path.is_symlink() or not path.is_file():
        raise ValueError('review source must remain an ordinary file: '+str(path))
    raw=path.read_bytes()
    assert len(raw)==source['bytes'] and digest(raw)==source['sha256'], 'review input changed after its pin was recorded'
    write(target,raw); target.chmod(0o444)
    copied=pin(target)
    assert all(copied[key]==source[key] for key in ('bytes','sha256'))
    return copied


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    sys.modules[name] = value
    spec.loader.exec_module(value)
    return value


def git(root, *args):
    return subprocess.run(['/usr/bin/git', '--no-replace-objects', '-c', 'core.hooksPath=/dev/null',
        '-c', 'core.fsmonitor=false', '-C', str(root), *args], capture_output=True, check=True, timeout=120).stdout


def physical(path):
    if not path.is_absolute() or path.resolve() != path:
        raise ValueError('absolute physical path required: '+str(path))
    return path


def guard():
    require_route_config()
    physical(W); physical(S)
    if A.existing_venv:
        physical(VENV)
        if not VENV.is_dir() or VENV.is_relative_to(S) or S.is_relative_to(VENV):
            raise ValueError('supplied environment must exist and be disjoint from driver scratch state')
    if W == P or W == R or W.is_relative_to(S) or S.is_relative_to(W):
        raise ValueError('checkout and scratch must be disjoint and not primary/report checkout')
    if (E / 'plans/native_quiet_window.lock').exists():
        raise ValueError('quiet-window lock active')
    if W.exists():
        if Path(git(W, 'rev-parse', '--show-toplevel').decode().strip()) != W:
            raise ValueError('checkout must be the exact Git top-level directory')
        if git(W, 'rev-parse', 'HEAD').decode().strip() != A.main_sha:
            raise ValueError('checkout HEAD differs from selected main SHA')
        if git(W, 'diff', '--name-only', 'HEAD').strip():
            raise ValueError('tracked checkout edits are not admitted')
    state = S / 'identity.json'
    if state.exists() and encode(load(state)) != encode(identity()):
        raise ValueError('scratch identity or dry-run mode differs; use a fresh scratch root')


def identity():
    value=dict(main_sha=A.main_sha, checkout=str(W), scratch=str(S), dry_run=A.dry_run)
    if A.existing_venv: value['existing_venv']=str(VENV)
    value.update(route_fields())
    return value


def command_text(argv):
    return shlex.join([str(x) for x in argv])


def clean_env():
    env = dict(os.environ)
    runner = module('fastpath_env_runner', RUNNER)
    for name in tuple(env):
        if name.endswith('_API_KEY') or name in runner.SCRUBBED_PROVIDER_VARS or name in (
            'CLAUDE_CODE_OAUTH_TOKEN', 'CLAUDE_CODE_MAX_OUTPUT_TOKENS', 'PYTHONPATH',
            'PYTHONHOME', 'PYTHONSTARTUP', 'PYTHONOPTIMIZE', 'VIRTUAL_ENV', 'POETRY_ACTIVE', '__PYVENV_LAUNCHER__'):
            env.pop(name, None)
    env.update(PYTHONDONTWRITEBYTECODE='1', PYTHONNOUSERSITE='1', PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',
        PIP_NO_INDEX='1', UV_OFFLINE='1', GIT_NO_LAZY_FETCH='1', GIT_NO_REPLACE_OBJECTS='1',
        GIT_CONFIG_GLOBAL='/dev/null', GIT_CONFIG_SYSTEM='/dev/null', GIT_OPTIONAL_LOCKS='0',
        GIT_TERMINAL_PROMPT='0', GIT_ALLOW_PROTOCOL='file')
    return env


def offline_profile():
    path = S / 'offline.sb'
    if not path.exists():
        allowed = sorted({str(BASE_PYTHON.resolve()), '/usr/bin/git', '/bin/cp', '/usr/bin/sandbox-exec',
            '/Library/Developer/CommandLineTools/usr/bin/git', '/Applications/Xcode.app/Contents/Developer/usr/bin/git'})
        raw = '(version 1)\n(allow default)\n(deny network*)\n' + '(deny process-exec (require-all ' + ' '.join(
            '(require-not (literal '+json.dumps(item)+'))' for item in allowed) + '))\n'
        write(path, raw.encode())
    return path


def run_cli(label, argv, *, expected=(0,), timeout=1800, sandbox=True, cwd=None):
    # These are offline preparation watchdogs, never native Bash, probe or cell limits.
    record = S / 'commands' / label
    retries=sorted((S/'commands').glob(label+'.retry-*')) if (S/'commands').exists() else []
    if retries: record=retries[-1]
    if record.exists():
        old = load(record / 'result.json')
        if old['returncode'] not in expected and label in A.retry_command:
            record=S/'commands'/(label+'.retry-'+str(len(retries)+1).zfill(3))
        elif old['requested_argv'] != [str(x) for x in argv] or old['returncode'] not in expected:
            raise ValueError('existing command evidence is not reusable: '+label)
        else:
            for item in old.get('verified_artifacts', []):
                if pin(Path(item['path'])) != item:
                    raise ValueError('saved output changed: '+item['path'])
            return old
    record.mkdir(parents=True)
    actual = [str(x) for x in argv]
    if sandbox:
        actual = ['/usr/bin/sandbox-exec', '-f', str(offline_profile()), *actual]
    started = time.monotonic()
    try:
        result = bounded(actual, cwd or W, timeout)
    except (subprocess.TimeoutExpired,InterruptedError) as exc:
        partial=getattr(exc,'output',None) or b''
        if isinstance(partial,str): partial=partial.encode()
        result=subprocess.CompletedProcess(actual,124,partial,(type(exc).__name__+': '+str(exc)+'\n').encode())
    write(record / 'stdout.txt', result.stdout)
    write(record / 'stderr.txt', result.stderr)
    outcome = dict(requested_argv=[str(x) for x in argv], actual_argv=actual, cwd=str(cwd or W),
        returncode=result.returncode, elapsed_seconds=time.monotonic()-started,
        stdout_path=str(record / 'stdout.txt'), stderr_path=str(record / 'stderr.txt'))
    save(record / 'result.json', outcome)
    if result.returncode not in expected:
        raise ValueError(label+' failed with exit '+str(result.returncode)+': '+result.stderr.decode(errors='replace')[-1800:])
    return outcome


def bounded(argv, cwd, timeout):
    """TERM the owned group first so gate parents can reap separately sessioned validators."""
    previous={sig:signal.getsignal(sig) for sig in (signal.SIGTERM,signal.SIGINT)}
    process=None
    creating=True
    cleaning=False
    pending=None
    def interrupted(signum, frame):
        nonlocal pending
        pending=signum
        if not creating and not cleaning:
            raise InterruptedError('external termination '+str(signum))
    for sig in previous: signal.signal(sig,interrupted)
    try:
        process=subprocess.Popen(argv,cwd=cwd,env=clean_env(),stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
        creating=False
        if pending is not None: raise InterruptedError('termination while creating child '+str(pending))
        stdout,stderr=process.communicate(timeout=timeout)
        return subprocess.CompletedProcess(argv,process.returncode,stdout,stderr)
    except BaseException:
        cleaning=True
        if process is None: raise
        if process.returncode is None:
            try: os.killpg(process.pid,signal.SIGTERM)
            except ProcessLookupError: pass
        try: process.communicate(timeout=20)
        except subprocess.TimeoutExpired:
            try: os.killpg(process.pid,signal.SIGKILL)
            except ProcessLookupError: pass
            process.communicate(timeout=10)
        raise
    finally:
        for sig,handler in previous.items(): signal.signal(sig,handler)


def inputs(project):
    return dict(source_manifest=W / 'data/preprocessed/source_manifest.yaml',
        bundle=W / 'data/preprocessed/concatenated' / (project+'_preprocessed.txt'),
        chunk_manifest=W / 'data/preprocessed/chunks' / (project+'_chunks.yaml'),
        context=W / 'data/omission_contexts' / (project.lower()+'_omission_context.json'),
        full_schema=W / 'src/data_sheets_schema/schema/data_sheets_schema_all.yaml',
        core_schema=W / 'src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml')


def packet(project):
    return S / 'packets' / project


def support():
    names=('preflight_step5e_20261116.py','preflight_step5e_saved_20261116.py','preflight_step5e_sizes_20261116.py')
    captured={name:pin(SUPPORT/name) for name in names}
    record=S/'retained-helper-pins.json'
    if record.exists(): assert load(record)==captured, 'retained rehearsal helpers changed'
    else: save(record,captured)
    b = module('fastpath_rehearsal_base', SUPPORT / 'preflight_step5e_20261116.py')
    b.ROOT, b.HEAD, b.SCRATCH, b.VENV, b.PYTHON = W, A.main_sha, S, VENV, PYTHON
    chain = module('fastpath_rehearsal_chain', SUPPORT / 'preflight_step5e_saved_20261116.py')
    chain.b, chain.ROOT, chain.SCRATCH = b, W, S
    sizes = module('fastpath_rehearsal_sizes', SUPPORT / 'preflight_step5e_sizes_20261116.py')
    sizes.b, sizes.ROOT, sizes.SCRATCH = b, W, S
    assert {name:pin(SUPPORT/name) for name in names}==captured
    return b, chain, sizes


def checked_environment():
    result = load(S / 'environment.json')
    assert result['checkout'] == str(W) and result['main_sha'] == A.main_sha
    assert result['venv']==str(VENV) and result['interpreter']==str(PYTHON)
    assert pin(Path(result['isolated_pth']['path'])) == result['isolated_pth']
    return result


def checkout():
    existed = W.exists()
    if existed and not A.dry_run and not (S / 'checkout.json').exists():
        raise ValueError('production requires a new checkout or this driver’s prior checkout record')
    if not existed:
        git(P, 'cat-file', '-e', A.main_sha+'^{commit}')
        git(P, 'worktree', 'add', '--detach', str(W), A.main_sha)
    guard()
    expected = git(W, 'rev-parse', 'HEAD:fairscape_models').decode().strip()
    sub = W / 'fairscape_models'
    if not (sub / '.git').exists():
        if sub.exists() and any(sub.iterdir()):
            raise ValueError('uninitialized submodule directory is nonempty')
        git(P / 'fairscape_models', 'cat-file', '-e', expected+'^{commit}')
        git(W, 'clone', '--shared', '--no-checkout', str(P / 'fairscape_models'), str(sub))
        git(sub, 'remote', 'remove', 'origin')
        git(sub, 'checkout', '--detach', expected)
    assert git(sub, 'rev-parse', 'HEAD').decode().strip() == expected
    assert not git(sub, 'status', '--porcelain').strip()
    record = dict(**identity(), existing_assigned_checkout=existed, fairscape_commit=expected,
        source_clean=not bool(git(W, 'status', '--porcelain', '--untracked-files=all').strip()))
    assert record['source_clean']
    if (S/'checkout.json').exists():
        prior=load(S/'checkout.json')
        assert prior['main_sha']==record['main_sha'] and prior['fairscape_commit']==record['fairscape_commit']
    else:
        save(S / 'checkout.json', record)
    return dict(status='ready', artifacts=[pin(S / 'checkout.json')], holds=[])


def environment():
    if not (A.existing_venv and A.dry_run):
        assert load(S / 'checkout.json')['main_sha'] == A.main_sha
    if (S/'environment.json').exists():
        record=checked_environment()
        for row in record['namespace_checks'].values(): assert pin(Path(row['path']))==row
        return dict(status='ready',artifacts=[pin(S/'environment.json')],holds=[])
    source = P / '.venv/lib/python3.13/site-packages/data_sheets_schema.pth'
    before = pin(source)
    own = VENV / 'lib/python3.13/site-packages/data_sheets_schema.pth'
    backup=None
    if A.existing_venv:
        assert PYTHON.is_file() and own.is_file()
        assert own.read_text().strip()==str(W/'src'), 'supplied editable path must already select the assigned checkout'
        initial_pth=pin(own)
    else:
        if VENV.exists():
            raise ValueError('environment already exists; preserve it and use its saved record')
        run_cli('environment-apfs-clone', ['/bin/cp', '-cR', str(P / '.venv'), str(VENV)], timeout=1800)
        assert own.read_bytes() == source.read_bytes() and own.stat().st_ino != source.stat().st_ino
        backup = own.with_name(own.name+'.bak-fastpath-20261117')
        write(backup, own.read_bytes())
        own.write_text(str(W / 'src')+'\n')
        initial_pth=pin(own)
    assert pin(source) == before
    checker = R / 'scripts/adhoc/rehearse_clean_production_checkout_20261114.py'
    reports = {}
    for name, flags in (('default', ['-B']), ('safe-path', ['-P', '-s', '-B'])):
        result = run_cli('namespace-'+name, [str(PYTHON), *flags, str(checker), '--internal-check-namespace',
            '--checkout', str(W), '--repo', str(P)], cwd=S, timeout=600)
        value = json.loads(Path(result['stdout_path']).read_bytes())
        assert value['resolves_strictly_to_checkout_src'] and value['data_sheets_schema_is_pep420_namespace']
        assert not value['foreign_primary_entries_in_sys_path'] and value['raw_record_census']
        assert value['sys_prefix'] == str(VENV)
        save(S / ('namespace-'+name+'.json'), value)
        reports[name] = pin(S / ('namespace-'+name+'.json'))
    assert pin(own)==initial_pth and pin(source)==before
    record = dict(main_sha=A.main_sha, checkout=str(W), venv=str(VENV), interpreter=str(PYTHON),
        base_interpreter=str(PYTHON.resolve()), primary_pth=before, isolated_pth=pin(own), backup=pin(backup) if backup else None,
        environment_origin='supplied_existing_read_only' if A.existing_venv else 'apfs_clone_with_redirected_pth',
        submodule_setup_performed=False,fairscape_initialized=(W/'fairscape_models/.git').exists(),
        fairscape_gitlink=git(W,'rev-parse','HEAD:fairscape_models').decode().strip(),
        namespace_checks=reports, full_manifest_generated=False,
        retained_installation_metadata='Own RECORD/direct_url and console shebangs retain original install paths; invoke this Python explicitly. External base interpreter is unchanged.',
        undo='No environment edits were made.' if A.existing_venv else 'Restore only the cloned pth from its adjacent backup. Primary environment is unchanged.')
    save(S / 'environment.json', record)
    return dict(status='ready', artifacts=[pin(S / 'environment.json'), *reports.values()], holds=[])


def binary_copy():
    checked_environment()
    source = Path(C.get('binary_source', str(DEFAULT_SOURCE)))
    target = Path(C.get('durable_binary', str(DEFAULT_BINARY)))
    physical(source); physical(target)
    source_pin = pin(source)
    if not stat.S_ISREG(source.stat().st_mode) or not os.access(source, os.X_OK):
        raise ValueError('binary source must be an executable regular file')
    active = Path('/Users/marcin/.local/bin/claude')
    active_target = str(active.resolve()) if active.exists() else None
    recipe = [str(BASE_PYTHON), '-B', str(HERE), 'binary-copy', '--main-sha', A.main_sha,
        '--checkout', str(E/('native-production-'+A.main_sha[:12]) if A.dry_run else W),
        '--scratch', str(E/('native-fastpath-'+A.main_sha[:12]) if A.dry_run else S),
        '--config', str(A.config or S / 'production-inputs.DRAFT.json')]
    holds=[]
    if A.dry_run:
        holds.append('Binary copy was not run. Lead must choose and record updater/durable version; active updater differs from the runbook when reported below.')
        result = dict(source=source_pin, existing_copy=pin(target) if target.is_file() else None,
            active_updater=active_target, command=recipe, mode='commands_only_no_copy', source_selected_for_draft_only=True)
        template=S/'production-inputs.DRAFT.json'
        if not template.exists():
            save(template,dict(kind='DRAFT_NOT_PRODUCTION_CONFIGURATION',binary_source=str(source),durable_binary=str(target),
                gate_root=str(E/'codex-native-pin-comparison-20261113'),
                projects={name:{} for name in PROJECTS},
                missing_decisions=['Exact merged SHA and fresh production checkout/scratch','Binary version and durable copy',
                    'Accepted gate bundle and exact pins','System/account/config/admission choices','Live probe evidence',
                    'Quiet-host timing qualification','Timestamp archive and actual post-merge CI']))
        result['configuration_template']=pin(template)
    else:
        if 'binary_source' not in C or 'durable_binary' not in C:
            raise ValueError('explicit binary_source and durable_binary production choices required')
        if not target.is_relative_to(E / 'native-binary-durable') or target == source:
            raise ValueError('durable copy must be under the designated durable root')
        if not target.exists():
            write(target, source.read_bytes())
            target.chmod(0o755)
        copy = pin(target)
        assert copy['sha256'] == source_pin['sha256'] and copy['bytes'] == source_pin['bytes']
        assert stat.S_IMODE(target.stat().st_mode) == 0o755
        assert pin(source) == source_pin
        result = dict(source=source_pin, copy=copy, source_identity=dict(device=source.stat().st_dev,inode=source.stat().st_ino),
            copy_identity=dict(device=target.stat().st_dev,inode=target.stat().st_ino), native_executions=0)
    state(S / 'binary-copy.json', result)
    return dict(status='prepared_only' if A.dry_run else 'ready', artifacts=[pin(S / 'binary-copy.json')], holds=holds)


def probe_commands(project=None):
    project = selected_route()[0] if project is None else project
    directory = S / 'inputs'
    p = packet(project)
    authorization = str(C.get('authorization', directory / 'authorization.json'))
    provisional = str(C.get('provisional_runtime', directory / 'provisional-runtime.json'))
    observation_choice = str(C.get('observation_account_choice', directory / 'observation-account-choice.json'))
    permission_choice = str(C.get('permission_account_choice', directory / 'permission-account-choice.json'))
    runtime_choice = str(C.get('final_runtime_account_choice', directory / 'final-runtime-account-choice.json'))
    permission = str(C.get('permission_probe', S / 'probes/permission/permission-probe.json'))
    base = [str(PYTHON), '-P', '-B', '-m', 'data_sheets_schema.native_generation']
    return dict(observation=[*base,'observation-probe','--authorization',authorization,'--runtime',provisional,'--account-choice',observation_choice],
        permission=[*base,'bound-permission-probe','--authorization',authorization,'--expectation',str(p/'expectation/expectation.json'),'--account-choice',permission_choice],
        validate=[*base,'validate-probe-sequence','--runtime',str(p/'runtime/runtime.json'),'--probe',permission,'--account-choice',runtime_choice])


def model_label_args():
    version=getattr(A,'model_label_version',1)
    if type(version) is not int or version not in (1,2):
        raise ValueError('model label version must be an explicit 1 or 2')
    return [] if version==1 else ['--model-label-version',str(version)]


def observed_model_usage(runtime, terminal):
    from data_sheets_schema import native_model_aliases as aliases
    pair=aliases.model_aliases(runtime)
    aliases.require_model_usage(terminal,pair)
    return terminal['modelUsage'][aliases.reported_model(pair)]


def probe_prepare():
    project=selected_route()[0]
    require_route_config()
    checked_environment()
    binary = Path(C.get('durable_binary', str(DEFAULT_BINARY)))
    if not A.dry_run:
        copied = load(S / 'binary-copy.json')
        assert pin(binary) == copied['copy']
    out = S / 'inputs/probe-packet-draft'
    out.parent.mkdir(parents=True,exist_ok=True)
    run_cli('probe-draft', [str(PYTHON), '-P', '-B', str(W/'scripts/draft_native_probe_packet.py'),
        '--source-root',str(W),'--binary',str(binary),'--output',str(out),'--project',project,
        '--source-manifest',str(inputs(project)['source_manifest']),*model_label_args()])
    draft = load(out/'probe-packet.DRAFT.json')
    assert draft['project']==project and draft['no_execution'] is True
    actual_binary=pin(binary)
    assert all(draft['installed_binary_read_only'][key]==actual_binary[key] for key in ('path','bytes','sha256'))
    assert load(out/'provisional-runtime.DRAFT.json')['kind']=='DRAFT_NOT_A_RUNTIME'
    assert load(out/'authorization.DRAFT.json')['kind']=='DRAFT_NOT_AN_AUTHORIZATION'
    commands = probe_commands()
    required = ('provisional_runtime','authorization','observation_account_choice')
    holds = ['Finalize explicit '+name+' bytes; draft wrappers are intentionally invalid.' for name in required if name not in C]
    observation_ready=False
    if not holds:
        from data_sheets_schema import native_u4b_probe_sequence as probe
        from data_sheets_schema.native_generation import _account_choice
        from data_sheets_schema import native_shared_contract as contract
        for name in required: pin(Path(C[name]))
        runtime_raw=Path(C['provisional_runtime']).read_bytes()
        runtime=contract.strict_json(runtime_raw)
        if contract.canonical(runtime)!=runtime_raw: raise ValueError('provisional runtime must have canonical exact bytes before live probe')
        chosen=load(S/'binary-copy.json')['copy']
        assert pin(Path(chosen['path']))==chosen
        assert runtime['executable']['path']==chosen['path'] and runtime['executable']['sha256']==chosen['sha256']
        probe.authorization(Path(C['authorization']).read_bytes(), runtime)
        _account_choice(C['observation_account_choice'],Path(C['provisional_runtime']).read_bytes(),runtime)
        observation_ready=True
    phase_ready={}
    for name,subject in (('permission_account_choice',packet(project)/'expectation/expectation.json'),
                         ('final_runtime_account_choice',packet(project)/'runtime/runtime.json')):
        phase_ready[name]=False
        if name in C and subject.is_file():
            from data_sheets_schema.native_generation import _account_choice
            pin(Path(C[name])); raw=subject.read_bytes(); body=json.loads(raw)
            _account_choice(C[name],raw,body['runtime'] if name=='permission_account_choice' else body)
            phase_ready[name]=True
        else:
            holds.append('Finalize '+name+' after its exact saved subject exists.')
    prefix_ready=(packet(project)/'prefix-verification.json').is_file()
    if prefix_ready:
        for row in load(packet(project)/'prefix-verification.json')['artifacts']:
            assert pin(Path(row['path']))==row
    else:
        holds.append('Build and verify the '+project+' input prefix before the lead executes observation-probe.')
    operation='register-project' if route_fields() else 'register-chorus'
    result = dict(commands=commands, command_text={k:command_text(v) for k,v in commands.items()},
        commands_executed=False, prerequisite_order=[operation+' prefix','lead observation',operation+' intermediates',
            'lead bound permission','offline validate-probe-sequence',operation+' finalization'],
        saved_sequence_instruction='Set projects.'+project+'.probe_sequence to the raw sequence.json named by validate-probe-sequence stdout result.sequence.path, not to redirected CLI stdout.',
        observed_limit_required=64000, observed_limit_verified=False,
        observation_inputs_ready=observation_ready, later_phase_choices_ready=phase_ready,
        input_prefix_ready=prefix_ready, observation_phase_ready=observation_ready and prefix_ready,
        final_inputs_ready=observation_ready and prefix_ready and all(phase_ready.values()), draft_artifacts=[pin(path) for path in sorted(out.iterdir())])
    result.update(route_fields())
    state(S/'probe-prepare.json',result)
    print(json.dumps(result['command_text'],indent=2),flush=True)
    return dict(status='prepared_only',artifacts=[pin(S/'probe-prepare.json'),*result['draft_artifacts']],holds=holds+['Lead runs the two live probe commands; this driver never executes them.'],**route_fields())


def prefix(project):
    p=packet(project); p.mkdir(parents=True,exist_ok=True)
    result_path=p/'prefix-verification.json'
    conf=C.get('projects',{}).get(project,{})
    if not A.dry_run:
        missing=[key for key in ('attempt_directory','registration_id','label') if key not in conf]
        if missing: raise ValueError('production prefix choices required before freezing: '+', '.join(missing))
    attempt=Path(conf.get('attempt_directory',str(S/'never-launched-attempts'/project/('FASTPATH-'+project))))
    stage=attempt/'stages'
    command=[str(PYTHON),'-P','-B',str(W/'scripts/build_native_canary_packet.py'),'--checkout',str(W),
        '--output',str(p/'input-prefix'),'--stage-root',str(stage),'--project',project,'--profile','bridge2ai',
        '--registration-id',conf.get('registration_id',('OFFLINE-FASTPATH-' if A.dry_run else 'FASTPATH-')+project),
        '--label','OFFLINE-FASTPATH-NOT-LAUNCH-AUTHORITY' if A.dry_run else conf.get('label','post-merge-native')]
    for name,path in inputs(project).items():
        pin(path)
        command+=['--'+name.replace('_','-'),str(path)]
    if result_path.exists():
        previous=load(result_path)
        assert previous['command']['requested_argv']==command, 'prefix choices changed; preserve packet and start a fresh approved packet'
        for item in previous['artifacts']: assert pin(Path(item['path']))==item
        return
    outcome=run_cli('prefix-'+project,command,expected=(2,),timeout=1800)
    assert load(p/'input-prefix/status.json')['status']=='dependency_stop'
    files=[pin(p/'input-prefix'/name) for name in ('receipt-policy.json','selection.json','environment-manifest.json','input-inventory.json','status.json')]
    assert not attempt.exists()
    save(result_path,dict(artifacts=files,command=outcome,attempt_root_absent=True))
    # Adapter only for the retained dry fixture producer; the real prefix CLI above produced these bytes.
    if A.dry_run:
        save(p/'prefix-result.json',dict(returncode=2,artifacts={Path(row['path']).name:row for row in files}))


def saved_step(project,step,data):
    p=packet(project); source=p/(step+'-inputs.json'); out=p/step
    verify=p/(step+'-verification.json')
    if verify.exists():
        previous=load(verify)
        assert load(source)==data
        assert previous['dependency_pins']==dependency_pins(data), 'saved-step input dependency bytes changed'
        for row in previous['artifacts']:
            assert pin(Path(row['path']))==row
        return out
    save(source,data)
    result=run_cli('saved-'+project+'-'+step,[str(PYTHON),'-P','-B',str(W/'scripts/native_canary_saved_step.py'),
        '--checkout',str(W),'--step',step,'--inputs',str(source),'--output',str(out)],timeout=1800)
    names={'runtime':['runtime.json'],'preparation':['preparation.json','instruction.md'],
        'composition':['composition.json'],'expectation':['expectation.json'],'registration':['registration.json']}[step]
    save(verify,dict(command=result,inputs=pin(source),dependency_pins=dependency_pins(data),artifacts=[pin(out/name) for name in names]))
    return out


def dependency_pins(value):
    rows={}
    def visit(item):
        if isinstance(item,dict):
            for nested in item.values(): visit(nested)
        elif isinstance(item,list):
            for nested in item: visit(nested)
        elif isinstance(item,str) and item.startswith('/'):
            path=Path(item)
            if path.is_file(): rows[item]=pin(path)
    visit(value)
    return rows


def production_chain(project):
    conf=C.get('projects',{}).get(project,{})
    missing_prefix=[key for key in ('attempt_directory','registration_id','label') if key not in conf]
    if missing_prefix: return ['Supply projects.'+project+'.'+key+' before creating the prefix' for key in missing_prefix]
    prefix(project)
    p=packet(project); conf=C.get('projects',{}).get(project,{})
    required=('runtime_inputs','system_path','job_id','run_date','attempt_id','attempt_directory','evidence_directory','max_draft_checks')
    missing=[key for key in required if key not in conf]
    if missing:
        return ['Supply projects.'+project+'.'+key for key in missing]
    runtime_inputs=load(Path(conf['runtime_inputs']))
    from data_sheets_schema import native_u4b_probe_sequence as probes
    observed=probes.validate_observation(runtime_inputs['arguments']['observation_probe_path'])
    selected=load(S/'binary-copy.json')
    assert pin(Path(selected['copy']['path']))==selected['copy']
    executable=observed['provisional_runtime']['executable']
    assert executable['path']==selected['copy']['path'] and executable['sha256']==selected['copy']['sha256']
    assert observed['authorization_sha256']==pin(Path(C['authorization']))['sha256']
    from data_sheets_schema import native_shared_contract as contract
    assert contract.canonical(observed['provisional_runtime'])==Path(C['provisional_runtime']).read_bytes()
    transcript=Path(observed['transcript']['path']).read_bytes()
    terminal=json.loads(transcript.splitlines()[-1])
    limit=observed_model_usage(observed['provisional_runtime'],terminal)['maxOutputTokens']
    if type(limit) is not int or limit<64000:
        raise ValueError('live observed maxOutputTokens is below 64000')
    floor=p/'observed-output-floor.json'
    if not floor.exists(): save(floor,dict(observation=observed['pin'],maxOutputTokens=limit,passed=True))
    runtime=saved_step(project,'runtime',runtime_inputs)
    preparation=saved_step(project,'preparation',dict(selection_path=str(p/'input-prefix/selection.json'),
        runtime_path=str(runtime/'runtime.json'),environment_manifest_path=str(p/'input-prefix/environment-manifest.json'),
        job_id=conf['job_id'],run_date=conf['run_date'],max_draft_checks=conf['max_draft_checks']))
    composition=saved_step(project,'composition',dict(preparation_path=str(preparation/'preparation.json'),instruction_path=str(preparation/'instruction.md')))
    system=str(Path(conf['system_path']))
    expectation=saved_step(project,'expectation',dict(composition_path=str(composition/'composition.json'),system_path=system,
        config_directory=str(Path(conf['attempt_directory'])/'cli_config')))
    if 'permission_probe' not in conf:
        return ['Run the prepared bound-permission command, then supply projects.'+project+'.permission_probe.']
    if 'probe_sequence' not in conf:
        return ['Run offline validate-probe-sequence; set projects.'+project+'.probe_sequence to its stdout result.sequence.path (the raw sequence.json), not the redirected CLI stdout envelope.']
    verified_sequence=probes.validate_bound_probe(load(runtime/'runtime.json'),conf['permission_probe'])
    assert verified_sequence['checked'] is True and verified_sequence['passed'] is True
    assert pin(Path(conf['probe_sequence']))==verified_sequence['sequence'], 'configured sequence differs from validated bound sequence'
    frozen_expectation=Path(observed['sequence_directory'])/'expectation.json'
    assert frozen_expectation.read_bytes()==(expectation/'expectation.json').read_bytes(), 'bound permission used another expectation'
    registration=saved_step(project,'registration',dict(composition_path=str(composition/'composition.json'),system_path=system,
        permission_probe_path=conf['permission_probe'],attempt_id=conf['attempt_id'],attempt_directory=conf['attempt_directory'],
        evidence_directory=conf['evidence_directory'],max_draft_checks=conf['max_draft_checks']))
    from data_sheets_schema.native_shared_registration_orchestration import verified
    verified((registration/'registration.json').read_bytes())
    return []


def rehearsal_chain(project):
    prefix(project)
    b,chain,_=support()
    if (packet(project)/'chain-result.json').exists():
        record=load(packet(project)/'chain-result.json'); assert pin(Path(record['registration']['path']))==record['registration']
        return
    # Existing test utilities fabricate observations and permissions; never used in production mode.
    chain.chain(project)
    assert load(packet(project)/'chain-result.json')['live_acceptance'] is False


def run_registered(project):
    if A.dry_run:
        prefix(project)
        run_cli('rehearsal-chain-'+project,[str(PYTHON),'-P','-B',str(HERE),'register-project' if route_fields() else 'register-chorus',*common_args(),
            '--internal-chain',project],timeout=3600)
        return []
    return production_chain(project)


def effective_native_limits(project):
    """Read exact registered limits and their selected source profile; never rewrite them."""
    from data_sheets_schema import native_runtime_profiles as profiles
    from data_sheets_schema import native_run_limits as run_limits
    from data_sheets_schema import native_shared_runtime_values as values
    from data_sheets_schema import native_u4b_policy as policy
    from data_sheets_schema import native_shared_permission_protocol as protocol
    from data_sheets_schema import native_subscription_guard_v2 as subscription
    from data_sheets_schema import native_admission_timer as admission_timer
    modules=(profiles,run_limits,values,policy,protocol,subscription,admission_timer)
    source_pins={}
    for source in modules:
        path=Path(source.__file__).resolve()
        assert path.is_relative_to(W/'src/data_sheets_schema'), 'native limits imported from another checkout'
        source_pins[path.name]=pin(path)
    p=packet(project)
    paths=dict(registration=p/'registration/registration.json',runtime=p/'runtime/runtime.json',
        composition=p/'composition/composition.json',expectation=p/'expectation/expectation.json')
    before={name:pin(path) for name,path in paths.items()}
    body=load(paths['registration'])['registration']
    runtime=body['runtime']
    assert load(paths['runtime'])==runtime
    assert paths['composition'].read_bytes()==body['composition_raw_json'].encode()
    assert before['composition']['sha256']==body['composition_sha256']
    composed=load(paths['composition']); expected=load(paths['expectation'])
    assert expected['runtime']==runtime
    history=composed['policy']['pretool_control']
    assert expected['policy']['pretool_control']==history==protocol.history_contract()
    paths['permission_probe']=Path(body['permission_probe'])
    permission_pin=pin(paths['permission_probe'])
    assert permission_pin['sha256']==body['permission_probe_sha256']
    permission=load(paths['permission_probe'])
    assert permission['binding']['policy']['pretool_control']==history
    assert permission['binding']['runtime']==runtime
    profile=profiles.profile_name(runtime)
    if profile==profiles.PRODUCTION_PROFILE:
        selected_pair=run_limits.require_registered_pair(runtime)
    else:
        profiles.require_synthetic_declarations(runtime)
        selected_pair=(runtime['budget_guard_usd'],runtime['deadline_seconds'])
    values.require_bash_timeouts(runtime['environment'])
    bash={key:runtime['environment'][key] for key in values.BASH_TIMEOUT_ENV}
    assert bash==values.BASH_TIMEOUT_ENV
    assert all(body['environment'][key]==value for key,value in bash.items())
    admission=policy.registered_policy(runtime)
    assert admission['max_age_seconds']<=subscription.MAX_AGE_SECONDS
    basis=json.loads(runtime['limits_basis'])
    probe_limits=None
    observed_pin=basis.get('observation_probe')
    if type(observed_pin) is dict and 'path' in observed_pin:
        paths['observation_probe']=Path(observed_pin['path'])
        assert pin(paths['observation_probe'])==observed_pin
        observed=load(paths['observation_probe'])
        if type(observed.get('authorization')) is dict:
            authorized_pin=observed['authorization']
            paths['probe_authorization']=Path(authorized_pin['path'])
            assert pin(paths['probe_authorization'])==authorized_pin
            authorization=load(paths['probe_authorization'])
            probe_limits={key:authorization[key] for key in ('observation_deadline_seconds','permission_deadline_seconds')}
    if profile==profiles.PRODUCTION_PROFILE:
        assert probe_limits is not None, 'registered production-shaped probe authorization is required'
    result=dict(project=project,main_sha=A.main_sha,profile=profile,dry_run_fabricated_evidence=A.dry_run,
        native_acceptance=False,selected_budget_deadline_pair=list(selected_pair),
        deadline_seconds=runtime['deadline_seconds'],budget_guard_usd=runtime['budget_guard_usd'],
        bash_timeouts_ms=bash,model_limits=runtime['limits'],admission_policy=admission,
        pretool_control=history,probe_authorization_limits=probe_limits,
        source_catalog=dict(registered_budget_deadline_pairs=[list(pair) for pair in run_limits.REGISTERED_PAIRS],
            synthetic_deadline_seconds=profiles.SYNTHETIC_DEADLINE_SECONDS,
            bash_timeout_environment=values.BASH_TIMEOUT_ENV,admission_terms=policy.TERM_VALUES,
            usage_max_age_ceiling_seconds=subscription.MAX_AGE_SECONDS,
            admission_watchdog_seconds=admission_timer.ADMISSION_SECONDS,pretool_control=protocol.history_contract()),
        artifacts={name:pin(path) for name,path in paths.items()},source_profiles=source_pins,
        source_profile_equalities_checked=True,
        scope='Effective values from saved registration and selected checkout. Offline process watchdogs are separate. No native limit is inferred, copied from another branch, or rewritten.')
    assert all(pin(paths[name])==row for name,row in before.items())
    assert all(pin(Path(row['path']))==row for row in source_pins.values())
    target=p/'effective-native-limits.json'
    if target.exists(): assert load(target)==result, 'registered limits or profile source changed'
    else: save(target,result)
    return pin(target)


def register_chorus():
    if selected_route()!=('CHORUS',1):
        raise ValueError('register-chorus is restricted to CHORUS rep1; use register-project')
    return register_project()


def register_project():
    require_route_config()
    project=selected_route()[0]
    checked_environment()
    holds=run_registered(project)
    p=packet(project)
    if holds:
        return dict(status='dependency_stop',artifacts=[pin(p/'prefix-verification.json')] if (p/'prefix-verification.json').exists() else [],holds=holds,lead_commands=probe_commands(),**route_fields())
    verify_actual_project(p/'registration/registration.json')
    artifacts=[pin(p/'registration/registration.json'),effective_native_limits(project)]
    if A.dry_run:
        artifacts.append(pin(p/'PLACEHOLDERS.json'))
        holds=['Registration is an offline placeholder proposal; observation, permission, D92/N1.8 qualification, archive and post-merge CI are not established.']
    else:
        for name in ('qualification','registration_commit','ci'):
            if name not in C:
                holds.append('Supply verified '+name+' evidence before review.')
        if 'registration_commit' in C:
            run_cli('registration-archive-verify',[str(PYTHON),'-P','-B',str(W/'scripts/native_registration_timestamp.py'),
                '--registration',str(p/'registration/registration.json'),'--verify-evidence',C['registration_commit']])
    result=dict(status='dry_run_registration_verified' if A.dry_run else ('dependency_stop' if holds else 'registration_ready_for_gate'),
        artifacts=artifacts,holds=holds,live_acceptance=False,**route_fields())
    state(registration_state(),result)
    return result


def gate_sources():
    root=Path(C.get('gate_root',str(E/'codex-native-pin-comparison-20261113')))
    if not A.dry_run and ('gate_root' not in C or 'gate_expected_pins' not in C):
        raise ValueError('lead-selected approved gate_root and gate_expected_pins are required')
    pins={name:pin(root/'scripts'/name) for name in GATE_NAMES}
    if 'gate_expected_pins' in C:
        expected=load(Path(C['gate_expected_pins']))['tools']
        assert expected==pins, 'gate tools differ from approved exact pins'
    return root,pins


def gate_check(project):
    import yaml
    root,tools=gate_sources()
    gate_root=packet(project)/'np15'; gate_root.mkdir(exist_ok=True)
    index=1
    while (gate_root/f'attempt-{index:03d}').exists(): index+=1
    out=gate_root/f'attempt-{index:03d}'; out.mkdir()
    tuples={}
    manifest=yaml.safe_load(inputs(project)['source_manifest'].read_bytes())
    for name in PROJECTS:
        paths=inputs(name)
        tuples[name]={key:pin(paths[key])['sha256'] for key in ('source_manifest','bundle','chunk_manifest')}
        tuples[name]['omission_context']=pin(paths['context'])['sha256']
        tuples[name]['scope']=digest(encode(manifest['scope'][name]))
    save(out/'tuples.json',dict(kind='d4d_native_np1b_input_tuples',schema_version=1,projects=tuples))
    save(out/'floor.json',dict(kind='d4d_native_gate_floor_input',schema_version=1,coverage_floor=dict(state='pending',mode='diagnostic_pilot')))
    save(out/'expected-tools.json',dict(kind='d4d_native_gate_expected_tool_pins',schema_version=1,tools=tools))
    registrations={side:packet(name)/'registration/registration.json' for side,name in (('reference','CHORUS'),('candidate',project))}
    command=[str(PYTHON),'-I','-B',str(root/'scripts/native_registration_pin_gate.py'),
        '--reference',str(registrations['reference']),'--candidate',str(registrations['candidate']),
        '--tuple',str(out/'tuples.json'),'--floor',str(out/'floor.json'),'--expected-tool-pins',str(out/'expected-tools.json'),
        '--reference-root',str(W),'--python',str(PYTHON),'--dependency-prefix',str(VENV),
        '--dependency-root',str(VENV/'lib/python3.13/site-packages'),'--timeout-seconds','1800',
        '--output',str(out/'gate'),'--source-bound-validation']
    if A.dry_run:
        marks=dict(kind='d4d_native_gate_synthetic_probe_marks',schema_version=1,branch='i',scope='OFFLINE FASTPATH FABRICATED TEST EVIDENCE; NO NATIVE ACCEPTANCE')
        for side,path in registrations.items():
            body=load(path)['registration']; prep=json.loads(body['preparation_raw_json'])['registration']
            marks[side]=dict(registration=pin(path),selection=prep['selection'],
                permission_probe=dict(path=body['permission_probe'],sha256=body['permission_probe_sha256']),own_selection_required=True)
        save(out/'synthetic-marks.json',marks)
        command+=['--synthetic-probe-marks',str(out/'synthetic-marks.json')]
    audit=root/'scripts/adhoc/h3_gate_parent_launch_20261113.py'
    audit_pin=pin(audit)
    protocol=module('fastpath_gate_protocol',root/'scripts/native_registration_validation_protocol.py')
    environments=[protocol.clean_environment(load(path)['registration']['environment']) for path in registrations.values()]
    snapshots={}
    for name,row in tools.items():
        target=out/'sources'/name
        write(target,Path(row['path']).read_bytes()); target.chmod(0o444)
        assert pin(target)['sha256']==row['sha256']
        snapshots[name]=pin(target)
    write(out/'parent-audit.source',audit.read_bytes())
    plan=dict(gate_root=str(root),argv=command,tools=tools,snapshots=snapshots,audit=audit_pin,
        audit_snapshot=pin(out/'parent-audit.source'),production_validation=dict(checkout_root=str(W),python=str(PYTHON),
            profile=str(out/'gate/validation-readonly.sb'),environments=environments),output=str(out/'gate'))
    save(out/'parent-plan.json',plan)
    # The reviewed parent audit replaces an inherited OS profile: the validation worker installs its own sandbox.
    invocation=run_cli('np15-'+project+'-'+str(index),[str(PYTHON),'-I','-S','-B',str(HERE),'preflight-all',*common_args(),
        '--internal-gate',str(out/'parent-plan.json')],expected=(0,1,2,77),timeout=2000,sandbox=False,cwd=root)
    result=load(out/'gate/comparison-result.json') if (out/'gate/comparison-result.json').is_file() else dict(status='no_saved_result')
    assert all(pin(root/'scripts'/name)==row for name,row in tools.items()), 'gate source changed during comparison'
    save(out/'result.json',dict(status=result['status'],invocation=invocation,tools=tools,
        provisional_gate_bundle=A.dry_run and 'gate_expected_pins' not in C,
        native_acceptance=False,result=pin(out/'gate/comparison-result.json') if (out/'gate/comparison-result.json').is_file() else None))
    state(gate_root/'result.json',dict(**load(out/'result.json'),attempt_evidence=pin(out/'result.json')))
    return load(gate_root/'result.json')


def internal_gate(path):
    plan=load(path)
    for name,row in plan['tools'].items():
        assert pin(Path(row['path']))==row
        assert pin(Path(plan['snapshots'][name]['path']))==plan['snapshots'][name]
    audit_raw=Path(plan['audit_snapshot']['path']).read_bytes()
    assert digest(audit_raw)==plan['audit']['sha256']
    code=Path(plan['snapshots']['native_registration_pin_gate.py']['path']).read_bytes()
    namespace=dict(__name__='fastpath_reviewed_parent_audit',__file__=plan['audit']['path'])
    exec(compile(audit_raw,plan['audit']['path'],'exec'),namespace)
    sys.argv=plan['argv'][3:]
    namespace['install_parent_audit']('gate',source_root=plan['gate_root'],
        code_inputs={'scripts/'+name:row for name,row in plan['tools'].items()},write_roots=[plan['output']],
        python_paths=[plan['argv'][0]],production_validation=plan['production_validation'])
    exec(compile(code,plan['tools']['native_registration_pin_gate.py']['path'],'exec'),
        dict(__name__='__main__',__file__=plan['tools']['native_registration_pin_gate.py']['path']))


def sizing(project):
    run_cli('sizes-'+project,[str(PYTHON),'-P','-B',str(HERE),'preflight-all',*common_args(),'--internal-size',project],timeout=1200)
    path=packet(project)/'sizing.json'
    check=packet(project)/'sizing-verification.json'
    if check.exists(): assert load(check)==pin(path)
    else: save(check,pin(path))
    return load(path)


def verified_basic_sizing(project, sizes):
    """Resume only complete, source-bound basic evidence; never overwrite its exclusive outputs."""
    path=packet(project)/'sizing.json'
    receipt=packet(project)/'basic-sizing-verification.json'
    resumed_failure=None
    if not path.exists():
        sizes.measure(project)
    elif receipt.exists():
        assert load(receipt)['sizing']==pin(path), 'basic sizing changed after verification'
    else:
        label='sizes-'+project
        failed=S/'commands'/label
        assert label in A.retry_command, 'unsealed existing basic sizing requires explicit reviewed retry'
        assert load(failed/'result.json')['returncode']==1
        assert 'retained scaffold assumptions need explicit adaptation' in (failed/'stderr.txt').read_text()
        resumed_failure=dict(command=pin(failed/'result.json'),stderr=pin(failed/'stderr.txt'),
            finding='FP-16: driver compared declared response limit to the smaller effective typed response limit; no production bound changed.')
    measured=load(path)
    assert measured['project']==project and measured['head']==A.main_sha
    from data_sheets_schema import native_shared_selection as selection
    from data_sheets_schema import native_shared_contract as contract
    assert measured['stratum_bounds']==selection.capture(packet(project)/'input-prefix/selection.json').bounds()
    assert measured['hard_limits']==dict(contract.HARD_LIMITS)
    checked=[]
    def visit(value):
        if isinstance(value,dict):
            if all(key in value for key in ('path','bytes','sha256')):
                actual=pin(Path(value['path']))
                assert all(actual[key]==value[key] for key in actual), 'sizing artifact pin changed'
                checked.append(actual)
            for child in value.values(): visit(child)
        elif isinstance(value,list):
            for child in value: visit(child)
    visit(measured)
    for name,source in inputs(project).items():
        actual=pin(source)
        assert all(measured['inputs'][name][key]==value for key,value in actual.items())
    if not receipt.exists():
        save(receipt,dict(sizing=pin(path),references=checked,resumed_failure=resumed_failure))
    return measured


def preflight_all():
    require_route_config()
    checked_environment()
    if not A.dry_run:
        project=selected_route()[0]
        actual=packet(project)/'registration/registration.json'
        assert actual.is_file()
        verify_actual_project(actual)
        cohort=S/'offline-preflight-candidates'
        args=['--main-sha',A.main_sha,'--checkout',str(W),'--scratch',str(cohort),'--dry-run']
        if A.existing_venv: args+=['--existing-venv',str(VENV)]
        if A.config: args+=['--config',str(A.config)]
        run_cli('offline-five-project-candidates',[str(PYTHON),'-P','-B',str(HERE),'preflight-all',*args,
            '--internal-cohort',str(S/'environment.json')],expected=(0,2),timeout=9600,sandbox=False)
        result=load(cohort/'preflight-all.json')
        result['actual_registration' if route_fields() else 'actual_chorus_registration']=pin(actual)
        result.update(route_fields())
        result['offline_candidate_root']=str(cohort)
        result['holds'].append(actual_reference_hold())
        result['status']='hold'
        state(S/'preflight-all.json',result)
        return dict(status='hold',artifacts=[pin(S/'preflight-all.json')],holds=result['holds'],**route_fields())
    if route_fields():
        raise ValueError('five-project synthetic cohort requires its separate legacy candidate route')
    assert (packet('CHORUS')/'registration/registration.json').is_file(), 'CHORUS must complete before fan-out'
    chorus=load(S/'chorus-registration.json')
    for row in chorus['artifacts']: assert pin(Path(row['path']))==row
    rows=[]; holds=[]
    # CHORUS is the real builder/saved-step canary. Verify sizing before the serial remainder.
    for project in PROJECTS:
        started=time.monotonic()
        pending=[] if project=='CHORUS' else run_registered(project)
        if pending:
            rows.append(dict(project=project,status='dependency_stop',holds=pending,elapsed_seconds=time.monotonic()-started))
            holds.extend(pending); break
        limits=effective_native_limits(project)
        measured=sizing(project)
        output_sizing=load(packet(project)/'output-size-scenarios.json')
        native_scenario=next(row for row in output_sizing['scenarios'] if row['partition']=='native_candidate')
        rows.append(dict(project=project,registration=pin(packet(project)/'registration/registration.json'),
            native_limits=limits,
            sizing=pin(packet(project)/'sizing.json'),elapsed_seconds=time.monotonic()-started,
            native_partition=measured['partitions']['native_candidate']['verdict'],
            input_envelope=measured['input_envelope_scenario']['verdict'],
            native_inner_request=measured['native_inner_request_scenarios']['verdict'],
            response_caps=measured['response_caps'],
            largest_retained_write_bytes=measured['largest_retained_single_write']['bytes'],
            output_scenarios=pin(packet(project)/'output-size-scenarios.json'),
            hypothetical_native_write_arguments_bytes=native_scenario.get('largest',{}).get('write_argument_bytes'),
            hypothetical_token_headroom_at_2_48=native_scenario.get('largest',{}).get('token_headroom_at_2_48'),
            hypothetical_response_byte_headroom=min((row['response_byte_headroom'] for row in native_scenario.get('workers',[])),default=None),
            native_first_request=output_sizing['native_first_request']['status'],
            native_first_request_detail=output_sizing['native_first_request']))
        outer=output_sizing['native_first_request']
        if outer['status']!='measured_scenario':
            holds.append(project+' retained-record native outer request is '+outer['status']+'; first-request fit is not established'+(': '+outer['reason'] if outer.get('reason') else '.'))
        elif outer.get('uncached_lexical_guard',{}).get('verdict')!='pass':
            holds.append(project+' hypothetical native outer request failed lexical admission: '+str(outer.get('uncached_lexical_guard')))
        if rows[-1]['hypothetical_token_headroom_at_2_48'] is not None and rows[-1]['hypothetical_token_headroom_at_2_48']<0:
            holds.append(project+' hypothetical full-text Write scaffold exceeds the 64000 output placeholder at 2.48 bytes/token; actual output fit and any bound choice remain unresolved.')
        if rows[-1]['hypothetical_response_byte_headroom'] is not None and rows[-1]['hypothetical_response_byte_headroom']<0:
            holds.append(project+' hypothetical response content exceeds the effective typed-response byte cap.')
        if measured['partitions']['native_candidate']['verdict']!='pass':
            holds.append(project+' native partition refused')
        if measured['input_envelope_scenario']['verdict']!='pass':
            holds.append(project+' complete native input envelope is not certified by component sizing')
        if measured['native_inner_request_scenarios']['verdict']!='pass':
            holds.append(project+' retained-record typed request: '+measured['native_inner_request_scenarios']['verdict'])
    gate_rows=[]
    if len(rows)==len(PROJECTS):
        # First prove self-comparison, then AI_READI, before repeating the expensive comparison.
        for project in PROJECTS:
            try:
                result=gate_check(project)
                gate_rows.append(dict(project=project,status=result['status'],evidence=str(packet(project)/'np15/result.json')))
                if result.get('provisional_gate_bundle'):
                    hold='NP1.5 tool bundle is provisional local source; no lead-approved exact gate pins were supplied.'
                    if hold not in holds: holds.append(hold)
                if result['status']!='equal':
                    holds.append('NP1.5 '+project+' '+result['status']+'; later gate comparisons not run after failed canary')
                    break
            except Exception as exc:
                gate_rows.append(dict(project=project,status='refused',reason=type(exc).__name__+': '+str(exc)))
                holds.append('NP1.5 canary failed; later gate comparisons not run')
                break
    if A.dry_run:
        holds.append('All registrations contain explicit fabricated probe evidence; live binary output floor remains unverified.')
    result=dict(status='hold' if holds else 'ready',order=list(PROJECTS),projects=rows,gates=gate_rows,holds=holds,
        native_acceptance=False,shared_bounds_changed=False)
    state(S/'preflight-all.json',result)
    return dict(status=result['status'],artifacts=[pin(S/'preflight-all.json')],holds=holds)


def reviewer_kinds_for(pair):
    if type(pair) is not str or pair not in REVIEWER_PAIRS:
        raise ValueError('reviewer-pair must be codex-agy or codex-claude')
    return REVIEWER_PAIRS[pair]


def review_packets():
    require_route_config()
    actual_project=selected_route()[0]
    pair=getattr(A,'reviewer_pair','codex-agy')
    reviewer_kinds=reviewer_kinds_for(pair)
    preflight=load(S/'preflight-all.json')
    registered=load(registration_state())
    if route_fields():
        for document in (preflight,registered):
            assert encode(document.get('cell_route'))==encode(route_fields()['cell_route']), 'saved review input route differs'
        actual=packet(actual_project)/'registration/registration.json'
        assert pin(actual)==preflight['actual_registration'], 'actual registration differs from preflight'
        verify_actual_project(actual)
    holds=list(preflight['holds'])
    holds.extend(registered.get('holds',[]))
    common={}
    required=('input-prefix/receipt-policy.json','input-prefix/selection.json','input-prefix/environment-manifest.json',
        'runtime/runtime.json','preparation/preparation.json','preparation/instruction.md','composition/composition.json',
            'expectation/expectation.json','registration/registration.json','effective-native-limits.json')
    candidate_root=Path(preflight.get('offline_candidate_root',str(S)))
    for project in PROJECTS:
        p=candidate_root/'packets'/project
        for relative in required:
            if not (p/relative).is_file(): holds.append('Missing required candidate artifact '+project+'/'+relative)
        for relative in ('input-prefix/receipt-policy.json','input-prefix/selection.json','input-prefix/environment-manifest.json',
            'runtime/runtime.json','preparation/preparation.json','preparation/instruction.md','composition/composition.json',
            'expectation/expectation.json','registration/registration.json','sizing.json','output-size-scenarios.json',
            'hypothetical-native-first-request.json','PLACEHOLDERS.json','np15/result.json','effective-native-limits.json',
            'basic-sizing-verification.json','sizing-verification.json'):
            path=p/relative
            if path.is_file(): common[project+'/'+relative]=pin(path)
        basic=p/'basic-sizing-verification.json'
        if basic.is_file():
            resumed=load(basic).get('resumed_failure') or {}
            for name in ('command','stderr'):
                if name in resumed:
                    common[project+'/sizing-retry-evidence/'+name+('.json' if name=='command' else '.txt')]=resumed[name]
        for path in sorted((p/'hypothetical-single-write').glob('*.json')):
            common[project+'/hypothetical-single-write/'+path.name]=pin(path)
        for path in sorted((p/'np15').rglob('*')) if (p/'np15').exists() else ():
            if path.is_file() and path.stat().st_size:
                common[project+'/np15/'+str(path.relative_to(p/'np15'))]=pin(path)
        gate=p/'np15/result.json'
        if gate.is_file():
            comparison=load(gate).get('result')
            if comparison:
                assert pin(Path(comparison['path']))==comparison
                validation=load(Path(comparison['path'])).get('reference_validation') or {}
                refusal=validation.get('refusal') or {}
                if refusal:
                    holds.append('NP1.5 '+project+' stopped during '+str(refusal.get('phase'))+': '+str(refusal.get('error_type'))+
                        '. See its pinned comparison result; no fresh production validation was accepted.')
                if refusal.get('error_type')=='FileNotFoundError' and 'native_registration_validation_worker.py' in refusal.get('reason',''):
                    holds.append('The selected external gate requires matching validation-worker source inside the registered checkout, where it is absent. No supported CLI override exists; the lead must resolve gate packaging before a fresh manifest capture. Do not add files to this frozen checkout.')
        registration=p/'registration/registration.json'
        if registration.is_file():
            body=load(registration)['registration']
            permission=Path(body['permission_probe'])
            common[project+'/bound-permission.json']=pin(permission)
        limits=p/'effective-native-limits.json'
        if limits.is_file():
            for name,row in load(limits)['artifacts'].items():
                if name in ('observation_probe','probe_authorization'):
                    common[project+'/native-limit-evidence/'+name+'.json']=row
    for relative in required:
        path=packet(actual_project)/relative
        if path.is_file(): common['actual-'+actual_project+'/'+relative]=pin(path)
        else: holds.append('Missing actual '+actual_project+' artifact '+relative)
    actual_limits=packet(actual_project)/'effective-native-limits.json'
    if actual_limits.is_file():
        for name,row in load(actual_limits)['artifacts'].items():
            if name in ('observation_probe','probe_authorization'):
                common['actual-'+actual_project+'/native-limit-evidence/'+name+'.json']=row
    common['source/native_launch_sequence.py']=pin(W/'src/data_sheets_schema/native_launch_sequence.py')
    for row in load(packet(actual_project)/'effective-native-limits.json')['source_profiles'].values():
        common['source/native-limits/'+Path(row['path']).name]=row
    common['preflight-all.json']=pin(S/'preflight-all.json')
    for name in ('qualification','registration_commit','ci','permission_probe'):
        if name in C:
            common['external/'+name+'.json']=pin(Path(C[name]))
            if name in ('qualification','ci'):
                holds.append(name+' evidence is supplied for independent review; this driver does not certify its substantive qualification.')
        else:
            holds.append('Missing real '+name+' evidence for independent reviews')
    for name in ('system_path',):
        value=C.get('projects',{}).get(actual_project,{}).get(name)
        if value: common['external/'+name]=pin(Path(value))
        elif A.dry_run:
            common['OFFLINE-system.md']=pin(S/'OFFLINE-PLACEHOLDERS/system.md')
            holds.append('Production system.md and account/config choices remain unset')
    root=S/'reviews'; root.mkdir()
    manifests=[]
    for reviewer in reviewer_kinds:
        dest=root/reviewer; dest.mkdir()
        copies={}
        for name,row in common.items():
            target=dest/'artifacts'/name
            copies[name]=dict(source=row,copy=copy_pinned(row,target))
        instructions=('Review packet prepared offline; no review has been performed or approved.\n'
            'Reviewer kind: '+reviewer+'\n'
            'Verify source, all pins, observed output limit at least 64000, D92/N1.8 qualification, timestamp archive, post-merge CI, and all-five preflight.\n'
            'Explicitly confirm that the first v3 registration gate regenerates and checks the environment manifest against the live environment.\n'
            'Verify effective-native-limits.json against the registered runtime and selected source profiles, including D159 on the merged checkout. The bc61 rehearsal preserves its older values and is not D159 qualification.\n'
            'Selected reviewer pair: '+pair+'; exactly one '+reviewer_kinds[0]+' and one '+reviewer_kinds[1]+'. No reviewer is relabeled.\n'
            + ('Selected cell: '+actual_project+' rep'+str(selected_route()[1])+'; use fresh independent '+reviewer_kinds[0]+' and '+reviewer_kinds[1]+' contexts.\n' if route_fields() else 'Cell 1 uses fresh independent codex_cli and claude contexts; agy is available for later cells.\n')
            +
            'Reviewer identity must differ from author, operator, and the other reviewer. Use independent reviewer sessions and record each actual kind truthfully.\n'
            'Record findings, actual decision and UTC review time; do not treat these draft packets or fabricated evidence as approval.\n'
            'Current holds:\n'+'\n'.join('- '+item for item in holds)+'\n')
        write(dest/'instructions.md',instructions.encode())
        save(dest/'manifest.json',dict(main_sha=A.main_sha,reviewer_kind=reviewer,reviewer_pair=pair,dry_run=A.dry_run,
            status='draft_with_holds' if holds else 'ready_for_independent_review',reviews_performed=False,holds=holds,artifacts=copies,**route_fields()))
        manifests.append(pin(dest/'manifest.json'))
    result=dict(status='draft_with_holds' if holds else 'ready_for_independent_review',reviewer_pair=pair,artifacts=manifests,holds=holds,
        reviews_performed=False,messages_sent=False,**route_fields())
    save(S/'review-packets.json',result)
    return result


def common_args():
    args=['--main-sha',A.main_sha,'--checkout',str(W),'--scratch',str(S)]
    args+=['--reviewer-pair',getattr(A,'reviewer_pair','codex-agy')]
    args+=model_label_args()
    if route_fields(): args+=['--project',selected_route()[0],'--rep',str(selected_route()[1])]
    if A.dry_run: args+=['--dry-run']
    if A.config: args+=['--config',str(A.config)]
    if A.existing_venv: args+=['--existing-venv',str(VENV)]
    for name in A.retry_command: args+=['--retry-command',name]
    return args


def self_checks():
    global W
    target=S/'self-checks'; target.mkdir()
    results=[]
    original=W
    try:
        W=original/'src'
        try: guard()
        except ValueError as exc:
            assert 'Git top-level' in str(exc)
            results.append(dict(case='nested_checkout_refused',passed=True))
        else: raise AssertionError('nested checkout admitted')
    finally: W=original
    previous=A.dry_run
    try:
        A.dry_run=not previous
        try: guard()
        except ValueError as exc:
            assert 'scratch identity' in str(exc)
            results.append(dict(case='production_rehearsal_state_mix_refused',passed=True))
        else: raise AssertionError('mode mixing admitted')
    finally: A.dry_run=previous
    versioned=target/'state.json'
    state(versioned,dict(phase='first')); old=versioned.read_bytes()
    state(versioned,dict(phase='second'))
    assert (S/'state-history'/versioned.name/digest(old)).read_bytes()==old
    results.append(dict(case='prior_state_preserved_on_resume',passed=True))
    source=target/'dependency.txt'; write(source,b'first')
    first=dependency_pins(dict(path=str(source)))
    source.write_bytes(b'second')
    assert dependency_pins(dict(path=str(source)))!=first
    results.append(dict(case='changed_saved_dependency_detected',passed=True))
    marker=target/'term-cleanup.txt'
    command=[str(BASE_PYTHON),'-P','-B',str(HERE),'checkout',*common_args(),'--internal-timeout-child',str(marker)]
    try: bounded(command,S,2)
    except subprocess.TimeoutExpired: pass
    else: raise AssertionError('timeout control did not time out')
    assert marker.read_bytes()==b'TERM cleanup observed\n'
    results.append(dict(case='inner_timeout_delivers_term_before_kill',passed=True))
    save(target/'results.json',dict(results=results,all_passed=all(row['passed'] for row in results)))
    findings=[
        ('FP-01','Resume state collided with immutable status file','Versioned state snapshots preserve earlier holds'),
        ('FP-02','Missing production prefix choices froze defaults','Require explicit choices and exact argv on reuse'),
        ('FP-03','Nested directory could masquerade as checkout','Require exact Git top-level'),
        ('FP-04','Saved sequence was only checked for truthiness','Use genuine bound verifier and exact sequence/expectation pins'),
        ('FP-05','Selected binary/authorization not joined before probe','Require canonical runtime and exact durable/auth/account-choice bindings'),
        ('FP-06','Production preflight requested additional live probes','Separate explicit offline cohort; retain real-reference and sizing holds'),
        ('FP-07','Review packet silently omitted required evidence','Closed minimum roster plus complete gate artifacts and propagated holds'),
        ('FP-08','Inner timeout killed parent before cleanup','TERM-first bound with handlers installed before child creation'),
        ('FP-09','Cached saved step ignored referenced-file changes','Dependency pin checks and final production reconstruction'),
        ('FP-10','Probe draft parent directory was missing','Create parent; retain initial failed command and explicit retry'),
        ('FP-11','Draft binary recipe reused rehearsal identity','Prepare fresh production paths and a deliberately invalid configuration template'),
        ('FP-12','Incomplete report prose implied later stages ran','Condition artifact references and claims on saved outcomes; report failed stages as holds'),
        ('FP-13','Provisional gate source was absent from reviewer holds','Propagate unapproved exact gate pins into preflight and reviewer-packet holds'),
        ('FP-14','Sequence input wording could select CLI stdout envelope','Name the raw sequence.json from result.sequence.path explicitly'),
        ('FP-15','Production review could overwrite the rehearsal handoff','Restrict automatic and explicit rehearsal reporting to dry-run mode'),
    ]
    save(S/'local-review-findings.json',dict(scope='Local issue records for lead; no GitHub write authorized',
        findings=[dict(id=key,problem=problem,resolution=resolution,status='addressed_in_driver') for key,problem,resolution in findings]))
    return dict(status='checks_passed',artifacts=[pin(target/'results.json'),pin(S/'local-review-findings.json')],holds=[])


def parent():
    guard()
    if A.plan:
        print(json.dumps(dict(**identity(),step=A.step,gate_wait_seconds=A.gate_wait_seconds,
            execution='offline rehearsal with explicit fabricated evidence' if A.dry_run else 'production saved-input preparation',
            native_binary_execution=False),indent=2))
        return 0
    S.mkdir(parents=True,exist_ok=True)
    if not (S/'identity.json').exists(): save(S/'identity.json',identity())
    label='self-check' if A.self_check else A.step
    number=1
    while (S/'operations'/f'{label}-{number:03d}').exists(): number+=1
    op=S/'operations'/f'{label}-{number:03d}'; op.mkdir(parents=True)
    runner=module('fastpath_runner',RUNNER); runner.disarm_inherited_timers()
    selected=BASE_PYTHON if A.step in ('checkout','environment') else PYTHON
    command=[str(selected),'-P','-B',str(HERE),A.step,*common_args(),'--internal-worker',str(op)]
    if A.self_check: command+=['--self-check']
    # Each builder/sizing child has its own OS sandbox. Do not nest OS profiles:
    # the source-bound gate's reviewed parent audit installs its worker sandbox.
    save(op/'plan.json',dict(command=command,producer=pin(HERE),runner=pin(RUNNER),timeout_seconds=A.timeout_seconds,
        parent_argv=list(getattr(sys,'orig_argv',[sys.executable,*sys.argv])),admission_wait_seconds=A.gate_wait_seconds,
        timeout_scope='Offline preparation process watchdog; native limits are read from registration and runtime profile.',
        configuration=pin(A.config) if A.config else None))
    began=time.monotonic()
    lease,gate_seconds=runner.acquire_host_gate(lock_dir=runner.default_lock_dir(W),max_slots=2,exclusive=False,
        max_load=round(2.0*(os.cpu_count() or 1),1),wait_seconds=A.gate_wait_seconds,no_wait=False,
        metadata=dict(pid=os.getpid(),lane='postmerge-'+A.step,root=str(W),exclusive=False,started_at=runner.utc_now_iso()))
    save(op/'gate.json',dict(acquired=lease is not None,elapsed_seconds=gate_seconds,wait_limit_seconds=A.gate_wait_seconds))
    if lease is None:
        save(op/'outcome.json',dict(returncode=75,elapsed_seconds=time.monotonic()-began,gate_seconds=gate_seconds,status='not_admitted'))
        return 75
    dispatched=pin(HERE)
    command+=['--expected-producer-sha',dispatched['sha256']]
    write(op/'producer.source',HERE.read_bytes())
    save(op/'dispatch.json',dict(command=command,producer=dispatched))
    try:
        rc,seconds,timed_out=runner.run_step_without_sigalrm(step=runner.StepSpec(A.step,tuple(command),{},()),
            root=W if W.exists() else P,env=clean_env(),log_path=op/'output.log',timeout_seconds=A.timeout_seconds,kill_grace_seconds=30)
    finally:
        lease.release()
    outcome=dict(step=A.step,returncode=rc,process_seconds=seconds,gate_seconds=gate_seconds,
        wall_seconds=time.monotonic()-began,timed_out=timed_out,worker_result=load(op/'result.json') if (op/'result.json').exists() else None)
    save(op/'outcome.json',outcome)
    guard()
    print(json.dumps(outcome),flush=True)
    if A.dry_run and A.step=='review-packets' and rc in (0,2):
        render_handoff()
    return rc


def install_runbook_section():
    backup=RUNBOOK.with_name(RUNBOOK.name+'.bak-fastpath-20261117')
    original=RUNBOOK.read_bytes()
    d159=('D159: Native timing limits are read from the exact registration and the runtime profiles in the selected checkout. '
        'Each successful registration gets an `effective-native-limits.json` receipt with artifact and source pins, including the selected deadline, Bash limits, admission terms, callback contract and saved probe authorization deadlines. '
        'Offline host-gate waits and preparation watchdogs do not set native limits. The dated bc61 rehearsal preserves its older effective values; production must use the merged checkout containing the ratified D159 profiles.\n\n')
    gate_note=('NP1.5 packaging hold found in this rehearsal: the selected external source-bound gate also requires matching validation-worker source inside the registered checkout. '
        'The assigned bc61 checkout lacks it, and the gate exposes no supported override, so the CHORUS self-comparison returns `cannot_decide` before production validation. '
        'The lead must resolve the accepted gate packaging or external support binding before fresh environment capture. Do not copy or symlink gate tools into an already frozen checkout.\n\n')
    if backup.exists():
        assert pin(backup)==load(S/'runbook-edit.json')['backup'], 'original runbook backup changed'
        marker=b'## Post-merge fast path, 2026-11-17\n'
        assert original.count(marker)==1, 'owned runbook section is missing or ambiguous'
        start=original.index(marker)
        following=original.find(b'\n## ',start+len(marker))
        end=following if following>=0 else len(original)
        if d159.encode() not in original[start:end]:
            note,suffix=d159,'d159-note'
        elif gate_note.encode() not in original[start:end]:
            note,suffix=gate_note,'gate-layout-note'
        else: return
        anchor=('The dry-run handoff is `'+str(HANDOFF)+'`.\n').encode()
        assert original[start:end].count(anchor)==1, 'owned section differs; preserve it for review'
        point=original.index(anchor,start)+len(anchor)
        addition=('\n'+note).encode()
        updated=original[:point]+addition+original[point:]
        before=S/('runbook-before-'+suffix+'.md'); after=S/('runbook-after-'+suffix+'.md')
        write(before,original)
        assert RUNBOOK.read_bytes()==original
        RUNBOOK.write_bytes(updated)
        assert RUNBOOK.read_bytes()==updated and updated[:point]==original[:point] and updated[point+len(addition):]==original[point:]
        write(after,updated)
        save(S/('runbook-'+suffix+'.json'),dict(original_backup=pin(backup),before=pin(before),after=pin(after),
            live_after=pin(RUNBOOK),only_owned_section_changed=True,all_other_bytes_preserved=True))
        return
    write(backup,original)
    section=('\n\n## Post-merge fast path, 2026-11-17\n\n'
        'Driver: `'+str(HERE)+'`. It never executes Claude, contacts GitHub, merges or pushes. Use a fresh scratch root and the exact merged SHA. The explicit `--dry-run` mode fabricates software-test evidence and can never share a state directory with production.\n\n'
        'Run the subcommands in this order: `checkout`, `environment`, `binary-copy`, `probe-prepare`, `register-chorus`, `preflight-all`, `review-packets`. Supply `--main-sha`, `--checkout`, `--scratch`, and production `--config` on each invocation. `--plan` performs read-only preflight; actual steps wait up to 1800 seconds on the adopted host gate and run under an outside process-group deadline.\n\n'
        'Interleaving: `register-chorus` first builds the input prefix and stops if saved observation inputs are missing. The lead runs the observation command printed by `probe-prepare`. Run `register-chorus` again to verify observed `maxOutputTokens >= 64000` and build runtime/preparation/composition/expectation. The lead runs the printed bound-permission and offline validation commands. Run `register-chorus` again with their saved evidence, then `preflight-all` in D158 order, then `review-packets`. Existing successful phase artifacts are checked before reuse; a failed phase is retained and requires review.\n\n'
        'Before production, record binary version/durable copy, system text, account/config location, admission dates, saved probe inputs, qualification and archive evidence, actual post-merge CI, and an accepted external NP1.5 gate bundle with exact tool pins in the configuration. The gate tools are absent from the PR checkout; do not stage them into its frozen environment after manifest capture. The fast path uses the external source-bound gate mode. Any non-equal gate or unresolved sizing result is a hold. The cooperative load gate does not establish D92 qualification.\n\n'
        'Step 5e always builds a separately labelled offline candidate cohort; it does not request four extra live D117 probe pairs. Its fabricated CHORUS reference is separate from the actual CHORUS registration. Comparison to that real reference and the unresolved input-envelope/retained-record limitations remain explicit reviewer decisions. Review packets can be staged with holds; no hold is converted into a pass.\n\n'
        'The environment step APFS-clones the primary venv, backs up and redirects only the cloned editable path, and runs the two prescribed namespace/RECORD checks without creating an environment manifest. Always invoke the cloned interpreter explicitly; copied console entrypoints retain their old shebangs.\n\n'
        'Review packets are local pinned inputs and instructions for the explicit `--reviewer-pair`: `codex-claude` for cell 1, or `codex-agy` for later cells (the compatibility default). The v3 validator requires exactly two distinct independent reviewers with truthful kinds and the existing author/operator separation. They are not review decisions, owner acts, or launch words. The dry-run handoff is `'+str(HANDOFF)+'`.\n\n'+d159+gate_note)
    assert chr(64) not in section
    assert RUNBOOK.read_bytes()==original
    RUNBOOK.write_bytes(original+section.encode())
    assert RUNBOOK.read_bytes().startswith(backup.read_bytes())
    save(S/'runbook-edit.json',dict(backup=pin(backup),after=pin(RUNBOOK),original_prefix_preserved=True,appended_section_only=True))


def render_handoff():
    if not A.dry_run:
        raise ValueError('this dated handoff is only for the offline rehearsal; production outcomes stay in their own scratch root')
    review=S/'local-review-findings.json'
    if review.exists():
        findings=load(review)
        additions=[
            ('FP-17','D159 needed explicit registered-limit provenance','Read and cross-check saved runtime, permission and selected source profiles; preserve historical bc61 values.'),
            ('FP-18','Production review omitted actual-reference probe-limit dependencies','Include actual CHORUS observation and authorization alongside offline cohort evidence.'),
            ('FP-19','Review copies did not enforce the recorded source payload hash','Compare source and copied bytes with each saved pin before accepting packet output.'),
            ('FP-20','Reviewers needed scratch paths to inspect the sizing retry','Include basic and final sizing receipts plus the original pinned failure command and stderr in both packets.'),
        ]
        for key,problem,resolution in additions:
            if not any(row['id']==key for row in findings['findings']):
                findings['findings'].append(dict(id=key,problem=problem,resolution=resolution,status='addressed_in_driver',
                    validation_scope='Static review plus the saved dry-run artifacts; genuine production probe paths remain unexercised.'))
        gate=packet('CHORUS')/'np15/result.json'
        if gate.is_file() and load(gate)['status']=='cannot_decide' and not any(row['id']=='FP-21' for row in findings['findings']):
            findings['findings'].append(dict(id='FP-21',problem='External gate cannot construct validation against this checkout layout',
                resolution='Lead decision required: supported gate packaging or external support binding before fresh manifest capture. Frozen checkout preserved.',
                status='open_dependency_hold',evidence=pin(gate)))
        state(review,findings)
    records=[]
    for step in STEPS:
        found=sorted((S/'operations').glob(step+'-*/outcome.json'))
        if not found:
            records.append(dict(step=step,status='not_completed',wall_seconds=None,process_seconds=None,
                gate_seconds=None,total_attempt_wall_seconds=None,returncode=None,evidence=None,holds=['No completed dry-run result for '+step]))
            continue
        row=load(found[-1]); result=row.get('worker_result') or {}
        records.append(dict(step=step,status=result.get('status',row.get('status','failed')),wall_seconds=row.get('wall_seconds',row.get('elapsed_seconds')),
            process_seconds=row.get('process_seconds'),gate_seconds=row.get('gate_seconds'),returncode=row['returncode'],evidence=str(found[-1]),holds=result.get('holds',[]),
            total_attempt_wall_seconds=sum(load(path).get('wall_seconds',load(path).get('elapsed_seconds',0)) for path in found),
            attempts=[dict(evidence=str(path),**load(path)) for path in found]))
    holds=[]
    for row in records:
        if row['returncode'] not in (0,2):
            holds.append(row['step']+' did not complete successfully; inspect its retained operation evidence before retrying.')
        for item in row['holds']:
            if item not in holds: holds.append(item)
    decisions=[
        'Record the exact merged main SHA, its actual post-merge CI, and the D159 runtime profiles; this offline rehearsal uses the older PR head as a stand-in.',
        'Choose the binary version explicitly: the runbook draft selects 2.1.325; the active updater observed during preparation may differ. Verify the chosen durable copy without executing it in this driver.',
        'Finalize production system text, account/home/config/PATH/storage choices, admission dates, authorization and phase-specific account-choice evidence.',
        'Obtain genuine observation with maxOutputTokens at least 64000 and bound-permission evidence; fabricated rehearsal records cannot satisfy these conditions.',
        'Supply the lead quiet-host D92 and N1.8 timing qualification and timestamped registration archive. The cooperative load gate does not establish qualification.',
        'Select the accepted external NP1.5 gate bundle and exact tool pins, and resolve its checkout-local worker requirement before fresh manifest capture; provisional local gate source is not approval.',
        'Resolve all five-project sizing holds and compare offline candidates to the actual CHORUS reference before cell 1; this driver grants no waiver.',
        'Select --reviewer-pair codex-claude for cell 1; codex-agy remains available for later cells. Name truthful kinds and independent identities separated from author/operator and each other.',
    ]
    state(S/'summary.json',dict(main_sha=A.main_sha,steps=records,manual_decisions_and_holds=decisions+holds,dry_run=A.dry_run))
    lines=['**Answer: the offline fast-path rehearsal is recorded below. Production remains on hold for the explicit decisions and live evidence listed here. No Claude binary, live probe, binary copy, launch or GitHub action ran.**','','| Step | Dry-run result | Latest wall seconds | Process seconds | Gate seconds | All attempts wall seconds | Exit |','| --- | --- | --- | --- | --- | --- | --- |']
    for row in records:
        lines.append('| '+' | '.join(format(row[key],'.3f') if isinstance(row[key],float) else str(row[key]) for key in
            ('step','status','wall_seconds','process_seconds','gate_seconds','total_attempt_wall_seconds','returncode'))+' |')
    lines+=['','Open manual decisions and holds:','']+['- '+item for item in decisions+holds]
    timing_paths=[packet(project)/'effective-native-limits.json' for project in PROJECTS]
    if any(path.is_file() for path in timing_paths):
        lines+=['','Effective native limits are read from pinned registration/runtime/profile artifacts, not from the driver’s offline watchdogs. The assigned bc61 source predates D159; its historical values are preserved here. Production must be checked against the selected merged source containing D159. Dry-run fabrication does not imply the synthetic software-test runtime profile.',
            '', '| Project | Profile | Run deadline seconds | Bash default/max milliseconds | Usage age/margin seconds | Init/classifier/observer/runtime callback seconds | Probe observation/permission seconds |',
            '| --- | --- | --- | --- | --- | --- | --- |']
        for path in timing_paths:
            if not path.is_file(): continue
            value=load(path); history=value['pretool_control']; admission=value['admission_policy']
            bash=value['bash_timeouts_ms']; probe=value['probe_authorization_limits'] or {}
            join=lambda values:'/'.join(str(item) for item in values)
            fields=(value['project'],value['profile'],value['deadline_seconds'],
                join(bash.values()),join(admission[key] for key in ('max_age_seconds','pre_reservation_margin_seconds')),
                join(history[key] for key in ('initialize_timeout_seconds','callback_timeout_seconds','observer_timeout_seconds','runtime_callback_timeout_seconds')),
                join(probe.get(key,'unavailable') for key in ('observation_deadline_seconds','permission_deadline_seconds')))
            lines.append('| '+' | '.join(map(str,fields))+' |')
    if (S/'preflight-all.json').is_file():
        preflight=load(S/'preflight-all.json')
        lines+=['','| Project | Native partition | Input envelope | Retained typed request | Native outer request scenario | Hypothetical Write argument bytes | Token headroom at 2.48 bytes/token | NP1.5 |',
            '| --- | --- | --- | --- | --- | --- | --- | --- |']
        gates={row['project']:row['status'] for row in preflight.get('gates',[])}
        for row in preflight.get('projects',[]):
            lines.append('| '+' | '.join(str(value) for value in (row['project'],row.get('native_partition','not_run'),
                row.get('input_envelope','not_run'),row.get('native_inner_request','not_run'),row.get('native_first_request','not_run'),
                row.get('hypothetical_native_write_arguments_bytes'),row.get('hypothetical_token_headroom_at_2_48'),
                gates.get(row['project'],'not_run')))+' |')
        lines+=['','The Write and token columns describe hypothetical scaffolds, not actual model output or a future maximum. Their exact JSON escaping and assumptions are retained in each project’s output-size-scenarios.json.']
    if (packet('CHORUS')/'basic-sizing-verification.json').is_file():
        basic=load(packet('CHORUS')/'basic-sizing-verification.json')
        limits=load(packet('CHORUS')/'sizing.json')['response_caps']
        lines+=['','The CHORUS declared response cap is '+str(limits['declared_response_bytes'])+' bytes; its effective typed worker/integration cap is '+str(limits['typed_worker_and_integration'])+' bytes, and its receipt/omission cap is '+str(limits['receipt_and_omission'])+' bytes. These are acceptance byte caps, not output-token fit guarantees.']
        if basic.get('resumed_failure'):
            lines+=['','The initial sizing canary stopped on FP-16, a driver check that compared the declared cap with the smaller effective typed cap. The retry verified and reused the completed basic sizing before running the missing scaffold. No production limit changed. Evidence: `'+str(packet('CHORUS')/'basic-sizing-verification.json')+'`.']
    if (S/'binary-copy.json').is_file():
        binary=load(S/'binary-copy.json')
        assert pin(Path(binary['source']['path']))==binary['source']
        lines+=['','Prepared binary-copy command (not executed). Its production checkout/scratch are future targets. Finalize the deliberately invalid draft configuration and exact merged SHA before using this recipe:',
            '', '```sh',command_text(binary['command']),'```',
            '', 'Recorded active updater: `'+str(binary.get('active_updater'))+'`. Draft-selected source: `'+binary['source']['path']+'`, SHA-256 `'+binary['source']['sha256']+'`.']
    if (S/'probe-prepare.json').is_file():
        probe=load(S/'probe-prepare.json')
        lines+=['','Prepared probe inputs:','','| Existing draft artifact | Bytes | SHA-256 |','| --- | --- | --- |']
        for row in probe['draft_artifacts']:
            assert pin(Path(row['path']))==row
            lines.append('| `'+row['path']+'` | '+str(row['bytes'])+' | `'+row['sha256']+'` |')
        lines+=['','Prepared commands below use the rehearsal paths. Their final authorization/runtime/account-choice paths are required inputs, not existing approved artifacts. Production probe-prepare prints the corresponding commands from its selected production checkout, scratch and configuration. Neither live command ran.']
        for phase,command in probe['command_text'].items():
            lines+=['',phase+':','','```sh',command,'```']
        lines+=['',probe['saved_sequence_instruction']]
    lines+=['',f'Source `{A.main_sha}` at `{W}`. Script: `{HERE}`. Saved summary: `{S / "summary.json"}`.',
        '', 'Each row reports the latest completed attempt, including host-gate wait, plus the sum of all attempt wall times for that step. These sums overlap when independent steps queued concurrently; they are not total elapsed task time. All earlier attempts remain in the summary. Checkout verified the supplied detached worktree and initialized submodule; the fresh-worktree creation branch was not exercised. Binary copying and live probes were deliberately not exercised.',
        '', 'Registration stages invoke real prefix builders and saved-step CLIs against manifest-declared project inputs. Only probe/runtime/account/system/permission declarations use labelled test fixtures. Completed stages are identified by the saved outcomes above; missing or failed stages are not claimed as exercised. The observed output floor and production readiness are not established by fixtures.',
        '', 'The driver requires the CHORUS registration and sizing artifacts before running the remaining projects serially. The first failed NP1.5 comparison stops the gate batch; no later project receives an inferred verdict.',
        '', 'The production subcommands accept an explicit JSON config. Binary fields: `binary_source`, `durable_binary`; probe paths: `provisional_runtime`, `authorization`, `observation_account_choice`, `permission_account_choice`, `final_runtime_account_choice`; gate fields: `gate_root`, `gate_expected_pins`; external evidence: `qualification`, `registration_commit`, `ci`, `permission_probe`. Per-project `projects.PROJECT` supplies `registration_id`, `label`, `runtime_inputs`, `system_path`, `job_id`, `run_date`, `attempt_id`, `attempt_directory`, `evidence_directory`, `max_draft_checks`, `permission_probe`, and `probe_sequence`. Missing fields produce an explicit dependency stop. No owner or reviewer values are inferred.',
        '', 'Production registration archival commit and quiet-host qualification remain lead operations prescribed by the earlier runbook sections; this script verifies supplied archival evidence and stages it for review. The cooperative gate is scheduling only.',
        '', 'Environment provenance: `'+str(S/'environment.json')+'`. It documents whether the environment was supplied or cloned, any path-file backup, and retained installation metadata. Runbook edit proof: `'+str(S/'runbook-edit.json')+'`. Only the appended fast-path section was edited; the complete original is preserved in the required backup.',
        '', 'No independent review was performed and no message was sent. Reviewer packets are staging artifacts and carry unresolved holds.',
        '', 'Reproduction uses the same script and subcommand order with fresh checkout/scratch paths. Retain failed evidence rather than overwriting or treating it as approval. Each operation stores its exact argv, producer hash, gate wait, outside deadline, stdout/stderr and outcome.',
        '', 'When a mutable state pointer advances, its old bytes remain under the scratch state-history directory, grouped by filename and SHA-256. Historical outcomes retain the original hash; the latest state file may legitimately have a newer hash.',
        '', 'Static review and local issue dispositions are retained in the self-check evidence when that stage is admitted. The small timeout control establishes ordinary TERM-first cleanup of its immediate child; it does not exercise termination during child creation or separately sessioned descendants. Dependency hashing is checked separately from the live saved-step validation path.',
        '', 'All tables are rendered by the same script from saved operation JSON. The helper and handoff are retained on the report branch for the lead; committed PR files are unchanged.',
        '', 'Report generation is part of the final command (use fresh scratch outputs for a new rehearsal):','',
        '```sh',command_text([BASE_PYTHON,'-B',HERE,'review-packets',*common_args()]),'```','']
    for label,path in (('Prepared binary command and draft configuration',S/'binary-copy.json'),
                       ('Prepared probe commands and draft input pins',S/'probe-prepare.json'),
                       ('Per-project evidence',S/'packets'),('Local reviewer packets',S/'reviews'),
                       ('D159 runbook note and preservation proof',S/'runbook-d159-note.json'),
                       ('Gate-layout runbook note and preservation proof',S/'runbook-gate-layout-note.json'),
                       ('Focused control results',S/'self-checks/results.json'),('Local review findings',S/'local-review-findings.json')):
        if path.exists(): lines+=['- '+label+': `'+str(path)+'`.']
    text='\n'.join(lines)
    assert chr(64) not in text
    write(HANDOFF,text.encode())
    print(json.dumps(dict(handoff=pin(HANDOFF))),flush=True)


def main():
    global A,W,S,VENV,PYTHON,C
    parser=argparse.ArgumentParser(description=__doc__,allow_abbrev=False)
    parser.add_argument('step',choices=STEPS)
    parser.add_argument('--main-sha',required=True)
    parser.add_argument('--checkout',type=Path)
    parser.add_argument('--scratch',type=Path)
    parser.add_argument('--config',type=Path)
    parser.add_argument('--project',choices=PROJECTS,default='CHORUS')
    parser.add_argument('--model-label-version',type=int,choices=(1,2),default=1,
        help='Explicit draft provisional alias basis; never selected from binary version or transcript.')
    parser.add_argument('--rep',type=int,default=1)
    parser.add_argument('--reviewer-pair',choices=tuple(REVIEWER_PAIRS),default='codex-agy',
        help='C20 reviewers: codex-claude for cell 1; codex-agy retains the later-cell compatibility default.')
    parser.add_argument('--existing-venv',type=Path,help='Use a supplied physical isolated environment for offline dry runs only; verify it without cloning or changing its path file.')
    parser.add_argument('--dry-run',action='store_true',help='Execute offline test-evidence rehearsal; never production acceptance.')
    parser.add_argument('--plan',action='store_true')
    parser.add_argument('--retry-command',action='append',default=[],help='Explicitly retry a reviewed failed offline command, retaining its old evidence; partial outputs still refuse.')
    parser.add_argument('--gate-wait-seconds',type=float,default=1800)
    parser.add_argument('--timeout-seconds',type=int,default=10800,help='Outside watchdog for offline preparation only; never a native runtime or cell limit.')
    parser.add_argument('--install-runbook-section',action='store_true')
    parser.add_argument('--self-check',action='store_true',help='Run focused offline driver controls, under the host gate.')
    parser.add_argument('--render-handoff',action='store_true',help='Render retained results without launching a step; missing results remain explicit.')
    parser.add_argument('--internal-worker',type=Path,help=argparse.SUPPRESS)
    parser.add_argument('--internal-chain',choices=PROJECTS,help=argparse.SUPPRESS)
    parser.add_argument('--internal-size',choices=PROJECTS,help=argparse.SUPPRESS)
    parser.add_argument('--internal-gate',type=Path,help=argparse.SUPPRESS)
    parser.add_argument('--internal-cohort',type=Path,help=argparse.SUPPRESS)
    parser.add_argument('--internal-timeout-child',type=Path,help=argparse.SUPPRESS)
    parser.add_argument('--expected-producer-sha',help=argparse.SUPPRESS)
    A=parser.parse_args()
    selected_route()
    if route_fields() and (A.checkout is None or A.scratch is None or A.config is None):
        parser.error('nonlegacy routes require explicit checkout, scratch and config')
    if A.step=='register-chorus' and route_fields():
        parser.error('register-chorus requires CHORUS rep1; select register-project')
    if A.existing_venv and not A.dry_run:
        parser.error('--existing-venv is supported only with --dry-run')
    if A.expected_producer_sha and digest(HERE.read_bytes())!=A.expected_producer_sha:
        raise ValueError('driver source changed between dispatch and worker start')
    if not re.fullmatch('[0-9a-f]{40}',A.main_sha): raise ValueError('main-sha requires full lowercase 40-hex commit')
    W=A.checkout or E/('native-production-'+A.main_sha[:12])
    S=A.scratch or E/('native-fastpath-'+A.main_sha[:12])
    VENV=A.existing_venv or W/'.venv'; PYTHON=VENV/'bin/python'; C=load(A.config) if A.config else {}
    if A.internal_cohort:
        if not A.dry_run or route_fields(): raise ValueError('offline candidate cohort requires its separate legacy dry-run route')
        C={key:value for key,value in C.items() if key in ('gate_root','gate_expected_pins')}
    if A.internal_timeout_child:
        if not A.dry_run or not A.internal_timeout_child.is_relative_to(S/'self-checks'):
            raise ValueError('timeout control is confined to dry-run self-check data')
        def stopped(signum,frame):
            A.internal_timeout_child.write_bytes(b'TERM cleanup observed\n')
            raise SystemExit(0)
        signal.signal(signal.SIGTERM,stopped)
        while True: time.sleep(1)
    if not A.dry_run and str(C.get('kind','')).startswith('DRAFT'):
        raise ValueError('draft configuration is not production input; lead must finalize explicit choices')
    if A.internal_gate:
        internal_gate(A.internal_gate); return 0
    guard()
    if A.render_handoff:
        render_handoff()
        return 0
    if A.internal_cohort:
        if not A.dry_run: raise ValueError('offline candidate cohort requires explicit dry-run scope')
        C={key:value for key,value in C.items() if key in ('gate_root','gate_expected_pins')}
        S.mkdir(parents=True,exist_ok=True)
        if not (S/'identity.json').exists(): save(S/'identity.json',identity())
        if not (S/'environment.json').exists(): save(S/'environment.json',load(A.internal_cohort))
        register_chorus()
        result=preflight_all()
        return 2 if result['holds'] else 0
    if A.internal_chain:
        if not A.dry_run: raise ValueError('fabricated evidence is restricted to explicit dry-run mode')
        rehearsal_chain(A.internal_chain); return 0
    if A.internal_size:
        _,_,sizes=support()
        measured=verified_basic_sizing(A.internal_size,sizes)
        helper=SUPPORT/'size_step5e_output_scenarios_20261116.py'
        before=pin(helper)
        record=S/'output-sizing-helper-pin.json'
        if record.exists(): assert load(record)==before
        else: save(record,before)
        effective=min(measured['stratum_bounds']['max_response_bytes'],measured['hard_limits']['typed_response_bytes'])
        assert measured['response_caps']['typed_worker_and_integration']==effective==2097152, 'effective typed response cap needs explicit scaffold adaptation'
        extra=module('fastpath_output_sizing',helper)
        extra.W,extra.S=W,S
        extra.measure(A.internal_size)
        assert pin(helper)==before
        review=S/'local-review-findings.json'
        if review.exists() and not any(row['id']=='FP-16' for row in load(review)['findings']):
            findings=load(review)
            findings['findings'].append(dict(id='FP-16',problem='Sizing guard confused declared and effective typed response caps',
                resolution='Validate min of declared and hard typed caps; preserve and verify completed basic sizing before retrying only the missing scaffold.',
                status='verified_by_sizing_canary',evidence=pin(packet(A.internal_size)/'basic-sizing-verification.json')))
            state(review,findings)
        return 0
    if A.internal_worker:
        try:
            result=self_checks() if A.self_check else {'checkout':checkout,'environment':environment,'binary-copy':binary_copy,'probe-prepare':probe_prepare,
                'register-chorus':register_chorus,'register-project':register_project,'preflight-all':preflight_all,'review-packets':review_packets}[A.step]()
            guard(); save(A.internal_worker/'result.json',result)
            return 2 if result['status'] in ('dependency_stop','hold','draft_with_holds') else 0
        except Exception as exc:
            save(A.internal_worker/'failure.json',dict(error_type=type(exc).__name__,error=str(exc)))
            raise
    if A.install_runbook_section:
        install_runbook_section()
        proof=next(path for path in (S/'runbook-gate-layout-note.json',S/'runbook-d159-note.json',S/'runbook-edit.json') if path.exists())
        print(json.dumps(load(proof)),flush=True)
        return 0
    return parent()


if __name__=='__main__':
    raise SystemExit(main())
