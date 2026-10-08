"""The committed crate-mapper outputs validate against today's schema (#2916).

`data/ro-crate_packages/*/processed/` holds the working outputs of the two
deterministic mappers: `d4d rocrate map` (`*_crate_mapped_d4d.yaml`) and
`d4d rocrate normalize` (`*_crate_d4d.yaml`). #646 anchored the `doi` pattern
and nothing re-validated them, so five reports went on saying PASS over
records the schema rejected. They are not provenance records — no
`<method>_core` record pins their verdict, so `runs.validation_status` calls
them UNVERIFIED and `recheck-validation` never visits them — which leaves this
as the check that fails when a schema change makes them invalid.

The published arm directories (`rocrate_static_map/2026-07-27_ourmap-v{1,2}`,
`rocrate_mapped/2026-07-24_deterministic-v1`) are deliberately not walked:
they keep the verdicts they were published with (#426/#520).
"""

import re
import json
import hashlib
import zipfile
from collections import Counter
import tempfile
import unittest
from pathlib import Path

import pytest
import yaml

from data_sheets_schema.rocrate_map import (
    FULL_SCHEMA, MAPPING_TSV, PACKAGES_DIR, UNPLACED_KINDS, build_placement,
    load_mapping, map_crate, validate, write_provenance,
)
from data_sheets_schema.schema_view import shared_view

ROOT = Path(__file__).resolve().parents[2]
PACKAGES = ROOT / PACKAGES_DIR

#: The five records committed when this guard was written. More may follow
#: (AI_READI once its crate maps); fewer means the glob stopped seeing them.
KNOWN = {
    "CHORUS_crate_mapped_d4d.yaml", "CM4AI_crate_mapped_d4d.yaml",
    "VOICE_crate_mapped_d4d.yaml", "CHORUS_crate_d4d.yaml", "CM4AI_crate_d4d.yaml",
}

#: A verdict line and the basis #2916 writes beside it.
VERDICT_LINE = re.compile(r"^- (?:Validation|`[^`]+_crate_d4d\.yaml`): \*\*")
BASIS = re.compile(r"\*\*(?:PASS|FAIL)\*\* — schema \S+ / sha256 [0-9a-f]{64} "
                   r"/ \d{4}-\d{2}-\d{2} \(`[^`]+`\)$")

#: How the cell of a nested row refused only because its merge is undecided
#: ends, as `map_crate` writes it (#2915, #3270). Matched at the end of the
#: cell, not anywhere in the row, since a declared reason may use the same
#: words (#4413).
UNDECIDED_MERGE_END = "into one object is not decided (#2915, #3270) |"


def committed_records(packages: Path = PACKAGES) -> list[Path]:
    return sorted([*packages.glob("*/processed/*_crate_mapped_d4d.yaml"),
                   *packages.glob("*/processed/*_crate_d4d.yaml")])


def rejected(paths: list[Path]) -> list[tuple[str, str]]:
    """(path, verdict) for every record the current merged schema rejects,
    judged by the mappers' own `validate`, so the guard and the verdict the
    reports record are one instrument."""
    out = []
    for path in paths:
        verdict = validate(path)
        if verdict != "PASS":
            out.append((str(path), verdict))
    return out


