"""Fig09 displays two complete declared partitions without changing publication data."""
import copy
import csv
import hashlib
import io
from pathlib import Path
import xml.etree.ElementTree as ET

import pytest

from data_sheets_schema.crate_generation_comparison import parse_report
from scripts.figures import fig09_mapping_revision as figure
from tests.test_crate_generation_comparison import prepared_inputs  # noqa: F401


def _declared_report(header):
    # Thirteen filled entries, including one separately counted root ID.
    # Two copied narratives are explicitly unassessed in both dimensions.
    filled = [
        ("Dataset.id", "exactMatch", "none", "crate root identifier/@id", "doi:10.1234/neutral"),
        ("Dataset.title", "exactMatch", "none", "name", "Neutral record"),
        ("Dataset.a", "closeMatch", "minimal", "a", "a"),
        ("Dataset.b", "closeMatch", "minimal", "b", "b"),
        ("Dataset.c", "closeMatch", "minimal", "c", "c"),
        ("Dataset.d", "relatedMatch", "moderate", "d", "d"),
        ("Dataset.e", "relatedMatch", "moderate", "e", "e"),
        ("Dataset.f", "relatedMatch", "high", "f", "f"),
        ("Dataset.g", "relatedMatch", "none", "g", "g"),
        ("Dataset.h", "narrowMatch", "none", "h", "h"),
        ("Dataset.i", "futureDeclaredRelation", "none", "i", "i"),
        ("Dataset.j", "—", "—", "j", "Copied narrative"),
        ("Dataset.k", "—", "—", "k", "Copied narrative"),
    ]
    text = f"""- Mapping table: `mapping.tsv` ({header})
- Executable table rules: 16; retired: 1; deferred: 1; original table rows: 18
- Distinct top-level `Dataset` slots filled: 13 (from 13 filled rows)
## Outcome
| Status | Rows | Meaning |
|---|---|---|
| filled | 13 | placed |
| subsumed | 2 | already placed by a host row |
| empty | 2 | path valid but the crate has no value there |
| unresolvable | 0 | no path |
| unplaceable | 0 | no destination |
| retired | 1 | retained for accounting |
| deferred | 1 | not executable |
## Fidelity of what was filled
| Mapping type | Filled fields |
|---|---|
| exactMatch | 2 |
| closeMatch | 3 |
| relatedMatch | 4 |
| narrowMatch | 1 |
| futureDeclaredRelation | 1 |
| (unstated) | 2 |
| Information loss | Filled fields |
|---|---|
| none | 5 |
| minimal | 3 |
| moderate | 2 |
| high | 1 |
| (unstated) | 2 |
## Per-field detail
| D4D path | Status | Mapping | Loss | Source path | Value / note |
|---|---|---|---|---|---|
"""
    text += "".join(f"| {path} | filled | {mapping} | {loss} | {source} | {value} |\n"
                    for path, mapping, loss, source, value in filled)
    text += """| Other.a | subsumed | closeMatch | minimal | a | same value |
| Other.b | subsumed | relatedMatch | moderate | b | same value |
| Dataset.l | empty | exactMatch | none | l | absent |
| Dataset.m | empty | exactMatch | none | m | absent |
| Old.n | retired | exactMatch | none | n | inactive historical declaration |
| Old.o | deferred | exactMatch | none | o | inactive historical declaration |
"""
    return text


def _partition(ax, prefix):
    return {container.get_label()[len(prefix):]: list(container.patches)
            for container in ax.containers if container.get_label().startswith(prefix)}


def _assert_one_complete_stack(partition, project_index, total):
    intervals = sorted((patches[project_index].get_x(),
                        patches[project_index].get_x() + patches[project_index].get_width())
                       for patches in partition.values() if patches[project_index].get_width())
    assert intervals[0][0] == 0
    assert intervals[-1][1] == total
    assert all(end == start for (_, end), (start, _) in zip(intervals, intervals[1:]))


