"""Offline native attribution registration and trace verification (#4304).

No launch operation exists. This checks the additional draft obligation, not
all native phase, command, permission, accounting or terminal evidence gates.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shlex
import subprocess

import yaml

from data_sheets_schema import native_source_attribution as policy

KIND = 'd4d_native_source_attribution_offline_registration'
SCHEMA_VERSION = 1
EXECUTION = 'unsupported_pending_independent_controller_review'
SCOPE = ('Additional native draft attribution obligation only; historical native '
         'phase, permission, accounting and final evidence gates remain required. '
         'Offline results do not authorize execution or establish semantic support.')


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _json(raw):
    def pairs(items):
        out = {}
        for key, value in items:
            if key in out:
                raise ValueError(f'duplicate JSON key: {key}')
            out[key] = value
        return out
    def invalid(value):
        raise ValueError(f'nonfinite JSON number: {value}')
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid)


def _encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()


def _inputs(spec):
    paths = {'bundle': spec.bundle, 'chunk_manifest': spec.chunk_manifest}
    if spec.manifest_used:
        paths['source_manifest'] = spec.manifest
    return {name: {'path': str(Path(path).absolute()), 'sha256': _sha(Path(path).read_bytes())}
            for name, path in paths.items()}


def _code_pins():
    # The registration records actual dependency bytes, not a claim that a
    # prompt-only pin covers the checker. Drift requires a fresh registration.
    from data_sheets_schema.resources import resource_path
    root = resource_path(Path('src/data_sheets_schema'))
    paths = sorted(p for p in root.rglob('*') if p.is_file() and p.suffix in ('.py', '.yaml', '.json'))
    return {str(Path('src/data_sheets_schema') / p.relative_to(root)): _sha(p.read_bytes()) for p in paths}



def registration(spec):
    from data_sheets_schema.api_runner import assembly_digest
    policy.command_args(spec)  # requires active version and explicit finite limit
    before = _inputs(spec)
    rendered = spec.render_spec()
    from data_sheets_schema import prompt_registry
    from data_sheets_schema.resources import resource_path
    for path in spec.prompt_files:
        if prompt_registry.disk_status(path)[0] != prompt_registry.CANONICAL:
            raise ValueError(f'selected prompt is not at its canonical pin: {path}')
    prompt_pins = {str(p): _sha(resource_path(p).read_bytes()) for p in spec.prompt_files}
    instruction = spec.instruction
    result = {'kind': KIND, 'schema_version': SCHEMA_VERSION, 'execution': EXECUTION,
              'scope': SCOPE, 'working_directory': str(Path.cwd().resolve()),
              'code_commit': subprocess.check_output(
                  ['git', 'rev-parse', 'HEAD'], cwd=Path(__file__).resolve().parents[2], text=True).strip(),
              'project': spec.project, 'method': spec.method, 'label': spec.label,
              'render_spec': rendered, 'instruction': instruction,
              'instruction_sha256': _sha(instruction.encode()),
              'assembly': assembly_digest(spec.render_version, native_source_attribution_version=1),
              'policy': policy.policy_identity(), 'max_draft_checks': spec.native_source_attribution_max_checks,
              'command': shlex.join(policy.command_args(spec)), 'inputs': before,
              'checker_source_tree_sha256': _code_pins(), 'prompt_files_sha256': prompt_pins}
    if before != _inputs(spec):
        raise ValueError('selected source inputs changed while preparing registration')
    return result


def verified(raw):
    """Strictly reconstruct the offline selection; never infer a missing axis."""
    from data_sheets_schema.api_runner import RunSpec
    if type(raw) is not bytes:
        raise ValueError('registration must be captured bytes')
    value = _json(raw)
    if not isinstance(value, dict) or value.get('kind') != KIND:
        raise ValueError('not a native attribution offline registration')
    if type(value.get('schema_version')) is not int or value['schema_version'] != SCHEMA_VERSION:
        raise ValueError('unsupported native attribution registration version')
    if value.get('execution') != EXECUTION:
        raise ValueError('offline registration cannot authorize execution')
    try:
        spec = RunSpec.from_render_spec(value['render_spec'], project=value['project'],
                                       method=value['method'], label=value['label'])
        expected = registration(spec)
    except (KeyError, TypeError) as exc:
        raise ValueError('malformed native attribution registration') from exc
    if _encoded(value) != _encoded(expected):
        raise ValueError('registration differs from its exact spec, policy, inputs or checker identity')
    return spec, value


def write_registration(spec, destination):
    """One exclusive file; no partial directory, sidecar or historical rewrite."""
    value = registration(spec)
    # Verify exact round-trip before opening any output file.
    raw = _encoded(value)
    verified(raw)
    from data_sheets_schema.resources import resource_path
    if Path(destination).resolve().is_relative_to(resource_path(Path('src/data_sheets_schema')).resolve()):
        raise ValueError('registration destination must not modify the captured checker source tree')
    with Path(destination).open('xb') as stream:
        stream.write(raw)
    return {'path': str(destination), 'sha256': _sha(raw), 'execution': EXECUTION}


def _arguments(spec):
    from data_sheets_schema.evidence_assertions import protocol_for_renderer
    paths = spec._agentic_artifact_paths
    result = {'report': Path(paths['report']), 'record': Path(paths['full']),
              'bundle': Path(spec.bundle), 'chunk_manifest': Path(spec.chunk_manifest),
              'protocol_version': protocol_for_renderer(spec.render_version)}
    if spec.manifest_used:
        result.update(source_manifest=Path(spec.manifest), project=spec.project)
    return result


def _commands(spec):
    from data_sheets_schema.api_runner import native_evidence_instructions
    expected = {shlex.join(policy.command_args(spec)): 'draft'}
    for line in native_evidence_instructions(spec).splitlines():
        try:
            words = shlex.split(line)
        except ValueError:
            continue
        if len(words) > 2 and words[:2] == [spec._agentic_toolchain['python'], '-m']:
            if words[2] == 'data_sheets_schema.evidence_assertions':
                expected[line] = 'final_evidence' if '--report' in words else 'evidence'
            elif words[2] == 'data_sheets_schema.source_review':
                expected[line] = 'source_inventory'
    return expected


def command_kind(command, spec):
    """The extra adapter admits only exact bound helper spellings."""
    if not isinstance(command, str):
        raise ValueError('helper command must be text')
    expected = _commands(spec)
    if command in expected:
        return expected[command]
    try:
        words = shlex.split(command)
    except ValueError as exc:
        raise ValueError('malformed helper command') from exc
    if any(module in words for module in (policy.MODULE, 'data_sheets_schema.evidence_assertions',
                                         'data_sheets_schema.source_review')):
        raise ValueError('helper command differs from the registered exact arguments')
    return None  # other commands are outside this adapter's permission scope


def verify_history(registration_raw, events):
    """Check supplied ordered native events against current saved draft bytes.

    This is an offline verifier, not an authenticated event recorder. It never
    treats model prose as tool evidence. A future controller must preserve the
    actual event stream and enforce the same boundaries before dispatch.
    """
    from data_sheets_schema import source_attribution_preflight as preflight
    spec, reg = verified(registration_raw)
    if not isinstance(events, list):
        raise ValueError('native events must be an ordered list')
    problems, observations = [], []
    pending, seen = {}, set()
    epoch, checks = 0, 0
    accepted = None
    terminal = False
    paths = spec._agentic_artifact_paths
    protected = {Path(p).resolve() for p in (paths['full'], paths['core'], spec.bundle, spec.chunk_manifest,
                 Path(paths['core']).parent / 'evidence/original_full.yaml',
                 Path(paths['core']).parent / 'evidence/original_core.yaml',
                 Path(paths['core']).parent / 'evidence/audit.json')}
    if spec.manifest_used:
        protected.add(Path(spec.manifest).resolve())
    report = Path(paths['report']).resolve()

    def problem(index, text):
        problems.append(f'event {index}: {text}')

    for index, event in enumerate(events):
        if not isinstance(event, dict):
            problem(index, 'event is not a mapping'); continue
        message = event.get('message')
        if message is None:
            continue  # init/status events have no tool obligations
        content = message.get('content') if isinstance(message, dict) else None
        if not isinstance(content, list):
            problem(index, 'message content is not an array'); continue
        for item in content:
            if not isinstance(item, dict):
                problem(index, 'message block is not a mapping'); continue
            if item.get('type') == 'tool_use':
                if event.get('type') != 'assistant':
                    problem(index, 'tool call is not an assistant event'); continue
                identity, name, args = item.get('id'), item.get('name'), item.get('input')
                if not isinstance(identity, str) or not identity or identity in seen or not isinstance(args, dict):
                    problem(index, 'missing/duplicate tool identity or malformed inputs'); continue
                seen.add(identity)
                if name not in ('Read', 'Write', 'Bash'):
                    problem(index, 'tool is outside the native Read/Write/Bash contract')
                    epoch += 1; accepted = None
                if terminal:
                    problem(index, 'tool continuation after a terminal or unusable check')
                kind = None
                if name == 'Bash':
                    try:
                        kind = command_kind(args.get('command'), spec)
                    except ValueError as exc:
                        problem(index, str(exc))
                    if kind and args.get('run_in_background') not in (None, False):
                        problem(index, 'selected helper cannot run in background')
                    if kind is None:
                        epoch += 1; accepted = None  # unknown shell effects cannot preserve a draft pass
                elif name in ('Write', 'Edit', 'MultiEdit'):
                    epoch += 1; accepted = None
                    target = args.get('file_path')
                    if checks and (not isinstance(target, str) or Path(target).resolve() != report):
                        problem(index, 'draft correction permits only the registered report path')
                    if checks and isinstance(target, str) and Path(target).resolve() in protected:
                        problem(index, 'draft correction attempts to change a protected input or record')
                if kind == 'draft':
                    checks += 1
                    accepted = None
                    if checks > reg['max_draft_checks']:
                        problem(index, 'registered draft-check limit exceeded')
                    if pending:
                        problem(index, 'draft check overlaps an unresolved tool call')
                if kind == 'final_evidence' and (accepted is None or accepted['epoch'] != epoch or pending):
                    problem(index, 'final evidence check precedes a current settled draft pass')
                pending[identity] = {'kind': kind, 'epoch': epoch, 'call_event': index}
            elif item.get('type') == 'tool_result':
                if event.get('type') != 'user':
                    problem(index, 'tool result is not a user event'); continue
                row = pending.pop(item.get('tool_use_id'), None)
                if row is None:
                    problem(index, 'result has no unique pending call'); continue
                kind = row['kind']
                if kind is None:
                    continue
                meta = event.get('tool_use_result')
                meta = meta if isinstance(meta, dict) else {}
                exit_code = meta.get('exitCode', meta.get('exit_code'))
                # Every supplied alias is authority. Python numeric equality
                # would let False/0.0 impersonate an integer zero (#4305).
                exits = [meta[k] for k in ('exitCode', 'exit_code') if k in meta]
                explicit = bool(exits) and all(type(code) is int and code == exit_code for code in exits)
                failed = (not explicit or exit_code != 0 or item.get('is_error') is not False
                          or any(meta.get(k) for k in ('interrupted', 'backgroundTaskId', 'background_task_id')))
                if kind != 'draft':
                    if failed:
                        terminal = True; accepted = None
                        problem(index, 'terminal evidence/source-inventory check failed or has unusable result')
                    continue
                observation = {'tool_use_id': item['tool_use_id'], **row, 'result_event': index,
                               'exit_code': exit_code, 'reported_passed': False,
                               'verified_against_current_saved_bytes': False}
                observations.append(observation)
                try:
                    payload = _json(item.get('content'))
                    if not isinstance(payload, dict):
                        raise ValueError('draft result is not an object')
                    if 'stdout' in meta and _encoded(_json(meta['stdout'])) != _encoded(payload):
                        raise ValueError('tool output and stdout disagree')
                    if type(payload.get('checked')) is not bool or type(payload.get('passed')) is not bool:
                        raise ValueError('draft result lacks strict checked/passed states')
                    if not explicit or exit_code not in (0, 1) or payload['checked'] is not True:
                        raise ValueError('unusable draft result')
                    if exit_code != preflight.exit_status(payload) or item.get('is_error') is not bool(exit_code):
                        raise ValueError('draft tool status contradicts its checker result')
                    if any(meta.get(k) for k in ('interrupted', 'backgroundTaskId', 'background_task_id')):
                        raise ValueError('draft result is interrupted or pending')
                    if exit_code == 0:
                        hashes = payload.get('input_sha256')
                        required = {'report', 'final_full'} | set(reg['inputs'])
                        if (not isinstance(hashes, dict) or set(hashes) != required
                                or any(not isinstance(h, str) or len(h) != 64
                                       or any(c not in '0123456789abcdef' for c in h) for h in hashes.values())
                                or any(hashes[k] != v['sha256'] for k, v in reg['inputs'].items())):
                            raise ValueError('draft pass has invalid selected input identities')
                        if pending or row['epoch'] != epoch or terminal:
                            raise ValueError('draft pass is stale, overlapping or after a terminal failure')
                        accepted = {'epoch': epoch, 'payload': payload, 'observation': observation}
                        observation['reported_passed'] = True
                        observation['input_sha256'] = hashes
                except (TypeError, ValueError, KeyError, OSError, RecursionError, yaml.YAMLError) as exc:
                    terminal = True; accepted = None
                    problem(index, str(exc))
    if pending:
        problems.append('history has unresolved tool calls')
    if accepted is not None:
        try:
            current = preflight.check_files(**_arguments(spec))
            if not current['passed'] or _encoded(current) != _encoded(accepted['payload']):
                problems.append('draft pass differs from actual checker on current saved bytes')
            else:
                accepted['observation']['verified_against_current_saved_bytes'] = True
        except (TypeError, ValueError, KeyError, OSError, RecursionError, yaml.YAMLError) as exc:
            problems.append(f'current draft cannot be verified: {exc}')
    else:
        problems.append('no current passing draft check')
    return {'instrument': 'native source attribution offline history v1', 'execution': EXECUTION,
            'scope': SCOPE, 'registration_sha256': _sha(registration_raw), 'checks': checks,
            'max_draft_checks': reg['max_draft_checks'], 'observations': observations,
            'draft_gate_passed': accepted is not None and not problems,
            'terminal_failure_observed': terminal, 'problems': problems}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='operation', required=True)
    prepare = commands.add_parser('prepare', help='write a new offline-only registration')
    for key in ('project', 'method', 'label', 'out'):
        prepare.add_argument('--' + key, required=True)
    prepare.add_argument('--render-spec', help='replay an already selected v1 spec instead of rendering inputs')
    prepare.add_argument('--bundle', type=Path)
    prepare.add_argument('--chunk-manifest', type=Path)
    prepare.add_argument('--source-manifest', type=Path)
    prepare.add_argument('--render-version', type=int, choices=range(16, 24))
    prepare.add_argument('--condition')
    prepare.add_argument('--runtime')
    prepare.add_argument('--provider')
    prepare.add_argument('--run-date', required=True)
    prepare.add_argument('--output-directory', type=Path)
    prepare.add_argument('--max-draft-checks', required=True, type=int)
    verify = commands.add_parser('verify-history', help='read saved registration and ordered native JSON events')
    verify.add_argument('--registration', required=True, type=Path)
    verify.add_argument('--events', required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        if args.operation == 'prepare':
            from data_sheets_schema.api_runner import RunSpec
            if args.render_spec:
                if any((args.bundle, args.chunk_manifest, args.source_manifest, args.render_version, args.output_directory, args.condition, args.runtime, args.provider)):
                    raise ValueError('recorded render-spec and new input selections are mutually exclusive')
                recorded = _json(Path(args.render_spec).read_bytes())
                if (recorded.get('native_source_attribution_max_checks') != args.max_draft_checks
                        or recorded.get('run_date') != args.run_date):
                    raise ValueError('explicit limit/date differs from the selected render spec')
                spec = RunSpec.from_render_spec(recorded, project=args.project, method=args.method, label=args.label)
            else:
                if not args.bundle or not args.chunk_manifest or not args.render_version:
                    raise ValueError('new selection requires bundle, chunk-manifest and render-version')
                spec = RunSpec(project=args.project, arm='baseline', method=args.method, label=args.label,
                    bundle=args.bundle.absolute(), chunk_manifest=args.chunk_manifest.absolute(),
                    manifest=args.source_manifest.absolute() if args.source_manifest else None,
                    render_version=args.render_version, condition=args.condition or 'generic_v9', runtime=args.runtime or 'Claude Code',
                    provider=args.provider or 'Anthropic', run_date=args.run_date, out_dir=args.output_directory,
                    native_source_attribution_version=1, native_source_attribution_max_checks=args.max_draft_checks)
            result = write_registration(spec, args.out)
        else:
            result = verify_history(args.registration.read_bytes(), _json(args.events.read_bytes()))
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
        return int(args.operation == 'verify-history' and not result['draft_gate_passed'])
    except (ValueError, KeyError, TypeError, OSError, RecursionError, yaml.YAMLError) as exc:
        print(json.dumps({'execution': EXECUTION, 'error': str(exc)}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