@pytest.mark.corpus   # reads the committed mapper outputs under data/ (#1203)
class TestCommittedMapperOutputs(unittest.TestCase):
    def test_every_committed_record_passes_the_current_schema(self):
        records = committed_records()
        self.assertLessEqual(KNOWN, {p.name for p in records})
        self.assertEqual([], rejected(records))

    def test_the_guard_fails_a_record_with_the_resolver_url_restored(self):
        """The pre-#2916 form of a committed record: the same bytes with the
        crate's resolver URL back in `doi`."""
        source = PACKAGES / "CHORUS" / "processed" / "CHORUS_crate_mapped_d4d.yaml"
        text = source.read_text(encoding="utf-8")
        self.assertIn("\ndoi: 10.18130/V3/XNBOPG\n", text)
        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / source.name
            copy.write_text(text.replace("\ndoi: 10.18130/V3/XNBOPG\n",
                                         "\ndoi: https://doi.org/10.18130/V3/XNBOPG\n"),
                            encoding="utf-8")
            found = rejected([copy])
        self.assertEqual(1, len(found))
        self.assertIn("in /doi", found[0][1])

    def test_every_committed_verdict_names_the_schema_it_was_reached_against(self):
        lines = []
        for report in sorted([*PACKAGES.glob("*/processed/*_crate_mapping_provenance.md"),
                              *PACKAGES.glob("*/processed/*_crate_changes.md")]):
            for line in report.read_text(encoding="utf-8").splitlines():
                if VERDICT_LINE.match(line):
                    lines.append((report.name, line))
        # One per mapped record and one per normalized record.
        self.assertGreaterEqual(len(lines), len(KNOWN))
        self.assertEqual([], [(name, line) for name, line in lines
                              if not BASIS.search(line)])

    def test_every_filled_row_is_in_the_record_it_reports_on(self):
        """#2915. A nested row replaced the value a `Dataset` row had placed
        while the report still listed that row filled; a report's filled
        `Dataset.<slot>` rows name slots its record carries, and its slot
        count is the record's."""
        placement = build_placement(shared_view(FULL_SCHEMA))
        reports = sorted(PACKAGES.glob("*/processed/*_crate_mapping_provenance.md"))
        self.assertTrue(reports)
        for report in reports:
            with self.subTest(report=report.name):
                text = report.read_text(encoding="utf-8")
                mapped = report.with_name(report.name.replace(
                    "_crate_mapping_provenance.md", "_crate_mapped_d4d.yaml"))
                record = yaml.safe_load(mapped.read_text(encoding="utf-8"))
                filled = re.findall(r"^\| Dataset\.(\w+) \| filled \|", text, re.M)
                self.assertEqual([], [s for s in filled if s not in record])
                # and no nested row is also filled into a host a Dataset row
                # filled: that pair is the overwrite
                nested = re.findall(r"^\| (\w+)\.\w+ \| filled \|", text, re.M)
                hosts = {placement.get(cls) for cls in nested if cls != "Dataset"}
                self.assertEqual(set(), hosts & set(filled))
                m = re.search(r"^- Distinct top-level `Dataset` slots filled: (\d+) ",
                              text, re.M)
                self.assertIsNotNone(m)
                self.assertEqual(int(m.group(1)), len(record))

    def test_every_unplaceable_row_reported_is_one_the_table_declares(self):
        """#2915. A report's rows that place nowhere are the rows the current
        table declares unplaced, each ending in the kind and the reason the
        table declares, and the Outcome legend counts them by kind. A report
        left behind by a table edit to either column fails here, a kind
        flipped with the reason kept among them (#4413). A nested row whose
        merge is undecided does place, so it is not among them (#3270)."""
        declared = {row["D4D_Full_Path"].strip(): (row["Unplaced"].strip(),
                                                   row["Unplaced_Reason"].strip())
                    for row in load_mapping(ROOT / MAPPING_TSV)
                    if row.get("Execution", "active") == "active"
                    and (row.get("Unplaced") or "").strip()}
        reports = sorted(PACKAGES.glob("*/processed/*_crate_mapping_provenance.md"))
        self.assertTrue(reports)
        for report in reports:
            with self.subTest(report=report.name):
                text = report.read_text(encoding="utf-8")
                placed_nowhere = placed_nowhere_rows(text)
                self.assertEqual(set(declared), set(placed_nowhere))
                # The whole declaration, to the end of the cell, so a reason
                # the table shortened is not found inside the longer one.
                self.assertEqual([], [
                    path for path, rest in placed_nowhere.items()
                    if not rest.endswith(declaration_cell(*declared[path]))])
                legend = re.findall(r"^\| unplaceable \| \d+ \| .*$", text, re.M)
                self.assertEqual(1, len(legend))
                if declared:
                    self.assertTrue(legend[0].endswith(legend_tail(declared)), legend[0])
                else:
                    self.assertNotIn("the mapping table says why", legend[0])

    def test_every_original_rule_has_the_current_execution_outcome(self):
        """Retirement is visible and stays in the same 136-row denominator;
        inactive rows retain their current reason rather than an old fill."""
        rows = load_mapping(ROOT / MAPPING_TSV)
        self.assertEqual(len(rows), 136)
        self.assertEqual(Counter(row["Execution"] for row in rows),
                         {"active": 85, "retired": 19, "deferred": 32})
        reports = sorted(PACKAGES.glob("*/processed/*_crate_mapping_provenance.md"))
        self.assertGreaterEqual(len(reports), 3)
        for report in reports:
            with self.subTest(report=report.name):
                text = report.read_text(encoding="utf-8")
                self.assertIn("136 table rows declared", text)
                self.assertIn("Executable table rules: 85; retired: 19; deferred: 32; "
                              "original table rows: 136", text)
                detailed = re.findall(
                    r"^\| (\w+\.\w+) \| (filled|subsumed|empty|unresolvable|"
                    r"unplaceable|retired|deferred) \| (.*)$", text, re.M)
                by_path = {path: (status, rest) for path, status, rest in detailed}
                self.assertEqual(len(detailed), len(by_path))
                self.assertEqual(set(by_path),
                                 {row["D4D_Full_Path"] for row in rows} | {"Dataset.id"})
                totals = Counter(status for _, status, _ in detailed)
                for status in ("filled", "subsumed", "empty", "unresolvable",
                               "unplaceable", "retired", "deferred"):
                    self.assertRegex(text, rf"(?m)^\| {status} \| {totals[status]} \|")
                self.assertEqual(totals["retired"], 19)
                self.assertEqual(totals["deferred"], 32)
                for row in rows:
                    status, rest = by_path[row["D4D_Full_Path"]]
                    if row["Execution"] == "active":
                        self.assertNotIn(status, ("retired", "deferred"))
                    else:
                        self.assertEqual(status, row["Execution"])
                        reason = row["Execution_Reason"].replace("|", "\\|").replace("\n", " ")
                        self.assertTrue(rest.endswith(reason + " |"), row["Rule_ID"])

    def test_source_sidecars_pin_outputs_and_preserve_values_at_their_subjects(self):
        """Full source evidence must survive inactive rules, false values and
        member-only facts, with every recorded pointer joining to source bytes."""
        table_rows = load_mapping(ROOT / MAPPING_TSV)
        table_sha = hashlib.sha256((ROOT / MAPPING_TSV).read_bytes()).hexdigest()
        rules_sha = hashlib.sha256(json.dumps(table_rows, ensure_ascii=False,
                                             sort_keys=True).encode()).hexdigest()
        schema_sha = hashlib.sha256((ROOT / FULL_SCHEMA).read_bytes()).hexdigest()
        for project in ("CHORUS", "CM4AI", "VOICE"):
            with self.subTest(project=project):
                processed = PACKAGES / project / "processed"
                sidecar = processed / f"{project}_crate_mapping_sources.json"
                evidence = json.loads(sidecar.read_text(encoding="utf-8"))
                source = ROOT / evidence["source"]["path"]
                if source.is_file():
                    source_bytes = source.read_bytes()
                else:
                    self.assertEqual(project, "CM4AI")
                    with zipfile.ZipFile(PACKAGES / project / "raw/cm4ai_release_metadata.zip") as archive:
                        member = archive.getinfo("cm4ai_release_metadata/ro-crate-metadata.json")
                        self.assertLessEqual(member.file_size, 16 * 1024 * 1024)
                        source_bytes = archive.read(member)
                document = json.loads(source_bytes)
                self.assertEqual(evidence["format_version"], 1)
                self.assertEqual(evidence["source"]["sha256"], hashlib.sha256(source_bytes).hexdigest())
                self.assertEqual(evidence["mapping_table"]["sha256"], table_sha)
                self.assertEqual(evidence["mapping_table"]["rules_sha256"], rules_sha)
                self.assertEqual(evidence["schema"]["sha256"], schema_sha)
                record = processed / f"{project}_crate_mapped_d4d.yaml"
                self.assertEqual(evidence["record_sha256"], hashlib.sha256(record.read_bytes()).hexdigest())
                root_index = evidence["root"]["graph_index"]
                self.assertIsInstance(root_index, int)
                root = document["@graph"][root_index]
                self.assertEqual(evidence["root"]["properties"], root)
                self.assertEqual(evidence["root"]["id"], root["@id"])
                self.assertEqual(len(evidence["rows"]), 136)
                self.assertEqual([row["rule_id"] for row in evidence["rows"]],
                                 [row["Rule_ID"] for row in table_rows])
                for row, original in zip(evidence["rows"], table_rows, strict=True):
                    self.assertEqual(row["execution"], original["Execution"])
                    self.assertEqual(row["d4d_path"], original["D4D_Full_Path"])
                    self.assertEqual(row["source_expression"], original["RO_Crate_JSON_Path"])
                    if row["execution"] != "active":
                        self.assertEqual(row["status"], row["execution"])
                    for scope in ("root_assertions", "member_assertions", "linked_assertions"):
                        for assertion in row[scope]:
                            pointer = assertion["json_pointer"]
                            self.assertEqual(pointer_value(document, pointer), assertion["value"])
                            entity_index = int(pointer.split("/")[2])
                            self.assertEqual(document["@graph"][entity_index].get("@id"),
                                             assertion["entity_id"])
                            if scope == "root_assertions":
                                self.assertEqual(entity_index, root_index)
                            elif scope == "member_assertions":
                                self.assertNotEqual(entity_index, root_index)
                # A deferred FDA claim stays regulated, never silently drops
                # false or changes it into a compliance assertion.
                fda = next(row for row in evidence["rows"]
                           if row["rule_id"] == "49c24423:legacy-line-115")
                self.assertEqual(fda["status"], "deferred")
                if "fdaRegulated" in root:
                    self.assertEqual([a["value"] for a in fda["root_assertions"]],
                                     [root["fdaRegulated"]])
                if project == "VOICE":
                    self.assertIs(root["fdaRegulated"], False)
                    lineage = next(row for row in evidence["rows"]
                                   if row["rule_id"] == "49c24423:legacy-line-111")
                    self.assertEqual(lineage["root_assertions"], [])
                    self.assertTrue(lineage["member_assertions"])


