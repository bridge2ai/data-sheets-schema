"""The wheel installs into a clean environment and generates from a
directory that is neither a checkout nor holds a `pyproject.toml` (#1301).

Marked `install`: it builds the wheel, creates a virtual environment and
installs the wheel with its declared dependencies (network), then runs the
offline generation path there — the plan, the phase assembly with a fake
client, the derived core, the provenance record — with the study's data
tree absent. Skipped only when `poetry` is not available.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

pytestmark = pytest.mark.install


@unittest.skipUnless(os.environ.get("D4D_INSTALL_TESTS"),
                     "set D4D_INSTALL_TESTS=1 to build the wheel and install it into a fresh venv (minutes, network)")
@unittest.skipUnless(shutil.which("poetry"), "poetry is not installed")
class TestTheInstalledWheel(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="d4d-wheel-"))
        dist = cls.tmp / "dist"
        subprocess.run(["poetry", "build", "-o", str(dist)], cwd=ROOT, check=True,
                       capture_output=True, text=True)
        (cls.wheel,) = list(dist.glob("*.whl"))
        cls.venv = cls.tmp / "venv"
        subprocess.run([sys.executable, "-m", "venv", str(cls.venv)], check=True)
        cls.python = cls.venv / ("Scripts" if os.name == "nt" else "bin") / "python"
        # pytest only so the offline fake client of the runner tests can be
        # imported by the child; the wheel's own dependencies come from its
        # metadata — which is what this canary checks.
        r = subprocess.run([str(cls.python), "-m", "pip", "install", "--quiet", str(cls.wheel), "pytest"],
                           capture_output=True, text=True)
        if r.returncode != 0:
            # An opted-in canary fails on an install failure; it does not skip (#1489).
            raise AssertionError(f"the wheel did not install: {r.stderr[-1200:]}")
        cls.work = cls.tmp / "work"
        cls.work.mkdir()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def _run(self, code: str, **env):
        # The wheel, not this checkout: a PYTHONPATH pointing at `src/` (how the
        # suite is run from a worktree) would make the child import the
        # checkout and prove nothing.
        e = {k: v for k, v in os.environ.items()
             if not k.startswith(("D4D_", "ANTHROPIC", "CBORG")) and k not in ("PYTHONPATH", "VIRTUAL_ENV")}
        e.update(env)
        return subprocess.run([str(self.python), "-c", textwrap.dedent(code)], cwd=self.work,
                              capture_output=True, text=True, env=e)

    def test_the_metadata_requires_linkml_unconditionally(self):
        """#1476: `linkml` was in the `docs` extra as well as the main table, and
        poetry emitted it extra-only."""
        r = self._run("""
            from importlib.metadata import requires
            reqs = [x for x in requires("data-sheets-schema") if x.startswith("linkml")]
            assert reqs, "no linkml requirement"
            assert all("extra ==" not in x for x in reqs), reqs
            import linkml, linkml.validator          # importable in the install
            print("ok")
        """)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_it_is_not_a_checkout_and_the_resources_are_there(self):
        r = self._run("""
            from data_sheets_schema import resources
            assert not resources.is_checkout(), resources.CHECKOUT_ROOT
            p = resources.resource_path("src/download/prompts/d4d_generic_arm_prompt_v9.md")
            assert p.exists(), p
            assert resources.repo_relative(p) == "src/download/prompts/d4d_generic_arm_prompt_v9.md", p
            from data_sheets_schema import prompt_registry as pr
            st, why = pr.disk_status("src/download/prompts/d4d_generic_arm_prompt_v9.md")
            assert st == pr.CANONICAL, (st, why)
            print("ok")
        """)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_the_offline_generation_path_runs_without_the_study_tree(self):
        bundle = self.work / "clinical_preprocessed.txt"
        bundle.write_text("FILE: overview.txt\nOpen Clinical Cohort. A synthetic observational study of "
                          "adult outpatients, released under CC-BY-4.0. 1,200 participants at three sites.\n" * 30,
                          encoding="utf-8")
        r = self._run(f"""
            import json
            from pathlib import Path
            from click.testing import CliRunner
            from data_sheets_schema.cli import cli
            bundle = Path({str(bundle)!r})
            r = CliRunner().invoke(cli, ["bundle", "chunk", "--bundle", str(bundle)]) if False else None
            r = CliRunner().invoke(cli, ["api", "plan", "--project", "EXTERNAL_CLINICAL", "--bundle", str(bundle),
                                         "--label", "2026-09-13_x-api-generic_rep1", "--condition", "generic",
                                         "--out-dir", "out", "--json"])
            assert r.exit_code == 0, r.output
            plan = json.loads(r.output)
            assert plan["approx_total_input_tokens"] > 0
            assert "src/" not in (r.output if "FileNotFound" in r.output else "")
            from data_sheets_schema import schema_digest
            text = schema_digest.digest_text("Dataset")
            assert "## `title`" in text
            print("ok")
        """)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotIn("requires a repository checkout", r.stdout + r.stderr)

    def test_the_schema_preflight_passes_from_the_install(self):
        """#1478: the rebuilt merged schema names the logical source, so the
        sync gate reads IN_SYNC from any directory."""
        r = self._run("""
            from data_sheets_schema import schema_sync
            rows = schema_sync.check()
            assert rows and all(r["status"] == schema_sync.IN_SYNC for r in rows), rows
            print("ok")
        """)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_a_fake_client_generation_writes_and_validates_from_the_install(self):
        """#1489: the whole offline path from an installed package in a
        directory that is no checkout — every phase through the runner's
        fake client, the derived core, the record write, the deterministic
        checks, and `linkml-validate` through the install's own interpreter."""
        bundle = self.work / "clinical_preprocessed.txt"
        bundle.write_text("FILE: overview.txt\nOpen Clinical Cohort. A synthetic observational study of "
                          "adult outpatients, released under CC-BY-4.0. 1,200 participants at three sites.\n" * 30,
                          encoding="utf-8")
        r = self._run(f"""
            import sys, yaml
            from pathlib import Path
            sys.path.insert(0, {str(ROOT / "tests" / "test_download")!r})
            from test_api_runner import FakeClient            # imports data_sheets_schema from the install
            from data_sheets_schema import api_runner, resources
            assert not resources.is_checkout()
            out = Path("out")
            spec = api_runner.RunSpec(project="EXTERNAL_CLINICAL", arm="BASELINE (input documents only)",
                                      method="claudecode_api", bundle=Path({str(bundle)!r}),
                                      label="2026-09-13_x-api-generic_rep1", out_dir=out)
            assert spec.profile == "neutral", (spec.profile, spec.profile_basis)
            res = api_runner.execute(spec, client=FakeClient())
            for p in (spec.full_path, spec.core_path, spec.report_path):
                assert p.exists() and p.stat().st_size > 0, p
            rec = yaml.safe_load((out / "EXTERNAL_CLINICAL_provenance.yaml").read_text(encoding="utf-8"))
            assert rec["record_mode"] == "live"
            f = rec["prompts"]["files"][0]
            assert f["path"] == "src/download/prompts/d4d_generic_arm_prompt.md", f
            assert f["exists"] is True and f["bytes"] > 0 and len(f["sha256"]) == 64, f
            assert all(pb["exists"] for pb in rec["playbooks"]["files"]), rec["playbooks"]
            assert rec["schema"]["profile"] == "neutral", rec["schema"]
            v = rec.get("validation") or {{}}
            assert v.get("passed") is not None and not v.get("failure"), v
            from data_sheets_schema.provenance import check_record
            violations, why = check_record(rec)
            assert why is None and not violations, (violations, why)
            print("ok", len(res["usage"]))
        """)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("ok 4", r.stdout)

    def test_a_record_written_from_the_install_stores_relative_resource_paths(self):
        full = self.work / "rec" / "P_d4d.yaml"
        full.parent.mkdir(exist_ok=True)
        full.write_text("# Generated: 2026-09-13\nid: https://example.org/p\ntitle: P\n", encoding="utf-8")
        r = self._run(f"""
            from pathlib import Path
            from data_sheets_schema.provenance import build_record
            from data_sheets_schema import api_runner
            full = Path({str(full)!r})
            rec = build_record("P", "claudecode_api", "L", mode="live", input_bundle=full, input_verified=True,
                               prompt_paths=[api_runner.GENERIC_PROMPT_V9],
                               outputs={{"full": full, "core": full.with_name("c.yaml"), "report": full.with_name("r.md")}})
            files = rec.data["prompts"]["files"]
            paths = [f["path"] if isinstance(f, dict) else str(f) for f in files]
            assert paths == ["src/download/prompts/d4d_generic_arm_prompt_v9.md"], paths
            print("ok")
        """)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
