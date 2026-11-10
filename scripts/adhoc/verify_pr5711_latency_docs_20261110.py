#!/usr/bin/env python3
"""Purpose: Verify historical digests and current links for PR #5711 latency docs.
Inputs: Worktree root (--repo, defaults to parents[2]) and optional sibling d4d-executions root (--d4d-executions).
Outputs: JSON verification summary to stdout; exits non-zero on any digest, link, or at-sign mismatch.
Serves: PR #5711 documentation review, #5740 links and #5741 mutable coordination.
Historical assessment/plan bytes remain pinned. Current coordination files are
required to be nonempty and hashed for reporting, not compared with old snapshots.
Date: 2026-11-10
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re


PINNED_WORKTREE_SHAS = {
    "notes/reviews/agy4_native_latency_assignment_2026-11-10.md": (
        "51c30f2a5bfc87c9933e8faea1639e9cb63d52490217487ea2f38d2304301b9f"
    ),
    "notes/reviews/native_development_latency_2026-11-10.md": (
        "c0164a3d41ad85112adb1ecb3f6d918580a2eb91ad86ca0d00619be0b594bbbd"
    ),
    "notes/reviews/native_latency_implementation_plan_2026-11-10.md": (
        "7cddbdab212fc70dbccec74fa6d73b94ebf9065beb69ac241cbb87299e131b22"
    ),
    "notes/reviews/native_latency_implementation_plan_2026-11-10_v2.md": (
        "57ccd828662d6076e4edbf444446fe828fc5999be135fc46e3fd1b841858da53"
    ),
    "notes/reviews/native_latency_implementation_plan_2026-11-10_v3.md": (
        "fbe0bd80d622576bc4c5305e1a7ef7de857ced28f9a3a8016035b7bde79e3467"
    ),
    "notes/reviews/native_latency_plan_lead_review_2026-11-10.md": (
        "ffb38c2544ad116cd88d717c46122eacc18dbf7281741eb054f429e6c872b6c4"
    ),
    "notes/reviews/native_latency_plan_v2_lead_review_2026-11-10.md": (
        "76b6a6b7e262fc7ccca7a08a05c0ef8af8d0d23227bf0263f31c7bf41b909c7c"
    ),
    "notes/reviews/native_latency_plan_v3_lead_review_2026-11-10.md": (
        "ff81141341ea18a519838e966c753835338d2c7f7c47102560188bc5b3e469b4"
    ),
    "notes/reviews/codex_native_wp1_assignment_2026-11-10.md": (
        "9e1531d7d729ed9772781ea91501b468a4879a990af473ab21d4939c6ea4da5d"
    ),
}

CURRENT_COORDINATION_PATHS = (
    "notes/reviews/worker_dispatch_2026-11-10.md",
    "scripts/adhoc/monitor_worker_terminals_20261110.applescript",
    "notes/reviews/live-resource-pause-20261110/README.md",
    "notes/reviews/live-resource-pause-20261110/pfas.json",
    "notes/reviews/live-resource-pause-20261110/website.json",
    "scripts/adhoc/pause_contending_jobs_20261110.py",
)

APPENDIX_A_SHAS = {
    "plans/reviews/native_u3j_2026-11-09.md": (
        "6142f5ff851f04246b7dc06a6359490cbdcd69696779d942a149ed8fedada630"
    ),
    "plans/reviews/native_u3k_2026-11-09.md": (
        "8f53db8f19523213534874bd89ed4b8868dabcfc55fb5b9014da7bd438833f3f"
    ),
    "scratch-native-u1u3/u3k/composition-a2241d4c67b1/composition.json": (
        "6a3ade1472db2e19665cd7e1f2a170ab530e5e1527895aa2085b55ca70f41d45"
    ),
    "scratch-native-u1u3/u3k/schema-hit-canary-03426fd33/pytest.xml": (
        "2ca6d91cfd111334c1fe405fcd175752a668db4c33035ca0ff2535f188c12c10"
    ),
    "scratch-native-u1u3/u3k/composition-70457f66e6f1/composition.json": (
        "1561d42257e7fc6b8b3d49064a1ca117d01b945909ac03d2eb0a2e9e1fe06edb"
    ),
    "scratch-native-u1u3/u3k/grouping-canary.json": (
        "203d8208223f78d62b3def05153bf54103f72425f253bece0df33785ee593da3"
    ),
    "scratch-native-u1u3/u3k/grouping-correction-summary.json": (
        "be437ae4ce88652e7adf9d9f0ef8a1a0c85d8b49dd2a8df4dd529512902b7781"
    ),
    "scratch-native-u1u3/u3k/dependency-isolation-canary-2c6537d0f/dependency-write-denied.json": (
        "19730050656e62e28f0c949c8addd4479a4d84dd10f0583545c351576acbfdfd"
    ),
    "scratch-native-u1u3/u3k/final-validation-summary.json": (
        "397118dd5e7b231367abf0f09cc799aaf6baf0872b5d83b31998444daf2f5bd6"
    ),
    "scratch-native-u1u3/u3k/dependency-stop-audit.json": (
        "6dbd2d2914801db8e5e7d6d3bf9a7003f8e02568386e150d12db8d8721811efa"
    ),
    "scratch-native-u1u3/u3k/baseline-profile-summary.json": (
        "14bd79d6a8f7c7d6ad03cbc047ec6ab5e6b063abc48354c30ae227e58422b486"
    ),
    "scratch-native-u1u3/u3k/correction-summary.json": (
        "766d827c7774e8fd2ce01bc0a6ec2b1ffa1dde70de6fd80a9edce391fa3c05c95"
        if False
        else "766d827c7774e8fd2ce01bc0a6ec2b1ffa1dde70de6fd80a9edce31fa3c05c95"
    ),
    "scratch-native-u1u3/u3k/public-pair-grouped-summary.json": (
        "d72b3faface41226cc1cb5ee6cb5f5982b1f11e9986bcf2a8ccc26bc81cf6f8d"
    ),
    "scratch-native-u1u3/u3k/public-pair-summary.json": (
        "2ecfb00c88a23ad231009782e6b98c0aa6dd17ccaf201cbdae46f051ba070d58"
    ),
}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_repo(repo_root: Path, d4d_exec_root: Path | None) -> dict[str, object]:
    at_char = chr(64)
    verified_worktree: dict[str, str] = {}
    for rel, expected in PINNED_WORKTREE_SHAS.items():
        target = repo_root / rel
        actual = sha256_file(target)
        if actual != expected:
            raise AssertionError(f"Digest mismatch for {rel}: {actual} != {expected}")
        if at_char in target.read_text(encoding="utf-8"):
            raise AssertionError(f"Unexpected at-sign character in {rel}")
        verified_worktree[rel] = actual

    current_coordination: dict[str, str] = {}
    for rel in CURRENT_COORDINATION_PATHS:
        raw = (repo_root / rel).read_bytes()
        if not raw.strip():
            raise AssertionError(f"Empty current coordination artifact: {rel}")
        current_coordination[rel] = hashlib.sha256(raw).hexdigest()

    index_path = repo_root / "notes/reviews/native_latency_review_index_2026-11-10.md"
    index_text = index_path.read_text(encoding="utf-8")
    if at_char in index_text:
        raise AssertionError("Unexpected at-sign character in native_latency_review_index_2026-11-10.md")
    resolved_index_links: list[dict[str, str]] = []
    for label, target_href in re.findall(r"\[([^\]]+)\]\(([^)]+)\)", index_text):
        resolved = (index_path.parent / target_href).resolve()
        if not resolved.is_file():
            raise AssertionError(f"Broken relative link in index: [{label}]({target_href}) -> {resolved}")
        resolved_index_links.append({"label": label, "href": target_href, "sha256": sha256_file(resolved)})

    verified_appendix_a: dict[str, str] = {}
    if d4d_exec_root is not None and d4d_exec_root.is_dir():
        for rel, expected in APPENDIX_A_SHAS.items():
            target = d4d_exec_root / rel
            actual = sha256_file(target)
            if actual != expected:
                raise AssertionError(f"Appendix A digest mismatch for {rel}: {actual} != {expected}")
            verified_appendix_a[rel] = actual

    return {
        "index_sha256": sha256_file(index_path),
        "index_link_count": len(resolved_index_links),
        "index_links": resolved_index_links,
        "pinned_worktree_files_verified": len(verified_worktree),
        "current_coordination_sha256_observed": current_coordination,
        "appendix_a_files_verified": len(verified_appendix_a),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo",
        type=Path,
        default=Path(__file__).resolve().parents[2],
        help="Repository or worktree root",
    )
    parser.add_argument(
        "--d4d-executions",
        type=Path,
        default=Path("/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions"),
        help="Optional sibling d4d-executions directory for Appendix A artifact verification",
    )
    args = parser.parse_args()
    summary = verify_repo(args.repo.resolve(), args.d4d_executions)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
