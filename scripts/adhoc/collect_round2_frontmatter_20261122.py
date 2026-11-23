"""Retain real round-two startup evidence for PR 6302, 2026-11-22.

Inputs: the seven completed CHORUS diagnostic traces listed below, read-only.
Output: round2_frontmatter.json with exact base64 files and physical frames.
Only the standard library is used; no native binary, network or project imports.
Run with --check to verify the pack and original files without writing.
"""

import argparse
import base64
import hashlib
import json
from pathlib import Path
import stat


REPOSITORY = Path(__file__).resolve().parents[2]
SOURCE = REPOSITORY.parent / (
    "scratch-diagnostic-stop-traces-20261121-round2-personal-plan-03/"
    "run/CHORUS-seven"
)
OUTPUT = REPOSITORY / "tests/fixtures/native_permission_2_1_325/round2_frontmatter.json"
TRACES = (
    "settled", "stop-source_write", "stop-sealed_request_write",
    "stop-helper_owned_write", "stop-outside_response_write",
    "stop-future_response_write", "stop-stale_response_write",
)
FILES = (
    "transcript.jsonl", "control.jsonl", "launch.before.json",
    "evidence_root/projection.json", "stdout.unprocessed",
)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def read_regular(path):
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise ValueError("expected a single-link regular input: " + str(path))
    return path.read_bytes()


def identity(raw):
    return {"decoded_bytes": len(raw), "decoded_sha256": digest(raw)}


def encoded(raw):
    return {**identity(raw), "encoding": "base64",
        "raw_base64": base64.b64encode(raw).decode("ascii")}


def objects(raw, label):
    lines = raw.splitlines(keepends=True)
    if not lines or any(not line.endswith(b"\n") for line in lines):
        raise ValueError("JSONL requires complete physical lines: " + label)
    parsed = [json.loads(line) for line in lines]
    if any(type(value) is not dict for value in parsed):
        raise ValueError("JSONL includes a non-object: " + label)
    return lines, parsed


def one_index(rows, predicate, label):
    indices = [index for index, row in enumerate(rows) if predicate(row)]
    if len(indices) != 1:
        raise ValueError("expected one " + label)
    return indices[0]


