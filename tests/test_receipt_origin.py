"""Receipt origin: contemporaneous, Phase 1 and Phase 3 snippets told apart
from the transcript, and `unknown` wherever the history cannot be rebuilt
(#2933). Synthetic transcripts only."""
import json
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

    def bash(self, command, *, ok=True):
        identity = self.call("Bash", command=command, description="x")
        self.result(identity, "out", {"stdout": "", "stderr": "", "interrupted": False,
                                      "isImage": False}, is_error=not ok)
        return identity

    def derive(self, *, ok=True, full=None):
        return self.bash(f"poetry run d4d derive core \\\n  --full {full or self.full.relative_to(self.root)}"
                         f" \\\n  --out data/claudecode_direct_core/L/CHORUS_d4d_core.yaml", ok=ok)

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
        self.assertEqual(block["deltas"]["draft_to_derive_core"], {"removed": 0, "added": 0})
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
        self.assertIsNone(block["deltas"]["derive_core_to_final"])
        self.assertEqual(block["origin"], {"contemporaneous": 3, "phase1_correction": 1, "phase3_backport": 0})

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
        checked = rc.check(receipt, manifest, texts, FULL, manifest["bundle_md5"])
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


class Unknown(Base):
    def _complete(self):
        r = self.new_run()
        r.write(r.receipt, PRE)
        r.write(r.full, "id: x\n")
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

    def test_an_edit_of_the_receipt_is_unknown(self):
        r = self._complete()
        identity = r.call("Edit", file_path=str(r.receipt), old_string="a", new_string="b")
        r.result(identity, "ok", {"filePath": str(r.receipt)})
        self.assertUnknown(r.report(), "may change the receipt other than by a Write")

    def test_a_refused_edit_is_listed_not_a_mutation(self):
        r = self._complete()
        identity = r.call("Edit", file_path=str(r.receipt), old_string="a", new_string="b")
        r.result(identity, "Error: not allowed", is_error=True)
        block = r.report()
        self.assertEqual(block["status"], "checked", block["reasons"])
        self.assertEqual(block["rejected_writes"][0]["tool"], "Edit")

    def test_a_shell_mutation_of_the_receipt_is_unknown(self):
        rel = "data/claudecode_direct_core/L/CHORUS_coverage_receipt.yaml"
        for command in (f"cat >> {rel} <<'EOF'\n- id: c009\nEOF",
                        f"sed -i '' 's/a/b/' {rel}",
                        f"python -c \"open('{rel}', 'a').write('x')\"",
                        f"cd data && sed -i.bak s/a/b/ claudecode_direct_core/L/CHORUS_coverage_receipt.yaml",
                        f"grep x {rel}\nrm {rel}",
                        "echo 'unbalanced CHORUS_coverage_receipt.yaml"):
            with self.subTest(command=command[:30]):
                r = self._complete()
                r.bash(command, ok=False)             # a failed command may still have written
                self.assertUnknown(r.report(), "Bash call")

    def test_read_only_shell_commands_are_not_mutations(self):
        r = self._complete()
        rel = "data/claudecode_direct_core/L/CHORUS_coverage_receipt.yaml"
        for command in (f"grep -n c001 {rel} 2>&1 | head -5",
                        f"sed -n '1,20p' {rel} > /dev/null",
                        f"wc -l {r.receipt}",
                        "cat data/ATTIC/CHORUS_coverage_receipt.yaml.bak > /tmp/x",
                        "poetry run d4d receipts check --label L --project CHORUS --strict",
                        f"poetry run d4d receipts invert --receipt {rel}"):
            r.bash(command)
        block = r.report()
        self.assertEqual(block["status"], "checked", block["reasons"])
        self.assertEqual(block["non_write_mutations"], [])

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
