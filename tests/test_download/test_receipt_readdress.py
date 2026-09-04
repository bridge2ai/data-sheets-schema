"""A receipt entry whose slot is not a path in the record gets one
re-addressing turn before the receipt is accepted (#952).

The v8 CM4AI canary receipted the Dataverse subject line under `subject`, a
name the schema has no slot for, for a value the record held under
`keywords`; `receipts.check` counted it as `slot_not_in_record`, a gated
finding, and the batch gate stopped. The receipt rule already said the slot
is the record path the value fills — this is the mechanism behind the rule:
the runner asks once where the value went, moves the entry only to a path
that resolves, drops an entry for a value the record does not carry, and
leaves anything else as written for the gate to count.
"""

import tempfile
import unittest.mock
import unittest
from pathlib import Path

import yaml

from data_sheets_schema import api_runner
from data_sheets_schema.api_runner import (
    PHASE_INSTRUCTIONS,
    RECEIPT_MARK,
    apply_readdress,
    assembly_digest,
    unresolved_receipt_slots,
)
from tests.test_download.test_api_runner import FakeMessages, FakeResponse, spec

RECORD = {"id": "x", "title": "T", "keywords": ["a", "Medicine, Health and Life Sciences"],
          "funders": [{"name": "NIH"}]}


def _receipt(*entries):
    return {"bundle_md5": "m", "chunks": [
        {"id": "c001", "status": "extracted", "extracted": [dict(e) for e in entries]}]}


class TestUnresolved(unittest.TestCase):
    def test_a_slot_the_record_does_not_carry_is_unresolved(self):
        r = _receipt({"slot": "title", "snippet": "T"},
                     {"slot": "subject", "snippet": "Medicine, Health and Life Sciences"},
                     {"slot": "funders[3].name", "snippet": "NIH"})
        self.assertEqual([(u["entry"], u["slot"]) for u in unresolved_receipt_slots(RECORD, r)],
                         [(1, "subject"), (2, "funders[3].name")])

    def test_entries_and_leaves_that_resolve_are_not(self):
        r = _receipt({"slot": "funders[0]", "snippet": "NIH"}, {"slot": "keywords[1]", "snippet": "M"})
        self.assertEqual(unresolved_receipt_slots(RECORD, r), [])