@pytest.mark.parametrize("header", [
    "18 table rows declared, plus the record's `id`, taken from the crate root",
    "18 original table rows; 16 active rows, plus the record's `id`",
])
def test_render_draws_independent_complete_filled_partitions(tmp_path, monkeypatch, header):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    report = parse_report(_declared_report(header))
    assert (report["original_rows"], report["active_rows"],
            report["root_identifier_rows"], report["outcome"]["subsumed"]) == (18, 16, 1, 2)
    prepared = {"projects": [
        {"project": "UNPUBLISHED", "status": "no published static-map record",
         "outcome": {}, "loss": {}, "maptype": {}, "overlap": {}},
        {"project": "NEUTRAL", "status": "mapped", **report, "overlap": {}},
    ]}
    before = copy.deepcopy(prepared)
    actual = []
    subplots = plt.subplots

    def retain_actual_axes(*args, **kwargs):
        result = subplots(*args, **kwargs)
        actual.append(result)
        return result

    monkeypatch.setattr(plt, "subplots", retain_actual_axes)
    figure.render(prepared, tmp_path)
    assert prepared == before
    assert len(actual) == 1
    _, axes = actual[0]
    mapping = _partition(axes[1], "type: ")
    loss = _partition(axes[1], "loss: ")
    assert {name: [p.get_width() for p in bars] for name, bars in mapping.items()} == {
        "exactMatch": [0, 2], "closeMatch": [0, 3], "relatedMatch": [0, 4],
        "narrowMatch": [0, 1], "futureDeclaredRelation": [0, 1], "unassessed": [0, 2],
    }
    assert {name: [p.get_width() for p in bars] for name, bars in loss.items()} == {
        "none": [0, 5], "minimal": [0, 3], "moderate": [0, 2], "high": [0, 1],
        "unassessed": [0, 2],
    }
    _assert_one_complete_stack(mapping, 1, 13)
    _assert_one_complete_stack(loss, 1, 13)
    type_y = {p[1].get_y() + p[1].get_height() / 2 for p in mapping.values()}
    loss_y = {p[1].get_y() + p[1].get_height() / 2 for p in loss.values()}
    assert len(type_y) == len(loss_y) == 1 and type_y != loss_y
    assert sum(p[1].get_width() for p in mapping.values()) == report["outcome"]["filled"]
    assert "empty (valid path, no crate value)" in axes[0].get_legend_handles_labels()[1]
    assert "retiring a rule does not increase source coverage" in axes[0].get_xlabel()
    assert "table-declared mapping type and information loss" in axes[1].get_title(loc="left")
    assert "copied text alone does not establish exactMatch or loss=none" in axes[1].get_xlabel()
    assert "generated-only does not mean source-absent" in axes[2].get_xlabel()
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    canvas = FigureCanvasAgg(actual[0][0])
    canvas.draw()
    renderer = canvas.get_renderer()
    label_bottom = axes[1].xaxis.label.get_window_extent(renderer).y0
    legend_top = axes[1].get_legend().get_window_extent(renderer).y1
    assert label_bottom > legend_top
    svg = (tmp_path / "fig09_crate_vs_generation.svg").read_bytes()
    assert ET.fromstring(svg).tag.endswith("svg")
    assert b"futureDeclaredRelation" in svg and b"unassessed" in svg
    assert (tmp_path / "fig09_crate_vs_generation.png").read_bytes().startswith(b"\x89PNG\r\n\x1a\n")


def test_publication_keeps_csv_and_pins_and_refuses_historical_output(
        prepared_inputs, tmp_path):
    module, packages, static, manifest_path, _ = prepared_inputs
    prepared = module.prepare(tmp_path, packages, static, manifest_path)
    inputs_before = {path: raw for path, raw in prepared["captured"].items()}
    output = tmp_path / "fresh-figure"
    completed = module.publish(prepared, output, "f" * 40)
    # Existing values and columns are retained; #4918 adds explicit portable locator scope.
    columns = [
        "project", "status", "original_rows", "active_rows", "root_identifier_rows", "distinct_slots",
        "outcome_filled", "outcome_subsumed", "outcome_empty", "outcome_unresolvable",
        "outcome_unplaceable", "outcome_retired", "outcome_deferred", "loss_none", "loss_minimal",
        "loss_moderate", "loss_high", "loss_unassessed", "maptype_exactMatch", "overlap_both_agree",
        "overlap_both_differ_scalar", "overlap_both_differ_nested", "overlap_crate_only",
        "overlap_generated_only", "generated_record", "generated_record_path_base",
    ]
    values = ["P", "mapped", 3, 2, 1, 2, 2, 0, 1, 0, 0, 1, 0, 2, 0, 0, 0, 0,
              2, 2, 0, 0, 0, 0, "historical.yaml", "repository_root"]
    expected = io.StringIO(newline="")
    csv.writer(expected).writerows([columns, values])
    assert (output / "fig09_crate_vs_generation.csv").read_bytes() == expected.getvalue().encode()
    observed = list(csv.DictReader(io.StringIO(
        (output / "fig09_crate_vs_generation_source_observations.csv").read_text())))
    assert [(row["rule_id"], row["mapping_status"]) for row in observed] == [
        ("r1", "filled"), ("r2", "retired"), ("r3", "empty")]
    assert len(observed) == 3  # No inactive source-evidence row disappears.
    assert completed["scientific_scoring"] is False
    assert completed["historical_generated_comparator"] == "generic-v8 rep 1, API arm"
    assert completed["format_version"] == 2
    assert set(completed["path_bases"]) == {"repository_root", "external_absolute"}
    resolved_inputs = {
        (tmp_path / row["path"] if row["path_base"] == "repository_root" else Path(row["path"])):
        row["sha256"] for row in completed["inputs"]}
    assert resolved_inputs == {path: hashlib.sha256(raw).hexdigest()
                               for path, raw in inputs_before.items()}
    assert all(path.read_bytes() == raw for path, raw in inputs_before.items())
    assert all(hashlib.sha256((output / name).read_bytes()).hexdigest() == digest
               for name, digest in completed["artifacts"].items())
    readme = (output / "README.txt").read_text()
    assert "valid mapped path has no value in the crate, not source-wide absence" in readme
    assert "same filled report entries" in readme
    assert "not independent fidelity assessments" in readme
    assert "does not establish round-trip losslessness" in readme
    saved = {path.name: path.read_bytes() for path in output.iterdir()}
    with pytest.raises(FileExistsError):
        module.publish(prepared, output, "f" * 40)
    assert {path.name: path.read_bytes() for path in output.iterdir()} == saved
    historical = tmp_path / "historical-figure"
    historical.mkdir()
    (historical / "manifest.json").write_bytes(b'{"historical": true}\n')
    (historical / "fig09_crate_vs_generation.svg").write_bytes(b"historical figure bytes\n")
    old = {path.name: path.read_bytes() for path in historical.iterdir()}
    with pytest.raises(FileExistsError):
        module.publish(prepared, historical, "f" * 40)
    assert {path.name: path.read_bytes() for path in historical.iterdir()} == old
