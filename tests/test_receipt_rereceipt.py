"""The uncovered-leaf list and the re-receipt validator (#2926, PR 1).

`uncovered_receiptable_leaves` is the untruncated list `check` truncates to
50 under `slots.without_receipt`, computed by the same functions; a
slot-driven re-receipt turn asks about exactly these paths, and
`apply_rereceipt` validates the answers and merges the verified ones into a
copy of the receipt. Nothing here is wired into a runner.
"""
import copy
import hashlib
from pathlib import Path
from unittest import mock

import pytest
import yaml

from data_sheets_schema import receipts as rc

ROOT = Path(__file__).resolve().parents[1]

BUNDLE = ("=" * 80 + "\nCONCATENATED DOCUMENT\n" + "=" * 80 + "\n\n"
          "FILE: a.txt\nPATH: x/a.txt\nSIZE: 1 bytes\n" + "-" * 80 + "\n"
          "The AI-READI dataset (Grant OT2OD032644) is a longitudinal, multimodal study.\n"
          "Funded by the NIH Common Fund's Bridge2AI program.\n\n" + "=" * 80 + "\n\n"
          "FILE: b.txt\nPATH: x/b.txt\nSIZE: 1 bytes\n" + "-" * 80 + "\n"
          "References\n[1] Something else entirely.\n")

FULL = {"id": "https://x/ds", "name": "ai-readi", "title": "AI-READI", "page": "https://x/page",
        "description": "a longitudinal, multimodal study", "conforms_to_class": "Dataset",
        "notes": "the run's own commentary",
        "funders": [{"id": "https://x/ds#funder-1", "name": "NIH Common Fund", "grant_id": "OT2OD032644"}],
        "file_collections": [{"id": "https://x/page#fc1", "name": "raw",
                              "resources": [{"id": "https://x/ds#f1", "name": "a.tsv", "md5": "0" * 32}]}],
        "keywords": ["multimodal"]}


def _manifest_and_texts(bundle=BUNDLE):
    from data_sheets_schema.chunking import chunk_text, chunk_texts
    chunks = chunk_text(bundle)
    return ({"bundle_md5": hashlib.md5(bundle.encode()).hexdigest(), "chunks": chunks},
            dict(zip([c["id"] for c in chunks], chunk_texts(bundle, chunks))))


def _receipt(md5, pairs):
    return {"bundle_md5": md5, "chunks": [
        {"id": "c001", "status": "nothing_relevant", "reason": "bundle header"},
        {"id": "c002", "status": "extracted", "extracted": pairs},
        {"id": "c003", "status": "nothing_relevant", "reason": "references only"}]}


def _both(receipt, manifest, texts, full, original=None):
    """(the helper's list, check's block) for the same arguments."""
    md5 = manifest["bundle_md5"]
    return (rc.uncovered_receiptable_leaves(receipt, manifest, texts, full, md5, original=original),
            rc.check(receipt, manifest, texts, full, md5, original))


def _agrees(paths, block):
    s = block["slots"]
    return len(paths) == s["receiptable"] - s["with_receipt"] and paths[:50] == s["without_receipt"]