class TestApply(unittest.TestCase):
    def test_moves_only_to_a_path_that_resolves_and_drops_on_request(self):
        r = _receipt({"slot": "subject", "snippet": "Medicine"},
                     {"slot": "funders[3].name", "snippet": "NIH"},
                     {"slot": "nowhere", "snippet": "z"},
                     {"slot": "title", "snippet": "T"})
        out = apply_readdress(r, RECORD, [
            {"chunk": "c001", "entry": 0, "slot": "subject", "new_slot": "keywords[1]"},
            {"chunk": "c001", "entry": 1, "slot": "funders[3].name", "new_slot": "funders[7].name"},  # still wrong
            {"chunk": "c001", "entry": 2, "slot": "nowhere", "drop": True, "reason": "not in the record"},
            {"chunk": "c001", "entry": 3, "slot": "title", "new_slot": "id"},                        # resolves: untouched
        ])
        slots = [e["slot"] for e in r["chunks"][0]["extracted"]]
        self.assertEqual(slots, ["keywords[1]", "funders[3].name", "title"])
        self.assertEqual([m["new_slot"] for m in out["moved"]], ["keywords[1]"])
        self.assertEqual([d["slot"] for d in out["dropped"]], ["nowhere"])
        self.assertEqual([(x["slot"], x["reason"]) for x in out["rejected"]],
                         [("funders[3].name", "new_slot does not resolve"), ("title", "already resolves")])
        self.assertEqual(out["emptied"], [])

    def test_duplicate_slots_in_one_chunk_are_addressed_by_ordinal(self):
        """#954: (chunk, slot) is not an identity — 27 of 29 receipts repeat one."""
        r = _receipt({"slot": "subject", "snippet": "a"}, {"slot": "subject", "snippet": "Medicine"})
        out = apply_readdress(r, RECORD, [
            {"chunk": "c001", "entry": 0, "slot": "subject", "new_slot": "keywords[0]"},
            {"chunk": "c001", "entry": 1, "slot": "subject", "new_slot": "keywords[1]"},
        ])
        self.assertEqual([e["slot"] for e in r["chunks"][0]["extracted"]], ["keywords[0]", "keywords[1]"])
        self.assertEqual(len(out["moved"]), 2)

    def test_answers_are_typed_and_exclusive(self):
        """#958: any truthy drop deleted the entry; drop plus new_slot was accepted."""
        r = _receipt({"slot": "subject", "snippet": "a"}, {"slot": "subject", "snippet": "b"},
                     {"slot": "subject", "snippet": "c"}, {"slot": "subject", "snippet": "d"})
        out = apply_readdress(r, RECORD, [
            {"chunk": "c001", "entry": 0, "slot": "subject", "drop": "false"},
            {"chunk": "c001", "entry": 1, "slot": "subject", "drop": True, "new_slot": "keywords[0]"},
            {"chunk": "c001", "entry": 2, "slot": "title", "new_slot": "keywords[0]"},     # slot mismatch
            {"chunk": "c001", "entry": 9, "slot": "subject", "new_slot": "keywords[0]"},   # no such entry
            {"chunk": "c001", "slot": "subject", "new_slot": "keywords[0]"},               # no ordinal
        ])
        self.assertEqual(len(r["chunks"][0]["extracted"]), 4, "nothing applied")
        self.assertEqual(sorted(x["reason"].split(" ")[0] for x in out["rejected"]),
                         sorted(["drop", "both", "entry", "no", "no"]))

    def test_a_chunk_emptied_by_drops_becomes_nothing_relevant(self):
        """#958: an `extracted` chunk with no pairs is itself a gated finding."""
        r = _receipt({"slot": "subject", "snippet": "Medicine"})
        out = apply_readdress(r, RECORD, [
            {"chunk": "c001", "entry": 0, "slot": "subject", "drop": True, "reason": "the record has no subject"}])
        chunk = r["chunks"][0]
        self.assertEqual(chunk["status"], "nothing_relevant")
        self.assertNotIn("extracted", chunk)
        self.assertIn("the record has no subject", chunk["reason"])
        self.assertEqual(out["emptied"], ["c001"])

    def test_non_dict_entries_are_passed_through(self):
        r = _receipt({"slot": "subject", "snippet": "Medicine"})
        r["chunks"][0]["extracted"].insert(0, "bad")
        out = apply_readdress(r, RECORD, [
            {"chunk": "c001", "entry": 1, "slot": "subject", "new_slot": "keywords[1]"}])
        self.assertEqual(r["chunks"][0]["extracted"][0], "bad")
        self.assertEqual(len(out["moved"]), 1)


class _ReceiptFake(FakeMessages):
    """A full phase that writes a receipt with one mis-addressed entry, and a
    re-addressing answer that moves it."""

    def __init__(self, bad_slot="subject", answer=None, raise_on_readdress=None, truncate=False):
        super().__init__()
        self.bad_slot, self.answer, self.raise_on_readdress = bad_slot, answer, raise_on_readdress
        self.truncate = truncate

    def create(self, **kw):
        last = kw["messages"][-1]
        if last["role"] == "user" and isinstance(last["content"], list) and any(
                PHASE_INSTRUCTIONS["full_readdress"] in p.get("text", "") for p in last["content"]):
            self.calls.append(kw)
            if self.raise_on_readdress:
                raise self.raise_on_readdress
            resp = FakeResponse(self.answer or
                                "readdress:\n- chunk: c001\n  entry: 1\n  slot: subject\n  new_slot: keywords[0]\n")
            if self.truncate:
                resp.stop_reason = "max_tokens"
            return resp
        blob = " ".join(p.get("text", "") for p in kw["messages"][0]["content"])
        if PHASE_INSTRUCTIONS["full"] in blob:
            self.calls.append(kw)
            # `keywords: a` is a scalar in a multivalued slot: the write path
            # normalises it to a list, so `keywords[0]` resolves only against
            # the normalised record (#957).
            return FakeResponse(
                "```yaml\n# full\nid: x\ntitle: T\nname: n\ndescription: d\nkeywords: a\n```\n"
                f"{RECEIPT_MARK}\n```yaml\nbundle_md5: m\nchunks:\n- id: c001\n  status: extracted\n"
                "  extracted:\n  - slot: title\n    snippet: \"a verbatim phrase here\"\n"
                f"  - slot: {self.bad_slot}\n    snippet: \"Medicine, Health and Life Sciences\"\n"
                "- id: c002\n  status: nothing_relevant\n  reason: r\n```\n")
        return super().create(**kw)


