"""Draft exact-location gate inventory from saved rehearsal documents, 2026-11-13.

Inputs are saved JSON artifacts only; outputs adjacent JSON. No source imports,
no production validators, and no claim that derived values have been verified.
Serves approved helper 3 reference-validation-context and gate-schema work.
"""
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
E = ROOT.parent
CURRENT = E / 'scratch-h3-environment-manifest-20261113/tests/final-boundaries-02/cases/popen-gw0/test_dispatch_recheck_rejects_0/SYNTHETIC-environment-only'
OLD = E / 'scratch-h3-packet-builder-20261112/tests/full-chain-rest-01/cases/full-chain-cohort0/SYNTHETIC-chain'
SOURCES = {
    'preparation': CURRENT / 'authority/preparation.json',
    'composition': CURRENT / 'authority/composition.json',
    'selection': CURRENT / 'authority/selection.json',
    'runtime': CURRENT / 'authority/runtime.json',
    'environment_manifest': CURRENT / 'authority/environment-manifest.json',
    'receipt_policy': CURRENT / 'authority/receipt-policy.json',
    'permission_probe': CURRENT / 'synthetic-runtime/probe-sequence/permission/permission-probe.json',
    'permission_expectation': CURRENT / 'synthetic-runtime/probe-sequence/expectation.json',
    'historical_execution_shape_only': OLD / 'synthetic-registration.json',
}

EMBEDDED = {'preparation_raw_json', 'composition_raw_json', 'selection_raw_json',
            'runtime_raw_json', 'raw_json', 'native_shared_generation_registration',
            'limits_basis', 'D4D_RENDER_SPEC'}
PROJECT_ROLES = {'bundle', 'chunk_manifest', 'source_manifest', 'context', 'scope'}
DERIVED_NAMES = {'instruction', 'instruction_sha256', 'effective_system', 'effective_system_sha256',
                 'preparation_sha256', 'composition_sha256', 'selection_sha256',
                 'runtime_declaration_sha256', 'runtime_sha256', 'permission_probe_sha256',
                 'permission_expected_sha256', 'policy_sha256', 'expectation_sha256',
                 'D4D_LAUNCH_INSTRUCTION'}
IDENTITIES = {'registration_id', 'attempt_id', 'job_id', 'session_id', 'label', 'project',
              'run_date', 'valid_from', 'valid_until', 'valid_through', 'created_at',
              'observed_at', 'started_at', 'finished_at', 'timestamp', 'device', 'inode',
              'working_directory', 'attempt_directory', 'evidence_directory', 'stage_root',
              'registration_path', 'system_path', 'permission_probe', 'composition_path',
              'instruction_path', 'runtime_path', 'python', 'PYTHONPATH', 'VIRTUAL_ENV',
              'HOME', 'PYSTOW_HOME', 'TMPDIR', 'CLAUDE_CONFIG_DIR'}
SCIENTIFIC = {'kind', 'version', 'schema_version', 'authority_version', 'execution',
              'condition', 'runtime', 'provider', 'model', 'effort', 'reasoning_effort',
              'max_draft_checks', 'method', 'arm', 'render_version', 'prompt_text_env',
              'registered_input_paths', 'native_shared_generation_version', 'python_version',
              'python_sha256', 'controller_sources_sha256', 'descriptor_sha256',
              'receipt_instrument_version', 'coverage_basis', 'floor_basis', 'profile',
              'profile_basis', 'name', 'root_class', 'schema', 'binary_sha256'}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()


def pin(path):
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def pointer(parts):
    return '/' + '/'.join(str(p).replace('~', '~0').replace('/', '~1') for p in parts)


def classify(role, parts, value):
    names = [str(p) for p in parts]
    leaf = names[-1] if names else ''
    # These are draft recognition rules, never installed as runtime catch-alls.
    # Output expands each result to one exact pointer; unresolved values hold.
    if role == 'environment_manifest':
        return 'must_equal', 'Environment semantic identity and installed RECORD manifest are fixed.'
    if 'package_sources' in names:
        return 'must_equal', 'Exact enumerated committed package-source roster and digest.'
    if ('modules' in names or 'additional_modules' in names) and leaf in {'path', 'sha256'}:
        return 'must_equal', 'Exact enumerated relative helper module location and digest.'
    if 'bounds' in names:
        return 'must_equal', 'Registered stratum constant bound; validate against supplied constant policy.'
    if leaf in EMBEDDED and isinstance(value, str) and value.lstrip().startswith(('{', '[')):
        return 'derived', 'Embedded JSON carrier: parse child document, production-reconstruct and verify serialization/hash; no exemption.'
    if leaf in DERIVED_NAMES:
        return 'derived', 'Reconstruct with reference production validator and candidate context; not validated by inventory.'
    if 'coverage_floor' in names or leaf in {'coverage_floor', 'floor'}:
        return 'floor_transition', 'Compare exact pending/numeric state and arithmetic to separately hashed floor input; basis remains fixed.'
    if leaf in IDENTITIES:
        return 'per_run', 'Explicit recorded host/run identity location; preserve internal consistency.'
    if 'inputs' in names and any(name in PROJECT_ROLES for name in names):
        return ('per_run', 'Input artifact location is per-run.') if leaf == 'path' else (
            'project_inputs', 'Check role content/size/hash against whole-file NP1b tuple.')
    if 'assets' in names or 'full_schema' in names or 'core_schema' in names:
        return ('per_run', 'Absolute artifact location changes; semantic asset role and content remain fixed.') if leaf == 'path' else (
            'must_equal', 'Selected prompt asset/schema closure content and role must remain equal.')
    if 'environment_manifest' in names:
        return ('per_run', 'Manifest path is a host location.') if leaf == 'path' else (
            'must_equal', 'Manifest bytes and sha256 bind fixed semantic environment identity.')
    if leaf in SCIENTIFIC:
        return 'must_equal', 'Explicit scientific/runtime/schema identity field; no exception inferred.'
    return None, 'Unclassified: hold until semantic role and production validation rule are explicitly assigned.'


