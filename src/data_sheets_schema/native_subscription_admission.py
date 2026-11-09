"""Version dispatch and raw authority joins for native subscription evidence.

Historical guard readback remains v1; current U4b launch requires v2. Neither
a saved verdict nor a caller-supplied statement is launch authority.
"""
from pathlib import Path

from . import native_subscription_guard as v1
from . import native_subscription_guard_v2 as v2
from . import native_launch_review as review


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
