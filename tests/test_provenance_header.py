"""The `#` header states what the request carried, not what the prompt said (#1027).

Every v8 full record's header read `Temperature: 0.0` — copied from the
prompt's example line — while `model.temperature` in the provenance record
is null, because claude-opus-5 rejects the parameter and the runner omits it.
A header asserting a setting the request never carried is a methods-section
error waiting to be transcribed. It is rewritten at write time from the same
settings the record's `model` block is written from.
"""
import unittest

from data_sheets_schema.api_runner import header_value, stamp_provenance_header

HEADER = ("# D4D Datasheet for VOICE Dataset\n"
          "# Model: claude-opus-5\n"
          "# Temperature: 0.0\n"
          "# Arm: BASELINE (input documents only)\n")
BODY = "id: x\ntitle: T\nnotes: '# Temperature: 0.0 is prose here, not a header'\n"


class TestHeaderStatesTheRequest(unittest.TestCase):
    def test_a_rejected_parameter_reads_not_sent(self):
        out = stamp_provenance_header(HEADER + BODY,
                                      {"name": "claude-opus-5", "temperature": 0.0,
                                       "temperature_applies": False})
        self.assertNotIn("# Temperature: 0.0", out.split("id: x")[0])
        self.assertIn("# Temperature: not sent (claude-opus-5 rejects the parameter", out)

    def test_a_sent_temperature_is_stated_as_sent(self):
        out = stamp_provenance_header(HEADER + BODY,
                                      {"name": "m", "temperature": 0.0,
                                       "temperature_applies": True})
        self.assertIn("# Temperature: 0.0\n", out)

    def test_only_the_header_is_touched(self):
        """The same string inside a YAML value is prose; the normalisers are
        written to leave the body alone and so is this."""
        out = stamp_provenance_header(HEADER + BODY,
                                      {"name": "claude-opus-5", "temperature": 0.0,
                                       "temperature_applies": False})
        self.assertIn("notes: '# Temperature: 0.0 is prose here, not a header'", out)
        self.assertEqual(out.split("id: x", 1)[1], (HEADER + BODY).split("id: x", 1)[1])

    def test_other_header_lines_are_byte_identical(self):
        out = stamp_provenance_header(HEADER + BODY,
                                      {"name": "claude-opus-5", "temperature": 0.0,
                                       "temperature_applies": False})
        for line in ("# D4D Datasheet for VOICE Dataset", "# Model: claude-opus-5",
                     "# Arm: BASELINE (input documents only)"):
            self.assertIn(line + "\n", out)

    def test_a_header_without_the_line_is_unchanged(self):
        text = "# Model: claude-opus-5\n" + BODY
        self.assertEqual(stamp_provenance_header(text, {"name": "claude-opus-5",
                                                        "temperature_applies": False}), text)

    def test_model_and_effort_lines_are_stamped_and_never_say_default(self):
        """Two records read `Reasoning effort: default` against a record that
        says nothing (#1027 review, finding 6) — the value #470 forbids."""
        settings = {"name": "claude-opus-5", "temperature": 0.0, "temperature_applies": False}
        out = stamp_provenance_header("# Model: x\n# Reasoning effort: default\nid: y\n", settings)
        self.assertIn("# Model: claude-opus-5\n", out)
        self.assertIn("# Reasoning effort: not set by the request", out)
        self.assertNotIn("default\n", out)
        out = stamp_provenance_header("# Reasoning effort: default\nid: y\n", {**settings, "effort": "high"})
        self.assertIn("# Reasoning effort: high\n", out)

    def test_header_value_refuses_unknown_fields(self):
        with self.assertRaises(KeyError):
            header_value("Model", {})


