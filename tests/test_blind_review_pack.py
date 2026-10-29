"""Offline blind-pack causal tests; source texts and scientific gates stay intact."""
from dataclasses import replace
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import socket
import stat
import subprocess

import pytest
import yaml

from data_sheets_schema.evaluation import blind_review_pack as pack


@pytest.fixture(autouse=True)
def offline_only(monkeypatch):
    monkeypatch.setattr(socket.socket, "connect", lambda *a, **k: pytest.fail("network forbidden"))
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: pytest.fail("subprocess forbidden"))


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def selection(tmp_path, count=6, raw=None):
    records = []
    for index in range(count):
        arm = "baseline-generation" if index % 2 else "candidate-generation"
        label = f"secret-selection-{index}"
        path = tmp_path / f"{label}.yaml"
        if raw is None:
            source = (
                f"# Model: claude-opus-5\n# Arm: {arm}\n# Label: {label}\n"
                f"run_label: {label}\nsource_path: {path}\n"
                "generation_metadata:\n  model: opaque-model-identifier\n  provider: test-only\n"
                "id: https://example.org/dataset\nname: A scientific dataset\n"
                "label: A scientific label\n"
                "description: |\n  Scientific words stay intact, including # Model: a source quote.\n"
                "  All 005 participants provided two observations.\n"
                "release_date: 2026-09-07\nversion: '005'\n"
                "resources:\n- id: example:child\n  description: Original member facts.\n"
                "keywords: [health, imaging]\nmissing: null\nconsented: false\n"
            ).encode()
        else:
            source = raw
        path.write_bytes(source)
        records.append(pack.Record(arm, "CHORUS", label, path))
    return records


def files(directory):
    return {path.name: path.read_bytes() for path in directory.iterdir()}


def build(tmp_path, records, *, name="pack", **kwargs):
    output = tmp_path / name
    cohort = kwargs.pop("cohort", "synthetic")
    default_seed = "a1b2c3d4e5f60718293a4b5c6d7e8f90112233445566778899aabbccddeeff00" if cohort == "campaign" else "registered-seed"
    key = pack.build_blind_review_pack(records, output, seed=kwargs.pop("seed", default_seed),
                                      cohort=cohort, **kwargs)
    return output, key


def test_bytes_order_and_metadata_deterministic_with_reordered_selection(tmp_path):
    records = selection(tmp_path)
    before = {r.source_path: r.source_path.read_bytes() for r in records}
    first, key = build(tmp_path, records)
    second, other = build(tmp_path, reversed(records), name="second")
    assert files(first) == files(second)
    assert key == other
    assert key["generated_at"] is None
    assert key["timestamp_basis"] == "omitted_for_reproducibility"
    assert key["scientific_approval"] is False
    assert {r.source_path: r.source_path.read_bytes() for r in records} == before
    third, changed = build(tmp_path, records, name="other-seed", seed="different-seed")
    assert [r["label"] for r in changed["records"]] != [r["label"] for r in key["records"]]
    assert files(first) != files(third)


