"""Version dispatch and raw authority joins for native subscription evidence.

Historical guard readback remains v1; current U4b launch requires v2. Neither
a saved verdict nor a caller-supplied statement is launch authority.
"""
from dataclasses import dataclass
from pathlib import Path

from . import native_subscription_guard as v1
from . import native_subscription_guard_v2 as v2
from . import native_launch_review as review


@dataclass(frozen=True, slots=True)
class CurrentSelection:
    """Unaccepted caller-selected bytes/paths; never subscription authority."""
    path: str
    expected_sha256: str
    registration_raw: bytes
    runtime_json: bytes
    launch_word_path: str
    review_path: str


def select_current(path, expected_sha256, *, registration_raw, runtime,
                   launch_word_path, review_path):
    """Bind data only; this neither accepts a capture nor observes an account."""
    if (type(registration_raw) is not bytes or not registration_raw
            or type(runtime) is not dict or type(expected_sha256) is not str
            or len(expected_sha256) != 64
            or any(char not in '0123456789abcdef' for char in expected_sha256)):
        raise ValueError('deferred subscription selection has invalid wire inputs')
    return CurrentSelection(str(Path(path).absolute()), expected_sha256,
        registration_raw, v1.canonical(runtime),
        str(Path(launch_word_path).absolute()), str(Path(review_path).absolute()))


def preflight_current_selection(selection, *, registration_raw, runtime):
    """Refuse stale, spent or mismatched capture inputs before engine entry.

    RunSpec boundary: validated-caller

    RunSpec precondition: Caller supplies execution bytes and the runtime from
    registration.verified; context reconstructs current capture preparation and
    checks live guard freshness without returning or accepting a guard.
    """
    if (type(selection) is not CurrentSelection
            or selection.registration_raw != registration_raw
            or selection.runtime_json != v1.canonical(runtime)):
        raise ValueError('deferred subscription selection differs from launch authority')
    raw = v1.read_regular(selection.path)
    word = v1.read_regular(selection.launch_word_path)
    bundle = v1.read_regular(selection.review_path)
    module, extra = context(raw, registration_raw=registration_raw, runtime=runtime,
        launch_word_raw=word, review_bundle_raw=bundle, current=True)
    if module is not v2:
        raise ValueError('current native launch requires subscription guard v2')
    module.SubscriptionGuard(raw, expected_sha256=selection.expected_sha256,
        registration_raw=registration_raw, runtime=runtime, launch_word_raw=word,
        check_freshness=True, **extra)


def _selection_inputs(selection, registration_raw, runtime, authorization):
    if (type(selection) is not CurrentSelection
            or selection.registration_raw != registration_raw
            or selection.runtime_json != v1.canonical(runtime)
            or selection.launch_word_path != authorization['inputs']['launch_word']
            or selection.review_path != authorization['inputs']['review']):
        raise ValueError('deferred subscription selection differs from launch authority')
    raw = v1.read_regular(selection.path)
    word = v1.read_regular(selection.launch_word_path)
    bundle = v1.read_regular(selection.review_path)
    if (word != authorization['raw']['launch_word']
            or bundle != authorization['raw']['review']):
        raise ValueError('deferred subscription authority bytes changed')
    return raw, word, bundle


def inspect_current_selection(selection, *, registration_raw, runtime, authorization):
    """Warm static reconstruction; the result is expressly NOT current admission.

    RunSpec boundary: validated-caller

    RunSpec precondition: Caller supplies execution bytes and the runtime from
    registration.verified; context reconstructs guarded capture preparation.
    This helper returns no guard and grants no freshness or current authority.

    The temporary guard checks exact bytes, quota declarations and chronology.
    It does not accept freshness or return a guard to the actuator. Current-word
    and actual-clock checks remain mandatory in accept_current_selection.
    """
    raw, word, bundle = _selection_inputs(
        selection, registration_raw, runtime, authorization)
    module, extra = context(raw, registration_raw=registration_raw, runtime=runtime,
        launch_word_raw=word, review_bundle_raw=bundle, current=False)
    if module is not v2:
        raise ValueError('current native launch requires subscription guard v2')
    module.SubscriptionGuard(raw, expected_sha256=selection.expected_sha256,
        registration_raw=registration_raw, runtime=runtime, launch_word_raw=word,
        check_freshness=False, **extra)


def accept_current_selection(selection, *, registration_raw, runtime, authorization):
    """Accept the original timestamp only after heavy launch reconstruction.

    RunSpec boundary: validated-caller

    RunSpec precondition: Caller supplies execution bytes and runtime from
    registration.verified plus independently recaptured authority; load_current
    reconstructs the guarded capture and validates current authority and age.
    """
    _selection_inputs(selection, registration_raw, runtime, authorization)
    return load_current(selection.path, selection.expected_sha256,
        registration_raw=registration_raw, runtime=runtime,
        launch_word_path=selection.launch_word_path, review_path=selection.review_path)


def context(raw, *, registration_raw, runtime, launch_word_raw, review_bundle_raw, current=False):
    """RunSpec boundary: validated-caller

    RunSpec precondition: Caller supplies execution bytes and the runtime
    returned by prior registration.verified; historical v1 only selects its
    saved reader, while v2 also reconstructs registered capture through
    read_capture_for_event before returning guard context.
    """
    if type(current) is not bool:
        raise ValueError('current subscription authority selection must be boolean')
    value = v1.strict_json(raw)
    if type(value) is not dict or type(value.get('version')) is not int:
        raise ValueError('subscription guard requires an explicit version')
    if value['version'] == 1:
        from .native_u4b_runtime import is_prepared_runtime
        if is_prepared_runtime(runtime):
            raise ValueError('U4b runtime cannot use a historical v1 guard')
        return v1, {}
    if value['version'] != 2:
        raise ValueError('unknown subscription guard version')
    from .native_u4b_runtime import validate_prepared_runtime
    from .native_subscription_capture import read_capture_for_event
    validate_prepared_runtime(runtime)
    terms = review.validate_bundle(registration_raw, review_bundle_raw, launch_word_raw)
    capture = read_capture_for_event(Path(terms['quota_capture']['directory']),
        registration_raw=registration_raw, review_bundle_raw=review_bundle_raw,
        launch_word_raw=launch_word_raw,
        require_current=current,
        **{key: value[key] for key in ('event_json', 'event_sha256', 'captured_at')})
    event = capture['selected_event']
    if any(value[key] != event[key] for key in ('event_json', 'event_sha256', 'captured_at')):
        raise ValueError('guard differs from the selected registered capture')
    return v2, {'owner_statement': terms}


def load_current(path, expected_sha256, *, registration_raw, runtime, launch_word_path, review_path):
    """RunSpec boundary: validated-caller

    RunSpec precondition: Caller supplies paths plus execution bytes/runtime
    from registration.verified; context selects v2 and reconstructs capture
    authority before load_guard checks the exact guard. No RunSpec argument
    is accepted.
    """
    raw, word, bundle = (v1.read_regular(path), v1.read_regular(launch_word_path),
                         v1.read_regular(review_path))
    module, extra = context(raw, registration_raw=registration_raw, runtime=runtime,
        launch_word_raw=word, review_bundle_raw=bundle, current=True)
    if module is not v2:
        raise ValueError('current native launch requires subscription guard v2')
    return module.load_guard(path, expected_sha256, registration_raw=registration_raw,
        runtime=runtime, launch_word_path=launch_word_path, **extra)
