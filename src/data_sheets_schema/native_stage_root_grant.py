"""Pure exact stage-root settings over the frozen permission protocol.

Callers bind the root to their selected production stage or projected probe
effect root. Physical-path checks belong to host capture and dispatch; saved
replay only compares captured canonical identities. PR 6302, 2026-11-21.
"""
import json

from . import native_shared_permission_protocol as protocol
from .native_shared_contract import canonical_path


def permission_arguments(policy, stage_root):
    """Grant one bound directory without changing the six-function protocol."""
    canonical_path(stage_root, 'stage grant root')
    if stage_root == '/':
        raise ValueError('stage grant root cannot be the filesystem root')
    arguments = protocol.permission_arguments(policy)
    settings = json.loads(arguments[-1])
    settings['permissions']['additionalDirectories'] = [stage_root]
    return [*arguments[:-1], json.dumps(settings, separators=(',', ':'))]
