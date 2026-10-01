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

    def edit(self, name="Edit", *, metadata=None, settle=True, **inputs):
        """An Edit or MultiEdit of the receipt. A successful one carries no
        `is_error` and the runtime's own metadata, as observed in local
        transcripts; the caller sets `last_receipt` to what the edit left."""
        identity = self.call(name, file_path=str(self.receipt), **inputs)
        if settle:
            self.result(identity, f"The file {self.receipt} has been updated.",
                        metadata if metadata is not None else {"filePath": str(self.receipt),
                                                               "userModified": False})
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
    def test_an_edit_of_the_receipt_that_cannot_be_replayed_is_unknown(self):
        # v2 replays a successful Edit (#3047); one whose `old_string` occurs
        # many times without `replace_all` cannot have succeeded as written.
        r = self._drafted()
        identity = r.call("Edit", file_path=str(r.receipt), old_string="a", new_string="b")
        r.result(identity, "ok", {"filePath": str(r.receipt)})
        r.derive()
        block = r.report()
        self.assertUnknown(block, f"Edit {identity} of the receipt (transcript 0 line 6) cannot be replayed")
        self.assertFalse(any("differs from the file on disk" in x for x in block["reasons"]), block["reasons"])

    def test_an_edit_of_the_receipt_with_no_success_evidence_is_unknown(self):
        r = self._drafted()
        r.call("Edit", file_path=str(r.receipt), old_string="c002", new_string="c003")
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
                # An absolute `--full`: after `cd data` a relative one no
                # longer resolves where the next call starts (#3719).
                r.derive(full=r.full)
                block = r.report()
                self.assertUnknown(block, "Bash call")
                self.assertEqual([m["covered_by_final_sha256"] for m in block["non_write_mutations"]
                                  if m["target"] == "receipt"], [False])

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

    def test_a_tool_call_whose_name_is_not_a_string_is_malformed(self):
        # A list-valued name raised TypeError in `_history` (#3918). Each
        # name gets a run of its own, so no earlier case's reason can
        # satisfy a later one's assertion.
        for name in (["Bash"], {"tool": "Bash"}, None, ""):
            with self.subTest(name=name):
                r = self.new_run()
                r.write(r.receipt, PRE)
                r.write(r.full, "id: x\n")
                r.events.append({"type": "assistant", "message": {"content": [
                    {"type": "tool_use", "id": f"bad_{len(r.events)}", "name": name, "input": {"command": "ls"}}]}})
                r.result(f"bad_{len(r.events) - 1}", "ok")
                block = r.report()
                self.assertUnknown(block, "whose name is not a non-empty string")
                # Its id is kept, so its result pairs with it and is not a
                # second malformed event, "a tool result with no earlier call".
                malformed = [reason for reason in block["reasons"] if "malformed tool event" in reason]
                self.assertEqual(len(malformed), 1, block["reasons"])
                self.assertTrue(malformed[0].startswith("1 malformed tool event(s)"), malformed)


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
                # The call under test is the first. A program in a process
                # substitution may be a function that changes directory, as
                # which parts a child runs is not read (#3782, #3810), so the
                # derive's relative `--out` after it may name the receipt too.
                self.assertEqual(block["non_write_mutations"][0]["tool_use_id"], "toolu_002")
                self.assertEqual(len(block["non_write_mutations"]), 2 if "(rm" in command or "(tee" in command else 1)

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
        r.result(identity, "ok", {"filePath": str(r.receipt)}, is_error=None)   # no success evidence
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
        # An absolute `--full`: an earlier call here may run a function or a sourced
        # script, which may change directory, so a relative one is not placed (#3782).
        r = self.run_
        r.write(r.receipt, PRE)
        r.write(r.full, "id: x\n")
        r.bash(f"git add {REL}")
        r.derive(full=r.full)
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


TITLE = "  - slot: title\n    snippet: The CHORUS dataset\n"
LICENSE = "  - slot: license\n    snippet: CC BY 4.0 license\n"
WITH_LICENSE = receipt_text(("c001", [("title", "The CHORUS dataset"), ("license", "CC BY 4.0 license"),
                                      ("funders[0].grant_id", "OT2OD032701")]),
                            ("c002", [("description", "a multimodal collection")]))


class EditReplay(Base):
    """A successful Edit or MultiEdit of the receipt, which the agentic
    playbook permits, is replayed exactly on the receipt as it last stood
    (#3047), and the final sha256 still holds the rebuilt receipt to disk."""

    def _drafted(self):
        r = self.run_
        r.write(r.receipt, PRE)
        r.write(r.full, "id: x\n")
        return r

    def test_the_fixture_edit_is_the_receipt_it_names(self):
        self.assertEqual(PRE.count(TITLE), 1)
        self.assertEqual(PRE.replace(TITLE, TITLE + LICENSE), WITH_LICENSE)

    def test_an_edit_before_the_derive_is_a_phase1_correction(self):
        r = self._drafted()
        identity = r.edit(old_string=TITLE, new_string=TITLE + LICENSE, replace_all=False)
        r.last_receipt = WITH_LICENSE
        r.derive()
        block = r.report()
        self.assertEqual(block["status"], "checked", block["reasons"])
        self.assertEqual(block["instrument"], "receipt_origin v5 (#2933, #3047, #3369, #3693, #3782)")
        self.assertEqual(block["origin"], {"contemporaneous": 3, "phase1_correction": 1, "phase3_backport": 0})
        self.assertEqual(block["snippets"], {"pre_draft": 3, "at_derive_core": 4, "final": 4})
        self.assertEqual((block["receipt"]["writes"], block["receipt"]["edits"]), (1, 1))
        self.assertEqual(block["non_write_mutations"], [])
        self.assertEqual([(e["tool_use_id"], e["tool"]) for e in block["replayed_edits"]], [(identity, "Edit")])
        self.assertEqual(set(block["replayed_edits"][0]), {"tool_use_id", "transcript", "line", "result_line",
                                                           "tool"})        # no payload
        self.assertIn("receipt rebuilt from 1 Write(s) and 1 replayed edit(s)", ro.summary(block))

    def test_an_edit_after_the_derive_is_a_phase3_backport(self):
        r = self._drafted()
        r.derive()
        r.edit(old_string=TITLE, new_string=TITLE + LICENSE)
        r.last_receipt = WITH_LICENSE
        block = r.report()
        self.assertEqual(block["status"], "checked", block["reasons"])
        self.assertEqual(block["origin"], {"contemporaneous": 3, "phase1_correction": 0, "phase3_backport": 1})
        self.assertEqual(block["post_draft_entries"][0]["slot"], "license")

    def test_a_multiedit_applies_its_edits_in_order(self):
        r = self._drafted()
        # The second edit's `old_string` exists only once the first has run.
        r.edit("MultiEdit", edits=[{"old_string": TITLE, "new_string": TITLE + "  - slot: lic\n"},
                                   {"old_string": "  - slot: lic\n", "new_string": LICENSE}])
        r.last_receipt = WITH_LICENSE
        block = r.report()
        self.assertEqual(block["status"], "checked", block["reasons"])
        self.assertEqual(block["origin"]["phase1_correction"], 1)
        self.assertEqual(block["replayed_edits"][0]["tool"], "MultiEdit")

    def test_replace_all_replaces_every_occurrence(self):
        r = self._drafted()
        self.assertEqual(PRE.count("status: extracted"), 2)
        r.edit(old_string="status: extracted", new_string="status: 'extracted'", replace_all=True)
        r.last_receipt = PRE.replace("status: extracted", "status: 'extracted'")
        block = r.report()
        self.assertEqual(block["status"], "checked", block["reasons"])
        self.assertEqual(block["origin"]["contemporaneous"], 3)
        self.assertEqual(block["receipt"]["rebuilt_sha256"], block["receipt"]["sha256"])

    def test_a_replay_that_is_not_exact_is_unknown(self):
        twice = PRE.replace(TITLE, TITLE + TITLE)
        for prior, inputs, metadata, why in (
                (PRE, {"old_string": "not in the receipt", "new_string": "x"}, None, "does not occur"),
                (twice, {"old_string": TITLE, "new_string": LICENSE}, None, "occurs 2 times"),
                (PRE, {"old_string": "", "new_string": "x"}, None,
                 "an empty `old_string` on a receipt that is not blank"),                  # #3588, #3604
                (PRE, {"old_string": None, "new_string": "x"}, None, "`old_string` that is not a string"),
                (PRE, {"old_string": TITLE, "new_string": 7}, None, "`new_string` that is not a string"),
                (PRE, {"old_string": TITLE, "new_string": LICENSE, "replace_all": "yes"}, None, "not a boolean"),
                (PRE, {"old_string": "OT2OD032701", "new_string": ""}, None, "may extend to the newline"),
                (PRE, {"old_string": "OT2OD032701", "new_string": "$&-2"}, None, "`$` pattern"),
                (PRE, {"old_string": TITLE, "new_string": TITLE + LICENSE},
                 {"filePath": "x", "originalFile": "something else"}, "`originalFile`"),
                (PRE, {"old_string": TITLE, "new_string": TITLE + LICENSE},
                 {"filePath": "x", "userModified": True}, "modified"),
                (PRE, {"old_string": TITLE, "new_string": TITLE + LICENSE},
                 {"filePath": "x", "staleRecovered": True}, "changed since it was read"),
                (PRE, {"old_string": TITLE, "new_string": TITLE + LICENSE},
                 {"filePath": "x", "oldString": "The CHORUS dataset"}, "a different edit"),
                (PRE, {"old_string": TITLE, "new_string": TITLE + LICENSE},
                 {"filePath": "x", "newString": TITLE}, "a different edit"),
                (PRE, {"old_string": TITLE, "new_string": TITLE + LICENSE},
                 {"filePath": "x", "replaceAll": True}, "a different edit")):
            with self.subTest(why=why, metadata=metadata):
                r = self.new_run()
                r.write(r.receipt, prior)
                r.write(r.full, "id: x\n")
                identity = r.edit(metadata=metadata, **inputs)
                block = r.report()
                self.assertUnknown(block, f"Edit {identity} of the receipt")
                self.assertUnknown(block, why)

    def test_matching_result_metadata_is_accepted(self):
        r = self._drafted()
        r.edit(old_string=TITLE, new_string=TITLE + LICENSE,
               metadata={"filePath": str(r.receipt), "oldString": TITLE, "newString": TITLE + LICENSE,
                         "replaceAll": False, "originalFile": PRE, "userModified": False, "staleRecovered": None})
        r.last_receipt = WITH_LICENSE
        self.assertEqual(r.report()["status"], "checked")

    def test_a_multiedit_step_that_cannot_be_replayed_is_named(self):
        r = self._drafted()
        r.edit("MultiEdit", edits=[{"old_string": TITLE, "new_string": TITLE + LICENSE},
                                   {"old_string": "absent", "new_string": "x"}])
        self.assertUnknown(r.report(), "edit 1: its `old_string` does not occur")

    def test_an_edit_with_no_earlier_state_is_unknown(self):
        r = self.run_
        r.receipt.write_text(PRE)
        r.edit(old_string=TITLE, new_string=TITLE + LICENSE)
        r.write(r.full, "id: x\n")
        r.last_receipt = WITH_LICENSE
        block = r.report()
        self.assertUnknown(block, "the first observed change of the receipt is an edit")
        self.assertIsNone(block["receipt"]["rebuilt_sha256"])
        self.assertEqual(block["replayed_edits"], [])                             # #3589
        self.assertEqual(len(block["unreplayed_edits"]), 1)
        self.assertFalse(any("rebuilt from" in x for x in ro.summary(block)))

    def test_an_edit_that_creates_the_receipt_is_replayed_on_empty_text(self):
        # #3588: an empty `old_string` is accepted only on an absent file or
        # one blank under `trim()` (#3604), and the result is the call's own
        # `new_string`; never "the text it edited is not in the transcripts".
        for name, inputs in (("Edit", {"old_string": "", "new_string": PRE}),
                             ("MultiEdit", {"edits": [{"old_string": "", "new_string": PRE}]})):
            with self.subTest(tool=name):
                r = self.new_run()
                identity = r.edit(name, metadata={"filePath": str(r.receipt), "originalFile": None,
                                                  "userModified": False}, **inputs)
                r.last_receipt = PRE
                r.write(r.full, "id: x\n")
                block = r.report()
                self.assertEqual(block["status"], "checked", block["reasons"])
                self.assertEqual(block["origin"]["contemporaneous"], 3)
                self.assertEqual(block["receipt"]["rebuilt_sha256"], block["receipt"]["sha256"])
                self.assertEqual([e["tool_use_id"] for e in block["replayed_edits"]], [identity])

    def test_js_blank_is_javascripts_trim(self):
        # #3604: the runtime refuses an empty `old_string` only where
        # `content.trim() !== ""`. JavaScript trims BOM and every Zs space;
        # Python's `isspace` also counts the information separators, which
        # `trim()` keeps.
        for text in ("", " \n\t\r\v\f", "\u00a0\ufeff\u2028\u2029", "\u3000\u2003"):
            with self.subTest(text=repr(text)):
                self.assertTrue(ro._js_blank(text))
        for text in ("x", "  x\n", "\x1c", "\x85", "\u200b"):
            with self.subTest(text=repr(text)):
                self.assertFalse(ro._js_blank(text))

    def test_an_empty_old_string_on_a_blank_receipt_is_replayed(self):
        # #3604: a receipt left holding only whitespace is accepted by the
        # runtime, which writes the whole `new_string`.
        r = self._drafted()
        r.write(r.receipt, " \n\t\u3000\n")
        identity = r.edit(old_string="", new_string=WITH_LICENSE,
                          metadata={"filePath": str(r.receipt), "originalFile": " \n\t\u3000\n"})
        r.last_receipt = WITH_LICENSE
        block = r.report()
        self.assertEqual(block["status"], "checked", block["reasons"])
        self.assertEqual(block["receipt"]["rebuilt_sha256"], block["receipt"]["sha256"])
        self.assertEqual([e["tool_use_id"] for e in block["replayed_edits"]], [identity])

    def test_a_creating_edit_over_a_blank_file_is_replayed(self):
        # #3604: the file it created over was blank, not absent; its result
        # names that text as `originalFile`, which is not a mismatch.
        r = self.run_
        identity = r.edit(old_string="", new_string=PRE,
                          metadata={"filePath": str(r.receipt), "originalFile": "\n\n"})
        r.write(r.full, "id: x\n")
        r.last_receipt = PRE
        block = r.report()
        self.assertEqual(block["status"], "checked", block["reasons"])
        self.assertEqual(block["receipt"]["rebuilt_sha256"], block["receipt"]["sha256"])
        self.assertEqual([e["tool_use_id"] for e in block["replayed_edits"]], [identity])

    def test_an_edit_after_a_failed_one_and_a_later_write_is_replayed(self):
        # #3605: an edit after a failed replay is unreplayed only until the
        # next successful Write of the receipt; after it, the edit replays on
        # the Write's content.
        r = self._drafted()
        failed = r.edit(old_string="absent", new_string="x")
        r.write(r.receipt, PRE)
        after = r.edit(old_string=TITLE, new_string=TITLE + LICENSE)
        r.last_receipt = WITH_LICENSE
        block = r.report()
        self.assertUnknown(block, f"Edit {failed} of the receipt")
        self.assertEqual([e["tool_use_id"] for e in block["replayed_edits"]], [after])
        self.assertEqual([e["tool_use_id"] for e in block["unreplayed_edits"]], [failed])
        self.assertEqual(block["receipt"]["rebuilt_sha256"], block["receipt"]["sha256"])

    def test_an_opening_create_edit_that_cannot_be_replayed_names_the_replay(self):
        # #3588: the reason is the replay's, never the opening-edit one.
        r = self.run_
        identity = r.edit(old_string="", new_string=PRE,
                          metadata={"filePath": str(r.receipt), "originalFile": "stale text"})
        r.write(r.full, "id: x\n")
        r.last_receipt = PRE
        block = r.report()
        self.assertUnknown(block, f"Edit {identity} of the receipt")
        self.assertUnknown(block, "`originalFile`")
        self.assertFalse(any("first observed change" in x for x in block["reasons"]), block["reasons"])

    def test_edit_counts_and_the_summary_line(self):
        # #3590: `receipt.edits` counts every successful edit of the receipt,
        # and the summary line appears only where an edit was replayed.
        r = self._drafted()
        block = r.report()
        self.assertEqual((block["receipt"]["writes"], block["receipt"]["edits"]), (1, 0))
        self.assertEqual((block["replayed_edits"], block["unreplayed_edits"]), ([], []))
        self.assertFalse(any("replayed edit" in x or "not replayed" in x for x in ro.summary(block)))
        r.edit(old_string=TITLE, new_string=TITLE + LICENSE)
        r.edit(old_string="OT2OD032701", new_string="OT2OD032702")
        r.last_receipt = WITH_LICENSE.replace("OT2OD032701", "OT2OD032702")
        block = r.report()
        self.assertEqual(block["status"], "checked", block["reasons"])
        self.assertEqual((block["receipt"]["writes"], block["receipt"]["edits"]), (1, 2))
        self.assertEqual(len(block["replayed_edits"]), 2)
        self.assertIn("receipt rebuilt from 1 Write(s) and 2 replayed edit(s)", ro.summary(block))

    def test_an_edit_that_was_not_replayed_is_not_listed_as_replayed(self):
        # #3589: a failed replay, and an edit after it, are counted as edits
        # but listed under `unreplayed_edits`, and the summary never says the
        # receipt was rebuilt from them.
        r = self._drafted()
        replayed = r.edit(old_string=TITLE, new_string=TITLE + LICENSE)
        failed = r.edit(old_string="absent", new_string="x")
        after = r.edit(old_string=TITLE, new_string=TITLE)
        block = r.report(sync=False)
        self.assertUnknown(block, f"Edit {failed} of the receipt")
        self.assertEqual(block["receipt"]["edits"], 3)
        self.assertIsNone(block["receipt"]["rebuilt_sha256"])
        self.assertEqual([e["tool_use_id"] for e in block["replayed_edits"]], [replayed])
        self.assertEqual([e["tool_use_id"] for e in block["unreplayed_edits"]], [failed, after])
        self.assertEqual(set(block["unreplayed_edits"][0]), {"tool_use_id", "transcript", "line", "result_line",
                                                             "tool"})      # no payload
        lines = ro.summary(block)
        self.assertFalse(any("rebuilt from" in x for x in lines), lines)
        self.assertIn("2 successful edit(s) of the receipt not replayed", lines)

    def test_a_replayed_receipt_that_differs_from_disk_is_unknown(self):
        r = self._drafted()
        r.edit(old_string=TITLE, new_string=TITLE + LICENSE)
        r.receipt.write_text(PRE)                   # as if the edit had not landed
        self.assertUnknown(r.report(sync=False), "differs from the file on disk")

    def test_an_edit_in_flight_with_the_derive_is_unknown(self):
        r = self._drafted()
        derive = r.call("Bash", command=r.derive_command(), description="x")
        edit = r.edit(settle=False, old_string=TITLE, new_string=TITLE + LICENSE)
        r.result(derive, "out", {"stdout": "", "stderr": "", "interrupted": False}, is_error=False)
        r.result(edit, "ok", {"filePath": str(r.receipt)})
        r.last_receipt = WITH_LICENSE
        reasons = r.report()["reasons"]
        self.assertTrue(any(f"receipt Edit {edit} was in flight with the derive core boundary" in x
                            for x in reasons), reasons)
        self.assertFalse(any(f"receipt Write {edit}" in x for x in reasons), reasons)   # #3556

    def test_an_edit_in_flight_with_a_receipt_write_names_both_tools(self):
        # #3556: the pairwise reason names each call's own tool.
        r = self._drafted()
        edit = r.edit(settle=False, old_string=TITLE, new_string=TITLE + LICENSE)
        write = r.call("Write", file_path=str(r.receipt), content=WITH_LICENSE)
        r.result(edit, "ok", {"filePath": str(r.receipt)})
        r.result(write, "ok", {"type": "update", "filePath": str(r.receipt), "content": WITH_LICENSE})
        r.last_receipt = WITH_LICENSE
        self.assertUnknown(r.report(), f"receipt Edit {edit} and receipt Write {write} were in flight together")

    def test_a_dollar_amount_in_new_string_is_replayed(self):
        # #3555: with a string search pattern JavaScript expands only `$$`,
        # `$&`, `` $` `` and `$'`; `$1` and `$<name>` stay literal.
        for amount in ("awarded $10 million", "grant $1 of $<n>", "$0 cost"):
            with self.subTest(amount=amount):
                r = self.new_run()
                r.write(r.receipt, PRE)
                r.write(r.full, "id: x\n")
                added = f"  - slot: funders[0].amount\n    snippet: {amount}\n"
                r.edit(old_string=TITLE, new_string=TITLE + added)
                r.last_receipt = PRE.replace(TITLE, TITLE + added)
                block = r.report()
                self.assertEqual(block["status"], "checked", block["reasons"])
                self.assertEqual(block["receipt"]["rebuilt_sha256"], block["receipt"]["sha256"])

    def test_every_expanding_dollar_pattern_is_unknown(self):
        for pattern in ("$$", "$&", "$`", "$'"):
            with self.subTest(pattern=pattern):
                r = self.new_run()
                r.write(r.receipt, PRE)
                r.write(r.full, "id: x\n")
                r.edit(old_string="OT2OD032701", new_string=f"OT2OD032701 {pattern}")
                self.assertUnknown(r.report(), "`$` pattern")

    def test_a_relative_edit_with_no_working_directory_is_unknown(self):
        # #3558: the edit branch's own relative-path reason.
        for name, inputs in (("Edit", {"old_string": TITLE, "new_string": TITLE + LICENSE}),
                             ("MultiEdit", {"edits": [{"old_string": TITLE, "new_string": TITLE + LICENSE}]})):
            with self.subTest(tool=name):
                r = self.new_run()
                r.write(r.receipt, PRE)
                r.write(r.full, "id: x\n")
                del r.events[0]["cwd"]
                rel = str(r.receipt.relative_to(r.root))
                identity = r.call(name, file_path=rel, **inputs)
                r.result(identity, "ok", {"filePath": rel, "userModified": False})
                r.last_receipt = WITH_LICENSE
                self.assertUnknown(r.report(), f"{name} {identity} names the receipt by a relative path "
                                               "with no working directory")

    def test_a_malformed_multiedit_is_unknown(self):
        # #3558: the `edits` shape guard.
        for edits in (None, "x", [], [{"old_string": TITLE, "new_string": TITLE + LICENSE}, "x"]):
            with self.subTest(edits=edits):
                r = self.new_run()
                r.write(r.receipt, PRE)
                r.write(r.full, "id: x\n")
                identity = r.edit("MultiEdit", edits=edits)
                block = r.report(sync=False)
                self.assertUnknown(block, f"MultiEdit {identity} of the receipt")
                self.assertUnknown(block, "its `edits` is not a non-empty list of mappings")

    def test_an_edit_of_the_full_record_is_not_replayed(self):
        # Only the receipt is rebuilt: an edit of the full record before its
        # first Write is still a change the history cannot place.
        r = self.run_
        r.write(r.receipt, PRE)
        identity = r.call("Edit", file_path=str(r.full), old_string="a", new_string="b")
        r.result(identity, "ok", {"filePath": str(r.full)})
        r.write(r.full, "id: x\n")
        self.assertUnknown(r.report(), "may change the full record other than by a Write")


