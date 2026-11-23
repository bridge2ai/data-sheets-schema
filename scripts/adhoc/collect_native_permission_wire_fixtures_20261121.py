"""Collect lossless permission wire fixtures for PR 6302, 2026-11-21.

Inputs: reviewed strict-profile companion and retained r4/round-1 files.
Output: tests/fixtures/native_permission_2_1_325/retained.json, base64 only.
No project imports, native process, provider, network, or source-file writes.
Run with --check to verify the existing pack without writing any files.
Run with --update to add records while preserving every existing decoded input.
"""

import argparse
import base64
import hashlib
import json
from pathlib import Path
import stat


REPOSITORY = Path(__file__).resolve().parents[2]
EXECUTIONS = REPOSITORY.parent
COMPANION = EXECUTIONS / (
    "codex-development-efficiency-20261111/notes/development_efficiency_20261111/"
    "handoffs/codex196-strict-profile-v2-template-20261121.json"
)
COMPANION_SHA256 = "3cc4badc14f30c968f501cb860c00515691e8ec0de7f2c5cdd21f62fb484094a"
OUTPUT = REPOSITORY / "tests/fixtures/native_permission_2_1_325/retained.json"
R4 = EXECUTIONS / (
    "native-fastpath-724f6b349bae-r4/probe-evidence/CHORUS-cell01-u4b-02/permission"
)
ROUND1 = EXECUTIONS / "scratch-diagnostic-stop-traces-20261121-plan-06/run/traces"
TRACES = (
    ("r4/settled", R4 / "settled"),
    ("r4/stop-future_response_write", R4 / "stop-future_response_write"),
    ("r4/stop-sealed_request_write", R4 / "stop-sealed_request_write"),
    ("round1_plan06/settled", ROUND1 / "settled"),
    ("round1_plan06/stop-source_write", ROUND1 / "stop-source_write"),
    ("round1_plan06/stop-sealed_request_write", ROUND1 / "stop-sealed_request_write"),
    ("round1_plan06/stop-helper_owned_write", ROUND1 / "stop-helper_owned_write"),
)
REQUIRED_FILES = ("transcript.jsonl", "control.jsonl", "launch.before.json")
OPTIONAL_FILES = (
    "completed/launch.json", "completed/neutral.before.json", "completed/neutral.after.json",
    "completed/outcome.json", "completed/effect-stop.json", "completed/parent-stop.json",
    "evidence_root/neutral.before.json", "evidence_root/projection.json", "cleanup.json",
)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    # Match the reviewed companion generator's digest convention, including LF.
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=False, allow_nan=False) + "\n").encode()


def read_regular(path):
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise ValueError("input must be a single-link regular file: " + str(path))
    return path.read_bytes()


