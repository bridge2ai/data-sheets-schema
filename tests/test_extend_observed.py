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
            # A second run adds nothing, and says so as "nothing to extend"
            # rather than "already carries the reasoning measure": this
            # fixture's observation carries three of the seven estimate keys,
            # and a record missing thinking_blocks or the character counts is
            # not a record that carries the measure. The guard read two keys
            # and would have skipped such a record for good (#1195 M4).
            r = self._run(tmp, path, {"agent-av6-P-rep1": FULL}, transcripts=[t])
            self.assertIn("nothing to extend", r.output)
            self.assertNotIn("already carries the reasoning measure", r.output)

    def test_a_partial_estimate_is_not_the_measure_and_a_complete_one_with_no_thinking_count_is(self):
        """The skip-for-good guard (#1195 M4). A record whose extension added
        every estimate key and found no `thinking_tokens` carries the measure —
        the runtime's own count is absent from many transcripts and its absence
        is a finding, not a gap to retry. A record carrying only some of those
        keys does not, however it got them."""
        from data_sheets_schema.cli import provenance as cli
        complete = {k: 1 for k in cli._ESTIMATE_KEYS}
        partial = {k: 1 for k in cli._ESTIMATE_KEYS[:3]}
        ext = [{"keys_added": sorted(complete), "transcripts": ["agent-x.jsonl"]}]

        def carries(prior, extended):
            return (cli._REASONING_KEYS <= set(prior) or (
                set(cli._ESTIMATE_KEYS) <= set(prior) and "thinking_tokens" not in prior
                and any(isinstance(e, dict) and "thinking_tokens" not in (e.get("keys_added") or [])
                        and "transcripts" in e for e in extended)))

        self.assertTrue(carries(complete, ext))
        self.assertFalse(carries(partial, ext))
        self.assertFalse(carries(partial, []))
        self.assertTrue(carries({k: 1 for k in cli._REASONING_KEYS}, []))

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
        # each sentence names only the keys the observation carries (round 4, S1)
        alone = cli._reasoning_basis({"turns_with_thinking_tokens"})
        self.assertIn("turns_with_thinking_tokens is the runtime's own count", alone)
        self.assertNotIn("thinking_tokens and", alone)
        only_tt = cli._reasoning_basis({"thinking_tokens"})
        self.assertNotIn("turns_with_thinking_tokens is fewer", only_tt)
        self.assertIn("how much of the run it covers is not stated", only_tt)
        # the estimate's qualification is its own sentence, so "never to be averaged" is about the measure (S5)
        est = cli._reasoning_basis({"output_tokens", "reasoning_tokens_estimate"})
        self.assertIn("never to be averaged with it.", est.split("reasoning_tokens_estimate is output tokens")[0])
        # the after-the-run clause names the keys an extension added, not every key (S2)
        both = cli._reasoning_basis({"output_tokens", "thinking_tokens", "turns_with_thinking_tokens"},
                                    extended={"thinking_tokens", "turns_with_thinking_tokens"})
        self.assertIn("Of these, thinking_tokens, turns_with_thinking_tokens were added after the run", both)
        self.assertNotIn("output_tokens were added", both)
        # a curator's sentence that opens like one of ours survives a recomputation (S3)
        log = {"run_observed": dict(FULL), "run_observed_basis": cli._RUN_OBSERVED_BASIS
               + " No thinking_tokens were requested by the curator, who checked by hand."}
        out = cli._basis_with(log, set(FULL) & cli._REASONING_KEYS)
        self.assertIn("requested by the curator", out)
        # a round-3 basis (every estimate key named, the clause inside the sentence) too (round 6, S2)
        r3 = (cli._RUN_OBSERVED_BASIS + " " + ", ".join(cli._ESTIMATE_KEYS[:-1]) + " and " + cli._ESTIMATE_KEYS[-1]
              + " (output tokens minus a 4-chars-per-token estimate of the text and tool-call payloads — a "
                "subtraction, an upper bound, not a measurement) are the transcript's reasoning measure "
                "(#1000/#1011), added after the run under run_observed_extended; comparable in kind with the "
                "API path's reasoning log, never to be averaged with it."
              + " No thinking_tokens: no line of the transcript carries usage.output_tokens_details, so "
                "the runtime's own count is not measured for this run.")
        out3 = cli._basis_with({"run_observed": dict(FULL), "run_observed_basis": r3}, set(FULL) & cli._REASONING_KEYS)
        self.assertEqual(out3.count("reasoning measure"), 1)
        self.assertEqual(out3.count("No thinking_tokens"), 1)
        self.assertEqual(cli._basis_with({"run_observed": dict(FULL), "run_observed_basis": out3},
                                         set(FULL) & cli._REASONING_KEYS), out3)
        # a round-4 basis (the estimate sentence with the aside inside it) is stripped, not doubled (round 5, S2)
        old_shape = {"run_observed": dict(FULL),
                     "run_observed_basis": cli._RUN_OBSERVED_BASIS + cli._superseded_reasoning_basis(set(FULL))}
        out = cli._basis_with(old_shape, set(FULL) & cli._REASONING_KEYS)
        self.assertEqual(out.count("Of the transcript's reasoning measure"), 1)
        self.assertEqual(out.count("No thinking_tokens"), 1)
        # an extension naming a key the observation no longer carries emits no clause (round 5, S3)
        gone = cli._reasoning_basis({"output_tokens"}, extended={"thinking_tokens"})
        self.assertNotIn("Of these", gone); self.assertNotIn("  ", gone)
        log = {"run_observed": {"output_tokens": 1}, "run_observed_extended": [{"keys_added": ["thinking_tokens"]}],
               "run_observed_basis": cli._RUN_OBSERVED_BASIS}
        once = cli._basis_with(log, {"output_tokens"}); twice = cli._basis_with({**log, "run_observed_basis": once}, {"output_tokens"})
        self.assertEqual(once, twice)
        # a curator sentence that follows one of ours, and starts lower-case, survives (round 5, S4)
        base = cli._basis_with({"run_observed": dict(FULL), "run_observed_basis": cli._RUN_OBSERVED_BASIS},
                               set(FULL) & cli._REASONING_KEYS)
        curated = {"run_observed": dict(FULL), "run_observed_basis": base + " see the launch log for the second transcript."}
        out = cli._basis_with(curated, set(FULL) & cli._REASONING_KEYS)
        self.assertIn("see the launch log for the second transcript.", out)
        self.assertEqual(out.count("Of the transcript's reasoning measure"), 1)
        # the sentence a lower-case curator sentence follows here is the
        # negative, and it is the one that doubled before (round 6, S1)
        self.assertEqual(out.count("No thinking_tokens"), 1)
        self.assertEqual(cli._basis_with({**curated, "run_observed_basis": out}, set(FULL) & cli._REASONING_KEYS), out)
        # a basis with no terminal full stop is not glued to the appended sentence (S3)
        log = {"run_observed": dict(FULL), "run_observed_basis": "prior basis with no full stop"}
        once = cli._basis_with(log, set(FULL) & cli._REASONING_KEYS)
        twice = cli._basis_with({**log, "run_observed_basis": once}, set(FULL) & cli._REASONING_KEYS)
        self.assertEqual(once, twice)
        self.assertEqual(once.count("Of the transcript's reasoning measure"), 1)

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


