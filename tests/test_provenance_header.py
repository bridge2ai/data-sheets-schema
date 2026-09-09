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

    def test_header_value_refuses_unknown_fields(self):
        with self.assertRaises(KeyError):
            header_value("Model", {})


if __name__ == "__main__":
    unittest.main()


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
        (root / f"{method}_core" / label / f"{proj}_provenance.yaml").write_text(yaml.safe_dump(
            {"model": {"model": "claude-opus-5", "temperature": None,
                       "temperature_basis": "not applicable to this model"}}))
        return root, method, label, proj

    def test_a_header_asserting_an_unsent_setting_is_reported(self):
        from data_sheets_schema.runs import header_disagreements
        root, method, label, proj = self._seed("0.0")
        got = header_disagreements(method, label, proj, concat_dir=root)
        self.assertEqual(len(got), 1)
        self.assertEqual((got[0]["field"], got[0]["header"], got[0]["record"]),
                         ("Temperature", "0.0", "null"))
        self.assertIn("not applicable", got[0]["basis"])

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
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["record"], "not recorded")

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
        self.assertEqual(header_disagreements(method, label, proj, concat_dir=root), [])
