"""A dataset that exists only in a supplied manifest goes from input
documents through preprocessing, concatenation, chunking, an offline
generation plan and status without editing Python or the Makefile (#637's
acceptance test; #621, #623, #624, #1299).

Everything here is synthetic and offline: a temporary manifest declaring
`EXTERNAL_CLINICAL`, raw documents in an arbitrary directory, no network, no
model call, no spend. The study's own manifest is never read by the external
run, and the test says so by checking what the record attests.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import socket
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml
from click.testing import CliRunner

ROOT = Path(__file__).resolve().parents[1]
STUDY_MANIFEST = ROOT / "data/preprocessed/source_manifest.yaml"


def _manifest(tmp: Path, *, raw_dir: Path, bundle: Path | None = None) -> Path:
    doc = {
        "version": 1,
        "naming": {"EXTERNAL_CLINICAL": {"canonical_label": "Open Clinical Cohort",
                                          "variants": ["OCC"]}},
        "scope": {"EXTERNAL_CLINICAL": {"referent": "the Open Clinical Cohort release",
                                         "referent_id": "https://example.org/occ"}},
        "projects": {
            "EXTERNAL_CLINICAL": {
                "raw_dir": str(raw_dir),
                **({"bundle": str(bundle)} if bundle else {}),
                "sources": [
                    {"id": "occ_overview", "raw_file": "overview.txt",
                     "processed_file": "overview.txt", "source_type": "documentation",
                     "priority": 1},
                    {"id": "occ_protocol", "raw_file": "protocol.txt",
                     "processed_file": "protocol.txt", "source_type": "protocol",
                     "priority": 2},
                ],
            },
            # The legacy override key beside the projects is metadata, not a
            # project (#626). Named for a project this manifest does not
            # declare, so it proves only that: a `<P>_source_dir` for a
            # declared P would say P's files live elsewhere.
            "ANOTHER_COHORT_source_dir": str(tmp / "nowhere"),
        },
    }
    p = tmp / "manifest.yaml"
    p.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
    return p


class _Offline(unittest.TestCase):
    """Every test runs from the repository root with the network refused."""

    def setUp(self):
        self._cwd = os.getcwd()
        os.chdir(ROOT)
        self._net = patch.object(socket.socket, "connect",
                                 side_effect=AssertionError("network refused in this test"))
        self._net.start()
        self.tmp = Path(tempfile.mkdtemp(prefix="d4d-external-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)      # nothing leaks (#1367 review, should-fix 2)
        self.raw = self.tmp / "docs"
        self.raw.mkdir()
        (self.raw / "overview.txt").write_text(
            "Open Clinical Cohort. A public, synthetic observational study of adult "
            "outpatients. Released under CC-BY-4.0. Contact: occ@example.org.\n" * 20,
            encoding="utf-8")
        (self.raw / "protocol.txt").write_text(
            "Protocol. Participants consented to secondary use. 1,200 participants, "
            "three sites, enrolment 2024-2025. Data dictionary: 140 variables.\n" * 20,
            encoding="utf-8")

    def tearDown(self):
        self._net.stop()
        os.chdir(self._cwd)


class TestTheRegistry(_Offline):

    def test_a_manifest_declares_its_projects_and_the_override_key_is_not_one(self):
        from data_sheets_schema.registry import load_registry
        reg = load_registry(_manifest(self.tmp, raw_dir=self.raw))
        self.assertEqual(reg.projects(), ["EXTERNAL_CLINICAL"])
        self.assertEqual(reg.raw_dir("EXTERNAL_CLINICAL"), self.raw)
        self.assertEqual(len(reg.sources("EXTERNAL_CLINICAL")), 2)

    def test_the_study_manifest_still_declares_its_five(self):
        from data_sheets_schema.registry import load_registry
        reg = load_registry(STUDY_MANIFEST)
        self.assertEqual(reg.projects(), ["AI_READI", "CHORUS", "CM4AI", "VOICE", "VOICE_PEDIATRIC"])
        self.assertEqual(reg.source_dir("VOICE_PEDIATRIC"), Path("data/preprocessed/individual/VOICE"))

    def test_a_project_whose_files_are_another_projects_is_not_preprocessed(self):
        """VOICE_PEDIATRIC's preprocessed files are VOICE's (#302); asking
        the preprocessor for it must say so, not report every source missing
        under a raw directory it never had (#1367 review, must-fix 9)."""
        import sys
        sys.path.insert(0, str(ROOT))
        from src.download.preprocess_sources import preprocess_manifest
        stats = preprocess_manifest(STUDY_MANIFEST, Path("data/raw"), self.tmp / "out", ["VOICE_PEDIATRIC"])
        self.assertEqual(stats["errors"], 0)
        self.assertEqual(stats["projects"]["VOICE_PEDIATRIC"]["source_dir"], "data/preprocessed/individual/VOICE")
        self.assertFalse((self.tmp / "out" / "VOICE_PEDIATRIC").exists())

    def test_no_manifest_is_an_empty_registry_not_the_study(self):
        from data_sheets_schema.registry import load_registry
        self.assertEqual(load_registry(None).projects(), [])
        self.assertIsNone(load_registry(None).md5())


class TestTheCliAcceptsAManifestDeclaredDataset(_Offline):

    def test_list_projects_reads_the_selected_manifest(self):
        from data_sheets_schema.cli import cli
        m = _manifest(self.tmp, raw_dir=self.raw)
        r = CliRunner().invoke(cli, ["download", "list-projects", "--manifest", str(m), "--plain"])
        self.assertEqual(r.exit_code, 0, r.output)
        self.assertEqual(r.output.split(), ["EXTERNAL_CLINICAL"])
        r = CliRunner().invoke(cli, ["download", "list-projects", "--plain"])
        self.assertEqual(r.exit_code, 0, r.output)
        self.assertIn("VOICE_PEDIATRIC", r.output.split())

    def test_an_undeclared_project_is_refused_by_name_of_the_registry(self):
        from data_sheets_schema.cli import cli
        m = _manifest(self.tmp, raw_dir=self.raw)
        r = CliRunner().invoke(cli, ["download", "preprocess", "--manifest", str(m),
                                     "--project", "SOMETHING_ELSE",
                                     "--output-dir", str(self.tmp / "pre")])
        self.assertNotEqual(r.exit_code, 0)
        self.assertIn("not declared by the selected manifest", r.output)
        self.assertIn("EXTERNAL_CLINICAL", r.output)
        self.assertNotIn("AI_READI", r.output)      # the study is not the universe

    def test_documents_go_through_preprocessing_concatenation_and_chunking(self):
        from data_sheets_schema.cli import cli
        m = _manifest(self.tmp, raw_dir=self.raw)
        pre = self.tmp / "pre"
        r = CliRunner().invoke(cli, ["download", "preprocess", "--manifest", str(m),
                                     "--project", "EXTERNAL_CLINICAL",
                                     "--input-dir", str(self.tmp / "unused-raw"),
                                     "--output-dir", str(pre)])
        self.assertEqual(r.exit_code, 0, r.output)
        self.assertTrue((pre / "EXTERNAL_CLINICAL" / "overview.txt").exists(), r.output)
        bundle = self.tmp / "out" / "EXTERNAL_CLINICAL_preprocessed.txt"
        r = CliRunner().invoke(cli, ["download", "concatenate", "--manifest", str(m),
                                     "--project", "EXTERNAL_CLINICAL",
                                     "--input-dir", str(pre), "--output-file", str(bundle)])
        self.assertEqual(r.exit_code, 0, r.output)
        self.assertTrue(bundle.exists(), r.output)
        text = bundle.read_text(encoding="utf-8")
        self.assertIn("Open Clinical Cohort", text)
        # Chunk the explicit bundle; the manifest lands beside it, not in the
        # study's chunks directory, and a second bundle with the same basename
        # elsewhere gets its own (#1299).
        r = CliRunner().invoke(cli, ["bundle", "chunk", "--bundle", str(bundle)])
        self.assertEqual(r.exit_code, 0, r.output)
        from data_sheets_schema.chunking import load_manifest, manifest_for
        mpath = manifest_for(bundle)
        self.assertEqual(mpath.parent, bundle.parent)
        self.assertTrue(mpath.exists())
        self.assertEqual(load_manifest(mpath)["bundle_md5"],
                         hashlib.md5(bundle.read_bytes()).hexdigest())
        other = self.tmp / "elsewhere" / "EXTERNAL_CLINICAL_preprocessed.txt"
        other.parent.mkdir()
        other.write_text(text + "\nmore\n", encoding="utf-8")
        self.assertNotEqual(manifest_for(other), mpath)
        self.assertFalse(str(manifest_for(other)).startswith("data/preprocessed/chunks"))
        r = CliRunner().invoke(cli, ["bundle", "chunk", "--check", "--strict", "--bundle", str(bundle)])
        self.assertEqual(r.exit_code, 0, r.output)
        r = CliRunner().invoke(cli, ["bundle", "chunk", "--check", "--strict", "--bundle", str(other)])
        self.assertEqual(r.exit_code, 1, r.output)       # missing: fails before any spend


class TestGenerationContextIsExplicit(_Offline):

    def _bundle(self) -> tuple[Path, Path]:
        m = _manifest(self.tmp, raw_dir=self.raw)
        bundle = self.tmp / "EXTERNAL_CLINICAL_preprocessed.txt"
        bundle.write_text("FILE: overview.txt\n" + (self.raw / "overview.txt").read_text()
                          + "\nFILE: protocol.txt\n" + (self.raw / "protocol.txt").read_text(),
                          encoding="utf-8")
        from data_sheets_schema.chunking import write_manifest_for
        write_manifest_for(bundle)
        return m, bundle

    def test_an_external_bundle_with_no_manifest_gets_no_study_context(self):
        from data_sheets_schema.cli.api import _spec
        from data_sheets_schema.api_runner import context_blocks, resolve_prompt
        _, bundle = self._bundle()
        # The project key is the study's own, and the bundle is not the
        # study's: the study manifest must not be selected implicitly (#621).
        # Nothing said about a manifest: the rule decides, and it decides
        # none. Also for a spec built directly, not through the CLI.
        from data_sheets_schema.api_runner import RunSpec, build_phase
        for spec in (_spec("VOICE", "baseline", "2026-09-12_x_rep1", "generic_v9", bundle=str(bundle)),
                     RunSpec(project="VOICE", arm="BASELINE (input documents only)",
                             method="claudecode_api", bundle=bundle,
                             label="2026-09-12_x_rep1", condition="generic_v9")):
            self.assertIsNone(spec.manifest)
            self.assertIn("not used", spec.manifest_line.lower())
            blocks = context_blocks(spec)
            for name in ("source_ranking", "declared_naming", "declared_scope"):
                self.assertFalse(blocks[name]["sent"], (name, blocks[name]))
            self.assertNotIn("Bridge2AI", resolve_prompt(spec))
            self.assertNotIn("source_manifest.yaml", resolve_prompt(spec))
            sent = "\n".join(b["text"] for b in build_phase(spec, "full", carry={}).cached_blocks)
            self.assertNotIn("Grand Challenge", sent)
            self.assertNotIn("DECLARED NAMING", sent)
            self.assertNotIn("DECLARED SCOPE", sent)

    def test_the_study_bundle_selects_the_study_manifest_as_before(self):
        from data_sheets_schema.cli.api import _spec
        from data_sheets_schema.registry import DEFAULT_MANIFEST
        spec = _spec("CHORUS", "baseline", "2026-09-12_x_rep1", "generic_v9")
        self.assertEqual(spec.manifest, DEFAULT_MANIFEST)
        self.assertIn("data/preprocessed/source_manifest.yaml", spec.manifest_line)

    def test_a_declared_external_dataset_gets_its_own_manifests_context(self):
        from data_sheets_schema.cli.api import _spec
        from data_sheets_schema.api_runner import context_blocks, naming_block, scope_block
        m, bundle = self._bundle()
        spec = _spec("EXTERNAL_CLINICAL", "baseline", "2026-09-12_x_rep1", "generic_v9",
                     bundle=str(bundle), manifest=str(m))
        self.assertEqual(spec.manifest, m)
        self.assertIn("Open Clinical Cohort", naming_block(spec.project, spec.manifest_line, manifest=spec.manifest))
        self.assertNotIn("Bridge2AI", naming_block(spec.project, spec.manifest_line, manifest=spec.manifest))
        self.assertIn("Open Clinical Cohort release", scope_block(spec.project, spec.manifest_line, manifest=spec.manifest))
        blocks = context_blocks(spec)
        self.assertTrue(blocks["declared_naming"]["sent"])
        self.assertTrue(blocks["declared_scope"]["sent"])
        # What the model is actually sent, not the helpers (#1367 review,
        # must-fix 1): the assembled phase carries this manifest's context.
        from data_sheets_schema.api_runner import build_phase
        sent = "\n".join(b["text"] for b in build_phase(spec, "full", carry={}).cached_blocks)
        self.assertIn('call this project "Open Clinical Cohort"', sent)
        self.assertIn("Open Clinical Cohort release", sent)
        self.assertNotIn("Bridge2AI", sent)
        self.assertNotIn("Grand Challenge", sent)

    def test_an_offline_plan_assembles_for_a_receipt_condition(self):
        from data_sheets_schema.cli import cli
        m, bundle = self._bundle()
        r = CliRunner().invoke(cli, ["api", "plan", "--project", "EXTERNAL_CLINICAL",
                                     "--bundle", str(bundle), "--manifest", str(m),
                                     "--condition", "generic_v9",
                                     "--label", "2026-09-12_x-api-generic-v9_rep1",
                                     "--out-dir", str(self.tmp / "out"), "--json"])
        self.assertEqual(r.exit_code, 0, r.output)
        plan = json.loads(r.output)
        self.assertGreater(plan["approx_total_input_tokens"], 0)
        self.assertEqual(plan["bundle"], str(bundle))

    def test_provenance_records_the_selected_manifest_or_none_never_the_study(self):
        from data_sheets_schema.provenance import build_record
        from data_sheets_schema.registry import DEFAULT_MANIFEST
        m, bundle = self._bundle()
        out = self.tmp / "rec"
        out.mkdir()
        full = out / "EXTERNAL_CLINICAL_d4d.yaml"
        full.write_text("# Generated: 2026-09-12\n# Source bundle: " + str(bundle)
                        + "\nid: https://example.org/occ\ntitle: Open Clinical Cohort\n",
                        encoding="utf-8")
        common = dict(mode="live", input_bundle=bundle, input_verified=True,
                      outputs={"full": full, "core": out / "c.yaml", "report": out / "r.md"})
        none = build_record("EXTERNAL_CLINICAL", "claudecode_api", "L", manifest=None, **common)
        sm = none.data["inputs"]["source_manifest"]
        self.assertIsNone(sm["path"])
        self.assertIsNone(sm["md5"])
        self.assertIn("no source manifest", sm["basis"])
        self.assertFalse(any(u["field"] == "inputs.source_manifest.md5"
                             for u in none.data.get("unrecoverable") or []))
        mine = build_record("EXTERNAL_CLINICAL", "claudecode_api", "L", manifest=m, **common)
        self.assertEqual(mine.data["inputs"]["source_manifest"]["path"], str(m))
        self.assertEqual(mine.data["inputs"]["source_manifest"]["md5"],
                         hashlib.md5(m.read_bytes()).hexdigest())
        # The chunk manifest beside the external bundle is what anchors the
        # receipt ids, and the record names it (#1299).
        self.assertIsNotNone(mine.data["inputs"]["chunks"])
        self.assertEqual(Path(mine.data["inputs"]["chunks"]["path"]).parent, bundle.parent)
        self.assertNotEqual(sm["path"], str(DEFAULT_MANIFEST))

    def test_batch_takes_a_manifest_and_per_project_bundles(self):
        from data_sheets_schema.cli import cli
        m, bundle = self._bundle()
        r = CliRunner().invoke(cli, ["api", "batch", "--manifest", str(m),
                                     "--project-bundle", f"EXTERNAL_CLINICAL={bundle}",
                                     "--condition", "generic_v9", "--replicates", "1",
                                     "--label-prefix", "2026-09-12_x-api-generic-v9",
                                     "--dry-run"])
        self.assertEqual(r.exit_code, 0, r.output)
        self.assertIn("EXTERNAL_CLINICAL", r.output)
        self.assertIn("1 runs", r.output)
        self.assertNotIn("AI_READI", r.output)     # the manifest's projects, not the study's four


class TestStatusAndMakeSeeTheRegistry(_Offline):

    def test_status_lists_the_manifests_projects(self):
        from data_sheets_schema.cli import cli
        m = _manifest(self.tmp, raw_dir=self.raw)
        r = CliRunner().invoke(cli, ["utils", "status", "--manifest", str(m)])
        self.assertEqual(r.exit_code, 0, r.output)
        self.assertIn("EXTERNAL_CLINICAL", r.output)
        self.assertNotIn("AI_READI", r.output)

    def test_the_makefile_asks_the_cli_for_its_projects(self):
        text = (ROOT / "project.Makefile").read_text(encoding="utf-8")
        self.assertNotRegex(text, r"(?m)^PROJECTS\s*=\s*AI_READI")
        self.assertRegex(text, r"(?m)^PROJECTS\s*\?=.*list-projects")
        # And a registry that cannot be read is an error, not an empty loop
        # (#1367 review, must-fix 8).
        self.assertIn("REGISTRY_UNAVAILABLE", text)
        self.assertRegex(text, r"\$\(error the project registry could not be read")

    def test_a_missing_manifest_is_a_failure_for_list_projects(self):
        from data_sheets_schema.cli import cli
        r = CliRunner().invoke(cli, ["download", "list-projects", "--plain",
                                     "--manifest", str(self.tmp / "absent.yaml")])
        self.assertEqual(r.exit_code, 1, r.output)
        self.assertIn("does not exist", r.output)
        self.assertNotIn("EXTERNAL_CLINICAL", r.output)

    def test_commands_without_a_manifest_option_take_the_root_one(self):
        """Fourteen commands validate --project but have no --manifest of
        their own; `d4d --manifest M <command>` is their registry (#1367
        review, must-fix 4)."""
        from data_sheets_schema.cli import cli
        m = _manifest(self.tmp, raw_dir=self.raw)
        r = CliRunner().invoke(cli, ["receipts", "check", "--project", "EXTERNAL_CLINICAL", "--label", "L"])
        self.assertNotEqual(r.exit_code, 0)
        self.assertIn("d4d --manifest PATH", r.output)
        r = CliRunner().invoke(cli, ["--manifest", str(m), "receipts", "check",
                                     "--project", "EXTERNAL_CLINICAL", "--label", "L"])
        self.assertNotIn("not declared by the selected manifest", r.output)