#: Verbatim from the branch's own history, not regenerated: the paragraph
#: round 2 (`da720634`) appended, and the estimate sentence round 3
#: (`d1b24ea5`) appended. A fixture the implementation produces cannot show
#: that the implementation has forgotten a form (#1195 M1, S9).
ROUND_2_BASIS = (
    " assistant_turns, output_tokens, thinking_blocks, thinking_text_chars, "
    "visible_text_chars, tool_input_chars and reasoning_tokens_estimate "
    "(output tokens minus a 4-chars-per-token estimate of the text and "
    "tool-call payloads — a subtraction, an upper bound, not a measurement) "
    "are the transcript's reasoning measure (#1000/#1011), added after the "
    "run under run_observed_extended; thinking_tokens and "
    "turns_with_thinking_tokens are the runtime's own count on the turns "
    "whose transcript line carries usage.output_tokens_details, and where "
    "turns_with_thinking_tokens is fewer than assistant_turns the count is "
    "partial (a resumed run whose earlier transcript predates the detail). "
    "Comparable in kind with the API path's reasoning log, never to be "
    "averaged with it.")
ROUND_3_BASIS = (
    " assistant_turns, output_tokens, thinking_blocks, thinking_text_chars, visible_text_chars, "
    "tool_input_chars and reasoning_tokens_estimate (output tokens minus a 4-chars-per-token "
    "estimate of the text and tool-call payloads — a subtraction, an upper bound, not a "
    "measurement) are the transcript's reasoning measure (#1000/#1011), comparable in kind with "
    "the API path's reasoning log, never to be averaged with it."
    " No thinking_tokens: no line of the transcript carries usage.output_tokens_details, "
    "so the runtime's own count is not measured for this run.")


