"""Closed offline E joining one S/C/R and checked saved permission evidence.

No executable discovery, native invocation, auth lookup or provider request.
The shared lifetime separately requires exact review, CI and owner authority.
"""
from __future__ import annotations

from pathlib import Path
from contextlib import nullcontext
import re
import sys

from . import native_shared_contract as c
from . import native_shared_controller as composition
from . import native_shared_policy as policy
from . import native_execution_registration as inherited
from . import native_execution_authority as authority
from .native_shared_evidence import read_regular

KIND = c.KINDS['execution']
VERSION = 1
EXECUTION = inherited.EXECUTION
_closed = inherited._closed
_text = inherited._text
validate_runtime = inherited.validate_runtime
executable_identity = inherited.executable_identity


def _read(path, label, limit):
    return read_regular(str(path), label, max_bytes=limit).captured.raw


def _selection(raw):
    return _selected_composition(composition.verified_composition(raw))


def _selection_in_scope(raw):
    from . import native_owner_profile_v1 as owner_profile
    with owner_profile._reconstruction_controls():
        return _selected_composition(composition._verified_composition_in_scope(raw))


def _selected_composition(selected):
    from .api_runner import RunSpec
    doc = c.parse_selection(selected['selection_raw_json'].encode('utf-8'))
    run = doc['run']
    spec = RunSpec.from_render_spec(selected['render_spec'], project=run['project'], method=run['method'], label=run['label'])
    runtime = validate_runtime(c.strict_json(selected['runtime_raw_json'].encode('utf-8'), 'sole R'))
    if (spec.provider, spec.reasoning_effort) != (runtime['provider'], runtime['effort']):
        raise ValueError('execution runtime differs from selected provider/effort')
    from .agentic_runtime import toolchain
    if c.canonical(spec._agentic_toolchain) != c.canonical(toolchain()):
        raise ValueError('execution requires the exact local helper toolchain')
    return selected, spec, doc, runtime


def _production_sources(dependencies):
    """Actual nonempty Python members; complete raw closure also remains in E."""
    rows = []
    for relative, digest in sorted(dependencies['base']['package_sources'].items()):
        if not relative.endswith('.py'):
            continue
        path = authority.ROOT / relative
        raw = _read(str(path), 'production source', c.HARD_LIMITS['input_bytes'])
        if c.sha(raw) != digest:
            raise ValueError('production source changed while preparing permission authority')
        if raw:
            module = '.'.join(Path(relative).with_suffix('').parts[1:])
            rows.append({'module': module, 'path': str(path), 'sha256': digest, 'bytes': len(raw)})
    if not 0 < len(rows) <= c.HARD_LIMITS['authority_files']:
        raise ValueError('production source closure exceeds its bound')
    return rows


def permission_expectation(runtime, selected, spec, effective_system, config_directory, dependencies):
    """Expected bindings are selected software/input authority, never probe flags."""
    from .native_shared_permissions import recipe
    doc = c.parse_selection(selected['selection_raw_json'].encode('utf-8'))
    commands = policy.helper_commands(selected['policy'])
    raw = selected['selection_raw_json'].encode('utf-8')
    expected = {'kind': c.KINDS['permission_expected'], 'version': 1, 'runtime': runtime,
        'selection': {'path': doc['registration_path'], 'sha256': c.sha(raw), 'bytes': len(raw)},
        'policy': selected['policy'], 'commands': {'stage': commands['advance'],
            'draft': commands['draft'], 'final_evidence': commands['final_evidence'], 'recorder': commands['recorder']},
        'source': doc['inputs']['bundle'],
        'permission_environment': inherited.environment(runtime, selected, spec, config_directory),
        'controller_sources': selected['controller_sources'],
        'instruction_sha256': selected['instruction_sha256'], 'system_sha256': c.sha(effective_system.encode('utf-8')),
        'production_sources': _production_sources(dependencies)}
    expected['probe_recipe'] = recipe(expected)
    return expected