class TestRunsCheckSeesTheDisagreement(unittest.TestCase):
    """`d4d runs check` reports a header that contradicts the record, and is
    quiet once the header says what the record says."""

    def _seed(self, header_temp):
        import tempfile, yaml
        from pathlib import Path
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        label, proj, method = "2026-09-04f_x-generic-v8_rep1", "VOICE", "claudecode_api"
        (root / method / label).mkdir(parents=True)
        (root / f"{method}_core" / label).mkdir(parents=True)
        (root / method / label / f"{proj}_d4d.yaml").write_text(
            f"# D4D Datasheet\n# Model: claude-opus-5\n# Temperature: {header_temp}\nid: x\n")
        # the core carries the same copied line (278 of them on disk); the
        # check reads both artifacts (#1027 review, finding 3)
        (root / f"{method}_core" / label / f"{proj}_d4d_core.yaml").write_text(
            f"# D4D Datasheet\n# Model: claude-opus-5\n# Temperature: {header_temp}\nid: x\n")
        (root / f"{method}_core" / label / f"{proj}_provenance.yaml").write_text(yaml.safe_dump(
            {"model": {"model": "claude-opus-5", "temperature": None,
                       "temperature_basis": "not applicable to this model"}}))
        return root, method, label, proj

    def test_a_header_asserting_an_unsent_setting_is_reported(self):
        from data_sheets_schema.runs import header_disagreements
        root, method, label, proj = self._seed("0.0")
        got = header_disagreements(method, label, proj, concat_dir=root)
        self.assertEqual([g["artifact"] for g in got], ["full", "core"])   # both artifacts (review finding 3)
        for g in got:
            self.assertEqual((g["field"], g["header"], g["record"]), ("Temperature", "0.0", "null"))
            self.assertIn("not applicable", g["basis"])

    def test_a_record_with_no_temperature_field_is_a_gap_not_a_contradiction(self):
        """`model.get(key)` is None for a missing key too. Four records in the
        corpus carry no `temperature` key; calling their header a contradiction
        would assert the record said "not sent" when it said nothing."""
        import yaml
        from data_sheets_schema.runs import header_disagreements
        root, method, label, proj = self._seed("0.0")
        (root / f"{method}_core" / label / f"{proj}_provenance.yaml").write_text(
            yaml.safe_dump({"model": {"model": "claude-opus-5"}}))
        got = header_disagreements(method, label, proj, concat_dir=root)
        self.assertEqual(len(got), 2)
        self.assertEqual({g["record"] for g in got}, {"not recorded"})

    def test_a_default_effort_header_against_a_silent_record_is_reported_and_a_stamped_one_is_not(self):
        from data_sheets_schema.runs import header_disagreements
        root, method, label, proj = self._seed("not sent (x)")
        full = root / method / label / f"{proj}_d4d.yaml"
        full.write_text(full.read_text().replace("# Model: claude-opus-5\n",
                                                 "# Model: claude-opus-5\n# Reasoning effort: default\n"))
        got = [g for g in header_disagreements(method, label, proj, concat_dir=root) if g["field"] == "Reasoning effort"]
        self.assertEqual([(g["artifact"], g["header"], g["record"]) for g in got],
                         [("full", "default", "not recorded")])
        full.write_text(full.read_text().replace("Reasoning effort: default", "Reasoning effort: not set by the request"))
        got = [g for g in header_disagreements(method, label, proj, concat_dir=root) if g["field"] == "Reasoning effort"]
        self.assertEqual(got, [])

    def test_an_agentic_record_asserting_the_same_value_is_quiet(self):
        """135 agentic records store `temperature: '0.0'` as an asserted value.
        Header and record agree; that the agreement is unverified is #614's
        question, not this one's."""
        import yaml
        from data_sheets_schema.runs import header_disagreements
        root, method, label, proj = self._seed("0.0")
        (root / f"{method}_core" / label / f"{proj}_provenance.yaml").write_text(
            yaml.safe_dump({"model": {"model": "claude-opus-5", "temperature": "0.0",
                                      "temperature_basis": "asserted by the generating agent, not observed"}}))
        self.assertEqual(header_disagreements(method, label, proj, concat_dir=root), [])

    def test_a_header_that_agrees_is_quiet(self):
        from data_sheets_schema.runs import header_disagreements
        root, method, label, proj = self._seed("not sent (claude-opus-5 rejects the parameter)")
        self.assertEqual(header_disagreements(method, label, proj, concat_dir=root), [])

    def test_the_writer_and_the_check_agree_by_construction(self):
        """What `stamp_provenance_header` writes is what `header_disagreements`
        accepts — one vocabulary, so the two cannot drift apart silently."""
        from data_sheets_schema.runs import header_disagreements
        stamped = stamp_provenance_header(
            "# Model: claude-opus-5\n# Temperature: 0.0\nid: x\n",
            {"name": "claude-opus-5", "temperature": 0.0, "temperature_applies": False})
        root, method, label, proj = self._seed("0.0")
        (root / method / label / f"{proj}_d4d.yaml").write_text(stamped)
        (root / f"{method}_core" / label / f"{proj}_d4d_core.yaml").write_text(stamped)
        self.assertEqual(header_disagreements(method, label, proj, concat_dir=root), [])