def main():
    rows, containers, sources = [], [], {}
    for role, path in SOURCES.items():
        if not path.is_file():
            sources[role] = {'path': str(path), 'status': 'missing_saved_sample'}
            continue
        sources[role] = pin(path)
        value = json.loads(path.read_bytes())
        def visit(item, parts):
            if isinstance(item, dict):
                containers.append({'document': role, 'pointer': pointer(parts), 'type': 'object',
                                   'exact_keys': sorted(item), 'allow_extra_keys': False})
                for key in sorted(item):
                    visit(item[key], (*parts, key))
            elif isinstance(item, list):
                containers.append({'document': role, 'pointer': pointer(parts), 'type': 'array',
                                   'observed_length': len(item), 'variable_length_rule': None})
                for index, child in enumerate(item):
                    visit(child, (*parts, index))
            else:
                group, reason = classify(role, parts, item)
                rows.append({'document': role, 'pointer': pointer(parts), 'type': type(item).__name__,
                             'class': group, 'reason': reason,
                             'sample_value_sha256': hashlib.sha256(canonical(item)).hexdigest(),
                             'validation_implemented': False})
                if parts and parts[-1] in EMBEDDED and isinstance(item, str) and item.lstrip().startswith(('{', '[')):
                    try:
                        nested = json.loads(item)
                    except ValueError:
                        return
                    visit(nested, (*parts, '$decoded'))
        visit(value, ())
    unresolved = [r for r in rows if r['class'] is None]
    result = {
        'kind': 'h3_exact_field_inventory_draft', 'version': 1,
        'status': 'draft_inventory_not_complete_schema_not_equivalence_gate',
        'script': pin(Path(__file__)), 'samples': sources,
        'primitive_field_count': len(rows), 'class_counts': dict(Counter(r['class'] or 'unclassified' for r in rows)),
        'fields': rows, 'closed_observed_containers': containers,
        'unclassified_terminal_names': dict(Counter(r['pointer'].rsplit('/', 1)[-1] for r in unresolved)),
        'requirements': [
            'Complete every unclassified field; unclassified fields and unknown container keys produce cannot_decide.',
            'These samples do not exhaust valid optional variants. Enumerate optional branches from production closed schemas before using as gate data.',
            'Historical execution sample is shape evidence only. Replace with saved successor execution before freezing gate data.',
            'Variable arrays require explicit element schemas and bounds; source maps require exact closed role/relative-path rosters, not unrestricted wildcards.',
            'Every $decoded node is a parsed embedded JSON document; raw carrier serialization and every derived digest require reference production recomputation.',
            'Project input tuple authority is NP1b and includes whole source manifest, bundle, chunk manifest, omission context and scope.',
            'Observed current preparation/composition fixture uses a synthetic small project, not a rebuilt real CHORUS or AI_READI registration.',
        ],
        'builder_paths': {
            'real_project_prefix': str(E / 'codex-native-packet-builder-20261112/scripts/build_native_canary_packet.py'),
            'all_project_prefix_tests': str(E / 'codex-native-packet-builder-20261112/tests/test_native_all_project_prefix.py'),
            'saved_chain_builder': str(E / 'codex-native-packet-builder-20261112/tests/test_native_packet_full_chain.py'),
            'rebuild_strategy': 'Feed each real-project prefix selection into the saved-input full-chain builder; generate marked synthetic runtime/permission evidence and new IDs/paths/dates through production constructors. Existing build_chain starts a generic SYNTHETIC fixture and needs adaptation.',
        },
    }
    output = Path(__file__).with_suffix('.json')
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'output': pin(output), 'class_counts': result['class_counts'],
                      'unclassified_terminal_names': result['unclassified_terminal_names']}, sort_keys=True))


if __name__ == '__main__':
    main()