def _paths(value, selected, *, fresh, extra_protected=()):
    """Actual static envelope, including separate new stage reservation."""
    doc = c.parse_selection(selected['selection_raw_json'].encode('utf-8'))
    outputs = sorted({Path(p) for p in selected['policy']['readonly_lookups']['output_directories']})
    reserved = [Path(value[k]) for k in ('attempt_directory', 'evidence_directory')] + outputs
    protected = [Path(value[k]) for k in ('composition', 'system_path', 'permission_probe')]
    protected += [Path(selected['runtime_path']), Path(value['runtime']['executable']['path'])]
    protected += [Path(p) for p in selected['policy']['readonly_lookups']['inputs']]
    protected += [authority.ROOT / p for p in ('src', 'notes', 'scripts', 'tests', 'project', '.git', '.github', '.claude')]
    protected += [Path(p).resolve() for p in extra_protected]
    if Path(doc['stage_root']) not in outputs:
        raise ValueError('new execution requires its exact stage reservation')
    for path in reserved:
        if not path.is_absolute() or path != path.resolve() or path.is_symlink():
            raise ValueError('reserved paths must be canonical physical paths')
        if fresh and (path.exists() or path.is_symlink()):
            raise ValueError('attempt, evidence, output and stage directories must be new; spent identities cannot resume')
        if any(path == p or c._strict_path_ancestor(path, p)
               or c._strict_path_ancestor(p, path) for p in protected):
            raise ValueError('reserved directory overlaps immutable authority/input or protected source')
    for index, path in enumerate(reserved):
        if any(path == other or c._strict_path_ancestor(path, other)
               or c._strict_path_ancestor(other, path) for other in reserved[index + 1:]):
            raise ValueError('attempt, evidence, output and stage reservations must be disjoint')
    if any(not path.parent.is_dir() for path in reserved[:2]):
        raise ValueError('attempt and evidence parents must already exist')
    return reserved


def registration(composition_path, system_path, *, permission_probe_path, attempt_id,
                 attempt_directory, evidence_directory, max_draft_checks, receipt_origin_version=0):
    """Prepare E, without consuming an attempt or asserting actual permission."""
    return _registration(composition_path, system_path, permission_probe_path=permission_probe_path,
        attempt_id=attempt_id, attempt_directory=attempt_directory, evidence_directory=evidence_directory,
        max_draft_checks=max_draft_checks, receipt_origin_version=receipt_origin_version, controls=None)


def _registration_in_scope(composition_path, system_path, *, permission_probe_path, attempt_id,
                           attempt_directory, evidence_directory, max_draft_checks, receipt_origin_version=0):
    """Prepare all of selected E in the admitted scope; no public dispatch."""
    from . import native_owner_profile_v1 as owner_profile
    with owner_profile._reconstruction_controls() as controls:
        return _registration(composition_path, system_path, permission_probe_path=permission_probe_path,
            attempt_id=attempt_id, attempt_directory=attempt_directory, evidence_directory=evidence_directory,
            max_draft_checks=max_draft_checks, receipt_origin_version=receipt_origin_version, controls=controls)


def _registration(composition_path, system_path, *, permission_probe_path, attempt_id,
                  attempt_directory, evidence_directory, max_draft_checks, receipt_origin_version, controls):
    return _registration_capture(composition_path, system_path,
        permission_probe_path=permission_probe_path, attempt_id=attempt_id,
        attempt_directory=attempt_directory, evidence_directory=evidence_directory,
        max_draft_checks=max_draft_checks, receipt_origin_version=receipt_origin_version,
        controls=controls)[0]


def _registration_capture(composition_path, system_path, *, permission_probe_path, attempt_id,
                          attempt_directory, evidence_directory, max_draft_checks,
                          receipt_origin_version, controls):
    """Return the fresh reconstruction's inputs, never a reusable admission."""
    from . import native_owner_profile_v1 as owner_profile
    context = nullcontext(None) if controls is None else owner_profile._reconstruction_controls()
    with context as current:
        if current is not controls:
            raise ValueError('selected registration requires the exact current controls map')
        return _registration_body(composition_path, system_path, permission_probe_path=permission_probe_path,
            attempt_id=attempt_id, attempt_directory=attempt_directory, evidence_directory=evidence_directory,
            max_draft_checks=max_draft_checks, receipt_origin_version=receipt_origin_version, controls=controls)