@unittest.skipUnless(Path("data/preprocessed/chunks/CHORUS_chunks.yaml").exists(), "manifest absent")
class TestEndToEnd(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.out = Path(self.tmp.name) / "out"
        self._client = api_runner._client
        self.addCleanup(lambda: setattr(api_runner, "_client", self._client))

    def _run(self, fake):
        client = type("C", (), {})(); client.messages = fake
        api_runner._client = lambda: client
        s = spec(out_dir=self.out, condition="generic_v7")
        with unittest.mock.patch.object(api_runner, "_validator_lines", lambda *a: ([], None)):
            res = api_runner.execute(s)
        return s, res, fake

    def test_a_mis_addressed_entry_is_re_addressed_once_and_the_original_kept(self):
        s, res, fake = self._run(_ReceiptFake())
        phases = [u["phase"] for u in res["usage"]]
        self.assertEqual(phases, ["full", "full_readdress", "audit", "reconcile_full", "report"])
        written = yaml.safe_load(api_runner._receipt_path(s).read_text())
        self.assertEqual([e["slot"] for e in written["chunks"][0]["extracted"]], ["title", "keywords[0]"])
        r = next(u for u in res["usage"] if u["phase"] == "full_readdress")["readdress"]
        self.assertEqual([(u["entry"], u["slot"]) for u in r["unresolved_before"]], [(1, "subject")])
        self.assertEqual(r["moved"], [{"chunk": "c001", "entry": 1, "slot": "subject", "new_slot": "keywords[0]"}])
        self.assertEqual(yaml.safe_load(s.full_path.read_text())["keywords"], ["a"], "normalised on disk")
        self.assertEqual(r["still_unresolved"], [])
        inter = s.provenance_path.parent / "intermediate"
        original = yaml.safe_load((inter / "CHORUS_coverage_receipt_as_written.yaml").read_text())
        self.assertEqual(original["chunks"][0]["extracted"][1]["slot"], "subject")
        # The re-addressing turn carries the full-phase exchange, not a fresh request.
        call = fake.calls[1]
        self.assertEqual([m["role"] for m in call["messages"]], ["user", "assistant", "user"])
        self.assertIn(RECEIPT_MARK, call["messages"][1]["content"])
        d = yaml.safe_load((self.out / "CHORUS_provenance.yaml").read_text())
        self.assertEqual([u["phase"] for u in d["api_usage"]], phases)
        # The usage entry's `readdress` block must be something the record
        # schema accepts, or every re-addressed run would fail conformance.
        from data_sheets_schema.provenance import check_record
        self.assertEqual(check_record(d), ([], None))

    def test_a_receipt_whose_slots_all_resolve_makes_no_extra_call(self):
        s, res, fake = self._run(_ReceiptFake(bad_slot="keywords[0]"))
        self.assertEqual([u["phase"] for u in res["usage"]], ["full", "audit", "reconcile_full", "report"])
        self.assertFalse((s.provenance_path.parent / "intermediate" / "CHORUS_coverage_receipt_as_written.yaml").exists())

    def test_an_unusable_answer_leaves_the_receipt_as_written(self):
        s, res, fake = self._run(_ReceiptFake(answer="I cannot help with that.\n"))
        r = next(u for u in res["usage"] if u["phase"] == "full_readdress")["readdress"]
        self.assertIn("not a YAML mapping", r["call_failed"])
        self.assertEqual([u["slot"] for u in r["still_unresolved"]], ["subject"])
        written = yaml.safe_load(api_runner._receipt_path(s).read_text())
        self.assertEqual(written["chunks"][0]["extracted"][1]["slot"], "subject")


    def test_a_failing_corrective_call_leaves_the_receipt_as_written_and_the_run_completes(self):
        """#955: the full phase had succeeded; the follow-up must not undo it."""
        s, res, fake = self._run(_ReceiptFake(raise_on_readdress=RuntimeError("boom")))
        phases = [u["phase"] for u in res["usage"]]
        self.assertEqual(phases, ["full", "full_readdress", "audit", "reconcile_full", "report"])
        r = next(u for u in res["usage"] if u["phase"] == "full_readdress")["readdress"]
        self.assertIn("RuntimeError", r["call_failed"])
        self.assertEqual([u["slot"] for u in r["still_unresolved"]], ["subject"])
        written = yaml.safe_load(api_runner._receipt_path(s).read_text())
        self.assertEqual(written["chunks"][0]["extracted"][1]["slot"], "subject")
        self.assertEqual(sum(1 for c in fake.calls if c["messages"][-1]["role"] == "user"
                             and PHASE_INSTRUCTIONS["full"] in " ".join(p.get("text", "") for p in c["messages"][0]["content"])
                             and len(c["messages"]) == 1), 1, "the full phase ran once")

    def test_the_plan_names_the_conditional_call_and_the_record_its_cap(self):
        s = spec(out_dir=self.out, condition="generic_v7")
        self.assertTrue(any("full_readdress" in c for c in api_runner.plan(s)["conditional_calls"]))
        self.assertEqual(api_runner.plan(spec(out_dir=self.out))["conditional_calls"], [])
        s, res, fake = self._run(_ReceiptFake())
        d = yaml.safe_load((self.out / "CHORUS_provenance.yaml").read_text())
        self.assertEqual(d["model"]["max_tokens_by_phase"]["full_readdress"], api_runner.READDRESS_MAX_TOKENS)


@unittest.skipUnless(Path("data/preprocessed/chunks/CHORUS_chunks.yaml").exists(), "manifest absent")
class TestTruncation(TestEndToEnd):
    # Inherits setUp/_run only; the parent's tests are not re-collected here.
    test_a_mis_addressed_entry_is_re_addressed_once_and_the_original_kept = None
    test_a_receipt_whose_slots_all_resolve_makes_no_extra_call = None
    test_an_unusable_answer_leaves_the_receipt_as_written = None
    test_a_failing_corrective_call_leaves_the_receipt_as_written_and_the_run_completes = None
    test_the_plan_names_the_conditional_call_and_the_record_its_cap = None
    def test_a_truncated_answer_applies_nothing(self):
        """A cut-off list parses as a shorter list; `drop: tru` parses as a string."""
        fake = _ReceiptFake(answer="readdress:\n- chunk: c001\n  entry: 1\n  slot: subject\n  drop: tru",
                            truncate=True)
        s, res, fake = self._run(fake)
        r = next(u for u in res["usage"] if u["phase"] == "full_readdress")["readdress"]
        self.assertIn("truncated", r["call_failed"])
        self.assertEqual([u["slot"] for u in r["still_unresolved"]], ["subject"])
        written = yaml.safe_load(api_runner._receipt_path(s).read_text())
        self.assertEqual(len(written["chunks"][0]["extracted"]), 2, "nothing dropped")


class TestTelemetryAcceptsThePhase(unittest.TestCase):
    def test_the_phase_enum_names_it(self):
        """#956: the telemetry copies every api_usage phase into PhaseEnum."""
        from data_sheets_schema.run_telemetry import SCHEMA_PATH
        from data_sheets_schema.schema_view import shared_view
        sv = shared_view(Path(SCHEMA_PATH) if Path(SCHEMA_PATH).is_absolute() else Path(SCHEMA_PATH))
        self.assertIn("full_readdress", sv.get_enum("PhaseEnum").permissible_values)


class TestTheAssemblyDigestCoversIt(unittest.TestCase):
    def test_editing_the_instruction_moves_the_digest(self):
        before = assembly_digest()["sha256"]
        with unittest.mock.patch.dict(PHASE_INSTRUCTIONS, {"full_readdress": "changed"}):
            self.assertNotEqual(assembly_digest()["sha256"], before)


if __name__ == "__main__":
    unittest.main()
