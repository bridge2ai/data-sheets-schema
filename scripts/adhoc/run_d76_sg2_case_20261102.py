#!/usr/bin/env python3
"""Explicit review adapter for an isolated pytest case, PR #5213, 2026-11-03.

Only the evidence runner selects this adapter via a SHA-bound opt-in. Ordinary
tests use tests/utils/isolated_pytest.py directly and need no Git or review code.
The review route still requires exact tracked source and verifies import origins.
"""
import importlib.util
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def main():
    spec = importlib.util.spec_from_file_location("_review_isolated_pytest",
                                                  ROOT / "tests/utils/isolated_pytest.py")
    utility = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = utility
    spec.loader.exec_module(utility)
    parser = utility.argument_parser()
    parser.add_argument("--expect-head", required=True)
    args = parser.parse_args()
    root = args.root.resolve(strict=True)
    output = args.output.resolve()
    if root != ROOT or output.exists() or output.is_relative_to(root):
        raise ValueError("review child requires its pinned root and fresh external output")
    utility.bootstrap(root, args.dependencies)
    sys.path.insert(0, str(HERE))
    import d76_suite_common_20261031 as common

    before = common.source(root)
    if not before["tracked_exact"] or before["head"] != args.expect_head:
        raise ValueError("review child source must match its recorded commit")
    common.fairscape(root, before)

    class Origins:
        def pytest_collection_finish(self, session):
            common.save(output / "origins-collected.json", common.origins(root, before))

    report = utility.execute_case(root, args.node, output, plugins=[Origins()],
        before_run=lambda: common.save(output / "source-before.json", before))
    after = common.source(root)
    common.save(output / "source-after.json", after)
    common.save(output / "origins-after.json", common.origins(root, before))
    unchanged = before == after and after["tracked_exact"]
    report.update(head=before["head"], git_tree=before["tree"], source_unchanged=unchanged,
                  origins_verified=True, review_attestation=True,
                  passed=report["passed"] and unchanged,
                  scope="explicit review adapter; exact source, import origins and complete child phases")
    common.save(output / "outcome.json", report)
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
