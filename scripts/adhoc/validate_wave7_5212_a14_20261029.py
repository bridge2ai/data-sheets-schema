#!/usr/bin/env python3
# Purpose: offline Wave7 D41/A14 composition tests with import, protected-union and JUnit evidence.
# Inputs: clean local checkout, base/head pins, explicit test modules, physical venv.
# Outputs: fresh external source/origin/outcome evidence; Refs #5212 / #5162, 2026-10-29.
"""No providers; Python network hooks supplement (do not replace) the host sandbox."""
import argparse
import importlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('wave3_common', Path(__file__).with_name('wave3_validation_common_20261027.py'))
common = importlib.util.module_from_spec(spec)
spec.loader.exec_module(common)
common.ROOT = ROOT
PROTECTED = ('.claude/commands/d4d-uniform-rules-v2.md', 'src/download/prompts/d4d_generic_arm_prompt_v10.md',
             'src/data_sheets_schema/shared_generation.py', 'src/download/prompts/canonical_hashes.yaml',
             'src/data_sheets_schema/api_Generation_v2.py')


def deny_live(event, args):
    if event in {'socket.connect', 'socket.getaddrinfo', 'socket.sendto'}:
        raise RuntimeError('Wave7 offline validation forbids network: ' + event)
    if event == 'subprocess.Popen':
        name = Path(os.fsdecode(args[0])).name
        if name in {'claude', 'gh', 'curl', 'wget', 'ssh'}:
            raise RuntimeError('Wave7 forbids live command: ' + name)


def child(options):
    if not sys.flags.no_site or not sys.flags.safe_path or not sys.dont_write_bytecode:
        raise ValueError('requires -S -P -B')
    venv = Path(sys.executable).parent.parent
    site = venv / 'lib' / ('python' + '.'.join(map(str, sys.version_info[:2]))) / 'site-packages'
    if not (venv / 'pyvenv.cfg').is_file() or not site.is_dir() or site.resolve() != site:
        raise ValueError('physical venv required')
    sys.prefix = sys.exec_prefix = str(venv)
    sys.path.append(str(site))
    sys.addaudithook(deny_live)
    common.save(options.output / 'bootstrap.json', {'python': sys.version, 'executable': sys.executable,
        'site': str(site), 'pth_disabled': True, 'network_hook': True, 'dependency_bytes_attested': False})
    common.MODULES = tuple(options.module)
    for module in options.module:
        importlib.import_module('tests.' + module)
    baseline = json.loads((options.output / 'source-before.json').read_text())
    common.save(options.output / 'origins-before.json', common.origins(baseline))
    import pytest
    selected = ['tests/' + module.replace('.', '/') + '.py' for module in options.module]
    if options.test_node:
        selected = [selected[0] + '::' + options.test_node]
    args = ['-q', '-p', 'no:cacheprovider', '--basetemp', str(options.output / 'cases'),
            '--junitxml', str(options.output / 'pytest.xml'),
            *selected]
    common.save(options.output / 'pytest-command.json', {'args': args, 'cwd': str(ROOT)})
    try:
        return int(pytest.main(args))
    finally:
        common.save(options.output / 'origins-after.json', common.origins(baseline))