def collect():
    originals = {}

    def capture(path):
        raw = read_regular(path)
        key = str(path)
        if key in originals and originals[key] != raw:
            raise ValueError("input changed during collection: " + key)
        originals[key] = raw
        return {
            "original_path": key,
            "encoding": "base64",
            "decoded_bytes": len(raw),
            "decoded_sha256": digest(raw),
            "raw_base64": base64.b64encode(raw).decode("ascii"),
        }

    companion_record = capture(COMPANION)
    if companion_record["decoded_sha256"] != COMPANION_SHA256:
        raise ValueError("reviewed companion pin differs")
    companion = json.loads(originals[str(COMPANION)])
    if digest(canonical(companion["template"])) != companion["template_sha256"]:
        raise ValueError("reviewed literal template digest differs")
    traces = {}
    for name, directory in TRACES:
        files = {filename: capture(directory / filename) for filename in REQUIRED_FILES}
        absent = []
        for filename in OPTIONAL_FILES:
            path = directory / filename
            if path.exists() or path.is_symlink():
                files[filename] = capture(path)
            else:
                absent.append(filename)
        traces[name] = {
            "qualification_expected": "refuse",
            "reason": "Historical launch lacks the required exact directory grant; wire recognition alone is insufficient.",
            "files": files,
            "absent_optional_files": absent,
        }
    for source in companion["sources"]:
        raw = originals[source["path"]]
        if len(raw) != source["bytes"] or digest(raw) != source["sha256"]:
            raise ValueError("reviewed transcript identity differs")
    for launch in companion["retained_launches"]:
        raw = originals[launch["path"]]
        if len(raw) != launch["bytes"] or digest(raw) != launch["sha256"]:
            raise ValueError("reviewed launch identity differs")
    reviewed_frames = 0
    for group in companion["wire_frames"].values():
        for record in group.values():
            raw = base64.b64decode(record["raw_base64"], validate=True)
            source = originals[record["source_path"]]
            lines = source.splitlines(keepends=True)
            if (record["encoding"] != "base64"
                    or len(raw) != record["decoded_bytes_including_newline"]
                    or digest(raw) != record["decoded_sha256_including_newline"]
                    or digest(source) != record["source_transcript_sha256"]
                    or raw != lines[record["physical_line"] - 1]
                    or digest(canonical(json.loads(raw))) != record["canonical_parsed_frame_sha256"]):
                raise ValueError("reviewed physical frame differs")
            reviewed_frames += 1
    if reviewed_frames != 20:
        raise ValueError("reviewed frame roster differs")
    for path, raw in originals.items():
        if read_regular(Path(path)) != raw:
            raise ValueError("original evidence changed during collection: " + path)
    script_raw = Path(__file__).read_bytes()
    if bytes([64]) in script_raw:
        raise ValueError("collector contains forbidden literal character")
    pack = {
        "kind": "retained_native_permission_wire_fixtures",
        "version": 1,
        "profile": companion["profile"],
        "interpretation": "Lossless wire fixtures and historical qualification failures; no granted success, execution authorization, or observation authenticity claim.",
        "reviewed_companion": companion_record,
        "reviewed_frame_count": reviewed_frames,
        "traces": traces,
        "collector": {
            "path": "scripts/adhoc/collect_native_permission_wire_fixtures_20261121.py",
            "sha256": digest(script_raw),
            "original_files_checked_unchanged": len(originals),
        },
    }
    encoded = (json.dumps(pack, sort_keys=True, indent=2, ensure_ascii=True) + "\n").encode()
    if bytes([64]) in encoded:
        raise ValueError("fixture JSON contains forbidden literal character")
    return encoded, len(originals), reviewed_frames


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--update", action="store_true")
    args = parser.parse_args()
    encoded, original_count, frame_count = collect()
    if args.check:
        if read_regular(OUTPUT) != encoded:
            raise ValueError("existing fixture pack differs from retained originals")
    elif args.update:
        previous = json.loads(read_regular(OUTPUT))
        updated = json.loads(encoded)
        if previous["reviewed_companion"] != updated["reviewed_companion"]:
            raise ValueError("fixture update would replace reviewed companion bytes")
        for trace, record in previous["traces"].items():
            for name, artifact in record["files"].items():
                if artifact != updated["traces"][trace]["files"].get(name):
                    raise ValueError("fixture update would replace retained artifact bytes")
        OUTPUT.write_bytes(encoded)
        if read_regular(OUTPUT) != encoded:
            raise ValueError("updated fixture pack readback differs")
    else:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        with OUTPUT.open("xb") as stream:
            stream.write(encoded)
        if read_regular(OUTPUT) != encoded:
            raise ValueError("fixture pack readback differs")
    print(json.dumps({"fixture": str(OUTPUT), "bytes": len(encoded), "sha256": digest(encoded),
        "original_files_checked_unchanged": original_count, "reviewed_frames": frame_count,
        "mode": "checked" if args.check else "updated" if args.update else "created"}, sort_keys=True))


if __name__ == "__main__":
    main()