class CodexRound(unittest.TestCase):
    """The Codex CLI review of PR #1191 (#1195)."""

    def test_a_basis_written_by_an_earlier_round_is_stripped_not_doubled(self):
        """M1. Both fixtures are the historical text, so a form the strip has
        forgotten fails here rather than being generated into the answer."""
        for name, prior in (("round 2", ROUND_2_BASIS), ("round 3", ROUND_3_BASIS)):
            with self.subTest(name):
                log = {"run_observed": dict(FULL), "run_observed_basis": cli._RUN_OBSERVED_BASIS + prior}
                out = cli._basis_with(log, set(FULL) & cli._REASONING_KEYS)
                self.assertEqual(out.count("reasoning measure"), 1, out)
                self.assertEqual(out.count("No thinking_tokens"), 1, out)
                self.assertEqual(cli._basis_with({**log, "run_observed_basis": out},
                                                 set(FULL) & cli._REASONING_KEYS), out)

    def test_the_no_op_extension_clause_an_earlier_round_wrote_is_stripped(self):
        """M1. Round 5 emitted the clause with an empty name list when the
        extension named no key the observation still carried; the head cannot
        produce it, so only a literal can remove it."""
        empty = " Of these,  was added after the run, under run_observed_extended, which names the source."
        log = {"run_observed": {"output_tokens": 1},
               "run_observed_basis": cli._RUN_OBSERVED_BASIS + empty}
        out = cli._basis_with(log, {"output_tokens"})
        self.assertNotIn("Of these,  was", out)

    def test_a_sentence_ending_in_other_punctuation_is_a_sentence(self):
        """M3. `_basis_with` has always treated `!` and `?` as terminal while
        the split looked only for a full stop, so a second recomputation
        doubled the paragraph."""
        for ending in ("curator checked!", "did the curator check?",
                       'the curator said "checked."', "the curator checked [twice.]"):
            with self.subTest(ending):
                log = {"run_observed": dict(FULL), "run_observed_basis": ending}
                once = cli._basis_with(log, set(FULL) & cli._REASONING_KEYS)
                twice = cli._basis_with({**log, "run_observed_basis": once}, set(FULL) & cli._REASONING_KEYS)
                self.assertEqual(once, twice)
                self.assertEqual(once.count("Of the transcript's reasoning measure"), 1)
                self.assertIn(ending, once)

    def test_what_is_removed_is_the_text_the_last_extension_recorded(self):
        """M2. Authorship is not readable from a sentence. Once an extension
        records what it appended, that text is what the next one removes — so
        a curator sentence identical to one of ours survives beside it."""
        base = {"run_observed": dict(FULL), "run_observed_basis": cli._RUN_OBSERVED_BASIS}
        text, appended, _t, _e = cli._basis_parts(base, set(FULL) & cli._REASONING_KEYS)
        twin = " No thinking_tokens: the observation carries none, so the runtime's own count is not measured for this run."
        log = {"run_observed": dict(FULL),
               "run_observed_basis": cli._RUN_OBSERVED_BASIS + twin + appended,
               "run_observed_extended": [{"keys_added": sorted(set(FULL) & cli._REASONING_KEYS),
                                          "basis_added": appended}]}
        out, _a, _t, edited = cli._basis_parts(log, set(FULL) & cli._REASONING_KEYS)
        self.assertFalse(edited)
        self.assertIn(twin.strip(), out)                       # the curator's copy is left alone
        self.assertEqual(out.count("Of the transcript's reasoning measure"), 1)

    def test_an_edited_paragraph_is_reported_rather_than_guessed_at(self):
        """M2, the other direction: a word changed inside the recorded text
        means it can no longer be located, and removing an approximation of it
        would be editing the curator. The doubling is stated instead."""
        base = {"run_observed": dict(FULL), "run_observed_basis": cli._RUN_OBSERVED_BASIS}
        _text, appended, _t, _e = cli._basis_parts(base, set(FULL) & cli._REASONING_KEYS)
        edited_text = appended.replace("upper bound", "curator-reviewed upper bound")
        log = {"run_observed": dict(FULL),
               "run_observed_basis": cli._RUN_OBSERVED_BASIS + edited_text,
               "run_observed_extended": [{"keys_added": sorted(set(FULL) & cli._REASONING_KEYS),
                                          "basis_added": appended}]}
        out, _a, _t, edited = cli._basis_parts(log, set(FULL) & cli._REASONING_KEYS)
        self.assertTrue(edited)
        self.assertIn("curator-reviewed upper bound", out)

    def test_a_record_with_no_cut_does_not_claim_one(self):
        """M5. The observer correctly gets `until=None`; the extension said
        "under the record's own cut" whatever the record carried."""
        with tempfile.TemporaryDirectory() as tmp:
            path = _record(tmp)
            data = yaml.safe_load(path.read_text().split("\n", 1)[1])
            data["phase_log"].pop("run_observed_until")
            path.write_text("# header\n" + yaml.safe_dump(data))
            (t,) = _transcripts(tmp, ["agent-av6-P-rep1"])
            r = Extension._run(self, tmp, path, {"agent-av6-P-rep1": FULL}, transcripts=[t])
            self.assertEqual(r.exit_code, 0, r.output)
            log = yaml.safe_load(path.read_text().split("\n", 1)[1])["phase_log"]
            (ext,) = log["run_observed_extended"]
            self.assertIn("the record records no cut", ext["instrument"])
            self.assertNotIn("under the record's own", ext["instrument"])
            self.assertNotIn("Cut at run_observed_until", log["run_observed_basis"])

    def test_the_transcript_is_recorded_by_its_bytes(self):
        """M6. Two files with one basename under the two config roots are
        different inputs and were recorded identically."""
        with tempfile.TemporaryDirectory() as tmp:
            path = _record(tmp); (t,) = _transcripts(tmp, ["agent-av6-P-rep1"])
            r = Extension._run(self, tmp, path, {"agent-av6-P-rep1": FULL}, transcripts=[t])
            self.assertEqual(r.exit_code, 0, r.output)
            (ext,) = yaml.safe_load(path.read_text().split("\n", 1)[1])["phase_log"]["run_observed_extended"]
            self.assertEqual(ext["transcript_sha256"],
                             {t.name: hashlib.sha256(t.read_bytes()).hexdigest()})

    def test_three_transcripts_under_one_name_offer_the_resumed_pair(self):
        """M7. Discovery tried every single file and the whole group, so the
        pair that is the resumed run was never offered."""
        import click.testing
        with tempfile.TemporaryDirectory() as tmp:
            path = _record(tmp)
            root = Path(tmp) / "cfg" / "s1" / "subagents"; root.mkdir(parents=True, exist_ok=True)
            files = []
            for i, h in enumerate(("a" * 16, "b" * 16, "c" * 16)):
                f = root / f"agent-x-rep1-{h}.jsonl"; f.write_text(f"{i}\n")
                import os
                os.utime(f, (1_700_000_000 + i, 1_700_000_000 + i))
                files.append(f)
            pair = {files[0], files[1]}
            tried = []

            def observe(ts, bundle, until, receipt, manifest):
                tried.append(frozenset(ts))
                return dict(FULL) if set(ts) == pair else {k: 0 for k in FULL}

            with mock.patch.object(cli, "_observe", observe), \
                 mock.patch.object(cli, "_require_repo_root_cwd", lambda *a, **k: None), \
                 mock.patch.object(cli, "_transcript_candidates", lambda p, l: list(files)), \
                 mock.patch("data_sheets_schema.provenance.record_path_for",
                            lambda project, method, label, concat_dir=None: path), \
                 mock.patch("data_sheets_schema.receipts.receipt_path", lambda core, p: Path(tmp) / "none.yaml"):
                r = click.testing.CliRunner().invoke(
                    cli.provenance, ["extend-observed", "--label", "L_rep1", "--project", "P",
                                     "--method", "claudecode_agent", "--execute"])
            self.assertIn(frozenset(pair), tried, "the resumed pair was never tried")
            self.assertEqual(r.exit_code, 0, r.output)
            (ext,) = yaml.safe_load(path.read_text().split("\n", 1)[1])["phase_log"]["run_observed_extended"]
            self.assertEqual(sorted(ext["transcripts"]), sorted(f.name for f in pair))