class TestEveryArtifactWriteIsStamped(unittest.TestCase):
    """The stamp exists at the phase write and nowhere else was the defect
    the review found (#1027 review, findings 1–2): repair rewrites the same
    two files and the model re-emits the prompt's header with them."""

    def test_every_full_or_core_write_in_the_runner_is_preceded_by_the_stamp(self):
        """`_repair_invalid` and `execute` are the only functions that write a
        full or core artifact (the review's ignore-independent scan found
        `:3027`, `:3111`, `:4153` and nothing else; `_snapshot` writes
        intermediates). Each write of a record body there is preceded by the
        stamp; a missing artifact-write site would be a new function, which
        the count guards."""
        import inspect
        import re as _re
        from data_sheets_schema import api_runner
        seen = 0
        for fn in (api_runner._repair_invalid, api_runner.execute):
            src = inspect.getsource(fn)
            for m in _re.finditer(r"(spec\.core_path|spec\.full_path|path|target)\.write_text\((\w+)", src):
                var = m.group(2)
                before = src[max(0, m.start() - 900):m.start()]
                self.assertIn(f"{var} = stamp_provenance_header({var}, settings)", before,
                              f"{fn.__name__}: write of {var} is not stamped")
                seen += 1
        self.assertEqual(seen, 3)

    def test_the_repaired_record_on_disk_carries_the_stamp(self):
        """Through `_repair_invalid` with a fake client that returns the
        prompt-copied header: the file lands stamped, and the re-derived core
        with it."""
        import tempfile
        from pathlib import Path
        from unittest import mock
        from data_sheets_schema import api_runner
        from tests.test_download.test_api_runner import spec
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        s = spec(out_dir=Path(tmp.name) / "out")
        s.full_path.parent.mkdir(parents=True, exist_ok=True)
        s.core_path.parent.mkdir(parents=True, exist_ok=True)
        s.full_path.write_text("# Model: claude-opus-5\n# Temperature: 0.0\nid: x\ntitle: T\nname: n\ndescription: d\nkeywords: [a]\n")
        repaired = ("```yaml\n# Model: claude-opus-5\n# Temperature: 0.0\nid: x\ntitle: T\nname: n\n"
                    "description: d\nkeywords: [a]\n```\n")

        class _Block:
            type = "text"; text = repaired

        class _Usage:
            input_tokens = output_tokens = 1; cache_read_input_tokens = cache_creation_input_tokens = 0

        class _Resp:
            stop_reason = "end_turn"; content = [_Block()]; usage = _Usage()

        settings = {"name": "claude-opus-5", "temperature": 0.0, "max_tokens": 1000,
                    "temperature_applies": False, "config_path": "x"}
        calls = {"n": 0}

        def fake_validate(path, schema, cls):
            calls["n"] += 1
            return (["one failure"], None) if calls["n"] == 1 else ([], None)

        with mock.patch.object(api_runner, "_validator_lines", fake_validate), \
                mock.patch.object(api_runner, "_call_with_retry", lambda *a, **k: _Resp()), \
                mock.patch.object(api_runner, "_snapshot", lambda *a, **k: None):
            api_runner._repair_invalid(s, object(), settings, [])
        head = s.full_path.read_text().splitlines()[1]
        self.assertTrue(head.startswith("# Temperature: not sent ("), head)
        if s.core_path.exists():
            self.assertIn("# Temperature: not sent (", s.core_path.read_text())


if __name__ == "__main__":
    unittest.main()
