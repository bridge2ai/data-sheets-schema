#!/usr/bin/env python3
"""Build the offline prefix of a manifest-declared native packet (G13).

Explicit repository inputs -> validated receipt policy, selection and byte pins.
Exit 2 is an expected dependency stop, 1 a refusal, 0 is reserved for completion.
This command NEVER probes, captures, authorizes, reserves, or launches. It only
writes a NEW output directory. Downstream human documents are not templates
filled with fabricated approval values. See the adjacent review adapter and
notes/native_canary_runbook_DRAFT_20261112.md for the unresolved live stages.
"""
from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import os
from pathlib import Path
import sys


# Lead ruling under NP1 item (ap), 2026-11-13; common to the canary and stratum.
# These are declared operating bounds, not the source's permissive ceilings.
STRATUM_BOUNDS = {
    'max_workers': 64, 'max_populated_paths': 32768, 'max_paths_per_worker': 8192,
    'max_submissions': 128, 'max_history_records': 1024,
    'max_inventory_bytes': 2000000, 'max_input_bytes': 4000000,
    'max_authority_bytes': 16000000, 'max_evidence_bytes': 256000000,
    'max_history_bytes': 48000000, 'max_request_bytes': 32000000,
    'max_response_bytes': 4000000,
}


class OfflineViolation(RuntimeError):
    pass


def physical(path, *, exists=True):
    path = Path(path)
    if not path.is_absolute() or path != path.resolve(strict=exists):
        raise ValueError('path must be absolute and physical: ' + str(path))
    return path


def pin(path, raw=None):
    path = physical(path)
    raw = path.read_bytes() if raw is None else raw
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def write_new(path, raw):
    # O_EXCL also refuses a final symlink. Main's audit guard constrains the parent.
    with Path(path).open('xb') as stream:
        stream.write(raw)


def offline_guard(output):
    """Irreversible per-process audit barrier; the CLI never spawns children.

    Covers Python-level subprocess/socket and filesystem mutation APIs, including
    lazy dependency imports. Run under the provided OS sandbox for independent
    enforcement; this is not a sandbox for arbitrary malicious native extensions.
    """
    output = physical(output, exists=False)
    def writable(path):
        if isinstance(path, int):
            raise OfflineViolation('file descriptor mutation is not a packet output')
        candidate = Path(os.fsdecode(path)).absolute().resolve()
        if candidate != output and not candidate.is_relative_to(output):
            raise OfflineViolation('write outside output directory: ' + str(candidate))
    def audit(event, args):
        if (event.startswith('socket.') or event.startswith('subprocess.')
                or event in {'os.system', 'os.posix_spawn', 'os.fork', 'os.forkpty', 'os.exec', 'pty.spawn'}):
            raise OfflineViolation('offline packet builder forbids ' + event)
        if event == 'open':
            path, mode, flags = args
            if ((isinstance(mode, str) and any(x in mode for x in 'wax+'))
                    or flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND)):
                writable(path)
        elif event in {'os.mkdir', 'os.remove', 'os.rmdir', 'os.chmod', 'os.chown', 'os.truncate', 'os.utime'}:
            writable(args[0])
        elif event in {'os.rename', 'os.link'}:
            writable(args[0]); writable(args[1])
        elif event == 'os.symlink':
            raise OfflineViolation('packet outputs cannot be symlinks')
    sys.addaudithook(audit)


def parser():
    p = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    for name in ('checkout', 'output', 'source-manifest', 'bundle', 'chunk-manifest', 'context', 'full-schema', 'core-schema', 'stage-root'):
        p.add_argument('--'+name, type=Path, required=True)
    for name in ('project', 'profile', 'registration-id', 'label'):
        p.add_argument('--'+name, required=True)
    return p


