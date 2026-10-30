#!/usr/bin/env python3
# Purpose: derive canonical CHORUS wires without #5210 admission, tracing inherited assets.
# Inputs: exact committed baseline, unchanged #5157 fixture, physical venv; outputs: external wire evidence.
# Refs #5210 / #5157, Wave5 baseline diagnosis; 2026-10-28. Offline scripted client only.
"""Run with -S -P -B; fixture preparation uses immutable Git bytes, never an owner edit."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
FIXTURE_SOURCE = 'aaa6f5bec2a0c7832d36143c4c7470d51cb8cee4'
FIXTURE_PATH = ROOT / 'scripts/adhoc/wave5_5210_fixture_20261028.py'
HEADER = ('# Purpose: unchanged copied CHORUS wire fixture for baseline lineage diagnosis.\n'
          '# Inputs: scripted local records; outputs: captured fake-client wires via companion helper.\n'
          '# Refs #5210 / #5157; 2026-10-28. Original module below is copied verbatim.\n')


def git(*args):
    env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
    env.update(GIT_NO_LAZY_FETCH='1', GIT_OPTIONAL_LOCKS='0')
    return subprocess.check_output(['git', '--no-replace-objects', *args], cwd=ROOT, env=env)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write('\n')


def deny_live(event, args):
    if event in {'socket.connect', 'socket.getaddrinfo', 'socket.sendto'}:
        raise RuntimeError('offline wire proof forbids network')
    if event == 'subprocess.Popen' and Path(os.fsdecode(args[0])).name in {'claude', 'gh', 'curl', 'wget', 'ssh'}:
        raise RuntimeError('offline wire proof forbids live command')


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare-fixture', action='store_true')
    parser.add_argument('--base')
    parser.add_argument('--head')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    original = git('show', FIXTURE_SOURCE + ':tests/test_report_admission.py')
    if args.prepare_fixture:
        with FIXTURE_PATH.open('xb') as stream:
            stream.write(HEADER.encode() + original)
        print(sha(original))
        return 0
    if not (sys.flags.no_site and sys.flags.safe_path and sys.dont_write_bytecode):
        raise ValueError('requires -S -P -B')
    if os.environ.get('PYTHONPATH') or os.environ.get('PYTHONHOME'):
        raise ValueError('requires empty PYTHONPATH and PYTHONHOME')
    if FIXTURE_PATH.read_bytes() != HEADER.encode() + original:
        raise ValueError('fixture is not exact committed source plus provenance header')
    output = args.output
    if not output.is_absolute() or output.resolve() != output or output.is_relative_to(ROOT):
        raise ValueError('fresh physical external output required')
    output.mkdir(parents=True, exist_ok=False)
    common = load('wire_common', ROOT / 'scripts/adhoc/wave3_validation_common_20261027.py')
    common.ROOT, common.MODULES = ROOT, ()
    before = common.source()
    save(output / 'source-before.json', before)
    if before['head'] != args.head or not before['tracked_exact'] or git('status', '--porcelain=v1', '--untracked-files=all'):
        raise ValueError('clean exact source required')
    if git('diff', '--name-only', args.base, 'HEAD', '--', 'src', 'tests', 'data', '.claude'):
        raise ValueError('baseline production/assets/tests differ')
    removed = [k for k in os.environ if k.startswith(('ANTHROPIC_', 'CBORG_', 'OPENAI_'))
               or k.endswith(('_API_KEY', '_AUTH_TOKEN', '_ACCESS_TOKEN'))
               or k in {'CLAUDE_CODE_OAUTH_TOKEN', 'PYTEST_PLUGINS', 'D4D_INSTALL_TESTS'}]
    for key in removed:
        os.environ.pop(key)
    os.environ.update(PYTHONDONTWRITEBYTECODE='1', PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',
                      PIP_NO_INDEX='1', UV_OFFLINE='1', GIT_NO_LAZY_FETCH='1')
    venv = Path(sys.executable).parent.parent
    site = venv / 'lib' / ('python' + '.'.join(map(str, sys.version_info[:2]))) / 'site-packages'
    if not (venv / 'pyvenv.cfg').is_file() or not site.is_dir() or site.resolve() != site:
        raise ValueError('physical venv required')
    sys.prefix = sys.exec_prefix = str(venv)
    sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'scripts'), str(ROOT)]
    sys.path.append(str(site))
    sys.addaudithook(deny_live)
    fixture = load('scripts.adhoc.wave5_5210_fixture_20261028', FIXTURE_PATH)
    # Only relocate the unchanged module's checkout constants to their original meaning.
    # Its functions, classes, fake scripts and golden constants remain byte-identical.
    fixture.ROOT = ROOT
    fixture.CHORUS_BUNDLE = ROOT / 'data/preprocessed/concatenated/CHORUS_preprocessed.txt'
    if hasattr(fixture.api, '_admit_shared_context'):
        raise ValueError('baseline unexpectedly contains #5210 admission implementation')
    save(output / 'origins-before.json', common.origins(before))
    save(output / 'plan.json', {'base': args.base, 'head': args.head,
         'fixture_source': FIXTURE_SOURCE, 'fixture_source_sha256': sha(original),
         'fixture_file_sha256': sha(FIXTURE_PATH.read_bytes()), 'python': sys.version,
         'executable': sys.executable, 'site': str(site), 'pth_disabled': True,
         'network_hook': True, 'dependency_bytes_attested': False,
         'credential_names_removed': sorted(removed),
         'argv': sys.argv, 'cwd': str(ROOT),
         'fixture_constant_relocation': ['ROOT', 'CHORUS_BUNDLE']})
    from pytest import MonkeyPatch
    case = output / 'case'
    started = time.monotonic()
    code, wires, error = 1, {}, None
    try:
        with MonkeyPatch.context() as patch:
            patch.setattr(fixture.api, 'provider_identity', lambda: {'provider': None, 'base_url': None, 'key_env': None})
            patch.setattr(fixture.api, 'MAX_ATTEMPTS', 1)
            spec, messages, requests = fixture.chorus_wires(case, patch)
            for phase, wire in requests.items():
                raw = json.dumps(wire, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
                normal = raw.replace(str(case), '<root>').replace(fixture.checkout(), '<repo>').encode()
                expected = fixture.wire_sha256(wire, case)
                if sha(normal) != expected:
                    raise ValueError('normalization differs from unchanged fixture')
                (output / (phase + '.canonical.json')).write_bytes(normal)
                wires[phase] = {'sha256': expected, 'bytes': len(normal),
                    'old_golden': fixture.BASE_WIRE_SHA256[phase],
                    'matches_old_golden': expected == fixture.BASE_WIRE_SHA256[phase]}
            save(output / 'phases.json', {'phases': messages.phases, 'admitted_count_phases': messages.counted})
            code = 0
    except Exception as caught:
        error = {'type': type(caught).__name__, 'message': str(caught)}
        raise
    finally:
        save(output / 'origins-after.json', common.origins(before))
        after = common.source()
        save(output / 'source-after.json', after)
        outcome = {'returncode': code, 'source_unchanged': before == after,
                   'wires': wires, 'error': error, 'wall_seconds': time.monotonic() - started,
                   'passed': code == 0 and before == after, 'scientific_acceptance': 'not_assessed'}
        save(output / 'outcome.json', outcome)
        print(json.dumps(outcome, sort_keys=True), flush=True)
    return 0 if outcome['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
