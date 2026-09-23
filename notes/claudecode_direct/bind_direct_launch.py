"""Write the two records the direct-arm launcher requires (#2202).

`review`: binds an approving independent review and a successful CI run on
the registered code commit to the registration's hash. `word`: records the
maintainer's exact launch instruction for that same hash. The launcher refuses
to start without both, and each names the hash it was written for, so a
re-prepared registration needs both again. Neither makes a model call.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

KIND = "d4d_direct_arm_registration"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    path = Path(path)
    if path.exists():
        raise SystemExit(f"refusing to overwrite {path}")
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def load_registration(path):
    registration = json.loads(Path(path).read_bytes())
    if registration.get("kind") != KIND:
        raise SystemExit("not a direct-arm registration")
    return registration


def ci_run(run_id):
    """The run's head and conclusion, from GitHub."""
    raw = subprocess.check_output(["gh", "run", "view", str(run_id), "--json", "headSha,conclusion,name,status"], text=True)
    return json.loads(raw)


def review(args):
    registration = load_registration(args.registration)
    digest = sha(args.registration)
    independent = json.loads(Path(args.independent_review).read_bytes())
    if independent.get("verdict") != "approve" or independent.get("registration_sha256") != digest:
        raise SystemExit("the independent review does not approve this exact registration")
    run = ci_run(args.ci_run)
    if run.get("status") != "completed" or run.get("conclusion") != "success":
        raise SystemExit(f"CI run {args.ci_run} is not a completed success")
    if run.get("headSha") != registration["code_commit"]:
        raise SystemExit("CI run is not on the registered code commit")
    if not str(run.get("name", "")).startswith("Build and test"):
        raise SystemExit("CI run is not the build-and-test workflow")
    jobs = [job["id"] for job in registration["generation"]["jobs"]]
    save(args.out, {"verdict": "approve", "ci_conclusion": "success", "ci_run_id": int(args.ci_run),
                    "ci_head": run["headSha"], "registration_sha256": digest, "allowed_jobs": jobs,
                    "independent_review_sha256": sha(args.independent_review),
                    "recorded_at": datetime.now(timezone.utc).isoformat(),
                    "scope": "binds review and CI to this registration; not a launch instruction"})


def word(args):
    load_registration(args.registration)
    if not args.exact_response.strip():
        raise SystemExit("the maintainer's exact response is required")
    save(args.out, {"registration_sha256": sha(args.registration), "exact_response": args.exact_response,
                    "quoted_request": args.quoted_request, "recorded_at": datetime.now(timezone.utc).isoformat(),
                    "scope": "the maintainer's launch instruction for exactly this registration; one launch"})


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    r = commands.add_parser("review")
    r.add_argument("--registration", required=True)
    r.add_argument("--independent-review", required=True, help="JSON with verdict and registration_sha256")
    r.add_argument("--ci-run", required=True)
    r.add_argument("--out", required=True)
    r.set_defaults(run=review)
    w = commands.add_parser("word")
    w.add_argument("--registration", required=True)
    w.add_argument("--exact-response", required=True, help="the maintainer's words, verbatim")
    w.add_argument("--quoted-request", required=True, help="the question those words answered, verbatim")
    w.add_argument("--out", required=True)
    w.set_defaults(run=word)
    args = parser.parse_args(argv)
    args.run(args)


if __name__ == "__main__":
    main()