def test_key_hashes_blinding_review_sheet_and_permissions(tmp_path):
    records = selection(tmp_path)
    output, key = build(tmp_path, records, generated_at="2026-10-20T12:34:56Z")
    assert json.loads((output / "sealed_blind_key.json").read_bytes()) == key
    assert key["generated_at"] == "2026-10-20T12:34:56Z"
    assert key["timestamp_basis"] == "caller_supplied_unverified"
    assert stat.S_IMODE(output.stat().st_mode) == 0o700
    assert stat.S_IMODE((output / "sealed_blind_key.json").stat().st_mode) == 0o600
    assert set(files(output)) == {"sealed_blind_key.json", "review_sheet.tsv"} | {
        f"blind_{i:02d}.yaml" for i in range(1, 7)}
    with (output / "review_sheet.tsv").open(newline="") as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        assert reader.fieldnames == list(pack.REVIEW_COLUMNS)
        rows = list(reader)
    assert len(rows) == 6
    for entry, row in zip(key["records"], rows):
        assert row["blind_id"] == entry["blind_id"]
        assert row["project"] == entry["project"]
        assert all(row[column] == "" for column in pack.REVIEW_COLUMNS[2:])
        blinded = (output / (entry["blind_id"] + ".yaml")).read_bytes()
        assert sha(blinded) == entry["blinded_sha256"]
        assert sha(Path(entry["source_path"]).read_bytes()) == entry["source_sha256"]
        assert "claude-opus-5" not in blinded.decode()
        assert "opaque-model-identifier" not in blinded.decode()
        for original in records:
            assert all(token not in blinded.decode() for token in
                       (original.arm, original.label, str(original.source_path)))
        doc = yaml.safe_load(blinded)
        assert doc["description"] == (
            "Scientific words stay intact, including # Model: a source quote.\n"
            "All 005 participants provided two observations.\n")
        assert doc["label"] == "A scientific label"
        assert doc["release_date"] == "2026-09-07"
        assert doc["version"] == "005"
        assert doc["keywords"] == ["health", "imaging"]
        assert doc["consented"] is False
        assert doc["missing"] is None
        assert doc["resources"][0]["description"] == "Original member facts."


def test_seed_integer_matches_cli_string_and_timestamp_changes_only_key(tmp_path):
    records = selection(tmp_path)
    first, _ = build(tmp_path, records, seed=42)
    second, _ = build(tmp_path, records, name="second", seed="42",
                      generated_at="2026-10-20T00:00:00Z")
    assert {k: v for k, v in files(first).items() if k != "sealed_blind_key.json"} == {
        k: v for k, v in files(second).items() if k != "sealed_blind_key.json"}


def campaign(tmp_path):
    records = []
    concat_dir = tmp_path / "data" / "d4d_concatenated"
    for arm in pack.ARMS:
        for project in pack.PROJECTS:
            for replicate in (1, 2, 3):
                prefix = "04f" if project in {"CHORUS", "VOICE"} else "04g"
                label = (f"2026-09-{prefix}_claude-opus-5-api-generic-v8_rep{replicate}"
                         if arm == "v8" else f"registered-final-{project}-{replicate}")
                full_dir = concat_dir / "claudecode_api" / label
                core_dir = concat_dir / "claudecode_api_core" / label
                full_dir.mkdir(parents=True, exist_ok=True)
                core_dir.mkdir(parents=True, exist_ok=True)
                path = full_dir / f"{project}_d4d.yaml"
                raw = f"# Label: {label}\nid: example:{project}:rep{replicate}\nname: Scientific record\n".encode("utf-8")
                path.write_bytes(raw)
                prov_path = core_dir / f"{project}_provenance.yaml"
                prov_path.write_text(
                    yaml.safe_dump({
                        "run": {
                            "project": project,
                            "label": label,
                            "condition": "generic_v8" if arm == "v8" else "generic_v10",
                        },
                        "validation": {
                            "artifacts": {
                                "full": {"path": str(path), "sha256": sha(raw)},
                            },
                        },
                    }),
                    encoding="utf-8",
                )
                records.append(pack.Record(arm, project, label, path))
    return records


def test_campaign_exact_24_cohort_and_correct_v8_fill(tmp_path):
    records = campaign(tmp_path)
    output, key = build(tmp_path, records, cohort="campaign")
    assert len(key["records"]) == 24
    assert (output / "blind_24.yaml").is_file()
    assert key["cohort"] == "campaign"
    assert len({(r["arm"], r["project"], r["label"]) for r in key["records"]}) == 24


@pytest.mark.parametrize("change", ["missing", "extra", "duplicate", "wrong-arm", "wrong-project",
                                   "wrong-v8-fill", "wrong-v8-replicate"])
