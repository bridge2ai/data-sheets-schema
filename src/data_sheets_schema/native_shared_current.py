"""Fixed ordinary artifact roles shared by live and captured-only native gates."""
from . import native_shared_contract as c
from . import native_shared_evidence as evidence


def current_artifact(run, role, path):
    """Read current ordinary artifacts once, or only their sealed pool version."""
    limits = {'final_full': 'input_bytes', 'final_core': 'input_bytes',
              'final_report': 'input_bytes', 'provenance': 'request_bytes',
              'original_receipt_output': 'original_full_bytes'}
    expected_paths = {'final_full': run.spec._agentic_artifact_paths['full'],
        'final_core': run.spec._agentic_artifact_paths['core'],
        'final_report': run.spec._agentic_artifact_paths['report'],
        'original_receipt_output': run.spec._agentic_artifact_paths['receipt'],
        'provenance': run.composition['policy']['post_final_recorder']['destination']}
    if role not in limits or str(path) != expected_paths[role]:
        raise ValueError('ordinary artifact differs from its selected exact role')
    limit = c.HARD_LIMITS[limits[role]]
    if role in ('final_full', 'final_core', 'final_report'):
        limit = min(limit, run.selection.bounds()['max_input_bytes'])
    if run.reader.pool is None:
        return evidence.read_regular(str(path), role, max_bytes=limit).captured
    matches = [m.captured for m in run.reader.pool.members
               if m.captured.pin.role == role and m.captured.pin.path == str(path)]
    if len(matches) != 1 or matches[0].pin.bytes > limit:
        raise ValueError('saved ordinary artifact is missing, ambiguous or oversized')
    return matches[0]