def _registration_body(composition_path, system_path, *, permission_probe_path, attempt_id,
                       attempt_directory, evidence_directory, max_draft_checks, receipt_origin_version, controls):
    if type(receipt_origin_version) is not int or receipt_origin_version not in (0, 1):
        raise ValueError('receipt_origin_version must be exact integer 0 or 1')
    if type(attempt_id) is not str or re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,127}', attempt_id) is None:
        raise ValueError('attempt_id must be an explicit safe component')
    c.positive_int(max_draft_checks, 'execution draft-check allowance')
    paths = {key: c.canonical_path(str(path), key) for key, path in {
        'composition': composition_path, 'system_path': system_path, 'permission_probe': permission_probe_path,
        'attempt_directory': attempt_directory, 'evidence_directory': evidence_directory}.items()}
    if Path(paths['attempt_directory']).name != attempt_id:
        raise ValueError('attempt basename must equal its one-use identity')
    raw = _read(paths['composition'], 'composition', c.HARD_LIMITS['request_bytes'])
    selected, spec, doc, runtime = _selection(raw) if controls is None else _selection_in_scope(raw)
    if max_draft_checks != selected['max_draft_checks']:
        raise ValueError('execution draft allowance differs from selected composition')
    if selected['working_directory'] != str(Path.cwd().resolve()):
        raise ValueError('composition cwd differs from actual execution preparation cwd')
    system = _read(paths['system_path'], 'system', c.HARD_LIMITS['input_bytes'])
    if not system.decode('utf-8').strip():
        raise ValueError('system instructions must be explicit nonblank UTF-8')
    dependencies = (authority.dependency_identity() if controls is None
                    else authority.dependency_identity(stream_snapshot_profile=1))
    if controls is not None and c.canonical(dependencies['stream_snapshot_profile']) != c.canonical(selected['stream_snapshot_profile']):
        raise ValueError('selected execution dependencies differ from the composition profile')
    guidance = (policy.command_guidance(selected['policy']) if controls is None else
                policy._command_guidance_in_scope(selected['policy'], selected['stream_snapshot_profile']))
    effective = system.decode('utf-8') + guidance
    config = Path(paths['attempt_directory']) / 'cli_config'
    expected = permission_expectation(runtime, selected, spec, effective, config, dependencies)
    probe = _read(paths['permission_probe'], 'saved permission', c.HARD_LIMITS['permission_wire_bytes'])
    from .native_shared_permissions import verify_saved_probe, _verify_saved_probe_in_scope
    checked = (verify_saved_probe(probe, expected=expected) if controls is None else
               _verify_saved_probe_in_scope(probe, expected=expected, profile=selected['stream_snapshot_profile']))
    if checked.get('checked') is not True or checked.get('passed') is not True:
        raise ValueError('native shared saved permission observations are not complete and passing')
    if controls is None:
        with authority.loaded_dependencies(dependencies) as loaded:
            argv = inherited.command(runtime, selected, effective, attempt_id, loaded)
    else:
        argv = inherited.command(runtime, selected, effective, attempt_id, controls)
    value = {'kind': KIND, 'version': VERSION, 'execution': EXECUTION, 'attempt_id': attempt_id, **paths,
        'runtime': runtime, 'max_draft_checks': max_draft_checks, 'selection_sha256': selected['selection_sha256'],
        'runtime_declaration_sha256': selected['runtime_sha256'], 'working_directory': selected['working_directory'],
        'dependencies': dependencies, 'composition_raw_json': raw.decode('utf-8'), 'composition_sha256': c.sha(raw),
        'system_sha256': c.sha(system), 'effective_system': effective, 'effective_system_sha256': c.sha(effective.encode('utf-8')),
        'instruction_sha256': selected['instruction_sha256'], 'permission_probe_sha256': c.sha(probe),
        'permission_expected_sha256': c.sha(c.canonical(expected)), 'permission_observations': checked,
        'argv': argv, 'environment': inherited.environment(runtime, selected, spec, config),
        'selection': {**doc['run'], 'render_spec': selected['render_spec']},
        'scope': 'Offline proposal only; requires exact independent review, CI and owner launch evidence. '
                 'Saved permission evidence is not cryptographic authentication, production helper validation or scientific acceptance.'}
    if receipt_origin_version:
        from .native_receipt_origin import declaration
        value['receipt_origin_reporting'] = declaration(value['attempt_directory'], spec._agentic_artifact_paths)
    _paths(value, selected, fresh=False)
    if (raw != _read(paths['composition'], 'composition', c.HARD_LIMITS['request_bytes'])
            or system != _read(paths['system_path'], 'system', c.HARD_LIMITS['input_bytes'])
            or probe != _read(paths['permission_probe'], 'saved permission', c.HARD_LIMITS['permission_wire_bytes'])
            or c.canonical(dependencies) != c.canonical(authority.dependency_identity() if controls is None
                else authority.dependency_identity(stream_snapshot_profile=1))):
        raise ValueError('execution authority changed during capture')
    return value, selected, spec, doc, runtime


def _execution_value(raw):
    value = c.strict_json(raw, 'native shared execution', c.HARD_LIMITS['request_bytes'])
    if (type(value) is not dict or value.get('kind') != KIND or type(value.get('version')) is not int
            or value['version'] != VERSION or value.get('execution') != EXECUTION):
        raise ValueError('not the selected native shared execution registration')
    return value