def build(args):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from native_packet_review_inputs import source_contract
    from data_sheets_schema import api_runner, chunking, native_shared_contract as c
    from data_sheets_schema import native_shared_selection as selection
    from data_sheets_schema.profiles import declared_profile, profile_named
    from data_sheets_schema.registry import load_registry
    from data_sheets_schema.schema_snapshot import capture_schema
    from data_sheets_schema.resources import resource_path

    if physical(Path(api_runner.__file__)).parent.parent != args.checkout / 'src':
        raise ValueError('foreign project package namespace')
    registry = load_registry(args.source_manifest)
    if not registry.declares(args.project) or registry.bundle(args.project).resolve() != args.bundle:
        raise ValueError('project or bundle differs from the selected manifest declaration')
    if declared_profile(args.source_manifest) != args.profile:
        raise ValueError('explicit profile differs from source manifest declaration')
    profile = profile_named(args.profile)  # Deliberately never select_profile/env.
    name = chunking.canonical_name(args.bundle, source_manifest=args.source_manifest)
    chunking.validate_manifest_mapping(chunking.load_manifest(args.chunk_manifest), args.bundle.read_bytes(), name)
    schemas = {}
    for role, cls, path, installed in (
        ('full_schema', 'Dataset', args.full_schema, api_runner.FULL_SCHEMA_PATH),
        ('core_schema', 'CoreDataset', args.core_schema, api_runner.CORE_SCHEMA_PATH),
    ):
        if path != resource_path(installed).absolute():
            raise ValueError('schema differs from installed production root: ' + role)
        captured = capture_schema(path, strict=True)
        schemas[role] = {'root': str(path), 'root_class': cls,
            'sources': [{'name': str(n), **pin(p, raw)} for n, p, raw in captured.sources]}
    assets = selection.capture_assets()
    receipt = {'kind': c.KINDS['receipt_policy'], 'version': c.VERSION,
        'registration_id': args.registration_id, 'condition': c.CONDITION,
        'runtime_policy_sha256': selection.RECEIPT_POLICY_SHA256,
        'receipt_instrument_version': source_contract()['receipt_instrument_version'],
        'coverage_floor': {'state': 'pending', 'mode': 'diagnostic_pilot'}}
    receipt_raw = c.canonical(receipt)
    c.parse_receipt_policy(receipt_raw, selection.RECEIPT_POLICY_SHA256)
    receipt_path = args.output / 'receipt-policy.json'
    write_new(receipt_path, receipt_raw)
    axes = {k: v for k, v in selection.descriptor().items()
            if k not in {'typed_protocol', 'projection', 'receipt_policy', 'assets'}}
    selection_path = args.output / 'selection.json'
    doc = {'kind': c.KINDS['selection'], 'version': c.VERSION,
        'registration_id': args.registration_id, 'registration_path': str(selection_path),
        'run': {'project': args.project, 'arm': 'BASELINE (input documents only)',
                'method': 'claudecode_direct', 'label': args.label},
        'selection': {**axes, 'descriptor_sha256': selection.descriptor_capture().sha256,
                      'assets': {a.pin.role[len('asset:'):]: pin(a.pin.path, a.raw) for a in assets}},
        'inputs': {'project': args.project, **{name: pin(getattr(args, name)) for name in
                    ('source_manifest', 'bundle', 'chunk_manifest', 'context')}, **schemas,
                   'profile': {'name': profile.name, 'basis': 'explicit caller; source manifest agrees',
                               'vocabulary': None if profile.pin_path is None else pin(profile.pin_path.absolute())}},
        'receipt_policy': pin(receipt_path, receipt_raw), 'bounds': dict(STRATUM_BOUNDS),
        'stage_root': str(args.stage_root)}
    raw = c.canonical(doc)
    c.parse_selection(raw)
    write_new(selection_path, raw)
    captured = selection.capture(selection_path)
    # Full production capture rereads all exact pins and validates schema/context/assets.
    snapshot = {'scope': 'DRAFT OFFLINE INPUTS ONLY; NOT REGISTRATION OR AUTHORIZATION',
        'running_source_contract': source_contract(),
        'selection': pin(selection_path), 'receipt_policy': pin(receipt_path),
        'descriptor_sha256': captured.descriptor.sha256,
        'schema_sources': {role: value['sources'] for role, value in schemas.items()},
        'assets': doc['selection']['assets'], 'profile': doc['inputs']['profile'],
        'protected_RunSpec_has_native_shared_generation_version':
            'native_shared_generation_version' in inspect.signature(api_runner.RunSpec).parameters}
    write_new(args.output / 'input-inventory.json', c.canonical(snapshot))
    return {'status': 'dependency_stop', 'scope': snapshot['scope'],
        'completed': ['receipt-policy.json', 'selection.json', 'input-inventory.json'],
        'needed': 'Owner-approved provisional-runtime.json and D117 authorization.json, then actual saved observation manifest/transcript/request; no final runtime can be prepared without them.',
        'producer_command': 'python -m data_sheets_schema.native_generation observation-probe --authorization /ABS/authorization.json --runtime /ABS/provisional-runtime.json --account-choice /ABS/observation-account-choice.json',
        'producer_authorization': 'Owner AUTHORIZE_TWO_SCRIPTED_NATIVE_PROBES required. Command is documented only, never run by this builder.',
        'subsequent_preparer': 'data_sheets_schema.native_u4b_runtime.prepare_runtime(runtime, probe_init_path=..., native_request_path=..., updater_source=..., updater_root=..., thinking_setting=..., thinking_basis=..., observation_probe_path=..., admission_policy=...)',
        'protected_source_status': 'RunSpec native integration present' if snapshot['protected_RunSpec_has_native_shared_generation_version'] else 'This base lacks RunSpec native_shared_generation_version; preparation must wait for approved merged integration.',
        'reservation_performed': False}


def main(argv=None):
    args = parser().parse_args(argv)
    args.checkout = physical(args.checkout)
    args.output = physical(args.output, exists=False)
    if Path.cwd().resolve() != args.checkout:
        raise ValueError('run from the explicit checkout root; no ambient resource fallback')
    for name in ('source_manifest', 'bundle', 'chunk_manifest', 'context', 'full_schema', 'core_schema'):
        setattr(args, name, physical(getattr(args, name)))
    args.stage_root = physical(args.stage_root, exists=False)
    if (args.stage_root.exists() or args.output == args.stage_root
            or args.output.is_relative_to(args.stage_root) or args.stage_root.is_relative_to(args.output)):
        raise ValueError('stage root must remain fresh and disjoint from immutable packet output')
    if args.output.exists():
        raise FileExistsError('refusing existing output directory: ' + str(args.output))
    physical(args.output.parent)
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(args.checkout / 'src'))
    offline_guard(args.output)
    args.output.mkdir()  # No parents created, exclusive output ownership.
    try:
        result = build(args)
        code = 2
    except Exception as exc:
        result = {'status': 'production_refusal', 'exception': type(exc).__name__, 'message': str(exc),
                  'scope': 'DRAFT INCOMPLETE; NOT REGISTRATION OR AUTHORIZATION', 'reservation_performed': False}
        code = 1
    write_new(args.output / 'status.json', (json.dumps(result, indent=2)+'\n').encode())
    print(json.dumps(result, indent=2))
    return code


if __name__ == '__main__':
    raise SystemExit(main())
