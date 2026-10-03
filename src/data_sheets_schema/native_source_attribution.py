"""Opt-in native draft instruction identity; no execution authorization (#4304)."""
from __future__ import annotations

import hashlib
from pathlib import Path
import shlex

POLICY_PATH = Path('src/download/prompts/native_source_attribution_v1.md')
POLICY_SHA256 = 'e13f0bd8de8e4e28cd1c1216799defb7005f7e041698698a4478d824e8acc761'
MODULE = 'data_sheets_schema.source_attribution_preflight'
NATIVE_RUNTIMES = frozenset({'Claude Code', 'Claude Code (direct)'})


def validate(version, *, native, renderer, max_checks):
    if type(version) is not int or version not in (0, 1):
        raise ValueError('native_source_attribution_version must be 0 or 1')
    if version:
        if not native or type(renderer) is not int or renderer not in range(16, 24):
            raise ValueError('native source attribution v1 requires native Claude Code renderer 16 through 23')
        if type(max_checks) is not int or max_checks < 1:
            raise ValueError('native source attribution requires an explicit positive max_checks')
    elif max_checks is not None:
        raise ValueError('native source attribution max_checks requires opt-in version 1')


def policy_text():
    from data_sheets_schema.resources import resource_path
    raw = resource_path(POLICY_PATH).read_bytes()
    if hashlib.sha256(raw).hexdigest() != POLICY_SHA256:
        raise ValueError('native source attribution v1 policy differs from its frozen SHA256')
    return raw.decode('utf-8').split('## Prompt body', 1)[1].strip()


def policy_identity():
    policy_text()
    return {'version': 1, 'path': str(POLICY_PATH), 'sha256': POLICY_SHA256}


def command_args(spec):
    from data_sheets_schema.evidence_assertions import protocol_for_renderer
    validate(spec.native_source_attribution_version, native=spec.runtime in NATIVE_RUNTIMES,
             renderer=spec.render_version, max_checks=spec.native_source_attribution_max_checks)
    if spec.native_source_attribution_version != 1:
        raise ValueError('draft command requires native source attribution version 1')
    if spec.chunk_manifest is None:
        raise ValueError('native draft preflight requires an explicitly resolved chunk manifest')
    paths = spec._agentic_artifact_paths
    args = [spec._agentic_toolchain['python'], '-m', MODULE,
            '--report', paths['report'], '--record', paths['full'],
            '--bundle', str(spec.bundle), '--chunk-manifest', str(spec.chunk_manifest),
            '--protocol-version', str(protocol_for_renderer(spec.render_version))]
    if spec.manifest_used:
        args += ['--source-manifest', str(spec.manifest), '--project', spec.project]
    return args


def instructions(spec):
    return ('\n\n## Native source-attribution draft preflight v1\n\n' + policy_text()
            + '\n\nRegistered maximum draft checks: '
            + str(spec.native_source_attribution_max_checks)
            + '. Execution requires a separately reviewed controller; offline registration alone '
              'does not authorize a run.\n\n' + shlex.join(command_args(spec)) + '\n\n')
