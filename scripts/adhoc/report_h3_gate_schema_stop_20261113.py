"""Record the gate-schema format decision stop; source inputs, handoff outputs; 2026-11-13."""
import hashlib
import json
import subprocess
from pathlib import Path

R = Path(__file__).resolve().parents[2]
N = R.parent / 'codex-native-recorder-env-20261113'
stem = R / 'notes/development_efficiency_20261111/handoffs/codex-h3-recorder-env-and-pin-comparison-20261113'
assignment = R / 'notes/development_efficiency_20261111/assignments/claude-lead-helper3-gate-schema-20261113.md'

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

evidence = []
for name, start, end, conclusion in [
    ('native_shared_contract.py', 685, 692, 'Selection has exact closed top-level fields and version.'),
    ('native_shared_selection.py', 207, 219, 'Artifact declarations enumerate fixed semantic roles.'),
    ('native_shared_selection.py', 365, 376, 'Extra asset names and captured roles are rejected.'),
    ('native_execution_registration_v2.py', 205, 222, 'Preparation pin map is generated from selected authority and source dependencies.'),
    ('native_execution_registration_v2.py', 375, 401, 'Verifier regenerates preparation and compares the entire canonical body.'),
    ('native_shared_authority_wire.py', 15, 39, 'Execution has a closed key set; only receipt-origin extension is admitted.'),
]:
    path = N / 'src/data_sheets_schema' / name
    raw = path.read_bytes()
    evidence.append(dict(path=str(path), sha256=sha(raw), start=start, end=end,
                         excerpt='\n'.join(raw.decode().splitlines()[start-1:end]), conclusion=conclusion))

record = dict(status='design_stop_environment_manifest_requires_versioned_registration_change',
    source_commit=subprocess.check_output(['git', '-C', str(N), 'rev-parse', 'HEAD'], text=True).strip(),
    assignment_sha256=sha(assignment.read_bytes()), script_sha256=sha(Path(__file__).read_bytes()),
    schema_data_sha256=None, field_counts=None, demonstration_results=None, proposed_bounds=None,
    evidence=evidence,
    ruling_resolved='Reference-only isolated production validation is authorized; the previous validation question is closed.',
    reason='No existing validated arbitrary-artifact slot binds an environment manifest. A free-standing sidecar would not satisfy the registration-time pin requirement.',
    proposal={
        'decision_requested': 'Approve a versioned successor preparation and execution registration that binds an environment manifest.',
        'minimal_scope': 'Keep historical v2 acceptance unchanged. Add one required environment_manifest file pin to successor preparation; bind it transitively through embedded preparation in successor execution. Use distinct successor kinds/versions and explicit dispatch, rather than silently expanding v2.',
        'manifest': 'Versioned closed document with interpreter identity and sorted unique distribution records: normalized name, version, installed RECORD sha256. Enumerate the interpreter import environment without importing third-party packages; missing or ambiguous distribution metadata holds.',
        'verification': 'Recompute the manifest from the declared interpreter environment at preparation and production verification, require its file bytes and pin to agree, and include it in captured authority. Gate compares semantic interpreter identity and distribution records; host path is per-run. Freeze serialization and whether interpreter path is excluded from manifest bytes before implementation.',
        'tests_after_approval': 'Missing, extra, altered and stale environment pins refuse; distribution version or RECORD mutation refuses; old v2 behavior remains unchanged; then implement the closed field schema and requested two-project demonstrations.',
    },
    unperformed=['No new gate branch or implementation', 'No schema classification or derived-value computation', 'No rehearsal packets or mutant demonstrations', 'No constant-bound proposal', 'No native binary, probe, capture, reservation, provider, model or publication action'])

jpath = stem.with_suffix('.json')
prior = json.loads(jpath.read_text())
prior['gate_schema_20261113'] = record
jpath.write_text(json.dumps(prior, indent=2, sort_keys=True) + '\n')
mpath = stem.with_suffix('.md')
heading = '# Gate-schema follow-up: explicit version-design stop (2026-11-13)\n'
assert heading not in mpath.read_text(), 'already recorded; do not duplicate'
section = heading + '''
Data-file SHA-256: not produced. Field counts: not computed. Demonstration results: not run. Constant bounds: not proposed. The assignment's explicit format-change stop applies before these deliverables.

The lead's 04:21Z ruling resolves the previous validation question: production validation may run from the reference export in isolation. The new environment-manifest requirement cannot be bound through an existing arbitrary-artifact slot. Selection has exact fields and fixed artifact roles; preparation regenerates its pin map and compares the complete body; execution permits only its closed fields and the receipt-origin extension. An extra pinned_files entry or loose sidecar would fail verification or remain outside the registered authority. The companion JSON records source hashes and exact excerpts. An ignore-independent hidden-file search of the source package for environment_manifest, extra_artifacts and additional_artifacts returned no matches; this supports, but does not replace, the positive closed-schema evidence.

Recommended smallest scoped change: introduce successor preparation and execution kinds/versions, leaving historical v2 unchanged. Add one required environment_manifest file pin to preparation and bind it transitively through the execution's embedded preparation. Its closed versioned document records interpreter identity and sorted unique distribution names, versions and installed RECORD hashes. Production preparation and verification must regenerate and check it. Missing or ambiguous metadata holds. A gate-only wrapper is insufficient because existing production validators would not bind its added artifact.

The lead must approve that versioned change before implementation, as the assignment explicitly directs: "If it does not, stop and propose the smallest versioned change." Freeze manifest serialization and interpreter-path treatment with that decision: semantic interpreter identity is must-equal, while host paths are per-run. Then implement the schema and all requested rehearsals against that final format, including missing/altered/stale manifest controls. No source files or protected files were edited, no source branch was created, and no native binary, probe, capture, reservation, provider or model was run. Nothing was published. Prior handoff evidence follows unchanged.

---

'''
mpath.write_text(section + mpath.read_text())
for path in (mpath, jpath):
    raw = path.read_bytes()
    assert raw and b'@' not in raw
    print(str(path), sha(raw))
