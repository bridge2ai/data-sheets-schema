"""Explicit offline native-shared composition and fixed callback controller.

Runtime binding reads and fingerprints supplied declarations only. Native
version/auth observations and dispatch belong exclusively to the execution
lifetime, after independently supplied permission and launch evidence.
"""
from __future__ import annotations

from pathlib import Path
import sys

from . import native_shared_contract as c
from . import native_shared_render as render
from . import native_shared_selection as selection
from . import native_shared_policy as policy
from . import native_attribution_controller as inherited
from . import native_execution_registration as runtime_registration
from .native_shared_evidence import read_regular

KIND = 'd4d_native_shared_callback_composition'
VERSION = 1
EXECUTION = 'offline_composition_only_requires_separate_native_execution_registration'


def bind_runtime(spec, runtime_path, max_draft_checks):
    """Bind the one explicit R and allowance, without executing any binary."""
    if render.validate_spec(spec) is None:
        raise ValueError('runtime binding requires explicitly selected native26')
    c.positive_int(max_draft_checks, 'native draft-check allowance')
    artifact = read_regular(str(runtime_path), 'runtime_declaration',
                            max_bytes=c.HARD_LIMITS['input_bytes']).captured
    runtime = runtime_registration.validate_runtime(c.strict_json(artifact.raw, 'runtime declaration'))
    if (runtime['provider'], runtime['effort']) != (spec.provider, spec.reasoning_effort):
        raise ValueError('runtime provider/effort differ from the explicit selected spec')
    previous = getattr(spec, '_native_shared_runtime_capture', None)
    if previous is not None and previous != artifact:
        raise ValueError('cannot rebind an existing native runtime authority')
    allowance = getattr(spec, '_native_shared_max_draft_checks', None)
    if allowance is not None and (type(allowance) is not int or allowance != max_draft_checks):
        raise ValueError('cannot rebind an existing native draft-check allowance')
    spec._native_shared_runtime_capture = artifact
    spec._native_shared_max_draft_checks = max_draft_checks
    return spec


def compose(spec, *, runtime_path, instruction_path, max_draft_checks):
    """Capture selected S/R/instruction/policy; this is not launch authority."""
    bind_runtime(spec, runtime_path, max_draft_checks)
    declared = render.validate_spec(spec)
    current = selection.capture(declared['registration_path'])
    if current.registration.raw != spec.native_shared_generation_registration.encode('utf-8'):
        raise ValueError('composition selection differs from actual S bytes')
    if current.generation_context() != render.metadata(spec)['native_shared_generation_context']:
        raise ValueError('composition generation context differs from captured S authority')
    spec._native_shared_generation_capture = current
    instruction = read_regular(str(instruction_path), 'instruction', max_bytes=c.HARD_LIMITS['request_bytes']).captured
    if instruction.raw != spec.instruction.encode('utf-8'):
        raise ValueError('composition instruction differs from the actual selected rendering')
    controls = inherited.load_controls()
    selected_policy = policy.command_policy(spec, instruction.pin.path, controls)
    runtime = spec._native_shared_runtime_capture
    return {'kind': KIND, 'version': VERSION, 'execution': EXECUTION,
        'selection_raw_json': current.registration.raw.decode('utf-8'),
        'selection_sha256': current.registration.pin.sha256,
        'runtime_path': runtime.pin.path, 'runtime_raw_json': runtime.raw.decode('utf-8'),
        'runtime_sha256': runtime.pin.sha256, 'max_draft_checks': max_draft_checks,
        'render_spec': spec.render_spec(), 'instruction_path': instruction.pin.path,
        'instruction_sha256': instruction.pin.sha256,
        'controller_sources': inherited.controller_sources(),
        'controller_sources_sha256': inherited.SOURCES_SHA256,
        'policy': selected_policy, 'policy_sha256': c.sha(c.canonical(selected_policy)),
        'working_directory': str(Path.cwd().resolve()), 'python': sys.executable, 'python_version': sys.version}


def verified_composition(raw):
    """Rebuild from exact captured metadata and recheck current S/R identities."""
    from .api_runner import RunSpec
    value = c.strict_json(raw, 'native shared composition', c.HARD_LIMITS['request_bytes'])
    if type(value) is not dict or value.get('kind') != KIND:
        raise ValueError('not a native shared callback composition')
    try:
        doc = c.parse_selection(value['selection_raw_json'].encode('utf-8'))
        run = doc['run']
        spec = RunSpec.from_render_spec(value['render_spec'], project=run['project'],
                                       method=run['method'], label=run['label'])
        expected = compose(spec, runtime_path=value['runtime_path'],
                           instruction_path=value['instruction_path'], max_draft_checks=value['max_draft_checks'])
    except (KeyError, AttributeError, TypeError) as exc:
        raise ValueError('malformed native shared callback composition') from exc
    if c.canonical(value) != c.canonical(expected):
        raise ValueError('native shared composition identity changed')
    return value