def test_campaign_refuses_wrong_cohort(tmp_path, change):
    records = campaign(tmp_path)
    if change == "missing":
        records.pop()
    elif change == "extra":
        records.append(replace(records[0], label="new-label"))
    elif change == "duplicate":
        records[1] = records[0]
    elif change == "wrong-arm":
        records[0] = replace(records[0], arm="v7")
    elif change == "wrong-project":
        records[0] = replace(records[0], project="OTHER")
    elif change == "wrong-v8-fill":
        records[0] = replace(records[0], label=records[0].label.replace("04f", "04g"))
    else:
        records[0] = replace(records[0], label=records[0].label.replace("_rep1", "_rep4"))
    with pytest.raises(ValueError):
        build(tmp_path, records, cohort="campaign")
    assert not (tmp_path / "pack").exists()


@pytest.mark.parametrize("kind", ["label", "arm", "path", "uppercase", "escaped", "cross-record",
                                  "metadata-model", "header-model", "model-spelling"])
def test_leakage_in_scientific_text_refuses_without_redaction(tmp_path, kind):
    records = selection(tmp_path, count=2)
    first, second = records
    token = {
        "label": first.label, "arm": first.arm, "path": str(first.source_path),
        "uppercase": first.label.upper(), "escaped": first.label,
        "cross-record": second.label, "metadata-model": "opaque-model-identifier",
        "header-model": "claude-opus-5", "model-spelling": "gpt-4o",
    }[kind]
    addition = f"\ndescription: {json.dumps(token)}\n"
    if kind == "escaped":
        addition = '\ndescription: "' + "".join(f"\\u{ord(char):04x}" for char in token) + '"\n'
    original = first.source_path.read_text().replace("description: |", "original_description: |") + addition
    first.source_path.write_text(original)
    with pytest.raises(ValueError, match="identity|model identifier"):
        build(tmp_path, records)
    assert first.source_path.read_text() == original
    assert not (tmp_path / "pack").exists()
    assert not list(tmp_path.glob(".blind-review-pack-*"))


def test_review_sheet_leakage_rejected_even_when_yaml_is_clean(tmp_path):
    records = selection(tmp_path, count=1, raw=b"id: example:test\n")
    records[0] = replace(records[0], arm="CHORUS")
    with pytest.raises(ValueError, match="identity"):
        build(tmp_path, records)


@pytest.mark.parametrize("raw", [
    b"id: x\nprovenance:\n  description: Scientific lineage must not be deleted.\n",
    b"id: x\nmodel: arbitrary-model\n",
    b"id: x\nresources:\n- id: y\n  generation_metadata:\n    model: arbitrary-model\n",
    b"id: x\nresources:\n- id: y\n  model: arbitrary-model\n",
    b"id: x\nresources:\n- id: y\n  source_path: scientific-relative-file.csv\n",
    b"id: x\narm: unexpected-arm\n",
])
def test_ambiguous_or_nested_metadata_is_refused_not_silently_erased(tmp_path, raw):
    records = selection(tmp_path, 1, raw)
    with pytest.raises(ValueError, match="explicit blinding review"):
        build(tmp_path, records)
    assert records[0].source_path.read_bytes() == raw


def test_exact_root_and_wrapper_metadata_stripped_scientific_fields_kept(tmp_path):
    records = selection(tmp_path, 1, b"id: unused\n")
    record = records[0]
    document = {
        "generation_metadata": {"model": "outer-secret"},
        "Dataset": {
            "id": "example:scientific", "label": record.label, "arm": record.arm,
            "generator_model": "inner-secret",
            "provenance": {"record_type": "d4d_generation_provenance",
                           "run": {"label": record.label}, "model": "provenance-secret"},
            "description": "Do not change the citation, version, processing or source facts.",
            "version": "2.1", "processing": ["raw", "filtered"],
        },
    }
    record.source_path.write_text(yaml.safe_dump(document))
    output, _ = build(tmp_path, records)
    actual = yaml.safe_load((output / "blind_01.yaml").read_bytes())
    assert actual == {"Dataset": {"id": "example:scientific", "description": document["Dataset"]["description"],
                                  "version": "2.1", "processing": ["raw", "filtered"]}}


