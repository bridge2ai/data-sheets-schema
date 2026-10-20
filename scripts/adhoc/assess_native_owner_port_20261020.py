"""Read-only #4354/#4740 owner-lineage port inventory (2026-10-20).

Inputs: the preserved aa09 owner repository and current Track N checkout.
Output: JSON file-level changes and overlap; this is not an integration test.
Git objects are read directly; no checkout, fetch, merge or source edit occurs.
"""
import argparse
import json
from pathlib import Path
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preserved-git", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]

    def historical(*command):
        return subprocess.check_output(
            ["git", "--git-dir=" + str(args.preserved_git), *command], text=True)

    def current(*command):
        return subprocess.check_output(["git", "-C", str(root), *command], text=True)

    owner = historical("rev-parse", "aa09dbbc6").strip()
    base = historical("merge-base", owner, "38fb11d5").strip()
    source = current("rev-parse", "HEAD").strip()
    changes = []
    for line in historical("diff", "--numstat", base, owner).splitlines():
        added, removed, path = line.split("\t", 2)
        changes.append({"path": path,
                        "added_lines": None if added == "-" else int(added),
                        "removed_lines": None if removed == "-" else int(removed)})
    current_changed = set(current("diff", "--name-only", base, source).splitlines())
    src = [row for row in changes if row["path"].startswith("src/")]
    new_native = [row for row in src if row["removed_lines"] == 0
                  and row["path"].endswith((
                      "/native_clock_domain_v1.py", "/native_owner_control_v1.py",
                      "/native_owner_profile_v1.py", "/native_owner_runner_v1.py",
                      "/native_stream_coordination_v1.py"))]
    result = {
        "owner_commit": owner, "common_base": base, "assigned_head": source,
        "total_changed_files": len(changes),
        "source_changed_files": len(src),
        "new_owner_modules": new_native,
        "new_owner_module_lines": sum(row["added_lines"] for row in new_native),
        "source_overlap_with_assigned_branch": [
            row["path"] for row in src if row["path"] in current_changed],
        "source_changes": src,
        "tracked_work_in_progress": current("diff", "--name-only", "HEAD").splitlines(),
        "acceptance_nodes": [
            "tests/test_native_owner_stage_helper.py::test_registered_helper_process_publishes_first_receipt_stage_with_real_clock",
            "tests/test_native_owner_receipt_process.py::test_registered_receipt_process_reads_current_inputs_with_real_clock",
        ],
        "limits": "File overlap is a review inventory, not proof of a merge conflict or complete dynamic import closure.",
    }
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({key: value for key, value in result.items()
                      if key not in {"source_changes", "tracked_work_in_progress"}}))


if __name__ == "__main__":
    main()
