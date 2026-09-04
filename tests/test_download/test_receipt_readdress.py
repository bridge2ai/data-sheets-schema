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
        self.assertEqual([u["slot"] for u in unresolved_receipt_slots(RECORD, r)],
                         ["subject", "funders[3].name"])

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
            {"chunk": "c001", "slot": "subject", "new_slot": "keywords[1]"},
            {"chunk": "c001", "slot": "funders[3].name", "new_slot": "funders[7].name"},   # still wrong
            {"chunk": "c001", "slot": "nowhere", "drop": True, "reason": "not in the record"},
            {"chunk": "c001", "slot": "title", "new_slot": "id"},                          # resolves: untouched
        ])
        slots = [e["slot"] for e in r["chunks"][0]["extracted"]]
        self.assertEqual(slots, ["keywords[1]", "funders[3].name", "title"])
        self.assertEqual([m["new_slot"] for m in out["moved"]], ["keywords[1]"])
        self.assertEqual([d["slot"] for d in out["dropped"]], ["nowhere"])
        self.assertEqual([x["slot"] for x in out["rejected"]], ["funders[3].name"])

    def test_an_entry_the_answer_does_not_name_is_untouched(self):
        r = _receipt({"slot": "subject", "snippet": "Medicine"})
        out = apply_readdress(r, RECORD, [])
        self.assertEqual(r["chunks"][0]["extracted"][0]["slot"], "subject")
        self.assertEqual(out, {"moved": [], "dropped": [], "rejected": []})


class _ReceiptFake(FakeMessages):
    """A full phase that writes a receipt with one mis-addressed entry, and a
    re-addressing answer that moves it."""

    def __init__(self, bad_slot="subject", answer=None):
        super().__init__()
        self.bad_slot, self.answer = bad_slot, answer

    def create(self, **kw):
        last = kw["messages"][-1]
        if last["role"] == "user" and isinstance(last["content"], list) and any(
                PHASE_INSTRUCTIONS["full_readdress"] in p.get("text", "") for p in last["content"]):
            self.calls.append(kw)
            return FakeResponse(self.answer or
                                "readdress:\n- chunk: c001\n  slot: subject\n  new_slot: keywords[0]\n")
        blob = " ".join(p.get("text", "") for p in kw["messages"][0]["content"])
        if PHASE_INSTRUCTIONS["full"] in blob:
            self.calls.append(kw)
            return FakeResponse(
                "```yaml\n# full\nid: x\ntitle: T\nname: n\ndescription: d\nkeywords: [a]\n```\n"
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
        self.assertEqual([u["slot"] for u in r["unresolved_before"]], ["subject"])
        self.assertEqual(r["moved"], [{"chunk": "c001", "slot": "subject", "new_slot": "keywords[0]"}])
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
        self.assertIn("unusable", r)
        self.assertEqual([u["slot"] for u in r["still_unresolved"]], ["subject"])
        written = yaml.safe_load(api_runner._receipt_path(s).read_text())
        self.assertEqual(written["chunks"][0]["extracted"][1]["slot"], "subject")


class TestTheAssemblyDigestCoversIt(unittest.TestCase):
    def test_editing_the_instruction_moves_the_digest(self):
        before = assembly_digest()["sha256"]
        with unittest.mock.patch.dict(PHASE_INSTRUCTIONS, {"full_readdress": "changed"}):
            self.assertNotEqual(assembly_digest()["sha256"], before)


if __name__ == "__main__":
    unittest.main()