@pytest.mark.parametrize("raw", [
    b"id: first\nid: second\n",
    b"id: x\nvalue: .nan\n",
    b"id: x\nvalue: .inf\n",
    b"&root {id: x, recursive: *root}\n",
    b"id: x\nvalue: !!binary aGVsbG8=\n",
    b"id: x\n1: integer mapping key\n",
    b"- list\n- is not a record\n",
    b"Dataset: {id: x}\nother: scientific but invalid wrapper\n",
])
def test_strict_source_parser_refuses_lossy_or_invalid_inputs(tmp_path, raw):
    records = selection(tmp_path, 1, raw)
    with pytest.raises(ValueError):
        build(tmp_path, records)


def test_finite_aliases_are_preserved_as_values(tmp_path):
    raw = b"id: example:test\nkeywords: &items [health, imaging]\nother_keywords: *items\n"
    records = selection(tmp_path, 1, raw)
    output, _ = build(tmp_path, records)
    assert yaml.safe_load((output / "blind_01.yaml").read_bytes()) == yaml.safe_load(raw)


@pytest.mark.parametrize("envelope", [
    "generation_metadata:\n  invocations:\n  - model: opaque-generator\n",
    "generation_metadata:\n  model: [opaque-generator]\n",
    "generator_model: [opaque-generator]\n",
])
def test_model_identifiers_inside_metadata_lists_still_block_later_leaks(tmp_path, envelope):
    raw = (envelope + "id: example:test\ndescription: opaque-generator\n").encode()
    with pytest.raises(ValueError, match="identity"):
        build(tmp_path, selection(tmp_path, 1, raw))


@pytest.mark.parametrize("prefix", ["---\n", "\ufeff---\n"])
def test_header_metadata_after_yaml_marker_remains_part_of_leakage_gate(tmp_path, prefix):
    raw = (prefix + "# Model: opaque-generator\nid: example:test\ndescription: opaque-generator\n").encode()
    with pytest.raises(ValueError, match="identity"):
        build(tmp_path, selection(tmp_path, 1, raw))


@pytest.mark.parametrize("prefix", [
    "id: example:test\n",
    "id: example:test\ndescription: |\n  Prior scientific text.\n",
    "id: example:test\nname: Scientific café\n",
])
def test_late_metadata_comments_still_identify_opaque_model_leaks(tmp_path, prefix):
    raw = (prefix + "# Model: opaque-generator\nother_text: opaque-generator\n").encode()
    records = selection(tmp_path, 1, raw)
    with pytest.raises(ValueError, match="identity"):
        build(tmp_path, records)
    assert records[0].source_path.read_bytes() == raw
    assert not (tmp_path / "pack").exists()


@pytest.mark.parametrize("scalar", [
    "|\n  Scientific quote:\n  # Model: opaque-source-phrase\n",
    '"Scientific quote:\n# Model: opaque-source-phrase\n"\n',
    "'Scientific quote:\n# Model: opaque-source-phrase\n'\n",
])
def test_metadata_like_text_inside_scientific_scalars_is_preserved(tmp_path, scalar):
    raw = ("id: example:test\ndescription: " + scalar).encode()
    output, _ = build(tmp_path, selection(tmp_path, 1, raw))
    assert yaml.safe_load((output / "blind_01.yaml").read_bytes()) == yaml.safe_load(raw)


@pytest.mark.parametrize("kind", ["same-path", "symlink", "hardlink"])
def test_alias_sources_cannot_count_as_distinct_records(tmp_path, kind):
    records = selection(tmp_path, 2)
    first, second = records
    if kind == "same-path":
        records[1] = replace(second, source_path=first.source_path)
    else:
        second.source_path.unlink()
        if kind == "symlink":
            second.source_path.symlink_to(first.source_path)
        else:
            os.link(first.source_path, second.source_path)
    with pytest.raises(ValueError, match="duplicate source"):
        build(tmp_path, records)


