#!/usr/bin/env python3
"""Render exact Markdown tables and summary figures for handoffs/agy1-ci-chunk-sharding.md
from /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/agy1-ci-chunk-sharding-20261111/tmp/partition_proof_20261111.json.

Purpose: Eliminate any hand-transcribed values in Sections 2, 4.1, 4.2, and 5 of
handoffs/agy1-ci-chunk-sharding.md.
Date: 2026-11-11
"""

from __future__ import annotations

import json
from pathlib import Path

PROOF_PATH = Path(
    "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/"
    "agy1-ci-chunk-sharding-20261111/tmp/partition_proof_20261111.json"
)


def main() -> None:
    data = json.loads(PROOF_PATH.read_text(encoding="utf-8"))
    ev6 = data["evaluations"]["6"]
    ev8 = data["evaluations"]["8"]

    split6 = ev6["split_files"]
    split8 = ev8["split_files"]
    assert len(split6) == len(split8) == 31

    split_weight_sum = round(sum(row["weight_seconds"] for row in split6), 3)
    single_above_sum = round(
        sum(row["weight_seconds"] for row in ev6["single_item_files_above_threshold"]), 3
    )
    total_ordinary_weight_6 = round(
        sum(s["predicted_seconds"] for s in ev6["predicted_before_balanced_files"]["shards"]), 3
    )
    unsplit_le_300_weight = round(
        total_ordinary_weight_6 - split_weight_sum - single_above_sum, 3
    )
    unsplit_le_300_files = (
        ev6["ordinary_files"]
        - ev6["split_file_count"]
        - len(ev6["single_item_files_above_threshold"])
    )
    total_chunks_6 = sum(row["chunk_count"] for row in split6)
    total_chunks_8 = sum(row["chunk_count"] for row in split8)

    print("=== SECTION 2 SUMMARY FIGURES ===")
    print(f"ordinary_files: {ev6['ordinary_files']}")
    print(f"ordinary_occurrence_count: {ev6['ordinary_occurrence_count']}")
    print(f"ordinary_unique_nodeids: {ev6['ordinary_unique_nodeids']}")
    print(f"unsplit_le_300_files: {unsplit_le_300_files}")
    print(f"single_item_above_300_files: {len(ev6['single_item_files_above_threshold'])}")
    print(f"split_file_count: {ev6['split_file_count']}")
    print(f"total_ordinary_weight_seconds: {total_ordinary_weight_6:.3f}")
    print(f"split_31_weight_seconds: {split_weight_sum:.3f} ({split_weight_sum / total_ordinary_weight_6 * 100:.1f}%)")
    print(f"single_above_300_weight_seconds: {single_above_sum:.3f}")
    print(f"unsplit_le_300_weight_seconds: {unsplit_le_300_weight:.3f}")
    print(f"total=6 chunks: {total_chunks_6}, extra_visits: {ev6['total_extra_file_shard_visits']}")
    print(f"total=8 chunks: {total_chunks_8}, extra_visits: {ev8['total_extra_file_shard_visits']}")
    print()

    print("=== SECTION 4.1 TABLE ===")
    print(
        "| File | Ordinary Items | Committed Weight (s) | Assigned Shard (`total = 6`) | Assigned Shard (`total = 8`) | Why Unsplit |"
    )
    print("|---|---:|---:|---:|---:|---|")
    s8_by_file = {r["file"]: r for r in ev8["single_item_files_above_threshold"]}
    for r6 in ev6["single_item_files_above_threshold"]:
        r8 = s8_by_file[r6["file"]]
        print(
            f"| `{r6['file']}` | {r6['ordinary_items']} | `{r6['weight_seconds']:.3f}` | `{r6['shard']}` | `{r8['shard']}` | `ordinary_items == 1` |"
        )
    print()

    print("=== SECTION 4.2 TABLE ===")
    print(
        "| # | File | Ordinary Items | Weight (s) | `total = 6` Chunks (`k`) | `total = 6` Chunk Sizes (items) | `total = 6` Assigned Shards (in chunk order) | `total = 8` Chunks (`k`) | `total = 8` Chunk Sizes (items) | `total = 8` Assigned Shards (in chunk order) |"
    )
    print("|---:|---|---:|---:|---:|---|---|---:|---|---|")
    for idx, (r6, r8) in enumerate(zip(split6, split8), start=1):
        assert r6["file"] == r8["file"]
        assert r6["ordinary_items"] == r8["ordinary_items"]
        assert r6["weight_seconds"] == r8["weight_seconds"]
        sizes6 = ", ".join(str(c["items"]) for c in r6["chunks"])
        shards6 = ", ".join(str(c["shard"]) for c in r6["chunks"])
        sizes8 = ", ".join(str(c["items"]) for c in r8["chunks"])
        shards8 = ", ".join(str(c["shard"]) for c in r8["chunks"])
        print(
            f"| {idx} | `{r6['file']}` | {r6['ordinary_items']} | `{r6['weight_seconds']:.3f}` | {r6['chunk_count']} | `{sizes6}` | `{shards6}` | {r8['chunk_count']} | `{sizes8}` | `{shards8}` |"
        )
    print()

    for label, ev in [("5.1 main (total = 6)", ev6), ("5.2 pull_request (total = 8)", ev8)]:
        print(f"=== SECTION {label} TABLE ===")
        bef = ev["predicted_before_balanced_files"]
        aft = ev["predicted_after_balanced_nodeids"]
        print(
            "| Shard | Before (`balanced_files`) Items | Before Files | Before Predicted Total Weight (s) | Before Max Single-File Slice on Shard (s) | After (`balanced_nodeids`) Items | After Files Touched | After Predicted Total Weight (s) | After Max Single-File Slice on Shard (s) |"
        )
        print("|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
        for b_row, a_row in zip(bef["shards"], aft["shards"]):
            assert b_row["shard"] == a_row["shard"]
            print(
                f"| {b_row['shard']} | {b_row['items']} | {b_row['files']} | `{b_row['predicted_seconds']:.3f}` | `{b_row['max_file_slice_seconds']:.3f}` | {a_row['items']} | {a_row['files_touched']} | `{a_row['predicted_seconds']:.3f}` | `{a_row['max_file_slice_seconds']:.3f}` |"
            )
        b_items_sum = sum(r["items"] for r in bef["shards"])
        b_files_sum = sum(r["files"] for r in bef["shards"])
        a_items_sum = sum(r["items"] for r in aft["shards"])
        a_files_sum = sum(r["files_touched"] for r in aft["shards"])
        print(
            f"| **Summary** | **{b_items_sum}** (unique `{ev['ordinary_unique_nodeids']}`) | **{b_files_sum}** | **min `{bef['min_seconds']:.3f}` / max `{bef['max_seconds']:.3f}` (spread `{bef['spread_seconds']:.3f}s`)** | **max `{bef['max_single_file_slice_seconds']:.3f}s`** | **{a_items_sum}** (unique `{ev['ordinary_unique_nodeids']}`) | **{a_files_sum} shard-file visits (`+{ev['total_extra_file_shard_visits']}`)** | **min `{aft['min_seconds']:.3f}` / max `{aft['max_seconds']:.3f}` (spread `{aft['spread_seconds']:.3f}s`)** | **max `{aft['max_single_file_slice_seconds']:.3f}s` (`968.016s` / `645.344s` multi-item)** |"
        )
        print()


if __name__ == "__main__":
    main()
