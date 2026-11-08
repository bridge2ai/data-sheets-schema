"""Real A/C consumer scopes and non-mutating test observations for U3-D R9.

Tests keep invented input data, but use the source-loaded production consumers
and their genuine classifier projection. No verifier or mint is substituted.
"""
from contextlib import contextmanager
import sys

from data_sheets_schema import native_execution_authority_v2 as authority
from data_sheets_schema import native_shared_controls_orchestration as controls


@contextmanager
def loaded_consumer(name, dependencies=None):
    dependencies = authority.dependency_identity() if dependencies is None else dependencies
    with authority.loaded_verified_package_module(
            'data_sheets_schema.' + name,
            package_sources=dependencies['base']['package_sources']) as consumer:
        yield consumer


def command_guidance(policy):
    dependencies = authority.dependency_identity()
    with controls.loaded_controls(dependencies) as projection, \
            loaded_consumer('native_shared_policy', dependencies) as policy_consumer:
        return policy_consumer.command_guidance(policy, classifier_projection=projection)


@contextmanager
def observe_consumer_calls(targets, *, refuse=None, forbid=False):
    """Observe actual function entry without changing any pinned callable.

    ``targets`` maps (module basename, function name) to local names to retain.
    The optional refusal is a deliberately injected test exception at that
    actual function entry, so a cached result cannot masquerade as a fresh call.
    """
    calls = []
    previous = sys.getprofile()
    names = frozenset(name for _, name in targets)

    def observe(frame, event, argument):
        if previous is not None:
            previous(frame, event, argument)
        if event != 'call':
            return
        # Most calls cannot match. Avoid parsing every unrelated filename while
        # the genuine source checks and historical callbacks are running.
        if frame.f_code.co_name not in names:
            return
        key = (frame.f_code.co_filename.rsplit('/', 1)[-1].removesuffix('.py'),
               frame.f_code.co_name)
        if key not in targets:
            return
        calls.append((key, {name: frame.f_locals[name]
                            for name in targets[key] if name in frame.f_locals}))
        if forbid:
            raise AssertionError('forbidden production operation: ' + '.'.join(key))
        if refuse is not None and key == refuse[0]:
            raise refuse[1]

    sys.setprofile(observe)
    try:
        yield calls
    finally:
        sys.setprofile(previous)