def test_equal_bytes_distinct_files_are_allowed_and_hashes_remain_visible(tmp_path):
    records = selection(tmp_path, 2, b"id: example:same\n")
    _, key = build(tmp_path, records)
    assert key["records"][0]["source_sha256"] == key["records"][1]["source_sha256"]
    assert key["records"][0]["source_path"] != key["records"][1]["source_path"]


@pytest.mark.parametrize("extension", ["json", "yaml"])
def test_manifest_paths_are_relative_and_pins_checked(tmp_path, extension):
    source_dir = tmp_path / "inputs"
    source_dir.mkdir()
    records = selection(source_dir, 1)
    record = records[0]
    manifest = source_dir / ("selection." + extension)
    document = {"records": [dict(arm=record.arm, project=record.project, label=record.label,
                                 source_path=record.source_path.name,
                                 source_sha256=sha(record.source_path.read_bytes()))]}
    manifest.write_text(json.dumps(document) if extension == "json" else yaml.safe_dump(document))
    selected = pack.read_manifest(manifest)
    assert selected[0].source_path == record.source_path
    build(tmp_path, selected)
    wrong = replace(selected[0], source_sha256="0" * 64)
    with pytest.raises(ValueError, match="source_sha256"):
        build(tmp_path, [wrong], name="wrong-pin")


@pytest.mark.parametrize("raw", [
    '{"records": [], "records": []}', '{"records": [], "unknown": true}',
    '{"records": [{"arm": "a", "project": "p", "label": "l", "source_path": 42}]}',
    '{"records": [{"arm": "a", "project": "p", "label": "l", "source_path": NaN}]}',
    '{"records": [{"arm": "a", "project": "p", "label": "l", "source_path": "x", "extra": 1}]}',
    '{"records": [{"arm": "a", "project": "p", "label": "l", "source_path": "x", "source_sha256": 2}]}',
    '{"records": null}', '[]', 'records: []',
])
def test_strict_json_manifest(tmp_path, raw):
    path = tmp_path / "selection.json"
    path.write_text(raw)
    with pytest.raises(ValueError):
        pack.read_manifest(path)


@pytest.mark.parametrize("raw", [
    "records: []\nrecords: []\n", "records: .inf\n", "records: &list [*list]\n",
    "records:\n- {arm: x, project: x, label: x, source_path: x, source_sha256: false}\n",
])
def test_strict_yaml_manifest(tmp_path, raw):
    path = tmp_path / "selection.yaml"
    path.write_text(raw)
    with pytest.raises(ValueError):
        pack.read_manifest(path)


@pytest.mark.parametrize("existing", ["empty-directory", "file", "dangling-symlink"])
def test_output_is_never_overwritten(tmp_path, existing):
    records = selection(tmp_path, 1)
    output = tmp_path / "pack"
    if existing == "empty-directory":
        output.mkdir()
    elif existing == "file":
        output.write_bytes(b"preserve me")
    else:
        output.symlink_to(tmp_path / "missing")
    with pytest.raises(ValueError, match="already exists"):
        build(tmp_path, records)
    assert output.is_symlink() if existing == "dangling-symlink" else output.exists()


def test_atomic_publish_refuses_concurrent_destination_without_replacing_it(tmp_path, monkeypatch):
    records = selection(tmp_path, 1)
    real = pack._rename_new

    def race(source, destination):
        destination.mkdir()
        (destination / "other-owner").write_text("keep")
        return real(source, destination)

    monkeypatch.setattr(pack, "_rename_new", race)
    with pytest.raises(OSError):
        build(tmp_path, records)
    assert files(tmp_path / "pack") == {"other-owner": b"keep"}
    assert not list(tmp_path.glob(".blind-review-pack-*"))


