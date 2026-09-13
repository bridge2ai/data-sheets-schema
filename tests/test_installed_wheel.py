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
        # Install only the wheel and its declared runtime dependencies.
        r = subprocess.run([str(cls.python), "-m", "pip", "install", "--quiet", str(cls.wheel)],
                           capture_output=True, text=True)
        if r.returncode != 0:
            # An opted-in canary fails on an install failure; it does not skip (#1489).
            raise AssertionError(f"the wheel did not install: {r.stderr[-1200:]}")
        cls.work = cls.tmp / "work"
        cls.work.mkdir()
        for fixture in ("installed_workflow_fixture.py", "judge_fixtures.py"):
            shutil.copy2(ROOT / "tests" / fixture, cls.work / fixture)

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

    def test_the_metadata_declares_the_runners_sdk_and_ships_only_the_rubrics(self):
        """#1636: `anthropic` and `httpx` are requirements of the wheel, at the
        locked SDK; #1637: the rubric directory ships the rubrics alone."""
        import zipfile
        r = self._run("""
            from importlib.metadata import requires, version
            reqs = requires("data-sheets-schema")
            assert any(x.startswith("anthropic") for x in reqs), reqs
            assert any(x.startswith("httpx") for x in reqs), reqs
            assert version("anthropic") == "0.72.0", version("anthropic")
            print("ok")
        """)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        names = zipfile.ZipFile(self.wheel).namelist()
        rubric = sorted(n for n in names if n.startswith("data/rubric/"))
        self.assertEqual(rubric, ["data/rubric/rubric10.txt", "data/rubric/rubric20.txt"], rubric)

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
            r = CliRunner().invoke(cli, ["api", "plan", "--project", "EXTERNAL_CLINICAL", "--bundle", str(bundle),
                                         "--label", "2026-09-13_x-api-generic_rep1", "--condition", "generic",
                                         "--out-dir", "out", "--json"])
            assert r.exit_code == 0, r.output
            plan = json.loads(r.output)
            assert plan["approx_total_input_tokens"] > 0
            assert "FileNotFound" not in r.output and "requires a repository checkout" not in r.output, r.output
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
            import yaml
            from pathlib import Path
            from installed_workflow_fixture import GenerationClient, check_installed_evaluation_and_rendering
            from data_sheets_schema import api_runner, resources
            assert not resources.is_checkout()
            out = Path("out")
            spec = api_runner.RunSpec(project="EXTERNAL_CLINICAL", arm="BASELINE (input documents only)",
                                      method="claudecode_api", bundle=Path({str(bundle)!r}),
                                      label="2026-09-13_x-api-generic_rep1", out_dir=out)
            assert spec.profile == "neutral", (spec.profile, spec.profile_basis)
            res = api_runner.execute(spec, client=GenerationClient())
            for p in (spec.full_path, spec.core_path, spec.report_path):
                assert p.exists() and p.stat().st_size > 0, p
            rec = yaml.safe_load((out / "EXTERNAL_CLINICAL_provenance.yaml").read_text(encoding="utf-8"))
            assert rec["record_mode"] == "live"
            f = rec["prompts"]["files"][0]
            assert f["path"] == "src/download/prompts/d4d_generic_arm_prompt.md", f
            assert f["exists"] is True and f["bytes"] > 0 and len(f["sha256"]) == 64, f
            pbs = rec["playbooks"]["files"]
            assert len(pbs) >= 4 and all(pb["exists"] and len(pb["sha256"]) == 64 for pb in pbs), rec["playbooks"]   # #1578
            assert rec["schema"]["profile"] == "neutral", rec["schema"]
            v = rec.get("validation") or {{}}
            assert v.get("passed") is True and not v.get("problems") and not v.get("failure"), v
            assert (rec.get("pair_consistency") or {{}}).get("ran") is True, rec.get("pair_consistency")
            assert (rec.get("form") or {{}}).get("checked") is True and (rec.get("grounding") or {{}}).get("checked") is True, (rec.get("form"), rec.get("grounding"))   # the runner computes them inline
            repo = rec.get("repo") or {{}}
            assert repo.get("resource_kind") == "install" and repo.get("dirty") is False and repo.get("package_version"), repo   # measured against the RECORD (#1683)
            assert (rec.get("core_derivation") or {{}}).get("derived") is True, rec.get("core_derivation")
            notes = rec.get("notes") or []
            assert any("Model settings read from .github/workflows/d4d_assistant_deterministic.config" in n for n in notes), notes   # the shipped config was read (#1529)
            from data_sheets_schema.provenance import check_record
            violations, why = check_record(rec)
            assert why is None and not violations, (violations, why)
            check_installed_evaluation_and_rendering(spec.full_path, spec.core_path)
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
