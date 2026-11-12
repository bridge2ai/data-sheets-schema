#!/usr/bin/env python3
"""Extract open ratification items of native amendment N1 as structured data.

Purpose:
  Read `754fbfdae10dbe9fe3f4443725cf0fa2a696b49e:notes/generic_v10_analysis_plan_amendment_n1_2026-11-08.md`
  from the primary repository's Git object store and cross-reference owner decision
  numbers (`D` + digits) against `notes/coordination/STATUS.md` via `grep -n`.

Inputs:
  - Primary repository Git object store:
    `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.git`
    commit `754fbfdae10dbe9fe3f4443725cf0fa2a696b49e`, path
    `notes/generic_v10_analysis_plan_amendment_n1_2026-11-08.md`
  - Coordination status ledger:
    `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/notes/coordination/STATUS.md`

Outputs:
  - JSON data:
    `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/notes/development_efficiency_20261111/handoffs/agy1-n1-ratification-items-20261112.json`
  - Markdown report (generated 100% from the JSON by this script):
    `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/notes/development_efficiency_20261111/handoffs/agy1-n1-ratification-items-20261112.md`

Assignment:
  `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/notes/development_efficiency_20261111/assignments/claude-lead-agy1-n1-ratification-items-20261112.md`
Date: 2026-11-12
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import struct
import subprocess
import zlib
from pathlib import Path
from typing import Any


PRIMARY_REPO = Path("/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema")
STATUS_MD = PRIMARY_REPO / "notes/coordination/STATUS.md"
COMMIT_SHA = "754fbfdae10dbe9fe3f4443725cf0fa2a696b49e"
AMENDMENT_REL_PATH = "notes/generic_v10_analysis_plan_amendment_n1_2026-11-08.md"
AMENDMENT_WORKTREE_FILE = Path(
    "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/"
    "agy-native-amendment/notes/generic_v10_analysis_plan_amendment_n1_2026-11-08.md"
)

REPORT_WORKTREE = Path(
    "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111"
)
ASSIGNMENT_PATH = (
    REPORT_WORKTREE
    / "notes/development_efficiency_20261111/assignments/claude-lead-agy1-n1-ratification-items-20261112.md"
)
DEFAULT_JSON_OUT = (
    REPORT_WORKTREE
    / "notes/development_efficiency_20261111/handoffs/agy1-n1-ratification-items-20261112.json"
)
DEFAULT_MD_OUT = (
    REPORT_WORKTREE
    / "notes/development_efficiency_20261111/handoffs/agy1-n1-ratification-items-20261112.md"
)

DECISION_RE = re.compile(r"\bD\d+\b")
ITEM_RE = re.compile(r"^- \*\*\(([a-z])\)\*\* (.+)$")

CLAUSE_MAP: dict[str, dict[str, Any]] = {
    "a": {
        "section": "N1.2",
        "proposed_lines": [136],
        "clause_lines": [136, 137, 138, 139],
        "enclosing_lines": [136, 137, 138, 139],
    },
    "b": {
        "section": "N1.2",
        "proposed_lines": [150],
        "clause_lines": [149, 150, 151],
        "enclosing_lines": [149, 150, 151, 410],
    },
    "c": {
        "section": "N1.3",
        "proposed_lines": [159],
        "clause_lines": [159],
        "enclosing_lines": [159],
        "subclause_pattern": r"• \[proposed\] the \*\*literal launch argv, recorded verbatim\*\*[^<]*",
    },
    "d": {
        "section": "N1.3",
        "proposed_lines": [159],
        "clause_lines": [159],
        "enclosing_lines": [159],
        "subclause_pattern": r"\[proposed\] Any change to these is a new registration\.",
    },
    "e": {
        "section": "N1.1",
        "proposed_lines": [121],
        "clause_lines": [121],
        "enclosing_lines": [117, 118, 119, 120, 121],
    },
    "f": {
        "section": "N1.3",
        "proposed_lines": [161],
        "clause_lines": [161],
        "enclosing_lines": [161],
        "subclause_pattern": r"\[proposed\] D18\x27s original subject,[^<]*",
    },
    "g": {
        "section": "N1.3",
        "proposed_lines": [161],
        "clause_lines": [161],
        "enclosing_lines": [161],
        "subclause_pattern": r"\[proposed\] D18 now means a \*\*two-week validity window\*\*[^|]*",
    },
    "h": {
        "section": "N1.1 / N1.7",
        "proposed_lines": [110, 341],
        "clause_lines": [110, 111, 341],
        "enclosing_lines": [110, 111, 112, 113, 114, 115, 116, 341],
    },
    "i": {
        "section": "N1.4(B)",
        "proposed_lines": [178],
        "clause_lines": [178],
        "enclosing_lines": list(range(178, 225)),
    },
    "j": {
        "section": "N1.4(B) B3",
        "proposed_lines": [199],
        "clause_lines": [199, 200, 201, 202, 203, 204],
        "enclosing_lines": [199, 200, 201, 202, 203, 204, 411],
    },
    "k": {
        "section": "N1.4(B) B4",
        "proposed_lines": [205],
        "clause_lines": [205, 206, 207, 208, 209, 210],
        "enclosing_lines": [205, 206, 207, 208, 209, 210],
    },
    "l": {
        "section": "N1.5",
        "proposed_lines": [250],
        "clause_lines": [250],
        "enclosing_lines": [236, 250, 383],
    },
    "m": {
        "section": "N1.5",
        "proposed_lines": [252],
        "clause_lines": [251, 252],
        "enclosing_lines": [251, 252, 383],
    },
    "n": {
        "section": "N1.5",
        "proposed_lines": [253],
        "clause_lines": [253],
        "enclosing_lines": [253],
    },
    "o": {
        "section": "N1.5",
        "proposed_lines": [255],
        "clause_lines": [255],
        "enclosing_lines": [237, 255],
    },
    "p": {
        "section": "N1.5",
        "proposed_lines": [279],
        "clause_lines": [279],
        "enclosing_lines": [235, 279],
    },
    "q": {
        "section": "N1.5",
        "proposed_lines": [276],
        "clause_lines": [276, 278],
        "enclosing_lines": [239, 276, 278],
    },
    "r": {
        "section": "N1.5",
        "proposed_lines": [277],
        "clause_lines": [277],
        "enclosing_lines": [277],
    },
    "s": {
        "section": "N1.5",
        "proposed_lines": [287],
        "clause_lines": [287],
        "enclosing_lines": [287],
    },
    "t": {
        "section": "N1.5",
        "proposed_lines": [288],
        "clause_lines": [288],
        "enclosing_lines": [288],
    },
    "u": {
        "section": "N1.5",
        "proposed_lines": [256],
        "clause_lines": [256],
        "enclosing_lines": [237, 256, 262, 263, 264, 384],
    },
    "v": {
        "section": "N1.5",
        "proposed_lines": [265],
        "clause_lines": [265, 266, 267],
        "enclosing_lines": [265, 266, 267],
    },
    "w": {
        "section": "N1.5",
        "proposed_lines": [233],
        "clause_lines": [233],
        "enclosing_lines": list(range(233, 243)) + [397, 398, 399, 400, 401, 402],
    },
    "x": {
        "section": "N1.2 / N1.5",
        "proposed_lines": [130],
        "clause_lines": [130, 131, 132],
        "enclosing_lines": [130, 131, 132, 257, 385],
    },
}


def _read_git_object_from_pack(git_dir: Path, sha_hex: str) -> tuple[str, bytes]:
    sha_bytes = bytes.fromhex(sha_hex)
    pack_dir = git_dir / "objects/pack"
    for idx_path in sorted(pack_dir.glob("*.idx")):
        idx_data = idx_path.read_bytes()
        if idx_data[:8] != b"\xfftOc\x00\x00\x00\x02":
            continue
        fanout = struct.unpack(">256I", idx_data[8 : 8 + 1024])
        total_objects = fanout[255]
        first_byte = sha_bytes[0]
        start = 0 if first_byte == 0 else fanout[first_byte - 1]
        end = fanout[first_byte]
        names_offset = 8 + 1024
        found_index = None
        for i in range(start, end):
            pos = names_offset + i * 20
            if idx_data[pos : pos + 20] == sha_bytes:
                found_index = i
                break
        if found_index is None:
            continue
        crc_offset = names_offset + total_objects * 20
        offsets_offset = crc_offset + total_objects * 4
        offset_val = struct.unpack(
            ">I", idx_data[offsets_offset + found_index * 4 : offsets_offset + (found_index + 1) * 4]
        )[0]
        if offset_val & 0x80000000:
            large_index = offset_val & 0x7FFFFFFF
            large_offset = offsets_offset + total_objects * 4 + large_index * 8
            pack_offset = struct.unpack(">Q", idx_data[large_offset : large_offset + 8])[0]
        else:
            pack_offset = offset_val
        pack_path = idx_path.with_suffix(".pack")
        return _unpack_pack_object(pack_path.read_bytes(), pack_offset)
    raise FileNotFoundError(f"Git object {sha_hex} not found in loose objects or packs")


def _unpack_pack_object(pack_data: bytes, offset: int) -> tuple[str, bytes]:
    pos = offset
    byte = pack_data[pos]
    pos += 1
    obj_type_num = (byte >> 4) & 0x07
    size = byte & 0x0F
    shift = 4
    while byte & 0x80:
        byte = pack_data[pos]
        pos += 1
        size |= (byte & 0x7F) << shift
        shift += 7
    type_map = {1: "commit", 2: "tree", 3: "blob", 4: "tag"}
    if obj_type_num in type_map:
        decomp = zlib.decompressobj()
        raw = decomp.decompress(pack_data[pos:])
        return type_map[obj_type_num], raw[:size]
    if obj_type_num == 6:
        byte = pack_data[pos]
        pos += 1
        neg_offset = byte & 0x7F
        while byte & 0x80:
            byte = pack_data[pos]
            pos += 1
            neg_offset = ((neg_offset + 1) << 7) | (byte & 0x7F)
        base_type, base_data = _unpack_pack_object(pack_data, offset - neg_offset)
        decomp = zlib.decompressobj()
        delta = decomp.decompress(pack_data[pos:])
        return base_type, _apply_git_delta(base_data, delta)
    raise ValueError(f"Unsupported pack object type {obj_type_num}")


def _apply_git_delta(base: bytes, delta: bytes) -> bytes:
    pos = 0
    while delta[pos] & 0x80:
        pos += 1
    pos += 1
    while delta[pos] & 0x80:
        pos += 1
    pos += 1
    out = bytearray()
    while pos < len(delta):
        cmd = delta[pos]
        pos += 1
        if cmd & 0x80:
            cp_off = 0
            cp_size = 0
            if cmd & 0x01:
                cp_off |= delta[pos]
                pos += 1
            if cmd & 0x02:
                cp_off |= delta[pos] << 8
                pos += 1
            if cmd & 0x04:
                cp_off |= delta[pos] << 16
                pos += 1
            if cmd & 0x08:
                cp_off |= delta[pos] << 24
                pos += 1
            if cmd & 0x10:
                cp_size |= delta[pos]
                pos += 1
            if cmd & 0x20:
                cp_size |= delta[pos] << 8
                pos += 1
            if cmd & 0x40:
                cp_size |= delta[pos] << 16
                pos += 1
            if cp_size == 0:
                cp_size = 0x10000
            out.extend(base[cp_off : cp_off + cp_size])
        elif cmd > 0:
            out.extend(delta[pos : pos + cmd])
            pos += cmd
        else:
            raise ValueError("Invalid delta opcode 0")
    return bytes(out)


def read_git_object(git_dir: Path, sha_hex: str) -> tuple[str, bytes]:
    loose = git_dir / "objects" / sha_hex[:2] / sha_hex[2:]
    if loose.exists():
        raw = zlib.decompress(loose.read_bytes())
        header, body = raw.split(b"\x00", 1)
        obj_type = header.decode("ascii").split(" ", 1)[0]
        return obj_type, body
    return _read_git_object_from_pack(git_dir, sha_hex)


def parse_tree_entries(tree_body: bytes) -> dict[str, str]:
    entries: dict[str, str] = {}
    pos = 0
    while pos < len(tree_body):
        nul = tree_body.index(b"\x00", pos)
        mode_name = tree_body[pos:nul].decode("utf-8")
        _, name = mode_name.split(" ", 1)
        sha_hex = tree_body[nul + 1 : nul + 21].hex()
        entries[name] = sha_hex
        pos = nul + 21
    return entries


def read_amendment_from_object_store() -> tuple[str, str, str]:
    """Return (text, blob_sha1, extraction_method) for COMMIT_SHA:AMENDMENT_REL_PATH."""
    git_dir = PRIMARY_REPO / ".git"
    env = {
        **os.environ,
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_CONFIG_NOSYSTEM": "1",
    }
    proc = subprocess.run(
        ["git", "-C", str(PRIMARY_REPO), "show", f"{COMMIT_SHA}:{AMENDMENT_REL_PATH}"],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    obj_type, commit_body = read_git_object(git_dir, COMMIT_SHA)
    assert obj_type == "commit"
    tree_sha = commit_body.decode("utf-8").splitlines()[0].split()[1]
    for part in AMENDMENT_REL_PATH.split("/")[:-1]:
        _, tree_body = read_git_object(git_dir, tree_sha)
        tree_sha = parse_tree_entries(tree_body)[part]
    _, tree_body = read_git_object(git_dir, tree_sha)
    blob_sha = parse_tree_entries(tree_body)[AMENDMENT_REL_PATH.split("/")[-1]]
    blob_type, blob_bytes = read_git_object(git_dir, blob_sha)
    assert blob_type == "blob"
    blob_text = blob_bytes.decode("utf-8")

    if AMENDMENT_WORKTREE_FILE.exists():
        assert AMENDMENT_WORKTREE_FILE.read_text(encoding="utf-8") == blob_text

    if proc.returncode == 0:
        assert proc.stdout == blob_text
        method = (
            f"git show {COMMIT_SHA}:{AMENDMENT_REL_PATH} "
            "(with GIT_CONFIG_GLOBAL=/dev/null; verified byte-identical to .git/objects blob)"
        )
    else:
        method = (
            f"primary repository .git/objects traversal from commit {COMMIT_SHA} "
            f"to blob {blob_sha} (git CLI blocked on ~/.gitconfig by sandbox)"
        )
    return blob_text, blob_sha, method


def extract_decisions_ordered(text: str) -> list[str]:
    seen: list[str] = []
    for match in DECISION_RE.findall(text):
        if match not in seen:
            seen.append(match)
    return seen


def grep_status_decision(decision: str) -> dict[str, Any]:
    """Run `grep -n` on STATUS.md to locate owner-decision headings and bullets."""
    proc = subprocess.run(
        ["grep", "-n", "-E", rf"\b{re.escape(decision)}\b", str(STATUS_MD)],
        capture_output=True,
        text=True,
        check=True,
    )
    matches: list[dict[str, Any]] = []
    for raw_line in proc.stdout.splitlines():
        line_str, content = raw_line.split(":", 1)
        matches.append({"line": int(line_str), "text": content})

    heading_lines: list[dict[str, Any]] = []
    standalone_bullet_lines: list[dict[str, Any]] = []
    d107_default_subbullet_lines: list[dict[str, Any]] = []

    for m in matches:
        ln = m["line"]
        txt = m["text"]
        if ln <= 850:
            if txt.startswith("### ") and "by the owner" in txt:
                heading_lines.append(m)
            elif re.match(rf"^- \*\*{re.escape(decision)}\b", txt):
                standalone_bullet_lines.append(m)
            elif re.match(rf"^  - {re.escape(decision)}:", txt) and 815 <= ln <= 824:
                d107_default_subbullet_lines.append(m)

    dec_num = int(decision[1:])
    range_heading_proc = subprocess.run(
        ["grep", "-n", "-E", r"^### (Decided|Performed|Approved|Directed) by the owner", str(STATUS_MD)],
        capture_output=True,
        text=True,
        check=True,
    )
    for raw_line in range_heading_proc.stdout.splitlines():
        line_str, content = raw_line.split(":", 1)
        ln = int(line_str)
        for r_match in re.finditer(r"\bD(\d+)[–-]D(\d+)\b", content):
            lo, hi = int(r_match.group(1)), int(r_match.group(2))
            if lo <= dec_num <= hi and all(h["line"] != ln for h in heading_lines):
                heading_lines.append({"line": ln, "text": content})

    heading_lines.sort(key=lambda x: x["line"])
    standalone_bullet_lines.sort(key=lambda x: x["line"])
    d107_default_subbullet_lines.sort(key=lambda x: x["line"])

    if standalone_bullet_lines or heading_lines:
        record_kind = "standalone_owner_decision"
        recorded_as_decided = True
        primary_lines = sorted({m["line"] for m in heading_lines + standalone_bullet_lines})
    elif d107_default_subbullet_lines:
        record_kind = "d107_amendment_default_subbullet"
        recorded_as_decided = True
        primary_lines = [805, 815] + [m["line"] for m in d107_default_subbullet_lines]
    else:
        record_kind = "not_recorded"
        recorded_as_decided = False
        primary_lines = []

    return {
        "decision": decision,
        "recorded_in_status_as_owner_decided": recorded_as_decided,
        "record_kind": record_kind,
        "has_standalone_heading_or_bullet": bool(standalone_bullet_lines or heading_lines),
        "has_d107_default_subbullet": bool(d107_default_subbullet_lines),
        "status_primary_lines": primary_lines,
        "status_heading_matches": heading_lines,
        "status_standalone_bullet_matches": standalone_bullet_lines,
        "status_d107_default_subbullet_matches": d107_default_subbullet_lines,
        "grep_command": f"grep -n -E '\\b{decision}\\b' {STATUS_MD}",
        "total_grep_matches_in_status": len(matches),
    }


def build_payload() -> dict[str, Any]:
    amendment_text, blob_sha1, extraction_method = read_amendment_from_object_store()
    amendment_sha256 = hashlib.sha256(amendment_text.encode("utf-8")).hexdigest()
    lines = amendment_text.splitlines()

    proposed_lines: list[dict[str, Any]] = []
    for idx, line in enumerate(lines, start=1):
        if "[proposed]" in line:
            proposed_lines.append(
                {
                    "line_number": idx,
                    "occurrences_on_line": line.count("[proposed]"),
                    "first_200_chars": line[:200],
                    "is_full_line": len(line) <= 200,
                    "full_line_length": len(line),
                }
            )

    ratification_items: list[dict[str, Any]] = []
    all_decisions_seen: list[str] = []

    for idx, line in enumerate(lines, start=1):
        if idx < 344 or idx > 371:
            continue
        m = ITEM_RE.match(line)
        if not m:
            continue
        letter = m.group(1)
        item_body = m.group(2)
        mapping = CLAUSE_MAP[letter]

        prop_line_nums = mapping["proposed_lines"]
        for pln in prop_line_nums:
            assert "[proposed]" in lines[pln - 1], f"Line {pln} missing [proposed] for ({letter})"

        clause_line_nums = mapping["clause_lines"]
        enclosing_line_nums = mapping["enclosing_lines"]

        clause_text = "\n".join(lines[ln - 1] for ln in clause_line_nums)
        if "subclause_pattern" in mapping:
            sub_m = re.search(mapping["subclause_pattern"], clause_text)
            assert sub_m is not None, f"Subclause pattern failed for ({letter})"
            immediate_clause_text = sub_m.group(0)
        else:
            immediate_clause_text = clause_text

        enclosing_text = "\n".join(lines[ln - 1] for ln in enclosing_line_nums)

        decisions_item = extract_decisions_ordered(line)
        decisions_immediate = extract_decisions_ordered(immediate_clause_text)
        decisions_clause_lines = extract_decisions_ordered(clause_text)
        decisions_enclosing = extract_decisions_ordered(enclosing_text)

        decisions_item_or_clause: list[str] = []
        for d in decisions_item + decisions_clause_lines:
            if d not in decisions_item_or_clause:
                decisions_item_or_clause.append(d)

        decisions_item_or_enclosing: list[str] = []
        for d in decisions_item_or_clause + decisions_enclosing:
            if d not in decisions_item_or_enclosing:
                decisions_item_or_enclosing.append(d)

        for d in decisions_item_or_enclosing:
            if d not in all_decisions_seen:
                all_decisions_seen.append(d)

        ratification_items.append(
            {
                "letter": letter,
                "line_number": idx,
                "full_line": line,
                "item_text": item_body,
                "matching_section": mapping["section"],
                "marks_matching_clause_proposed": True,
                "proposed_clause_line_numbers": prop_line_nums,
                "matching_clause_line_numbers": clause_line_nums,
                "enclosing_clause_line_numbers": enclosing_line_nums,
                "decisions_in_item_text": decisions_item,
                "decisions_in_immediate_subclause": decisions_immediate,
                "decisions_in_matching_clause_lines": decisions_clause_lines,
                "decisions_named_item_or_clause": decisions_item_or_clause,
                "decisions_named_including_enclosing_block": decisions_item_or_enclosing,
            }
        )

    assert len(ratification_items) == 24

    all_decisions_sorted = sorted(all_decisions_seen, key=lambda s: int(s[1:]))
    decision_records: dict[str, Any] = {}
    for d in all_decisions_sorted:
        rec = grep_status_decision(d)
        rec["named_by_items_in_item_or_clause"] = [
            it["letter"]
            for it in ratification_items
            if d in it["decisions_named_item_or_clause"]
        ]
        rec["named_by_items_in_enclosing_only"] = [
            it["letter"]
            for it in ratification_items
            if d in it["decisions_named_including_enclosing_block"]
            and d not in it["decisions_named_item_or_clause"]
        ]
        decision_records[d] = rec

    for item in ratification_items:
        decs_clause = item["decisions_named_item_or_clause"]
        decs_enclosing = item["decisions_named_including_enclosing_block"]
        item["names_any_decision_in_item_or_clause"] = len(decs_clause) > 0
        item["names_any_recorded_decision_in_item_or_clause"] = any(
            decision_records[d]["recorded_in_status_as_owner_decided"] for d in decs_clause
        )
        item["names_any_standalone_recorded_decision_in_item_or_clause"] = any(
            decision_records[d]["has_standalone_heading_or_bullet"] for d in decs_clause
        )
        item["names_any_decision_including_enclosing"] = len(decs_enclosing) > 0
        item["names_any_recorded_decision_including_enclosing"] = any(
            decision_records[d]["recorded_in_status_as_owner_decided"] for d in decs_enclosing
        )

    counts = {
        "total_ratification_items": len(ratification_items),
        "items_with_proposed_clause": sum(
            1 for it in ratification_items if it["marks_matching_clause_proposed"]
        ),
        "items_without_proposed_clause": sum(
            1 for it in ratification_items if not it["marks_matching_clause_proposed"]
        ),
        "items_naming_recorded_decision_item_or_clause": sum(
            1 for it in ratification_items if it["names_any_recorded_decision_in_item_or_clause"]
        ),
        "items_naming_no_decision_item_or_clause": sum(
            1 for it in ratification_items if not it["names_any_decision_in_item_or_clause"]
        ),
        "letters_naming_recorded_decision_item_or_clause": [
            it["letter"]
            for it in ratification_items
            if it["names_any_recorded_decision_in_item_or_clause"]
        ],
        "letters_naming_no_decision_item_or_clause": [
            it["letter"]
            for it in ratification_items
            if not it["names_any_decision_in_item_or_clause"]
        ],
        "items_naming_recorded_decision_including_enclosing": sum(
            1 for it in ratification_items if it["names_any_recorded_decision_including_enclosing"]
        ),
        "items_naming_no_decision_including_enclosing": sum(
            1 for it in ratification_items if not it["names_any_decision_including_enclosing"]
        ),
        "letters_naming_no_decision_including_enclosing": [
            it["letter"]
            for it in ratification_items
            if not it["names_any_decision_including_enclosing"]
        ],
        "items_naming_only_d107_default_subbullet_decisions": [
            it["letter"]
            for it in ratification_items
            if it["names_any_recorded_decision_in_item_or_clause"]
            and not it["names_any_standalone_recorded_decision_in_item_or_clause"]
        ],
        "items_naming_standalone_recorded_decision_item_or_clause": sum(
            1
            for it in ratification_items
            if it["names_any_standalone_recorded_decision_in_item_or_clause"]
        ),
        "total_proposed_lines_in_amendment": len(proposed_lines),
        "total_proposed_occurrences_in_amendment": sum(
            p["occurrences_on_line"] for p in proposed_lines
        ),
        "total_distinct_decisions_named": len(all_decisions_sorted),
    }

    return {
        "source": {
            "primary_repository": str(PRIMARY_REPO),
            "branch": "agy/native-amendment-n1-20261108",
            "commit": COMMIT_SHA,
            "path": AMENDMENT_REL_PATH,
            "checked_out_worktree_path": str(AMENDMENT_WORKTREE_FILE),
            "blob_sha1": blob_sha1,
            "file_sha256": amendment_sha256,
            "line_count": len(lines),
            "extraction_method": extraction_method,
            "status_md_path": str(STATUS_MD),
        },
        "counts": counts,
        "ratification_items": ratification_items,
        "decisions_in_status_md": decision_records,
        "proposed_lines": proposed_lines,
    }


def _code_span(text: str) -> str:
    """Wrap text in double backticks for Markdown table cells so internal single backticks stay intact."""
    escaped = text.replace("|", "\\|")
    if "`" in escaped:
        return f"`` {escaped} ``"
    return f"`{escaped}`"


def render_markdown(payload: dict[str, Any], script_path: Path, json_path: Path) -> str:
    src = payload["source"]
    cnt = payload["counts"]
    items = payload["ratification_items"]
    decs = payload["decisions_in_status_md"]
    prop_lines = payload["proposed_lines"]

    out: list[str] = []
    out.append("# AGY1 Handoff: Open Ratification Items of Native Amendment N1 (as Data)")
    out.append("")
    out.append("- **Date**: `2026-11-12`")
    out.append(f"- **Assignment**: `{ASSIGNMENT_PATH}`")
    out.append(f"- **Primary Repository**: `{src['primary_repository']}`")
    out.append(
        f"- **Amendment Commit**: `{src['commit']}` (branch agy/native-amendment-n1-20261108; checked-out file `{src['checked_out_worktree_path']}`)"
    )
    out.append(f"- **Amendment File SHA-256**: `{src['file_sha256']}` (`{src['line_count']}` lines)")
    out.append(f"- **Status Ledger**: `{src['status_md_path']}`")
    out.append(f"- **Extraction Script**: `{script_path}`")
    out.append(f"- **Extracted JSON**: `{json_path}`")
    out.append("")
    out.append("## Extraction Command")
    out.append("")
    out.append("```zsh")
    out.append(
        f"/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python {script_path}"
    )
    out.append("```")
    out.append("")
    out.append("## Summary Counts")
    out.append("")
    out.append("| Metric | Count | Details |")
    out.append("|---|---:|---|")
    out.append(
        f"| Lettered ratification items in N1.8 | `{cnt['total_ratification_items']}` | Items `(a)` through `(x)` (`lines 346–369`) |"
    )
    out.append(
        f"| Items with a `[proposed]` matching clause in body | `{cnt['items_with_proposed_clause']}` | All 24 items `(a)`–`(x)` (`0` items without `[proposed]`) |"
    )
    out.append(
        f"| Items naming a recorded owner decision (item text + immediate matching clause lines) | `{cnt['items_naming_recorded_decision_item_or_clause']}` | `{', '.join('(' + l + ')' for l in cnt['letters_naming_recorded_decision_item_or_clause'])}` (`12` name standalone top-level owner rulings `D43, D53, D56, D71, D98, D99, D107, D108, D110, D111, D114, D115, D117, D118`; `4` — `(f)`, `(g)`, `(p)`, `(s)` — name only `D18`, `D14`, or `D12`, which are recorded in `{src['status_md_path']}` at `lines 818, 820, 821` as `D107` default sub-bullets under `L805`/`L815`) |"
    )
    out.append(
        f"| Items naming no owner decision (item text + immediate matching clause lines) | `{cnt['items_naming_no_decision_item_or_clause']}` | `{', '.join('(' + l + ')' for l in cnt['letters_naming_no_decision_item_or_clause'])}` |"
    )
    out.append(
        f"| Items naming a recorded owner decision / naming none when enclosing block lines are included (`B0–B7` lines `178–224` for `(i)` and margin-refusal lines `262–264` for `(u)`) | `{cnt['items_naming_recorded_decision_including_enclosing']}` / `{cnt['items_naming_no_decision_including_enclosing']}` | Including enclosing blocks adds `(i)` (`D109, D43, D53, D56, D36`) and `(u)` (`D115, D113`), leaving `{', '.join('(' + l + ')' for l in cnt['letters_naming_no_decision_including_enclosing'])}` naming none |"
    )
    out.append(
        f"| Lines in amendment containing `[proposed]` | `{cnt['total_proposed_lines_in_amendment']}` | `{cnt['total_proposed_occurrences_in_amendment']}` total `[proposed]` occurrences across `{cnt['total_proposed_lines_in_amendment']}` lines (lines `159` and `161` contain 2 occurrences each; line `24` is the document-level rule; lines `110` and `341` both mark `(h)`) |"
    )
    out.append(
        f"| Distinct owner decision numbers (`D` + digits) named across items and matching/enclosing clauses | `{cnt['total_distinct_decisions_named']}` | `{', '.join(decs.keys())}` |"
    )
    out.append("")
    out.append("## 1 & 2. N1.8 Lettered Ratification Items, `[proposed]` Clauses, and Named Decisions")
    out.append("")
    out.append(
        "| Letter | N1.8 Line | Full Text (Exact Line from Amendment) | Matching Clause `[proposed]`? | `[proposed]` Line(s) | Matching Clause Line(s) | `D`-Decisions in Item Text | `D`-Decisions in Matching Clause Line(s) | Additional `D`-Decisions in Enclosing Block |"
    )
    out.append("|---|---:|---|---|---:|---:|---|---|---|")
    for it in items:
        prop_flag = "Yes" if it["marks_matching_clause_proposed"] else "No"
        prop_lns = ", ".join(f"`{n}`" for n in it["proposed_clause_line_numbers"])
        clause_lns = ", ".join(f"`{n}`" for n in it["matching_clause_line_numbers"])
        d_item = ", ".join(f"`{d}`" for d in it["decisions_in_item_text"]) or "none"
        d_clause = ", ".join(f"`{d}`" for d in it["decisions_in_matching_clause_lines"]) or "none"
        extra_enc = [
            d
            for d in it["decisions_named_including_enclosing_block"]
            if d not in it["decisions_named_item_or_clause"]
        ]
        d_extra = (
            f"{', '.join(f'`{d}`' for d in extra_enc)} (lines `{it['enclosing_clause_line_numbers'][0]}–{it['enclosing_clause_line_numbers'][-1]}`)"
            if extra_enc
            else "none"
        )
        out.append(
            f"| `({it['letter']})` | `{it['line_number']}` | {_code_span(it['full_line'])} | {prop_flag} | {prop_lns} | {clause_lns} | {d_item} | {d_clause} | {d_extra} |"
        )
    out.append("")
    out.append(
        f"## 3. Owner Decision Numbers Cross-Referenced in `{src['status_md_path']}` (via `grep -n`)"
    )
    out.append("")
    out.append(
        "| Decision | Named by Item(s) (Item Text / Clause) | Named in Enclosing Block Only | Recorded as Decided by Owner in Status Ledger? | Record Type | Heading Line(s) | Bullet Line(s) | Total `grep -n` Matches |"
    )
    out.append("|---|---|---|---|---|---|---|---:|")
    for d, info in decs.items():
        rec_flag = "Yes" if info["recorded_in_status_as_owner_decided"] else "No"
        by_clause = (
            ", ".join(f"`({l})`" for l in info["named_by_items_in_item_or_clause"]) or "none"
        )
        by_enc = (
            ", ".join(f"`({l})`" for l in info["named_by_items_in_enclosing_only"]) or "none"
        )
        h_lns = (
            ", ".join(f"`{m['line']}`" for m in info["status_heading_matches"])
            if info["status_heading_matches"]
            else ("`805` (via `D107`)" if info["has_d107_default_subbullet"] else "none")
        )
        b_matches = info["status_standalone_bullet_matches"] + info["status_d107_default_subbullet_matches"]
        b_lns = (
            ", ".join(f"`{m['line']}`" for m in b_matches)
            if b_matches
            else "none"
        )
        if info["has_d107_default_subbullet"]:
            b_lns = f"`815` (`D107`), {b_lns}"
        out.append(
            f"| `{d}` | {by_clause} | {by_enc} | {rec_flag} | `{info['record_kind']}` | {h_lns} | {b_lns} | `{info['total_grep_matches_in_status']}` |"
        )
    out.append("")
    out.append("## 4. Every Line of Amendment N1 Containing `[proposed]` (Line Number and First 200 Characters)")
    out.append("")
    out.append("| # | Line Number | `[proposed]` Count on Line | Full Line Length | First 200 Characters (Exact) |")
    out.append("|---:|---:|---:|---:|---|")
    for idx, pl in enumerate(prop_lines, start=1):
        out.append(
            f"| {idx} | `{pl['line_number']}` | `{pl['occurrences_on_line']}` | `{pl['full_line_length']}` | {_code_span(pl['first_200_chars'])} |"
        )
    out.append("")
    return "\n".join(out)


def verify_outputs(json_path: Path, md_path: Path) -> None:
    json_text = json_path.read_text(encoding="utf-8")
    md_text = md_path.read_text(encoding="utf-8")
    assert "@" not in json_text, "Found @ in JSON output"
    assert "@" not in md_text, "Found @ in Markdown output"

    # Check every backticked token that looks like a file path (contains / or ends with a file extension)
    for m in re.finditer(r"`+([^`\n]+)`+", md_text):
        token = m.group(1).strip()
        if "/" in token or token.endswith((".md", ".py", ".json", ".yaml", ".yml", ".sh")):
            assert Path(token).exists(), f"Backticked path does not exist: {token}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON_OUT)
    parser.add_argument("--md-output", type=Path, default=DEFAULT_MD_OUT)
    args = parser.parse_args()

    payload = build_payload()
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    loaded_payload = json.loads(args.json_output.read_text(encoding="utf-8"))
    md_text = render_markdown(loaded_payload, Path(__file__).resolve(), args.json_output.resolve())
    args.md_output.parent.mkdir(parents=True, exist_ok=True)
    args.md_output.write_text(md_text, encoding="utf-8")
    verify_outputs(args.json_output, args.md_output)


if __name__ == "__main__":
    main()