# ------------------------------------------------------------ uncovered leaves
class TestUncoveredReceiptableLeaves:
    def test_exempt_leaves_are_not_listed(self):
        manifest, texts = _manifest_and_texts()
        paths, block = _both(_receipt(manifest["bundle_md5"], [
            {"slot": "title", "snippet": "AI-READI dataset"}]), manifest, texts, FULL)
        assert _agrees(paths, block)
        # commentary, the class declaration, fragments on the record's own
        # id (#722) and on its carried page (#1123) have no bundle receipt
        for p in ("conforms_to_class", "notes", "funders[0].id",
                  "file_collections[0].id", "file_collections[0].resources[0].id"):
            assert p not in paths
        assert "id" in paths                                           # the own id names the record (#843)
        assert "title" not in paths
        assert block["slots"]["exempt_on_carried_identifier"] == 1

    def test_an_entry_receipt_covers_its_leaves_and_a_list_receipt_does_not(self):
        manifest, texts = _manifest_and_texts()
        entry, _ = _both(_receipt(manifest["bundle_md5"], [
            {"slot": "funders[0]", "snippet": "Grant OT2OD032644"}]), manifest, texts, FULL)
        assert "funders[0].name" not in entry and "funders[0].grant_id" not in entry
        listed, block = _both(_receipt(manifest["bundle_md5"], [
            {"slot": "funders", "snippet": "Grant OT2OD032644"}]), manifest, texts, FULL)
        assert {"funders[0].name", "funders[0].grant_id"} <= set(listed)          # #721
        assert _agrees(listed, block)

    def test_an_unattesting_snippet_earns_no_coverage_here_either(self):
        manifest, texts = _manifest_and_texts()
        paths, block = _both(_receipt(manifest["bundle_md5"], [
            {"slot": "title", "snippet": "AI"}]), manifest, texts, FULL)             # below the #720 floors
        assert block["snippets"]["unattesting"] == 1
        assert "title" in paths and _agrees(paths, block)

    @pytest.mark.parametrize("where", ["chunk not in the manifest", "chunk without text"])
    def test_a_below_floor_snippet_check_cannot_read_still_earns_what_check_credits(self, where):
        # check() judges a below-floor snippet unattesting only in a chunk the
        # manifest lists and whose text it has; elsewhere the path is credited.
        # The helper must list exactly what check() leaves without a receipt (#3320).
        manifest, texts = _manifest_and_texts()
        receipt = _receipt(manifest["bundle_md5"], [{"slot": "description", "snippet": "a longitudinal, multimodal study"}])
        if where == "chunk not in the manifest":
            receipt["chunks"].append({"id": "c099", "status": "extracted",
                                      "extracted": [{"slot": "title", "snippet": "AI"}]})
            texts = {**texts, "c099": "AI-READI"}                  # text alone does not make it listed
        else:
            receipt["chunks"][1]["extracted"].append({"slot": "title", "snippet": "AI"})
            texts = {k: v for k, v in texts.items() if k != "c002"}
        paths, block = _both(receipt, manifest, texts, FULL)
        assert block["snippets"]["unattesting"] == 0
        assert "title" not in block["slots"]["without_receipt"]
        assert paths == block["slots"]["without_receipt"]
        assert "title" not in paths and _agrees(paths, block)

    def test_the_list_is_not_truncated(self):
        manifest, texts = _manifest_and_texts()
        full = {**FULL, "creators": [{"name": f"Person {i}"} for i in range(70)]}
        paths, block = _both(_receipt(manifest["bundle_md5"], [
            {"slot": "title", "snippet": "AI-READI dataset"}]), manifest, texts, full)
        s = block["slots"]
        assert len(s["without_receipt"]) == 50 and s["without_receipt_truncated"] > 0
        assert len(paths) == s["receiptable"] - s["with_receipt"] > 70
        assert paths[:50] == s["without_receipt"]
        assert [p for p, _v in rc.populated_leaves(full) if p in set(paths)] == paths   # record order

    def test_a_snapshot_decides_credit_as_check_does(self):
        manifest, texts = _manifest_and_texts()
        # phase 1 wrote two funders; reconcile dropped the first. A receipt
        # at funders[0] is the dropped entry's, not the survivor's (#907).
        original = {**FULL, "funders": [{"name": "Gates Foundation", "grant_id": "X1"},
                                        {"name": "NIH Common Fund", "grant_id": "OT2OD032644"}]}
        receipt = _receipt(manifest["bundle_md5"], [
            {"slot": "funders[0].name", "snippet": "Funded by the NIH Common Fund"},
            {"slot": "funders[1].grant_id", "snippet": "Grant OT2OD032644"}])
        paths, block = _both(receipt, manifest, texts, FULL, original=original)
        assert _agrees(paths, block)
        assert "funders[0].grant_id" not in paths                  # followed by identity to its new index
        assert "funders[0].name" in paths                          # the dropped entry's receipt earns nothing
        without_snapshot, _ = _both(receipt, manifest, texts, FULL)
        assert paths != without_snapshot

    def test_the_bundle_md5_argument_has_no_bearing(self):
        manifest, texts = _manifest_and_texts()
        receipt = _receipt(manifest["bundle_md5"], [{"slot": "title", "snippet": "AI-READI dataset"}])
        assert (rc.uncovered_receiptable_leaves(receipt, manifest, texts, FULL, None)
                == rc.uncovered_receiptable_leaves(receipt, manifest, texts, FULL, "0" * 32))


# ------------------------------------------------------------- apply_rereceipt
def _setup():
    manifest, texts = _manifest_and_texts()
    receipt = _receipt(manifest["bundle_md5"], [{"slot": "title", "snippet": "AI-READI dataset"}])
    listed = rc.uncovered_receiptable_leaves(receipt, manifest, texts, FULL, manifest["bundle_md5"])
    return manifest, texts, receipt, listed