def test_write_failure_leaves_no_partial_output(tmp_path, monkeypatch):
    records = selection(tmp_path, 1)
    real = pack._write

    def fail(path, raw):
        real(path, raw)
        raise OSError("simulated disk failure")

    monkeypatch.setattr(pack, "_write", fail)
    with pytest.raises(OSError, match="disk failure"):
        build(tmp_path, records)
    assert not (tmp_path / "pack").exists()
    assert not list(tmp_path.glob(".blind-review-pack-*"))


def test_postwrite_gate_detects_tamper_and_source_change(tmp_path, monkeypatch):
    records = selection(tmp_path, 1)
    real = pack._write

    def tamper(path, raw):
        real(path, raw)
        if path.suffix == ".yaml":
            path.write_bytes(raw + b"\n# unexpected injected header\n")

    monkeypatch.setattr(pack, "_write", tamper)
    with pytest.raises(ValueError, match="written review package"):
        build(tmp_path, records)
    assert not (tmp_path / "pack").exists()

    def mutate_source(path, raw):
        real(path, raw)
        records[0].source_path.write_text("id: changed-source\n")

    monkeypatch.setattr(pack, "_write", mutate_source)
    with pytest.raises(ValueError, match="source changed"):
        build(tmp_path, records)
    assert not (tmp_path / "pack").exists()


@pytest.mark.parametrize("seed", ["", True, None, [], "newline\nseed"])
def test_invalid_seed_refused(tmp_path, seed):
    with pytest.raises(ValueError, match="seed"):
        build(tmp_path, selection(tmp_path, 1), seed=seed)


@pytest.mark.parametrize("timestamp", ["now", "2026-10-20", "2026-10-20T01:00:00+00:00",
                                      "2026-02-30T00:00:00Z"])
def test_timestamp_never_inferred_or_malformed(tmp_path, timestamp):
    with pytest.raises(ValueError):
        build(tmp_path, selection(tmp_path, 1), generated_at=timestamp)


def test_nonregular_source_and_bounded_pack(tmp_path, monkeypatch):
    records = selection(tmp_path, 1)
    records[0].source_path.unlink()
    records[0].source_path.mkdir()
    with pytest.raises((ValueError, OSError)):
        build(tmp_path, records)
    records[0].source_path.rmdir()
    records[0].source_path.write_bytes(b"id: x\n")
    monkeypatch.setattr(pack, "MAX_PACK_BYTES", 1)
    with pytest.raises(ValueError, match="size bound"):
        build(tmp_path, records)


def test_cli_record_selection_and_manifest_exclusive(tmp_path, capsys):
    records = selection(tmp_path, 1)
    record = records[0]
    entry = f"{record.arm}:{record.project}:{record.label}={record.source_path}"
    assert pack.parse_record(entry) == record
    assert pack.main(["--record", entry, "--seed", "42", "--cohort", "synthetic",
                      "--output-dir", str(tmp_path / "pack")]) == 0
    assert "never the sealed key" in capsys.readouterr().out
    with pytest.raises(SystemExit) as exc:
        pack.main(["--record", entry, "--manifest", "elsewhere", "--seed", "42",
                   "--output-dir", str(tmp_path / "other")])
    assert exc.value.code == 2
    with pytest.raises(ValueError):
        pack.parse_record("not-a-record")


def test_cli_missing_seed_and_default_campaign_refusal(tmp_path):
    record = selection(tmp_path, 1)[0]
    entry = f"{record.arm}:{record.project}:{record.label}={record.source_path}"
    for arguments in ([], ["--seed", "explicit"]):
        with pytest.raises(SystemExit) as exc:
            pack.main(["--record", entry, "--output-dir", str(tmp_path / "pack"), *arguments])
        assert exc.value.code == 2
    assert not (tmp_path / "pack").exists()


