"""Receipt origin: contemporaneous, Phase 1 and Phase 3 snippets told apart
from the transcript, and `unknown` wherever the history cannot be rebuilt
(#2933). Synthetic transcripts only."""
import itertools
import json
import os
import tempfile
import unittest
from pathlib import Path

import yaml
from click.testing import CliRunner

from data_sheets_schema import receipt_origin as ro

SECRET = "Grant OT2OD032644 secret-snippet-text"


def receipt_text(*entries):
    """A receipt from (chunk, [(slot, snippet), ...]) entries."""
    return yaml.safe_dump({"bundle_md5": "0" * 32, "chunks": [
        {"id": chunk, "status": "extracted",
         "extracted": [{"slot": slot, "snippet": snippet} for slot, snippet in pairs]}
        for chunk, pairs in entries]}, sort_keys=False)


class Run:
    """One synthetic stream-json attempt: calls, results and the files on disk."""

    def __init__(self, root: Path):
        self.root = root
        self.receipt = root / "data" / "claudecode_direct_core" / "L" / "CHORUS_coverage_receipt.yaml"
        self.full = root / "data" / "claudecode_direct" / "L" / "CHORUS_d4d.yaml"
        self.receipt.parent.mkdir(parents=True)
        self.full.parent.mkdir(parents=True)
        self.events = [{"type": "system", "subtype": "init", "cwd": str(root), "session_id": "s"}]
        self.n = 0
        self.created: set = set()
        self.last_receipt = None

    def _id(self):
        self.n += 1
        return f"toolu_{self.n:03d}"

    def call(self, name, identity=None, **inputs):
        identity = identity or self._id()
        self.events.append({"type": "assistant", "session_id": "s", "parent_tool_use_id": None,
                            "message": {"role": "assistant", "content": [
                                {"type": "tool_use", "id": identity, "name": name, "input": inputs}]}})
        return identity

    def result(self, identity, content="ok", metadata=None, **flags):
        block = {"type": "tool_result", "tool_use_id": identity, "content": content, **flags}
        event = {"type": "user", "session_id": "s", "parent_tool_use_id": None,
                 "message": {"role": "user", "content": [block]}}
        if metadata is not None:
            event["tool_use_result"] = metadata
        self.events.append(event)

    def write(self, path, content, *, outcome="ok"):
        identity = self.call("Write", file_path=str(path), content=content)
        if outcome == "ok":
            kind = "update" if path in self.created else "create"
            self.created.add(path)
            # A successful native Write carries no `is_error` and the
            # runtime's own metadata (observed in the fake-provider transcript).
            self.result(identity, f"File written at: {path}",
                        {"type": kind, "filePath": str(path), "content": content})
            if path == self.receipt:
                self.last_receipt = content
        elif outcome == "file_not_read":
            self.result(identity, ro.UNREAD_WRITE_ERROR,
                        "Error: File has not been read yet. Read it first before writing to it.",
                        is_error=True)
        elif outcome == "error":
            self.result(identity, "denied", "Error: denied", is_error=True)
        return identity

    def bash(self, command, *, ok=True, content=None, metadata=None):
        """A shell call and its result. By default a run that exited as `ok`
        says, in the runtime's observed shapes: a dict of stdout/stderr with
        `is_error: false`, or `Exit code 1` text with `is_error: true`."""
        identity = self.call("Bash", command=command, description="x")
        if metadata is None:
            metadata = ({"stdout": "", "stderr": "", "interrupted": False, "isImage": False} if ok
                        else "Error: Exit code 1")
        self.result(identity, content if content is not None else ("out" if ok else "Exit code 1"),
                    metadata, is_error=not ok)
        return identity

    def derive_command(self, full=None):
        return (f"poetry run d4d derive core \\\n  --full {full or self.full.relative_to(self.root)}"
                f" \\\n  --out data/claudecode_direct_core/L/CHORUS_d4d_core.yaml")

    def derive(self, *, ok=True, full=None):
        return self.bash(self.derive_command(full), ok=ok)

    def transcript(self, name="transcript.jsonl", events=None):
        path = self.root / name
        path.write_text("".join(json.dumps(e) + "\n" for e in (events or self.events)), encoding="utf-8")
        return path

    def report(self, sync=True):
        if sync and self.last_receipt is not None:
            self.receipt.write_text(self.last_receipt, encoding="utf-8")
        return ro.origin([self.transcript()], self.receipt, self.full)