class TestApplyRereceipt:
    def test_a_verified_snippet_is_merged_and_closes_the_leaf(self):
        manifest, texts, receipt, listed = _setup()
        assert "funders[0].grant_id" in listed
        before = copy.deepcopy(receipt)
        out = rc.apply_rereceipt(receipt, FULL, [
            {"path": "funders[0].grant_id", "receipt": {"chunk": "c002", "snippet": "Grant OT2OD032644"}}],
            texts, listed=listed)
        assert (out["added"], out["unsupported"], out["rejected"]) == (1, 0, 0)
        assert receipt == before                                    # the input receipt is not modified
        pairs = out["receipt"]["chunks"][1]["extracted"]
        assert pairs[-1] == {"slot": "funders[0].grant_id", "snippet": "Grant OT2OD032644"}
        after = rc.uncovered_receiptable_leaves(out["receipt"], manifest, texts, FULL, manifest["bundle_md5"])
        assert set(listed) - set(after) == {"funders[0].grant_id"}
        block = rc.check(out["receipt"], manifest, texts, FULL, manifest["bundle_md5"])
        assert block["findings_gated"] == 0 and block["snippets"]["mismatched"] == 0

    @pytest.mark.parametrize("answer, reason", [
        ({"path": "funders[0].grant_id", "receipt": {"chunk": "c003", "snippet": "Grant OT2OD032644"}},
         "snippet not verified in c003"),                          # verbatim, but in another chunk
        ({"path": "funders[0].grant_id", "receipt": {"chunk": "c002", "snippet": "Grant OT2OD099999"}},
         "snippet not verified in c002"),
        ({"path": "funders[0].grant_id", "receipt": {"chunk": "c002", "snippet": "OT2"}},
         "snippet not verified in c002: too short"),
        ({"path": "funders[0].grant_id", "receipt": {"chunk": "c099", "snippet": "Grant OT2OD032644"}},
         "unknown chunk"),
        ({"path": "title", "receipt": {"chunk": "c002", "snippet": "AI-READI dataset"}},
         "path was not listed"),                                   # already covered
        ({"path": "no_such_slot", "receipt": {"chunk": "c002", "snippet": "AI-READI dataset"}},
         "path was not listed"),
        ({"path": "funders[0].grant_id", "unsupported": True, "reason": "x",
          "receipt": {"chunk": "c002", "snippet": "Grant OT2OD032644"}}, "both receipt and unsupported"),
        ({"path": "funders[0].grant_id"}, "no action"),
        ({"path": "funders[0].grant_id", "unsupported": "true", "reason": "x"},
         "unsupported must be the boolean true"),
        ({"path": "funders[0].grant_id", "unsupported": True}, "unsupported without a reason"),
        ({"path": "funders[0].grant_id", "receipt": "c002: Grant OT2OD032644"}, "receipt is not a"),
        ({"path": "funders[0].grant_id", "receipt": {"chunk": "c002", "snippet": "  "}}, "empty snippet"),
        ("funders[0].grant_id", "not a mapping"),
    ])
    def test_a_bad_answer_is_rejected_with_its_reason(self, answer, reason):
        _manifest, texts, receipt, listed = _setup()
        out = rc.apply_rereceipt(receipt, FULL, [answer], texts, listed=listed)
        assert (out["added"], out["unsupported"], out["rejected"]) == (0, 0, 1)
        assert out["rejections"][0]["reason"].startswith(reason)
        assert out["receipt"] == receipt

    def test_a_path_answered_twice_takes_neither_answer(self):
        _manifest, texts, receipt, listed = _setup()
        out = rc.apply_rereceipt(receipt, FULL, [
            {"path": "funders[0].grant_id", "receipt": {"chunk": "c002", "snippet": "Grant OT2OD032644"}},
            {"path": "funders[0].grant_id", "unsupported": True, "reason": "not stated"}],
            texts, listed=listed)
        assert (out["added"], out["unsupported"], out["rejected"]) == (0, 0, 2)
        assert out["receipt"] == receipt

    def test_a_listed_path_the_record_does_not_carry_is_rejected(self):
        _manifest, texts, receipt, listed = _setup()
        out = rc.apply_rereceipt(receipt, FULL, [
            {"path": "funders[3].name", "unsupported": True, "reason": "x"}],
            texts, listed=listed + ["funders[3].name"])
        assert out["rejections"][0]["reason"] == "path does not resolve in the record"

    def test_a_duplicate_of_chunk_takes_no_pair(self):
        manifest, texts, receipt, listed = _setup()
        receipt["chunks"][2] = {"id": "c003", "status": "duplicate_of", "of": "c002"}
        out = rc.apply_rereceipt(receipt, FULL, [
            {"path": "keywords", "receipt": {"chunk": "c003", "snippet": "Something else entirely"}}],
            texts, listed=listed)
        assert out["rejected"] == 1 and "duplicate_of" in out["rejections"][0]["reason"]

    @pytest.mark.parametrize("entries", [0, 2])
    def test_a_chunk_without_exactly_one_entry_takes_no_pair(self, entries):
        _manifest, texts, receipt, listed = _setup()
        receipt["chunks"] = [c for c in receipt["chunks"] if c["id"] != "c002"]
        receipt["chunks"] += [{"id": "c002", "status": "extracted",
                               "extracted": [{"slot": "title", "snippet": "AI-READI dataset"}]}
                              for _ in range(entries)]
        out = rc.apply_rereceipt(receipt, FULL, [
            {"path": "funders[0].grant_id", "receipt": {"chunk": "c002", "snippet": "Grant OT2OD032644"}}],
            texts, listed=listed)
        assert (out["added"], out["rejected"]) == (0, 1)
        assert out["rejections"][0]["reason"] == f"chunk c002 has {entries} entries in the receipt, not one"
        assert out["receipt"] == receipt

    @pytest.mark.parametrize("extracted", ["title: AI-READI dataset", ["AI-READI dataset"],
                                           {"slot": "title", "snippet": "AI-READI dataset"}])
    def test_a_malformed_extracted_is_rejected_not_raised(self, extracted):
        _manifest, texts, receipt, listed = _setup()
        receipt["chunks"][1]["extracted"] = extracted
        out = rc.apply_rereceipt(receipt, FULL, [
            {"path": "funders[0].grant_id", "receipt": {"chunk": "c002", "snippet": "Grant OT2OD032644"}}],
            texts, listed=listed)
        assert (out["added"], out["already_present"], out["rejected"]) == (0, 0, 1)
        assert out["rejections"][0] == {
            "index": 0, "path": "funders[0].grant_id",
            "reason": "chunk c002's extracted is not a list of {slot, snippet} mappings"}
        assert out["receipt"] == receipt

    def test_unsupported_paths_are_recorded_with_their_reasons(self):
        _manifest, texts, receipt, listed = _setup()
        out = rc.apply_rereceipt(receipt, FULL, [
            {"path": "keywords", "unsupported": True, "reason": " inferred from the title "},
            {"path": "description", "unsupported": True, "reason": "paraphrase"}], texts, listed=listed)
        assert (out["added"], out["unsupported"], out["rejected"]) == (0, 2, 0)
        assert out["unsupported_paths"] == [{"path": "keywords", "reason": "inferred from the title"},
                                            {"path": "description", "reason": "paraphrase"}]
        assert out["receipt"] == receipt                           # an unsupported path changes no receipt

    def test_a_nothing_relevant_chunk_becomes_extracted_and_keeps_its_prior(self):
        manifest, texts, receipt, listed = _setup()
        out = rc.apply_rereceipt(receipt, FULL, [
            {"path": "keywords", "receipt": {"chunk": "c003", "snippet": "Something else entirely"}}],
            texts, listed=listed)
        entry = out["receipt"]["chunks"][2]
        assert entry == {"id": "c003", "status": "extracted",
                         "rereceipt_prior": {"status": "nothing_relevant", "reason": "references only"},
                         "extracted": [{"slot": "keywords", "snippet": "Something else entirely"}]}
        assert out["status_changed"] == ["c003"]
        block = rc.check(out["receipt"], manifest, texts, FULL, manifest["bundle_md5"])
        assert block["findings_gated"] == 0

    def test_a_redundant_with_chunk_becomes_extracted_and_keeps_its_chunks(self):
        manifest, texts, receipt, listed = _setup()
        receipt["chunks"][2] = {"id": "c003", "status": "redundant_with", "chunks": ["c002"]}
        out = rc.apply_rereceipt(receipt, FULL, [
            {"path": "keywords", "receipt": {"chunk": "c003", "snippet": "Something else entirely"}}],
            texts, listed=listed)
        assert (out["added"], out["rejected"]) == (1, 0)
        assert out["receipt"]["chunks"][2] == {
            "id": "c003", "status": "extracted",
            "rereceipt_prior": {"status": "redundant_with", "chunks": ["c002"]},
            "extracted": [{"slot": "keywords", "snippet": "Something else entirely"}]}
        assert out["status_changed"] == ["c003"]
        assert receipt["chunks"][2] == {"id": "c003", "status": "redundant_with", "chunks": ["c002"]}
        block = rc.check(out["receipt"], manifest, texts, FULL, manifest["bundle_md5"])
        assert block["findings_gated"] == 0

    def test_the_record_is_never_modified(self):
        _manifest, texts, receipt, listed = _setup()
        record = copy.deepcopy(FULL)
        rc.apply_rereceipt(receipt, record, [
            {"path": "funders[0].grant_id", "receipt": {"chunk": "c002", "snippet": "Grant OT2OD032644"}},
            {"path": "keywords", "unsupported": True, "reason": "x"},
            {"path": "title", "receipt": {"chunk": "c002", "snippet": "AI-READI"}}], texts, listed=listed)
        assert record == FULL

    def test_re_application_is_idempotent(self):
        _manifest, texts, receipt, listed = _setup()
        answers = [
            {"path": "funders[0].grant_id", "receipt": {"chunk": "c002", "snippet": "Grant OT2OD032644"}},
            {"path": "keywords", "receipt": {"chunk": "c003", "snippet": "Something else entirely"}},
            {"path": "description", "unsupported": True, "reason": "paraphrase"},
            {"path": "name", "receipt": {"chunk": "c099", "snippet": "x" * 20}}]
        once = rc.apply_rereceipt(receipt, FULL, answers, texts, listed=listed)
        twice = rc.apply_rereceipt(once["receipt"], FULL, answers, texts, listed=listed)
        assert twice["receipt"] == once["receipt"]
        assert (once["added"], once["already_present"]) == (2, 0)
        assert (twice["added"], twice["already_present"]) == (0, 2)
        assert (twice["unsupported"], twice["rejected"]) == (once["unsupported"], once["rejected"]) == (1, 1)
        assert twice["status_changed"] == []


