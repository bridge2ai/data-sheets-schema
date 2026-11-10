"""Synthetic receipt/source-review component boundaries, 2026-11-10.

Receipt attestation and review of present claims do not establish complete
final-record acceptance. These tests do not execute native or API generation,
admission, typed assembly, or the complete final-evidence gate.
"""

import hashlib
import json

import yaml


IDENTIFIER = "https://example.org/dataset/n1-fictional"
FULL = ("id: " + IDENTIFIER + "\n").encode()
BUNDLE = (
    "FILE: protocol.txt\nPATH: protocol.txt\n"
    "The dataset identifier is " + IDENTIFIER + ".\n"
    "The fictional dataset contains two measurement tables.\n"
).encode()


def save_evidence(tmp_path, name, value):
    payload = {
        "scope": "synthetic component checks; no generation execution or acceptance",
        "whole_native_acceptance": "unverified",
        "whole_generation_acceptance": "unverified",
        "full_sha256": hashlib.sha256(FULL).hexdigest(),
        "bundle_sha256": hashlib.sha256(BUNDLE).hexdigest(),
        **value,
    }
    with (tmp_path / (name + ".json")).open("x", encoding="utf-8") as stream:
        json.dump(payload, stream, indent=2, sort_keys=True)
        stream.write("\n")


def source_inputs():
    from data_sheets_schema import chunking, evidence_assertions

    manifest = chunking.manifest_from_bytes(BUNDLE, "n1-fictional-bundle.txt")
    chunks, _ = evidence_assertions.source_chunks_from_bytes(
        BUNDLE, yaml.safe_dump(manifest).encode()
    )
    assert len(manifest["chunks"]) == 1
    return manifest, chunks


def test_receipt_v4_distinguishes_unattested_stub_from_identifier_attestation(tmp_path):
    """A real refusal for zero attestation is not a universal stub guard."""
    from data_sheets_schema import canary, receipts

    manifest, chunks = source_inputs()
    chunk = manifest["chunks"][0]["id"]
    record = yaml.safe_load(FULL)
    rows = {}
    for mode in ("unattested", "literal_identifier_only"):
        entry = {
            "id": chunk,
            "status": "nothing_relevant",
            "reason": "Synthetic negative case declares no extraction.",
        }
        if mode == "literal_identifier_only":
            entry = {
                "id": chunk,
                "status": "extracted",
                "extracted": [{
                    "slot": "id",
                    "snippet": "The dataset identifier is " + IDENTIFIER + ".",
                }],
            }
        receipt = {"bundle_md5": manifest["bundle_md5"], "chunks": [entry]}
        block = receipts.check(
            receipt, manifest,
            {key: item["text"] for key, item in chunks.items()}, record,
            manifest["bundle_md5"], record,
            instrument_version=4, identifier_bases=(),
        )
        rows[mode] = {
            "receipt": receipt,
            "checked_block": block,
            "floors": canary.receipt_floors(block),
        }
    save_evidence(tmp_path, "receipt-v4", {
        "cases": rows,
        "checked_components": ["receipts.check", "canary.receipt_floors"],
        "not_exercised": [
            "typed assembly reconstruction", "registered receipt policy admission",
            "complete final-evidence gate", "complete native or API acceptance",
        ],
    })
    empty = rows["unattested"]
    assert empty["checked_block"]["findings"] == []
    assert empty["checked_block"]["chunks"]["total"] == 1
    assert empty["checked_block"]["chunks"]["reviewed"] == 1
    assert empty["checked_block"]["snippets"]["verified"] == 0
    assert empty["floors"]["receipts vacuous"] == 1
    literal = rows["literal_identifier_only"]
    assert literal["checked_block"]["findings"] == []
    assert literal["checked_block"]["snippets"]["verified"] == 1
    assert literal["checked_block"]["slots"]["receiptable"] == 1
    assert literal["checked_block"]["slots"]["with_receipt"] == 1
    assert not any(literal["floors"].values())


def test_source_review_covers_id_claim_without_proving_omission_recall(tmp_path):
    """Reviewing a supported present claim does not measure omitted source facts."""
    from data_sheets_schema import source_review

    manifest, chunks = source_inputs()
    chunk = manifest["chunks"][0]["id"]
    review = {
        "artifact": "final_full",
        "sha256": hashlib.sha256(FULL).hexdigest(),
        "values": [{"path": "/id", "claims": [{
            "text": IDENTIFIER,
            "verdict": "supported",
            "attributed_to": ["protocol.txt"],
            "claim_status": "fact",
            "source_status": "fact",
            "evidence": [{
                "source": "protocol.txt", "chunk": chunk,
                "quote": "The dataset identifier is " + IDENTIFIER + ".",
            }],
            "reason": "The fictional source explicitly names this exact identifier.",
        }]}],
    }
    checked = source_review.check(
        review, raw=FULL.decode(), artifact="final_full",
        chunks=chunks, protocol_version=7,
    )
    save_evidence(tmp_path, "source-review", {
        "source_review": checked,
        "checked_components": ["source_review.check"],
        "omitted_source_fact": "The fictional dataset contains two measurement tables.",
        "not_exercised": [
            "typed audit/reconciliation assembly", "omission recall",
            "complete final-evidence gate with audit totals",
            "complete native or API acceptance",
        ],
    })
    assert checked["findings"] == []
    assert checked["claims_checked"] == 1
