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


class Siblings(unittest.TestCase):
    def test_a_sibling_projects_transcript_is_never_offered_and_an_abbreviation_is_known(self):
        """#1191 round 1, S3: VOICE_PEDIATRIC is `voicepeds` on disk and must
        not be offered as VOICE's run."""
        with tempfile.TemporaryDirectory() as tmp:
            _transcripts(tmp, ["agent-av6-VOICE-rep3", "agent-avoicepeds-rep3", "agent-avoicepediatric-rep3",
                               "agent-av6-VOICE-rep10"])
            roots = [Path(tmp) / "cfg"]
            got = lambda p, l: sorted(f.name.rsplit("-", 1)[0] for f in cli._transcript_candidates(p, l, roots))
            self.assertEqual(got("VOICE", "x_rep3"), ["agent-av6-VOICE-rep3"])
            self.assertEqual(got("VOICE_PEDIATRIC", "x_rep3"), ["agent-avoicepediatric-rep3", "agent-avoicepeds-rep3"])
            self.assertEqual(got("VOICE", "x_rep1"), [])                                       # rep10 is not rep1

    def test_the_driver_refuses_transcripts_without_a_project_and_more_than_four(self):
        """#1191 round 1, S6; round 2, S7."""
        import click.testing
        with tempfile.TemporaryDirectory() as tmp:
            ts = _transcripts(tmp, [f"agent-x-rep1-{i}" for i in range(5)])
            with mock.patch.object(cli, "_require_repo_root_cwd", lambda *a, **k: None):
                r = click.testing.CliRunner().invoke(cli.provenance, ["extend-observed", "--label", "L_rep1", "--method",
                                                                       "claudecode_agent", "--transcript", str(ts[0])])
                self.assertNotEqual(r.exit_code, 0); self.assertIn("pass --project", r.output)
                args = ["extend-observed", "--label", "L_rep1", "--project", "P", "--method", "claudecode_agent"]
                for t in ts:
                    args += ["--transcript", str(t)]
                r = click.testing.CliRunner().invoke(cli.provenance, args)
                self.assertNotEqual(r.exit_code, 0); self.assertIn("at most four", r.output)

    def test_one_projects_refusal_does_not_stop_the_others(self):
        """#1191 round 1, S5."""
        import click.testing
        calls = []
        def one(proj, method, label, given, execute, observer):
            calls.append(proj)
            if proj == "AI_READI":
                raise click.ClickException("boom")
        with mock.patch.object(cli, "_extend_one", one), \
             mock.patch.object(cli, "_observer_sha256", lambda: "0" * 64), \
             mock.patch.object(cli, "_require_repo_root_cwd", lambda *a, **k: None), \
             mock.patch("data_sheets_schema.provenance.record_path_for",
                        lambda project, method, label, concat_dir=None: Path(__file__)):
            r = click.testing.CliRunner().invoke(cli.provenance, ["extend-observed", "--label", "L_rep1", "--method", "claudecode_agent"])
        self.assertEqual(r.exit_code, 0, r.output); self.assertIn("AI_READI L_rep1: boom", r.output)
        from data_sheets_schema.constants import PROJECTS
        self.assertEqual(calls, list(PROJECTS))                                            # every project visited


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
            (ext,) = log["run_observed_extended"]                                          # a list: a second extension keeps the first (S4)
            self.assertEqual(ext["keys_added"], ["assistant_turns", "output_tokens", "reasoning_tokens_estimate"])
            self.assertEqual(ext["transcripts"], [t.name]); self.assertEqual(ext["bundle_basis"]["source"], "bundle on disk")
            self.assertEqual(ext["recorded_by"], "d4d provenance extend-observed (#1010)")
            self.assertEqual(len(ext["observer_sha256"]), 64); self.assertIn("agentic_observed.py", ext["instrument"])
            self.assertIn("upper bound", log["run_observed_basis"])                           # the basis describes the new keys (M3)
            self.assertIn("No thinking_tokens", log["run_observed_basis"])                    # ... and only them (round 2, S1)
            self.assertNotIn("turns_with_thinking_tokens are the runtime", log["run_observed_basis"])
            self.assertIn("added after the run, under run_observed_extended", log["run_observed_basis"])   # round 3, S2
            self.assertNotIn("thinking_blocks", log["run_observed_basis"])                    # a key not carried is not described (round 3, S3)
            self.assertIn("Cut at run_observed_until", log["run_observed_basis"])               # the record's cut is said (S5)
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
            (ext,) = yaml.safe_load(path.read_text().split("\n", 1)[1])["phase_log"]["run_observed_extended"]
            self.assertEqual(ext["transcripts"], [a.name, b.name])                     # oldest first

    def test_report_mode_writes_nothing_and_an_api_record_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _record(tmp); (t,) = _transcripts(tmp, ["agent-av6-P-rep1"])
            before = path.read_text()
            r = self._run(tmp, path, {"agent-av6-P-rep1": {**FULL, "receipt_chunks_unopened": 1}}, execute=False, transcripts=[t])
            self.assertIn("report only", r.output); self.assertEqual(path.read_text(), before)
            self.assertIn("adds ['assistant_turns', 'output_tokens', 'reasoning_tokens_estimate']", r.output)   # the set --execute writes (round 2, S4)
            self.assertNotIn("receipt_chunks", r.output)
            path = _record(tmp, api=True)
            r = self._run(tmp, path, {"agent-av6-P-rep1": FULL}, transcripts=[t])
            self.assertIn("API-path record", r.output)

    def test_the_extension_helper_is_the_one_annotate_observed_uses(self):
        """One function, two commands: `annotate-observed --extend` and this
        driver must refuse and record identically."""
        import click
        log = {"run_observed": dict(PRIOR), "run_observed_basis": "prior basis."}
        with self.assertRaises(click.ClickException):
            cli._extend_run_observed(log, {**PRIOR, "tool_uses": 6}, recorded_by="x", instrument="i")
        with self.assertRaises(click.ClickException):
            cli._extend_run_observed(log, dict(PRIOR), recorded_by="x", instrument="i")     # nothing to add
        with self.assertRaises(click.ClickException) as cm:                                  # another instrument's key is not added (S2)
            cli._extend_run_observed(log, {**PRIOR, "receipt_chunks_unopened": 1}, recorded_by="x", instrument="i")
        self.assertIn("receipt_chunks_unopened", str(cm.exception))
        self.assertEqual(cli._extend_run_observed(log, {**FULL, "receipt_chunks_unopened": 1}, recorded_by="x", instrument="i"),
                         ["assistant_turns", "output_tokens", "reasoning_tokens_estimate"])
        self.assertEqual(log["run_observed"], FULL)                                           # the receipt key stays out
        self.assertEqual([e["recorded_by"] for e in log["run_observed_extended"]], ["x"])
        self.assertTrue(log["run_observed_basis"].startswith("prior basis."))
        self.assertEqual(log["run_observed_basis"].count("reasoning measure"), 1)
        cli._extend_run_observed(log, {**FULL, "thinking_tokens": 3}, recorded_by="y", instrument="j")
        self.assertEqual([e["recorded_by"] for e in log["run_observed_extended"]], ["x", "y"])   # the first trace kept (S4)
        self.assertEqual(log["run_observed_basis"].count("reasoning measure"), 1)             # appended once (S3)
        fresh = {"run_observed": dict(PRIOR), "run_observed_until": "2026-08-28T10:00:00+00:00"}   # no basis at all (S5)
        cli._extend_run_observed(fresh, FULL, recorded_by="x", instrument="i")
        self.assertTrue(fresh["run_observed_basis"].startswith("aggregate totals for the whole run"))
        self.assertIn("Cut at run_observed_until", fresh["run_observed_basis"])
        annotated = {"run_observed": dict(PRIOR), "run_observed_basis": cli._RUN_OBSERVED_BASIS + cli._reasoning_basis(set(FULL))}
        cli._extend_run_observed(annotated, FULL, recorded_by="x", instrument="i")
        self.assertEqual(annotated["run_observed_basis"].count("reasoning measure"), 1)      # today's annotate paragraph is not doubled (S3)
        # a later extension that adds thinking_tokens replaces the "No thinking_tokens" statement (round 3, M1)
        self.assertIn("No thinking_tokens", annotated["run_observed_basis"])
        cli._extend_run_observed(annotated, {**FULL, "thinking_tokens": 11, "turns_with_thinking_tokens": 3}, recorded_by="y", instrument="j")
        self.assertNotIn("No thinking_tokens", annotated["run_observed_basis"])
        self.assertIn("thinking_tokens and turns_with_thinking_tokens are the runtime", annotated["run_observed_basis"])
        self.assertEqual(annotated["run_observed_basis"].count("reasoning measure"), 1)
        self.assertEqual(annotated["run_observed_basis"].count("added after the run"), 1)
        self.assertTrue(annotated["run_observed_basis"].startswith("aggregate totals"))
        # the sentences name only the keys present (round 3, S3), and the negative is about the observation (S1)
        self.assertNotIn("thinking_blocks", cli._reasoning_basis({"output_tokens"}))
        self.assertIn("the observation carries none", cli._reasoning_basis({"output_tokens"}))
        self.assertNotIn("transcript carries", cli._reasoning_basis({"output_tokens"}))
        self.assertIn("counts the turns", cli._reasoning_basis({"turns_with_thinking_tokens"}))

    def test_annotate_observed_extend_keeps_the_cut_and_names_its_own_route(self):
        """#1191 review, M1/M2: `--extend` deleted `run_observed_until` and
        wrote the driver's instrument text for numbers typed on the command line."""
        import json
        import click.testing
        with tempfile.TemporaryDirectory() as tmp:
            path = _record(tmp)
            with mock.patch("data_sheets_schema.provenance.record_path_for",
                            lambda project, method, label, concat_dir=None: path), \
                 mock.patch.object(cli, "_require_repo_root_cwd", lambda *a, **k: None):
                r = click.testing.CliRunner().invoke(cli.provenance, ["annotate-observed", "--project", "P", "--method",
                                                                       "claudecode_agent", "--label", "L_rep1", "--extend",
                                                                       "--run", json.dumps(FULL)])
                self.assertEqual(r.exit_code, 0, r.output)
                log = yaml.safe_load(path.read_text().split("\n", 1)[1])["phase_log"]
                self.assertEqual(log["run_observed_until"], "2026-08-28T10:00:00+00:00")     # kept (M1)
                self.assertEqual(log["run_observed"], FULL)
                (ext,) = log["run_observed_extended"]
                self.assertIn("command line", ext["instrument"]); self.assertNotIn("transcripts", ext)  # its own route (M2)
                r = click.testing.CliRunner().invoke(cli.provenance, ["annotate-observed", "--project", "P", "--method",
                                                                       "claudecode_agent", "--label", "L_rep1", "--extend",
                                                                       "--run", json.dumps({**FULL, "thinking_tokens": 1}),
                                                                       "--until", "2026-08-28T11:00:00+00:00"])
                self.assertNotEqual(r.exit_code, 0); self.assertIn("not the record's own cut", r.output)
                # the same --run again: nothing changes, the cut stays (round 2, M1)
                before = path.read_text()
                r = click.testing.CliRunner().invoke(cli.provenance, ["annotate-observed", "--project", "P", "--method",
                                                                       "claudecode_agent", "--label", "L_rep1", "--extend",
                                                                       "--run", json.dumps(FULL)])
                self.assertEqual(r.exit_code, 0, r.output); self.assertIn("nothing changed", r.output)
                self.assertEqual(path.read_text(), before)
                # a plain annotate (no --extend) on a record with a cut and no --until keeps the cut too
                fresh = _record(tmp)
                r = click.testing.CliRunner().invoke(cli.provenance, ["annotate-observed", "--project", "P", "--method",
                                                                       "claudecode_agent", "--label", "L_rep1",
                                                                       "--run", json.dumps(PRIOR)])
                self.assertEqual(r.exit_code, 0, r.output)
                log = yaml.safe_load(fresh.read_text().split("\n", 1)[1])["phase_log"]
                self.assertEqual(log["run_observed_until"], "2026-08-28T10:00:00+00:00"); self.assertIn("Cut at", log["run_observed_basis"])
                # --until on the extend path where the record has no cut is refused, not dropped (round 2, S2)
                d = yaml.safe_load(fresh.read_text().split("\n", 1)[1]); del d["phase_log"]["run_observed_until"]
                fresh.write_text("# header\n" + yaml.safe_dump(d))
                r = click.testing.CliRunner().invoke(cli.provenance, ["annotate-observed", "--project", "P", "--method",
                                                                       "claudecode_agent", "--label", "L_rep1", "--extend",
                                                                       "--run", json.dumps(FULL), "--until", "2026-08-28T11:00:00+00:00"])
                self.assertNotEqual(r.exit_code, 0); self.assertIn("not the record's own cut (none)", r.output)

    def test_the_real_observer_on_a_synthetic_transcript_and_a_bundle_from_git(self):
        """#1191 review, S7: the observer is not stubbed — a small JSONL
        transcript through `scripts/agentic_observed.py`, the key filter, the
        `run_observed_until` parse, and the git-blob branch with the bundle
        gone from disk."""
        import click.testing
        import sys
        sys.path.insert(0, str(Path(__file__).parent))
        from test_agentic_observed import _event
        with tempfile.TemporaryDirectory() as tmp:
            path = _record(tmp)
            rec = yaml.safe_load(path.read_text().split("\n", 1)[1])
            bundle = Path(rec["inputs"]["bundle_path"]); raw = bundle.read_bytes(); md5 = rec["inputs"]["bundle_md5"]
            lines = [_event("2026-08-28T09:00:00Z", usage={"input_tokens": 10, "output_tokens": 40},
                            tools=[("Read", {"file_path": str(bundle)})]),
                     _event("2026-08-28T09:01:00Z", usage={"input_tokens": 1, "output_tokens": 1},
                            tools=[("Read", {"file_path": str(bundle), "offset": 3, "limit": 4})]),
                     _event("2026-08-28T12:00:00Z", usage={"output_tokens": 999}, tools=[])]   # after the cut
            root = Path(tmp) / "cfg" / "s1" / "subagents"; root.mkdir(parents=True)
            t = root / "agent-av6-P-rep1-0000000000000000.jsonl"; t.write_text("\n".join(lines) + "\n")
            # the prior keys as the real observer computes them, so the proof is real
            obs = cli._observe([t], bundle, __import__("datetime").datetime.fromisoformat("2026-08-28T10:00:00+00:00"), None, None)
            rec["phase_log"]["run_observed"] = {k: obs[k] for k in ("total_tokens", "tool_uses", "duration_ms",
                                                                   "bundle_lines_read", "bundle_lines_total")}
            self.assertEqual(rec["phase_log"]["run_observed"]["tool_uses"], 2)                   # the cut applied
            path.write_text("# header\n" + yaml.safe_dump(rec))
            bundle.unlink()                                                                     # gone from disk: git supplies it
            entry = {"commit": "c" * 40, "date": "2026-08-28", "md5": md5, "sha256": "s", "matched_on": ["md5"]}
            with mock.patch.object(cli, "_require_repo_root_cwd", lambda *a, **k: None), \
                 mock.patch("data_sheets_schema.provenance.record_path_for",
                            lambda project, method, label, concat_dir=None: path), \
                 mock.patch("data_sheets_schema.provenance.bundle_bytes_for",
                            lambda p, md5=None, sha256=None: (raw, entry) if md5 == entry["md5"] else None), \
                 mock.patch("data_sheets_schema.receipts.receipt_path", lambda core, p: Path(tmp) / "no_receipt.yaml"), \
                 mock.patch.object(cli, "_transcript_candidates", lambda p, l, roots=None: [t]):
                r = click.testing.CliRunner().invoke(cli.provenance, ["extend-observed", "--label", "L_rep1", "--project", "P",
                                                                       "--method", "claudecode_agent", "--execute"])
            self.assertEqual(r.exit_code, 0, r.output); self.assertIn("wrote", r.output)
            log = yaml.safe_load(path.read_text().split("\n", 1)[1])["phase_log"]
            self.assertEqual(log["run_observed"]["output_tokens"], 41)                          # 999 after the cut is not the run
            self.assertEqual(log["run_observed"]["assistant_turns"], 2)
            (ext,) = log["run_observed_extended"]
            self.assertEqual(ext["bundle_basis"]["source"], "git blob"); self.assertEqual(ext["bundle_basis"]["commit"], "c" * 40)
            self.assertFalse(any(isinstance(v, bool) for v in log["run_observed"].values()))


if __name__ == "__main__":
    unittest.main()
