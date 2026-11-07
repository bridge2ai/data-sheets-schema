"""Input-only D reconstruction from verified preparation and explicit C inputs.

Proposal/envelope verification belongs to native_shared_registration_orchestration.
The fixed A entry keeps its exact signature and refuses the unresolved explicit
projection handoff; it never borrows ambient modules or invents C authority.
"""
from __future__ import annotations
from pathlib import Path
import re
import sys

from . import native_shared_contract as c
from . import native_shared_controller as composition
from . import native_shared_policy as policy
from . import native_shared_controls as pure_controls
from .native_shared_runtime_values import validate_runtime, POLICY_ENV, FLAGS
from .native_shared_evidence import read_regular
from .native_execution_engine import GATES

ROOT = Path(__file__).resolve().parents[2]
AUTHORITY_VERSION = 2
KIND = 'd4d_native_shared_execution_registration_v2'
VERSION = 2
EXECUTION = 'requires_exact_independent_review_ci_permission_and_owner_launch_evidence'



def environment(runtime, selected, spec, config_directory):
    """Derive the exact isolated child environment without inherited secrets.

    RunSpec boundary: guarded
    """
    from .api_runner import _require_registered_input_spellings
    _require_registered_input_spellings(spec)
    return {**runtime['environment'], **POLICY_ENV,
        'CLAUDE_CONFIG_DIR': str(config_directory),
        'PYTHONPATH': str(ROOT / 'src'), 'VIRTUAL_ENV': sys.prefix,
        'D4D_LAUNCH_INSTRUCTION': selected['instruction_path'],
        'D4D_MANIFEST': str(spec.manifest), 'D4D_PROFILE': spec.profile}


def command(runtime, selected, effective_system, attempt_id):
    """Compose argv only; the execution engine owns independently gated dispatch."""
    from .native_shared_permissions import _permission_protocol
    protocol = _permission_protocol()
    return [runtime['executable']['path'], *FLAGS, '--effort', runtime['effort'],
        '--model', runtime['model'], '--name', attempt_id,
        '--max-budget-usd', runtime['budget_guard_usd'],
        *protocol.permission_arguments(selected['policy']),
        '--system-prompt', effective_system]


def _read(path, label, limit):
    return read_regular(str(path), label, max_bytes=limit).captured.raw


def _selection(raw):
    selected, spec, captured = composition.reconstruct_composition(raw)
    doc = c.parse_selection(selected['selection_raw_json'].encode('utf-8'))
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
        path = ROOT / relative
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
        'permission_environment': environment(runtime, selected, spec, config_directory),
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
    protected += [ROOT / p for p in ('src', 'notes', 'scripts', 'tests', 'project', '.git', '.github', '.claude')]
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