def pointer_value(document, pointer):
    """Read an RFC6901 pointer without importing the producer's evidence code."""
    value = document
    for part in pointer.split("/")[1:]:
        key = part.replace("~1", "/").replace("~0", "~")
        value = value[int(key)] if isinstance(value, list) else value[key]
    return value


def placed_nowhere_rows(text):
    """A report's `unplaceable` rows that place nowhere, D4D path -> the rest
    of the row: all of them but the nested rows refused only because their
    merge is undecided, which do place (#3270)."""
    rows = re.findall(r"^\| (\S+) \| unplaceable \| (.*)$", text, re.M)
    return {path: rest for path, rest in rows if not rest.endswith(UNDECIDED_MERGE_END)}


def declaration_cell(kind, reason):
    """How the report cell of a row the table declares `kind`, for `reason`,
    ends: as `map_crate` words it, escaped as `write_provenance` escapes a
    cell."""
    text = (f"{UNPLACED_KINDS.get(kind, kind)}, as the table declares"
            + (f": {reason}" if reason else ""))
    return text.replace("|", "\\|").replace("\n", " ") + " |"


def legend_tail(declared):
    """How the Outcome legend's `unplaceable` row ends for `declared` (D4D
    path -> (kind, reason)), as `write_provenance` writes it: the known kinds
    first, in `UNPLACED_KINDS` order, each with its count."""
    kinds = [kind for kind, _ in declared.values()]
    return (f"; the mapping table says why for {len(kinds)} of them: "
            + ", ".join(f"{kinds.count(kind)} {UNPLACED_KINDS.get(kind, kind)}"
                        for kind in dict.fromkeys([*UNPLACED_KINDS, *kinds])
                        if kind in kinds) + " |")


