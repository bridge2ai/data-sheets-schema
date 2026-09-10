"""`d4d provenance extend-observed` (#1010): a prior `run_observed` is
extended with the reasoning keys only when exactly one candidate transcript
reproduces every key the record already carries. The observer is stubbed
per transcript; discovery, matching, the refusals and the write are what is
under test."""
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml

from data_sheets_schema.cli import provenance as cli

PRIOR = {"total_tokens": 100, "tool_uses": 5, "duration_ms": 1000, "bundle_lines_read": 10, "bundle_lines_total": 12}
FULL = {**PRIOR, "output_tokens": 40, "reasoning_tokens_estimate": 7, "assistant_turns": 3}


def _record(tmp, prior=PRIOR, api=False):
    core = Path(tmp) / "claudecode_agent_core" / "L_rep1"; core.mkdir(parents=True, exist_ok=True)
    bundle = Path(tmp) / "P_preprocessed.txt"; bundle.write_text("FILE: a\nline\n" * 6)
    md5 = hashlib.md5(bundle.read_bytes()).hexdigest()
    rec = {"inputs": {"bundle_path": str(bundle), "bundle_md5": md5},
           "phase_log": {"run_observed": dict(prior), "run_observed_until": "2026-08-28T10:00:00+00:00"}}
    if api:
        rec["api_usage"] = [{"phase": "full"}]
    path = core / "P_provenance.yaml"; path.write_text("# header\n" + yaml.safe_dump(rec))
    return path


def _transcripts(tmp, names):
    root = Path(tmp) / "cfg" / "s1" / "subagents"; root.mkdir(parents=True, exist_ok=True)
    out = []
    for n in names:
        f = root / f"{n}-{hashlib.sha256(n.encode()).hexdigest()[:16]}.jsonl"; f.write_text(n + "\n"); out.append(f)
    return out


class Discovery(unittest.TestCase):
    def test_candidates_are_named_after_the_project_and_replicate_and_deduplicated(self):
        with tempfile.TemporaryDirectory() as tmp:
            names = ["agent-av6-AI_READI-rep1", "agent-av6-AI_READI-rep2", "agent-afanout-aireadi-rep1",
                     "agent-acanary-aireadi-agentic", "agent-av6-CHORUS-rep1", "agent-areview-712"]
            files = _transcripts(tmp, names)
            twin_root = Path(tmp) / "cfg2" / "s1" / "subagents"; twin_root.mkdir(parents=True)
            (twin_root / files[0].name).write_bytes(files[0].read_bytes())            # the identical copy (#688)
            roots = [Path(tmp) / "cfg", Path(tmp) / "cfg2"]
            got = [f.name.rsplit("-", 1)[0] for f in cli._transcript_candidates("AI_READI", "2026-08-28_x_rep1", roots)]
            self.assertEqual(got, ["agent-acanary-aireadi-agentic", "agent-afanout-aireadi-rep1", "agent-av6-AI_READI-rep1"])
            got2 = [f.name.rsplit("-", 1)[0] for f in cli._transcript_candidates("AI_READI", "2026-08-28_x_rep2", roots)]
            self.assertEqual(got2, ["agent-av6-AI_READI-rep2"])                         # the canary is rep1's only


