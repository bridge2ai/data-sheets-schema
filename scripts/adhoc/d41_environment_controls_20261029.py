#!/usr/bin/env python3
"""#5212 design evidence, 2026-10-29: isolate validation-environment errors.

Inputs: unchanged base checkout, installed dependency Python, fresh TMPDIR root,
and an external evidence root. Outputs: the shared observer's JUnit/JSON reports.
No installation, source/test modification, network, or protected-directory write.
Run serially under d41_validation_offline_20261029.sb, canary before each group.
Poetry controls select the installed environment; checkout controls change only
the location of streamed reports. Copy frozen reports back after pytest exits.
"""
import argparse
import importlib.util
import os
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tree", type=Path, required=True)
    parser.add_argument("--scratch", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--suite", choices=("poetry", "checkout"), required=True)
    parser.add_argument("--canary", action="store_true")
    args = parser.parse_args()
    for key in ("tree", "scratch", "evidence"):
        setattr(args, key, getattr(args, key).resolve())
    assert not args.scratch.is_relative_to(args.tree)
    assert not args.evidence.is_relative_to(args.tree)
    driver_path = Path(__file__).resolve().with_name("d41_legacy_controls_20261029.py")
    spec = importlib.util.spec_from_file_location("d41_environment_driver", driver_path)
    driver = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(driver)
    assert driver.git(args.tree, "rev-parse", "HEAD") == driver.BASE
    environment = driver.bootstrap(args.tree, args.scratch)
    environment.update(environment_control_sha256=driver.sha(Path(__file__).read_bytes()),
                       reports_outside_checkout=True)
    if args.suite == "poetry":
        venv = Path(sys.executable).parent.parent
        overrides = {"VIRTUAL_ENV": str(venv), "POETRY_VIRTUALENVS_CREATE": "false",
                     "POETRY_CACHE_DIR": str(args.scratch / "poetry-cache")}
        os.environ.update(overrides)
        os.environ["PATH"] = str(venv / "bin") + os.pathsep + os.environ["PATH"]
        environment.update(environment_overrides=overrides, path_prefix=str(venv / "bin"))
        driver.SUITES = ["tests/test_d4d_full_schema.py",
                        "tests/test_review_pack_schema_refresh.py",
                        "tests/test_schema/test_datacite_relationships.py::TestTheValuesThatFailedNowValidate",
                        "tests/test_schema/test_filecollection_resources.py::TestTheSlotCanActuallyBePopulated"]
        if args.canary:
            driver.SUITES = ["tests/test_d4d_full_schema.py::TestD4DFullSchema::test_d4d_full_schema_generated"]
    else:
        driver.SUITES = ["tests/test_preflight_resource_authority.py"]
        if args.canary:
            driver.SUITES[0] += "::test_positional_draft_context_worktree_selects_vocabulary"
    args.mode = args.suite + ("-environment-canary" if args.canary else "-environment-control")
    driver.checks(args, environment)


if __name__ == "__main__":
    main()