def trace_record(name, captured):
    directory = SOURCE / name
    raw_files = {}
    files = {}
    for relative in FILES:
        path = directory / relative
        raw = read_regular(path)
        captured[str(path)] = raw
        raw_files[relative] = raw
        files[relative] = {"original_path": str(path), **encoded(raw)}
    if raw_files["stdout.unprocessed"] != b"":
        raise ValueError("unprocessed stdout is not empty: " + name)
    transcript_lines, transcript = objects(raw_files["transcript.jsonl"], name)
    control_lines, control = objects(raw_files["control.jsonl"], name)
    ui = [index for index, row in enumerate(transcript)
        if (isinstance(row.get("subtype"), str) and row["subtype"].startswith("ui_"))
        or (isinstance(row.get("event"), str) and row["event"].startswith("ui."))]
    if ui:
        raise ValueError("unexpected UI frame in round-two transcript: " + name)
    if (transcript[0].get("type") != "control_response"
            or transcript[0].get("response", {}).get("subtype") != "success"
            or transcript[1].get("type") != "system"
            or transcript[1].get("subtype") != "init"):
        raise ValueError("round-two startup is not exact ack then init: " + name)
    initialize_sent = one_index(control, lambda row: row.get("kind") == "initialize_sent",
        "initialize_sent control row")
    initialize_ack = one_index(control, lambda row: row.get("kind") == "initialize_ack",
        "initialize_ack control row")
    if control[initialize_ack]["frame"] != transcript[0]:
        raise ValueError("initialize acknowledgement does not join its transcript")
    calls = []
    for index, row in enumerate(transcript):
        if row.get("type") == "assistant":
            for block in row.get("message", {}).get("content", []):
                if type(block) is dict and block.get("type") == "tool_use":
                    calls.append((index, block))
    if not calls:
        raise ValueError("round-two trace lacks a tool call: " + name)
    first_call, first_block = calls[0]
    first_callback = one_index(transcript,
        lambda row: row.get("type") == "control_request"
        and row.get("request", {}).get("tool_use_id") == first_block["id"],
        "first matching callback")
    decisions = [index for index, row in enumerate(control)
        if row.get("kind") == "decision" and row.get("request") == transcript[first_callback]]
    if len(decisions) > 1:
        raise ValueError("duplicate first matching callback decision")
    if not 1 < first_call < first_callback:
        raise ValueError("round-two first tool order differs")
    call_names = {block["id"]: block["name"] for _, block in calls}
    failed_bash = []
    for index, row in enumerate(transcript):
        if row.get("type") == "user":
            for block in row.get("message", {}).get("content", []):
                if (type(block) is dict and block.get("type") == "tool_result"
                        and block.get("is_error") is True
                        and call_names.get(block.get("tool_use_id")) == "Bash"):
                    failed_bash.append({"physical_line": index + 1,
                        "tool_use_id": block["tool_use_id"]})
    if name == "settled" and not failed_bash:
        raise ValueError("settled historical helper failure is absent")
    launch = json.loads(raw_files["launch.before.json"])
    projection = json.loads(raw_files["evidence_root/projection.json"])
    if (launch["executable"]["init_version"] != transcript[1]["claude_code_version"]
            or launch["cwd"] != transcript[1]["cwd"]
            or type(projection["probe_policy"]) is not dict):
        raise ValueError("launch, init or retained probe policy identity differs")

    def frame(relative, index):
        lines = transcript_lines if relative == "transcript.jsonl" else control_lines
        return {"source_file": relative, "source_path": str(directory / relative),
            "source_sha256": files[relative]["decoded_sha256"],
            "physical_line": index + 1, **encoded(lines[index])}

    frames = {
        "ack": frame("transcript.jsonl", 0),
        "init": frame("transcript.jsonl", 1),
        "initialize_sent": frame("control.jsonl", initialize_sent),
        "initialize_ack": frame("control.jsonl", initialize_ack),
        "first_tool_call": frame("transcript.jsonl", first_call),
        "first_callback": frame("transcript.jsonl", first_callback),
        "first_callback_decision": (frame("control.jsonl", decisions[0]) if decisions else None),
        "first_failed_bash_result": (frame("transcript.jsonl", failed_bash[0]["physical_line"] - 1)
            if failed_bash else None),
    }
    return {
        "qualification_expected": "refuse",
        "qualification_basis": "Historical failed helper or prescribed stop; wire recognition does not establish production qualification.",
        "files": files, "frames": frames,
        "transcript_physical_line_count": len(transcript_lines),
        "control_physical_line_count": len(control_lines),
        "ui_frame_count": 0, "stdout_unprocessed_bytes": 0,
        "failed_bash_results": failed_bash,
        "metadata_sources": {
            "executable": "launch.before.json:executable",
            "working_directory": "launch.before.json:cwd",
            "model": "transcript.jsonl:physical_line_2.model",
            "policy": "evidence_root/projection.json:probe_policy",
        },
    }


def collect():
    captured = {}
    traces = {name: trace_record(name, captured) for name in TRACES}
    before = {path: identity(raw) for path, raw in sorted(captured.items())}
    after = {}
    for path, raw in sorted(captured.items()):
        reread = read_regular(Path(path))
        after[path] = identity(reread)
        if reread != raw:
            raise ValueError("original input changed during collection: " + path)
    script_raw = Path(__file__).read_bytes()
    if bytes([64]) in script_raw:
        raise ValueError("collector contains a forbidden literal character")
    pack = {
        "kind": "round2_native_frontmatter", "version": 1,
        "interpretation": "Lossless retained diagnostic evidence; no normalization, new execution, production success or authorization claim.",
        "source_root": str(SOURCE), "traces": traces,
        "source_before": before, "source_after": after, "source_unchanged": before == after,
        "collector": {"path": "scripts/adhoc/collect_round2_frontmatter_20261122.py",
            "sha256": digest(script_raw), "original_files_checked_unchanged": len(captured)},
    }
    result = (json.dumps(pack, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False)
        + "\n").encode()
    if bytes([64]) in result:
        raise ValueError("fixture contains a forbidden literal character")
    return result, traces


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    raw, traces = collect()
    if args.check:
        if read_regular(OUTPUT) != raw:
            raise ValueError("existing fixture differs from retained original bytes")
    else:
        with OUTPUT.open("xb") as stream:
            stream.write(raw)
        if read_regular(OUTPUT) != raw:
            raise ValueError("fixture readback differs")
    print(json.dumps({"fixture": str(OUTPUT), **identity(raw),
        "mode": "checked" if args.check else "created",
        "original_files_checked_unchanged": len(TRACES) * len(FILES),
        "transcripts": {name: {"sha256": value["files"]["transcript.jsonl"]["decoded_sha256"],
            "bytes": value["files"]["transcript.jsonl"]["decoded_bytes"],
            "physical_lines": value["transcript_physical_line_count"],
            "failed_bash_results": len(value["failed_bash_results"]), "ui_frame_count": 0}
            for name, value in traces.items()}}, sort_keys=True))


if __name__ == "__main__":
    main()