class Round8(unittest.TestCase):
    """The reviewer round after the Codex one."""

    def test_a_curator_sentence_that_ends_inside_a_quote_or_bracket_is_left_alone(self):
        """M1: `_split_sentences` learned that a closing quote or bracket may
        follow terminal punctuation; the "does this need a full stop" test did
        not, so a basis ending `."` or `.]` was given a stray one outside its
        own quotation marks on the first extension. Idempotent afterwards, but
        the curator's text is wrong from then on — assert the text exactly,
        not that it is a substring, which the corrupted string also satisfies."""
        keys = set(FULL) & cli._REASONING_KEYS
        for ending in ('the curator said "checked."', "the curator checked [twice.]",
                       "curator checked!", "did the curator check?"):
            with self.subTest(ending):
                log = {"run_observed": dict(FULL), "run_observed_basis": ending}
                text, appended, terminated, _edited = cli._basis_parts(log, keys)
                self.assertFalse(terminated, ending)
                self.assertEqual(text, ending + appended)

    def test_a_basis_with_no_terminal_punctuation_still_gets_one_and_says_so(self):
        keys = set(FULL) & cli._REASONING_KEYS
        text, appended, terminated, _e = cli._basis_parts(
            {"run_observed": dict(FULL), "run_observed_basis": "prior basis with no full stop"}, keys)
        self.assertTrue(terminated)
        self.assertEqual(text, "prior basis with no full stop." + appended)

    def test_a_whitespace_only_recorded_addition_does_not_wipe_the_account(self):
        """M2: it passed the truthy filter, `prior.rstrip()` was then `""`,
        `b.endswith("")` is True for every string, and `b[: -len("")]` is
        `b[:0]` — the whole account, curator prose included. No caller can
        produce one; the mechanism exists so that nothing is destroyed by
        guesswork, and this was the one path that could destroy everything."""
        keys = set(FULL) & cli._REASONING_KEYS
        for value in ("   ", "\t", "\n", ""):
            with self.subTest(repr(value)):
                log = {"run_observed": dict(FULL),
                       "run_observed_basis": "a curator wrote this account by hand.",
                       "run_observed_extended": [{"keys_added": sorted(keys), "basis_added": value}]}
                text, _a, _t, edited = cli._basis_parts(log, keys)
                self.assertTrue(text.startswith("a curator wrote this account by hand."), repr(value))
                self.assertFalse(edited)
        self.assertEqual(cli._recorded_additions(
            {"run_observed_extended": [{"basis_added": "  "}, {"basis_added": "real text."}]}),
            ["real text."])
