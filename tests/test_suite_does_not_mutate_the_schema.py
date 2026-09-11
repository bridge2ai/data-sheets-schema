"""Running the tests must not rewrite the repository's merged schemas (#1208).

`tests/test_d4d_full_schema.py` used to run `make full-schema` in the
repository root as class setup, rewriting
`src/data_sheets_schema/schema/data_sheets_schema_all.yaml` in place.
`gen-linkml` writes that file non-atomically, so a concurrent reader saw a
partial one — and `schema_sync.check`, which `api_runner.execute` treats as
fatal, then reported the merged schema as differing from a fresh build of
its source. The rewrite produces **identical bytes**: the committed file
reproduces exactly, on Linux and on macOS, so nothing about the content
was ever wrong and a content check could never have found this. What
mattered was that the file was replaced at all, while other tests were
reading it. Serially the rewrite finished before anything else looked;
under `pytest -n auto` between one and nine runner-gate tests failed per
run, on different tests each time, which read as flakiness rather than as
one test mutating shared state.

The committed merged schemas are an input to every generation run — their
sha256 is recorded in every provenance record — so a test suite that
rewrites them is changing the thing under test.
"""
import hashlib
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MERGED = (ROOT / "src/data_sheets_schema/schema/data_sheets_schema_all.yaml",
          ROOT / "src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml")


def _state():
    """Hash *and* mtime. The hash alone cannot see this: the rewrite puts
    back byte-identical content, and the damage is the window during the
    write, not the result."""
    out = {}
    for p in MERGED:
        if p.exists():
            st = p.stat()
            out[p.name] = (hashlib.sha256(p.read_bytes()).hexdigest(), st.st_mtime_ns)
    return out


class TheSuiteLeavesTheMergedSchemasAlone(unittest.TestCase):
    def test_the_full_schema_tests_do_not_rewrite_the_committed_artifact(self):
        """Behavioural, not a grep: run the module that used to do it and
        compare hash and mtime before and after."""
        if not all(p.exists() for p in MERGED):
            self.skipTest("merged schemas are not built in this checkout")
        before = _state()
        r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                            "tests/test_d4d_full_schema.py"],
                           cwd=ROOT, capture_output=True, text=True, timeout=1800)
        self.assertIn(r.returncode, (0, 5), (r.stdout or r.stderr)[-600:])
        after = _state()
        self.assertEqual(after, before,
                         "running the full-schema tests replaced a committed merged schema "
                         "(the content may be identical — the mtime says it was rewritten, "
                         "and a concurrent reader sees the partial file); generate into a "
                         "temporary directory instead (#1208)")

    #: `make` targets that write a committed artifact. `validate-core` and
    #: the other checking targets are fine in the repository root — they
    #: read. These rewrite, and a test that calls one is mutating an input
    #: every other test and every generation run shares.
    GENERATING_TARGETS = ("full-schema", "gen-project", "regen-all",
                          "gen-core-schema", "gen-doc", "gendoc")

    def test_no_test_calls_a_generating_make_target_in_the_repository_root(self):
        """The narrow guard for the shape that caused it. The behavioural
        test above is the real one; this names the offender at the line
        rather than as a hash that changed."""
        offenders = []
        for path in sorted((ROOT / "tests").rglob("test_*.py")):
            if path.name == Path(__file__).name:
                continue
            for n, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                if '"make"' in line and any(f'"{t}"' in line for t in self.GENERATING_TARGETS):
                    offenders.append(f"{path.relative_to(ROOT).as_posix()}:{n}")
        self.assertEqual(offenders, [],
                         "these run a generating `make` target in the repository root, which "
                         "rewrites a committed artifact while other tests read it (#1208)")