class Extension(unittest.TestCase):
    def _run(self, tmp, path, observations, execute=True, transcripts=()):
        """`observations`: transcript basename prefix → what the observer returns for it."""
        import click.testing
        def observe(ts, bundle, until, receipt, manifest):
            key = "+".join(t.name.rsplit("-", 1)[0] for t in ts)
            if key not in observations:
                return {k: 0 for k in FULL}
            self.assertEqual(hashlib.md5(bundle.read_bytes()).hexdigest(),
                             yaml.safe_load(path.read_text().split("\n", 1)[1])["inputs"]["bundle_md5"])
            return observations[key]
        args = ["extend-observed", "--label", "L_rep1", "--project", "P", "--method", "claudecode_agent"]
        for t in transcripts:
            args += ["--transcript", str(t)]
        if execute:
            args.append("--execute")
        with mock.patch.object(cli, "_observe", observe), \
             mock.patch.object(cli, "_require_repo_root_cwd", lambda *a, **k: None), \
             mock.patch("data_sheets_schema.provenance.record_path_for",
                        lambda project, method, label, concat_dir=None: path), \
             mock.patch("data_sheets_schema.receipts.receipt_path", lambda core, p: Path(tmp) / "no_receipt.yaml"):
            return click.testing.CliRunner().invoke(cli.provenance, args)

    def test_one_reproducing_transcript_extends_and_the_extension_is_recorded(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _record(tmp); (t,) = _transcripts(tmp, ["agent-av6-P-rep1"])
            r = self._run(tmp, path, {"agent-av6-P-rep1": FULL}, transcripts=[t])
            self.assertEqual(r.exit_code, 0, r.output); self.assertIn("wrote", r.output)
            log = yaml.safe_load(path.read_text().split("\n", 1)[1])["phase_log"]
            self.assertEqual(log["run_observed"], FULL)
            ext = log["run_observed_extended"]
            self.assertEqual(ext["keys_added"], ["assistant_turns", "output_tokens", "reasoning_tokens_estimate"])
            self.assertEqual(ext["transcripts"], [t.name]); self.assertEqual(ext["bundle_basis"]["source"], "bundle on disk")
            self.assertEqual(ext["recorded_by"], "d4d provenance extend-observed (#1010)")
            self.assertEqual(log["run_observed_until"], "2026-08-28T10:00:00+00:00")     # untouched
            r = self._run(tmp, path, {"agent-av6-P-rep1": FULL}, transcripts=[t])
            self.assertIn("already carries the reasoning measure", r.output)

    def test_a_transcript_that_does_not_reproduce_a_prior_key_writes_nothing_and_names_the_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _record(tmp); (t,) = _transcripts(tmp, ["agent-av6-P-rep1"])
            before = path.read_text()
            r = self._run(tmp, path, {"agent-av6-P-rep1": {**FULL, "tool_uses": 6}}, transcripts=[t])
            self.assertEqual(r.exit_code, 0, r.output)
            self.assertIn("0 of 1 candidate", r.output); self.assertIn("tool_uses 5→6", r.output); self.assertIn("nothing written", r.output)
            self.assertEqual(path.read_text(), before)

    def test_two_reproducing_transcripts_are_ambiguous_and_write_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _record(tmp); ts = _transcripts(tmp, ["agent-av6-P-rep1", "agent-afanout-p-rep1"])
            before = path.read_text()
            r = self._run(tmp, path, {"agent-av6-P-rep1": FULL, "agent-afanout-p-rep1": FULL}, transcripts=ts)
            self.assertIn("2 of 3 candidate", r.output); self.assertEqual(path.read_text(), before)   # the pair is tried too

    def test_a_resumed_run_is_the_set_of_its_transcripts(self):
        """#688: a killed-and-resumed run has two transcripts under one name
        and its observation summed them; each alone differs, the set
        reproduces, and both names are recorded."""
        with tempfile.TemporaryDirectory() as tmp:
            path = _record(tmp)
            root = Path(tmp) / "cfg" / "s1" / "subagents"; root.mkdir(parents=True)
            a = root / "agent-afanout-p-rep1-aaaaaaaaaaaaaaaa.jsonl"; a.write_text("first\n")
            b = root / "agent-afanout-p-rep1-bbbbbbbbbbbbbbbb.jsonl"; b.write_text("second\n")
            import os, time
            os.utime(a, (time.time() - 100, time.time() - 100))
            with mock.patch.object(cli, "_transcript_candidates", lambda p, l, roots=None: [b, a]):
                r = self._run(tmp, path, {"agent-afanout-p-rep1+agent-afanout-p-rep1": FULL})
            self.assertEqual(r.exit_code, 0, r.output); self.assertIn("wrote", r.output)
            ext = yaml.safe_load(path.read_text().split("\n", 1)[1])["phase_log"]["run_observed_extended"]
            self.assertEqual(ext["transcripts"], [a.name, b.name])                     # oldest first

    def test_report_mode_writes_nothing_and_an_api_record_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _record(tmp); (t,) = _transcripts(tmp, ["agent-av6-P-rep1"])
            before = path.read_text()
            r = self._run(tmp, path, {"agent-av6-P-rep1": FULL}, execute=False, transcripts=[t])
            self.assertIn("report only", r.output); self.assertEqual(path.read_text(), before)
            path = _record(tmp, api=True)
            r = self._run(tmp, path, {"agent-av6-P-rep1": FULL}, transcripts=[t])
            self.assertIn("API-path record", r.output)

    def test_the_extension_helper_is_the_one_annotate_observed_uses(self):
        """One function, two commands: `annotate-observed --extend` and this
        driver must refuse and record identically."""
        import click
        log = {"run_observed": dict(PRIOR)}
        with self.assertRaises(click.ClickException):
            cli._extend_run_observed(log, {**PRIOR, "tool_uses": 6}, recorded_by="x")
        with self.assertRaises(click.ClickException):
            cli._extend_run_observed(log, dict(PRIOR), recorded_by="x")                 # nothing to add
        self.assertEqual(cli._extend_run_observed(log, FULL, recorded_by="x"), ["assistant_turns", "output_tokens", "reasoning_tokens_estimate"])
        self.assertEqual(log["run_observed"], FULL); self.assertEqual(log["run_observed_extended"]["recorded_by"], "x")


if __name__ == "__main__":
    unittest.main()