# ---------------------------------------------------------------- corpus
def _v8_api_receipts():
    base = ROOT / "data/d4d_concatenated/claudecode_api_core"
    found = sorted(base.glob("*-generic-v8_rep*/*_coverage_receipt.yaml")) if base.is_dir() else []
    return [pytest.param(p, id=f"{p.parent.name}/{p.name}") for p in found]


@pytest.mark.corpus
@pytest.mark.parametrize("receipt", _v8_api_receipts())
def test_the_helper_counts_what_every_committed_v8_api_block_states(receipt, monkeypatch):
    """For each committed v8 API record, recomputed through `d4d receipts
    check` itself: the helper, given the arguments that command passes to
    `check`, lists exactly receiptable − with_receipt paths of the block
    stored in the provenance record, and the block's truncated list is its
    head."""
    from click.testing import CliRunner

    from data_sheets_schema.cli.receipts import receipts as group
    project = receipt.name.split("_coverage_receipt")[0]
    label = receipt.parent.name
    prov = receipt.parent / f"{project}_provenance.yaml"
    stored = (yaml.safe_load(prov.read_text(encoding="utf-8")).get("receipts") or {}).get("slots") or {}
    calls = []
    real = rc.check

    def spy(*args, **kwargs):
        calls.append((args, kwargs, real(*args, **kwargs)))
        return calls[-1][2]

    monkeypatch.chdir(ROOT)
    before = prov.read_bytes()
    with mock.patch.object(rc, "check", spy):
        result = CliRunner().invoke(group, ["check", "--method", "claudecode_api",
                                            "--label", label, "--project", project])
    assert result.exit_code == 0, result.output
    if not calls:
        pytest.skip(f"{label}/{project} was not checked here: {result.output.strip()[:200]}")
    (args, kwargs, block), = calls
    paths = rc.uncovered_receiptable_leaves(*args, **kwargs)
    assert len(paths) == stored["receiptable"] - stored["with_receipt"]
    assert len(paths) == block["slots"]["receiptable"] - block["slots"]["with_receipt"]
    assert paths[:50] == block["slots"]["without_receipt"] == stored["without_receipt"]
    assert prov.read_bytes() == before