def run(options):
    output = options.output
    if output.is_relative_to(ROOT):
        raise ValueError('evidence must be outside frozen tree')
    output.mkdir(parents=True, exist_ok=False)
    before = common.source()
    common.save(output / 'source-before.json', before)
    if before['head'] != options.expect_head or not before['tracked_exact'] or common.git('status', '--porcelain=v1', '--untracked-files=all'):
        raise ValueError('clean exact committed source required')
    proof_spec = importlib.util.spec_from_file_location('wave7_union',
        Path(__file__).with_name('verify_wave7_5212_a14_merge_20261029.py'))
    proof_module = importlib.util.module_from_spec(proof_spec)
    proof_spec.loader.exec_module(proof_module)
    common.save(output / 'protected-union.json', proof_module.verify())
    changed = common.git('diff', '--name-only', options.base, 'HEAD').decode().splitlines()
    if any(p.startswith(('src/', 'tests/', 'data/', '.claude/')) or p ==
           'notes/reviews/v10_human_decisions_and_context_review_2026-10-20.md' for p in changed):
        raise ValueError('validation permits only helper/evidence changes after the reviewed merge')
    if any(p in PROTECTED or p.startswith(('data/d4d_concatenated/', 'data/ATTIC/', 'data/rubric/',
            'data/context/', 'data/omission_contexts/', 'src/data_sheets_schema/schema/', '.claude/agents/')) for p in changed):
        raise ValueError('protected or historical-run path changed against base')
    env = dict(os.environ)
    removed = sorted(k for k in env if k.startswith(('ANTHROPIC_', 'CBORG_', 'OPENAI_', 'GIT_'))
                     or k.endswith(('_API_KEY', '_AUTH_TOKEN', '_ACCESS_TOKEN'))
                     or k in {'CLAUDE_CODE_OAUTH_TOKEN', 'D4D_INSTALL_TESTS', 'PYTHONHOME', 'PYTEST_PLUGINS', 'RECEIPTS_V5_INSTRUMENT'})
    for key in removed:
        env.pop(key)
    env.update(PYTHONDONTWRITEBYTECODE='1', PYTEST_DISABLE_PLUGIN_AUTOLOAD='1', PYTEST_ADDOPTS='',
               PIP_NO_INDEX='1', UV_OFFLINE='1', HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1',
               GIT_NO_LAZY_FETCH='1', PYTHONPATH=os.pathsep.join(str(ROOT / p) for p in ('src', 'scripts', '.')))
    command = [sys.executable, '-S', '-P', '-B', str(Path(__file__).resolve()), '--child', '--output', str(output)]
    for module in options.module:
        command += ['--module', module]
    if options.test_node:
        command += ['--test-node', options.test_node]
    common.save(output / 'plan.json', {'command': command, 'head': options.expect_head, 'base': options.base,
        'modules': options.module, 'test_node': options.test_node,
        'credential_names_removed': removed, 'changed_paths': changed,
        'scope': 'Offline selected modules; Python audit guard does not isolate arbitrary child binaries.'})
    start = time.monotonic()
    with (output / 'pytest.log').open('xb') as log:
        code = subprocess.run(command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT).returncode
    after = common.source()
    common.save(output / 'source-after.json', after)
    counts = dict.fromkeys(options.module, 0)
    invalid, skipped, seen = [], [], set()
    if (output / 'pytest.xml').is_file():
        for case in ET.parse(output / 'pytest.xml').getroot().iter('testcase'):
            classname = case.get('classname', '').removeprefix('tests.')
            module = next((name for name in sorted(counts, key=len, reverse=True)
                           if classname == name or classname.startswith(name + '.')), None)
            identity = (case.get('classname'), case.get('name'))
            if identity in seen or module not in counts or not case.get('name') or any(case.find(t) is not None for t in ('failure', 'error')):
                invalid.append({'identity': identity, 'tags': [n.tag for n in case]})
            elif case.find('skipped') is not None:
                skipped.append({'identity': identity, 'reason': case.find('skipped').get('message')})
            else:
                counts[module] += 1
            seen.add(identity)
    complete = all((output / f'origins-{stage}.json').is_file() for stage in ('before', 'after'))
    selection_complete = (seen == {('tests.' + options.module[0], options.test_node)}
                          if options.test_node else all(counts.values()))
    outcome = {'returncode': code, 'source_unchanged': before == after, 'wall_seconds': time.monotonic() - start,
               'passed_cases_by_module': counts, 'invalid_junit_cases': invalid, 'skipped': skipped,
               'scientific_acceptance': 'not_assessed',
               'selection_complete': selection_complete,
               'passed': code == 0 and before == after and selection_complete and all(counts.values()) and not invalid and complete}
    common.save(output / 'outcome.json', outcome)
    print(json.dumps(outcome, sort_keys=True), flush=True)
    return 0 if outcome['passed'] else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--module', action='append', required=True)
    parser.add_argument('--test-node', help='One existing unparameterized test function within the sole selected module.')
    parser.add_argument('--expect-head')
    parser.add_argument('--base')
    parser.add_argument('--child', action='store_true')
    args = parser.parse_args()
    if args.test_node and (len(args.module) != 1 or not re.fullmatch(r'test_[A-Za-z0-9_]+', args.test_node)):
        parser.error('--test-node requires one module and an exact test function name')
    args.output = args.output.resolve()
    raise SystemExit(child(args) if args.child else run(args))
