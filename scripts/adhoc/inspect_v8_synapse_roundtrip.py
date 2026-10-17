#!/usr/bin/env python3
"""Diagnose public Synapse v8 HTML round trips without authentication or writes.

Purpose: #5055 live-publication verification failure, 2026-10-16.
Inputs: anonymous public table queries and committed src/html/output/v8 assets.
Outputs: raw query responses and bounded text/hash comparisons under --output-dir
(outside the repository). No credential files, SDK login, uploads or snapshots.
"""

import argparse
from collections import Counter
from difflib import SequenceMatcher
import hashlib
import json
from pathlib import Path
import re
import subprocess
import time
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[2]
API = "https://repo-prod.prod.sagebase.org/repo/v1"
TABLE = "syn68885644"
FAILED_UPLOAD_COMMIT = "289863340cf864bf0ed6ec2197ca8cb637eec5f1"
FILES = {
    ("css", ""): "datasheet-v8.css",
    ("html", "B2AI_ORG:114"): "D4D_-_AI-READI_v8_human_readable.html",
    ("html", "B2AI_ORG:115"): "D4D_-_CHORUS_v8_human_readable.html",
    ("html", "B2AI_ORG:116"): "D4D_-_CM4AI_v8_human_readable.html",
    ("html", "B2AI_ORG:117"): "D4D_-_VOICE_v8_human_readable.html",
}


def request(path, body=None):
    data = None if body is None else json.dumps(body).encode("utf-8")
    # urllib has no netrc or credential-file discovery and no cookies/session.
    call = Request(API + path, data=data, headers={
        "Accept": "application/json", "Content-Type": "application/json",
    })
    with urlopen(call, timeout=30) as response:
        return response.status, json.load(response)


def query(table_reference, output):
    rows = []
    page = 0
    while True:
        path = f"/entity/{TABLE}/table/query/async"
        _, started = request(path + "/start", {
            "concreteType": "org.sagebionetworks.repo.model.table.QueryBundleRequest",
            "query": {
                "sql": f"SELECT content_type, content_id, content_text FROM {table_reference}",
                "isConsistent": True, "limit": 100, "offset": len(rows),
            },
            "partMask": 3,
        })
        token = started["token"]
        (output / f"{table_reference}-page-{page}-started.json").write_text(
            json.dumps(started, indent=2) + "\n"
        )
        for attempt in range(12):
            status, result = request(path + "/get/" + token)
            if status in (200, 201) and "queryResult" in result:
                break
            (output / f"{table_reference}-page-{page}-pending.json").write_text(
                json.dumps(result, indent=2) + "\n"
            )
            if attempt in (0, 5, 11):
                print(json.dumps({"table": table_reference, "poll": attempt,
                                  "status": status,
                                  "job_state": result.get("jobState")}), flush=True)
            time.sleep(1)
        else:
            raise RuntimeError("Public read query did not complete in 12 polls")
        (output / f"{table_reference}-page-{page}.json").write_text(
            json.dumps(result, indent=2, ensure_ascii=False) + "\n"
        )
        batch = result_rows(result)
        rows.extend(batch)
        count = result["queryCount"]
        if len(rows) >= count:
            return rows
        if not batch or page >= 20:
            raise RuntimeError("Public read query pagination did not finish")
        page += 1


def result_rows(result):
    rowset = result["queryResult"]["queryResults"]
    columns = [item["name"] for item in rowset["headers"]]
    return [
        {**dict(zip(columns, row["values"])),
         "row_id": row.get("rowId"), "version": row.get("versionNumber")}
        for row in rowset["rows"]
    ]


def saved_query(folder, table_reference):
    rows = []
    pages = sorted(path for path in folder.iterdir() if re.fullmatch(
        re.escape(table_reference) + r"-page-\d+\.json", path.name
    ))
    if not pages:
        raise ValueError(f"No saved public query pages for {table_reference}")
    for path in pages:
        rows.extend(result_rows(json.loads(path.read_text())))
    return rows


def digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def comparison(expected, actual):
    prefix = 0
    while prefix < min(len(expected), len(actual)) and expected[prefix] == actual[prefix]:
        prefix += 1
    suffix = 0
    while (suffix < min(len(expected), len(actual)) - prefix
           and expected[len(expected) - 1 - suffix] == actual[len(actual) - 1 - suffix]):
        suffix += 1
    old_lines, new_lines = expected.split("\n"), actual.split("\n")
    changes = []
    kinds = Counter()
    deleted = []
    inserted = []
    for tag, old_start, old_stop, new_start, new_stop in SequenceMatcher(
        a=old_lines, b=new_lines, autojunk=False
    ).get_opcodes():
        if tag == "equal":
            continue
        kinds[tag] += 1
        deleted.extend(old_lines[old_start:old_stop])
        inserted.extend(new_lines[new_start:new_stop])
        if len(changes) < 8:
            changes.append({
                "kind": tag, "expected_line_start": old_start + 1,
                "expected_lines": old_stop - old_start,
                "actual_lines": new_stop - new_start,
                "expected_preview": [line[:80] for line in old_lines[old_start:min(old_stop, old_start + 2)]],
                "actual_preview": [line[:80] for line in new_lines[new_start:min(new_stop, new_start + 2)]],
            })
    return {
        "expected_characters": len(expected), "actual_characters": len(actual),
        "expected_sha256": digest(expected), "actual_sha256": digest(actual),
        "exact_match": expected == actual,
        "common_prefix_characters": prefix, "common_suffix_characters": suffix,
        "expected_first_difference": expected[prefix:prefix + 80],
        "actual_first_difference": actual[prefix:prefix + 80],
        "expected_tail": expected[-50:], "actual_tail": actual[-50:],
        "matches_expected_rstrip": actual == expected.rstrip(),
        "matches_expected_strip": actual == expected.strip(),
        "matches_expected_without_final_newlines": actual == expected.rstrip("\r\n"),
        "matches_expected_crlf_normalization": actual == expected.replace("\r\n", "\n"),
        "matches_expected_without_empty_lines": actual == "\n".join(
            line for line in expected.split("\n") if line
        ),
        "matches_expected_without_blank_lines": actual == "\n".join(
            line for line in expected.split("\n") if line.strip()
        ),
        "line_change_kinds": dict(kinds), "changed_line_examples": changes,
        "deleted_line_count": len(deleted), "inserted_line_count": len(inserted),
        "deleted_nonempty_line_count": sum(bool(line) for line in deleted),
        "deleted_nonblank_line_count": sum(bool(line.strip()) for line in deleted),
        "inserted_nonblank_line_count": sum(bool(line.strip()) for line in inserted),
    }


def identity(row):
    return row["content_type"], row["content_id"] or "", row["content_text"] or ""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--raw-dir", type=Path, help="Recompare saved public JSON without any network access")
    parser.add_argument("--expected-commit", default=FAILED_UPLOAD_COMMIT)
    args = parser.parse_args()
    output = args.output_dir.resolve()
    if output == ROOT or ROOT in output.parents:
        parser.error("raw diagnostic outputs must be outside the repository")
    output.mkdir(parents=True, exist_ok=False)
    if not re.fullmatch(r"[0-9a-f]{40}", args.expected_commit):
        parser.error("--expected-commit must be an immutable full commit SHA")
    current = saved_query(args.raw_dir, TABLE) if args.raw_dir else query(TABLE, output)
    previous = saved_query(args.raw_dir, TABLE + ".13") if args.raw_dir else query(TABLE + ".13", output)
    old = Counter(identity(row) for row in previous)
    remaining = old.copy()
    new_rows = []
    for row in current:
        key = identity(row)
        if remaining[key]:
            remaining[key] -= 1
        else:
            new_rows.append(row)
    summary = {
        "table": TABLE, "baseline_snapshot": 13,
        "expected_commit": args.expected_commit,
        "current_count": len(current), "baseline_count": len(previous),
        "baseline_rows_missing_or_changed": sum(remaining.values()),
        "new_row_count": len(new_rows), "comparisons": [],
    }
    for row in new_rows:
        filename = FILES[(row["content_type"], row["content_id"] or "")]
        expected = subprocess.check_output([
            "git", "show", f"{args.expected_commit}:src/html/output/{filename}",
        ], cwd=ROOT).decode("utf-8")
        summary["comparisons"].append({
            "filename": filename, "row_id": row["row_id"], "version": row["version"],
            **comparison(expected, row["content_text"]),
        })
    (output / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
