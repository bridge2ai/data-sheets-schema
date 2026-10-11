#!/usr/bin/env python3
"""Export revised fig09 against historical generic-v8 rep 1 (#2915, #4385).

Inputs and output directory are explicit. Published historical figures and run
labels are never opened for writing. The generated comparator is historical;
this figure makes no claim about current generation quality or scientific truth.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from data_sheets_schema.crate_generation_comparison import (  # noqa: E402
    EMPTY, OVERLAP, STATUSES, compare_records, generated_v8_rep1, parse_report,
    source_evidence_rows,
)
from data_sheets_schema import figure_publication  # noqa: E402

PROJECTS = ("AI_READI", "CHORUS", "CM4AI", "VOICE")
STEM = "fig09_crate_vs_generation"
# Reuse the held figure set's palette values, not its output-writing helper.
COLORS = ("#256abf", "#1baf7a", "#86b6ef", "#eda100", "#e34948", "#898781", "#4a3aa7")
INK = "#0b0b0b"
SURFACE = "#fcfcfb"


PATH_BASES = {
    "repository_root": "Resolve this relative path from the repository root, including after relocation.",
    "external_absolute": "Absolute acquisition path outside the repository; relocation is not implied.",
}


def _locator(repo: Path, path: Path) -> dict[str, str]:
    """Describe an already-resolved acquisition path without changing its bytes."""
    try:
        return {"path": path.relative_to(repo).as_posix(), "path_base": "repository_root"}
    except ValueError:
        return {"path": str(path), "path_base": "external_absolute"}


def prepare(repo: Path, packages: Path, static_records: Path, manifest: Path) -> dict:
    """Read each input once, retain exact hashes, and reconcile report/sidecar."""
    repo = repo.resolve()
    captured = {}

    def read(path: Path) -> bytes:
        path = path.resolve()
        if path not in captured:
            captured[path] = path.read_bytes()
        return captured[path]

    generated = generated_v8_rep1(json.loads(read(manifest)))
    panels, overlaps, observations = [], [], []
    for project in PROJECTS:
        if project not in generated:
            raise ValueError(f"historical manifest has no {project} comparator")
        gen_path = (repo / generated[project]).resolve()
        gen_locator = _locator(repo, gen_path)
        full = yaml.safe_load(read(gen_path))
        mapped = (static_records / f"{project}_d4d.yaml").resolve()
        if not mapped.exists():
            panels.append({"project": project, "status": "no published static-map record",
                           "generated_record": gen_locator["path"],
                           "generated_record_path_base": gen_locator["path_base"], "outcome": {},
                           "loss": {}, "maptype": {}, "overlap": {}})
            continue
        processed = packages / project / "processed"
        report = parse_report(read(processed / f"{project}_crate_mapping_provenance.md").decode("utf-8"))
        sidecar = json.loads(read(processed / f"{project}_crate_mapping_sources.json"))
        if sidecar.get("project") != project:
            raise ValueError(f"source sidecar project differs for {project}")
        rows = source_evidence_rows(sidecar)
        if len(rows) != report["original_rows"]:
            raise ValueError(f"source sidecar row count differs for {project}")
        statuses = Counter(row["mapping_status"] for row in rows)
        statuses["filled"] += report["root_identifier_rows"]
        if any(statuses[status] != report["outcome"].get(status, 0)
               for status in set(statuses) | set(report["outcome"])):
            raise ValueError(f"source sidecar outcomes differ for {project}")
        for label in ("mapping_table", "schema"):
            binding = sidecar[label]
            bound = repo / binding["path"]
            if hashlib.sha256(read(bound)).hexdigest() != binding["sha256"]:
                raise ValueError(f"source sidecar {label} hash differs for {project}")
        source_path = repo / sidecar["source"]["path"]
        if source_path.is_file():
            source_raw = read(source_path)
        elif project == "CM4AI":
            archive = packages / project / "raw/cm4ai_release_metadata.zip"
            with zipfile.ZipFile(io.BytesIO(read(archive))) as handle:
                member = "cm4ai_release_metadata/ro-crate-metadata.json"
                members = [entry for entry in handle.infolist() if entry.filename == member]
                if len(members) != 1 or members[0].file_size > 16 * 1024 * 1024:
                    raise ValueError("invalid CM4AI metadata member")
                with handle.open(members[0]) as stream:
                    source_raw = stream.read(16 * 1024 * 1024 + 1)
                if len(source_raw) != members[0].file_size:
                    raise ValueError("CM4AI metadata member length differs")
        else:
            raise ValueError(f"source evidence is unavailable for {project}")
        if hashlib.sha256(source_raw).hexdigest() != sidecar["source"]["sha256"]:
            raise ValueError(f"source sidecar raw-source hash differs for {project}")
        producer = sidecar.get("producer", {}).get("files_sha256", {})
        expected_producer = {f"src/data_sheets_schema/{name}.py" for name in
                             ("rocrate_map", "rocrate_sources", "rocrate_assertions", "scope", "schema_view")}
        if set(producer) != expected_producer or any(
                hashlib.sha256(read(repo / name)).hexdigest() != expected
                for name, expected in producer.items()):
            raise ValueError(f"source sidecar producer code differs for {project}")
        table_rows = list(csv.DictReader(io.StringIO(read(repo / sidecar["mapping_table"]["path"]).decode("utf-8")), delimiter="\t"))
        report_rows = [row for row in report["fields"] if row["source_path"] != "crate root identifier/@id"]
        if len(table_rows) != len(rows):
            raise ValueError(f"mapping table row count differs for {project}")
        for declared, evidence in zip(table_rows, sidecar["rows"], strict=True):
            if (declared["Rule_ID"] != evidence["rule_id"]
                    or declared["D4D_Full_Path"] != evidence["d4d_path"]
                    or declared["Execution"] != evidence["execution"]
                    or declared["RO_Crate_JSON_Path"] != evidence["source_expression"]):
                raise ValueError(f"per-rule mapping evidence differs for {project}")
        # Markdown is sorted for readers; sidecar order follows stable table IDs.
        # A multiset join retains duplicate declarations without using position.
        reported = Counter((row["d4d_path"], row["status"], row["source_path"])
                           for row in report_rows)
        observed = Counter((row["d4d_path"], row["status"], row["source_expression"] or "—")
                           for row in sidecar["rows"])
        if reported != observed:
            raise ValueError(f"per-rule mapping report differs for {project}")
        crate = yaml.safe_load(read(mapped))
        working_raw = read(processed / f"{project}_crate_mapped_d4d.yaml")
        if hashlib.sha256(working_raw).hexdigest() != sidecar["record_sha256"]:
            raise ValueError(f"source sidecar record hash differs for {project}")
        working = yaml.safe_load(working_raw)
        if crate != working:
            raise ValueError(f"published and reported working records differ for {project}")
        actual_slots = sum(value not in EMPTY for value in crate.values())
        if report["distinct_slots"] != actual_slots:
            raise ValueError(f"reported slot count differs for {project}")
        counts, detail = compare_records(project, crate, full)
        panels.append({"project": project, "status": "mapped", **report,
                       "overlap": counts, "generated_record": gen_locator["path"],
                       "generated_record_path_base": gen_locator["path_base"],
                       "static_record": _locator(repo, mapped)["path"],
                       "static_record_path_base": _locator(repo, mapped)["path_base"],
                       "source_observation_counts": dict(Counter(row["source_evidence"] for row in rows))})
        overlaps.extend(detail)
        observations.extend(rows)
    for path in (Path(__file__), ROOT / "src/data_sheets_schema/crate_generation_comparison.py",
                 ROOT / "src/data_sheets_schema/scope.py",
                 ROOT / "src/data_sheets_schema/rocrate_map.py",
                 ROOT / "src/data_sheets_schema/rocrate_sources.py",
                 ROOT / "src/data_sheets_schema/rocrate_assertions.py",
                 ROOT / "src/data_sheets_schema/schema_view.py",
                 ROOT / "src/data_sheets_schema/figure_publication.py"):
        read(path)
    return {"repository_root": repo, "projects": panels, "overlap_slots": overlaps,
            "source_observations": observations, "captured": captured}


def _csv_bytes(rows: list[dict]) -> bytes:
    if not rows:
        raise ValueError("cannot publish an empty figure table")
    keys = list(dict.fromkeys(key for row in rows for key in row))
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=keys)
    writer.writeheader()
    for row in rows:
        writer.writerow({key: json.dumps(value, ensure_ascii=False, sort_keys=True)
                         if isinstance(value, (list, dict)) else value
                         for key, value in row.items()})
    return output.getvalue().encode("utf-8")


def render(prepared: dict, output: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9,
                         "text.color": INK, "figure.facecolor": SURFACE,
                         "axes.facecolor": SURFACE, "svg.fonttype": "none"})
    figure, axes = plt.subplots(3, 1, figsize=(12, 11), constrained_layout=True)
    projects = prepared["projects"]
    positions = range(len(projects))
    names = [row["project"].replace("_", "-") for row in projects]
    for ax in axes:
        ax.spines[["top", "right"]].set_visible(False)
        ax.set_yticks(list(positions), names)
        ax.invert_yaxis()
        ax.set_axisbelow(True)
        ax.grid(axis="x", color="#e1e0d9", linewidth=0.6)

    left = [0] * len(projects)
    for status, color in zip(STATUSES, COLORS):
        values = [row["outcome"].get(status, 0) for row in projects]
        axes[0].barh(list(positions), values, left=left, color=color,
                     label="empty (valid path, no crate value)" if status == "empty" else status)
        left = [a + b for a, b in zip(left, values)]
    for i, row in enumerate(projects):
        if row["status"] == "mapped":
            text = (f"{row['original_rows']} declared; {row['active_rows']} active; "
                    f"{row['root_identifier_rows']} root ID; {row['distinct_slots']} slots")
        else:
            text = row["status"]
        axes[0].text(left[i] + 1, i, text, va="center", fontsize=8)
    axes[0].set_title("A  Mapping dispositions: original rows retained, root identifier counted separately", loc="left")
    axes[0].set_xlabel("report entries (retiring a rule does not increase source coverage)")
    axes[0].legend(ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.22), fontsize=8)
    axes[0].set_xlim(0, max(left, default=0) * 1.65 + 1)

    # Each bar independently partitions the same filled-report-entry denominator.
    # Preserve explicit additional labels accepted by the report parser as well.
    mapping_colors = {"exactMatch": "#256abf", "closeMatch": "#1baf7a",
                      "relatedMatch": "#eda100", "narrowMatch": "#4a3aa7", "—": "#898781"}
    mapping_types = list(mapping_colors) + sorted(
        {label for row in projects for label in row["maptype"]} - set(mapping_colors))
    type_positions = [i - 0.2 for i in positions]
    loss_positions = [i + 0.2 for i in positions]
    left = [0] * len(projects)
    for mapping_type in mapping_types:
        values = [row["maptype"].get(mapping_type, 0) for row in projects]
        label = "unassessed" if mapping_type == "—" else mapping_type
        axes[1].barh(type_positions, values, left=left, height=0.34,
                     color=mapping_colors.get(mapping_type, "#636363"), label=f"type: {label}")
        left = [a + b for a, b in zip(left, values)]
    left = [0] * len(projects)
    for loss, color in zip(("none", "minimal", "moderate", "high", "—"),
                           ("#86b6ef", "#3987e5", "#1c5cab", "#0d366b", "#898781")):
        values = [row["loss"].get(loss, 0) for row in projects]
        label = "unassessed" if loss == "—" else loss
        axes[1].barh(loss_positions, values, left=left, height=0.34, color=color,
                     label=f"loss: {label}")
        left = [a + b for a, b in zip(left, values)]
    axes[1].set_yticks([y for pair in zip(type_positions, loss_positions) for y in pair],
                      [f"{name} · {dimension}" for name in names for dimension in ("type", "loss")])
    axes[1].set_title("B  Filled entries by table-declared mapping type and information loss", loc="left")
    axes[1].set_xlabel("filled report entries (same denominator in both bars)\n"
                       "copied text alone does not establish exactMatch or loss=none")
    axes[1].legend(ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.32), fontsize=8)

    left = [0] * len(projects)
    labels = ("both: serialized/DOI agreement", "both: scalar difference",
              "both: nested serialization difference", "static record only", "generated record only")
    for status, label, color in zip(OVERLAP, labels, COLORS):
        values = [row["overlap"].get(status, 0) for row in projects]
        axes[2].barh(list(positions), values, left=left, color=color, label=label)
        left = [a + b for a, b in zip(left, values)]
    axes[2].set_title("C  Record overlap with historical generic-v8 rep 1 (API arm)", loc="left")
    axes[2].set_xlabel("populated top-level slots; generated-only does not mean source-absent")
    axes[2].legend(ncol=2, loc="upper center", bbox_to_anchor=(0.5, -0.22), fontsize=8)
    figure.suptitle("Revised deterministic mapping and a fixed historical generation comparator\n"
                     "Source evidence is reported separately by original row; no current-generation quality claim", fontsize=12)
    figure.savefig(output / f"{STEM}.svg", format="svg")
    figure.savefig(output / f"{STEM}.png", dpi=180)
    plt.close(figure)


def publish(prepared: dict, output: Path, code_commit: str) -> dict:
    """Write a fresh derived artifact; never replace an existing export."""
    inputs = prepared["captured"]

    def verify_inputs():
        for path, raw in inputs.items():
            if path.read_bytes() != raw:
                raise ValueError(f"figure input changed: {path}")

    verify_inputs()
    output.mkdir(parents=True, exist_ok=False)
    panels = []
    for row in prepared["projects"]:
        missing = row["status"] != "mapped"
        panels.append({"project": row["project"], "status": row["status"],
                       "original_rows": row.get("original_rows"), "active_rows": row.get("active_rows"),
                       "root_identifier_rows": row.get("root_identifier_rows"),
                       "distinct_slots": row.get("distinct_slots"),
                       **{f"outcome_{key}": None if missing else row["outcome"].get(key, 0) for key in STATUSES},
                       **{f"loss_{'unassessed' if key == '—' else key}": None if missing else row["loss"].get(key, 0) for key in ("none", "minimal", "moderate", "high", "—")},
                       **{f"maptype_{key}": value for key, value in row["maptype"].items()},
                       **{f"overlap_{key}": None if missing else row["overlap"].get(key, 0) for key in OVERLAP},
                       "generated_record": row["generated_record"],
                       "generated_record_path_base": row["generated_record_path_base"]})
    for suffix, rows in (("", panels), ("_overlap_slots", prepared["overlap_slots"]),
                         ("_source_observations", prepared["source_observations"])):
        (output / f"{STEM}{suffix}.csv").write_bytes(_csv_bytes(rows))
    render(prepared, output)
    note = ("This is a revision of fig09 using the explicitly selected new static-map label.\n"
            "The comparator remains historical generic-v8 rep 1, not a current-generation run.\n"
            "DOI and ID comparisons recognize DOI spellings; other values use normalized YAML.\n"
            "Nested differences are serialization differences, not scientific disagreements.\n"
            "The source_observations CSV retains every original row, raw source values and entity pointers.\n"
            "Root presence, member-only presence, empty properties and checked-source absence are distinct.\n"
            "Panel A empty means a valid mapped path has no value in the crate, not source-wide absence.\n"
            "Panel B shows mapping type and loss as separate partitions of the same filled report entries.\n"
            "These are table declarations, not independent fidelity assessments; copied text alone establishes\n"
            "neither exactMatch nor loss=none, and does not establish round-trip losslessness.\n"
            "A retired/deferred row can repeat evidence placed elsewhere; this is not unique-source coverage.\n"
            "generated_only is strictly record-slot overlap and does not establish source absence.\n"
            "VOICE's differing release DOIs remain different identities. No human scientific review is implied.\n"
            "Paths tagged repository_root resolve from the relocated repository root.\n"
            "Paths tagged external_absolute record outside acquisitions and are not portable repository references.\n")
    (output / "README.txt").write_text(note, encoding="utf-8")
    verify_inputs()
    artifacts = {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                 for path in sorted(output.iterdir()) if path.is_file()}
    manifest = {"state": "complete", "format_version": 2, "code_commit": code_commit,
                "path_bases": dict(PATH_BASES),
                "historical_generated_comparator": "generic-v8 rep 1, API arm",
                "inputs": [{**_locator(prepared["repository_root"], path),
                            "sha256": hashlib.sha256(raw).hexdigest()}
                           for path, raw in inputs.items()], "artifacts": artifacts,
                "scientific_scoring": False}
    def verify():
        verify_inputs()
        for name, digest in artifacts.items():
            if hashlib.sha256((output / name).read_bytes()).hexdigest() != digest:
                raise ValueError(f"figure output changed: {name}")

    raw_manifest = (json.dumps(manifest, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    directory = os.open(output, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    committed = False
    try:
        figure_publication.complete(directory, "manifest.json", raw_manifest, verify)
        committed = True
    finally:
        figure_publication.close_descriptor(directory, committed=committed)
    return manifest


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packages-dir", type=Path, required=True)
    parser.add_argument("--static-records-dir", type=Path, required=True,
                        help="Explicit newly published static-map label directory")
    parser.add_argument("--generated-manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True, help="Fresh derived-artifact directory")
    parser.add_argument("--code-commit", required=True, help="Expected committed producer/figure code HEAD")
    args = parser.parse_args(argv)
    actual = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if actual != args.code_commit:
        parser.error("code commit does not match current HEAD")
    code_paths = [str(Path(__file__).resolve().relative_to(ROOT)),
                  "src/data_sheets_schema/crate_generation_comparison.py",
                  "src/data_sheets_schema/rocrate_map.py",
                  "src/data_sheets_schema/rocrate_sources.py",
                  "src/data_sheets_schema/rocrate_assertions.py",
                  "src/data_sheets_schema/schema_view.py",
                  "src/data_sheets_schema/scope.py",
                  "src/data_sheets_schema/figure_publication.py"]
    subprocess.check_output(["git", "ls-files", "--error-unmatch", "--", *code_paths], cwd=ROOT)
    subprocess.run(["git", "diff", "--quiet", "HEAD", "--", *code_paths], cwd=ROOT, check=True)
    prepared = prepare(ROOT, args.packages_dir, args.static_records_dir, args.generated_manifest)
    publish(prepared, args.output_dir, actual)
    print(json.dumps({"state": "complete", "output_dir": str(args.output_dir), "code_commit": actual}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
