"""Trusted C minting boundary for the input-only classifier projection.

Only this layer obtains A's helpers and installs the private source attestor.
The consumer authenticates exact class, mint membership and lifetime before
using that attestor; no carrier-provided validator or look-alike is accepted.
"""
from __future__ import annotations

from contextlib import contextmanager
import sys

from . import native_execution_authority_v2 as authority
from . import native_shared_controls as consumer


@contextmanager
def loaded_controls(dependencies=None):
    """Mint a revocable projection inside A's exact source-loader lifetime."""
    if dependencies is None:
        dependencies = authority.dependency_identity()
    projected = {}
    controls = None
    with authority.loaded_dependencies(dependencies):
        try:
            for name, members in consumer._MEMBERS.items():
                pin = dependencies['base']['modules'][name]
                path = authority.ROOT / pin['path']
                authority._verified_source_bytes(path, pin['sha256'])
                module = sys.modules.get(name)
                identity = {'name': name, 'path': str(path), 'sha256': pin['sha256']}
                if authority.module_source_identity(module) != identity:
                    raise ValueError('native shared pure helper differs from its selected source')
                projection = consumer._PureProjection(module, identity, members)
                projected[name] = projection
                consumer._PROJECTION_ATTESTORS[projection] = authority.module_source_identity
                projection._check()
            controls = consumer._PureControls(projected)
            consumer._LOADER_CONTROLS[controls] = tuple(
                (name, module, tuple(sorted(module._identity.items())))
                for name, module in sorted(projected.items()))
            consumer.require_controls(controls)
            yield controls
            consumer.require_controls(controls)
        finally:
            if controls is not None:
                consumer._LOADER_CONTROLS.pop(controls, None)
            for module in projected.values():
                module._active = False
                consumer._PROJECTION_ATTESTORS.pop(module, None)
