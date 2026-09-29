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
                        lambda r: r.derive_command().replace(" \\\n", "\n")):
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
                 "a || d4d derive core --full F": "none", "d4d derive core --full F &": "none"}
        for command, basis in cases.items():
            with self.subTest(command=command):
                segments, joins, leading = ro._layout(ro._tokens(command))
                index = next(i for i, s in enumerate(segments) if s[:3] == ["d4d", "derive", "core"])
                self.assertEqual(ro._status_basis(index, joins, leading, False), basis)
        segments, joins, leading = ro._layout(ro._tokens("d4d derive core --full F"))
        self.assertEqual(ro._status_basis(0, joins, leading, True), "none")


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