def test_campaign_seed_minimum_length_and_cli_default_seed(tmp_path):
    records = campaign(tmp_path)
    for bad_seed in (
        "short-seed",
        "00000000000000000000000000000007",
        "a" * 64,
        "2026-10-25-v10-campaign-seed-0001",
        "registered-seed-0123456789abcdef0123456789",
    ):
        with pytest.raises(ValueError, match="64-character hex seed with at least 8 distinct hex digits"):
            build(tmp_path, records, cohort="campaign", seed=bad_seed, name=f"pack_{bad_seed[:8]}")

    record = selection(tmp_path, 1)[0]
    entry = f"{record.arm}:{record.project}:{record.label}={record.source_path}"
    out_dir = tmp_path / "cli_auto_seed"
    assert pack.main(["--record", entry, "--cohort", "synthetic", "--output-dir", str(out_dir)]) == 0
    key = json.loads((out_dir / "sealed_blind_key.json").read_text(encoding="utf-8"))
    assert len(key["seed"]) == 64


def test_campaign_v10_label_and_sibling_provenance_validation(tmp_path):
    records = campaign(tmp_path)
    # Bad v10 label
    bad_label = list(records)
    v10_idx = next(i for i, r in enumerate(bad_label) if r.arm == "v10")
    bad_label[v10_idx] = replace(bad_label[v10_idx], label="unregistered-custom-label")
    with pytest.raises(ValueError, match="requires a v10 or registered-final label"):
        build(tmp_path, bad_label, cohort="campaign", name="pack_bad_label")

    # Swapping two replicates' full files on the corpus layout (claudecode_api vs claudecode_api_core) is refused (R4 F5)
    swapped = list(records)
    r1_idx = next(i for i, r in enumerate(swapped) if r.arm == "v8" and r.project == "AI_READI" and r.label.endswith("rep1"))
    r2_idx = next(i for i, r in enumerate(swapped) if r.arm == "v8" and r.project == "AI_READI" and r.label.endswith("rep2"))
    swapped[r1_idx] = replace(swapped[r1_idx], source_path=records[r2_idx].source_path)
    swapped[r2_idx] = replace(swapped[r2_idx], source_path=records[r1_idx].source_path)
    with pytest.raises(ValueError, match="do not match sibling provenance"):
        build(tmp_path, swapped, cohort="campaign", name="pack_swapped_reps")

    # Missing provenance in campaign mode is refused (R4 F5)
    v10_rec = records[v10_idx]
    core_prov = (
        v10_rec.source_path.parent.parent.parent
        / "claudecode_api_core"
        / v10_rec.label
        / f"{v10_rec.project}_provenance.yaml"
    )
    saved_prov = core_prov.read_bytes()
    core_prov.unlink()
    with pytest.raises(ValueError, match="has no provenance record"):
        build(tmp_path, records, cohort="campaign", name="pack_missing_prov")
    core_prov.write_bytes(saved_prov)

    # Provenance with mismatched full hash refuses
    core_prov.write_text(
        yaml.safe_dump({
            "run": {"project": v10_rec.project, "label": v10_rec.label, "condition": "generic_v10"},
            "validation": {"artifacts": {"full": {"sha256": "0" * 64}}},
        }),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="do not match sibling provenance"):
        build(tmp_path, records, cohort="campaign", name="pack_bad_prov")


def test_short_arm_minimum_length_and_word_boundary_leakage(tmp_path):
    path = tmp_path / "rec.yaml"
    path.write_text("id: example:test\ndescription: Architectural armv8a instruction set.\n", encoding="utf-8")
    with pytest.raises(ValueError, match="at least 2 non-whitespace characters"):
        pack.Record("v", "CHORUS", "secret-label-01", path)

    # 2-char arm "v8" does not false-positive on substring inside "armv8a"
    rec = pack.Record("v8", "CHORUS", "secret-label-01", path)
    build(tmp_path, [rec], name="pack_v8_ok")

    # Standalone "v8" word in scientific text is still caught
    path.write_text("id: example:test\ndescription: Generated under v8 condition.\n", encoding="utf-8")
    with pytest.raises(ValueError, match="identity"):
        build(tmp_path, [pack.Record("v8", "CHORUS", "secret-label-01", path)], name="pack_v8_leak")

