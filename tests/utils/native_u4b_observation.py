"""Explicit fabricated D117 metadata for tests, 2026-11-08 (#4354).

Inputs are invented runtime and saved transcript/request files. Re-minting is
an explicit test action that overwrites only this test fixture's metadata.
No process/provider/authorization is obtained; production remains exclusive.
"""
from copy import deepcopy
from pathlib import Path

from data_sheets_schema import native_model_aliases as aliases
from data_sheets_schema import native_u4b_probe_sequence as sequence


def mint_observation(provisional_runtime, transcript_path, request_path):
    """Return a fabricated observation manifest; never call from production."""
    transcript_path, request_path = Path(transcript_path), Path(request_path)
    observation = transcript_path.parent
    root = observation.parent
    assert observation.name == 'observation' and root.name == 'probe-sequence'
    assert transcript_path == observation / 'transcript.jsonl'
    assert request_path == observation / 'native_request.json'
    provisional = deepcopy(provisional_runtime)
    provisional['limits_basis'] = sequence.canonical({'kind': aliases.PROVISIONAL_KIND,
        'version': 1, 'model_aliases': {'requested': aliases.REQUESTED, 'returned': aliases.RETURNED}}).decode()
    stamp = '2026-11-08T00:00:00Z'
    authorization = {'kind': sequence.AUTH_KIND, 'version': 1,
        'owner': 'Invented offline fixture identity', 'authorized_at': stamp,
        'word': 'AUTHORIZE_TWO_SCRIPTED_NATIVE_PROBES', 'directory': str(root),
        'provisional_runtime_sha256': sequence.sha(sequence.canonical(provisional)),
        'observation_deadline_seconds': min(60, provisional['deadline_seconds']),
        'permission_deadline_seconds': min(60, provisional['deadline_seconds']),
        'provider': sequence.PROVIDER, 'permission_protocol': sequence.PERMISSION_PROTOCOL}
    raw = sequence.canonical(authorization)
    process = {'spawn_count': 1, 'returncode': 0,
        'cleanup': {'child_started': True, 'leader_reaped': True, 'group_absent': True}}
    url = 'http://127.0.0.1:18455'
    document = sequence.observation_document(raw, provisional,
        transcript_raw=transcript_path.read_bytes(), request_raw=request_path.read_bytes(),
        provider_url=url, started_at=stamp, finished_at=stamp, process=process)
    for name, value in {
        'authorization.json': authorization, 'provisional-runtime.json': provisional,
        'observation-claim.json': sequence.observation_claim(raw, provisional, stamp),
        'observation/invocation.json': sequence.observation_invocation(provisional, root, url),
        'observation/observation.json': document,
    }.items():
        (root / name).write_bytes(sequence.canonical(value))
    return observation / 'observation.json'
