"""Explicit native guard/probe front door (#4760/#2370).

Preparation and validation are offline. Only the named permission-probe and
launch subcommands can invoke the registered binary. Neither creates review,
CI or owner authorization, and neither has a synthetic fallback.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from . import native_subscription_guard as guard


def _new_file(path, raw):
    from .native_permission_probe import _write_new
    target = Path(path)
    if not target.is_absolute() or target.parent.resolve(strict=True) != target.parent:
        raise ValueError("output requires a resolved absolute parent")
    _write_new(target, raw)


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    commands = result.add_subparsers(dest="command", required=True)
    probe = commands.add_parser("permission-probe", help="LIVE pinned binary; loopback scripted provider")
    probe.add_argument("--expectation", required=True)
    probe.add_argument("--output-directory", required=True)
    probe.add_argument("--deadline-seconds", type=int, required=True)
    validate = commands.add_parser("validate-probe", help="Offline saved-probe verification")
    validate.add_argument("--expectation", required=True)
    validate.add_argument("--probe", required=True)
    prepare = commands.add_parser("prepare-subscription-guard", help="Offline binding of saved quota evidence")
    prepare.add_argument("--registration", required=True)
    prepare.add_argument("--launch-word", required=True)
    prepare.add_argument("--event", required=True)
    prepare.add_argument("--captured-at", required=True)
    prepare.add_argument("--max-starting-weekly-utilization", type=float, required=True)
    prepare.add_argument("--max-age-seconds", type=int, required=True)
    prepare.add_argument("--output", required=True)
    launch = commands.add_parser("launch", help="LIVE one registered native attempt")
    for name in ("registration", "review", "ci", "launch-word", "subscription-guard",
                 "subscription-guard-sha256"):
        launch.add_argument("--" + name, required=True)
    return result


def main(argv=None):
    args = parser().parse_args(argv)
    if args.command in ("permission-probe", "validate-probe"):
        expected = guard.strict_json(guard.read_regular(args.expectation, limit=32 * 1024 * 1024))
        if args.command == "permission-probe":
            from .native_permission_probe import produce_saved_probe
            print(produce_saved_probe(expected, args.output_directory, deadline_seconds=args.deadline_seconds))
        else:
            from . import native_shared_permissions as shared
            from . import native_execution_permissions as legacy
            protocol = shared if expected.get("kind") == shared.EXPECTED_KIND else legacy
            raw = guard.read_regular(args.probe,
                limit=shared.MAX_WIRE if protocol is shared else legacy.MAX_BYTES)
            print(guard.canonical(protocol.verify_saved_probe(raw, expected=expected)).decode())
    elif args.command == "prepare-subscription-guard":
        from .native_shared_registration import verified
        registration_raw = guard.read_regular(args.registration, limit=32 * 1024 * 1024)
        value = verified(registration_raw)
        raw = guard.prepare_guard(registration_raw=registration_raw, runtime=value["runtime"],
            launch_word_raw=guard.read_regular(args.launch_word),
            event_raw=guard.read_regular(args.event), captured_at=args.captured_at,
            maximum_starting_utilization=args.max_starting_weekly_utilization,
            max_age_seconds=args.max_age_seconds)
        _new_file(args.output, raw)
        print(guard.sha(raw))
    else:
        from .native_shared_execution import launch
        result = launch(guard.read_regular(args.registration, limit=32 * 1024 * 1024),
            review_path=args.review, ci_path=args.ci, launch_word_path=args.launch_word,
            subscription_guard_path=args.subscription_guard,
            subscription_guard_sha256=args.subscription_guard_sha256)
        print(guard.canonical(result).decode())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
