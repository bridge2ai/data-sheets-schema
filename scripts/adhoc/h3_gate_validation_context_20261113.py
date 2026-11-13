"""Document reference-validator relocation design choice, 2026-11-13.

Inputs: current registration/authority source, AST only; output adjacent JSON.
Serves helper 3 environment-manifest/gate-schema assignment; no production imports.
"""
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / 'src/data_sheets_schema'


def pin(path):
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def source_function(filename, name, explanation):
    path = PACKAGE / filename
    source = path.read_text()
    node = next(n for n in ast.parse(source).body
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name)
    return dict(pin(path), function=name, start_line=node.lineno, end_line=node.end_lineno,
                explanation=explanation,
                excerpt='\n'.join(source.splitlines()[node.lineno-1:node.end_lineno]))


def main():
    path = Path(__file__).with_suffix('.json')
    prior = json.loads(path.read_text()) if path.exists() else None
    history = prior.get('proposal_history', []) if prior else []
    if prior and not history:
        history = [{'version': prior['version'], 'status': prior['status'],
                    'document': pin(path), 'decision_requested': prior['decision_requested']}]
    evidence = [
        source_function('native_execution_registration_v2.py', '_wire',
                        'Reads the envelope, obtains live dependency identity from the reference interpreter/ROOT and requires its committed closure.'),
        source_function('native_execution_registration_v2.py', '_prepare',
                        'Requires cwd equal authority.ROOT; constructs dependencies and pin map from that live source, then renders preparation.'),
        source_function('native_execution_registration_v2.py', 'verify_preparer',
                        'Reconstructs preparation in that live context and compares its entire canonical body with the original candidate preparation; relocated host fields cause mismatch.'),
        source_function('native_execution_registration_v2.py', 'verified',
                        'Requires preparation and execution dependencies to equal the live identity, verifies dependent hashes, then reconstructs the full execution through the fixed consumer.'),
        source_function('native_execution_registration_v2.py', '_consumer',
                        'Loads verified consumer source only from authority.ROOT; this properly confines code origin but does not separate candidate registered host identity.'),
        source_function('native_supervisor_authority_v2.py', 'dependency_identity',
                        'Identity records live Git HEAD, package closure, sys.executable path, sys.version and interpreter bytes.'),
        source_function('native_execution_authority_v2.py', 'require_committed',
                        'Requires identity equal live dependency_identity before proving all named source bytes in the registered Git object.'),
    ]
    orchestration = PACKAGE / 'native_shared_registration_orchestration.py'
    lines = orchestration.read_text().splitlines()
    relevant = []
    for number, line in enumerate(lines, 1):
        if ("body['working_directory'] != cwd" in line
                or "selected['python'] != sys.executable" in line
                or "selected['working_directory'] != cwd" in line):
            relevant.append({'line': number, 'text': line.strip()})
    evidence.append(dict(pin(orchestration), matching_lines=relevant,
                         explanation='Captured verification independently requires the same live cwd/ROOT and interpreter path.'))
    output = {
        'kind': 'h3_gate_validation_context_design_proposal', 'version': 2,
        'status': 'design_approved_not_a_gate_schema_or_equivalence_result',
        'approval': {'actor': 'user', 'reply': 'Approve reference-only validation context',
                     'basis': 'Explicit approval in the current conversation, reported by the parent agent.',
                     'scope': 'Implement the reference-only validation context; no launch or publication authorization.'},
        'proposal_history': history,
        'scope': 'Offline source inspection only; no provider, model, native binary, probe, capture, reservation or production validator executed by this script.',
        'script': pin(Path(__file__)), 'evidence': evidence,
        'finding': 'Running existing production validators from the reference export does not validate an original candidate packet with different checkout or interpreter paths, even if all source and executable bytes are identical. They regenerate host-dependent identities from reference ROOT/sys.executable and require exact equality.',
        'current_supported_case': 'Two project packets built in the same checkout and interpreter may have fresh IDs, labels, dates and artifact roots, provided all production checks pass. That case does not demonstrate the full allowed relocation class.',
        'decision_requested': 'Approve an explicit read-only production validation context separating trusted reference code origin from the candidate registered artifact/host identity, shared with the current production validators.',
        'recommendation': [
            'Retain unmodified original packet bytes and bind them in the immutable comparison-input manifest. Never rewrite candidate paths, IDs or hashes to make current validation pass.',
            'Keep interpreter/package imports and all consumer loading rooted exclusively in the verified reference export. Never add the candidate checkout to sys.path or import candidate modules.',
            'Introduce an explicit immutable validation context supplying registered checkout/interpreter identity and artifact reads separately from trusted code origin. Do not monkeypatch module globals or skip existing checks.',
            'Refactor preparation, composition, instruction, policy and permission reconstruction to consume that context. Current launch uses a live context; read-only gate validation uses the registered candidate context. Both retain the same semantic validators and hash rules.',
            'Before reconstructing candidate data, verify the complete candidate source/asset/dependency closure against reference pins. Valid understood changed pins yield not_equal without executing candidate validation; invalid/incomplete evidence yields cannot_decide.',
            'Verify candidate registered interpreter and environment-manifest identity from bound artifacts and explicit reference-safe metadata validation. Do not substitute reference host identity silently; specify how archived environments are validated before approving this context.',
            'Prove candidate file bytes and immutable evidence through bounded stable reads; host device/inode/path differences remain recorded per-run values and their internal consistency checks remain active.',
            'Add a refusal/equality matrix: same source at different checkout and interpreter paths, altered candidate source, forged interpreter identity, stale/missing environment manifest, altered derived hash, unknown field, and attempted candidate import. Confirm candidate code is never imported in every case.',
        ],
        'alternative': 'A path-preserving isolated filesystem could mount verified reference source bytes at registered paths while retaining original packet bytes. No such virtualization is implemented or demonstrated here; ordinary subprocess isolation alone is insufficient.',
        'why_no_equal_claim': 'An identity bypass or relocation/re-hashing preprocessing would validate changed evidence rather than the original candidate packet and would weaken the required full production validation. A same-checkout demonstration cannot establish distinct-checkout handling.',
        'input_tuple_authority': 'The admitted project input tuple comes from NP1b, not the floor-registration amendment, per the approved ruling; it pins whole source manifest, bundle, chunk manifest, omission context and scope by sha256.',
        'remaining_work': 'The context design is approved. The separate gate worktree implements it and the closed field schema, recomputes derived values and supplies CHORUS/AI_READI/mutant evidence. This historical design record is not proof of that implementation or any equality result.',
        'bounds_artifact': pin(Path(__file__).with_name('h3_gate_bounds_20261113.json')),
        'bounds_limit': 'Historical prefix bounds data excludes the new environment manifest and runtime/preparation/composition/probe products; final-format totals must be measured before registration. Generated output/evidence budgets are planning assumptions, not measured guarantees.',
    }
    path.write_text(json.dumps(output, indent=2, sort_keys=True) + '\n')
    print(json.dumps(pin(path), sort_keys=True))


if __name__ == '__main__':
    main()