class MovedArtifacts(Base):
    """`receipt_at_run` / `full_at_run` name the files as the transcript
    spelled them, for artifacts moved since the run (#3047)."""

    def _moved(self):
        r = self.run_
        r.write(r.receipt, PRE)
        r.write(r.full, "id: x\n")
        r.derive()
        r.edit(old_string=TITLE, new_string=TITLE + LICENSE)
        r.receipt.write_text(WITH_LICENSE)
        r.full.write_text("id: x\n")
        moved = r.root / "moved"
        moved.mkdir()
        receipt, full = moved / r.receipt.name, moved / r.full.name
        r.receipt.rename(receipt)
        r.full.rename(full)
        return r, receipt, full

    def test_without_the_spelling_a_moved_run_is_unknown(self):
        r, receipt, full = self._moved()
        self.assertUnknown(ro.origin([r.transcript()], receipt, full), "no successful Write of the full record")

    def test_the_spelling_matches_the_transcript_and_the_moved_receipt_is_hashed(self):
        r, receipt, full = self._moved()
        block = ro.origin([r.transcript()], receipt, full, receipt_at_run=r.receipt, full_at_run=r.full)
        self.assertEqual(block["status"], "checked", block["reasons"])
        self.assertEqual(block["origin"]["phase3_backport"], 1)
        self.assertEqual((block["receipt"]["path"], block["receipt"]["at_run"]), (str(receipt), str(r.receipt)))
        self.assertEqual(block["full"]["at_run"], str(r.full))

    def test_the_cli_takes_the_spellings(self):
        from data_sheets_schema.cli.receipts import receipts
        r, receipt, full = self._moved()
        out = CliRunner().invoke(receipts, ["origin", "--transcript", str(r.transcript()), "--receipt", str(receipt),
                                            "--full", str(full), "--receipt-at-run", str(r.receipt),
                                            "--full-at-run", str(r.full), "--json"])
        self.assertEqual(out.exit_code, 0, out.output)
        self.assertEqual(json.loads(out.output)["status"], "checked")


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

    def test_a_successful_derive_followed_by_arithmetic_is_the_boundary(self):
        # Arithmetic's `((` and `))` are words, not joins, so a `$((...))`
        # or `(( ... ))` after `&&` keeps the derive's and_chain basis (#3840).
        for tail in (" && echo $((1+1))", " && sleep $((2))", " && (( i++ ))"):
            with self.subTest(tail=tail):
                self.run_ = self.new_run()
                identity, block = self._around(lambda r: r.derive_command() + tail)
                self.assertEqual(block["status"], "checked", block["reasons"])
                self.assertEqual(block["boundaries"]["derive_core"]["tool_use_id"], identity)
                self.assertEqual(block["boundaries"]["derive_core"]["status_basis"], "and_chain")

    def test_a_derive_last_after_cd_carries_its_own_status(self):
        for ok, boundary_is_first in ((True, True), (False, False)):
            with self.subTest(ok=ok):
                self.run_ = self.new_run()
                identity, block = self._around(
                    lambda r: f"cd {r.root} && " + r.derive_command().replace("poetry run ", "", 1), ok=ok)
                self.assertEqual(block["status"], "checked", block["reasons"])
                attempt = block["derive_core_attempts"][0]
                self.assertEqual((attempt["status_basis"], attempt["outcome"]),
                                 ("command", "succeeded" if ok else "failed"))
                self.assertEqual(block["boundaries"]["derive_core"]["tool_use_id"] == identity, boundary_is_first)
                self.assertEqual(block["origin"]["phase3_backport" if ok else "phase1_correction"], 1)

    def test_a_poetry_run_derive_after_cd_that_failed_may_have_run_another_projects_d4d(self):
        # After `cd`, `poetry run` takes the virtualenv of the project the new
        # directory is in (#3723). A successful derive of the tracked record
        # is the boundary whatever ran it; a failed one is not, and may have
        # derived the record through another project's `d4d`.
        for ok in (True, False):
            with self.subTest(ok=ok):
                self.run_ = self.new_run()
                identity, block = self._around(lambda r: f"cd {r.root} && " + r.derive_command(), ok=ok)
                if ok:
                    self.assertEqual(block["status"], "checked", block["reasons"])
                    self.assertEqual(block["boundaries"]["derive_core"]["tool_use_id"], identity)
                    self.assertEqual(block["possible_unseen_derives"], [])
                else:
                    self.assertUnknown(block, f"Bash call {identity} (transcript 0 line 6) runs a program this "
                                              "does not read")
                    self.assertEqual([row["tool_use_id"] for row in block["possible_unseen_derives"]], [identity])

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

    def test_a_derive_backgrounded_by_its_input_is_ambiguous_without_metadata(self):
        # The result's metadata is per event; the call's own input still says
        # its result is the launch (#3744).
        r = self.run_
        r.write(r.receipt, PRE)
        r.write(r.full, "id: x\n")
        r.write(r.receipt, Boundaries.C003)
        identity = r.call("Bash", command=r.derive_command(), description="x", run_in_background=True)
        r.result(identity, "Command running in background with ID: bg1", is_error=False)
        block = r.report()
        self.assertUnknown(block, f"derive core {identity} cannot be placed: its result is ambiguous")
        # Anything but absent or `false` asks for the background, as the
        # native phase history reads the flag.
        self.assertEqual(ro._backgrounded(None, {"run_in_background": "yes"}), True)
        self.assertEqual(ro._backgrounded(None, {"run_in_background": ""}), True)
        self.assertEqual(ro._backgrounded({"metadata": ro._ABSENT}, {"run_in_background": False}), False)
        self.assertEqual(ro._shell_outcome({"is_error": False, "metadata": ro._ABSENT},
                                           {"run_in_background": True}), "ambiguous")
        self.assertEqual(ro._shell_outcome({"is_error": False, "metadata": ro._ABSENT}), "succeeded")

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
                 "d4d derive core --full F # then | tail ; echo": "command",
                 # arithmetic's brackets are words, not joins (#3840)
                 "d4d derive core --full F && echo $((1+1))": "and_chain",
                 "(( n = 1 )) ; d4d derive core --full F": "command",
                 "d4d derive core --full F && echo $(pwd)": "none"}
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
        identity, block = self._derived("pushd /elsewhere && d4d derive core "
                                        "--full data/claudecode_direct/L/CHORUS_d4d.yaml")
        # Another record derived: no boundary, both later snippets Phase 1.
        self.assertEqual(block["status"], "checked", block["reasons"])
        self.assertIsNone(block["boundaries"]["derive_core"])
        self.assertEqual(block["origin"], {"contemporaneous": 3, "phase1_correction": 2,
                                           "phase3_backport": 0})
        self.assertEqual(block["possible_unseen_derives"], [])
        # Through `poetry run` the d4d that runs is the one the project
        # `/elsewhere` is in installs, which may derive the tracked record:
        # the call is a possible derive (#3723).
        identity, block = self._derived("pushd /elsewhere && poetry run d4d derive core "
                                        "--full data/claudecode_direct/L/CHORUS_d4d.yaml")
        self.assertUnknown(block, f"Bash call {identity} (transcript 0 line 8) runs a program this does not read")
        self.assertEqual([row["tool_use_id"] for row in block["possible_unseen_derives"]], [identity])

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
                         f"pushd /elsewhere; popd; poetry run d4d derive core --full {self.FULL}",
                         f"cd data && echo a ; poetry run d4d derive core --full claudecode_direct/L/CHORUS_d4d.yaml",
                         f"cd /elsewhere\npoetry run d4d derive core --full {self.FULL}",
                         "cd data\npoetry run d4d derive core --full claudecode_direct/L/CHORUS_d4d.yaml",
                         # A change in a subshell, a pipe's left side or a `&`
                         # job does not move this shell, but which parts a child
                         # runs is not read, so it counts (#3810, #3830).
                         f"(cd /elsewhere) && poetry run d4d derive core --full {self.FULL}",
                         f"cd /elsewhere & poetry run d4d derive core --full {self.FULL}",
                         f"cd /elsewhere | cat && poetry run d4d derive core --full {self.FULL}"):
            with self.subTest(spelling=spelling):
                identity, block = self._derived(spelling)
                # Not dropped as another record's: the derive cannot be placed
                # (by its --full, or also by its status where that is not its own).
                self.assertUnknown(block, f"derive core {identity} cannot be placed")
                self.assertIsNone(block["derive_core_attempts"][0]["targets_full"])

    #: Commands in which reading a part as run in a child, or as a case
    #: pattern, placed a relative `--full` after a change bash runs in this
    #: shell (#3904, #3911, #3912): a `|` split out of a backquote, a
    #: `${...}` or an arithmetic `$((...))`, and a here-document body line
    #: read as a case clause. None of them may be placed.
    SPLIT_CDS = ("cd `git rev-parse --show-toplevel | head -1`", "cd `ls -d d* | head -1`", "cd ${D//a|b/}",
                 "cd sub$((0|cat))", "cd $((1|false))", "cd $((1|cat))", "cd $((x|head))",
                 "cat > notes.md <<EOF\ncase in point: the run\nEOF\n{ cd sub; }",
                 "cat > notes.md <<EOF\ncase in point: the run\nEOF\neval \"cd $D\"",
                 "cat > notes.md <<EOF\ncase in point: the run\nEOF\n$GO sub",
                 "cat > notes.md <<EOF\ncase in point: the run\nEOF\nsource env.sh",
                 "cat > notes.md <<EOF\ncase in point: the run\nEOF\nmyfunc")

    def test_a_change_read_through_a_split_word_or_a_case_line_still_counts(self):
        # The derive runs wherever the change left it, so its relative
        # `--full` is placed neither in this call nor in the next (#3904,
        # #3911, #3912).
        target = [ro._Target("full", "/w/data/F.yaml")]
        for cd in self.SPLIT_CDS:
            with self.subTest(cd=cd):
                out = ro._shell(f"{cd} && d4d derive core --full data/F.yaml", "/w", target)
                self.assertIs(out["moves"], True)
                self.assertEqual([row["targets_full"] for row in out["derives"]], [None])
                identity, block = self._derived(f"{cd} && poetry run d4d derive core --full {self.FULL}")
                self.assertUnknown(block, f"derive core {identity} cannot be placed")
                self.assertIsNone(block["derive_core_attempts"][0]["targets_full"])
                self.assertIsNone(block["boundaries"]["derive_core"])

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
                 # a change in a subshell, a pipe's left side or a `&` job
                 # does not move this shell, but which parts a child runs is
                 # not read, so it counts (#3810, #3830)
                 "(cd /x) && d4d derive core --full data/F.yaml": None,
                 "cd /x | d4d derive core --full data/F.yaml": None,
                 "cd /x & d4d derive core --full data/F.yaml": None,
                 "X=$(cd /x; pwd) && d4d derive core --full data/F.yaml": None,
                 "(cd /x) ; (cd /y) && d4d derive core --full data/F.yaml": None,
                 "(cd /x && d4d derive core --full data/F.yaml)": None,
                 "(cd /x; (d4d derive core --full data/F.yaml))": None,
                 "cd data && (cd /x) && d4d derive core --full F.yaml": None,
                 "case x in a) cd /x;; esac; d4d derive core --full data/F.yaml": None,
                 "pushd /x; popd && d4d derive core --full data/F.yaml": None,
                 "pushd data && pushd /x ; popd && d4d derive core --full F.yaml": None,
                 "cd data\nd4d derive core --full F.yaml": None,
                 # a here-document's lines read as parts: no change in a
                 # multi-line command is trusted, even one `&&` guards
                 "echo a\ncd data && d4d derive core --full F.yaml": None,
                 # a skipped pushd pushed nothing; a skipped popd popped nothing
                 "true || pushd /x && popd && d4d derive core --full data/F.yaml": None,
                 "pushd data && true || popd && d4d derive core --full F.yaml": None,
                 "echo a\nd4d derive core --full /r/data/F.yaml": True,
                 # a `|` inside a backquote or a `${...}` is no pipe (#3904)
                 "cd `git rev-parse --show-toplevel | head -1` && d4d derive core --full data/F.yaml": None,
                 "cd `ls -d d* | head -1` && d4d derive core --full data/F.yaml": None,
                 "cd ${D//a|b/} && d4d derive core --full data/F.yaml": None,
                 "cd ${D} | cat && d4d derive core --full data/F.yaml": None,
                 # nor inside an arithmetic `$((...))` (#3912)
                 "cd $((1|false)) && d4d derive core --full data/F.yaml": None}
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
    the status `checked` (#3137). The `timeout`, `env` and `nice` wrappers are
    read through; a derive whose program is a variable or a relative path
    (`$PY -m data_sheets_schema.cli`, `./d4d`) is read but not placed, as that
    program may be a wrapper (#3693); any other part that carries the words
    `derive core` is a derive that cannot be placed."""

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

    def test_wrapped_and_interpreter_spellings_are_the_boundary(self):
        derive = f"derive core --full {self.FULL} {self.OUT}"
        for spelling in (f"timeout 600 poetry run d4d {derive}",
                         f"timeout -s KILL --preserve-status 10m d4d {derive}",
                         f"timeout --kill-after=5 1.5h d4d {derive}",
                         f"env PYTHONPATH=src python -m data_sheets_schema.cli {derive}",
                         f"env -i -u HOME -- D4D_PROFILE=bridge2ai poetry run d4d {derive}",
                         # An interpreter named by a bare word or an absolute
                         # path is taken to be one (#3693).
                         f"python3 -m data_sheets_schema.cli {derive}",
                         f"/venv/bin/python3.12 -m data_sheets_schema.cli {derive}",
                         f"timeout 60 /venv/bin/python -m data_sheets_schema.cli {derive}",
                         f"nice -n 10 d4d {derive}",
                         f"nice -5 poetry run d4d {derive}",
                         f"X=1 timeout 60 env Y=2 nice d4d {derive} && d4d receipts check --label L",
                         # #3478: redirections after the call's words leave it read as written
                         f"poetry run d4d {derive} 2>&1",
                         f"poetry run d4d {derive} > /tmp/derive-3374.log 2>&1",
                         f"poetry run d4d {derive} 2 >& 1"):
            with self.subTest(spelling=spelling):
                identity, block = self._derived(spelling)
                self.assertEqual(block["status"], "checked", block["reasons"])
                self.assertEqual(block["boundaries"]["derive_core"]["tool_use_id"], identity)
                self.assertEqual(block["origin"], {"contemporaneous": 3, "phase1_correction": 1,
                                                   "phase3_backport": 1})

    def test_a_derive_whose_program_is_a_variable_or_relative_path_is_not_placed(self):
        # `$PY` may name a wrapper rather than an interpreter, as `./d4d` may
        # name any program: the derive the words spell may not have run, so
        # the row places nothing and the block is `unknown` (#3693).
        derive = f"derive core --full {self.FULL} {self.OUT}"
        for spelling in (f"$PY -m data_sheets_schema.cli {derive}",
                         f"${{PY}} -m data_sheets_schema.cli {derive}",
                         f"timeout 60 $PY -m data_sheets_schema.cli {derive}",
                         f"$PY -m data_sheets_schema.cli {derive} && echo done",
                         f"./python -m data_sheets_schema.cli {derive}",
                         f"./d4d {derive}", f"bin/d4d {derive}", f"./timeout 60 d4d {derive}",
                         f"$NICE d4d {derive}"):
            with self.subTest(spelling=spelling):
                identity, block = self._derived(spelling)
                self.assertIsNone(block["boundaries"]["derive_core"])
                if spelling.startswith("$NICE"):
                    # Not read as the CLI at all: the words make it a derive
                    # that cannot be placed (#3137).
                    self.assertUnknown(block, f"derive core {identity} cannot be placed")
                    continue
                self.assertUnknown(block, f"derive core {identity} cannot be placed: the call succeeded but its "
                                          "status is not the derive's own (unnamed_program: its program is a "
                                          "variable or a relative path")
                attempt = block["derive_core_attempts"][0]
                self.assertEqual((attempt["targets_full"], attempt["status_basis"], attempt["outcome"]),
                                 (None, "unnamed_program", "ambiguous"))
        # One the native control refused never ran, whatever its program.
        identity, block = self._derived(f"$PY -m data_sheets_schema.cli {derive}", ok=False,
                                        content=ro.NATIVE_DENIAL_PREFIX + "not registered",
                                        metadata="Error: " + ro.NATIVE_DENIAL_PREFIX)
        self.assertEqual(block["status"], "checked", block["reasons"])
        self.assertEqual(block["derive_core_attempts"][0]["outcome"], "failed")

    def test_names_its_program(self):
        full = ro._Target("full", Path("/w/data/claudecode_direct/L/CHORUS_d4d.yaml"))
        cases = {"d4d x": True, "/venv/bin/d4d x": True, "python -m data_sheets_schema.cli x": True,
                 "X=1 timeout 60 env Y=2 nice poetry run d4d x": True,
                 "$PY -m data_sheets_schema.cli x": False, "${PY} -m data_sheets_schema.cli x": False,
                 "./d4d x": False, "bin/python -m data_sheets_schema.cli x": False,
                 "./timeout 60 d4d x": False, "timeout 60 $PY -m x": False, "": False}
        for command, named in cases.items():
            with self.subTest(command=command):
                self.assertEqual(ro._names_its_program(ro._tokens(command) or []), named)
        # A read-only subcommand is read-only only where the program runs as
        # its words name it; one aimed at another record keeps its placement.
        for command, read_only in (("python -m data_sheets_schema.cli receipts check --receipt R", True),
                                   ("$PY -m data_sheets_schema.cli receipts check --receipt R", False),
                                   ("./d4d receipts check --receipt R", False)):
            with self.subTest(command=command):
                self.assertEqual(ro._shell(command, "/w", [full])["read_only"], read_only)
        other = ro._shell("$PY -m data_sheets_schema.cli derive core --full /o/f.yaml", "/w", [full])
        self.assertEqual([(d["targets_full"], d["basis"]) for d in other["derives"]], [(False, "command")])
        self.assertTrue(other["runs_unread"])                                        # #3722
        # The recorder's `--phase 'derive core'` beside a variable program
        # is a derive that cannot be placed: the backstop reads a `$`
        # invocation (#3478).
        phase = ro._shell("$PY -m data_sheets_schema.cli provenance record --phase 'derive core'", "/w", [full])
        self.assertEqual([(d["targets_full"], d["basis"]) for d in phase["derives"]], [(None, "unparsed")])

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
                         f"xargs d4d derive < /tmp/args-3374",
                         # #3457: a quoted redirection target holding spaces is re-split,
                         # so a redirection directly after the derive is enough
                         f"xargs d4d derive <<< \"core --full {self.FULL} {self.OUT}\"",
                         f"xargs d4d derive <<< 'core --full {self.FULL} {self.OUT}'",
                         "xargs d4d derive < \"/tmp/my args-3374.txt\"",
                         # #3458: a command shlex cannot split (an apostrophe in a
                         # here-document body) is tested whole for the words
                         f"cat > /tmp/notes-3374.txt <<EOF\nit's done\nEOF\n"
                         f"poetry run d4d derive core --full {self.FULL} {self.OUT}",
                         f"cat > /tmp/notes-3374.txt <<EOF\nit's done\nEOF\n"
                         f"poetry run d4d derive \"core\" --full {self.FULL} {self.OUT}",
                         f"cat > /tmp/notes-3374.txt <<EOF\nit's done\nEOF\n"
                         f"poetry run d4d derive $SUB --full {self.FULL} {self.OUT}"):
            for ok in (True, False):
                with self.subTest(spelling=spelling, ok=ok):
                    # `poetry run d4d derive` carries no `derive core` words, but the
                    # command-wide backstop (#3478-#3480) reads it as a derive that
                    # cannot be placed; before the backstop it was no derive at all.
                    identity, block = self._derived(spelling, ok=ok)
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
        # An absolute `--full`: an earlier call here may run a function or a sourced
        # script, which may change directory, so a relative one is not placed (#3782).
        for spelling in ("grep -n 'derive core' .claude/commands/d4d-full-core.md",
                         "echo derive core && printf '%s\\n' 'derive core'",
                         "sed -n '/derive core/,+3p' .claude/commands/d4d-full-core.md",
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
                         "poetry run d4d receipts check --label \"$L\" --project CHORUS",
                         # #3426: an xargs replacement string or appended word that is not
                         # the word after `derive` supplies nothing to it
                         "ls | xargs -I% python scripts/derive corex %",
                         "ls | xargs grep -n derive x.md",
                         "ls | xargs -I% cat %; python scripts/derive corex %",
                         # #3458: a command shlex cannot split, without the words
                         "cat > /tmp/notes-3374.txt <<EOF\nit's done\nEOF\nls",
                         "cat > /tmp/notes-3374.txt <<EOF\nit's derived\nEOF\npython scripts/derive corex"):
            with self.subTest(spelling=spelling):
                r = self.new_run()
                r.write(r.receipt, PRE)
                r.write(r.full, "id: x\n")
                r.write(r.receipt, Boundaries.C003)
                r.bash(spelling)
                identity = r.derive(full=r.full)
                r.write(r.receipt, Boundaries.C004)
                block = r.report()
                self.assertEqual(block["status"], "checked", block["reasons"])
                self.assertEqual([a["tool_use_id"] for a in block["derive_core_attempts"]], [identity])

    def test_the_command_wide_backstop_catches_what_the_parts_miss(self):
        # #3478-#3480: Codex's reproductions, each read as `checked` with the
        # Phase 3 entry counted as Phase 1 before the backstop.
        for spelling in (f"d4d derive 2>/dev/null core --full {self.FULL} {self.OUT}",            # #3478
                         f"d4d derive core --full 2>/dev/null {self.FULL} {self.OUT}",            # #3478
                         f"result=\"$(d4d derive core --full {self.FULL} {self.OUT})\"",          # #3479
                         f"printf 'core\\n' | xargs -I'|' d4d derive '|' --full {self.FULL} {self.OUT}",  # #3480
                         # #3479: a cd part, and other assignments
                         f"cd \"$(d4d derive core --full {self.FULL} {self.OUT})\"",
                         f"export X=\"$(d4d derive core --full {self.FULL} {self.OUT})\"",
                         f"X=`poetry run d4d derive core --full {self.FULL} {self.OUT}`",
                         # #3480: the other operator placeholders
                         f"printf 'core\\n' | xargs -I';' d4d derive ';' --full {self.FULL} {self.OUT}",
                         f"printf 'core\\n' | xargs -I'&' d4d derive '&' --full {self.FULL} {self.OUT}",
                         # a `$`-variable invocation, and data_sheets_schema
                         f"$D4D derive 2>/dev/null core --full {self.FULL} {self.OUT}",
                         f"python -m data_sheets_schema.cli derive 2>/dev/null core --full {self.FULL} {self.OUT}",
                         # a command the tokenizer cannot split, whose words no rule matches
                         f"cat > /tmp/notes-3374.txt <<EOF\nit's done\nEOF\n"
                         f"d4d derive 2>/dev/null core --full {self.FULL} {self.OUT}"):
            for ok in (True, False):
                with self.subTest(spelling=spelling, ok=ok):
                    identity, block = self._derived(spelling, ok=ok)
                    self.assertUnknown(block, f"derive core {identity} cannot be placed")
                    self.assertIn("the command-wide backstop", " ".join(block["reasons"]))
                    self.assertEqual([(a["targets_full"], a["status_basis"], a["outcome"])
                                      for a in block["derive_core_attempts"]], [(None, "unparsed", "ambiguous")])

    def test_a_row_for_one_derive_does_not_account_for_another(self):
        # Codex review of #3374: `--help` (or another record's derive) gave a
        # row, so the backstop, which then fired only on a call with no row,
        # let the assignment's real derive through as `checked`.
        for spelling in (f"d4d derive core --help && result=\"$(d4d derive core --full {self.FULL} {self.OUT})\"",
                         f"d4d derive core --full other_d4d.yaml other_core.yaml && "
                         f"X=`d4d derive core --full {self.FULL} {self.OUT}`"):
            for ok in (True, False):
                with self.subTest(spelling=spelling, ok=ok):
                    identity, block = self._derived(spelling, ok=ok)
                    self.assertUnknown(block, f"derive core {identity} cannot be placed")
                    self.assertIn("unparsed", [a["status_basis"] for a in block["derive_core_attempts"]])

    def test_the_backstops_cost_is_a_false_unknown(self):
        # These run no derive, but the word `derive` sits beside a d4d or `$`
        # invocation, so the backstop reads each as one that cannot be placed.
        # The first three were `checked` (not a derive) before #3478-#3480.
        for spelling in ("poetry run d4d provenance record --project CHORUS --label L "
                         "--phase '{\"name\": \"derive core\"}'",
                         "poetry run d4d receipts check --label L --project CHORUS --note 'after derive core'",
                         "grep -n \"derive $x\" x.md",
                         "grep 'd4d derive core' notes.md"):
            with self.subTest(spelling=spelling):
                identity, block = self._derived(spelling)
                self.assertUnknown(block, f"derive core {identity} cannot be placed")
                self.assertEqual(block["derive_core_attempts"][0]["status_basis"], "unparsed")

    def test_backstop(self):
        cases = {"d4d derive core": True, "x=\"$(d4d derive core)\"": True, "cd $(d4d derive core)": True,
                 "printf core | xargs -I'|' d4d derive '|'": True, "$PY -m x derive": True,
                 "${PY} derive": True, "python -m data_sheets_schema.cli derive": True,
                 "d4d de\"\"rive core": True, "/venv/bin/d4d derive": True,
                 # no invocation of the CLI at all: the one exception
                 "grep -n 'derive core' notes.md": False, "python scripts/derive corex": False,
                 "cat .claude/commands/d4d-full-core.md | grep derive": False,
                 # `derive` only inside a longer word
                 "d4d rederive core": False, "d4d derive_core": False, "d4d derive-core": False,
                 "d4d derive.py": False, "d4d receipts check": False,
                 # `d4d` only inside a longer word
                 "cd d4d-executions && grep derive x": False, "ls data/d4d_concatenated derive": False}
        for command, expected in cases.items():
            with self.subTest(command=command):
                self.assertIs(ro._backstop(command), expected)

    def test_redirection_interleaved(self):
        cases = {"core --full F --out O": False, "core --full F --out O 2 >& 1": False,
                 "core --full F --out O > log 2 >& 1": False, "core --full F < in": False,
                 "core --full 2 > /dev/null F --out O": True, "2 > /dev/null core --full F": True,
                 "core --full F > log --out O": True, "core --full F &> log x": True}
        for words, expected in cases.items():
            with self.subTest(words=words):
                self.assertIs(ro._redirection_interleaved(words.split()), expected)

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
                 "xargs d4d derive full 2>&1": False, "xargs d4d derive <(ls)": False,
                 # #3457: a redirection directly after the derive counts whatever follows
                 # it, since a quoted target arrives re-split into several words
                 "xargs d4d derive <<< core --full F --out O": True,
                 "xargs d4d derive < my args.txt": True, "xargs d4d derive > my log.txt": True,
                 "xargs d4d derive 2 > my log.txt": True, "xargs -I% d4d derive > log": True,
                 "xargs d4d derive 2> err full": True, "xargs d4d derive >log full": True,
                 "ls > derive.log; xargs d4d derive full": False,
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
        self.assertIn("One run without the words `derive core` on the command line", text)
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
        self.assertIn("a file that an earlier call wrote the words into and a later call runs", text)
        # #3397: the quote rule, the run-time word and the route still unseen
        self.assertIn("The words are matched after quote and escape characters are removed", text)
        self.assertIn("`xargs ... derive {}`) counts as a derive that cannot be placed", text)
        self.assertIn("a variable or substitution supplying the word `derive` itself", text)
        # #3426: any xargs replacement string, and the one xargs route still unseen
        self.assertIn("as does a word carrying any replacement string an `xargs` in the command sets "
                      "(`xargs -I% ... derive %`, `-J %`, `-i`, `--replace`)", text)

        # #3453: the appended-word rule reads the command with its redirections aside
        self.assertIn("redirections (`2>&1`, `>log`, `< args`) aside, since they are the shell's (#3453)", text)
        self.assertIn("ends it once the shell's redirections are set aside", doc)
        # #3457, #3458: a redirection directly after the derive, and a command
        # the tokenizer cannot split, and what stays unseen
        self.assertIn("and a `derive` with a redirection directly after it in an xargs command, "
                      "whatever follows (#3457)", text)
        self.assertIn("A command the tokenizer cannot split (an apostrophe in a here-document body) is "
                      "tested whole, quote characters removed, by the same rules (#3458)", text)
        # #3478-#3480: the command-wide backstop, its cost, and what no rule sees
        self.assertIn("Last, a command-wide backstop (#3478-#3480): a call carrying more whole-word `derive`s "
                      "than these rules gave rows, whose raw text, quote and escape characters removed, carries the word `derive` as a "
                      "whole word anywhere (in a substitution, an assignment, a `cd` part, an `xargs` "
                      "argument) beside a `d4d`, `data_sheets_schema` or `$`-variable invocation, is one "
                      "derive that cannot be placed; its cost is a false `unknown` (`grep 'd4d derive core' "
                      "notes.md`", text)
        self.assertIn("A derive call with a redirection among its words (`--full 2>/dev/null F`) cannot be "
                      "placed (#3478)", text)
        self.assertIn("what no word rule sees is a command with no whole word `derive`, or with one but no such "
                      "invocation (a script, alias or program under another name: `run.sh derive core`), which is "
                      "left to the position rule", text)
        # #3369: a derive with no words on the command line is placed by position
        self.assertNotIn("such a derive is not seen, and the Phase 1 / Phase 3 boundary is missed", text)
        self.assertIn("is not placed by the words (#3137, #3384) but by position (#3369): a shell call that runs a "
                      "program not read here -- neither a reader, a directory change (the builtin `cd`, "
                      "`pushd` or `popd`; a path-qualified lookalike, `./cd`, or `poetry run cd`, is a program "
                      "not read, #3753), a d4d call of a literal subcommand, nor `linkml-validate` or `linkml-term-validator` with options read here, "
                      "each counted only where it runs what its words name: a bare name or an absolute path as "
                      "its program, never a variable or a relative path (`$PY`, `./python`), and no assignment "
                      "before it or as an earlier part (`PYTHONPATH=./hack`, `PATH=./bin:$PATH;`, `printf -v "
                      "PATH`), #3689, #3700, nor, for a `python -c` or `python -m` part, a directory change "
                      "before it in the command, since the interpreter imports from the directory it starts in "
                      "first (#3699), nor, for a part run through `poetry run`, one either, since poetry takes "
                      "its virtualenv from the project that directory is in (#3723), a d4d `derive core` call "
                      "aimed at another record included (#3722) -- or runs a command or process substitution, "
                      "whose inner command is not "
                      "read (#3675), or cannot be split by the tokenizer, that "
                      "had not returned when the draft was issued (one issued before the draft that returned "
                      "after it, or one whose run is open-ended, counts: #3676), was issued before the derive "
                      "boundary, and has a receipt change issued before that boundary returning after both it "
                      "and the draft were issued (#3697), is a "
                      "reason; its cost is a false `unknown` for such a program that derived nothing", text)
        self.assertNotIn("issued after the draft and before the derive boundary", text)
        # #3674: what makes a call's run open-ended, and the detach it cannot see
        self.assertIn("where the runtime backgrounded it (its `run_in_background` input or its result's "
                      "metadata says so, #3744), a part is started with `&` (at the top level, or ending a "
                      "command inside a word a nested shell may run: `bash -c './derive.sh &'`, and, as that "
                      "shell splits a word with a space in it, `bash -c './derive.sh&echo started'` (#3745); "
                      "in a word with no space, in a word inside that one that no program in it runs as a "
                      "command (the argument a shell program's `-c` receives there, and `eval`'s and "
                      "`ssh`'s, are read by the whole rule in turn, however deep, #3748: `bash -c \"bash -c "
                      "'./derive.sh&echo x'\"`), and in a command the tokenizer cannot split, only a `&` "
                      "followed by a space, `)`, `}`, `;`, `#` or the end counts, so `R&D` does not) or by "
                      "`coproc` (#3690), or a part's "
                      "program detaches what it runs (`setsid`, `daemon`, `disown`, `screen`, `tmux`, `at`, "
                      "`batch`, `systemd-run`, `start-stop-daemon`, #3674), read through `timeout`, `env`, "
                      "`nice`, `nohup`, `exec` and `command` and as a command's first word inside such a nested "
                      "word (#3690), or a part starts a process substitution, which bash does not wait for "
                      "(`true <(bash step.sh)`: a `<(` or `>(` outside quotes, anywhere after a command "
                      "substitution opens, or in a nested shell's word with a space in it, #3752), each read "
                      "in the words a nested shell runs as a command however deep (#3748), and a "
                      "command the tokenizer cannot split is open-ended where its whole text carries such a "
                      "`&`, `coproc`, detaching program, `<(` or `>(` (#3698, #3752); a script or program that "
                      "backgrounds or daemonises a child itself, or a "
                      "detaching program behind any other wrapper (`sudo`, `xargs`), is not seen as open-ended",
                      text)
        # #3689: an environment set outside the command is not read
        self.assertIn("Nor is an environment set outside the command (exported earlier or inherited) read: a "
                      "bare name is taken to be the program `PATH` finds, and an absolute path the program it "
                      "names (#3689); nor is a package in the directory the session's shell started in that a "
                      "`python -c` or `python -m` part imports before the installed one (a `linkml` or "
                      "`data_sheets_schema` directory there, #3699), nor the project there whose virtualenv a "
                      "`poetry run` part takes (#3723)", text)
        # #3719: a directory an earlier call left the shell in is read; #3782:
        # so is code a sourced script, a function or an alias may run there;
        # #3810 and #3824 stay open: a change in a child counts, and a
        # directory the call's own event records after a change is not
        # trusted.
        self.assertIn("A directory an earlier call left the shell in is read (#3719): after a call not denied "
                      "whose builtin `cd`, `pushd` or `popd`, or one `eval` runs or may run as a word supplied "
                      "at run time (`eval \"$X\"`, #3815), may leave anywhere but where it started (plain or "
                      "behind a brace, a compound keyword, `!`, `time`, `builtin` or `command`, #3797), or "
                      "which may run in that shell code not on its command line (#3782: `source` or `.`, or a "
                      "program named by a bare word not read here, which may be a function or an alias -- not "
                      "a path, a reader, a reserved word or builtin that changes no directory, `poetry run` or "
                      "a wrapper read here, a d4d call, a validator or arithmetic), such a part counts as after "
                      "a directory change and a relative `--full` cannot be placed. One in a subshell, an "
                      "unquoted command or process substitution (`(cd x)`, `$(cd x)`, `<(cd x)`), a pipe's left "
                      "side or a `&` job does not move the shell but counts all the same, the rule's cost: "
                      "which parts a child runs is not read from the tokenizer's brackets and joins, where a "
                      "`)`, `|` or `&` may come from a case pattern, a here-document body, a backquote, a "
                      "`${...}` or an arithmetic `$((...))` (#3810, #3904, #3911, #3912; it waits for a shell "
                      "grammar, #3830), and a case pattern is read as a command, so its word may count", text)
        self.assertIn("where both hold the earlier change decides and the `--full` is not placed, as a recorded "
                      "directory may be inherited from the init event and is not trusted after a change (#3812), "
                      "even one the call's own event records (#3824), a false `unknown` in a transcript that "
                      "records the directory on every event", text)
        self.assertIn("and a command the tokenizer cannot split counts, whatever its words (#3782)", text)
        self.assertIn("Still not read: a function or alias named as a program read here (`cat() { cd x; }`), "
                      "defined in the session or by the profile the session's shell started with; a program bash "
                      "builds at run time behind `nohup`, `exec` or `command` (`nohup $X ./derive.sh`), which is "
                      "not read as detaching; and, in a command the tokenizer cannot split, a program word built "
                      "other than from a leading `$` or backquote (`set${X}sid`, a glob, a brace expansion), "
                      "which is not read as detaching there (#3923); a brace expansion with a quoted or escaped "
                      "space in it", text)
        for gone in ("a directory a `source`d script or a function changed to is not seen",
                     "Still not read: a detaching program supplied at run time",
                     "runs in a child: it does not count", "unless the call's own event records",
                     "a case pattern or arithmetic", "no part is a child"):
            with self.subTest(gone=gone):
                self.assertNotIn(gone, text)
        self.assertIn("The runtime's shell keeps its directory between calls (#3719)", flat := " ".join(
            ro.__doc__.split()))
        self.assertIn("behind a brace, a compound keyword (`if`, `then`, `elif`, `else`, `while`, `until`, "
                      "`do`), `!`, `time`, `builtin` or `command` (#3797) -- or which may run in it code not on "
                      "its command line (#3782): `source` or `.`, or a program named by a bare word this does "
                      "not read, which may be a function or an alias", flat)
        self.assertIn("One in a subshell, an unquoted command or process substitution (`(cd x)`, `$(cd x)`, "
                      "`<(cd x)`), a pipe's left side or a `&` job does not move the shell, but it counts all the "
                      "same, the rule's cost", flat)
        self.assertIn("that waits for a shell grammar (#3830). A case pattern after the first on a `case ... in` line, or on a line of its own, is read as a command too", flat)
        self.assertIn("such a part is read as after a change too, and, where no earlier call's change was seen, "
                      "a relative `--full` resolves against the recorded directory, where the call started "
                      "(#3798). Where both hold, the earlier change decides and the `--full` is not placed "
                      "(#3812)", flat)
        self.assertIn("even where the call's own event records it (#3824 stays open", flat)
        for gone in ("runs in a child, so it does not count", "that is where the shell was",
                     "no part is read as in a child of any kind"):
            with self.subTest(gone=gone):
                self.assertNotIn(gone, flat)
        self.assertIn("(or one `eval` runs, or may run as a word supplied at run time, `eval \"$X\"`, #3815)", flat)
        # #3841: which substitutions are read.
        self.assertIn("One in a backquoted or double-quoted substitution (`` `cd x` ``, `\"$(cd x)\"`) is kept "
                      "inside one word and not read; it moves nothing (#3841)", flat)
        self.assertNotIn("subshell counts, the rule's cost --", flat)
        self.assertIn("In the same command, a directory change `eval` runs (or may run), or code run in this "
                      "shell as above, leaves no known directory for the parts after it, as one behind a brace "
                      "does (#3815). A resumed run's next transcript starts afresh. A package in the directory "
                      "the session's shell started in that such a part imports first is not read, nor a "
                      "function or alias named as a program read here", flat)
        self.assertNotIn("A package in the call's own starting directory", flat)
        # #3693: a variable or relative-path program's derive is not placed
        self.assertIn("A d4d call whose program, or a wrapper's, is a variable or a relative path (`$PY -m "
                      "data_sheets_schema.cli`, `./d4d`) is read as one, but a `derive core` of the full record "
                      "it spells cannot be placed, since the program may be a wrapper that did not run it, and "
                      "no subcommand of it is read-only (#3693)", text)
        self.assertIn("A d4d call whose program, or a wrapper's, is a variable or a relative path (`$PY -m "
                      "data_sheets_schema.cli`, `./d4d`) is read as one, but a `derive core` of the full record "
                      "it spells cannot be placed, as the program may be a wrapper that did not run it, and no "
                      "subcommand of it is read-only (#3693)", flat)
        self.assertNotIn("and an interpreter held in a variable (`$PY -m data_sheets_schema.cli`), are read "
                         "through", flat)
        # Round 6 (#3843-#3847): the texts name each rule and what remains unread.
        for phrase in ("a redirection with its target and descriptor is read past (`2>/dev/null cd /tmp`, #3845)",
                       "whose program word bash builds at run time (a `$` or backquote anywhere in it, a glob or a "
                       "brace expansion: `$C /tmp`, `c${X}d /tmp`) counts as a change and as open-ended, as it "
                       "may be a detaching program (`$X ./derive.sh`, `$(which setsid) ./derive.sh`, #3852)",
                       "never in an argument (`echo \"$(bash derive.sh)\"`)",
                       "the command `eval` runs is its words joined and tokenised again, each part read by the "
                       "same rules (`eval '\"cd\" /tmp'`, #3844)",
                       "every argument of a shell program given `-c` is read as a command it may run (`bash -ceo "
                       "pipefail 'cmd'`, #3843)",
                       "each run of `ssh`'s arguments to the end (#3846)",
                       "such a command string that carries a word supplied at run time or cannot be split is "
                       "open-ended (`bash -c \"$X\"`, #3852)"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)
        for phrase in ("a redirection, with its target and any descriptor before it (`2>/dev/null cd /tmp`, #3845)",
                       "The command `eval` runs is its words joined by spaces and tokenised again, which removes a "
                       "second level of quotes, and each part of it is read by the same rules however deep (`eval "
                       "'\"cd\" /tmp'`, #3844); an `eval` whose command carries a word supplied at run time, or "
                       "cannot be split, counts as a change and as open-ended (#3844, #3846)",
                       "Every argument of a shell program given `-c` in any option cluster is read as a command it "
                       "may run, since which word `-c` receives depends on the options that take values (`bash "
                       "-ceo pipefail 'cmd'`, #3843)",
                       "A part whose program word bash builds at run time (a `$` or backquote anywhere in it, a "
                       "glob or a brace expansion: `$C /tmp`, `c${X}d /tmp`) may be the builtin, and counts as a "
                       "change; it may be a detaching program, too, and makes the call open-ended (#3852)",
                       "Such a command string that carries a word supplied at run time, or cannot be split, may "
                       "run anything, and is open-ended as an `eval` of it is (`bash -c \"$X\"`, #3852)"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, flat)
        flat = " ".join(ro.__doc__.split())
        self.assertIn("or such a part not run as its words name (a variable or relative path as its program, "
                      "an assignment before it or as an earlier part, `printf -v` included, #3689, #3700, or "
                      "for a `python -c` or `python -m` part a directory change before it in the command, as "
                      "the interpreter imports from the directory it starts in first, #3699, and for a part run "
                      "through `poetry run` one too, as poetry takes its virtualenv from the project that "
                      "directory is in, #3723; a d4d `derive core` call aimed at another record is held to the "
                      "same, #3722)", flat)
        self.assertIn("a backgrounded call's result is its launch -- its own `run_in_background` input or its "
                      "result's metadata says so, #3744 -- and a part started with `&` -- at the top level or "
                      "ending a command inside a word a nested shell may run, which is read as that shell "
                      "splits it where the word has a space in it, `bash -c './derive.sh&echo started'`, "
                      "#3745, and the word a shell nested in that one gives its `-c`, or `eval` or `ssh` runs, "
                      "read so in turn, however deep, #3748, and otherwise only where a space, "
                      "`)`, `}`, `;`, `#` or the end follows the `&`, so `R&D` is text -- "
                      "or by `coproc`, or by a program that detaches it, `setsid`, `screen`, `tmux` and the "
                      "like, may outlive it, so none of them has, #3674, #3690; nor has a call that starts a "
                      "process substitution, which bash does not wait for (`true <(bash step.sh)`): a `<(` or "
                      "`>(` outside quotes, one anywhere after a command substitution opens, or one in a nested "
                      "shell's word with a space in it, #3752; a command the tokenizer cannot "
                      "split is open-ended where its whole text carries such a `&`, by the rule for a word "
                      "with no space, `coproc`, detaching program or `<(` / `>(`, #3698, #3752; a script that "
                      "detaches a child itself, or a detaching program behind a wrapper not read, `sudo`, is "
                      "not seen", flat)
        self.assertIn("a directory change (the builtin `cd`, `pushd` or `popd` as the part's first word after "
                      "its assignments; a path-qualified lookalike, `./cd`, or `poetry run cd`, is a program not "
                      "read, #3753)", flat)
        self.assertIn("and a receipt change issued before that boundary returned after both it and the draft "
                      "were issued (#3697)", flat)
        self.assertIn("a `derive core` run by anything other than a shell call in the transcripts given", text)
        self.assertIn("A derive whose words are not on the command line at all (a script, an alias or function, "
                      "`d4d $SUB`, `python -c` building the argument list) is placed by position instead (#3369)",
                      doc)
        self.assertIn("or a shell call may have run one unseen where it would move the boundary (#3369)", doc)
        self.assertNotIn("A word the shell builds some other way (a glob, `derive c*`) is not seen", text)
        self.assertNotIn("nor is a word xargs appends to a `derive` that neither ends", text)
        self.assertIn("Last, a command-wide backstop (#3478-#3480): a call whose raw text carries more "
                      "whole-word `derive`s than the rules above gave rows (so a `--help` row never accounts "
                      "for a derive hidden beside it), where that text, quote and escape characters removed, "
                      "carries the word `derive` as a whole word anywhere -- inside a substitution, an assignment, a `cd` part or an "
                      "`xargs` argument included -- and also a `d4d`, `data_sheets_schema` or `$`-variable "
                      "invocation, is one derive that cannot be placed", doc)
        self.assertIn("its cost is a false `unknown` for a call that only mentions the word beside such an "
                      "invocation", doc)
        self.assertIn("one with a redirection directly after it in an xargs command, whatever follows the "
                      "redirection", doc)
        self.assertIn("A command the tokenizer cannot split at all (an apostrophe in a here-document's body) "
                      "is not read part by part: it is tested whole, quote characters removed, for the same "
                      "words, and a match is a derive that cannot be placed (#3458)", doc)
        self.assertIn("as does one carrying any replacement string an `xargs` in the command sets", doc)
        self.assertIn("The words are matched after quote and escape characters are removed, as the shell "
                      "running a nested string removes them", doc)


class UnseenDerive(Base):
    """A `derive core` run without the words on the command line (a script,
    an alias or function, `d4d $SUB`, `python -c` building the argument list)
    left the block `checked` with a Phase 3 entry read as Phase 1 (#3369). A
    shell call that runs a program this does not read, that had not returned
    when the draft was issued and was issued before the derive boundary, with
    a receipt change after it, is now a reason. The two schema validators the
    playbook runs are read; a command or process substitution is not (#3675)."""

    FULL = "data/claudecode_direct/L/CHORUS_d4d.yaml"
    VALIDATE = ("python -c 'from linkml.validator.cli import cli; cli()' -s schema.yaml -C Dataset "
                f"{FULL}")
    TERMS = ("/venv/bin/python3 -c 'from linkml_term_validator.cli import main; main()' validate-data "
             f"{FULL} --schema schema.yaml --target-class Dataset")
    UNSEEN = ("bash derive.sh", "sh -c ./run", "./derive.sh", "source derive.sh", "myderive",
              "d4d $SUB --full F", f"python -c 'import sys; sys.argv[1:] = [\"de\" + \"rive\", \"core\"]' {FULL}",
              "python scripts/fix.py", "make core", "cat x | bash", "timeout 60 cat x",
              "echo ok && python tools/step.py", "python - <<'EOF'\nprint(1)\nEOF",
              "poetry run linkml-validate --config c.yaml F",
              "linkml-validate -m datamodel.py F", "linkml-validate -s s.yaml --legacy-mode F",
              "linkml-term-validator validate-data F -s s.yaml -a pronto:x.obo",
              "linkml-term-validator validate-data F -s s.yaml --config oak.yaml",
              "linkml-term-validator F -s s.yaml",
              "python -c 'from linkml.validator.cli import cli; cli(); import os' F",
              # A substitution's inner command is not read, whatever carries it (#3675).
              "echo \"$(date)\"", "echo \"$(bash derive.sh)\"", "echo `./derive.sh`", "ls `./derive.sh`",
              "cat <(bash derive.sh)", "d4d receipts check --receipt \"$(bash derive.sh)\"",
              "linkml-validate -s s.yaml <(./derive.sh)", "linkml-validate -s s.yaml \"$(./derive.sh)\"",
              "echo $((1 + 2))",
              # A part read here, or a validator, spelled so that it may run
              # another program (#3689): a variable or relative-path program,
              # an assignment before it (on the part, to `env`, or as a part
              # of its own), or an interpreter held in a variable.
              "PY=./derive.sh; $PY -c \"from linkml.validator.cli import cli; cli()\" -s s.yaml x.yaml",
              "PY=./run.sh; $PY -c \"from linkml.validator.cli import cli; cli()\" -s s.yaml x.yaml",
              "PYTHONPATH=./hack linkml-validate -s s.yaml x.yaml",
              "env PYTHONPATH=./hack linkml-validate -s s.yaml x.yaml",
              "./python -c \"from linkml.validator.cli import cli; cli()\" -s s.yaml x.yaml",
              "${PY} -c 'from linkml_term_validator.cli import main; main()' validate F -s s.yaml",
              "bin/linkml-validate -s s.yaml F", "PATH=./bin:$PATH; linkml-validate -s s.yaml F",
              "PATH=./bin:$PATH linkml-validate -s s.yaml F", "./cat x", "$CAT x",
              "PYTHONPATH=./hack d4d receipts check --receipt R",
              "$PY -m data_sheets_schema.cli receipts check --receipt R", "F=x.yaml; cat $F",
              # `printf -v NAME` assigns as `NAME=...;` does (#3700).
              "printf -v PATH '%s' ./bin; linkml-validate -s s.yaml F",
              "printf -vPATH ./bin; linkml-validate -s s.yaml F",
              # `python -c` and `-m` import from the directory they start in
              # first, so after a directory change they may run a package
              # it holds (#3699).
              f"cd hack && {VALIDATE}", f"cd hack; {TERMS}", f"pushd hack && {VALIDATE}",
              "cd hack && python -m data_sheets_schema.cli receipts check --receipt R",
              # `poetry run` takes its virtualenv, and so the console script
              # it runs, from the project the new directory is in (#3723).
              "cd hack && poetry run linkml-validate -s s.yaml F",
              "cd hack && poetry run d4d receipts check --receipt R",
              "cd hack && timeout 60 poetry run d4d receipts check --receipt R",
              "pushd hack && env poetry run linkml-validate -s s.yaml F",
              # A `derive core` aimed at another record places nothing, and is
              # held to the same rules as any other part read here (#3722).
              "./d4d derive core --full /other/full.yaml --out /o/c.yaml",
              "PYTHONPATH=./hack d4d derive core --full /other/full.yaml --out /o/c.yaml",
              "$PY -m data_sheets_schema.cli derive core --full /other/full.yaml --out /o/c.yaml",
              "cd hack && python -m data_sheets_schema.cli derive core --full /other/full.yaml --out /o/c.yaml",
              "cd hack && poetry run d4d derive core --full /other/full.yaml --out /o/c.yaml",
              "PATH=./bin:$PATH; d4d derive core --full /other/full.yaml --out /o/c.yaml",
              "printf -v PATH '%s' ./bin; d4d derive core --full /other/full.yaml --out /o/c.yaml",
              "./d4d derive core --full /other/full.yaml 2>/dev/null --out /o/c.yaml",
              # Only the builtin `cd`, `pushd` or `popd` is a directory
              # change; a path-qualified lookalike, or one `poetry run`
              # runs, is a program not read (#3753).
              "./cd x", "./pushd x", "./popd", "bin/cd x", "/usr/bin/cd x", "X=1 ./cd x",
              "poetry run cd x", "./cd x && ls", "ls; ./popd")

    def _run(self, command, *, derive=True, **result):
        """Draft, the call under test, a receipt change, then (by default) the
        recognised derive and a later receipt change."""
        r = self.new_run()
        r.write(r.receipt, PRE)
        r.write(r.full, "id: x\n")
        identity = r.bash(command, **result)
        r.write(r.receipt, Boundaries.C003)
        if derive:
            # An absolute `--full`: after a call that moved the directory a
            # relative one cannot be placed (#3719).
            r.derive(full=r.full)
            r.write(r.receipt, Boundaries.C004)
        return identity, r.report()

    def test_a_program_not_read_between_the_draft_and_a_receipt_change_is_unknown(self):
        for command in self.UNSEEN:
            for derive in (True, False):
                with self.subTest(command=command, derive=derive):
                    identity, block = self._run(command, derive=derive)
                    where = "the derive core boundary" if derive else "the end of the transcripts"
                    self.assertUnknown(block, f"Bash call {identity} (transcript 0 line 6) runs a program this "
                                              "does not read and had not returned when the full record's first "
                                              f"Write was issued, was issued before {where}, "
                                              "with a receipt change after it: a `derive core` it ran without the "
                                              "words on its command line would move the Phase 1 / Phase 3 "
                                              "boundary (#3369)")
                    self.assertEqual([row["tool_use_id"] for row in block["possible_unseen_derives"]], [identity])
                    self.assertEqual(set(block["possible_unseen_derives"][0]),
                                     {"tool_use_id", "transcript", "line", "result_line", "outcome"})

    def test_a_failed_call_may_still_have_derived(self):
        identity, block = self._run("bash derive.sh", ok=False)
        self.assertUnknown(block, f"Bash call {identity} (transcript 0 line 6) runs a program this does not read")
        self.assertEqual(block["possible_unseen_derives"][0]["outcome"], "failed")

    def test_a_call_that_can_run_nothing_unseen_is_not_a_possible_derive(self):
        for command in ("cat CHORUS_d4d.yaml", "grep -n title x.md | head -3", "cd data && ls",
                        "d4d receipts check --receipt R", "d4d bundle chunk --check",
                        "python -m data_sheets_schema.cli receipts check --receipt R",
                        "cat x > /tmp/out.txt", "echo '$(date)'", "echo 'R&D' && ls",
                        self.VALIDATE, self.TERMS, "poetry run linkml-validate -s s.yaml -C Dataset F",
                        "linkml-validate --schema=s.yaml --target-class=Dataset --exit-on-first-failure -D F",
                        "linkml-term-validator validate-data F -s s.yaml -t Dataset --no-labels --bindings",
                        "/venv/bin/linkml-validate -s s.yaml F && /venv/bin/linkml-term-validator validate "
                        "F -s s.yaml",
                        # A `printf` without `-v` prints; a console script
                        # after a directory change runs from its own `bin`
                        # (#3699, #3700).
                        "printf '%s' -v; linkml-validate -s s.yaml F", "printf -- -v x; linkml-validate F",
                        "cd hack && linkml-validate -s s.yaml F", "cd hack && d4d receipts check --receipt R",
                        "cd data && head -c 200 x.yaml",
                        # `poetry run` with no directory change, and a
                        # `derive core` aimed at another record run as its
                        # words name it (#3722, #3723).
                        "poetry run d4d receipts check --receipt R",
                        "d4d derive core --full /other/full.yaml --out /o/c.yaml",
                        "cd hack && d4d derive core --full /other/full.yaml --out /o/c.yaml",
                        "poetry run d4d derive core --full /other/full.yaml --out /o/c.yaml",
                        "/venv/bin/python -m data_sheets_schema.cli derive core --full /other/full.yaml "
                        "--out /o/c.yaml"):
            with self.subTest(command=command):
                _, block = self._run(command)
                self.assertEqual(block["status"], "checked", block["reasons"])
                self.assertEqual(block["possible_unseen_derives"], [])
                self.assertEqual(block["origin"], {"contemporaneous": 3, "phase1_correction": 1,
                                                   "phase3_backport": 1})

    def test_only_a_call_that_could_move_the_boundary_counts(self):
        # An absolute `--full`: an earlier call here may run a function or a sourced
        # script, which may change directory, so a relative one is not placed (#3782).
        # After the boundary, the first successful derive has already run.
        r = self.new_run()
        r.write(r.receipt, PRE)
        r.write(r.full, "id: x\n")
        r.write(r.receipt, Boundaries.C003)
        r.derive(full=r.full)
        r.bash("bash derive.sh")
        r.write(r.receipt, Boundaries.C004)
        block = r.report()
        self.assertEqual(block["status"], "checked", block["reasons"])
        self.assertEqual(block["origin"], {"contemporaneous": 3, "phase1_correction": 1, "phase3_backport": 1})
        # With no receipt change after it, the snapshots are the same either way.
        for derive in (True, False):
            with self.subTest(derive=derive):
                r = self.new_run()
                r.write(r.receipt, PRE)
                r.write(r.full, "id: x\n")
                r.write(r.receipt, Boundaries.C003)
                r.bash("bash derive.sh")
                if derive:
                    r.derive(full=r.full)
                block = r.report()
                self.assertEqual(block["status"], "checked", block["reasons"])
                self.assertEqual(block["possible_unseen_derives"], [])
        # Before the draft was issued there was no full record to derive.
        r = self.new_run()
        r.write(r.receipt, PRE)
        r.bash("bash derive.sh")
        r.write(r.full, "id: x\n")
        r.write(r.receipt, Boundaries.C003)
        r.derive(full=r.full)
        block = r.report()
        self.assertEqual(block["status"], "checked", block["reasons"])
        self.assertEqual(block["possible_unseen_derives"], [])

    def test_a_call_in_flight_with_the_draft_or_backgrounded_before_it_counts(self):
        # An absolute `--full`: an earlier call here may run a function or a sourced
        # script, which may change directory, so a relative one is not placed (#3782).
        # Issued before the draft but returned after it was issued: it may
        # have run once the full record existed.
        r = self.new_run()
        r.write(r.receipt, PRE)
        identity = r.call("Bash", command="bash derive.sh", description="x")
        draft = r.call("Write", file_path=str(r.full), content="id: x\n")
        r.result(identity, "out", {"stdout": "", "stderr": "", "interrupted": False}, is_error=False)
        r.result(draft, f"File written at: {r.full}", {"type": "create", "filePath": str(r.full)})
        r.write(r.receipt, Boundaries.C003)
        r.derive(full=r.full)
        self.assertUnknown(r.report(), f"Bash call {identity} (transcript 0 line 4) runs a program")
        # A backgrounded call's result is its launch: it may run on after the draft.
        r = self.new_run()
        r.write(r.receipt, PRE)
        identity = r.bash("bash derive.sh", metadata={"stdout": "", "stderr": "", "interrupted": False,
                                                       "backgroundTaskId": "bg1"})
        r.write(r.full, "id: x\n")
        r.write(r.receipt, Boundaries.C003)
        r.derive(full=r.full)
        self.assertUnknown(r.report(), f"Bash call {identity} (transcript 0 line 4) runs a program")
        # The call's own `run_in_background` says so too where its result
        # carries no metadata: none at all, or a user event carrying two
        # results, whose metadata describes neither (#3744).
        for shared in (False, True):
            with self.subTest(run_in_background_without_metadata=shared):
                r = self.new_run()
                r.write(r.receipt, PRE)
                identity = r.call("Bash", command="./derive.sh", description="x", run_in_background=True)
                if shared:
                    other = r.call("Bash", command="ls", description="x")
                    r.events.append({"type": "user", "session_id": "s", "parent_tool_use_id": None,
                                     "message": {"role": "user", "content": [
                                         {"type": "tool_result", "tool_use_id": identity,
                                          "content": "Command running in background with ID: bg1",
                                          "is_error": False},
                                         {"type": "tool_result", "tool_use_id": other, "content": "x",
                                          "is_error": False}]},
                                     "tool_use_result": {"stdout": "x", "stderr": "", "interrupted": False}})
                else:
                    r.result(identity, "Command running in background with ID: bg1", is_error=False)
                r.write(r.full, "id: x\n")
                r.write(r.receipt, Boundaries.C003)
                r.derive(full=r.full)
                block = r.report()
                self.assertUnknown(block, f"Bash call {identity} (transcript 0 line 4) runs a program")
                self.assertEqual([row["tool_use_id"] for row in block["possible_unseen_derives"]], [identity])
        # `run_in_background: false` is a foreground call that returned.
        r = self.new_run()
        r.write(r.receipt, PRE)
        identity = r.call("Bash", command="./derive.sh", description="x", run_in_background=False)
        r.result(identity, "out", is_error=False)
        r.write(r.full, "id: x\n")
        r.write(r.receipt, Boundaries.C003)
        r.derive(full=r.full)
        block = r.report()
        self.assertEqual(block["status"], "checked", block["reasons"])
        # So may a part the command started with `&`, whatever the result says.
        for command in ("bash derive.sh &", "(bash derive.sh &)", "bash derive.sh & wait",
                        "bash derive.sh > /tmp/log 2>&1 &"):
            with self.subTest(command=command):
                r = self.new_run()
                r.write(r.receipt, PRE)
                identity = r.bash(command)
                r.write(r.full, "id: x\n")
                r.write(r.receipt, Boundaries.C003)
                r.derive(full=r.full)
                self.assertUnknown(r.report(), f"Bash call {identity} (transcript 0 line 4) runs a program")
        # So may a `&` ending a command inside a word a nested shell runs, or
        # a program that detaches what it runs (#3674).
        for command in ("bash -c './derive.sh &'", "sh -c \"./derive.sh > log 2>&1 &\"",
                        "bash -c '(./derive.sh &)'", "bash -c './derive.sh & wait'",
                        "setsid -f ./derive.sh", "timeout 60 setsid ./derive.sh",
                        "/usr/bin/setsid ./derive.sh", "screen -dm ./derive.sh",
                        "tmux new -d ./derive.sh", "echo ./derive.sh | at now", "daemon -- ./derive.sh",
                        "systemd-run --user ./derive.sh", "./derive.sh; disown",
                        # `coproc` starts its command asynchronously (#3690),
                        # and a detaching program may stand after `nohup`,
                        # `exec` or `command`, or first in a nested shell's word.
                        "coproc ./derive.sh", "coproc X { ./derive.sh; }", "{ coproc ./derive.sh; }",
                        "if true; then coproc ./derive.sh; fi", "bash -c 'coproc ./derive.sh'",
                        "bash -c 'cd x && coproc ./derive.sh'", "nohup setsid ./derive.sh",
                        "exec setsid ./derive.sh", "command setsid ./derive.sh",
                        "bash -c 'setsid ./derive.sh'", "bash -c 'cd x; /usr/bin/setsid ./derive.sh'"):
            with self.subTest(command=command):
                r = self.new_run()
                r.write(r.receipt, PRE)
                identity = r.bash(command)
                r.write(r.full, "id: x\n")
                r.write(r.receipt, Boundaries.C003)
                r.derive(full=r.full)
                self.assertUnknown(r.report(), f"Bash call {identity} (transcript 0 line 4) runs a program")
        # A `&` followed directly by the next command, or by a comment,
        # inside a nested shell's word with a space in it ends a command as
        # the shell splits that word (#3745); so does an unquoted `R&D`
        # there, which is the rule's cost.
        for command in ("bash -c './derive.sh&echo started'", "bash -c './derive.sh&#note'",
                        "bash -c 'cd x; ./derive.sh&wait'", "sh -c \"./derive.sh>log 2>&1&echo ok\"",
                        "bash -c 'echo R&D work'",
                        # The argument a shell nested in the nested shell
                        # gives its `-c`, or `eval` or `ssh` runs, is read by
                        # the same rules, however deep (#3748).
                        "bash -c \"bash -c './derive.sh&echo x'\"",
                        "bash -c \"bash -lc './derive.sh&echo x'\"",
                        "bash -c \"eval './derive.sh&echo x'\"",
                        "bash -c \"ssh host './derive.sh&echo x'\"",
                        "sh -c \"timeout 60 bash -c 'setsid ./derive.sh'\"",
                        "bash -c \"nohup bash -c 'coproc ./derive.sh'\"",
                        "bash -c \"bash -c 'cat <(./derive.sh)'\"",
                        "bash -c \"X=1 bash -o pipefail -c 'bash -c \\\"./derive.sh&echo x\\\"'\"",
                        # Every argument of a shell given `-c` is read, so an
                        # option cluster that takes a value (`-ceo pipefail`)
                        # cannot hide the command string (#3843); a positional
                        # argument that reads as a command is the rule's cost.
                        "bash -c \"bash -ceo pipefail './derive.sh&echo x'\"",
                        "bash -ceo pipefail './derive.sh&echo x'",
                        "bash -c \"bash -eo pipefail -c './derive.sh&echo x'\"",
                        "bash -c \"bash -c './derive.sh' 'R&D team'\"",
                        # The command `eval` runs is its words joined, and the
                        # command `ssh` runs is its words after its options
                        # and host (#3846).
                        "bash -c \"eval bash -c \\\"'./derive.sh&echo x'\\\"\"",
                        "eval bash -c \"'./derive.sh&echo x'\"",
                        "eval ./derive.sh '&' echo x",
                        "bash -c \"ssh -p 22 host bash -c \\\"'./derive.sh&echo x'\\\"\"",
                        "ssh -p 22 host bash -c \"'./derive.sh&echo x'\"",
                        # An eval whose command is not known by its words may
                        # start anything (#3846).
                        "eval \"$GO\"", "bash -c 'eval \"$GO\"'", "eval `cat cmd`",
                        # A redirection before the program is read past (#3845).
                        "2>/dev/null setsid ./derive.sh", ">log builtin eval \"$GO\"",
                        "bash -c '2>/dev/null setsid ./derive.sh'",
                        # A detaching program spelled across an escape or quotes
                        # in a command the tokenizer cannot split (#3847).
                        "s\\etsid ./derive.sh; cat <<EOF\nit's\nEOF",
                        "\"setsid\" ./derive.sh; cat <<EOF\nit's\nEOF"):
            with self.subTest(command=command):
                r = self.new_run()
                r.write(r.receipt, PRE)
                identity = r.bash(command)
                r.write(r.full, "id: x\n")
                r.write(r.receipt, Boundaries.C003)
                r.derive(full=r.full)
                block = r.report()
                self.assertUnknown(block, f"Bash call {identity} (transcript 0 line 4) runs a program")
                self.assertEqual([row["tool_use_id"] for row in block["possible_unseen_derives"]], [identity])
        # A `&` the nested word quotes is text, and a word with no space in
        # it keeps the narrow rule (a URL's query, `R&D`), as does any word
        # of a program nested in the nested shell that it does not run as a
        # command (#3748); a shell given no `-c` runs none of its words.
        for command in ("bash -c 'echo \"R&D team\"; ./derive.sh'", "bash -c \"./derive.sh 'a=1&b=2'\"",
                        "bash -c \"bash -c 'echo \\\"R&D team\\\"; ./derive.sh'\"",
                        "bash -c \"bash -c './derive.sh && echo done'\"",
                        "eval ./derive.sh '&&' echo x", "eval 'echo \"R&D team\"'",
                        "bash -c './derive.sh && echo done'", "bash derive.sh 'R&D'"):
            with self.subTest(command=command):
                r = self.new_run()
                r.write(r.receipt, PRE)
                r.bash(command)
                r.write(r.full, "id: x\n")
                r.write(r.receipt, Boundaries.C003)
                r.derive(full=r.full)
                block = r.report()
                self.assertEqual(block["status"], "checked", block["reasons"])
        # A `&&`, `|&` or a redirection's `&` detaches nothing, at the top
        # level or inside a word; nor does a `&` inside a word (`R&D`, a URL's
        # query), nor `nohup` without a `&`.
        for command in ("bash derive.sh && ls", "bash derive.sh |& cat", "bash derive.sh 2>&1",
                        "bash derive.sh &>/dev/null", "bash -c './derive.sh && ls'",
                        "bash -c './derive.sh 2>&1'", "bash -c './derive.sh &>/dev/null'",
                        "bash -c './derive.sh |& cat'", "bash derive.sh 'R&D'",
                        "curl 'https://x.org/?a=1&b=2'", "nohup ./derive.sh > log 2>&1",
                        # A redirection's `>&` or `<&` before a space inside
                        # a nested shell's word (#3692), and `coproc` or a
                        # detaching program's name as an argument.
                        "bash -c './derive.sh >& log'", "bash -c './derive.sh <& 3'",
                        "bash -c 'echo coproc; ./derive.sh'", "bash derive.sh coproc",
                        "bash -c './derive.sh at now'"):
            with self.subTest(command=command):
                r = self.new_run()
                r.write(r.receipt, PRE)
                r.bash(command)
                r.write(r.full, "id: x\n")
                r.write(r.receipt, Boundaries.C003)
                r.derive(full=r.full)
                block = r.report()
                self.assertEqual(block["status"], "checked", block["reasons"])
        # A receipt Write issued before the call but returned after it was
        # issued may have landed after a derive the call ran.
        r = self.new_run()
        r.write(r.receipt, PRE)
        r.write(r.full, "id: x\n")
        update = InFlight.start(r, r.receipt, Boundaries.C003)
        identity = r.call("Bash", command="bash derive.sh", description="x")
        InFlight.finish(r, update, r.receipt, Boundaries.C003)
        r.result(identity, "out", {"stdout": "", "stderr": "", "interrupted": False}, is_error=False)
        r.derive(full=r.full)
        block = r.report()
        self.assertUnknown(block, f"Bash call {identity} (transcript 0 line 7) runs a program")
        self.assertEqual([row["tool_use_id"] for row in block["possible_unseen_derives"]], [identity])

    def test_a_process_substitution_is_open_ended(self):
        # An absolute `--full`: an earlier call here may run a function or a sourced
        # script, which may change directory, so a relative one is not placed (#3782).
        # bash does not wait for a process substitution: `true <(bash
        # step.sh)` can return while step.sh runs on, so a call that returned
        # before the draft was issued may still derive after it (#3752).
        for command in ("true <(bash step.sh)", "cat <(./derive.sh)", "tee >(./derive.sh) < x",
                        "diff <(sort a) <(./derive.sh)", "echo \"$(cat <(./derive.sh))\"",
                        "echo `cat <(./derive.sh)`", "bash -c 'cat <(./derive.sh)'",
                        "linkml-validate -s s.yaml <(./derive.sh)",
                        "bash <<EOF\ncat <(./derive.sh)\nit's\nEOF"):
            with self.subTest(command=command):
                self.assertTrue(ro._shell(command, None, [])["detaches"])
                r = self.new_run()
                r.write(r.receipt, PRE)
                identity = r.bash(command)
                r.write(r.full, "id: x\n")
                r.write(r.receipt, Boundaries.C003)
                r.derive(full=r.full)
                block = r.report()
                self.assertUnknown(block, f"Bash call {identity} (transcript 0 line 4) runs a program")
                self.assertEqual([row["tool_use_id"] for row in block["possible_unseen_derives"]], [identity])
        # A quoted `<(` is text, and a command substitution, which bash
        # waits for, is not open-ended: a call that returned before the draft
        # was issued could not have derived after it.
        for command in ("bash derive.sh '<(x)'", "bash derive.sh \"<(x)\"", "echo \"$(bash derive.sh)\"",
                        "bash derive.sh \\<\\(x\\)", "bash derive.sh # <(x)"):
            with self.subTest(command=command):
                self.assertFalse(ro._shell(command, None, [])["detaches"])
                r = self.new_run()
                r.write(r.receipt, PRE)
                r.bash(command)
                r.write(r.full, "id: x\n")
                r.write(r.receipt, Boundaries.C003)
                r.derive(full=r.full)
                block = r.report()
                self.assertEqual(block["status"], "checked", block["reasons"])

    def test_process_substitutes(self):
        for command, expected in (("true <(x)", True), ("tee >(x)", True), ("cat a<(x)", True),
                                  ("echo '<(x)'", False), ("echo \"<(x)\"", False), ("echo \\<(x)", False),
                                  ("echo $'<(x)'", False), ("echo \"$(cat <(x))\"", True),
                                  ("echo `cat <(x)`", True), ("echo \"$(date)\" '<(x)'", True),
                                  ("echo '$(x)' '<(y)'", False), ("echo \"$(date)\"", False),
                                  ("cat <<< x", False), ("x=$((1<2))", False)):
            with self.subTest(command=command):
                self.assertEqual(ro._process_substitutes(command), expected)

    def test_command_strings(self):
        # The words a nested command runs as commands of their own: a shell
        # program's `-c` argument, and `eval`'s or `ssh`'s (#3748).
        # Every argument of a shell program given `-c` in any cluster, since
        # which one `-c` receives depends on the options that take values
        # (`--rcfile F`, #3813; `-ceo pipefail`, #3843); `eval`'s arguments
        # and their join; `ssh`'s and each run of them to the end (#3846).
        cases = {"bash -c 'a & b' name": ["-c", "a & b", "name"], "bash -lc x": ["-lc", "x"],
                 "sh -e -c x y": ["-e", "-c", "x", "y"],
                 "bash -o pipefail -c x": ["-o", "pipefail", "-c", "x"], "bash --norc -c x": ["--norc", "-c", "x"],
                 "/bin/zsh -c x": ["-c", "x"], "X=1 timeout 60 nohup bash -c x": ["-c", "x"],
                 "ls; bash -c x | eval y z": ["-c", "x", "y", "z", "y z"],
                 "ssh host 'a & b'": ["host", "a & b", "host a & b"], "bash x.sh 'a & b'": [],
                 "bash -- -c x": ["--", "-c", "x"], "bash -c": ["-c"], "echo 'R&D team'": [],
                 "python -c 'a & b'": [], "": [], "bash --rcfile /dev/null -c x": ["--rcfile", "/dev/null", "-c", "x"],
                 "bash -ceo pipefail x": ["-ceo", "pipefail", "x"], "bash -eo pipefail -c x": ["-eo", "pipefail", "-c", "x"],
                 "eval bash -c \"'a&b c'\"": ["bash", "-c", "'a&b c'", "bash -c 'a&b c'"],
                 "ssh -p 22 host bash -c x": ["-p", "22", "host", "bash", "-c", "x", "-p 22 host bash -c x",
                                              "22 host bash -c x", "host bash -c x", "bash -c x", "-c x"],
                 "2>/dev/null bash -c x": ["-c", "x"], "builtin eval x": ["x"]}
        for command, strings in cases.items():
            with self.subTest(command=command):
                self.assertEqual(ro._command_strings(ro._tokens(command) or []), strings)

    def test_nested_open_ended(self):
        for word, open_ended in (("./derive.sh &", True), ("bash -c './derive.sh&echo x'", True),
                                 ("eval './derive.sh&echo x'", True), ("bash -c 'setsid ./derive.sh'", True),
                                 ("bash -c 'cat <(./derive.sh)'", True),
                                 ("bash -c \"sh -c 'bash -c \\\"./derive.sh&echo x\\\"'\"", True),
                                 ("bash -c \"bash --rcfile /dev/null -c './derive.sh&echo x'\"", True),
                                 ("bash -c \"bash --init-file f -c './derive.sh&echo x'\"", True),
                                 ("echo 'R&D team'", False), ("bash -c 'echo \"R&D team\"'", False),
                                 ("bash x.sh 'a&b c'", False), ("R&D", False)):
            with self.subTest(word=word):
                self.assertEqual(ro._nested_open_ended(word), open_ended)

    def test_directory_builtin(self):
        for segment, expected in ((["cd", "x"], "cd"), (["pushd", "x"], "pushd"), (["popd"], "popd"),
                                  (["X=1", "cd", "x"], "cd"), (["./cd", "x"], None), (["bin/pushd", "x"], None),
                                  (["/usr/bin/cd", "x"], None), (["./popd"], None), (["poetry", "run", "cd", "x"], None),
                                  (["$CD", "x"], None), (["env", "cd", "x"], None), (["ls"], None), ([], None)):
            with self.subTest(segment=segment):
                self.assertEqual(ro._directory_builtin(segment), expected)
        # A lookalike moves no directory: a `--full` after it resolves where
        # the call started.
        target = ro._Target("full", "/w/CHORUS_d4d.yaml")
        for command, verdict in (("cd sub && d4d derive core --full CHORUS_d4d.yaml --out c.yaml", False),
                                 ("./cd sub && d4d derive core --full CHORUS_d4d.yaml --out c.yaml", True)):
            with self.subTest(command=command):
                rows = ro._shell(command, "/w", [target])["derives"]
                self.assertEqual([row["targets_full"] for row in rows], [verdict])

    def test_a_call_after_the_boundary_is_not_listed_even_beside_a_write_in_flight_with_it(self):
        # The receipt Write in flight with the boundary is the reason; the
        # call issued after the boundary cannot move it (the first derive ran).
        r = self.new_run()
        r.write(r.receipt, PRE)
        r.write(r.full, "id: x\n")
        update = InFlight.start(r, r.receipt, Boundaries.C003)
        derive = r.derive()
        r.bash("bash derive.sh")
        InFlight.finish(r, update, r.receipt, Boundaries.C003)
        block = r.report()
        self.assertUnknown(block, f"was in flight with the derive core boundary ({derive})")
        self.assertEqual(block["possible_unseen_derives"], [])

    def test_a_command_the_tokenizer_cannot_split_is_not_read(self):
        # An apostrophe in a here-document body (#3458): its parts are not read.
        identity, block = self._run("cat <<EOF\nit's\nEOF")
        self.assertUnknown(block, f"Bash call {identity} (transcript 0 line 6) runs a program")

    def test_an_unsplit_command_that_returned_before_the_draft_is_open_ended_only_as_its_text_says(self):
        # An absolute `--full`: an earlier call here may run a function or a sourced
        # script, which may change directory, so a relative one is not placed (#3782).
        # Returned before the draft was issued: it could not have derived
        # after it, unless its text starts something that outlives it (#3698).
        for command, open_ended in (("cat <<EOF\nit's\nEOF", False),
                                    ("bash <<EOF\n./derive.sh &\nit's\nEOF", True),
                                    ("bash <<EOF\nsetsid ./derive.sh\nit's\nEOF", True),
                                    ("bash <<EOF\ncoproc ./derive.sh\nit's\nEOF", True),
                                    ("bash <<EOF\n./derive.sh 2>&1 && ls\nit's\nEOF", False)):
            with self.subTest(command=command):
                self.assertEqual(ro._shell(command, None, [])["detaches"], open_ended)
                r = self.new_run()
                r.write(r.receipt, PRE)
                identity = r.bash(command)
                r.write(r.full, "id: x\n")
                r.write(r.receipt, Boundaries.C003)
                r.derive(full=r.full)
                block = r.report()
                if open_ended:
                    self.assertUnknown(block, f"Bash call {identity} (transcript 0 line 4) runs a program")
                else:
                    self.assertEqual(block["status"], "checked", block["reasons"])
                    self.assertEqual(block["possible_unseen_derives"], [])

    def test_a_receipt_change_that_returned_before_the_draft_was_issued_cannot_be_reordered(self):
        # An absolute `--full`: an earlier call here may run a function or a sourced
        # script, which may change directory, so a relative one is not placed (#3782).
        # The call is in flight across the draft, but the only receipt change
        # before the boundary returned before the draft was issued: no derive
        # ran before the full record existed, so it lands before any derive
        # the call ran (#3697).
        r = self.new_run()
        identity = r.call("Bash", command="bash derive.sh", description="x")
        r.write(r.receipt, PRE)
        r.write(r.full, "id: x\n")
        r.result(identity, "out", {"stdout": "", "stderr": "", "interrupted": False}, is_error=False)
        r.derive(full=r.full)
        r.write(r.receipt, Boundaries.C003)
        block = r.report()
        self.assertEqual(block["status"], "checked", block["reasons"])
        self.assertEqual(block["possible_unseen_derives"], [])
        # One returning after the draft was issued may land after it.
        r = self.new_run()
        identity = r.call("Bash", command="bash derive.sh", description="x")
        r.write(r.receipt, PRE)
        r.write(r.full, "id: x\n")
        r.write(r.receipt, Boundaries.C003)
        r.result(identity, "out", {"stdout": "", "stderr": "", "interrupted": False}, is_error=False)
        r.derive(full=r.full)
        block = r.report()
        self.assertUnknown(block, f"Bash call {identity} (transcript 0 line 2) runs a program")
        self.assertEqual([row["tool_use_id"] for row in block["possible_unseen_derives"]], [identity])

    def test_printf_assigns(self):
        cases = {("-v", "PATH", "%s", "x"): True, ("-vPATH", "x"): True, ("%s", "-v"): False,
                 ("--", "-v", "x"): False, (): False, ("x",): False}
        for args, assigns in cases.items():
            with self.subTest(args=args):
                self.assertEqual(ro._printf_assigns(list(args)), assigns)

    def test_imports_from_cwd(self):
        cases = {"python -c 'pass'": True, "/venv/bin/python3.12 -m data_sheets_schema.cli": True,
                 "python script.py": False, "python -I -c 'pass'": False, "linkml-validate F": False,
                 "head -c 10 x": False, "bash -c 'pass'": False,
                 "d4d receipts check": False, "": False}
        for command, imports in cases.items():
            with self.subTest(command=command):
                self.assertEqual(ro._imports_from_cwd(ro._unwrapped(ro._tokens(command) or [])), imports)

    def test_poetry_run_and_chosen_by_cwd(self):
        cases = {"poetry run linkml-validate F": (True, True),
                 "timeout 60 poetry run d4d receipts check": (True, True),
                 "X=1 env nice poetry run d4d x": (True, True),
                 "linkml-validate F": (False, False), "d4d receipts check": (False, False),
                 "python -m data_sheets_schema.cli x": (False, True),
                 "poetry install": (False, False), "echo poetry run d4d": (False, False),
                 "/usr/bin/poetry run d4d x": (False, False), "timeout 60": (False, False), "": (False, False)}
        for command, (poetry, chosen) in cases.items():
            with self.subTest(command=command):
                segment = ro._tokens(command) or []
                self.assertEqual(ro._poetry_run(segment), poetry)
                self.assertEqual(ro._chosen_by_cwd(segment), chosen)

    def test_a_derive_part_is_held_to_the_rules_of_the_parts_read_here(self):
        # The part is read as a derive row (placing nothing, as `--full`
        # names another record) and is still a possible derive of the tracked
        # one where it may not run what its words name (#3722).
        full = ro._Target("full", Path("/x/L/CHORUS_d4d.yaml"))
        for command, unread in (("./d4d derive core --full /o/f.yaml", True),
                                ("./d4d derive core --full 2>/dev/null /o/f.yaml", True),
                                ("cd hack && poetry run d4d derive core --full /o/f.yaml", True),
                                ("d4d derive core --full /o/f.yaml", False),
                                ("cd hack && d4d derive core --full /o/f.yaml", False)):
            with self.subTest(command=command):
                shell = ro._shell(command, None, [full])
                self.assertEqual(len(shell["derives"]), 1)
                self.assertIn(shell["derives"][0]["targets_full"], (False, None))
                self.assertEqual(shell["runs_unread"], unread)

    def test_a_denied_call_never_ran(self):
        r = self.new_run()
        r.write(r.receipt, PRE)
        r.write(r.full, "id: x\n")
        r.bash("bash derive.sh", ok=False, content=ro.NATIVE_DENIAL_PREFIX + "not registered",
               metadata="Error: " + ro.NATIVE_DENIAL_PREFIX)
        r.write(r.receipt, Boundaries.C003)
        r.derive()
        block = r.report()
        self.assertEqual(block["status"], "checked", block["reasons"])
        self.assertEqual(block["possible_unseen_derives"], [])

    def test_validator(self):
        cases = {"linkml-validate -s s.yaml -C Dataset F": True,
                 "linkml-validate --schema=s.yaml F G": True,
                 "linkml-validate -s": False,                       # a valued option with no value
                 "linkml-validate --config c.yaml F": False,
                 "linkml-validate --config=c.yaml F": False,
                 "linkml-validate -m m.py F": False,
                 "linkml-term-validator validate-schema s.yaml": True,
                 "linkml-term-validator validate-data F --adapter x": False,
                 "linkml-term-validator validate-data F -c oak.yaml": False,
                 "linkml-term-validator --help": False,
                 "python3.12 -c 'from linkml.validator.cli import cli; cli()' -s s.yaml F": True,
                 "/opt/venv/bin/python3 -c 'from linkml_term_validator.cli import main; main()' "
                 "validate F -s s.yaml": True,
                 "/venv/bin/linkml-validate -s s.yaml F": True,
                 # A variable or a relative path may name any program (#3689).
                 "${PY} -c 'from linkml_term_validator.cli import main; main()' validate F -s s.yaml": False,
                 "$PY -c 'from linkml.validator.cli import cli; cli()' -s s.yaml F": False,
                 "./python -c 'from linkml.validator.cli import cli; cli()' -s s.yaml F": False,
                 "bin/linkml-validate -s s.yaml F": False, "./linkml-validate -s s.yaml F": False,
                 "python -c 'from linkml.validator.cli import cli;cli()' F": False,
                 "python -c 'from linkml_term_validator.cli import main; main()' -s s.yaml F": False,
                 "python -I -c 'from linkml.validator.cli import cli; cli()' F": False,
                 "bash -c 'linkml-validate F'": False, "": False}
        for command, admitted in cases.items():
            with self.subTest(command=command):
                self.assertEqual(ro._validator(ro._unwrapped(ro._tokens(command) or [])), admitted)


    def test_plainly_run(self):
        # Whether a part runs what its words name (#3689): no assignment
        # before its program, on the part or to `env`, and no variable or
        # relative path as the program or a wrapper.
        cases = {"cat x": True, "/bin/cat x": True, "timeout 60 cat x": True, "env -u X cat x": True,
                 "poetry run linkml-validate F": True, "nice -n 5 d4d receipts check": True,
                 "X=1 cat x": False, "env X=1 cat x": False, "timeout 60 env X=1 cat x": False,
                 "./cat x": False, "bin/cat x": False, "$CAT x": False, "${CAT} x": False,
                 "`which cat` x": False, "$T 60 cat x": False, "./timeout 60 cat x": False,
                 "timeout 60": False, "": False}
        for command, plain in cases.items():
            with self.subTest(command=command):
                self.assertEqual(ro._plainly_run(ro._tokens(command) or []), plain)


class EarlierDirectoryChange(Base):
    """The runtime's shell keeps its directory between calls, so `cd hack`
    in one call starts the next in `hack`, where a `python -c` or `-m` part
    imports a `linkml` or `data_sheets_schema` package first and `poetry run`
    takes that project's virtualenv. Only a change in the same command was
    read (#3699, #3723); one in an earlier call, or a recorded working
    directory other than the one the transcript started in, is now read too
    (#3719)."""

    FULL = UnseenDerive.FULL
    READ_HERE = (UnseenDerive.VALIDATE, UnseenDerive.TERMS,
                 "python -m data_sheets_schema.cli receipts check --receipt R",
                 "poetry run linkml-validate -s s.yaml F")

    def _run(self, earlier, command, *, cwd=None, split=False, **earlier_result):
        """`earlier` before the draft, then the draft, `command` (recorded
        in `cwd` where given), a receipt change, the derive and another."""
        r = self.new_run()
        r.write(r.receipt, PRE)
        if earlier is not None:
            r.bash(earlier.replace("ROOT", str(r.root)), **earlier_result)
        resumed_at = len(r.events)
        r.write(r.full, "id: x\n")
        identity = r.bash(command)
        if cwd is not None:
            r.events[-2]["cwd"] = cwd.replace("ROOT", str(r.root))
        r.write(r.receipt, Boundaries.C003)
        r.derive(full=r.full)
        r.write(r.receipt, Boundaries.C004)
        if not split:
            return identity, r.report()
        # A killed-and-resumed run: the second invocation's shell starts afresh.
        r.receipt.write_text(r.last_receipt, encoding="utf-8")
        first = r.transcript("first.jsonl", r.events[:resumed_at])
        second = r.transcript("second.jsonl", r.events[:1] + r.events[resumed_at:])
        return identity, ro.origin([first, second], r.receipt, r.full)

    def test_a_part_the_directory_chooses_after_an_earlier_change_is_a_possible_derive(self):
        for earlier in ("cd hack", "cd hack && ls", "pushd hack", "ls; cd /tmp",
                        "cd -", "false || cd ROOT", "popd",
                        # Behind a brace, a compound keyword, `!`, `time`,
                        # `builtin` or `command`, the builtin runs in this
                        # shell (#3797).
                        "{ cd hack; }", "if true; then cd hack; fi", "for d in hack; do cd $d; done",
                        "while true; do cd hack; break; done", "if cd hack; then ls; fi",
                        "builtin cd hack", "command cd hack", "command -p cd hack", "time cd hack",
                        "time -p cd hack", "! cd hack", "X=1 builtin cd hack", "{ pushd hack; }",
                        "true && { eval 'cd hack'; }", "builtin eval 'cd hack'",
                        # A command the tokenizer cannot split, read by its text:
                        # a quoted cd word, or any `eval`, counts (#3839).
                        "cd hack; cat <<EOF\nit's\nEOF", "eval 'cd hack'; cat <<EOF\nit's\nEOF",
                        "eval \"$GO\"; cat <<EOF\nit's\nEOF", "X=`cd hack`; cat <<EOF\nit's\nEOF",
                        # A subshell read by the arithmetic's word (#3840).
                        "((cd hack); ls)",
                        # A change in a case clause's body runs here (#3810).
                        "case x in a) cd hack;; esac", "case x in (a) cd hack;; esac",
                        # A subshell, a substitution, a pipe's left side or a
                        # `&` job is a child, and its change dies with it, but
                        # which parts a child runs is not read: it counts, the
                        # rule's cost (#3810, #3830).
                        "(cd hack; ls)", "(cd hack); ls", "echo $(cd hack)", "X=$(cd hack; pwd)",
                        "cd hack | cat", "cd hack &", "(source env.sh)", "if (cd hack); then ls; fi"):
            for command in self.READ_HERE:
                with self.subTest(earlier=earlier, command=command):
                    identity, block = self._run(earlier, command)
                    self.assertUnknown(block, f"Bash call {identity} (transcript 0 line 8) runs a program this "
                                              "does not read")
                    # The one earlier call that is itself open-ended
                    # (`eval "$GO"`, #3852) may have derived after the draft
                    # too; named here, not read from `_shell` (#3908).
                    open_ended = earlier.startswith('eval "$GO"')
                    self.assertEqual([row["tool_use_id"] for row in block["possible_unseen_derives"]],
                                     ["toolu_002"] * open_ended + [identity])

    def test_a_recorded_directory_other_than_the_start_is_read_as_a_change(self):
        for command in self.READ_HERE:
            with self.subTest(command=command):
                identity, block = self._run(None, command, cwd="ROOT/hack")
                self.assertUnknown(block, f"Bash call {identity} (transcript 0 line 6) runs a program")
                _, block = self._run(None, command, cwd="ROOT/./")
                self.assertEqual(block["status"], "checked", block["reasons"])

    def test_a_call_after_no_change_away_from_the_start_is_read_as_before(self):
        for earlier in (None, "ls", "cd ROOT", "cd ROOT && ls", "cd .", "pushd ROOT && popd",
                        "./cd hack", "echo cd hack",
                        # `command -v` describes `cd` without running it, and
                        # a function body being defined is not run (#3797).
                        "command -v cd", "echo builtin cd hack", "f() { cd hack; }",
                        # A program named by a path is a file run in a child,
                        # never a function or an alias (#3782).
                        "./tool.sh", "/usr/bin/python3 fix.py", "poetry run pytest",
                        "nice -n 5 ls", "(( i++ ))", "case x in *) ls;; esac"):
            for command in self.READ_HERE:
                with self.subTest(earlier=earlier, command=command):
                    _, block = self._run(earlier, command)
                    self.assertEqual(block["status"], "checked", block["reasons"])
                    self.assertEqual(block["origin"], {"contemporaneous": 3, "phase1_correction": 1,
                                                       "phase3_backport": 1})
        # A console script run by name takes its code from its own `bin`.
        _, block = self._run("cd hack", "linkml-validate -s s.yaml F")
        self.assertEqual(block["status"], "checked", block["reasons"])
        # A change the native control refused never ran.
        _, block = self._run("cd hack", UnseenDerive.VALIDATE, ok=False,
                             content=ro.NATIVE_DENIAL_PREFIX + "not registered",
                             metadata="Error: " + ro.NATIVE_DENIAL_PREFIX)
        self.assertEqual(block["status"], "checked", block["reasons"])
        # A resumed run's next transcript starts where its own shell did.
        _, block = self._run("cd hack", UnseenDerive.VALIDATE, split=True)
        self.assertEqual(block["status"], "checked", block["reasons"])

    def test_a_relative_full_after_an_earlier_change_cannot_be_placed(self):
        # The transcript's init names where the shell started, not where an
        # earlier `cd` left it, so a relative `--full` does not resolve.
        r = self.new_run()
        r.write(r.receipt, PRE)
        r.bash("cd data")
        r.write(r.full, "id: x\n")
        r.write(r.receipt, Boundaries.C003)
        identity = r.derive()
        r.write(r.receipt, Boundaries.C004)
        block = r.report()
        self.assertUnknown(block, f"derive core {identity} cannot be placed: its --full cannot be resolved")
        self.assertIsNone(block["derive_core_attempts"][0]["targets_full"])
        # So after a change behind a brace or a compound keyword (#3797).
        # And after each change read through a split word or a here-document
        # line that starts with `case` (#3904, #3911, #3912): the derive in
        # the next call is not placed either.
        for earlier in ("{ cd data; }", "if true; then cd data; fi", "builtin cd data",
                        *UnestablishedDirectory.SPLIT_CDS):
            with self.subTest(earlier=earlier):
                r = self.new_run()
                r.write(r.receipt, PRE)
                r.bash(earlier)
                r.write(r.full, "id: x\n")
                r.write(r.receipt, Boundaries.C003)
                identity = r.derive()
                r.write(r.receipt, Boundaries.C004)
                block = r.report()
                self.assertUnknown(block, f"derive core {identity} cannot be placed: its --full cannot be "
                                          "resolved")
                self.assertIsNone(block["derive_core_attempts"][0]["targets_full"])

    #: Directory changes found by the Codex review of round 5 (#3844,
    #: #3845, #3847): a cd eval runs after removing a second level of quotes,
    #: an eval whose command cannot be split, a cd behind a leading
    #: redirection, a builtin's name spelled across an escape or quotes in a
    #: command the tokenizer cannot split, and a program supplied at run
    #: time, which may be the builtin.
    ROUND6_MOVES = ("eval '\"cd\" hack'", "eval 'c\\d hack'", "eval \"'cd' hack\"", "eval \"eval 'cd hack'\"",
                    "eval 'if true; then cd hack; fi'", "eval \"echo 'open\"", "eval '{ cd hack; }'",
                    "2>/dev/null cd hack", ">/dev/null cd hack", "2>&1 pushd hack", "</dev/null cd hack",
                    "{fd}>log cd hack", "X=1 2>/dev/null cd hack", "2>/dev/null eval 'cd hack'",
                    "{ 2>/dev/null cd hack; }", "2>/dev/null builtin cd hack",
                    "c\\d hack; cat <<EOF\nit's\nEOF", "c\"d\" hack; cat <<EOF\nit's\nEOF",
                    "'c'd hack; cat <<EOF\nit's\nEOF", "e\"v\"al 'cd hack'; cat <<EOF\nit's\nEOF",
                    "2>/dev/null cd hack; cat <<EOF\nit's\nEOF",
                    # A program supplied at run time may be the builtin (#3844).
                    "C=cd; $C hack", "$(echo cd) hack", "`echo cd` hack", "{ $C hack; }",
                    "C=cd; $C hack; cat <<EOF\nit's\nEOF")

    def test_round6_changes_move_the_next_call(self):
        # End to end: after each, a later `python -m` validator is unread
        # and a later relative `--full` is not placed (Codex review, #3844,
        # #3845, #3847).
        for earlier in self.ROUND6_MOVES:
            with self.subTest(earlier=earlier):
                self.assertIs(ro._shell(earlier, "/w", [])["moves"], True)
            for command in self.READ_HERE:
                with self.subTest(earlier=earlier, command=command):
                    identity, block = self._run(earlier, command)
                    self.assertUnknown(block, f"Bash call {identity} (transcript 0 line 8) runs a program this "
                                              "does not read")
            with self.subTest(earlier=earlier, rule="derive"):
                r = self.new_run()
                r.write(r.receipt, PRE)
                r.bash(earlier.replace("hack", "data"))
                r.write(r.full, "id: x\n")
                r.write(r.receipt, Boundaries.C003)
                identity = r.derive()
                r.write(r.receipt, Boundaries.C004)
                block = r.report()
                self.assertUnknown(block, f"derive core {identity} cannot be placed: its --full cannot be "
                                          "resolved")
                self.assertIsNone(block["derive_core_attempts"][0]["targets_full"])

    def test_round6_changes_in_the_same_command_leave_no_known_directory(self):
        # `2>/dev/null cd sub && d4d derive core --full data/X` runs the
        # derive in `sub`, and so does one after `eval '"cd" sub'` (#3844,
        # #3845): neither is placed against the start.
        for change in ("2>/dev/null cd sub", ">/dev/null cd sub", "eval '\"cd\" sub'", "eval 'c\\d sub'",
                       "2>/dev/null eval 'cd sub'", "C=cd; $C sub", "eval \"echo 'open\""):
            with self.subTest(change=change):
                r = self.new_run()
                r.write(r.receipt, PRE)
                r.write(r.full, "id: x\n")
                r.write(r.receipt, Boundaries.C003)
                identity = r.bash(f"{change} && d4d derive core --full {r.full.relative_to(r.root)} --out o.yaml")
                r.write(r.receipt, Boundaries.C004)
                block = r.report()
                self.assertUnknown(block, f"derive core {identity} cannot be placed: its --full cannot be "
                                          "resolved")
                [attempt] = block["derive_core_attempts"]
                self.assertIsNone(attempt["targets_full"])
                self.assertIsNone(block["boundaries"]["derive_core"])

    def test_a_relative_full_resolves_against_a_recorded_directory_other_than_the_start(self):
        # Where the transcript records the directory the call started in,
        # a relative `--full` resolves there, not against the start (#3798).
        for spelled, placed in (("../FULL", True), ("FULL", False)):
            with self.subTest(spelled=spelled):
                r = self.new_run()
                r.write(r.receipt, PRE)
                r.write(r.full, "id: x\n")
                r.write(r.receipt, Boundaries.C003)
                full = spelled.replace("FULL", str(r.full.relative_to(r.root)))
                identity = r.bash(f"d4d derive core --full {full} --out o.yaml")
                r.events[-2]["cwd"] = str(r.root / "sub")
                r.write(r.receipt, Boundaries.C004)
                block = r.report()
                [attempt] = block["derive_core_attempts"]
                self.assertEqual(attempt["tool_use_id"], identity)
                self.assertIs(attempt["targets_full"], placed)
                if placed:
                    self.assertEqual(block["status"], "checked", block["reasons"])
                    self.assertEqual(attempt["status_basis"], "command")
                    self.assertIsNotNone(block["boundaries"]["derive_core"])

    def test_after_an_earlier_change_a_recorded_directory_does_not_place_a_relative_full(self):
        # Where an earlier call's change was seen and the transcript also
        # records the call's directory, the earlier change decides: the
        # recorded directory may be inherited from the init event, so the
        # `--full` is not placed, whichever record it would name (#3812).
        # That holds where the call's own event records it too: no
        # transcript here records a per-event directory to check the
        # runtime's against, so it is not trusted (#3824 stays open).
        for spelled in ("../FULL", "FULL"):
            for earlier in ("cd sub", "eval 'cd sub'", "source env.sh", "myfunc"):
                with self.subTest(spelled=spelled, earlier=earlier):
                    r = self.new_run()
                    r.write(r.receipt, PRE)
                    r.bash(earlier)
                    r.write(r.full, "id: x\n")
                    r.write(r.receipt, Boundaries.C003)
                    full = spelled.replace("FULL", str(r.full.relative_to(r.root)))
                    identity = r.bash(f"d4d derive core --full {full} --out o.yaml")
                    r.events[-2]["cwd"] = str(r.root / "sub")
                    r.write(r.receipt, Boundaries.C004)
                    block = r.report()
                    self.assertUnknown(block, f"derive core {identity} cannot be placed: its --full cannot "
                                              "be resolved")
                    [attempt] = block["derive_core_attempts"]
                    self.assertIsNone(attempt["targets_full"])
                    self.assertIsNone(block["boundaries"]["derive_core"])

    def test_after_an_earlier_change_an_inherited_or_earlier_directory_does_not_place_a_relative_full(self):
        # A directory inherited from the init event is where the shell
        # started, which an earlier `cd` does not update (#3812); one the
        # call's event recorded before the change had returned may predate
        # it (#3824). Neither places a relative `--full`, whichever record
        # it would name.
        for spelled in ("../FULL", "FULL"):
            for case in ("inherited", "in_flight", "unreturned", "second_in_flight"):
                with self.subTest(spelled=spelled, case=case):
                    r = self.new_run()
                    r.write(r.receipt, PRE)
                    r.write(r.full, "id: x\n")
                    r.write(r.receipt, Boundaries.C003)
                    full = spelled.replace("FULL", str(r.full.relative_to(r.root)))
                    derive = f"d4d derive core --full {full} --out o.yaml"
                    if case == "inherited":
                        r.bash("cd sub")
                        identity = r.bash(derive)
                    else:
                        if case == "second_in_flight":
                            r.bash("cd other")             # returned; the next change had not
                        change = r.call("Bash", command="cd sub", description="x")
                        identity = r.call("Bash", command=derive, description="x")
                        r.events[-1]["cwd"] = str(r.root / "sub")
                        if case in ("in_flight", "second_in_flight"):
                            r.result(change, "out", {"stdout": "", "stderr": "", "interrupted": False},
                                     is_error=False)
                        r.result(identity, "out", {"stdout": "", "stderr": "", "interrupted": False},
                                 is_error=False)
                    r.write(r.receipt, Boundaries.C004)
                    block = r.report()
                    self.assertUnknown(block, f"derive core {identity} cannot be placed: its --full cannot "
                                              "be resolved")
                    [attempt] = block["derive_core_attempts"]
                    self.assertIsNone(attempt["targets_full"])
                    self.assertIsNone(block["boundaries"]["derive_core"])

    def test_a_recorded_directory_is_not_trusted_after_a_change_wherever_its_result_came_back(self):
        # After a change, a relative `--full` is not placed against the
        # directory a later call's own event records, wherever and whenever
        # the change's result came back (#3812; #3824 stays open): not where
        # it came back only in another transcript (#3906), nor where it came
        # back in its own before the derive was issued, nor where another
        # change was still in flight (#3914).
        def call(identity, command, cwd=None):
            event = {"type": "assistant", "message": {"content": [
                {"type": "tool_use", "id": identity, "name": "Bash", "input": {"command": command}}]}}
            return {**event, "cwd": cwd} if cwd else event

        def result(identity):
            return {"type": "user", "message": {"content": [
                {"type": "tool_result", "tool_use_id": identity, "content": "", "is_error": False}]}}

        targets = [ro._Target("receipt", Path("/w/r.yaml")), ro._Target("full", Path("/w/data/full.yaml"))]
        derive = call("dv", "d4d derive core --full ../data/full.yaml --out o.yaml", "/w/sub")
        for returned in ((1, 1), (0, 3)):
            with self.subTest(returned=returned):
                events = sorted([(0, 1, {"type": "system", "subtype": "init", "cwd": "/w"}),
                                 (0, 2, call("cd", "cd sub")), (0, 10, derive), (0, 11, result("dv")),
                                 (*returned, result("cd"))], key=lambda e: e[:2])
                reasons: list[str] = []
                calls, results = ro._pair(events, reasons)
                self.assertEqual(results["cd"]["transcript"], returned[0])
                history = ro._history(calls, results, targets, reasons)
                self.assertEqual([d["targets_full"] for d in history["derives"]], [None])
        # Two changes, the earlier still in flight when the derive is issued
        # and the later back before it: the #3914 case.
        events = [(0, 1, {"type": "system", "subtype": "init", "cwd": "/w"}),
                  (0, 2, call("a", "cd sub")), (0, 3, call("b", "cd sub")), (0, 4, result("b")),
                  (0, 10, derive), (0, 11, result("dv")), (0, 20, result("a"))]
        reasons = []
        calls, results = ro._pair(events, reasons)
        history = ro._history(calls, results, targets, reasons)
        self.assertEqual([d["targets_full"] for d in history["derives"]], [None])

    def test_a_relative_full_after_an_eval_d_change_in_the_same_command_is_not_placed(self):
        # `eval 'cd sub' && d4d derive core --full data/...` runs the derive
        # in `sub`, so its `--full` names `sub/data/...`, not the tracked
        # record: it is not placed against the start (#3815), nor against
        # a recorded directory.
        for command, cwd in (("eval 'cd sub' && d4d derive core --full FULL --out o.yaml", None),
                             ("eval \"$GO\" && d4d derive core --full FULL --out o.yaml", None),
                             ("true && { eval 'cd sub'; } && d4d derive core --full FULL --out o.yaml", None),
                             ("eval 'cd sub' && d4d derive core --full ../FULL --out o.yaml", "sub")):
            with self.subTest(command=command, cwd=cwd):
                r = self.new_run()
                r.write(r.receipt, PRE)
                r.write(r.full, "id: x\n")
                r.write(r.receipt, Boundaries.C003)
                identity = r.bash(command.replace("FULL", str(r.full.relative_to(r.root))))
                if cwd is not None:
                    r.events[-2]["cwd"] = str(r.root / cwd)
                r.write(r.receipt, Boundaries.C004)
                block = r.report()
                self.assertUnknown(block, f"derive core {identity} cannot be placed: its --full cannot be "
                                          "resolved")
                [attempt] = block["derive_core_attempts"]
                self.assertIsNone(attempt["targets_full"])
                self.assertIsNone(block["boundaries"]["derive_core"])

    def test_shell_moves(self):
        for command, cwd, moves in (("cd hack", "/w", True), ("cd hack && ls", "/w", True),
                                    ("cd /w && ls", "/w", False), ("cd /w/", "/w", False),
                                    ("cd . && ls", "/w", False), ("cd hack/..", "/w", False), ("cd /w", None, True),
                                    ("pushd /w && popd", "/w", False), ("pushd hack && popd", "/w", True),
                                    ("popd", "/w", True), ("cd -", "/w", True), ("cd", "/w", True),
                                    # A child's change counts, as which parts a child
                                    # runs is not read (#3810, #3830).
                                    ("false || cd /w", "/w", True), ("(cd hack; ls)", "/w", True),
                                    ("ls", "/w", False), ("./cd hack", "/w", False),
                                    # `bash` may be a function or an alias (#3782).
                                    ("poetry run cd hack", "/w", False), ("bash -c 'cd hack'", "/w", True),
                                    ("echo cd", "/w", False), ("eval 'cd hack'", "/w", True),
                                    ("eval \"ls; pushd hack\"", "/w", True), ("eval ls", "/w", False),
                                    # A command the tokenizer cannot split counts (#3782).
                                    ("cat <<EOF\nit's\nEOF", "/w", True),
                                    ("cat <<EOF\nit's\nEOF\ncd /w", "/w", True),
                                    # #3797: behind a brace, a compound keyword,
                                    # `!`, `time`, `builtin` or `command`.
                                    ("{ cd hack; }", "/w", True), ("if true; then cd hack; fi", "/w", True),
                                    ("for d in hack; do cd $d; done", "/w", True),
                                    ("if cd hack; then ls; fi", "/w", True), ("else pushd x", "/w", True),
                                    ("until popd; do :; done", "/w", True), ("elif cd x", "/w", True),
                                    ("builtin cd hack", "/w", True), ("builtin -- cd hack", "/w", True),
                                    ("command cd hack", "/w", True), ("command -p cd hack", "/w", True),
                                    ("time cd hack", "/w", True), ("time -p cd hack", "/w", True),
                                    ("! cd hack", "/w", True), ("X=1 builtin cd hack", "/w", True),
                                    ("{ eval 'cd hack'; }", "/w", True), ("builtin eval 'cd x'", "/w", True),
                                    # #3815: a word supplied at run time may be a cd.
                                    ("eval \"$X\"", "/w", True), ("eval `cat f`", "/w", True),
                                    ("{ eval \"$X\"; }", "/w", True), ("echo \"$X\"", "/w", False),
                                    # Through a wrapper, read conservatively.
                                    ("nice eval 'cd hack'", "/w", True),
                                    ("command -v cd", "/w", False), ("command -V cd", "/w", False),
                                    ("echo builtin cd", "/w", False), ("f() { cd x; }", "/w", False),
                                    ("{ ls; }", "/w", False), ("time ls", "/w", False),
                                    # Arithmetic runs no command for the #3782 rule,
                                    # but a word supplied at run time behind `((`
                                    # still counts as it did (#3844).
                                    ("(( i++ ))", "/w", False), ("(( $x ))", "/w", True),
                                    ("(( cd x ))", "/w", True)):
            with self.subTest(command=command, cwd=cwd):
                self.assertEqual(ro._shell(command, cwd, [])["moves"], moves)
        # In the same command, a change behind those words leaves no known
        # directory for a later part's relative `--full` (#3797); a plain
        # one is followed.
        target = [ro._Target("full", "/w/data/X_d4d.yaml")]
        for command, placed in (("{ cd data; } && d4d derive core --full data/X_d4d.yaml --out o.yaml", None),
                                ("{ cd data; } && d4d derive core --full X_d4d.yaml --out o.yaml", None),
                                ("builtin cd /w && d4d derive core --full data/X_d4d.yaml --out o.yaml", None),
                                ("cd data && d4d derive core --full X_d4d.yaml --out o.yaml", True),
                                ("{ ls; } && d4d derive core --full data/X_d4d.yaml --out o.yaml", True),
                                # So does one `eval` runs, or may run (#3815).
                                ("eval 'cd data' && d4d derive core --full X_d4d.yaml --out o.yaml", None),
                                ("eval 'cd data' && d4d derive core --full data/X_d4d.yaml --out o.yaml", None),
                                ("eval \"$X\" && d4d derive core --full data/X_d4d.yaml --out o.yaml", None),
                                ("{ eval 'cd data'; } && d4d derive core --full data/X_d4d.yaml --out o.yaml",
                                 None),
                                ("eval 'cd data'; d4d derive core --full data/X_d4d.yaml --out o.yaml", None),
                                ("eval ls && d4d derive core --full data/X_d4d.yaml --out o.yaml", True)):
            with self.subTest(command=command):
                [row] = ro._shell(command, "/w", target)["derives"]
                self.assertIs(row["targets_full"], placed)
        # A relative path named after a change `eval` runs is a target
        # wherever it may point (#3815).
        for command, named in (("eval 'cd data' && cat X_d4d.yaml", ["full"]), ("eval ls && cat X_d4d.yaml", [])):
            with self.subTest(command=command):
                self.assertEqual(ro._shell(command, "/w", target)["named"], named)
        # `moved` reads a `python -c`/`-m` or `poetry run` part as after a change.
        for command, unread in ((UnseenDerive.VALIDATE, True), ("poetry run d4d receipts check", True),
                                ("linkml-validate -s s.yaml F", False), ("d4d receipts check", False)):
            with self.subTest(command=command):
                self.assertFalse(ro._shell(command, "/w", [])["runs_unread"])
                self.assertEqual(ro._shell(command, "/w", [], moved=True)["runs_unread"], unread)


    #: Parts that may run, in the shell the next call runs in, code not on
    #: the command line: a sourced script, or a program named by a bare word
    #: not read here, which may be a function or an alias (#3782).
    RUNS_CODE_HERE = ("source env.sh", ". ./env.sh", "myfunc", "git status", "python fix.py",
                      "bash -c 'cd hack'", "{ source env.sh; }", "if myfunc; then ls; fi", "eval myfunc",
                      "X=1 myfunc", "2>/dev/null source env.sh", "ls && myfunc", "true; . env.sh",
                      "trap 'cd /tmp' DEBUG", "ls | myfunc", "case x in *) myfunc;; esac",
                      # A child's change dies with it, but which parts a
                      # child runs is not read, so these count (#3810, #3830).
                      "myfunc | cat", "myfunc &", "(myfunc)", "(source env.sh)", "X=$(myfunc)",
                      "echo $(myfunc)", "cat <(myfunc)")
    #: Parts that do not: a path is a file bash runs in a child, and the
    #: names read here are taken as what they name (#3782).
    RUNS_NOTHING_HERE = ("./tool.sh", "/usr/bin/python3 fix.py", "poetry run pytest", "nice -n 5 ls",
                         "timeout 5 cat x", "env X=1 ls", "d4d receipts check --receipt R",
                         "linkml-validate -s s.yaml F", "f() { cd x; }", "export X=1", ":", "false",
                         "for f in a b; do echo $f; done", "case x in *) ls;; esac", "(( i++ ))",
                         "[ -f x ]", "test -f x", "echo \"$(myfunc)\"")

    def test_code_run_in_this_shell_may_move_it(self):
        for command in self.RUNS_CODE_HERE:
            with self.subTest(command=command):
                self.assertIs(ro._shell(command, "/w", [])["moves"], True)
        for command in self.RUNS_NOTHING_HERE:
            with self.subTest(command=command):
                self.assertIs(ro._shell(command, "/w", [])["moves"], False)
        self.assertTrue(ro._may_run_code_here(["source", "x"]))
        self.assertTrue(ro._may_run_code_here([".", "x"]))
        self.assertTrue(ro._may_run_code_here(["myfunc"]))
        self.assertTrue(ro._may_run_code_here(["{", "myfunc"]))
        # #3920: an arithmetic argument does not exempt the part; only `((`
        # at the program position does.
        for command in ("source env.sh $((1))", "myfunc $((1))", "myfunc x $(( n + 1 ))", ". ./env.sh $((1+2))",
                        "((source env.sh; ls) )", "((myfunc; ls) )"):   # the last two: nested subshells (#3922)
            with self.subTest(command=command):
                self.assertIs(ro._shell(command, "/w", [])["moves"], True)
                full = ro._Target("full", "/w/data/X_full.yaml")
                shell = ro._shell(command + " && d4d derive core --full data/X_full.yaml", "/w", [full])
                self.assertEqual([d["targets_full"] for d in shell["derives"]], [None])
        for part in (["./x"], ["/bin/x"], ["$X"], ["cat", "x"], ["cd", "x"], ["eval", "x"], ["f", "()", "{", "x"],
                     ["function", "f"], ["poetry", "run", "x"], ["timeout", "5", "x"], ["d4d", "x", "y"],
                     ["export", "X"], ["((", "i++", "))"], ["if", "((", "x", "))"], ["command", "-v", "x"]):
            with self.subTest(part=part):
                self.assertFalse(ro._may_run_code_here(part))

    def test_code_run_in_this_shell_in_an_earlier_call_moves_the_next(self):
        # End to end (#3782): after each, a later `python -m` or `poetry run`
        # part is unread and a later relative `--full` is not placed.
        for earlier in ("source env.sh", ". ./env.sh", "myfunc", "git status", "{ source env.sh; }",
                        "eval myfunc", "if myfunc; then ls; fi", "myfunc | cat", "(source env.sh)",
                        "X=$(myfunc)"):
            for command in self.READ_HERE:
                with self.subTest(earlier=earlier, command=command):
                    identity, block = self._run(earlier, command)
                    self.assertUnknown(block, f"Bash call {identity} (transcript 0 line 8) runs a program this "
                                              "does not read")
            with self.subTest(earlier=earlier, rule="derive"):
                r = self.new_run()
                r.write(r.receipt, PRE)
                r.bash(earlier)
                r.write(r.full, "id: x\n")
                r.write(r.receipt, Boundaries.C003)
                identity = r.derive()
                r.write(r.receipt, Boundaries.C004)
                block = r.report()
                self.assertUnknown(block, f"derive core {identity} cannot be placed: its --full cannot be "
                                          "resolved")
        for earlier in ("./tool.sh", "/usr/bin/python3 fix.py", "case x in *) ls;; esac", "(( i++ ))"):
            with self.subTest(earlier=earlier):
                _, block = self._run(earlier, UnseenDerive.VALIDATE)
                self.assertEqual(block["status"], "checked", block["reasons"])

    def test_code_run_in_this_shell_leaves_no_known_directory_after_it(self):
        target = [ro._Target("full", "/w/data/X_d4d.yaml")]
        derive = "d4d derive core --full data/X_d4d.yaml --out o.yaml"
        for change, placed in (("source env.sh", None), (". env.sh", None), ("myfunc", None),
                               ("git status", None), ("eval myfunc", None), ("ls", True), ("./tool.sh", True),
                               ("(source env.sh)", None), ("X=$(myfunc)", None), ("myfunc | cat", None)):
            with self.subTest(change=change):
                [row] = ro._shell(f"{change} && {derive}", "/w", target)["derives"]
                self.assertIs(row["targets_full"], placed)
        # A `python -m` part after a change reads as after it in its command,
        # a change in a child included, as which parts a child runs is not
        # read (#3810, #3830).
        self.assertTrue(ro._shell(f"cd hack && {UnseenDerive.VALIDATE}", "/w", [])["runs_unread"])
        for child in ("(cd hack) && ", "cd hack | cat && ", "cd hack & "):
            with self.subTest(child=child):
                self.assertTrue(ro._shell(child + UnseenDerive.VALIDATE, "/w", [])["runs_unread"])
        self.assertTrue(ro._shell(f"(cd hack && {UnseenDerive.VALIDATE})", "/w", [])["runs_unread"])

    def test_a_change_in_a_child_still_counts(self):
        # #3810 stays open: which parts a child runs is not read from the
        # tokenizer's brackets and joins, so every change counts, wherever
        # it runs (#3830). The four spellings #3810 names, and the children
        # and case lines whose reading placed a `--full` (#3904, #3911,
        # #3912). Only a function being defined changes nothing.
        for command, moves in (("case x in a) cd y;; esac", True), ("f() { cd x; }", False),
                               ("(cd x); cd y", True), ("$(cd x) && cd y", True), ("(cd x)", True),
                               ("$(cd x)", True), ("X=$(cd x)", True), ("cd x | cat", True), ("cd x &", True),
                               ("ls | cd x", True), ("(cd x) | cat; cd y", True), ("(source env.sh)", True),
                               ("X=$(myfunc)", True), ("myfunc | cat", True), ("myfunc &", True),
                               ("'(' ; cd x ; ')'", True), ("\\( ; cd x ; \\)", True),
                               ("case x in *) myfunc;; esac", True), ("cat <(myfunc)", True),
                               ("echo $(myfunc)", True),
                               ("cat <<EOF\ncase in point\nEOF\n{ cd sub; }", True),
                               ("cd sub$((0|cat))", True), ("cd $((1|false))", True)):
            with self.subTest(command=command):
                self.assertIs(ro._shell(command, "/w", [])["moves"], moves)
        for gone in ("_subshell_scopes", "_in_child", "_case_patterns", "_unscannable", "_start"):
            with self.subTest(gone=gone):
                self.assertFalse(hasattr(ro, gone))

    def test_a_program_word_built_at_run_time_is_open_ended(self):
        # #3852: at a command's head, such a word may name a detaching program.
        for command in ("$X ./derive.sh", "$(which setsid) ./derive.sh", "`which setsid` ./derive.sh",
                        "set${X}sid ./derive.sh", "./set* ./derive.sh", "{setsid,true} ./derive.sh",
                        "nice $X ./derive.sh", "{ $X ./derive.sh; }", "echo \"$($X ./derive.sh)\"",
                        "echo \"$(echo \"$($X ./d)\")\"", "echo \"`$X ./derive.sh`\"",
                        "bash -c \"$X\"", "bash -c '$X ./derive.sh'", "sh -c 'echo $(date)'", "bash -c \"it's\"",
                        "bash -c 'bash -c \"$X\"'", "eval \"$X\"", "bash -c './set* ./derive.sh'",
                        "bash -c '{setsid,true} ./derive.sh'"):
            with self.subTest(command=command):
                self.assertIs(ro._shell(command, "/w", [])["detaches"], True)
        for command in ("echo \"$(bash derive.sh)\"", "echo $(bash derive.sh)", "X=$(bash derive.sh)",
                        "echo \"$X\"", "ls $X", "bash derive.sh $X", "bash -c 'echo hi'", "[ -f x ]",
                        "case x in *) ls;; esac", "echo $((1 + 2))", "echo \"$((1 + 2))\""):
            with self.subTest(command=command):
                self.assertIs(ro._shell(command, "/w", [])["detaches"], False)
        # End to end: returned before the draft was issued, it may still run on.
        for command in ("$X ./derive.sh", "$(which setsid) ./derive.sh", "bash -c \"$X\""):
            with self.subTest(command=command, rule="end to end"):
                r = self.new_run()
                r.write(r.receipt, PRE)
                identity = r.bash(command)
                r.write(r.full, "id: x\n")
                r.write(r.receipt, Boundaries.C003)
                r.derive(full=r.full)
                block = r.report()
                self.assertUnknown(block, f"Bash call {identity} (transcript 0 line 4) runs a program")
                self.assertEqual([row["tool_use_id"] for row in block["possible_unseen_derives"]], [identity])

    #: An unquoted command substitution, a nested one and a backquoted one,
    #: each ending right before an operator with no space (#3825).
    #: (Readers inside: a bare word not read here may be a function, which
    #: counts wherever it runs, #3782, #3810.)
    SUBSTITUTIONS = ("X=$(pwd)", "ls $(pwd)", "D=$(git rev-parse --show-toplevel)", "X=$(ls $(pwd))", "X=`pwd`")

    def test_tokens_split_an_operator_run_as_bash_does(self):
        # shlex returned `);`, `)&&`, `))` as one token, which the layout
        # does not read as a join (#3825).
        for command, tokens in (("X=$(pwd);cd data", ["X=$", "(", "pwd", ")", ";", "cd", "data"]),
                                ("X=$(pwd)&&cd data", ["X=$", "(", "pwd", ")", "&&", "cd", "data"]),
                                ("X=$(pwd)||cd d", ["X=$", "(", "pwd", ")", "||", "cd", "d"]),
                                ("echo $(pwd)|cd d", ["echo", "$", "(", "pwd", ")", "|", "cd", "d"]),
                                # Arithmetic's `))` is one word, as is one
                                # closing two substitutions (#3840).
                                ("X=$(a $(b));cd d", ["X=$", "(", "a", "$", "(", "b", "))", ";", "cd", "d"]),
                                ("X=$(a $(b)));cd d", ["X=$", "(", "a", "$", "(", "b", "))", ")", ";", "cd", "d"]),
                                ("echo $((1+2));cd d", ["echo", "$", "((", "1+2", "))", ";", "cd", "d"]),
                                ("(( i++ ))&&ls", ["((", "i++", "))", "&&", "ls"]),
                                ("(cd x)&&ls", ["(", "cd", "x", ")", "&&", "ls"]),
                                ("case x in a);; esac", ["case", "x", "in", "a", ")", ";;", "esac"]),
                                # Kept whole: bash's longest operators, and a
                                # definition's `()`, which is not a join.
                                ("ls 2>&1;x", ["ls", "2", ">&", "1", ";", "x"]),
                                ("ls &>/dev/null;x", ["ls", "&>", "/dev/null", ";", "x"]),
                                ("a|&b", ["a", "|&", "b"]), ("a;;&b", ["a", ";;&", "b"]),
                                ("f() { cd x; }", ["f", "()", "{", "cd", "x", ";", "}"]),
                                # A quoted run is text.
                                ("grep -c '<(' f", ["grep", "-c", "<(", "f"]),
                                ("echo ');' x", ["echo", ");", "x"]),
                                ("echo \"a)\";cd x", ["echo", "a)", ";", "cd", "x"]),
                                # (shlex keeps a `$'...'` string's `$`; the run inside is not split.)
                                ("echo $'a);';cd x", ["echo", "$a);", ";", "cd", "x"]),
                                ("echo a\\);cd x", ["echo", "a)", ";", "cd", "x"])):
            with self.subTest(command=command):
                self.assertEqual(ro._tokens(command), tokens)
        # The scan follows bash's quoting: an escaped quote character opens
        # nothing, and `\'` inside `$'...'` does not close it, so the run
        # after each is split or kept as bash reads it.
        self.assertEqual(ro._spaced_operators('echo \\" x);cd y'), 'echo \\" x) ;cd y')
        self.assertEqual(ro._spaced_operators("echo $'it\\'s);' x);cd y"), "echo $'it\\'s);' x) ;cd y")
        # `;;&` ends a case clause, a join; it starts nothing in the background.
        self.assertEqual(ro._layout(ro._tokens("a;;&b"))[0], [["a"], ["b"]])
        self.assertFalse(ro._shell("case x in a) ls;;& b) ls;; esac", "/w", [])["detaches"])
        # A case pattern is read as a command (#3911): a glob there may be a
        # program built at run time, so it is open-ended, the rule's cost.
        self.assertTrue(ro._shell("case x in a) ls;;& *) ls;; esac", "/w", [])["detaches"])
        self.assertTrue(ro._shell("(sleep 1&)", "/w", [])["detaches"])

    def test_no_multi_character_ampersand_operator_reads_as_a_background_ampersand(self):
        # Every operator of more than one character in the lexer's table
        # that carries a `&` is a join, a case terminator or a redirection,
        # never a background `&`: the exclusions are derived from the table,
        # so none can be missed (#3832: `;&` was, beside a hand-listed `;;&`).
        multi = [op for op in ro._SHELL_OPERATORS if "&" in op and len(op) > 1]
        self.assertIn(";&", multi)
        for op in multi:
            with self.subTest(operator=op):
                self.assertFalse(ro._lone_ampersand(op))
        self.assertTrue(ro._lone_ampersand("&"))
        # A quoted word is read as the operators in it: a `&` left once the
        # multi-character operators are removed is still a background `&`.
        self.assertTrue(ro._lone_ampersand("&;&"))
        self.assertTrue(ro._lone_ampersand("&&&"))
        # Read left to right in one pass, as bash's lexer reads `|&&` as
        # `|&` then `&`: removing `&&` first would leave no `&`.
        self.assertTrue(ro._lone_ampersand("|&&"))
        # `;&` falls through to the next case clause; nothing is detached.
        self.assertEqual(ro._tokens("case x in a) ls;& b) ls;; esac").count(";&"), 1)
        self.assertFalse(ro._shell("case x in a) ls;& b) ls;; esac", "/w", [])["detaches"])
        self.assertTrue(ro._shell("case x in a) ls& b) ls;; esac", "/w", [])["detaches"])

    def test_every_part_head_rule_reads_the_command_after_an_unquoted_substitution(self):
        # A `;`, `&&`, `||` or `|` straight after a substitution's closing
        # `)` is a join, so the command after it heads its own part for
        # every rule that reads a part's head (#3825).
        target = [ro._Target("full", "/w/data/X_d4d.yaml")]
        derive = "d4d derive core --full data/X_d4d.yaml --out o.yaml"
        for sub in self.SUBSTITUTIONS:
            for op in (";", "&&", "||", "|", "; ", " && "):
                # A directory change: plain, behind a brace, keyword, `!`,
                # `time`, `builtin` or `command`, or one `eval` runs.
                for tail in ("cd data", "pushd data", "popd", "cd \"$D\"", "{ cd data; }", "if true; then cd data; fi",
                             "! cd data", "time cd data", "builtin cd data", "command cd data",
                             "eval 'cd data'", "eval \"$GO\"", "{ eval \"$GO\"; }"):
                    with self.subTest(sub=sub, op=op, tail=tail):
                        self.assertIs(ro._shell(f"{sub}{op}{tail}", "/w", [])["moves"], True)
                # `git` is a bare word not read here, which may be a
                # function; in a substitution it runs in a child, but which
                # parts a child runs is not read, so it counts (#3782, #3810).
                unread = "git" in sub
                for tail in ("ls", "echo cd data", "command -v cd", "f() { cd data; }", "eval ls"):
                    with self.subTest(sub=sub, op=op, tail=tail):
                        self.assertIs(ro._shell(f"{sub}{op}{tail}", "/w", [])["moves"], unread)
                # A derive heads its own part, and a change before it in the
                # command leaves its relative `--full` unplaced.
                with self.subTest(sub=sub, op=op, rule="derive"):
                    [row] = ro._shell(f"{sub}{op}{derive}", "/w", target)["derives"]
                    self.assertIs(row["targets_full"], None if unread else True)
                    self.assertNotEqual(row.get("basis"), "unparsed")
                    for change in ("cd data", "{ cd data; }", "eval 'cd data'"):
                        [row] = ro._shell(f"{sub}{op}{change} && {derive}", "/w", target)["derives"]
                        self.assertIsNot(row["targets_full"], True, change)
                # A detaching program at a part's head.
                with self.subTest(sub=sub, op=op, rule="detacher"):
                    self.assertTrue(ro._shell(f"{sub}{op}setsid ./derive.sh", "/w", [])["detaches"])

    #: An apostrophe in a here-document's body: shlex cannot split a command
    #: carrying it (#3458).
    UNSPLIT = "; cat <<EOF\nit's\nEOF"

    def test_an_unsplit_command_reads_at_least_every_move_the_tokenised_path_reads(self):
        # The fallback reads the text for a directory or `eval` word, with
        # quote, escape, `$` and backquote characters as word breaks (#3839).
        tokenised = ("cd x", "pushd x", "popd", "{ cd x; }", "builtin cd x", "! cd x", "time cd x",
                     "eval 'cd x'", "eval \"cd x\"", "eval \"$GO\"", "eval `cat f`", "eval $GO",
                     "{ eval \"$GO\"; }", "builtin eval 'pushd x'", "nice eval 'cd x'", "X=$(pwd);cd x",
                     "(cd x; ls)", "echo $(cd x)", "cat <(cd x)", "((cd x); ls)", "eval \\cd x",
                     # Round 6 (#3844, #3845, #3847).
                     "eval '\"cd\" x'", "eval 'c\\d x'", "2>/dev/null cd x", ">/dev/null cd x", "{fd}>l cd x",
                     "c\\d x", "c\"d\" x", "'c'd x", "e\"v\"al 'cd x'", "p\\ushd x", "2>&1 eval ls",
                     "$C x", "${C} x", "`echo cd` x", "X=1 $C x", "'$C' x", "{ $C x; }", "nice $C x",
                     "$(echo cd) x", "2>/dev/null $C x", "echo $C",
                     "eval ls", "ls", "echo hi")
        for command in tokenised:
            with self.subTest(command=command):
                self.assertIsNotNone(ro._tokens(command))
                self.assertIsNone(ro._tokens(command + self.UNSPLIT))
                if ro._shell(command, "/w", [])["moves"]:
                    self.assertIs(ro._shell(command + self.UNSPLIT, "/w", [])["moves"], True)
        # Every such command counts (#3782), not only one whose text carries
        # an `eval`, a quoted or substituted cd word (#3839) or a word
        # starting with `$` or a backquote (#3844): a here-document body's
        # lines are commands to the tokenised path, and any word at a
        # command's start may be a function, an alias or `source`. A false
        # `unknown` is the cost.
        for command in ("eval 'cd x'", "eval \"$GO\"", "eval ls", "X=`cd x`", "echo \"$(cd x)\"", "echo \\cd",
                        "echo evaluate $HOME `date`", "$C x", "X=1 '$C' x",
                        "ls", "echo evaluate 'cdx'", "echo 'cdx'", "echo a$b", "true"):
            with self.subTest(command=command):
                self.assertIs(ro._shell(command + self.UNSPLIT, "/w", [])["moves"], True)

    def test_a_cd_in_a_quoted_or_backquoted_substitution_is_not_read(self):
        # shlex keeps such a substitution inside one word, and its cd moves
        # nothing; the docs say so (#3841). An unquoted one, a process
        # substitution and a subshell run in a child too, and their cd moves
        # nothing either, but which parts a child runs is not read, so they
        # count, the rule's cost (#3810, #3830).
        # A backquoted command with a space in it is split by the tokenizer,
        # so its fragments are read as parts (`x`, `` pwd` ``), which may be
        # a function or a program built at run time: counted (#3782, #3852).
        for command, moves in (("X=`cd x; pwd`", True), ("X=`pwd`", False), ("echo \"$(cd x; pwd)\"", False),
                               ("ls \"$(cd x)\"; ls", False), ("X=\"$(cd /tmp && pwd)\"", False),
                               ("echo \"`cd x`\"", False),
                               ("X=$(cd x; pwd)", True), ("(cd x; ls)", True), ("echo $(cd x)", True),
                               ("cat <(cd x)", True), ("echo >(cd x)", True)):
            with self.subTest(command=command):
                self.assertIs(ro._shell(command, "/w", [])["moves"], moves)

    def test_arithmetic_brackets_are_words(self):
        # `((` and `))` stay whole (#3840); a leading `((` is read as the
        # subshells bash falls back to, so a cd behind it still counts.
        self.assertEqual(ro._split_operators("))&&"), ["))", "&&"])
        self.assertEqual(ro._split_operators(")))"), ["))", ")"])
        self.assertEqual(ro._split_operators("();"), ["()", ";"])
        self.assertEqual(ro._layout(ro._tokens("a && echo $((1+1))"))[1], [["&&"], []])
        for command, moves in (("((cd x); ls)", True), ("(( i++ ))", False), ("echo $((1+2)); cd x", True),
                               ("echo $((1+2))", False), ("((eval \"$GO\"); ls)", True)):
            with self.subTest(command=command):
                self.assertIs(ro._shell(command, "/w", [])["moves"], moves)

    def test_a_change_after_an_unquoted_substitution_moves_the_next_call(self):
        # End to end (#3825): after `X=$(pwd); cd data` the next call starts
        # in `data`, so a `python -m` validator there is unread and a
        # relative `--full` is not placed against the start.
        for sub in self.SUBSTITUTIONS:
            for op in (";", "&&", "; "):
                earlier = f"{sub}{op}cd hack"
                for command in self.READ_HERE:
                    with self.subTest(earlier=earlier, command=command):
                        identity, block = self._run(earlier, command)
                        self.assertUnknown(block, f"Bash call {identity} (transcript 0 line 8) runs a program "
                                                  "this does not read")
                with self.subTest(earlier=earlier, rule="derive"):
                    r = self.new_run()
                    r.write(r.receipt, PRE)
                    r.bash(f"{sub}{op}cd data")
                    r.write(r.full, "id: x\n")
                    r.write(r.receipt, Boundaries.C003)
                    identity = r.derive()
                    r.write(r.receipt, Boundaries.C004)
                    block = r.report()
                    self.assertUnknown(block, f"derive core {identity} cannot be placed: its --full cannot be "
                                              "resolved")
                    self.assertIsNone(block["derive_core_attempts"][0]["targets_full"])
        # A substitution followed by no change leaves the next call as it was.
        for earlier in ("X=$(pwd);ls", "X=$(ls $(pwd))&&ls", "X=`pwd`;ls"):
            with self.subTest(earlier=earlier):
                _, block = self._run(earlier, UnseenDerive.VALIDATE)
                self.assertEqual(block["status"], "checked", block["reasons"])


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
        for option in ("--transcript", "--receipt", "--full", "--receipt-at-run", "--full-at-run", "--json"):
            self.assertIn(option, out.output)

    def test_help_says_the_moved_paths_are_not_the_transcripts_spelling(self):
        # #3591: with --receipt-at-run / --full-at-run, --receipt / --full are
        # the moved files, which the transcript does not name.
        from data_sheets_schema.cli import cli
        text = " ".join(CliRunner().invoke(cli, ["receipts", "origin", "--help"]).output.split())
        self.assertNotIn("spelled or resolving as the transcript's Writes name it", text)
        self.assertIn("without --receipt-at-run it must also be spelled or resolve as the transcript's calls "
                      "name it", text)
        self.assertIn("without --full-at-run it must also be spelled or resolve as the transcript's calls name it",
                      text)

    def test_help_states_the_derive_rule_the_code_applies(self):
        # A successful `derive && …` is the boundary (and_chain), so the help
        # must not say a derive followed by another command never counts (#3186).
        from data_sheets_schema.cli import cli
        # Rendered unwrapped: click breaks a long line at a hyphen, and
        # `linkml-term- validator` is not the text the help carries.
        text = " ".join(CliRunner().invoke(cli, ["receipts", "origin", "--help"], terminal_width=100_000,
                                           max_content_width=100_000).output.split())
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
                      "appends after a `derive` that ends its command, redirections such as `2>&1` aside, "
                      "or after a `derive` with a redirection directly after it) cannot be placed either",
                      text)                                                               # #3426, #3453, #3457
        self.assertIn("A command the tokenizer cannot split (an apostrophe in a heredoc body) is tested "
                      "whole for the same words, and a match cannot be placed", text)      # #3458
        self.assertNotIn("supplying `derive` itself) is not seen", text)
        self.assertIn("A derive whose words are not on the command line (a script, an alias, a variable "
                      "supplying `derive` itself, `python -c` building the arguments) is placed by position: a "
                      "shell call that runs a program this does not read (anything but a reader, a builtin "
                      "`cd`, `pushd` or `popd` -- not `./cd` or `poetry run cd` -- a d4d call of a literal subcommand, or `linkml-validate` or `linkml-term-validator` "
                      "with the options it reads, each run as its words name it: a bare name or absolute path, "
                      "no assignment before it, `printf -v` included, and no directory change before a "
                      "`python -c` or `-m` part or a `poetry run` part, a `derive core` call aimed at another "
                      "record included; the inner command of a command or process substitution is "
                      "never read), that had not returned when the first full-record Write was issued (one in "
                      "flight with it, backgrounded by its `run_in_background` input or its result, or started "
                      "with `&`, `coproc`, `setsid` and the like, or by a process substitution `<(...)` or "
                      "`>(...)`, which bash does not wait for, counts, a `&` inside a nested shell's word "
                      "read as that shell splits a word with a space in it, and the word a shell nested in it "
                      "gives its `-c`, or `eval` or `ssh` runs, read so in turn) and was "
                      "issued before the derive, with a receipt change returning after both it and the first",
                      text)
        self.assertIn("Write were issued, makes the status `unknown`", text)                 # #3369, #3674, #3675, #3676, #3697, #3699, #3700, #3752, #3753
        self.assertIn("A command the tokenizer cannot split is such a call, open-ended where its text carries "
                      "a `&`, `coproc`, `setsid` and the like, `<(` or `>(`.", text)            # #3698, #3752
        self.assertIn("nor a package in the directory the session's shell started in that a `python -c` or "
                      "`-m` part imports first, nor the project there whose virtualenv a `poetry run` part "
                      "takes; after an earlier call whose `cd`, `pushd` or `popd` may have left that "
                      "directory (plain, or behind a brace, a compound keyword, `!`, `time`, `builtin` or "
                      "`command`, or one `eval` runs or may run), or which may run code not on its command "
                      "line in that shell (`source`, `.`, or a program named by a bare word this does not "
                      "read, which may be a function or an alias; not a path, a reader or a d4d call), such a "
                      "part counts as after a directory change, and a relative `--full` cannot be placed, "
                      "even where the transcript records a directory for the call.", text)
        # #3699, #3719, #3723, #3782, #3797, #3812, #3815; #3824 stays open
        self.assertIn("A change in a subshell, an unquoted `$(...)`, `<(...)` or `>(...)`, a pipe's left side "
                      "or a `&` job counts too, though it runs in a child: which parts a child runs is not read "
                      "(#3830); one in a backquoted or double-quoted substitution is not read; and a command the "
                      "tokenizer cannot split counts. Where the transcript records another directory and no "
                      "earlier change was seen, such a part counts as after a change too, and a relative `--full` "
                      "resolves against the recorded directory.", text)          # #3782, #3798, #3810, #3841
        self.assertIn("where every join from the change to the derive is `&&`, and after one `eval` runs or "
                      "may run it cannot be placed.", text)                                     # #3815
        self.assertIn("A redirection before a program is read past (`2>/dev/null cd /tmp`); a program word "
                      "built at run time (`$C /tmp`, `c${X}d`, a glob) counts as a change and, at a part's "
                      "head, as open-ended (`$X ./derive.sh`); the command `eval` runs is its words joined and "
                      "tokenised again (`eval '\"cd\" /tmp'`), and one carrying a word supplied at run time or "
                      "that cannot be split counts as a change and as open-ended; every argument of a shell given "
                      "`-c` (`bash -ceo pipefail 'cmd'`), the command `eval` runs and each run of `ssh`'s "
                      "arguments to the end are read for a `&` and the like, and one carrying a word supplied "
                      "at run time is open-ended (`bash -c \"$X\"`); and a command the tokenizer cannot split "
                      "is open-ended where any word in it starts with `$` or a backquote.", text)  # #3843-#3847, #3852
        for gone in ("unless the call's own event records", "runs in a child and does not count",   # #3824, #3810
                     "where the brackets can be matched"):
            with self.subTest(gone=gone):
                self.assertNotIn(gone, text)
        self.assertIn("A derive whose program is a variable or a relative path (`$PY -m data_sheets_schema.cli`, "
                      "`./d4d`) cannot be placed, as that program may be a wrapper.", text)                 # #3693
        self.assertIn("A script that detaches a child itself is not seen as open-ended", text)    # #3674
        self.assertIn("nor is an environment set outside the command read", text)                  # #3689
        self.assertNotIn("issued after the first full-record Write", text)                        # #3676
        # #3478-#3480: the command-wide backstop and its cost
        self.assertIn("so does a derive call with a redirection among its words (`--full 2>/dev/null F`)", text)
        self.assertIn("Last, a command-wide backstop: a call carrying more `derive` words than these rules gave "
                      "rows, whose raw text with "
                      "quotes and escapes removed carries the whole word `derive` anywhere (a substitution, an "
                      "assignment, a `cd` part, an `xargs` argument) beside a `d4d`, `data_sheets_schema` or "
                      "`$`-variable invocation, cannot be placed; its cost is a false `unknown` (`grep 'd4d "
                      "derive core' notes.md`)", text)
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