# ---------------------------------------------------------------- reconcile_receipt
def test_reconcile_receipt_retains_and_prunes():
    receipt = {
        "bundle_md5": "abc",
        "chunks": [
            {
                "id": "c001",
                "status": "extracted",
                "extracted": [
                    {"slot": "title", "snippet": "AI-READI Dataset"},
                    {"slot": "extension_mechanism.extension_details", "snippet": "none"},
                ],
            },
            {
                "id": "c002",
                "status": "extracted",
                "extracted": [
                    {"slot": "download_url", "snippet": "https://fairhub.io/dataset/1"},
                ],
            },
            {
                "id": "c003",
                "status": "nothing_relevant",
                "reason": "references",
            },
        ],
    }
    orig = {
        "title": "AI-READI Dataset",
        "extension_mechanism": {"extension_details": "none"},
        "download_url": "https://fairhub.io/dataset/1",
        "funders": [
            {"name": "NIH", "grant_id": "OT2OD032644"},
            {"name": "NSF", "grant_id": "12345"},
        ],
    }
    final = {
        "title": "AI-READI Dataset",
        "funders": [
            {"name": "NSF", "grant_id": "12345"},
            {"name": "NIH", "grant_id": "OT2OD032644"},
        ],
    }
    clean_rc, stats = rc.reconcile_receipt(receipt, orig, final)
    assert stats["retained"] == 1
    assert stats["dropped"] == 2
    assert stats["emptied"] == 1

    c1 = next(c for c in clean_rc["chunks"] if c["id"] == "c001")
    assert c1["status"] == "extracted"
    assert c1["extracted"] == [{"slot": "title", "snippet": "AI-READI Dataset"}]

    c2 = next(c for c in clean_rc["chunks"] if c["id"] == "c002")
    assert c2["status"] == "nothing_relevant"
    assert "dropped during reconciliation" in c2["reason"]
    assert "extracted" not in c2

    c3 = next(c for c in clean_rc["chunks"] if c["id"] == "c003")
    assert c3["status"] == "nothing_relevant"
    assert c3["reason"] == "references"


