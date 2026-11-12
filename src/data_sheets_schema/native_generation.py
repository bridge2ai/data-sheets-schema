"""Explicit native front door: saved validation, guard preparation, probe, launch.

U4 preparation, 2026-11-08. D105 retains receipts v4; D106 selects explicit
high effort and the LBL work first-party Max account. The separately supplied
account-choice document binds that intent to exact input/runtime bytes. It is
not an account observation, permission proof, CI/review or launch authority.
Only explicitly selected probe phases, capture-subscription-event and launch can invoke the
registered executable. Saved validation/preparation never invokes a producer.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from . import native_subscription_guard as guard

CHOICE_KIND = "d4d_native_u4_owner_choice"
CHOICE_VERSION = 1
ACCOUNT_LABEL = "LBL work Claude Max"
CHOICE_KEYS = {"kind", "version", "decisions", "account_label", "effort",
               "receipt_instrument", "subject_sha256", "runtime_sha256"}
CHOICE_LIMIT = 16 * 1024
SUBJECT_LIMIT = 32 * 1024 * 1024


def _new_file(path, raw):
    from .native_permission_probe import _write_new
    target = Path(path)
    if (not target.is_absolute() or str(target) != str(path)
            or target.parent.resolve(strict=True) != target.parent):
        raise ValueError("output requires a canonical absolute path and resolved parent")
    _write_new(target, raw)


def _read(path, limit=SUBJECT_LIMIT):
    return guard.read_regular(path, limit=limit)


def _account_choice(path, subject_raw, runtime):
    """Validate selected intent; never infer the identity of a logged-in account."""
    raw = _read(path, CHOICE_LIMIT)
    value = guard.strict_json(raw)
    if type(value) is not dict or set(value) != CHOICE_KEYS:
        raise ValueError("account choice has missing or unknown fields")
    expected = {"kind": CHOICE_KIND, "version": CHOICE_VERSION,
        "decisions": ["D105", "D106"], "account_label": ACCOUNT_LABEL,
        "effort": "high", "receipt_instrument": 4,
        "subject_sha256": guard.sha(subject_raw),
        "runtime_sha256": guard.sha(guard.canonical(runtime))}
    if (type(value["version"]) is not int or type(value["receipt_instrument"]) is not int
            or guard.canonical(value) != guard.canonical(expected)):
        raise ValueError("account choice differs from D105/D106 or the exact selected subject/runtime")
    return raw


def _unchanged(*captures):
    """Re-read mutable external input paths immediately before the next effect."""
    for path, raw, limit in captures:
        if _read(path, limit) != raw:
            raise ValueError("native front-door input changed before use: " + str(path))


def _emit(result, choice_raw, *, command):
    scope = {
        "validate-probe": "Saved permission observations only; receipt-policy bytes, account identity and launch authorization are not established.",
        "permission-probe": "Saved local-provider permission observations; not production generation, account identity or launch authorization.",
        "observation-probe": "Authorized provisional observation against the scripted local provider; not account or launch acceptance.",
        "bound-permission-probe": "Authorized bound permission protocol after the pinned observation; not account or launch acceptance.",
        "validate-probe-sequence": "Saved two-phase evidence consistency; not authenticated execution or launch authority.",
        "record-capture-word": "Recorded supplied word supersession; no capture or generation attempt executed.",
        "prepare-subscription-guard": "Bound saved subscription observation and selected intent; not authenticated account state or launch authorization.",
        "prepare-subscription-guard-v2": "Bound registered capture and exact owner terms; not authenticated account state or authorization to launch.",
        "capture-subscription-event": "One explicitly authorized fixed-prompt quota capture; not a generation attempt or authenticated account evidence.",
        "launch": "The execution result defines completion and acceptance; selected account intent is not authenticated account identity.",
        "read-final": "Independent saved execution readback; not authorization to resume or launch, or fresh account evidence.",
    }[command]
    print(guard.canonical({"result": result,
        "account_choice_sha256": guard.sha(choice_raw),
        "account_choice_basis": "D105/D106 selected intent; not authenticated account state",
        "account_label": ACCOUNT_LABEL, "effort": "high", "selected_receipt_instrument": 4,
        "command": command, "verification_scope": scope}).decode())


def parser():
    result = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    commands = result.add_subparsers(dest="command", required=True)
    probe = commands.add_parser("permission-probe", allow_abbrev=False,
        help="LIVE pinned binary against an isolated scripted local provider")
    probe.add_argument("--expectation", required=True)
    probe.add_argument("--output-directory", required=True)
    probe.add_argument("--deadline-seconds", type=int, required=True)
    validate = commands.add_parser("validate-probe", allow_abbrev=False,
        help="Offline verification of saved observations; never produces a probe")
    validate.add_argument("--expectation", required=True)
    validate.add_argument("--probe", required=True)
    observation = commands.add_parser('observation-probe', allow_abbrev=False,
        help='LIVE authorized provisional observation against the scripted local provider only')
    observation.add_argument('--authorization', required=True)
    observation.add_argument('--runtime', required=True)
    bound = commands.add_parser('bound-permission-probe', allow_abbrev=False,
        help='LIVE authorized bound permission protocol after the saved observation')
    bound.add_argument('--authorization', required=True)
    bound.add_argument('--expectation', required=True)
    sequence = commands.add_parser('validate-probe-sequence', allow_abbrev=False,
        help='Offline reconstruction of the observation-to-permission binding')
    sequence.add_argument('--runtime', required=True)
    sequence.add_argument('--probe', required=True)
    prepare = commands.add_parser("prepare-subscription-guard", allow_abbrev=False,
        help="Offline binding of existing quota/word evidence; never creates authority")
    prepare.add_argument("--registration", required=True)
    prepare.add_argument("--launch-word", required=True)
    prepare.add_argument("--event", required=True)
    prepare.add_argument("--captured-at", required=True)
    prepare.add_argument("--max-starting-weekly-utilization", type=float, required=True)
    prepare.add_argument("--max-age-seconds", type=int, required=True)
    prepare.add_argument("--output", required=True)
    capture = commands.add_parser("capture-subscription-event", allow_abbrev=False,
        help="LIVE one fixed-prompt pinned-binary capture, only after its exact owner word")
    for name in ("registration", "review", "launch-word", "output-directory"):
        capture.add_argument("--" + name, required=True)
    record_word = commands.add_parser('record-capture-word', allow_abbrev=False,
        help='Record a supplied newer word and supersede older capture authority without a process')
    for name in ('registration', 'review', 'launch-word'):
        record_word.add_argument('--' + name, required=True)
    prepare_v2 = commands.add_parser("prepare-subscription-guard-v2", allow_abbrev=False,
        help="Offline guard v2 from the one registered capture and exact owner terms")
    for name in ("registration", "review", "launch-word", "capture", "output"):
        prepare_v2.add_argument("--" + name, required=True)
    launch = commands.add_parser("launch", allow_abbrev=False,
        help="LIVE one registered attempt; requires the complete admission chain")
    for name in ("registration", "review", "ci", "launch-word", "subscription-guard",
                 "subscription-guard-sha256"):
        launch.add_argument("--" + name, required=True)
    readback = commands.add_parser("read-final", allow_abbrev=False,
        help="Offline independent saved execution readback; never resumes an attempt")
    readback.add_argument("--registration", required=True)
    for command in (probe, validate, observation, bound, sequence, record_word,
                    prepare, capture, prepare_v2, launch, readback):
        command.add_argument("--account-choice", required=True,
            help="Closed D105/D106 selected-intent document bound to exact subject/runtime bytes")
    return result


def main(argv=None):
    """RunSpec boundary: validated-caller

    RunSpec precondition: Caller supplies CLI arguments, not a RunSpec;
    registration-consuming branches call registration.verified and rederive
    guarded preparation before dispatching capture, guard, launch or readback.
    Probe-only branches consume closed runtime/permission values without
    constructing RunSpec.
    """
    args = parser().parse_args(argv)
    from . import native_permission_probe as probe
    if args.command in ('observation-probe', 'bound-permission-probe', 'validate-probe-sequence'):
        from . import native_u4b_probe_sequence as sequence
        subject_path = args.expectation if args.command == 'bound-permission-probe' else args.runtime
        subject_raw = _read(subject_path)
        subject = guard.strict_json(subject_raw)
        runtime = subject['runtime'] if args.command == 'bound-permission-probe' else subject
        choice_raw = _account_choice(args.account_choice, subject_raw, runtime)
        captures = [(subject_path, subject_raw, SUBJECT_LIMIT),
                    (args.account_choice, choice_raw, CHOICE_LIMIT)]
        if args.command == 'validate-probe-sequence':
            result = sequence.validate_bound_probe(runtime, args.probe)
        else:
            authorization_raw = _read(args.authorization)
            captures.append((args.authorization, authorization_raw, SUBJECT_LIMIT))
            _unchanged(*captures)
            if args.command == 'observation-probe':
                output = sequence.produce_observation(authorization_raw, runtime)
                output_limit = sequence.MAX_BYTES
            else:
                from .native_shared_contract import HARD_LIMITS
                output = sequence.produce_bound_probe(authorization_raw, subject)
                output_limit = HARD_LIMITS['permission_wire_bytes']
            result = {'manifest': str(output), 'sha256': guard.sha(_read(output, output_limit))}
        _unchanged(*captures)
        _emit(result, choice_raw, command=args.command)
        return 0
    if args.command in ("permission-probe", "validate-probe"):
        subject_raw = _read(args.expectation)
        expected = guard.strict_json(subject_raw)
        # Shared expectation only: unknown or legacy kinds cannot fall through.
        probe.require_u4_expectation(expected)
        choice_raw = _account_choice(args.account_choice, subject_raw, expected["runtime"])
        captures = [(args.expectation, subject_raw, SUBJECT_LIMIT),
                    (args.account_choice, choice_raw, CHOICE_LIMIT)]
        if args.command == "permission-probe":
            from .native_u4b_runtime import MODEL, is_prepared_runtime
            if expected['runtime']['model'] == MODEL or is_prepared_runtime(expected['runtime']):
                raise ValueError('A3 current profile requires the authorized observation/bound probe sequence')
            _unchanged(*captures)
            produced = probe.produce_saved_probe(expected, args.output_directory,
                deadline_seconds=args.deadline_seconds)
            result = {"probe_manifest": str(produced)}
        else:
            from . import native_shared_permission_orchestration as permission
            from .native_shared_permissions import MAX_WIRE
            saved_raw = _read(args.probe, MAX_WIRE)
            result = permission.verify_saved_probe(saved_raw, expected=expected)
            _unchanged(*captures, (args.probe, saved_raw, MAX_WIRE))
        _emit(result, choice_raw, command=args.command)
        return 0

    from . import native_shared_registration_orchestration as registration
    from .native_shared_render import validate_metadata
    subject_raw = _read(args.registration)
    value = registration.verified(subject_raw)
    # E verification already reconstructs this exact metadata through A/C.
    # Retain an explicit current-contract v4 check here too: the account-choice
    # label is never sufficient evidence for the receipt instrument.
    validate_metadata(value["selection"]["render_spec"])
    probe.require_u4_runtime(value["runtime"])
    choice_raw = _account_choice(args.account_choice, subject_raw, value["runtime"])
    captures = [(args.registration, subject_raw, SUBJECT_LIMIT),
                (args.account_choice, choice_raw, CHOICE_LIMIT)]
    if args.command in ("capture-subscription-event", "prepare-subscription-guard-v2", 'record-capture-word'):
        from . import native_launch_review as review
        from . import native_subscription_capture as capture
        from .native_u4b_runtime import validate_prepared_runtime
        validate_prepared_runtime(value['runtime'])
        bundle_raw, word_raw = _read(args.review), _read(args.launch_word)
        review.validate_bundle(subject_raw, bundle_raw, word_raw)
        captures.extend([(args.review, bundle_raw, SUBJECT_LIMIT),
                         (args.launch_word, word_raw, SUBJECT_LIMIT)])
        _unchanged(*captures)
        if args.command == 'record-capture-word':
            result = capture.activate_capture_word(registration_raw=subject_raw,
                review_bundle_raw=bundle_raw, launch_word_raw=word_raw)
        elif args.command == "capture-subscription-event":
            path = capture.capture_subscription(registration_raw=subject_raw,
                review_bundle_raw=bundle_raw, launch_word_raw=word_raw, directory=args.output_directory)
            result = {"capture_manifest": str(path), "sha256": guard.sha(_read(path))}
        else:
            with capture.current_guard_preparation(args.capture, registration_raw=subject_raw,
                    review_bundle_raw=bundle_raw, launch_word_raw=word_raw) as raw:
                _unchanged(*captures)
                _new_file(args.output, raw)
            result = {"guard_sha256": guard.sha(raw), "path": args.output}
        _emit(result, choice_raw, command=args.command)
    elif args.command == "prepare-subscription-guard":
        word_raw, event_raw = _read(args.launch_word), _read(args.event)
        raw = guard.prepare_guard(registration_raw=subject_raw, runtime=value["runtime"],
            launch_word_raw=word_raw, event_raw=event_raw, captured_at=args.captured_at,
            maximum_starting_utilization=args.max_starting_weekly_utilization,
            max_age_seconds=args.max_age_seconds)
        _unchanged(*captures, (args.launch_word, word_raw, SUBJECT_LIMIT),
                   (args.event, event_raw, SUBJECT_LIMIT))
        _new_file(args.output, raw)
        _emit({"guard_sha256": guard.sha(raw), "path": args.output}, choice_raw, command=args.command)
    elif args.command == "launch":
        from .native_shared_execution_orchestration import launch
        _unchanged(*captures)
        result = launch(subject_raw, review_path=args.review, ci_path=args.ci,
            launch_word_path=args.launch_word, subscription_guard_path=args.subscription_guard,
            subscription_guard_sha256=args.subscription_guard_sha256)
        _emit(result, choice_raw, command=args.command)
    else:
        from .native_shared_execution_orchestration import read_final
        result = read_final(subject_raw)
        _unchanged(*captures)
        _emit(result, choice_raw, command=args.command)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