class TestTheGuardReadsWhatTheMapperWrites(unittest.TestCase):
    """The committed-report guard above reads a report as `write_provenance`
    writes one (#4413). This builds its own report, so it is not a corpus
    test: it runs in the pull-request lane."""

    def test_a_declared_row_is_told_from_an_undecided_merge_in_the_same_words(self):
        protocol = "rai:dataPreprocessingProtocol"
        graph = [{"@id": "ro-crate-metadata.json", "@type": "CreativeWork",
                  "about": {"@id": "./"}},
                 {"@id": "./", "@type": ["https://w3id.org/EVI#Dataset",
                                         "https://w3id.org/EVI#ROCrate"],
                  protocol: ["Resampled."], "rai:dataBiases": "Clinic cohort."}]

        def row(path, source, **declaration):
            return {"D4D_Full_Path": path, "RO_Crate_JSON_Path": source,
                    "Mapping_Type": "closeMatch", "Information_Loss": "minimal",
                    **declaration}

        # A declared reason in the words of the mapper's undecided-merge note.
        declared = {"NoSuchClass.description": (
            "owner_question", "Merging two crate properties into one object is not decided.")}
        kind, reason = declared["NoSuchClass.description"]
        rows = [row("Dataset.preprocessing_strategies",
                    f"@graph[?@type='Dataset']['{protocol}']"),
                row("PreprocessingStrategy.description", "rai:dataBiases"),
                row("NoSuchClass.description", protocol,
                    Unplaced=kind, Unplaced_Reason=reason)]
        res = map_crate(graph, rows, shared_view(FULL_SCHEMA), "TEST")
        res.validation = "PASS"
        self.assertEqual(["PreprocessingStrategy.description"],
                         [f.d4d_path for f in res.fields if f.merge_undecided])
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "TEST_crate_mapping_provenance.md"
            write_provenance(res, path, Path("crate/ro-crate-metadata.json"))
            text = path.read_text(encoding="utf-8")
        placed_nowhere = placed_nowhere_rows(text)
        self.assertEqual(["NoSuchClass.description"], list(placed_nowhere))
        self.assertTrue(placed_nowhere["NoSuchClass.description"].endswith(
            declaration_cell(kind, reason)))
        legend = re.findall(r"^\| unplaceable \| 2 \| .*$", text, re.M)
        self.assertEqual(1, len(legend), text)
        self.assertTrue(legend[0].endswith(legend_tail(declared)), legend[0])


if __name__ == "__main__":
    unittest.main()