def test_reconcile_receipt_remaps_moved_list_entry():
    receipt = {
        "bundle_md5": "abc",
        "chunks": [
            {
                "id": "c001",
                "status": "extracted",
                "extracted": [
                    {"slot": "funders[0].grant_id", "snippet": "OT2OD032644"},
                ],
            },
        ],
    }
    orig = {
        "funders": [
            {"name": "NIH", "grant_id": "OT2OD032644"},
        ],
    }
    final = {
        "funders": [
            {"name": "Other", "grant_id": "99999"},
            {"name": "NIH", "grant_id": "OT2OD032644"},
        ],
    }
    clean_rc, stats = rc.reconcile_receipt(receipt, orig, final)
    assert stats["remapped"] == 1
    assert stats["dropped"] == 0
    c1 = clean_rc["chunks"][0]
    assert c1["extracted"] == [{"slot": "funders[1].grant_id", "snippet": "OT2OD032644"}]


def test_reconcile_receipt_is_pure():
    receipt = {
        "bundle_md5": "abc",
        "chunks": [
            {"id": "c001", "status": "extracted", "extracted": [{"slot": "drop_me", "snippet": "foo"}]},
        ],
    }
    before = copy.deepcopy(receipt)
    clean_rc, stats = rc.reconcile_receipt(receipt, None, {"keep_me": "bar"})
    assert receipt == before
    assert clean_rc["chunks"][0]["status"] == "nothing_relevant"


def test_reconcile_receipt_prunes_unpopulated_leaves():
    """Empty string and None leaf slots in final must be pruned as dropped (#4905)."""
    receipt = {
        "bundle_md5": "abc",
        "chunks": [
            {
                "id": "c001",
                "status": "extracted",
                "extracted": [
                    {"slot": "title", "snippet": "AI-READI Dataset"},
                    {"slot": "version", "snippet": "v1.0.0"},
                    {"slot": "description", "snippet": "Empty description"},
                    {"slot": "license", "snippet": "Null license"},
                ],
            },
        ],
    }
    orig = {
        "title": "AI-READI Dataset",
        "version": "v1.0.0",
        "description": "Empty description",
        "license": "Null license",
    }
    final = {
        "title": "AI-READI Dataset",
        "version": "v1.0.0",
        "description": "",      # emptied during repair
        "license": None,        # blanked during repair
    }
    clean_rc, stats = rc.reconcile_receipt(receipt, orig, final)
    assert stats["retained"] == 2
    assert stats["dropped"] == 2
    c1 = clean_rc["chunks"][0]
    assert c1["status"] == "extracted"
    assert c1["extracted"] == [
        {"slot": "title", "snippet": "AI-READI Dataset"},
        {"slot": "version", "snippet": "v1.0.0"},
    ]