def _registration_body(composition_path, system_path, *, permission_probe_path, attempt_id,
                 attempt_directory, evidence_directory, max_draft_checks, preparation_raw, controls, controller_sources, receipt_origin_version=0):
    """Prepare E, without consuming an attempt or asserting actual permission."""
    pure_controls.require_controls(controls)
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
    selected, spec, doc, runtime = _selection(raw)
    if max_draft_checks != selected['max_draft_checks']:
        raise ValueError('execution draft allowance differs from selected composition')
    if selected['working_directory'] != str(Path.cwd().resolve()):
        raise ValueError('composition cwd differs from actual execution preparation cwd')
    system = _read(paths['system_path'], 'system', c.HARD_LIMITS['input_bytes'])
    if not system.decode('utf-8').strip():
        raise ValueError('system instructions must be explicit nonblank UTF-8')
    if selected['preparation_raw_json'].encode('utf-8') != preparation_raw:
        raise ValueError('composition differs from caller-verified preparation bytes')
    preparation = composition.captured_preparation_body(preparation_raw)
    dependencies = preparation['dependencies']
    if dependencies != selected['dependencies']:
        raise ValueError('execution preparation differs from current v2 authority')
    effective = system.decode('utf-8') + policy.command_guidance(selected['policy'])
    config = Path(paths['attempt_directory']) / 'cli_config'
    expected = permission_expectation(runtime, selected, spec, effective, config, dependencies)
    probe = _read(paths['permission_probe'], 'saved permission', c.HARD_LIMITS['permission_wire_bytes'])
    from .native_shared_permissions import verify_saved_probe
    checked = verify_saved_probe(probe, expected=expected, controls=controls,
        controller_sources=controller_sources)
    if checked.get('checked') is not True or checked.get('passed') is not True:
        raise ValueError('native shared saved permission observations are not complete and passing')
    argv = command(runtime, selected, effective, attempt_id)
    value = {'kind': KIND, 'schema_version': VERSION, 'execution': EXECUTION, 'attempt_id': attempt_id, **paths,
        'job_id': preparation['job_id'], 'preparation_raw_json': preparation_raw.decode('utf-8'),
        'preparation_sha256': c.sha(preparation_raw),
        'execution_gates': list(GATES),
        'runtime': runtime, 'max_draft_checks': max_draft_checks, 'selection_sha256': selected['selection_sha256'],
        'runtime_declaration_sha256': selected['runtime_sha256'], 'working_directory': selected['working_directory'],
        'dependencies': dependencies, 'composition_raw_json': raw.decode('utf-8'), 'composition_sha256': c.sha(raw),
        'system_sha256': c.sha(system), 'effective_system': effective, 'effective_system_sha256': c.sha(effective.encode('utf-8')),
        'instruction_sha256': selected['instruction_sha256'], 'permission_probe_sha256': c.sha(probe),
        'permission_expected_sha256': c.sha(c.canonical(expected)), 'permission_observations': checked,
        'argv': argv, 'environment': environment(runtime, selected, spec, config),
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
            or preparation != composition.captured_preparation_body(preparation_raw)):
        raise ValueError('execution authority changed during capture')
    pure_controls.require_controls(controls)
    return value


def _require_integrated_gate_implementation():
    try:
        from .native_shared_execution import require_gate_implementations
        require_gate_implementations()
    except (ImportError, AttributeError) as exc:
        raise ValueError('native shared execution gate implementation is incomplete') from exc


def rebuild_v2_body(*, preparation_raw, composition_path, system_path,
                    permission_probe_path, attempt_id, attempt_directory,
                    evidence_directory, max_draft_checks, receipt_origin_version):
    """Fresh input-only reconstruction for A's exact consumer interface.

    No submitted execution body or derived verdict is accepted. A's fixed nine
    inputs contain no live C classifier projection. That explicit handoff
    remains an unmet integration requirement, separate from graph acceptance.
    Ordinary proposal reconstruction remains distinct from execution admission.
    """
    if (type(preparation_raw) is not bytes or not preparation_raw
            or len(preparation_raw) > c.HARD_LIMITS['request_bytes']):
        raise ValueError('v2 consumer preparation requires bounded nonempty bytes')
    try:
        preparation_raw.decode('utf-8')
    except UnicodeDecodeError as exc:
        raise ValueError('v2 consumer preparation requires UTF-8 bytes') from exc
    # A has verified preparation_raw before this fixed entry, but supplies no
    # live C classifier projection. Never deserialize a carrier, consult hidden
    # process state or weaken permission reconstruction to manufacture one.
    raise ValueError('fixed A3 rebuild has no explicit C classifier projection handoff')



def execution_paths_v2(body, *, fresh, extra_protected):
    """Recheck physical identities and all unspent native stage reservations."""
    if type(fresh) is not bool:
        raise ValueError('fresh reservation selection must be a boolean')
    if (type(body) is not dict or body.get('kind') != KIND
            or type(body.get('schema_version')) is not int or body['schema_version'] != VERSION):
        raise ValueError('reservation requires the v2 execution body')
    composition_raw = body['composition_raw_json'].encode('utf-8')
    selected = composition.verified_composition(composition_raw)
    if c.sha(composition_raw) != body['composition_sha256']:
        raise ValueError('reservation composition differs from execution')
    return _paths(body, selected, fresh=fresh, extra_protected=extra_protected)