def _execution_profile(value):
    """Inspect both declarations before any default reconstruction/loader."""
    try:
        selector = authority._selector(value['dependencies'])
        selected = composition._composition_value(value['composition_raw_json'].encode('utf-8'))
    except (KeyError, AttributeError, TypeError) as exc:
        raise ValueError('incomplete native shared execution profile') from exc
    if selector == 0:
        if 'stream_snapshot_profile' in selected or 'stream_snapshot_profile' in value:
            raise ValueError('execution has a partial selected profile declaration')
        return None
    profile = value['dependencies']['stream_snapshot_profile']
    if (type(profile) is not dict or type(selected.get('stream_snapshot_profile')) is not dict
            or c.canonical(profile) != c.canonical(selected['stream_snapshot_profile'])
            or 'stream_snapshot_profile' in value):
        raise ValueError('execution and composition selected profiles differ')
    return profile


def _rebuild_execution(value, controls):
    return _rebuild_execution_capture(value, controls)[0]


def _rebuild_execution_capture(value, controls):
    origin_version = 0
    if 'receipt_origin_reporting' in value:
        from .native_receipt_origin import version
        origin_version = version(value)
    try:
        captured = _registration_capture(value['composition'], value['system_path'], permission_probe_path=value['permission_probe'],
            attempt_id=value['attempt_id'], attempt_directory=value['attempt_directory'],
            evidence_directory=value['evidence_directory'], max_draft_checks=value['max_draft_checks'],
            receipt_origin_version=origin_version, controls=controls)
    except (KeyError, TypeError) as exc:
        raise ValueError('incomplete native shared execution registration') from exc
    if c.canonical(value) != c.canonical(captured[0]):
        raise ValueError('execution registration differs from its selected authorities')
    return (value, *captured[1:])


def verified(raw):
    value = _execution_value(raw)
    if _execution_profile(value) is not None:
        raise ValueError('selected execution is not enabled in the public execution route')
    return _rebuild_execution(value, None)


def _verified_in_scope(raw):
    return _verified_capture_in_scope(raw)[0]


def _verified_capture_in_scope(raw):
    """Return one fully rebuilt E/C/spec join in its current owner scope."""
    from . import native_owner_profile_v1 as owner_profile
    value = _execution_value(raw)
    profile = _execution_profile(value)
    with owner_profile._reconstruction_controls(profile) as controls:
        return _rebuild_execution_capture(value, controls)


def _recheck_selected_capture(selected, spec, doc, runtime):
    """Fresh endpoint checks without regenerating already verified policy/text.

    This consumes only the just-returned reconstruction. The caller still owns
    its exact reader context, and no result is retained between callbacks.
    """
    from . import native_shared_selection as selections
    from . import native_owner_profile_v1 as owner_profile
    from .agentic_runtime import toolchain
    with owner_profile._reconstruction_controls(selected['stream_snapshot_profile']):
        current = selections.capture(doc['registration_path'])
        if (current.registration.raw != selected['selection_raw_json'].encode('utf-8')
                or current.generation_context() !=
                    selected['render_spec']['native_shared_generation_context']):
            raise ValueError('selected authority changed after execution reconstruction')
        actual_runtime = _read(selected['runtime_path'], 'runtime declaration', c.HARD_LIMITS['input_bytes'])
        if actual_runtime != selected['runtime_raw_json'].encode('utf-8'):
            raise ValueError('selected runtime changed after execution reconstruction')
        if c.canonical(validate_runtime(c.strict_json(actual_runtime))) != c.canonical(runtime):
            raise ValueError('selected executable changed after execution reconstruction')
        instruction = _read(selected['instruction_path'], 'instruction', c.HARD_LIMITS['request_bytes'])
        if (c.sha(instruction) != selected['instruction_sha256']
                or instruction != spec.instruction.encode('utf-8')):
            raise ValueError('selected instruction changed after execution reconstruction')
        if c.canonical(toolchain()) != c.canonical(spec._agentic_toolchain):
            raise ValueError('selected toolchain changed after execution reconstruction')
        if (selected['working_directory'] != str(Path.cwd().resolve())
                or selected['python'] != sys.executable or selected['python_version'] != sys.version):
            raise ValueError('selected process identity changed after execution reconstruction')
        outputs = {str(Path(spec._agentic_artifact_paths[role]).parent.resolve())
                   for role in ('full', 'core', 'report')}
        outputs.add(current.role('stage_root'))
        if sorted(outputs) != selected['policy']['readonly_lookups']['output_directories']:
            raise ValueError('selected output parents changed after execution reconstruction')
        if c.canonical(composition.inherited.controller_sources()) != c.canonical(selected['controller_sources']):
            raise ValueError('selected controller sources changed after execution reconstruction')