class Base(unittest.TestCase):
    def setUp(self):
        self.run_ = self.new_run()

    def new_run(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        return Run(Path(tmp.name))

    def assertUnknown(self, block, fragment):
        self.assertEqual(block["status"], "unknown")
        self.assertTrue(any(fragment in r for r in block["reasons"]), block["reasons"])
        for key in ("origin", "snippets", "deltas", "post_draft_entries", "readdressed"):
            self.assertNotIn(key, block)          # never a classification, never contemporaneous


PRE = receipt_text(("c001", [("title", "The CHORUS dataset"), ("funders[0].grant_id", "OT2OD032701")]),
                   ("c002", [("description", "a multimodal collection")]))


class Classification(Base):
    def test_receipt_written_only_before_the_draft_is_all_contemporaneous(self):
        r = self.run_
        r.write(r.receipt, receipt_text(("c001", [("title", "The CHORUS dataset")])))
        r.write(r.receipt, PRE)
        r.write(r.full, "id: x\n")
        r.derive()
        block = r.report()
        self.assertEqual(block["status"], "checked", block["reasons"])
        self.assertEqual(block["origin"], {"contemporaneous": 3, "phase1_correction": 0, "phase3_backport": 0})
        self.assertEqual((block["post_draft"], block["removed_contemporaneous"], block["readdressed"]), (0, 0, 0))
        self.assertEqual(block["snippets"], {"pre_draft": 3, "at_derive_core": 3, "final": 3})
        self.assertEqual(block["boundaries"]["full_record_write"]["line"], 6)
        self.assertEqual(block["boundaries"]["derive_core"]["tool_use_id"], "toolu_004")

    def test_a_readdress_only_rewrite_adds_and_removes_nothing(self):
        r = self.run_
        r.write(r.receipt, PRE)
        r.write(r.full, "id: x\n")
        r.write(r.receipt, receipt_text(("c001", [("name", "The CHORUS dataset"),
                                                  ("funders[1].grant_id", "OT2OD032701")]),
                                         ("c002", [("keywords", "a multimodal collection")])))
        block = r.report()
        self.assertEqual(block["status"], "checked", block["reasons"])
        self.assertEqual(block["deltas"]["draft_to_final"], {"removed": 0, "added": 0})
        self.assertEqual(block["deltas"]["triples_draft_to_final"], {"removed": 3, "added": 3})
        self.assertEqual(block["origin"]["contemporaneous"], 3)
        self.assertEqual((block["post_draft"], block["removed_contemporaneous"], block["readdressed"]), (0, 0, 3))

    def test_phase1_and_phase3_split_at_the_first_successful_derive(self):
        r = self.run_
        r.write(r.receipt, PRE)
        r.write(r.full, "id: x\n")
        phase1 = receipt_text(("c001", [("title", "The CHORUS dataset"), ("funders[0].grant_id", "OT2OD032701"),
                                        ("license", "CC BY 4.0 license")]),
                              ("c002", [("description", "a multimodal collection")]))
        r.write(r.receipt, phase1)
        r.derive(ok=False)                          # a failed derive does not move the boundary
        r.derive(full="data/elsewhere/CHORUS_d4d.yaml")   # another record's derive is not this one
        added = receipt_text(("c001", [("title", "The CHORUS dataset"), ("funders[0].grant_id", "OT2OD032701"),
                                       ("license", "CC BY 4.0 license")]),
                             ("c002", [("description", "a multimodal collection"), ("version", "release 2.0")]))
        r.write(r.receipt, added)
        r.derive()
        final = receipt_text(("c001", [("title", "The CHORUS dataset"), ("funders[0].grant_id", "OT2OD032701"),
                                       ("license", "CC BY 4.0 license")]),
                             ("c002", [("description", "a multimodal collection"), ("version", "release 2.0")]),
                             ("c003", [("creators[0].name", "Jane Parker")]))
        r.write(r.receipt, final)
        block = r.report()
        self.assertEqual(block["status"], "checked", block["reasons"])
        self.assertEqual(block["origin"], {"contemporaneous": 3, "phase1_correction": 2, "phase3_backport": 1})
        self.assertEqual(block["snippets"], {"pre_draft": 3, "at_derive_core": 5, "final": 6})
        self.assertEqual(block["deltas"]["draft_to_derive_core"], {"removed": 0, "added": 2})
        self.assertEqual(block["deltas"]["derive_core_to_final"], {"removed": 0, "added": 1})
        self.assertEqual([a["outcome"] for a in block["derive_core_attempts"]],
                         ["failed", "succeeded", "succeeded"])
        self.assertEqual([a["targets_full"] for a in block["derive_core_attempts"]], [True, False, True])
        self.assertEqual(block["boundaries"]["derive_core"]["tool_use_id"], "toolu_007")
        by_slot = {e["slot"]: e["origin"] for e in block["post_draft_entries"]}
        self.assertEqual(by_slot, {"license": "phase1_correction", "version": "phase1_correction",
                                   "creators[0].name": "phase3_backport"})
        self.assertEqual(block["by_chunk"]["c003"], {"contemporaneous": 0, "phase1_correction": 0,
                                                     "phase3_backport": 1})

    def test_without_a_successful_derive_every_post_draft_snippet_is_phase1(self):
        r = self.run_
        r.write(r.receipt, PRE)
        r.write(r.full, "id: x\n")
        r.derive(ok=False)
        r.write(r.receipt, receipt_text(("c001", [("title", "The CHORUS dataset"),
                                                  ("funders[0].grant_id", "OT2OD032701")]),
                                         ("c002", [("description", "a multimodal collection")]),
                                         ("c003", [("license", "CC BY 4.0 license")])))
        block = r.report()
        self.assertEqual(block["status"], "checked", block["reasons"])
        self.assertIsNone(block["boundaries"]["derive_core"])
        self.assertIsNone(block["snippets"]["at_derive_core"])
        self.assertEqual(block["origin"], {"contemporaneous": 3, "phase1_correction": 1, "phase3_backport": 0})
        # No derive-time snapshot, so no derive-core delta under that name:
        # the step is reported as draft → final (#3114).
        self.assertEqual(block["deltas"]["draft_to_derive_core"], None)
        self.assertEqual(block["deltas"]["derive_core_to_final"], None)
        self.assertEqual(block["deltas"]["draft_to_final"], {"removed": 0, "added": 1})
        lines = ro.summary(block)
        self.assertIn("snippets 3 pre-draft · no successful derive core · 4 final", lines)
        self.assertTrue(any(line.startswith("draft → final −0 / +1 ·") for line in lines), lines)
        self.assertFalse(any("→ derive core" in line for line in lines), lines)

    def test_with_a_derive_both_derive_core_deltas_and_draft_to_final_are_reported(self):
        r = self.run_
        r.write(r.receipt, PRE)
        r.write(r.full, "id: x\n")
        r.write(r.receipt, receipt_text(("c001", [("title", "The CHORUS dataset")]),
                                         ("c002", [("description", "a multimodal collection")]),
                                         ("c003", [("license", "CC BY 4.0 license")])))
        r.derive()
        r.write(r.receipt, receipt_text(("c001", [("title", "The CHORUS dataset")]),
                                         ("c002", [("description", "a multimodal collection")]),
                                         ("c003", [("license", "CC BY 4.0 license")]),
                                         ("c004", [("version", "release 2.0")])))
        block = r.report()
        self.assertEqual(block["status"], "checked", block["reasons"])
        self.assertEqual(block["deltas"]["draft_to_derive_core"], {"removed": 1, "added": 1})
        self.assertEqual(block["deltas"]["derive_core_to_final"], {"removed": 0, "added": 1})
        self.assertEqual(block["deltas"]["draft_to_final"], {"removed": 1, "added": 2})
        self.assertIn("draft → derive core −1 / +1 · derive core → final −0 / +1 · "
                      "(chunk, snippet, slot) triples −1 / +2", ro.summary(block))

    def test_no_receipt_before_the_draft_is_all_post_draft(self):
        r = self.run_
        r.write(r.full, "id: x\n")
        r.write(r.receipt, PRE)
        block = r.report()
        self.assertEqual(block["status"], "checked", block["reasons"])
        self.assertEqual(block["origin"]["contemporaneous"], 0)
        self.assertEqual(block["post_draft"], 3)

    def test_multiset_semantics(self):
        r = self.run_
        r.write(r.receipt, receipt_text(("c001", [("title", "The CHORUS dataset")])))
        r.write(r.full, "id: x\n")
        # added then removed before the final receipt: not counted
        r.write(r.receipt, receipt_text(("c001", [("title", "The CHORUS dataset"), ("name", "transient text")])))
        r.derive()
        # a duplicated final triple counts twice: once matched pre-draft, once added
        r.write(r.receipt, receipt_text(("c001", [("title", "The CHORUS dataset"), ("title", "The CHORUS dataset")])))
        block = r.report()
        self.assertEqual(block["status"], "checked", block["reasons"])
        self.assertEqual(block["snippets"]["final"], 2)
        self.assertEqual(block["origin"], {"contemporaneous": 1, "phase1_correction": 0, "phase3_backport": 1})
        self.assertEqual(block["deltas"]["derive_core_to_final"], {"removed": 1, "added": 1})
        self.assertNotIn("name", {e["slot"] for e in block["post_draft_entries"]})

    def test_a_removed_contemporaneous_snippet_is_counted_and_listed_by_hash(self):
        r = self.run_
        r.write(r.receipt, PRE)
        r.write(r.full, "id: x\n")
        r.write(r.receipt, receipt_text(("c001", [("title", "The CHORUS dataset")])))
        block = r.report()
        self.assertEqual(block["removed_contemporaneous"], 2)
        self.assertEqual(sorted(e["slot"] for e in block["removed_entries"]), ["description", "funders[0].grant_id"])
        self.assertTrue(all(len(e["snippet_sha256"]) == 64 for e in block["removed_entries"]))

    def test_the_final_count_is_the_snippet_total_receipts_check_reports(self):
        from data_sheets_schema import receipts as rc
        from tests.test_receipts import FULL, _manifest_and_texts, _receipt
        manifest, texts = _manifest_and_texts()
        receipt = _receipt(manifest["bundle_md5"])
        receipt["chunks"].append({"id": "c009", "status": "extracted", "extracted": "not a list"})
        # A chunk moved to nothing_relevant that keeps its old pairs: `check`
        # counts only `extracted` entries, and so must `triples` (#3118).
        self.assertEqual(receipt["chunks"][0]["status"], "nothing_relevant")
        receipt["chunks"][0]["extracted"] = [{"slot": "title", "snippet": "AI-READI"}]
        checked = rc.check(receipt, manifest, texts, FULL, manifest["bundle_md5"])
        self.assertEqual(checked["snippets"]["total"], 8)
        self.assertEqual(len(ro.triples(yaml.safe_dump(receipt))), checked["snippets"]["total"])


class Writes(Base):
    def test_a_rejected_write_changes_nothing_and_is_listed(self):
        r = self.run_
        r.write(r.receipt, PRE)
        r.write(r.full, "id: early\n", outcome="file_not_read")     # never the draft boundary
        r.write(r.full, "id: x\n")
        r.write(r.receipt, PRE + "extra: 1\n", outcome="error")
        block = r.report()
        self.assertEqual(block["status"], "checked", block["reasons"])
        self.assertEqual(block["boundaries"]["full_record_write"]["tool_use_id"], "toolu_003")
        self.assertEqual([(w["target"], w["rejection"]) for w in block["rejected_writes"]],
                         [("full", "file_not_read"), ("receipt", "is_error")])
        self.assertEqual(block["receipt"]["writes"], 1)
        self.assertEqual(block["post_draft"], 0)

    def test_a_write_without_success_evidence_is_unknown(self):
        r = self.run_
        r.write(r.receipt, PRE)
        r.write(r.full, "id: x\n")
        identity = r.call("Write", file_path=str(r.receipt), content=PRE)
        self.assertUnknown(r.report(), f"Write {identity} of the receipt has no success evidence (pending)")
        r.result(identity, "done")                   # no is_error, no runtime metadata
        self.assertUnknown(r.report(), "(ambiguous)")

    def test_explicit_is_error_false_is_success_evidence(self):
        r = self.run_
        r.write(r.receipt, PRE)
        r.write(r.full, "id: x\n")
        identity = r.call("Write", file_path=str(r.receipt), content=PRE)
        r.result(identity, "done", is_error=False)
        self.assertEqual(r.report()["status"], "checked")

    def test_an_earlier_history_missing_from_the_transcripts_is_unknown(self):
        r = self.run_
        r.write(r.receipt, PRE)
        r.write(r.full, "id: x\n")
        first = list(r.events)                       # init, two calls, two results
        r.write(r.receipt, PRE)                      # an update of an existing file
        second = r.events[:1] + r.events[len(first):]
        r.receipt.write_text(PRE)
        block = ro.origin([r.transcript("t2.jsonl", second)], r.receipt, r.full)
        self.assertUnknown(block, "first observed Write of the receipt updated an existing file")
        self.assertIn("no successful Write of the full record", " ".join(block["reasons"]))
        both = ro.origin([r.transcript("t1.jsonl", first), r.transcript("t2.jsonl", second)],
                         r.receipt, r.full)
        self.assertEqual(both["status"], "checked", both["reasons"])
        self.assertEqual(both["boundaries"]["full_record_write"]["transcript"], 0)
        self.assertEqual(both["receipt"]["writes"], 2)
        self.assertEqual([t["lines"] for t in both["transcripts"]], [5, 3])

    def test_a_first_write_with_no_create_metadata_is_unknown(self):
        # A resumed run whose first transcript is not supplied, and whose
        # Write results carry `is_error: false` but none of the runtime's
        # create/update metadata: nothing says the history starts here (#3116).
        r = self.run_
        r.write(r.full, "id: x\n")
        r.write(r.receipt, PRE)
        first = len(r.events)
        for path, content in ((r.receipt, PRE), (r.full, "id: y\n")):
            identity = r.call("Write", file_path=str(path), content=content)
            r.result(identity, "done", is_error=False)
        r.receipt.write_text(PRE)
        block = ro.origin([r.transcript("t2.jsonl", r.events[:1] + r.events[first:])], r.receipt, r.full)
        self.assertUnknown(block, "first observed Write of the receipt carries no create/update metadata")
        self.assertIn("first observed Write of the full record carries no create/update metadata",
                      " ".join(block["reasons"]))

    def test_the_full_records_first_write_updating_a_file_is_unknown(self):
        r = self.run_
        r.write(r.full, "id: x\n")                 # the omitted first transcript
        first = len(r.events)
        r.write(r.receipt, PRE)
        r.write(r.full, "id: y\n")                 # an update, as the runtime reports it
        r.receipt.write_text(PRE)
        block = ro.origin([r.transcript("t2.jsonl", r.events[:1] + r.events[first:])], r.receipt, r.full)
        self.assertUnknown(block, "first observed Write of the full record updated an existing file")
        self.assertEqual(len(block["reasons"]), 1, block["reasons"])

    def test_a_full_record_write_without_success_evidence_before_the_draft_is_unknown(self):
        r = self.run_
        r.write(r.receipt, PRE)
        identity = r.call("Write", file_path=str(r.full), content="id: early\n")   # never answered
        r.write(r.full, "id: x\n")
        self.assertUnknown(r.report(), f"Write {identity} of the full record has no success evidence (pending)")

    def test_a_full_record_write_without_success_evidence_after_the_draft_is_not_a_reason(self):
        # The draft boundary is the first successful full Write; a later
        # unsettled one cannot move it.
        r = self.run_
        r.write(r.receipt, PRE)
        r.write(r.full, "id: x\n")
        r.call("Write", file_path=str(r.full), content="id: later\n")
        r.derive()
        self.assertEqual(r.report()["status"], "checked")

    def test_result_metadata_describes_only_a_single_result_event(self):
        # One user event answering two Writes: its metadata cannot say which
        # of them it describes, so neither has success evidence.
        r = self.run_
        r.write(r.receipt, PRE)
        full = r.call("Write", file_path=str(r.full), content="id: x\n")
        receipt = r.call("Write", file_path=str(r.receipt), content=PRE)
        r.events.append({"type": "user", "session_id": "s", "parent_tool_use_id": None,
                         "tool_use_result": {"type": "create", "filePath": str(r.full)},
                         "message": {"role": "user", "content": [
                             {"type": "tool_result", "tool_use_id": full, "content": "ok"},
                             {"type": "tool_result", "tool_use_id": receipt, "content": "ok"}]}})
        block = r.report()
        self.assertUnknown(block, f"Write {receipt} of the receipt has no success evidence (ambiguous)")
        self.assertIn(f"Write {full} of the full record has no success evidence (ambiguous)",
                      " ".join(block["reasons"]))

    def test_a_write_through_a_symlinked_directory_is_the_tracked_file(self):
        r = self.run_
        link = r.root / "linked"
        os.symlink(r.root / "data", link)
        via = lambda path: link / path.relative_to(r.root / "data")
        for path, content in ((r.receipt, PRE), (r.full, "id: x\n")):
            identity = r.call("Write", file_path=str(via(path)), content=content)
            r.result(identity, "ok", {"type": "create", "filePath": str(via(path))})
        r.receipt.write_text(PRE)
        block = ro.origin([r.transcript()], r.receipt, r.full)
        self.assertEqual(block["status"], "checked", block["reasons"])
        self.assertEqual((block["receipt"]["writes"], block["full"]["writes"]), (1, 1))

    def test_a_relative_write_with_no_working_directory_is_unknown(self):
        r = self.run_
        del r.events[0]["cwd"]                         # no init cwd and no event cwd
        for path, content in ((r.receipt, PRE), (r.full, "id: x\n")):
            rel = str(path.relative_to(r.root))
            identity = r.call("Write", file_path=rel, content=content)
            r.result(identity, "ok", {"type": "create", "filePath": rel})
        r.receipt.write_text(PRE)
        block = ro.origin([r.transcript()], r.receipt, r.full)
        self.assertUnknown(block, "names the receipt by a relative path with no working directory")


REL = "data/claudecode_direct_core/L/CHORUS_coverage_receipt.yaml"


class Unknown(Base):
    def _drafted(self):
        r = self.new_run()
        r.write(r.receipt, PRE)
        r.write(r.full, "id: x\n")
        return r

    def _complete(self):
        r = self._drafted()
        r.derive()
        return r

    def test_duplicate_tool_id_is_unknown_even_when_a_later_result_references_it(self):
        # Two calls under one id and a single result: which Write it settles
        # is ambiguous, so nothing is rebuilt from either (#2077).
        r = self.new_run()
        r.call("Write", identity="dup", file_path=str(r.receipt), content=PRE)
        r.call("Write", identity="dup", file_path=str(r.receipt), content=receipt_text(("c001", [("x", "other text")])))
        r.result("dup", "ok", {"type": "create", "filePath": str(r.receipt)})
        r.last_receipt = PRE
        r.write(r.full, "id: x\n")
        r.derive()
        self.assertUnknown(r.report(), "tool id(s) are duplicated: dup")

    def test_a_second_result_for_one_call_is_unknown(self):
        r = self._complete()
        r.result("toolu_001", "ok", {"type": "update"})
        self.assertUnknown(r.report(), "tool id(s) are duplicated: toolu_001")

    def test_a_result_with_no_earlier_call_is_unknown(self):
        r = self._complete()
        r.result("toolu_999", "ok", {"type": "update"})
        self.assertUnknown(r.report(), "tool result with no earlier call")

    def test_missing_transcript(self):
        r = self._complete()
        r.receipt.write_text(PRE)
        self.assertUnknown(ro.origin([r.root / "absent.jsonl"], r.receipt, r.full), "transcript 0 cannot be read")

    def test_unreadable_transcript(self):
        r = self._complete()
        path = r.transcript()
        path.write_bytes(path.read_bytes() + b"\xff\xfe\n")
        r.receipt.write_text(PRE)
        self.assertUnknown(ro.origin([path], r.receipt, r.full), "is not UTF-8")

    def test_malformed_line(self):
        for bad, why in (("{not json\n", "is not JSON"), ("[1, 2]\n", "not a JSON object"),
                         ("\n", "is blank"), ('{"type": "user"}', "is unterminated")):
            with self.subTest(why=why):
                r = self._complete()
                path = r.transcript()
                path.write_text(path.read_text() + bad)
                r.receipt.write_text(PRE)
                self.assertUnknown(ro.origin([path], r.receipt, r.full), why)

    # A change placed between the draft and the derive can reach the
    # derive-time snapshot; one issued after every snapshot is covered by
    # the final sha256 instead (AfterEverySnapshot).
    def test_an_edit_of_the_receipt_is_unknown(self):
        r = self._drafted()
        identity = r.call("Edit", file_path=str(r.receipt), old_string="a", new_string="b")
        r.result(identity, "ok", {"filePath": str(r.receipt)})
        r.derive()
        self.assertUnknown(r.report(), "may change the receipt other than by a Write")

    def test_a_refused_edit_is_listed_not_a_mutation(self):
        r = self._drafted()
        identity = r.call("Edit", file_path=str(r.receipt), old_string="a", new_string="b")
        r.result(identity, "Error: not allowed", is_error=True)
        r.derive()
        block = r.report()
        self.assertEqual(block["status"], "checked", block["reasons"])
        self.assertEqual(block["rejected_writes"][0]["tool"], "Edit")
        self.assertEqual(block["non_write_mutations"], [])

    def test_a_shell_mutation_of_the_receipt_is_unknown(self):
        for command in (f"cat >> {REL} <<'EOF'\n- id: c009\nEOF",
                        # one-line redirects: only the redirect rule sees them (#3117)
                        f"printf '%s' '- id: c009' >> {REL}",
                        f"echo '- id: c009' > {REL}",
                        f"cat /tmp/a.yaml 1> {REL}",
                        f"sed -i '' 's/a/b/' {REL}",
                        f"python -c \"open('{REL}', 'a').write('x')\"",
                        f"cd data && sed -i.bak s/a/b/ claudecode_direct_core/L/CHORUS_coverage_receipt.yaml",
                        f"grep x {REL}\nrm {REL}",
                        "echo 'unbalanced CHORUS_coverage_receipt.yaml",
                        # a d4d command whose --out names it, and one not known to be read-only
                        f"poetry run d4d receipts invert --receipt /tmp/r.yaml --full /tmp/f.yaml --out {REL}",
                        f"poetry run d4d receipts readdress --receipt {REL}"):
            with self.subTest(command=command):
                r = self._drafted()
                r.bash(command, ok=False)             # a failed command may still have written
                r.derive()
                block = r.report()
                self.assertUnknown(block, "Bash call")
                self.assertEqual([m["covered_by_final_sha256"] for m in block["non_write_mutations"]], [False])

    def test_a_shell_call_the_native_control_denied_is_listed_not_a_mutation(self):
        # The control denied it before it ran (#3185): like a refused Edit,
        # it is listed and changes nothing.
        r = self._drafted()
        denial = ro.NATIVE_DENIAL_PREFIX + "compound command"
        identity = r.bash(f"python3 -c \"import yaml; print(open('{REL}').read())\"", ok=False,
                          content=denial, metadata="Error: " + denial)
        r.derive()
        block = r.report()
        self.assertEqual(block["status"], "checked", block["reasons"])
        self.assertEqual(block["non_write_mutations"], [])
        self.assertEqual([(w["tool_use_id"], w["target"], w["tool"], w["rejection"]) for w in block["rejected_writes"]],
                         [(identity, "receipt", "Bash", "native_denial")])
        self.assertIn("· rejected Bash of the receipt (native_denial), transcript 0 line 6", ro.summary(block))

    def test_a_failure_that_only_quotes_the_denial_is_still_a_mutation(self):
        # The control's reason must open the result: a command that ran and
        # printed it failed like any other command.
        r = self._drafted()
        r.bash(f"sed -i '' 's/a/b/' {REL}", ok=False, content="Exit code 1\n" + ro.NATIVE_DENIAL_PREFIX + "x")
        r.derive()
        block = r.report()
        self.assertUnknown(block, "may change the receipt other than by a Write")
        self.assertEqual(block["rejected_writes"], [])

    def test_read_only_shell_commands_are_not_mutations(self):
        r = self._drafted()
        for command in (f"grep -n c001 {REL} 2>&1 | head -5",
                        f"sed -n '1,20p' {REL} > /dev/null",
                        f"wc -l {r.receipt}",
                        f"printf '%s\\n' {REL} >&2",
                        "cat data/ATTIC/CHORUS_coverage_receipt.yaml.bak > /tmp/x",
                        "poetry run d4d receipts check --label L --project CHORUS --strict",
                        f"poetry run d4d receipts invert --receipt {REL} --full data/x.yaml --out /tmp/claims.yaml",
                        f"poetry run d4d receipts invert --receipt {REL}"):
            r.bash(command)
        r.derive()
        block = r.report()
        self.assertEqual(block["status"], "checked", block["reasons"])
        self.assertEqual(block["non_write_mutations"], [])

    def test_a_core_derived_before_the_draft_is_unknown(self):
        r = self.run_
        r.write(r.receipt, PRE)
        identity = r.derive()
        r.write(r.full, "id: x\n")
        self.assertUnknown(r.report(), f"core derived ({identity}) before the first full-record Write")

    def test_a_shell_creation_of_the_full_record_before_its_write_is_unknown(self):
        r = self.run_
        r.write(r.receipt, PRE)
        r.bash("cp /tmp/draft.yaml data/claudecode_direct/L/CHORUS_d4d.yaml")
        r.write(r.full, "id: x\n")
        self.assertUnknown(r.report(), "may change the full record other than by a Write")

    def test_a_rebuilt_receipt_that_differs_from_disk_is_unknown(self):
        r = self._complete()
        r.receipt.write_text(PRE + "# edited after the run\n")
        self.assertUnknown(r.report(sync=False), "differs from the file on disk")

    def test_a_missing_receipt_file_is_unknown(self):
        r = self._complete()
        self.assertUnknown(ro.origin([r.transcript()], r.receipt, r.full), "the receipt cannot be read")

    def test_no_full_record_write_is_unknown(self):
        r = self.run_
        r.write(r.receipt, PRE)
        self.assertUnknown(r.report(), "no successful Write of the full record")

    def test_a_derive_without_boolean_success_evidence_is_unknown(self):
        r = self.run_
        r.write(r.receipt, PRE)
        r.write(r.full, "id: x\n")
        identity = r.call("Bash", command=f"poetry run d4d derive core --full {r.full} --out x.yaml")
        r.result(identity, "done", {"stdout": ""})
        self.assertUnknown(r.report(), "cannot be placed: its result is ambiguous")

    def test_an_error_whose_metadata_says_it_wrote_is_unknown(self):
        r = self._complete()
        identity = r.call("Write", file_path=str(r.receipt), content=PRE)
        r.result(identity, "error", {"type": "update", "filePath": str(r.receipt)}, is_error=True)
        self.assertUnknown(r.report(), "has no success evidence (ambiguous)")

    def test_a_derive_whose_full_is_a_variable_is_unknown(self):
        r = self.run_
        r.write(r.receipt, PRE)
        r.write(r.full, "id: x\n")
        r.bash('poetry run d4d derive core --full "$FULL" --out x.yaml')
        self.assertUnknown(r.report(), "its --full cannot be resolved")

    def test_a_pre_draft_receipt_that_does_not_parse_is_unknown(self):
        r = self.run_
        r.write(r.receipt, f'chunks:\n- id: c001\n  snippet: "{SECRET}\n  : : bad')
        r.write(r.full, "id: x\n")
        r.write(r.receipt, PRE)
        block = r.report()
        self.assertUnknown(block, "(pre_draft) is not a receipt")
        self.assertNotIn(SECRET, json.dumps(block))


class ShellComments(Base):
    """A `#` starts a comment only at the start of a word, as bash reads it,
    never inside a word or a quote (#3184)."""

    def _before_draft(self, command):
        """receipt, the call under test, draft, derive: a change it made
        reaches the pre-draft snapshot."""
        r = self.new_run()
        r.write(r.receipt, PRE)
        r.bash(command)
        r.write(r.full, "id: x\n")
        r.derive()
        return r.report()

    def test_a_hash_inside_a_word_hides_no_shell_edit_of_the_receipt(self):
        for command in (f"sed -i '' -e /OT2OD032701/d -e s/#//g {REL}",
                        f"echo a#b >> {REL}",
                        f"printf '%s' x#y 1> {REL}",
                        f"echo '#' a#b | tee {REL}"):
            with self.subTest(command=command):
                block = self._before_draft(command)
                self.assertUnknown(block, "may change the receipt other than by a Write")

    def test_a_comment_at_the_start_of_a_word_is_not_part_of_the_command(self):
        for command in (f"cat {REL} # > {REL}",
                        f"sed -n '1,5p' {REL}  # don't edit it here",
                        f"wc -l {REL};# rm {REL}",
                        f"echo $# {REL}"):
            with self.subTest(command=command):
                block = self._before_draft(command)
                self.assertEqual(block["status"], "checked", block["reasons"])
                self.assertEqual(block["non_write_mutations"], [])

    def test_strip_comments_reads_quotes_and_words_as_bash_does(self):
        cases = {"a#b 'c #d' \"e #f\" g # h": "a#b 'c #d' \"e #f\" g ",
                 "x\\ #y": "x\\ #y", "$'q\\' #r' s #t": "$'q\\' #r' s ", "'p\\' #k": "'p\\' ",
                 "\"m\\\" #n\" #o": "\"m\\\" #n\" ",
                 "a;#b\nc # d\ne": "a;\nc \ne", "#only": "", "u=#v ${#w} $#": "u=#v ${#w} $#",
                 "'open #": "'open #"}
        for command, expected in cases.items():
            with self.subTest(command=command):
                self.assertEqual(ro._strip_comments(command), expected)


class SedWrites(Base):
    """sed without an in-place flag still writes a file through its `w` and
    `W` commands, the `s///w` flag, and runs one through `e`; a script from
    a file cannot be read (#3220)."""

    def _before_draft(self, command):
        r = self.new_run()
        r.write(r.receipt, PRE)
        r.bash(command)
        r.write(r.full, "id: x\n")
        r.derive()
        return r.report()

    def test_a_sed_script_that_writes_the_receipt_is_unknown(self):
        for command in (f"sed -n 'w {REL}' /dev/null",
                        f"sed -n 's/x/y/w {REL}' other.txt",
                        f"sed -n -e '1p' -e 'W {REL}' other.txt",
                        f"sed -ne '$w {REL}' other.txt",
                        f"sed --expression='/a/w {REL}' other.txt",
                        f"sed -n 'b end; w {REL}' other.txt",
                        f"sed 's/.*/cp x {REL}/e' other.txt",
                        f"sed -f fix.sed {REL}",
                        f"sed p {REL} -i ''"):
            with self.subTest(command=command):
                block = self._before_draft(command)
                self.assertUnknown(block, "may change the receipt other than by a Write")

    def test_a_sed_script_that_only_prints_is_read_only(self):
        for command in (f"sed -n '1,20p' {REL}",
                        f"sed -n '/c001/,+3p' {REL}",
                        f"sed -n '1,5p;/window/p' {REL}",
                        f"sed -E 's|a/b|c|g; y/ab/cd/' {REL}",
                        f"sed '$!N;P;D' {REL}",
                        f"sed -n -e /OT2OD/p -e 's/#//gp' {REL}"):
            with self.subTest(command=command):
                block = self._before_draft(command)
                self.assertEqual(block["status"], "checked", block["reasons"])
                self.assertEqual(block["non_write_mutations"], [])


class RipgrepPreprocessor(Base):
    """`rg --pre CMD` runs CMD on every file it searches, so an `rg` that
    names the receipt and sets a preprocessor can delete or rewrite it
    (#3256). Such a call is not read-only; plain searches still are."""

    def _before_draft(self, command):
        r = self.new_run()
        r.write(r.receipt, PRE)
        r.bash(command)
        r.write(r.full, "id: x\n")
        r.write(r.receipt, PRE)
        r.derive()
        return r.report()

    def test_a_preprocessor_on_the_receipt_is_unknown(self):
        for command in (f"rg --pre rm x {REL}",
                        f"rg --pre=rm x {REL}",
                        f"rg -n --pre-glob '*.yaml' --pre ./fix.sh x {REL}",
                        f"rg x {REL} --pre rm",
                        f"/opt/homebrew/bin/rg --pre rm x {REL}",
                        f"RIPGREP_CONFIG_PATH=rg.cfg rg x {REL}",
                        f"LC_ALL=C RIPGREP_CONFIG_PATH=rg.cfg rg x {REL}"):
            with self.subTest(command=command):
                block = self._before_draft(command)
                self.assertUnknown(block, "may change the receipt other than by a Write")
                self.assertEqual(len(block["non_write_mutations"]), 1)

    def test_a_plain_search_of_the_receipt_is_read_only(self):
        for command in (f"rg -n c001 {REL}",
                        f"rg -z --pre-glob '*.gz' x {REL}",
                        f"rg --no-pre x {REL}",
                        f"rg -e --prefix {REL}",
                        f"LC_ALL=C rg x {REL}"):
            with self.subTest(command=command):
                block = self._before_draft(command)
                self.assertEqual(block["status"], "checked", block["reasons"])
                self.assertEqual(block["non_write_mutations"], [])

    def test_rg_reads_only(self):
        cases = {("rg", "x", "R"): True, ("rg", "--pre", "rm", "x", "R"): False,
                 ("rg", "--pre=rm", "x", "R"): False, ("rg", "--pre-glob=*.gz", "x", "R"): True,
                 ("RIPGREP_CONFIG_PATH=c", "rg", "x"): False, ("A=1", "rg", "x"): True,
                 ("poetry", "run", "rg", "--pre", "rm", "R"): False,
                 ("rg", "x", "RIPGREP_CONFIG_PATH=c"): True}
        for segment, expected in cases.items():
            with self.subTest(segment=segment):
                self.assertIs(ro._rg_reads_only(list(segment)), expected)


class CommandSubstitution(Base):
    """A command inside backticks, a double-quoted `$(...)` or a process
    substitution is a word of the outer command to the tokeniser, so the
    outer `echo`/`cat` looked read-only while the inner one wrote the
    receipt (#3240). Such a command is never known to be read-only."""

    def _before_draft(self, command):
        r = self.new_run()
        r.write(r.receipt, PRE)
        r.bash(command)
        r.write(r.full, "id: x\n")
        r.derive()
        return r.report()

    def test_a_substituted_write_of_the_receipt_is_unknown(self):
        for command in (f"echo `sed -i '' -e /X/d {REL}`",
                        f"echo \"$(sed -i '' -e /X/d {REL})\"",
                        f"cat <(rm {REL})",
                        f"cat {REL} >(tee {REL})",
                        f"echo \"x `rm {REL}`\"",
                        f"echo $(sed -i d {REL})"):
            with self.subTest(command=command):
                block = self._before_draft(command)
                self.assertUnknown(block, "may change the receipt other than by a Write")
                self.assertEqual(len(block["non_write_mutations"]), 1)

    def test_a_quoted_or_escaped_substitution_is_text(self):
        for command in (f"echo '$(rm x)' {REL}",
                        f"echo '`rm x`' {REL}",
                        f"echo \\$\\(rm x\\) {REL}",
                        f"echo \"\\`rm x\\`\" {REL}",
                        f"grep -c '<(' {REL}",
                        f"echo \"<(x)\" {REL}"):
            with self.subTest(command=command):
                block = self._before_draft(command)
                self.assertEqual(block["status"], "checked", block["reasons"])
                self.assertEqual(block["non_write_mutations"], [])

    def test_substitutes_reads_quotes_as_bash_does(self):
        cases = {"echo `x`": True, 'echo "$(x)"': True, "echo $(x)": True, "cat <(x)": True,
                 "tee >(x)": True, "echo $((1+2))": True, 'echo "a `b` c"': True,
                 "echo '$(x)'": False, "echo '`x`'": False, "echo \\$(x)": False,
                 'echo "\\`x\\`"': False, 'echo "<(x)"': False, "echo $'\\'$(x)'": False,
                 "echo $'a'$(x)": True, 'echo "a" <(x)': True, "cat a < (b)": False, "echo 'a' \"b\" c": False}
        for command, expected in cases.items():
            with self.subTest(command=command):
                self.assertIs(ro._substitutes(command), expected)


class NonChecks(unittest.TestCase):
    def test_the_unattributable_shell_write_names_every_unnamed_route(self):
        # A write that never names the receipt is not seen at all; the stated
        # exception must cover it, not only a glob or variable (#3221).
        text = " ".join(ro.NON_CHECKS)
        for route in ("glob or variable", "a program or script that writes it", "python fix.py",
                      "a command on a directory that holds it", "git checkout -- DIR", "rm -r DIR"):
            self.assertIn(route, text)
        self.assertIn("does not name it literally", ro.__doc__)

    def test_a_ripgrep_config_preprocessor_is_named(self):
        # #3256: a `--pre` from a config file named outside the command is
        # not seen; the exception must say so.
        text = " ".join(ro.NON_CHECKS)
        self.assertIn("ripgrep preprocessor set in a config file", text)
        self.assertIn("RIPGREP_CONFIG_PATH", text)
        self.assertIn("ripgrep preprocessor set in a config file from outside the command",
                      " ".join(ro.__doc__.split()))


#: The playbook's recorder step (d4d-full-core, "Provenance record"): its
#: `--phase` JSON and the registered line's `--render-spec-json` both name
#: the receipt.
RECORD_LINE = ("poetry run d4d provenance record --project CHORUS --method claudecode_direct --label L "
               "--phase '{\"name\":\"full\",\"artifacts\":[\"CHORUS_d4d.yaml\",\"CHORUS_coverage_receipt.yaml\"]}' "
               "--render-spec-json '{\"outputs\":{\"receipt\":\"" + REL + "\"}}' --receipt-expected")


class AfterEverySnapshot(Base):
    """A non-Write change of the receipt issued once the draft, the last
    receipt Write and the derive boundary have all returned can reach only
    the final receipt, which the sha256 against the file on disk covers
    (#3112). Anything earlier stays a reason."""

    def _complete(self):
        r = self.run_
        r.write(r.receipt, PRE)
        r.write(r.full, "id: x\n")
        r.derive()
        return r

    def test_the_playbooks_recorder_after_the_run_is_checked(self):
        r = self._complete()
        r.bash(RECORD_LINE, ok=False)                 # the 09-22 direct canary's call failed
        r.bash(RECORD_LINE.replace("poetry run d4d", "/venv/bin/python3.13 -m data_sheets_schema.cli"))
        block = r.report()
        self.assertEqual(block["status"], "checked", block["reasons"])
        self.assertEqual(block["non_write_mutations"], [])     # `provenance record` writes neither file

    def test_the_recorder_before_a_back_port_is_not_a_change(self):
        r = self._complete()
        r.bash(RECORD_LINE)
        r.write(r.receipt, receipt_text(("c001", [("title", "The CHORUS dataset")]),
                                        ("c003", [("license", "CC BY 4.0 license")])))
        block = r.report()
        self.assertEqual(block["status"], "checked", block["reasons"])
        self.assertEqual(block["non_write_mutations"], [])

    def test_a_change_after_every_snapshot_is_listed_and_covered(self):
        r = self._complete()
        for command in (f"git add {REL}", f"sed -i '' 's/zzz/zzz/' {REL}"):
            r.bash(command)
        identity = r.call("Edit", file_path=str(r.receipt), old_string="zzz", new_string="zzz")
        r.result(identity, "ok", {"filePath": str(r.receipt)})
        block = r.report()
        self.assertEqual(block["status"], "checked", block["reasons"])
        self.assertEqual([(m["tool"], m["covered_by_final_sha256"]) for m in block["non_write_mutations"]],
                         [("Bash", True), ("Bash", True), ("Edit", True)])
        self.assertTrue(all(not k.startswith("_") for m in block["non_write_mutations"] for k in m))

    def test_a_covered_change_that_altered_the_receipt_is_caught_by_the_sha256(self):
        r = self._complete()
        r.bash(f"printf '# appended' >> {REL}")
        r.receipt.write_text(PRE + "# appended")
        self.assertUnknown(r.report(sync=False), "differs from the file on disk")

    def test_a_change_before_the_derive_is_not_covered(self):
        r = self.run_
        r.write(r.receipt, PRE)
        r.write(r.full, "id: x\n")
        r.bash(f"git add {REL}")
        r.derive()
        block = r.report()
        self.assertUnknown(block, "may change the receipt other than by a Write")
        self.assertEqual(block["non_write_mutations"][0]["covered_by_final_sha256"], False)

    def test_a_change_before_the_last_receipt_write_is_not_covered(self):
        r = self._complete()
        r.bash(f"git add {REL}")
        r.write(r.receipt, PRE)
        self.assertUnknown(r.report(), "may change the receipt other than by a Write")

    def test_a_change_issued_before_the_derive_returned_is_not_covered(self):
        # Two calls in flight: the change may have run before the derive did.
        r = self.run_
        r.write(r.receipt, PRE)
        r.write(r.full, "id: x\n")
        derive = r.call("Bash", command=r.derive_command(), description="x")
        change = r.call("Bash", command=f"git add {REL}", description="x")
        for identity in (derive, change):
            r.result(identity, "out", {"stdout": "", "stderr": "", "interrupted": False}, is_error=False)
        block = r.report()
        self.assertEqual(block["derive_core_attempts"][0]["outcome"], "succeeded")
        self.assertUnknown(block, f"Bash call {change}")
        self.assertEqual(block["non_write_mutations"][0]["covered_by_final_sha256"], False)

    def test_a_change_before_the_draft_is_not_covered_without_a_derive(self):
        r = self.run_
        r.write(r.receipt, PRE)
        r.bash(f"git add {REL}")
        r.write(r.full, "id: x\n")
        self.assertUnknown(r.report(), "may change the receipt other than by a Write")

    def test_without_a_derive_a_change_after_the_draft_and_last_write_is_covered(self):
        r = self.run_
        r.write(r.receipt, PRE)
        r.write(r.full, "id: x\n")
        r.bash(f"git add {REL}")
        block = r.report()
        self.assertEqual(block["status"], "checked", block["reasons"])
        self.assertTrue(block["non_write_mutations"][0]["covered_by_final_sha256"])


class DeriveStatus(Base):
    """A `derive core` is the Phase 1 / Phase 3 boundary only where its call's
    result carries the derive's own status (#3113)."""

    ADDED = receipt_text(("c001", [("title", "The CHORUS dataset"), ("funders[0].grant_id", "OT2OD032701")]),
                         ("c002", [("description", "a multimodal collection")]),
                         ("c003", [("license", "CC BY 4.0 license")]))

    def _around(self, first, **result):
        """receipt, draft, the derive call under test, a receipt entry added,
        then a bare successful derive."""
        r = self.run_
        r.write(r.receipt, PRE)
        r.write(r.full, "id: x\n")
        identity = r.bash(first(r), **result)
        r.write(r.receipt, self.ADDED)
        r.derive()
        return identity, r.report()

    def test_a_piped_derive_is_ambiguous_whatever_the_pipeline_returned(self):
        for ok in (True, False):
            with self.subTest(ok=ok):
                self.run_ = self.new_run()
                identity, block = self._around(lambda r: r.derive_command() + " 2>&1 | tail -5", ok=ok)
                self.assertUnknown(block, f"derive core {identity} cannot be placed: the call ")
                self.assertIn("not the derive's own (none", " ".join(block["reasons"]))

    def test_a_failed_derive_followed_by_and_is_ambiguous(self):
        # `derive && receipts check --strict`: the check may be what failed.
        identity, block = self._around(
            lambda r: r.derive_command() + " && poetry run d4d receipts check --label L --project CHORUS --strict",
            ok=False)
        self.assertUnknown(block, f"derive core {identity} cannot be placed: the call failed")
        self.assertIn("(and_chain", " ".join(block["reasons"]))

    def test_a_successful_derive_followed_by_and_is_the_boundary(self):
        identity, block = self._around(
            lambda r: r.derive_command() + " && poetry run d4d receipts check --label L --project CHORUS")
        self.assertEqual(block["status"], "checked", block["reasons"])
        self.assertEqual(block["boundaries"]["derive_core"]["tool_use_id"], identity)
        self.assertEqual(block["boundaries"]["derive_core"]["status_basis"], "and_chain")
        self.assertEqual(block["origin"]["phase3_backport"], 1)

    def test_a_derive_last_after_cd_carries_its_own_status(self):
        for ok, boundary_is_first in ((True, True), (False, False)):
            with self.subTest(ok=ok):
                self.run_ = self.new_run()
                identity, block = self._around(lambda r: f"cd {r.root} && " + r.derive_command(), ok=ok)
                self.assertEqual(block["status"], "checked", block["reasons"])
                attempt = block["derive_core_attempts"][0]
                self.assertEqual((attempt["status_basis"], attempt["outcome"]),
                                 ("command", "succeeded" if ok else "failed"))
                self.assertEqual(block["boundaries"]["derive_core"]["tool_use_id"] == identity, boundary_is_first)
                self.assertEqual(block["origin"]["phase3_backport" if ok else "phase1_correction"], 1)

    def test_a_compound_derive_the_native_control_denied_never_ran(self):
        identity, block = self._around(
            lambda r: r.derive_command() + " 2>&1 | tail -5", ok=False,
            content=ro.NATIVE_DENIAL_PREFIX + "compound command", metadata="Error: " + ro.NATIVE_DENIAL_PREFIX)
        self.assertEqual(block["status"], "checked", block["reasons"])
        self.assertEqual(block["derive_core_attempts"][0]["outcome"], "failed")
        self.assertNotEqual(block["boundaries"]["derive_core"]["tool_use_id"], identity)
        self.assertEqual(block["origin"]["phase1_correction"], 1)

    def test_a_backgrounded_derive_is_ambiguous(self):
        identity, block = self._around(lambda r: r.derive_command(),
                                       metadata={"stdout": "", "stderr": "", "interrupted": False,
                                                 "backgroundTaskId": "bg1"})
        self.assertUnknown(block, f"derive core {identity} cannot be placed: its result is ambiguous")

    def test_an_interrupted_or_non_zero_derive_is_not_the_boundary(self):
        for metadata in ({"stdout": "", "stderr": "", "interrupted": True},
                         {"stdout": "", "stderr": "", "interrupted": False, "exitCode": 1},
                         {"stdout": "", "stderr": "", "interrupted": False, "exit_code": 2}):
            with self.subTest(metadata=metadata):
                self.run_ = self.new_run()
                identity, block = self._around(lambda r: r.derive_command(), metadata=metadata)
                self.assertEqual(block["status"], "checked", block["reasons"])
                self.assertEqual(block["derive_core_attempts"][0]["outcome"], "failed")
                self.assertNotEqual(block["boundaries"]["derive_core"]["tool_use_id"], identity)
                self.assertEqual(block["origin"]["phase1_correction"], 1)

    def test_a_derive_after_or_or_before_another_command_is_ambiguous(self):
        for command in (lambda r: "false || " + r.derive_command(),
                        lambda r: r.derive_command() + " ; echo done",
                        lambda r: r.derive_command() + " &",
                        lambda r: r.derive_command() + "\necho done",
                        lambda r: "echo start\n" + r.derive_command()):
            with self.subTest(command=command(self.new_run())[-20:]):
                self.run_ = self.new_run()
                identity, block = self._around(command)
                self.assertUnknown(block, f"derive core {identity} cannot be placed")

    def test_status_basis(self):
        cases = {"d4d derive core --full F": "command", "d4d derive core --full F ;": "command",
                 "cd x && d4d derive core --full F": "command", "a; d4d derive core --full F": "command",
                 "d4d derive core --full F && d4d receipts check": "and_chain",
                 "a ; d4d derive core --full F && b && c": "and_chain",
                 "d4d derive core --full F && b ; c": "none", "d4d derive core --full F | tail": "none",
                 "a | d4d derive core --full F": "none", "(d4d derive core --full F)": "none",
                 "a || d4d derive core --full F": "none", "d4d derive core --full F &": "none",
                 # a `#` inside a word hides nothing after it; one starting a word does (#3184)
                 "d4d derive core --full F --tag a#b | tail": "none",
                 "d4d derive core --full F # then | tail ; echo": "command"}
        for command, basis in cases.items():
            with self.subTest(command=command):
                segments, joins, leading = ro._layout(ro._tokens(command))
                index = next(i for i, s in enumerate(segments) if s[:3] == ["d4d", "derive", "core"])
                self.assertEqual(ro._status_basis(index, joins, leading, False), basis)
        segments, joins, leading = ro._layout(ro._tokens("d4d derive core --full F"))
        self.assertEqual(ro._status_basis(0, joins, leading, True), "none")


class Boundaries(Base):
    """The draft is the first successful full-record Write, and every
    registered spelling of `derive core` is seen; a regression in either
    would leave the status `checked` with the wrong classification (#3187)."""

    C003 = receipt_text(("c001", [("title", "The CHORUS dataset"), ("funders[0].grant_id", "OT2OD032701")]),
                        ("c002", [("description", "a multimodal collection")]),
                        ("c003", [("license", "CC BY 4.0 license")]))
    C004 = receipt_text(("c001", [("title", "The CHORUS dataset"), ("funders[0].grant_id", "OT2OD032701")]),
                        ("c002", [("description", "a multimodal collection")]),
                        ("c003", [("license", "CC BY 4.0 license")]),
                        ("c004", [("version", "release 2.0")]))

    def test_the_draft_is_the_first_successful_full_record_write_not_the_last(self):
        r = self.run_
        r.write(r.receipt, PRE)
        draft = r.write(r.full, "id: x\n")
        r.write(r.receipt, self.C003)
        r.write(r.full, "id: x\ntitle: corrected\n")          # a later correction of the record
        r.derive()
        block = r.report()
        self.assertEqual(block["status"], "checked", block["reasons"])
        self.assertEqual(block["full"]["writes"], 2)
        self.assertEqual(block["boundaries"]["full_record_write"]["tool_use_id"], draft)
        self.assertEqual(block["origin"], {"contemporaneous": 3, "phase1_correction": 1, "phase3_backport": 0})

    def test_a_derive_with_no_result_cannot_be_placed(self):
        # A run killed mid-derive: the call has no result, in one transcript
        # or across a killed-and-resumed pair.
        r = self.run_
        r.write(r.receipt, PRE)
        r.write(r.full, "id: x\n")
        identity = r.call("Bash", command=r.derive_command(), description="x")
        split = len(r.events)
        r.write(r.receipt, self.C003)
        self.assertUnknown(r.report(), f"derive core {identity} cannot be placed: its result is pending")
        resumed = ro.origin([r.transcript("t1.jsonl", r.events[:split]),
                             r.transcript("t2.jsonl", r.events[:1] + r.events[split:])], r.receipt, r.full)
        self.assertUnknown(resumed, f"derive core {identity} cannot be placed: its result is pending")

    def test_every_registered_derive_spelling_is_the_boundary(self):
        full = "data/claudecode_direct/L/CHORUS_d4d.yaml"
        out = "--out data/claudecode_direct_core/L/CHORUS_d4d_core.yaml"
        for spelling in (f"D4D_PROFILE=bridge2ai poetry run d4d derive core --full {full} {out}",
                         f"cd data && poetry run d4d derive core --full claudecode_direct/L/CHORUS_d4d.yaml {out}",
                         f"poetry run d4d derive core --full={full} {out}",
                         f"poetry run d4d --manifest data/preprocessed/source_manifest.yaml derive core "
                         f"--full {full} {out}",
                         f"poetry run d4d --manifest=m.yaml derive core --full {full} {out}"):
            with self.subTest(spelling=spelling):
                r = self.new_run()
                r.write(r.receipt, PRE)
                r.write(r.full, "id: x\n")
                r.write(r.receipt, self.C003)
                identity = r.bash(spelling)
                r.write(r.receipt, self.C004)
                block = r.report()
                self.assertEqual(block["status"], "checked", block["reasons"])
                self.assertEqual(block["boundaries"]["derive_core"]["tool_use_id"], identity)
                self.assertEqual(block["origin"], {"contemporaneous": 3, "phase1_correction": 1,
                                                   "phase3_backport": 1})

    def _derived(self, spelling):
        r = self.new_run()
        r.write(r.receipt, PRE)
        r.write(r.full, "id: x\n")
        r.write(r.receipt, self.C003)
        identity = r.bash(spelling)
        r.write(r.receipt, self.C004)
        return identity, r.report()

    def test_pushd_moves_the_directory_a_derive_resolves_against(self):
        # #3222: pushd is a cd for `--full`, and popd returns.
        out = "--out data/claudecode_direct_core/L/CHORUS_d4d_core.yaml"
        for spelling in (f"pushd data && poetry run d4d derive core --full claudecode_direct/L/CHORUS_d4d.yaml",
                         f"pushd data/claudecode_direct && d4d derive core --full L/CHORUS_d4d.yaml",
                         f"pushd /elsewhere && popd && poetry run d4d derive core "
                         f"--full data/claudecode_direct/L/CHORUS_d4d.yaml {out}"):
            with self.subTest(spelling=spelling):
                identity, block = self._derived(spelling)
                self.assertEqual(block["status"], "checked", block["reasons"])
                self.assertEqual(block["boundaries"]["derive_core"]["tool_use_id"], identity)
                self.assertEqual(block["origin"], {"contemporaneous": 3, "phase1_correction": 1,
                                                   "phase3_backport": 1})

    def test_a_derive_after_pushd_elsewhere_is_not_the_boundary(self):
        identity, block = self._derived("pushd /elsewhere && poetry run d4d derive core "
                                        "--full data/claudecode_direct/L/CHORUS_d4d.yaml")
        # Another record derived: no boundary, both later snippets Phase 1.
        self.assertEqual(block["status"], "checked", block["reasons"])
        self.assertIsNone(block["boundaries"]["derive_core"])
        self.assertEqual(block["origin"], {"contemporaneous": 3, "phase1_correction": 2,
                                           "phase3_backport": 0})

    def test_popd_with_nothing_pushed_leaves_no_known_directory(self):
        _, block = self._derived("popd && poetry run d4d derive core --full data/claudecode_direct/L/CHORUS_d4d.yaml")
        self.assertUnknown(block, "its --full cannot be resolved")

    def test_a_directory_that_is_not_a_name_leaves_no_known_directory(self):
        # #3257: `cd -` returns to OLDPWD and `pushd +N`/`-N` rotates the
        # stack; neither is a directory named `-` or `+N`.
        full = "data/claudecode_direct/L/CHORUS_d4d.yaml"
        for spelling in (f"cd data && cd - && poetry run d4d derive core --full {full}",
                         f"pushd data && pushd +1 && poetry run d4d derive core --full {full}",
                         f"pushd data && pushd -0 && poetry run d4d derive core --full {full}",
                         f"cd +1 && poetry run d4d derive core --full {full}",
                         f"cd -P data && poetry run d4d derive core --full claudecode_direct/L/CHORUS_d4d.yaml"):
            with self.subTest(spelling=spelling):
                _, block = self._derived(spelling)
                self.assertUnknown(block, "its --full cannot be resolved")

    def test_an_absolute_full_after_cd_minus_is_still_the_boundary(self):
        # With no known directory an absolute --full still resolves.
        r = self.run_
        r.write(r.receipt, PRE)
        r.write(r.full, "id: x\n")
        r.write(r.receipt, self.C003)
        identity = r.bash(f"cd data && cd - && poetry run d4d derive core --full {r.full}")
        r.write(r.receipt, self.C004)
        block = r.report()
        self.assertEqual(block["status"], "checked", block["reasons"])
        self.assertEqual(block["boundaries"]["derive_core"]["tool_use_id"], identity)
        self.assertEqual(block["origin"], {"contemporaneous": 3, "phase1_correction": 1,
                                           "phase3_backport": 1})

    def test_a_read_of_the_receipt_is_not_a_change(self):
        r = self.run_
        r.write(r.receipt, PRE)
        r.write(r.full, "id: x\n")
        identity = r.call("Read", file_path=str(r.receipt))
        r.result(identity, "1\tbundle_md5: ...", {"type": "text", "file": {"filePath": str(r.receipt)}})
        r.derive()
        block = r.report()
        self.assertEqual(block["status"], "checked", block["reasons"])
        self.assertEqual(block["non_write_mutations"], [])

    def test_a_shell_change_of_the_full_record_after_the_draft_is_listed_not_a_reason(self):
        # The draft boundary is already placed; later changes to the record
        # cannot move it (each owner-step run carries 15 to 21 such calls).
        r = self.run_
        r.write(r.receipt, PRE)
        r.write(r.full, "id: x\n")
        identity = r.bash("sed -i '' 's/x/y/' data/claudecode_direct/L/CHORUS_d4d.yaml")
        r.derive()
        block = r.report()
        self.assertEqual(block["status"], "checked", block["reasons"])
        self.assertEqual([(m["tool_use_id"], m["target"]) for m in block["non_write_mutations"]],
                         [(identity, "full")])


class InFlight(Base):
    """The snapshots are chosen by the order calls were issued, which is the
    order they took effect only where no two relevant calls were in flight
    together (#3268). A receipt Write in flight with another receipt Write,
    the first full-record Write or the derive boundary cannot be placed."""

    ADDED = receipt_text(("c001", [("title", "The CHORUS dataset"), ("funders[0].grant_id", "OT2OD032701")]),
                         ("c002", [("description", "a multimodal collection")]),
                         ("c003", [("license", "CC BY 4.0 license")]))

    @staticmethod
    def start(r, path, content):
        return r.call("Write", file_path=str(path), content=content)

    @staticmethod
    def finish(r, identity, path, content):
        kind = "update" if path in r.created else "create"
        r.created.add(path)
        r.result(identity, f"File written at: {path}", {"type": kind, "filePath": str(path), "content": content})
        if path == r.receipt:
            r.last_receipt = content

    def test_a_receipt_write_returning_after_the_draft_was_issued_is_unknown(self):
        # The reviewer's case: issued before the draft Write, returned after
        # it, in either order of the two results.
        for receipt_first in (True, False):
            with self.subTest(receipt_result_first=receipt_first):
                r = self.new_run()
                r.write(r.receipt, PRE)
                update = self.start(r, r.receipt, self.ADDED)
                draft = self.start(r, r.full, "id: x\n")
                steps = [(update, r.receipt, self.ADDED), (draft, r.full, "id: x\n")]
                for identity, path, content in (steps if receipt_first else steps[::-1]):
                    self.finish(r, identity, path, content)
                r.derive()
                self.assertUnknown(r.report(), f"receipt Write {update} was in flight with the first "
                                               f"full-record Write ({draft})")

    def test_two_receipt_writes_in_flight_together_are_unknown(self):
        r = self.run_
        a = self.start(r, r.receipt, PRE)
        b = self.start(r, r.receipt, self.ADDED)
        self.finish(r, b, r.receipt, self.ADDED)
        self.finish(r, a, r.receipt, PRE)
        r.last_receipt = self.ADDED                    # the disk agrees with the later-issued one
        r.write(r.full, "id: x\n")
        r.derive()
        self.assertUnknown(r.report(), f"receipt Writes {a} and {b} were in flight together")

    def test_a_receipt_write_in_flight_with_the_derive_is_unknown(self):
        r = self.run_
        r.write(r.receipt, PRE)
        r.write(r.full, "id: x\n")
        derive = r.call("Bash", command=r.derive_command(), description="x")
        update = self.start(r, r.receipt, self.ADDED)
        r.result(derive, "out", {"stdout": "", "stderr": "", "interrupted": False}, is_error=False)
        self.finish(r, update, r.receipt, self.ADDED)
        self.assertUnknown(r.report(), f"receipt Write {update} was in flight with the derive core boundary")

    def test_a_derive_issued_before_the_draft_returned_is_unknown(self):
        r = self.run_
        r.write(r.receipt, PRE)
        draft = self.start(r, r.full, "id: x\n")
        derive = r.call("Bash", command=r.derive_command(), description="x")
        self.finish(r, draft, r.full, "id: x\n")
        r.result(derive, "out", {"stdout": "", "stderr": "", "interrupted": False}, is_error=False)
        r.write(r.receipt, self.ADDED)
        self.assertUnknown(r.report(), f"core derived ({derive}) before the first full-record Write had returned")

    def test_calls_in_flight_that_cannot_reorder_a_snapshot_are_checked(self):
        # A receipt Write in flight with a read, or with a later correction of
        # the full record (not the draft), moves no snapshot.
        r = self.run_
        r.write(r.receipt, PRE)
        r.write(r.full, "id: x\n")
        update = self.start(r, r.receipt, self.ADDED)
        read = r.call("Read", file_path=str(r.full))
        fix = self.start(r, r.full, "id: x\ntitle: y\n")
        r.result(read, "id: x", {"type": "text"})
        self.finish(r, fix, r.full, "id: x\ntitle: y\n")
        self.finish(r, update, r.receipt, self.ADDED)
        r.derive()
        block = r.report()
        self.assertEqual(block["status"], "checked", block["reasons"])
        self.assertEqual(block["origin"], {"contemporaneous": 3, "phase1_correction": 1, "phase3_backport": 0})


class UnestablishedDirectory(Base):
    """A `cd`, `pushd` or `popd` moves the directory a later part's
    relative `--full` resolves against only where that part runs only if
    the change ran and succeeded (#3268). Bash runs `cd /missing; derive`
    in the call's own directory, so resolving the `--full` under
    `/missing` dropped a real derive of the record as another record's."""

    C003 = Boundaries.C003
    C004 = Boundaries.C004
    FULL = "data/claudecode_direct/L/CHORUS_d4d.yaml"

    def _derived(self, spelling):
        return Boundaries._derived(self, spelling)

    def test_a_directory_change_that_may_not_have_happened_leaves_no_known_directory(self):
        out = "--out data/claudecode_direct_core/L/CHORUS_d4d_core.yaml"
        for spelling in (f"cd /unavailable; d4d derive core --full {self.FULL} {out}",
                         f"false && cd /elsewhere; poetry run d4d derive core --full {self.FULL}",
                         f"cd /elsewhere || true && poetry run d4d derive core --full {self.FULL}",
                         f"true || cd /elsewhere && poetry run d4d derive core --full {self.FULL}",
                         f"(cd /elsewhere) && poetry run d4d derive core --full {self.FULL}",
                         f"cd /elsewhere & poetry run d4d derive core --full {self.FULL}",
                         f"pushd /elsewhere; popd; poetry run d4d derive core --full {self.FULL}",
                         f"cd data && echo a ; poetry run d4d derive core --full claudecode_direct/L/CHORUS_d4d.yaml",
                         f"cd /elsewhere\npoetry run d4d derive core --full {self.FULL}",
                         "cd data\npoetry run d4d derive core --full claudecode_direct/L/CHORUS_d4d.yaml"):
            with self.subTest(spelling=spelling):
                identity, block = self._derived(spelling)
                # Not dropped as another record's: the derive cannot be placed
                # (by its --full, or also by its status where that is not its own).
                self.assertUnknown(block, f"derive core {identity} cannot be placed")
                self.assertIsNone(block["derive_core_attempts"][0]["targets_full"])

    def test_a_change_every_later_join_depends_on_is_followed(self):
        for spelling in ("cd data && cd claudecode_direct && d4d derive core --full L/CHORUS_d4d.yaml",
                         "cd data && echo a && d4d derive core --full claudecode_direct/L/CHORUS_d4d.yaml",
                         "echo a; cd data && d4d derive core --full claudecode_direct/L/CHORUS_d4d.yaml",
                         f"pushd /elsewhere && popd && d4d derive core --full {self.FULL}"):
            with self.subTest(spelling=spelling):
                identity, block = self._derived(spelling)
                self.assertEqual(block["status"], "checked", block["reasons"])
                self.assertEqual(block["boundaries"]["derive_core"]["tool_use_id"], identity)
                self.assertEqual(block["origin"], {"contemporaneous": 3, "phase1_correction": 1,
                                                   "phase3_backport": 1})

    def test_shell_resolves_full_only_through_a_change_that_ran(self):
        full = [ro._Target("full", Path("/r/data/F.yaml"))]
        cases = {"cd data && d4d derive core --full F.yaml": True,
                 "echo a; d4d derive core --full data/F.yaml": True,
                 "cd data && echo a && d4d derive core --full F.yaml": True,
                 "cd /x; cd /r/data && d4d derive core --full F.yaml": True,
                 "pushd data && popd && d4d derive core --full data/F.yaml": True,
                 "cd /x && d4d derive core --full data/F.yaml": False,
                 "cd /x; d4d derive core --full data/F.yaml": None,
                 "cd data && echo a ; d4d derive core --full F.yaml": None,
                 "false && cd /x; d4d derive core --full data/F.yaml": None,
                 "true || cd /x && d4d derive core --full data/F.yaml": None,
                 "cd /x || true && d4d derive core --full data/F.yaml": None,
                 "(cd /x) && d4d derive core --full data/F.yaml": None,
                 "cd /x | d4d derive core --full data/F.yaml": None,
                 "pushd /x; popd && d4d derive core --full data/F.yaml": None,
                 "pushd data && pushd /x ; popd && d4d derive core --full F.yaml": None,
                 "cd data\nd4d derive core --full F.yaml": None,
                 # a here-document's lines read as parts: no change in a
                 # multi-line command is trusted, even one `&&` guards
                 "echo a\ncd data && d4d derive core --full F.yaml": None,
                 # a skipped pushd pushed nothing; a skipped popd popped nothing
                 "true || pushd /x && popd && d4d derive core --full data/F.yaml": None,
                 "pushd data && true || popd && d4d derive core --full F.yaml": None,
                 "echo a\nd4d derive core --full /r/data/F.yaml": True}
        for command, expected in cases.items():
            with self.subTest(command=command):
                derives = ro._shell(command, "/r", full)["derives"]
                self.assertEqual([d["targets_full"] for d in derives], [expected])

    def test_newlines_are_joins_outside_quotes(self):
        self.assertEqual(ro._tokens("cd data\nd4d derive core"), ["cd", "data", ";", "d4d", "derive", "core"])
        for command, word in (('python -c "a\nb"', "a\nb"), ("echo 'a\nb'", "a\nb"), ("echo $'a\nb'", "$a\nb")):
            with self.subTest(command=command):
                self.assertEqual(ro._tokens(command)[-1], word)
                self.assertNotIn(";", ro._tokens(command))


class RipgrepHostnameHelper(Base):
    """`rg --hostname-bin CMD` runs CMD to name the host for its hyperlinks
    (#3268): a helper that rewrites the receipt before the draft, restored
    by a later Write, left stale evidence reported as contemporaneous."""

    def test_a_hostname_helper_restored_after_the_draft_is_unknown(self):
        for command in (f"rg --hostname-bin ./fix-receipt --hyperlink-format 'file://{{host}}{{path}}' x {REL}",
                        f"rg --hostname-bin=./fix-receipt x {REL}",
                        f"rg x {REL} --hostname-bin ./fix-receipt"):
            with self.subTest(command=command):
                r = self.new_run()
                r.write(r.receipt, PRE)
                r.bash(command)                         # the helper may rewrite the receipt here
                r.write(r.full, "id: x\n")
                r.write(r.receipt, PRE)                 # ... and this Write restores it
                r.derive()
                block = r.report()
                self.assertUnknown(block, "may change the receipt other than by a Write")
                self.assertEqual(len(block["non_write_mutations"]), 1)

    def test_rg_reads_only_refuses_a_hostname_helper(self):
        cases = {("rg", "--hostname-bin", "h", "x", "R"): False, ("rg", "--hostname-bin=h", "x", "R"): False,
                 ("rg", "--hyperlink-format", "default", "x", "R"): True, ("rg", "--hostname", "x", "R"): True}
        for segment, expected in cases.items():
            with self.subTest(segment=segment):
                self.assertIs(ro._rg_reads_only(list(segment)), expected)

    def test_a_config_hostname_helper_is_named(self):
        text = " ".join(ro.NON_CHECKS)
        self.assertIn("or a hostname helper (`--hostname-bin`) set there", text)
        self.assertIn("a ripgrep hostname helper set in a config file the same way", " ".join(ro.__doc__.split()))


class DeriveSpellings(Base):
    """A `derive core` the parser does not read was invisible: no attempt row,
    no boundary, and a Phase 3 snippet reported as `phase1_correction` with
    the status `checked` (#3137). The `timeout`, `env` and `nice` wrappers and
    an interpreter held in a variable are read through; any other part that
    carries the words `derive core` is a derive that cannot be placed."""

    FULL = "data/claudecode_direct/L/CHORUS_d4d.yaml"
    OUT = "--out data/claudecode_direct_core/L/CHORUS_d4d_core.yaml"

    def _derived(self, spelling, **result):
        """Draft, a Phase 1 entry, the call under test, a Phase 3 entry."""
        r = self.new_run()
        r.write(r.receipt, PRE)
        r.write(r.full, "id: x\n")
        r.write(r.receipt, Boundaries.C003)
        identity = r.bash(spelling, **result)
        r.write(r.receipt, Boundaries.C004)
        return identity, r.report()

    def test_wrapped_and_variable_interpreter_spellings_are_the_boundary(self):
        derive = f"derive core --full {self.FULL} {self.OUT}"
        for spelling in (f"timeout 600 poetry run d4d {derive}",
                         f"timeout -s KILL --preserve-status 10m d4d {derive}",
                         f"timeout --kill-after=5 1.5h d4d {derive}",
                         f"env PYTHONPATH=src python -m data_sheets_schema.cli {derive}",
                         f"env -i -u HOME -- D4D_PROFILE=bridge2ai poetry run d4d {derive}",
                         f"$PY -m data_sheets_schema.cli {derive}",
                         f"${{PY}} -m data_sheets_schema.cli {derive}",
                         f"nice -n 10 d4d {derive}",
                         f"nice -5 poetry run d4d {derive}",
                         f"X=1 timeout 60 env Y=2 nice d4d {derive} && d4d receipts check --label L"):
            with self.subTest(spelling=spelling):
                identity, block = self._derived(spelling)
                self.assertEqual(block["status"], "checked", block["reasons"])
                self.assertEqual(block["boundaries"]["derive_core"]["tool_use_id"], identity)
                self.assertEqual(block["origin"], {"contemporaneous": 3, "phase1_correction": 1,
                                                   "phase3_backport": 1})

    def test_a_wrapped_derive_carries_its_own_status(self):
        # `timeout` passes the derive's exit status through; its own 124 is a failure.
        identity, block = self._derived(f"timeout 600 poetry run d4d derive core --full {self.FULL} {self.OUT}",
                                        ok=False)
        self.assertEqual(block["status"], "checked", block["reasons"])
        self.assertEqual(block["derive_core_attempts"][0]["outcome"], "failed")
        self.assertIsNone(block["boundaries"]["derive_core"])
        self.assertEqual(block["origin"]["phase1_correction"], 2)

    def test_an_unparsed_derive_spelling_is_unknown(self):
        derive = f"derive core --full {self.FULL} {self.OUT}"
        for spelling in (f"bash -c 'poetry run d4d {derive}'",
                         f"sh -c \"cd data && d4d {derive}\"",
                         f"echo {self.FULL} | xargs -I{{}} poetry run d4d derive core --full {{}} {self.OUT}",
                         f"echo \"$(poetry run d4d {derive})\"",
                         f"cat `d4d {derive}`",
                         f"env -C data d4d {derive}",
                         f"timeout --unknown 5 d4d {derive}",
                         f"timeout forever d4d {derive}",
                         f"nice --weird d4d {derive}",
                         f"poetry run d4d -v {derive}",
                         f"poetry run d4d derive",
                         f"python -X utf8 -m data_sheets_schema.cli {derive}",
                         f"$PY -c 'x' -m data_sheets_schema.cli {derive}",
                         f"sed -n 'e d4d {derive}' {self.FULL}",
                         f"d4d receipts check --label \"$(d4d {derive})\"",
                         # #3384: the words in a reader, run by a program a pipe feeds
                         f"echo '{derive}' | xargs poetry run d4d",
                         f"echo 'poetry run d4d {derive}' | bash",
                         f"printf '%s\\n' 'd4d {derive}' | cat | sh",
                         f"echo 'd4d {derive}' |& bash",
                         f"(echo 'd4d {derive}'; echo true) | bash",
                         # command-wide, as documented: a pipe later in the command, not only
                         # the reader's own pipeline, is enough (a false unknown at worst)
                         "grep -n 'derive core' x.md && ls | python scripts/tally.py",
                         # #3385: a substitution anywhere makes a reader's words opaque
                         f"grep -c 'derive core' .claude/commands/d4d-full-core.md; echo $((1+1))",
                         "poetry run d4d provenance record --phase 'derive core' --recorded-at \"$(date -u)\"",
                         # #3397: quoted or escaped words inside a nested shell or `eval`
                         f"bash -c 'poetry run d4d derive \"core\" --full {self.FULL} {self.OUT}'",
                         f"eval 'd4d derive \"core\" --full {self.FULL} {self.OUT}'",
                         f"bash -c \"d4d 'derive' core --full {self.FULL} {self.OUT}\"",
                         f"bash -c \"d4d derive \\\"core\\\" --full {self.FULL} {self.OUT}\"",
                         f"bash -c 'd4d derive \\core --full {self.FULL} {self.OUT}'",
                         f"echo 'd4d derive \"core\" --full {self.FULL} {self.OUT}' | bash",
                         # #3397: the subcommand word supplied at run time
                         f"d4d derive $(echo core) --full {self.FULL} {self.OUT}",
                         f"d4d derive `echo core` --full {self.FULL} {self.OUT}",
                         f"echo core | xargs -I{{}} d4d derive {{}} --full {self.FULL} {self.OUT}",
                         f"d4d derive $SUB --full {self.FULL} {self.OUT}",
                         f"d4d derive ${{SUB}} --full {self.FULL} {self.OUT}",
                         # #3426: any xargs replacement string, not only `{}`, and a
                         # word xargs appends after a `derive` that ends its command
                         f"echo core | xargs -I% d4d derive % --full {self.FULL} {self.OUT}",
                         f"echo core | xargs -I % poetry run d4d derive % --full {self.FULL} {self.OUT}",
                         f"echo core | xargs -J % d4d derive % --full {self.FULL} {self.OUT}",
                         f"echo core | xargs -0I@ d4d derive @ --full {self.FULL} {self.OUT}",
                         f"echo core | xargs -i d4d derive {{}} --full {self.FULL} {self.OUT}",
                         f"echo core | xargs -iSUB d4d derive SUB --full {self.FULL} {self.OUT}",
                         f"echo core | xargs --replace=@ d4d derive @ --full {self.FULL} {self.OUT}",
                         f"echo core | xargs -L 1 -I @ sh -c 'd4d derive @ --full {self.FULL} {self.OUT}'",
                         f"echo core --full {self.FULL} {self.OUT} | xargs -n 9 d4d derive",
                         # #3453: a redirection is the shell's, so the derive still ends
                         # the xargs command and xargs still appends the word
                         f"echo core --full {self.FULL} {self.OUT} | xargs d4d derive 2>&1 | tail -5",
                         f"echo core --full {self.FULL} {self.OUT} | xargs d4d derive >/tmp/log",
                         f"echo core --full {self.FULL} {self.OUT} | xargs d4d derive 2>/dev/null",
                         f"echo core --full {self.FULL} {self.OUT} | xargs d4d derive > /tmp/log",
                         f"xargs d4d derive < /tmp/args-3374"):
            for ok in (True, False):
                with self.subTest(spelling=spelling, ok=ok):
                    identity, block = self._derived(spelling, ok=ok)
                    if spelling == "poetry run d4d derive":
                        # no `derive core` words at all: nothing to place
                        self.assertEqual(block["derive_core_attempts"], [])
                        continue
                    self.assertUnknown(block, f"derive core {identity} cannot be placed")
                    self.assertIn("a spelling of `derive core` the parser does not follow",
                                  " ".join(block["reasons"]))
                    attempt = block["derive_core_attempts"][0]
                    self.assertEqual((attempt["targets_full"], attempt["status_basis"], attempt["outcome"]),
                                     (None, "unparsed", "ambiguous"))

    def test_an_unparsed_derive_the_native_control_denied_never_ran(self):
        identity, block = self._derived(
            f"bash -c 'poetry run d4d derive core --full {self.FULL} {self.OUT}'", ok=False,
            content=ro.NATIVE_DENIAL_PREFIX + "compound command", metadata="Error: " + ro.NATIVE_DENIAL_PREFIX)
        self.assertEqual(block["status"], "checked", block["reasons"])
        self.assertEqual(block["derive_core_attempts"][0]["outcome"], "failed")
        self.assertEqual(block["origin"]["phase1_correction"], 2)

    def test_the_words_derive_core_where_nothing_runs_them_are_not_a_derive(self):
        for spelling in ("grep -n 'derive core' .claude/commands/d4d-full-core.md",
                         "echo derive core && printf '%s\\n' 'derive core'",
                         "sed -n '/derive core/,+3p' .claude/commands/d4d-full-core.md",
                         "poetry run d4d provenance record --project CHORUS --label L "
                         "--phase '{\"name\": \"derive core\"}'",
                         "poetry run d4d receipts check --label L --project CHORUS --note 'after derive core'",
                         "cat derive-core.log", "ls data/rederive core",
                         # #3384: a reader's words piped only into readers run nothing
                         "grep -n 'derive core' x.md | head -3 | wc -l",
                         "ls | python scripts/tally.py && grep -n 'derive core' x.md",
                         # #3386: whole words only, in a program that is not a reader
                         "python scripts/rederive core_x.py", "python scripts/derive core-x.py",
                         "python scripts/derive core.py", "python scripts/derive_core x.py",
                         "python scripts/re.derive core", "python scripts/derive corex.py",
                         "python scripts/rederive core",
                         # #3397: quote removal joins only what the shell joins
                         "bash -c 'python scripts/\"re\"derive core'",
                         "bash -c 'python scripts/\"derive\" \"core.py\"'",
                         "grep -n \"derive $x\" x.md",
                         "poetry run d4d receipts check --label \"$L\" --project CHORUS",
                         # #3426: an xargs replacement string or appended word that is not
                         # the word after `derive` supplies nothing to it
                         "ls | xargs -I% python scripts/derive corex %",
                         "ls | xargs grep -n derive x.md",
                         "ls | xargs -I% cat %; python scripts/derive corex %"):
            with self.subTest(spelling=spelling):
                r = self.new_run()
                r.write(r.receipt, PRE)
                r.write(r.full, "id: x\n")
                r.write(r.receipt, Boundaries.C003)
                r.bash(spelling)
                identity = r.derive()
                r.write(r.receipt, Boundaries.C004)
                block = r.report()
                self.assertEqual(block["status"], "checked", block["reasons"])
                self.assertEqual([a["tool_use_id"] for a in block["derive_core_attempts"]], [identity])

    def test_xargs_supplies_derive_word(self):
        # #3426: the replacement string xargs sets, whatever it is, or the word it
        # appends where it sets none; read on its own, apart from the `{}` rule.
        cases = {"xargs -I% d4d derive %": True, "xargs -I % d4d derive %": True,
                 "xargs -J % d4d derive %": True, "xargs -0I@ d4d derive @": True,
                 "xargs -i d4d derive {}": True, "xargs -iSUB d4d derive SUB": True,
                 "xargs --replace d4d derive {}": True, "xargs --replace=@ d4d derive @": True,
                 "xargs -L 1 -I @ sh -c d4d derive @": True, "xargs -I% timeout 5 d4d derive x%": True,
                 "xargs d4d derive": True, "xargs -n 1 -P 4 d4d derive": True,
                 "/usr/bin/xargs -r d4d derive": True,
                 # #3453: redirections are the shell's, not words xargs passes on
                 "xargs d4d derive 2>&1 | tail -5": True, "xargs d4d derive >/tmp/log": True,
                 "xargs d4d derive > /tmp/log": True, "xargs d4d derive 2>/dev/null": True,
                 "xargs d4d derive < args": True, "xargs d4d derive &>log": True,
                 "xargs d4d derive >>log 2>&1": True, "xargs <args d4d derive": True,
                 # as the segment's words arrive, split by shlex and joined by spaces
                 "xargs d4d derive 2 >& 1": True, "xargs d4d derive 2 > /dev/null": True,
                 "xargs d4d derive 2> err full": False, "xargs d4d derive >log full": False,
                 "xargs d4d derive full 2>&1": False, "xargs d4d derive <(ls)": False,
                 # with a replacement string set, xargs appends nothing
                 "xargs -I% d4d derive": False, "xargs -i d4d derive": False, "xargs -i d4d derive full": False,
                 "xargs -I% d4d derive full %": False, "xargs -I% d4d receipts check %": False,
                 "xargs d4d derive full": False, "xargs -n 1 d4d derive --full F": False,
                 "xargs -I% echo % | d4d derive %": False, "xargs -I% echo %; d4d derive": False,
                 "d4d derive %": False, "d4d derive": False}
        for command, expected in cases.items():
            with self.subTest(command=command):
                self.assertIs(ro._xargs_supplies_derive_word(command), expected)

    def test_wrapper_skip(self):
        cases = {"timeout 600 d4d": 2, "timeout -v -s TERM -k 5 10s d4d": 7, "timeout --signal=HUP 1d d4d": 3,
                 "timeout -sKILL 5 d4d": 3, "timeout 5": 2, "timeout x d4d": None, "timeout --x 5 d4d": None,
                 "env A=1 d4d": 1, "env -i - -u X --unset=Y -uZ d4d": 7, "env -- d4d": 2, "env -C d d4d": None,
                 "env -S 'd4d'": None, "nice d4d": 1, "nice -n 5 d4d": 3, "nice -n5 d4d": 2, "nice -10 d4d": 2,
                 "nice --adjustment=-3 d4d": 2, "nice -x d4d": None, "d4d derive core": None, "": None}
        for command, skip in cases.items():
            with self.subTest(command=command):
                self.assertEqual(ro._wrapper_skip(command.split()), skip)
        self.assertEqual(ro._unwrapped("A=1 timeout 5 env B=2 poetry run nice -n 1 d4d x".split()), ["d4d", "x"])
        self.assertEqual(ro._unwrapped("timeout 5".split()), ["timeout", "5"])
        self.assertEqual(ro._unwrapped("env -C d d4d".split()), ["env", "-C", "d", "d4d"])

    def test_a_wrapped_directory_change_is_not_a_directory_change(self):
        # A wrapper runs `cd` as a program, which cannot move the shell: the
        # relative `--full` resolves where the call started, not under `elsewhere`.
        identity, block = self._derived(f"env cd elsewhere && d4d derive core --full {self.FULL} {self.OUT}")
        self.assertEqual(block["status"], "checked", block["reasons"])
        self.assertEqual(block["boundaries"]["derive_core"]["tool_use_id"], identity)

    def test_the_route_it_cannot_see_is_named(self):
        text = " ".join(ro.NON_CHECKS)
        self.assertIn("a `derive core` run without the words `derive core` on the command line", text)
        self.assertIn("`python -c` building the argument list", text)
        doc = " ".join(ro.__doc__.split())
        self.assertIn("carries the words `derive core` and is neither a d4d call of another subcommand "
                      "nor a program known to read is a derive that cannot be placed (#3137): a nested "
                      "`bash -c`, an `xargs`, or a wrapper option or CLI option this does not read makes a "
                      "part such a one (#3455)", doc)
        self.assertNotIn("known to read (a nested `bash -c`", doc)
        self.assertIn("a reader part that carries them where a pipe later in the command feeds a program "
                      "not known to read", doc)                                    # #3384
        self.assertIn("in a command that substitutes anywhere (`$(...)`, backticks, `<(...)`), every part "
                      "that carries them, readers and the recorder's `--phase` included", doc)   # #3385
        self.assertIn("a file that an earlier part wrote the words into and a later part runs", text)
        # #3397: the quote rule, the run-time word and the route still unseen
        self.assertIn("The words are matched after quote and escape characters are removed", text)
        self.assertIn("`xargs ... derive {}`) counts as a derive that cannot be placed", text)
        self.assertIn("a variable or substitution supplying the word `derive` itself", text)
        self.assertIn("a word the shell builds some other way (a glob, `derive c*`) is not seen", text)
        # #3426: any xargs replacement string, and the one xargs route still unseen
        self.assertIn("as does a word carrying any replacement string an `xargs` in the command sets "
                      "(`xargs -I% ... derive %`, `-J %`, `-i`, `--replace`)", text)
        self.assertIn("nor is a word xargs appends to a `derive` that does not end the xargs command", text)
        # #3453: the appended-word rule reads the command with its redirections aside
        self.assertIn("redirections (`2>&1`, `>log`, `< args`) aside, since they are the shell's (#3453)", text)
        self.assertIn("ends it once the shell's redirections are set aside", doc)
        self.assertIn("as does one carrying any replacement string an `xargs` in the command sets", doc)
        self.assertIn("The words are matched after quote and escape characters are removed, as the shell "
                      "running a nested string removes them", doc)


class RuntimeDenial(Base):
    """A Bash call the runtime refused in `dontAsk` mode never ran, but only
    where the transcript's terminal `result` lists it under
    `permission_denials` with the call's own tool name and input (#3201)."""

    WRITE = f"sed -i '' 's/a/b/' {REL}"
    REFUSAL = ro.DONT_ASK_DENIAL_PREFIX + " IMPORTANT: You *may* attempt to accomplish this action another way."
    DERIVE = ("poetry run d4d derive core --full data/claudecode_direct/L/CHORUS_d4d.yaml "
              "--out data/claudecode_direct_core/L/CHORUS_d4d_core.yaml 2>&1 | tail -5")

    def _refused(self, command=WRITE, *, terminal=None, content=None, ok=False, derive_after=True):
        """Draft, then the call the runtime refused, then (by default) a
        derive, then the terminal `result` event; `terminal` edits that event
        (or returns None to drop it)."""
        r = self.new_run()
        r.write(r.receipt, PRE)
        r.write(r.full, "id: x\n")
        identity = r.bash(command, ok=ok, content=self.REFUSAL if content is None else content,
                          metadata="Error: " + ro.DONT_ASK_DENIAL_PREFIX)
        if derive_after:
            r.derive()
        event = {"type": "result", "subtype": "success", "is_error": False, "session_id": "s",
                 "permission_denials": [{"tool_name": "Bash", "tool_use_id": identity,
                                         "tool_input": {"command": command, "description": "x"}}]}
        if terminal is not None:
            event = terminal(event)
        if event is not None:
            r.events.append(event)
        return identity, r

    def test_a_corroborated_refusal_is_listed_not_a_mutation(self):
        identity, r = self._refused()
        block = r.report()
        self.assertEqual(block["status"], "checked", block["reasons"])
        self.assertEqual(block["non_write_mutations"], [])
        self.assertEqual([(w["tool_use_id"], w["target"], w["tool"], w["rejection"]) for w in block["rejected_writes"]],
                         [(identity, "receipt", "Bash", "runtime_denial")])
        self.assertIn("· rejected Bash of the receipt (runtime_denial), transcript 0 line 6", ro.summary(block))

    def test_an_uncorroborated_refusal_stays_a_possible_change(self):
        def denial(**edit):
            def change(event):
                event["permission_denials"][0].update(edit)
                return event
            return change

        def twice(event):
            event["permission_denials"] *= 2
            return event
        cases = {
            "no terminal event": dict(terminal=lambda e: None),
            "not listed": dict(terminal=lambda e: {**e, "permission_denials": []}),
            "no denial list": dict(terminal=lambda e: {k: v for k, v in e.items() if k != "permission_denials"}),
            "listed twice": dict(terminal=twice),
            "another input": dict(terminal=denial(tool_input={"command": "true", "description": "x"})),
            "another tool": dict(terminal=denial(tool_name="Edit")),
            "another id": dict(terminal=denial(tool_use_id="toolu_999")),
            "an error terminal": dict(terminal=lambda e: {**e, "is_error": True}),
            "a terminal that is not success": dict(terminal=lambda e: {**e, "subtype": "error_during_execution"}),
            "text not the refusal": dict(content="Exit code 1\n" + ro.DONT_ASK_DENIAL_PREFIX),
            "a result that is not an error": dict(ok=True),
        }
        for label, kwargs in cases.items():
            with self.subTest(label):
                _, r = self._refused(**kwargs)
                block = r.report()
                self.assertUnknown(block, "may change the receipt other than by a Write")
                self.assertEqual(block["rejected_writes"], [])

    def test_a_tool_use_id_that_is_not_a_string_corroborates_nothing(self):
        # #3454: a list or mapping id is not hashed and not an id, as in
        # `reference_rescore`; a real listing beside it still corroborates.
        for bad in (["x"], {"a": 1}, None, 7):
            with self.subTest(tool_use_id=bad):
                identity, r = self._refused()
                listing = r.events[-1]["permission_denials"]
                listing.insert(0, {**listing[0], "tool_use_id": bad})
                self.assertEqual(ro._runtime_denials(*self._paired(r)), {identity})
                self.assertEqual(r.report()["status"], "checked")
                listing.pop(1)                        # only the malformed entry is left
                self.assertEqual(ro._runtime_denials(*self._paired(r)), set())
                self.assertUnknown(r.report(), "may change the receipt other than by a Write")

    def test_the_rule_is_reference_rescores_own(self):
        # #3387: content that is a list of text blocks, or a command that is
        # not a string, is not corroborated here any more than there.
        blocks = [{"type": "text", "text": self.REFUSAL}]
        _, r = self._refused(content=blocks)
        self.assertUnknown(r.report(), "may change the receipt other than by a Write")
        identity, r = self._refused()
        call = next(b for e in r.events if e.get("type") == "assistant"
                    for b in e["message"]["content"] if b.get("id") == identity)
        call["input"]["command"] = [self.WRITE]
        r.events[-1]["permission_denials"][0]["tool_input"] = call["input"]
        self.assertNotIn(identity, ro._runtime_denials(*self._paired(r)))
        call["input"]["command"] = self.WRITE
        r.events[-1]["permission_denials"][0]["tool_input"] = call["input"]
        self.assertIn(identity, ro._runtime_denials(*self._paired(r)))

    @staticmethod
    def _paired(r):
        reasons: list = []
        _, events = ro._load([r.transcript()], reasons)
        calls, results = ro._pair(events, reasons)
        return events, calls, results

    def test_two_terminal_events_corroborate_nothing(self):
        identity, r = self._refused()
        r.events.append(dict(r.events[-1]))
        self.assertUnknown(r.report(), f"Bash call {identity}")

    def test_the_terminal_must_follow_the_result_in_the_calls_own_transcript(self):
        # A killed-and-resumed pair: the refusal is in the first file, which
        # has no terminal; the second file's terminal lists it.
        identity, r = self._refused(derive_after=False)
        terminal = r.events.pop()
        split = len(r.events)
        r.derive()
        for _ in range(5):                          # the terminal's line is past the refusal's
            r.bash("wc -l data/x.yaml")
        r.events.append(terminal)
        block = ro.origin([r.transcript("t1.jsonl", r.events[:split]),
                           r.transcript("t2.jsonl", r.events[:1] + r.events[split:])], r.receipt, r.full)
        self.assertUnknown(block, f"Bash call {identity}")
        # A terminal before the refusal's result is not its listing either.
        identity, r = self._refused(derive_after=False)
        terminal = r.events.pop()
        r.events.insert(len(r.events) - 1, terminal)
        r.derive()
        self.assertUnknown(r.report(), f"Bash call {identity}")

    def test_the_call_and_its_result_must_each_be_in_the_terminals_transcript(self):
        # #3399: each own-transcript condition, one at a time. `_pair` joins
        # ids across files, so a call in one file whose result and terminal
        # are in another reaches the check; so does a result in another file.
        identity, r = self._refused()
        events, calls, results = self._paired(r)
        self.assertIn(identity, ro._runtime_denials(events, calls, results))
        call = next(c for c in calls if c["id"] == identity)
        for moved in (call, results[identity]):
            with self.subTest(moved="call" if moved is call else "result"):
                moved["transcript"] = 1
                self.assertNotIn(identity, ro._runtime_denials(events, calls, results))
                moved["transcript"] = 0
        self.assertIn(identity, ro._runtime_denials(events, calls, results))

    def test_a_call_in_another_file_from_its_result_and_terminal_is_not_corroborated(self):
        # #3399, end to end: the call alone in the first file; its result,
        # the derive and the terminal in the second, each past the call's line.
        identity, r = self._refused()
        at = next(i for i, e in enumerate(r.events) if e.get("type") == "assistant"
                  and any(b.get("id") == identity for b in e["message"]["content"]))
        first = r.events[:at + 1]
        second = r.events[:1] + [{"type": "system", "subtype": "status"}] * (at + 1) + r.events[at + 1:]
        block = ro.origin([r.transcript("t1.jsonl", first), r.transcript("t2.jsonl", second)], r.receipt, r.full)
        self.assertEqual(block["rejected_writes"], [], block)
        self.assertUnknown(block, f"Bash call {identity}")

    def test_a_refused_derive_never_ran(self):
        command = self.DERIVE
        identity, r = self._refused(command, derive_after=False)
        terminal = r.events.pop()
        r.write(r.receipt, DeriveStatus.ADDED)
        r.events.append(terminal)
        block = r.report()
        self.assertEqual(block["status"], "checked", block["reasons"])
        self.assertEqual(block["derive_core_attempts"][0]["outcome"], "failed")
        self.assertIsNone(block["boundaries"]["derive_core"])
        self.assertEqual(block["origin"]["phase1_correction"], 1)
        # Uncorroborated, the same refusal is a derive that cannot be placed.
        identity, r = self._refused(command, derive_after=False, terminal=lambda e: None)
        r.write(r.receipt, DeriveStatus.ADDED)
        self.assertUnknown(r.report(), f"derive core {identity} cannot be placed")


class Listing(unittest.TestCase):
    """Which slot each listed entry names depends on the three multisets,
    never on the receipt's order (#3115)."""

    def test_post_draft_entries_do_not_depend_on_final_order(self):
        # Phase 1 added Z, present at derive; A was later re-addressed. Z sorts
        # last, so neither slot order nor receipt order can pick it by accident.
        base = [("c1", "S", "A")]
        core = [("c1", "S", "A"), ("c1", "S", "Z")]
        for slots, expected in ((("Z", "C"), [("Z", "phase1_correction")]),
                                (("Z", "C", "D"), [("D", "phase3_backport"), ("Z", "phase1_correction")])):
            outcomes = []
            for order in itertools.permutations(slots):
                block = ro.classify(base, core, [("c1", "S", slot) for slot in order])
                outcomes.append(block)
                self.assertEqual([(e["slot"], e["origin"]) for e in block["post_draft_entries"]], expected, order)
                self.assertEqual(block["readdressed"], 1)
            self.assertTrue(all(o == outcomes[0] for o in outcomes))

    def test_a_slot_the_draft_already_carried_is_not_the_phase1_one(self):
        # A second A added after derive; B added before it. The derive-time
        # snapshot's A is the pre-draft one, so B, not A, is the Phase 1 entry.
        block = ro.classify([("c1", "S", "A")], [("c1", "S", "A"), ("c1", "S", "B")],
                            [("c1", "S", "A"), ("c1", "S", "A"), ("c1", "S", "B")])
        self.assertEqual([(e["slot"], e["origin"]) for e in block["post_draft_entries"]],
                         [("A", "phase3_backport"), ("B", "phase1_correction")])

    def test_a_slot_absent_at_derive_is_not_listed_as_phase1_when_one_present_is_left(self):
        # A re-addressed to B before derive; C added after it.
        block = ro.classify([("c1", "S", "A")], [("c1", "S", "B")], [("c1", "S", "C"), ("c1", "S", "B")])
        self.assertEqual([(e["slot"], e["origin"]) for e in block["post_draft_entries"]], [("C", "phase3_backport")])

    def test_removed_entries_do_not_depend_on_pre_draft_order(self):
        for base in ([("c1", "S", "A"), ("c1", "S", "B")], [("c1", "S", "B"), ("c1", "S", "A")]):
            block = ro.classify(base, base, [("c1", "S", "C")])
            self.assertEqual((block["readdressed"], block["removed_contemporaneous"]), (1, 1))
            self.assertEqual([e["slot"] for e in block["removed_entries"]], ["B"])

    def test_removed_entries_are_listed_by_chunk_whatever_the_pre_draft_order(self):
        # Three removed entries over two chunks: only the list's own sort
        # makes its order independent of the pre-draft receipt's (#3188).
        base = [("c2", "T", "X"), ("c1", "S", "Z"), ("c1", "S", "Y")]
        blocks = [ro.classify(list(order), list(order), []) for order in itertools.permutations(base)]
        self.assertEqual([(e["chunk"], e["slot"]) for e in blocks[0]["removed_entries"]],
                         [("c1", "Y"), ("c1", "Z"), ("c2", "X")])
        self.assertTrue(all(b == blocks[0] for b in blocks))

    def test_entries_are_listed_by_chunk_whatever_the_receipt_order(self):
        final = [("c2", "T", "X"), ("c1", "S", "Y")]
        block = ro.classify([], [], final)
        self.assertEqual([e["chunk"] for e in block["post_draft_entries"]], ["c1", "c2"])
        self.assertEqual(block, ro.classify([], [], list(reversed(final))))


class Privacy(Base):
    def test_no_snippet_text_reaches_the_output(self):
        r = self.run_
        r.write(r.receipt, receipt_text(("c001", [("title", SECRET)])))
        r.write(r.full, f"title: {SECRET}\n")          # the record is model output too
        r.derive()
        r.write(r.receipt, receipt_text(("c001", [("title", SECRET), ("name", SECRET + " again")])))
        r.receipt.write_text(r.last_receipt)
        path = r.transcript()
        for args in ([], ["--json"]):
            from data_sheets_schema.cli.receipts import receipts
            out = CliRunner().invoke(receipts, ["origin", "--transcript", str(path), "--receipt", str(r.receipt),
                                                "--full", str(r.full), *args])
            self.assertEqual(out.exit_code, 0, out.output)
            self.assertNotIn("secret-snippet-text", out.output)
            self.assertIn("phase3_backport", out.output)
        block = json.loads(out.output)
        self.assertEqual(block["origin"]["phase3_backport"], 1)


class Cli(unittest.TestCase):
    def test_help(self):
        from data_sheets_schema.cli import cli
        out = CliRunner().invoke(cli, ["receipts", "origin", "--help"])
        self.assertEqual(out.exit_code, 0, out.output)
        for option in ("--transcript", "--receipt", "--full", "--json"):
            self.assertIn(option, out.output)

    def test_help_states_the_derive_rule_the_code_applies(self):
        # A successful `derive && …` is the boundary (and_chain), so the help
        # must not say a derive followed by another command never counts (#3186).
        from data_sheets_schema.cli import cli
        text = " ".join(CliRunner().invoke(cli, ["receipts", "origin", "--help"]).output.split())
        self.assertNotIn("followed by another command", text)
        self.assertIn("every join after it is `&&` and the call succeeded", text)
        self.assertIn("a failed `&&` chain cannot be placed", text)
        # #3137, #3201: the wrappers read through and the runtime's own refusal
        self.assertIn("`timeout`, `env` and `nice` wrappers are read through", text)
        self.assertNotIn("any other spelling that carries the words `derive core`", text)   # #3384
        # #3455: `bash -c` and `xargs` are named as parts that cannot be placed,
        # never in a parenthetical that reads as examples of readers
        self.assertNotIn("known only to read (`bash -c`, `xargs`)", text)
        self.assertIn("Three kinds of part carrying the words `derive core` cannot be placed: one that is "
                      "neither a d4d call it reads nor a program known only to read, such as a `bash -c` "
                      "or an `xargs` part;", text)
        self.assertIn("a reader part in a command where a later pipe feeds a program not known only to read "
                      "(`echo '... derive core ...' | bash`)", text)                          # #3384
        self.assertIn("and, in a command with a substitution anywhere, every such part.", text)   # #3385
        self.assertIn("The words are matched after quote and escape characters are removed "
                      "(`bash -c 'd4d derive \"core\"'`)", text)                               # #3397
        self.assertIn("`derive` followed by a word supplied at run time (`$SUB`, `$(echo core)`, `xargs`'s `{}` "
                      "or any other replacement string it sets, such as `-I%` or `-J %`, or the word xargs "
                      "appends after a `derive` that ends its command, redirections such as `2>&1` aside) "
                      "cannot be placed either", text)                                    # #3426, #3453
        self.assertIn("A derive whose words are not on the command line (a script, an alias, a variable "
                      "supplying `derive` itself) is not seen", text)
        self.assertIn("the runtime did in `dontAsk` mode and its terminal `result` lists the call", text)

    def test_unknown_prints_its_reasons_and_exits_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            from data_sheets_schema.cli.receipts import receipts
            out = CliRunner().invoke(receipts, ["origin", "--transcript", f"{tmp}/none.jsonl",
                                                "--receipt", f"{tmp}/r.yaml", "--full", f"{tmp}/f.yaml"])
        self.assertEqual(out.exit_code, 0, out.output)
        self.assertIn("receipt origin: unknown", out.output)
        self.assertIn("transcript 0 cannot be read", out.output)


if __name__ == "__main__":
    unittest.main()
