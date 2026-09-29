"""Offline audit recall on synthetic, neutral fixtures (#2921).

Nothing here reads a real audit, original or observation. The fixtures are
invented: an example record, an audit of it that passes audit_grammar, and
ground-truth entries pinned to its sha256.
"""
from copy import deepcopy
import hashlib
import json
import re
import unicodedata
from pathlib import Path

from click.testing import CliRunner
import pytest
import yaml

from data_sheets_schema import audit_grammar, audit_recall as recall

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_FILE = ROOT / "data" / "audit_ground_truth" / "ground_truth.schema.json"
EVIDENCE = [{"source": "example.txt", "chunk": "c001", "quote": "An illustrative source statement."}]


def original(**changes):
    record = {"title": "Example dataset",
              "maintainers": [{"name": "Example Contact", "email": "contact@example.invalid"}],
              "data_collectors": [{"name": "Example Group",
                                   "collector_details": "A group of example members."}],
              "notes": "An example note."}
    record.update(changes)
    return yaml.safe_dump(record, sort_keys=False).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def row(path, verdict="supported"):
    return {"path": path, "claims": [{
        "text": "An illustrative claim.", "verdict": verdict, "attributed_to": [],
        "claim_status": "fact", "source_status": "fact" if verdict == "supported" else "planned",
        "evidence": deepcopy(EVIDENCE), "reason": "Synthetic judgment, not source support."}]}


def finding(*paths, removal=None):
    value = {"severity": "medium", "record": "full", "slot": "example",
             "issue": "An illustrative concern.", "evidence": deepcopy(EVIDENCE)}
    if paths:
        value["review_paths"] = list(paths)
    if removal:
        value["remove_relationship"] = {"path": removal}
    return value


def audit(raw_original, rows, findings=()):
    value = {"findings": list(findings), "summary": "A synthetic audit.",
             "source_review": {"artifact": "original_full", "sha256": sha(raw_original), "values": rows}}
    data = json.dumps(value).encode()
    assert audit_grammar.check(data)["passed"], audit_grammar.check(data)
    return data


def entry(ident, raw_original, *paths, kind="role_placement"):
    return {"id": ident, "target_original_full_sha256": sha(raw_original), "paths": list(paths),
            "kind": kind, "governing_source": {"bundle_sha256": "b" * 64, "source": "example.txt",
                                               "chunk": "c001", "lines": [3, 5]},
            "observation": f"Synthetic observation {ident}.", "reviewer_role": "independent reviewer",
            "reviewed_on": "2026-09-18", "provenance_note": "notes/example_review.md", "held_out": True}


def truth(*entries):
    return {"format": recall.FORMAT, "project": "EXAMPLE", "entries": list(entries)}


def load(value):
    return recall.load_ground_truth(yaml.safe_dump(value, sort_keys=False).encode())


def scored(audit_raw, raw_original, value, **kw):
    return recall.score(audit_raw, raw_original, load(value), **kw)


# Acceptance 1: a supported row at the entry's path is a miss judged supported.
def test_supported_row_at_a_role_placement_path_is_a_miss_judged_supported():
    o = original()
    a = audit(o, [row("/maintainers/0/name"), row("/title")])
    result = scored(a, o, truth(entry("gt-1", o, "/maintainers/0/name")))
    assert result["totals"] == {"paths": 1, "hits": 0, "recall": 0.0, "entries": 1}
    assert result["by_kind"]["role_placement"]["recall"] == 0.0
    assert result["misses_judged_supported"] == [{
        "entry": "gt-1", "kind": "role_placement", "path": "/maintainers/0/name",
        "rows": [{"pointer": "/maintainers/0/name", "relation": "exact"}]}]


# Acceptance 2: a finding's review_path hits; the same audit with the row supported misses.
def test_review_path_hit_for_status_scope_and_the_supported_variant_misses():
    o = original()
    ground = truth(entry("gt-2", o, "/data_collectors/0/collector_details", kind="status_scope"))
    flagged = audit(o, [row("/data_collectors/0/collector_details", "revise")],
                    [finding("/data_collectors/0/collector_details")])
    hit = scored(flagged, o, ground)
    assert hit["by_kind"]["status_scope"] == {"paths": 1, "hits": 1, "recall": 1.0, "entries": 1,
                                              "all_paths_hit": 1, "some_paths_hit": 0, "no_path_hit": 0}
    assert {b["via"] for b in hit["paths"][0]["basis"]} == {"review_path", "revise_row"}
    assert hit["review_candidates"] == [] and hit["misses_judged_supported"] == []

    supported = audit(o, [row("/data_collectors/0/collector_details")])
    miss = scored(supported, o, ground)
    assert miss["by_kind"]["status_scope"]["hits"] == 0
    assert [m["path"] for m in miss["misses_judged_supported"]] == ["/data_collectors/0/collector_details"]


# Acceptance 3: ground truth for another original is not joined.
def test_another_originals_ground_truth_gives_zero_applicable_entries_not_zero_recall():
    o, other = original(), original(title="Another example")
    a = audit(o, [row("/maintainers/0/name")])
    result = scored(a, o, truth(entry("gt-3", other, "/maintainers/0/name")))
    assert result["applicable_entries"] == 0
    assert result["status"] == "no_applicable_entries"
    assert result["totals"]["recall"] == "n/a"
    assert result["entries_for_other_originals"] == {sha(other): 1}
    assert result["paths"] == [] and result["misses_judged_supported"] == []
    text = recall.render_text(recall.report([{"audit": a, "original": o}], load(
        truth(entry("gt-3", other, "/maintainers/0/name"))), ground_truth_raw=b"x"))
    assert "recall is n/a, not 0" in text


# Acceptance 4: an unmatched revise path is a candidate, never a false positive.
def test_an_unmatched_revise_path_is_a_review_candidate_not_a_false_positive():
    o = original()
    a = audit(o, [row("/notes", "revise"), row("/maintainers/0/name", "revise")],
              [finding("/notes"), finding("/maintainers/0/name")])
    result = scored(a, o, truth(entry("gt-4", o, "/maintainers/0/name")))
    assert result["totals"]["hits"] == 1
    assert result["review_candidates"] == [{"pointer": "/notes", "via": ["review_path", "revise_row"],
                                            "findings": [0], "inside_entries": []}]
    whole = json.dumps(recall.report([{"audit": a, "original": o}], load(
        truth(entry("gt-4", o, "/maintainers/0/name"))), ground_truth_raw=b"x"))
    assert "false_positive" not in whole and "precision" not in whole


# Acceptance 5: denominators per kind and per replicate; zero denominators read n/a.
def test_denominators_per_kind_and_replicate_with_n_a_for_empty_kinds():
    o1, o2 = original(), original(title="Second replicate")
    ground = truth(entry("gt-5a", o1, "/maintainers/0/name"),
                   entry("gt-5b", o1, "/notes", "/title", kind="status_scope"),
                   entry("gt-5c", o2, "/notes", kind="date_scope"))
    run1 = audit(o1, [row("/maintainers/0/name", "revise"), row("/notes", "revise"), row("/title")],
                 [finding("/maintainers/0/name", "/notes")])
    run2 = audit(o2, [row("/notes")])
    value = recall.report([{"audit": run1, "original": o1, "replicate": "rep1"},
                           {"audit": run2, "original": o2, "replicate": "rep2"}],
                          load(ground), ground_truth_raw=b"x", arm="example-arm")
    first, second = value["replicates"]
    assert (first["replicate"], second["replicate"]) == ("rep1", "rep2")
    assert set(first["by_kind"]) == set(recall.KINDS)
    assert first["by_kind"]["role_placement"]["recall"] == 1.0
    assert first["by_kind"]["status_scope"] == {"paths": 2, "hits": 1, "recall": 0.5, "entries": 1,
                                                "all_paths_hit": 0, "some_paths_hit": 1, "no_path_hit": 0}
    assert first["by_kind"]["date_scope"] == {"paths": 0, "hits": 0, "recall": "n/a", "entries": 0,
                                              "all_paths_hit": 0, "some_paths_hit": 0, "no_path_hit": 0}
    assert first["totals"] == {"paths": 3, "hits": 2, "recall": 0.6667, "entries": 2}
    assert second["by_kind"]["date_scope"]["recall"] == 0.0
    assert second["by_kind"]["role_placement"]["recall"] == "n/a"
    assert "pooled" not in json.dumps({k: v for k, v in value.items() if k != "limits"})
    text = recall.render_text(value)
    assert "replicate rep1" in text and "replicate rep2" in text and "n/a" in text
    assert value["arm"] == "example-arm"


# Acceptance 6: incomplete entries are refused, each problem named.
@pytest.mark.parametrize("field", ["target_original_full_sha256", "paths", "kind", "reviewer_role",
                                   "reviewed_on", "governing_source", "observation", "provenance_note",
                                   "held_out", "id"])
def test_an_entry_missing_a_required_field_is_refused(field):
    o = original()
    bad = entry("gt-6", o, "/title")
    del bad[field]
    with pytest.raises(recall.GroundTruthError) as caught:
        load(truth(bad))
    assert any(p["at"] == "/entries/0" and repr(field) in p["problem"] for p in caught.value.problems)


def test_every_problem_in_an_entry_and_across_entries_is_named():
    """Not the first problem: each one, at its own location (#3102)."""
    o = original()
    first = entry("gt-a", o, "/title")
    del first["kind"], first["reviewer_role"]
    first["held_out"] = False
    second = entry("gt-b", o, "/notes")
    second["reviewed_on"] = "2026-02-30"
    with pytest.raises(recall.GroundTruthError) as caught:
        load(truth(first, second))
    problems = caught.value.problems
    assert len(problems) == 4, problems
    assert sorted(p["at"] for p in problems) == ["/entries/0", "/entries/0", "/entries/0/held_out",
                                                 "/entries/1/reviewed_on"]
    missing = " ".join(p["problem"] for p in problems if p["at"] == "/entries/0")
    assert "'kind'" in missing and "'reviewer_role'" in missing


def test_problems_are_named_up_to_the_bound():
    o = original()
    many = [{**entry(f"gt-{n}", o, "/title"), "kind": "misc"} for n in range(recall.MAX_PROBLEMS + 5)]
    with pytest.raises(recall.GroundTruthError) as caught:
        load(truth(*many))
    assert len(caught.value.problems) == recall.MAX_PROBLEMS
    assert len({p["at"] for p in caught.value.problems}) == recall.MAX_PROBLEMS


@pytest.mark.parametrize("change, where", [
    ({"paths": []}, "/entries/0/paths"),
    ({"paths": ["title"]}, "/entries/0/paths/0"),
    ({"paths": ["/a~2b"]}, "/entries/0/paths/0"),
    ({"kind": "misc"}, "/entries/0/kind"),
    ({"target_original_full_sha256": "ABC"}, "/entries/0/target_original_full_sha256"),
    ({"reviewed_on": "2026-02-30"}, "/entries/0/reviewed_on"),
    ({"reviewed_on": "Sept 2026"}, "/entries/0/reviewed_on"),
    ({"reviewer_role": "  "}, "/entries/0/reviewer_role"),
    ({"held_out": False}, "/entries/0/held_out"),
    ({"provenance_note": "../elsewhere.md"}, "/entries/0/provenance_note"),
    ({"provenance_note": "/abs/note.md"}, "/entries/0/provenance_note"),
    ({"provenance_note": "notes/./note.md"}, "/entries/0/provenance_note"),
    ({"governing_source": {"bundle_sha256": "b" * 64, "lines": [3, 5]}}, "/entries/0/governing_source"),
    ({"governing_source": {"bundle_sha256": "b" * 64, "chunk": "c001", "lines": [9, 5]}},
     "/entries/0/governing_source/lines"),
    ({"governing_source": {"chunk": "c001", "lines": [3, 5]}}, "/entries/0/governing_source"),
    ({"governing_source": {"bundle_sha256": "b" * 64, "chunk": "c001", "lines": [3.0, 5]}},
     "/entries/0/governing_source/lines/0"),
    ({"expected_fix": "anything"}, "/entries/0"),
])
def test_malformed_entries_are_refused_at_their_location(change, where):
    bad = entry("gt-6", original(), "/title")
    bad.update(change)
    with pytest.raises(recall.GroundTruthError) as caught:
        load(truth(bad))
    assert where in {p["at"] for p in caught.value.problems}, caught.value.problems


def test_out_of_order_lines_written_as_floats_are_refused():
    """The schema's "integer" admits 9.0; the order check must not skip it (#3098)."""
    bad = entry("gt-6", original(), "/title")
    bad["governing_source"]["lines"] = [9.0, 5.0]
    with pytest.raises(recall.GroundTruthError) as caught:
        load(truth(bad))
    assert sorted(p["at"] for p in caught.value.problems) == [
        "/entries/0/governing_source/lines", "/entries/0/governing_source/lines/0",
        "/entries/0/governing_source/lines/1"]
    assert "first line is after the last" in str(caught.value)


@pytest.mark.parametrize("field, where", [
    (("target_original_full_sha256",), "/entries/0/target_original_full_sha256"),
    (("governing_source", "bundle_sha256"), "/entries/0/governing_source/bundle_sha256"),
    (("id",), "/entries/0/id"),
    (("reviewed_on",), "/entries/0/reviewed_on"),
])
def test_a_value_ending_in_a_newline_is_refused_not_left_to_join_nothing(field, where):
    """Python's "$" also matches before a final newline; the patterns anchor at end of input (#3097)."""
    bad = entry("gt", original(), "/title")
    *parents, leaf = field
    holder = bad
    for key in parents:
        holder = holder[key]
    holder[leaf] += "\n"
    with pytest.raises(recall.GroundTruthError) as caught:
        load(truth(bad))
    assert where in {p["at"] for p in caught.value.problems}, caught.value.problems


def test_a_hash_written_as_a_block_scalar_is_refused():
    o = original()
    raw = yaml.safe_dump(truth(entry("gt", o, "/title")), sort_keys=False).replace(
        f"target_original_full_sha256: {sha(o)}\n", f"target_original_full_sha256: |\n      {sha(o)}\n")
    assert f"|\n      {sha(o)}\n".encode() in raw.encode()
    with pytest.raises(recall.GroundTruthError) as caught:
        recall.load_ground_truth(raw.encode())
    assert [p["at"] for p in caught.value.problems] == ["/entries/0/target_original_full_sha256"]


#: ECMA-262's \s: WhiteSpace (TAB, VT, FF, SP, NBSP, ZWNBSP and category Zs)
#: and LineTerminator (LF, CR, LS, PS), as the specification lists them.
ECMA_WHITESPACE = ({"\t", "\v", "\f", " ", "\xa0", "\ufeff", "\n", "\r", "\u2028", "\u2029"}
                   | {chr(c) for c in range(0x110000) if unicodedata.category(chr(c)) == "Zs"})


def test_text_fields_refuse_the_same_characters_in_both_dialects():
    r"""``\S`` classifies U+FEFF, U+001C-U+001F and U+0085 differently in Python's
    re and ECMA-262 (#3215). The text pattern refuses the union, so a lone such
    character is refused by the loader and by an ECMA-262 validator alike."""
    pattern = recall._TEXT["pattern"]
    # The pattern as an ECMA-262 engine reads it: its \s spelled out. The rest
    # of the class (\xhh, \uhhhh, ranges) means the same in both dialects.
    assert pattern.count("\\s") == 1 and "\\S" not in pattern
    ecma_class = "".join(f"\\U{ord(c):08x}" for c in sorted(ECMA_WHITESPACE))
    as_ecma = re.compile(pattern.replace("\\s", ecma_class))
    as_python = re.compile(pattern)
    refused = set()
    for c in map(chr, range(0x110000)):
        python, ecma = bool(as_python.search(c)), bool(as_ecma.search(c))
        assert python is ecma, hex(ord(c))
        if not python:
            refused.add(c)
    # It still refuses exactly whitespace, by either dialect's definition.
    python_ws = {chr(c) for c in range(0x110000) if re.fullmatch(r"\s", chr(c))}
    assert refused == python_ws | ECMA_WHITESPACE
    o = original()
    for lone in ("\ufeff", "\x1f", "\x85", "\u3000"):
        with pytest.raises(recall.GroundTruthError) as caught:
            load(truth({**entry("gt", o, "/title"), "observation": lone}))
        assert [p["at"] for p in caught.value.problems] == ["/entries/0/observation"], hex(ord(lone))
    load(truth({**entry("gt", o, "/title"), "observation": "\ufeffA visible observation."}))


def test_every_anchored_pattern_ends_at_end_of_input_in_both_dialects():
    """A bare "$" means end of input in ECMA-262 but not in Python's re (#3097)."""
    patterns = []

    def walk(node):
        if isinstance(node, dict):
            for key, value in node.items():
                if key == "pattern":
                    patterns.append(value)
                else:
                    walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)
    walk(recall.ground_truth_schema())
    anchored = [p for p in patterns if p.startswith("^")]
    assert len(anchored) == 5
    assert [p for p in anchored if p.endswith("$") or not p.endswith(r"(?![\s\S])")] == []


def test_file_level_problems_are_refused():
    o = original()
    with pytest.raises(recall.GroundTruthError) as caught:
        load(truth(entry("dup", o, "/title"), entry("dup", o, "/notes")))
    assert "/entries/1/id" in {p["at"] for p in caught.value.problems}
    with pytest.raises(recall.GroundTruthError):
        load({"format": recall.FORMAT, "project": "EXAMPLE", "entries": []})
    with pytest.raises(recall.GroundTruthError):
        load({**truth(entry("a", o, "/title")), "format": "other_v1"})
    duplicated = b"format: audit_ground_truth_v1\nproject: A\nproject: B\nentries: []\n"
    with pytest.raises(recall.GroundTruthError, match="duplicate"):
        recall.load_ground_truth(duplicated)
    with pytest.raises(recall.GroundTruthError, match="UTF-8"):
        recall.load_ground_truth(b"\xff\xfe")


@pytest.mark.parametrize("dump", [
    lambda v: json.dumps(v, indent="\t"),
    lambda v: json.dumps(v).replace('": ', '":\t'),
    lambda v: json.dumps(v, indent=2).replace("\n    ", "\n\t  "),
], ids=["tab-indented", "tab-after-a-colon-on-one-line", "tab-below-the-first-level"])
def test_json_with_tab_whitespace_is_read_as_json(dump):
    """PyYAML reads YAML 1.1, which refuses a tab used as whitespace (#3177)."""
    value = truth(entry("tab", original(), "/title"))
    raw = dump(value).encode()
    assert b"\t" in raw and json.loads(raw) == value
    with pytest.raises(yaml.YAMLError):
        yaml.safe_load(raw)
    assert recall.load_ground_truth(raw) == value


def test_json_refuses_duplicate_keys_and_text_neither_grammar_reads_is_named_without_its_content():
    raw = b'{"format": "audit_ground_truth_v1",\t"project": "A", "project": "B", "entries": []}'
    with pytest.raises(recall.GroundTruthError, match="duplicate mapping key 'project'"):
        recall.load_ground_truth(raw)
    with pytest.raises(recall.GroundTruthError) as caught:
        recall.load_ground_truth(b'observation: "A planted observation left unterminated\n')
    [problem] = caught.value.problems
    assert problem["problem"] == ("neither JSON (Expecting value at line 1 column 1) "
                                  "nor YAML (ScannerError)")
    assert "planted" not in str(caught.value)


SECRET = "Planted held-out prose"


@pytest.mark.parametrize("change, where, named", [
    # jsonschema's messages repr the value; each of these once quoted it (#3255).
    (lambda e: {**e, "observation": SECRET + " " + "x" * 2000}, "/entries/0/observation",
     "longer than 2000 characters"),
    (lambda e: SECRET + " written as a bare entry", "/entries/0", "must be of type object"),
    (lambda e: {**e, "kind": SECRET}, "/entries/0/kind", "not one of ["),
    (lambda e: {**e, "id": SECRET}, "/entries/0/id", "does not match the pattern"),
    (lambda e: {**e, "paths": [SECRET]}, "/entries/0/paths/0", "does not match the pattern"),
    (lambda e: {**e, "paths": ["/title", "/title"]}, "/entries/0/paths", "items are not unique"),
    (lambda e: {**e, "held_out": SECRET}, "/entries/0/held_out", "must be True"),
    (lambda e: {**e, SECRET: 1, "extra_field": 2}, "/entries/0",
     "properties the schema does not declare: 'extra_field', 1 not shaped like a field name"),
])
def test_a_schema_refusal_names_the_rule_and_never_quotes_the_value(change, where, named):
    """The refusal reaches the terminal, and the text refused may be held-out prose (#3255)."""
    bad = change(entry("gt-1", original(), "/title"))
    with pytest.raises(recall.GroundTruthError) as caught:
        load(truth(bad))
    assert any(p["at"] == where and named in p["problem"] for p in caught.value.problems), caught.value.problems
    assert "Planted" not in str(caught.value) and "Planted" not in repr(caught.value.problems)


DUPLICATED_SECRET = {
    "yaml": ("format: audit_ground_truth_v1\nproject: A\nentries:\n- id: gt\n"
             f"  {SECRET}: one\n  {SECRET}: two\n").encode(),
    "json": ('{"format": "audit_ground_truth_v1", "project": "A", "entries": [{"id": "gt", '
             f'"{SECRET}": "one", "{SECRET}": "two"}}]}}').encode(),
}


@pytest.mark.parametrize("dialect", sorted(DUPLICATED_SECRET))
def test_a_duplicated_key_is_named_only_when_the_schema_declares_it(dialect):
    """Parsing runs before the #3255 redaction, and a key may be held-out prose (#3267)."""
    with pytest.raises(recall.GroundTruthError) as caught:
        recall.load_ground_truth(DUPLICATED_SECRET[dialect])
    [problem] = caught.value.problems
    assert problem["problem"].startswith("duplicate mapping key the schema does not declare")
    assert "Planted" not in str(caught.value) and "Planted" not in repr(caught.value.problems)
    if dialect == "yaml":
        assert problem["problem"].endswith(" at line 6 column 3")
    declared = b"format: audit_ground_truth_v1\nproject: A\nproject: B\nentries: []\n"
    with pytest.raises(recall.GroundTruthError, match="duplicate mapping key 'project' at line 3 column 1"):
        recall.load_ground_truth(declared)
    nested = b"entries:\n- governing_source: {lines: [1, 2], lines: [3, 4]}\n"
    with pytest.raises(recall.GroundTruthError, match="duplicate mapping key 'lines' at line 2"):
        recall.load_ground_truth(nested)


def test_every_rule_the_schema_uses_has_a_description_that_quotes_no_value():
    """A rule missing from the describer would fall back to naming only the rule (#3255)."""
    annotations = {"$schema", "$id", "title", "description", "properties", "items", "$defs"}

    def rules(node):
        # Keywords of a schema node; the names under "properties" are fields, not rules.
        yield from (k for k in node if k not in annotations)
        for child in node.get("properties", {}).values():
            yield from rules(child)
        for key in ("items", "additionalProperties"):
            if isinstance(node.get(key), dict):
                yield from rules(node[key])
        for child in node.get("anyOf", []):
            yield from rules(child)
    used = set(rules(recall.ground_truth_schema()))
    assert {"maxLength", "pattern", "enum", "type"} <= used
    assert used - set(recall._DESCRIBED_RULES) == set()


#: Well under MAX_GROUND_TRUTH_BYTES, and deeper than either parser recurses.
DEEP_TEXTS = {
    "json array": b"[" * 100_000 + b"]" * 100_000,
    "json under entries": b'{"entries": ' + b"[" * 100_000 + b"]" * 100_000 + b"}",
    "yaml block sequence": b"- " * 5_000 + b"x",
}


@pytest.mark.parametrize("raw", DEEP_TEXTS.values(), ids=DEEP_TEXTS)
def test_nesting_too_deep_to_parse_is_refused_not_raised(raw):
    """A RecursionError from either parser is a refusal with a named problem (#3214)."""
    assert len(raw) < recall.MAX_GROUND_TRUTH_BYTES
    with pytest.raises(recall.GroundTruthError) as caught:
        recall.load_ground_truth(raw)
    assert caught.value.problems == [{"at": "", "problem": "nested too deeply to read"}]


def test_an_original_nested_too_deeply_is_not_scored_rather_than_raised():
    deep = b"- " * 5_000 + b"x"
    with pytest.raises(recall.AuditRecallError, match="not a readable YAML record: RecursionError"):
        scored(audit(deep, []), deep, truth(entry("gt", original(), "/title")))


@pytest.mark.parametrize("raw", [b"title: T\nx: !!set {a, b}\n", b"title: T\nx: !!binary aGk=\n"],
                         ids=["set", "binary"])
def test_an_original_holding_a_value_json_cannot_carry_is_not_scored_rather_than_raised(raw):
    """``!!set`` and ``!!binary`` load as set and bytes, which the inventory cannot serialise (#3236)."""
    with pytest.raises(recall.AuditRecallError, match="not a readable YAML record: TypeError"):
        scored(audit(raw, []), raw, truth(entry("gt", raw, "/title")))


def test_a_complete_entry_loads_with_its_date_as_written():
    o = original()
    raw = yaml.safe_dump(truth(entry("ok", o, "/title")), sort_keys=False).replace(
        "'2026-09-18'", "2026-09-18").encode()
    assert b"reviewed_on: 2026-09-18\n" in raw
    loaded = recall.load_ground_truth(raw)
    assert loaded["entries"][0]["reviewed_on"] == "2026-09-18"


def test_ancestor_removal_hits_and_a_flag_below_does_not():
    o = original()
    ground = truth(entry("leaf", o, "/maintainers/0/name"), entry("container", o, "/data_collectors/0"))
    a = audit(o, [row("/maintainers/0/name"), row("/data_collectors/0/name", "revise")],
              [finding(removal="/maintainers/0"), finding("/data_collectors/0/name")])
    result = scored(a, o, ground)
    leaf, container = result["paths"]
    assert leaf["outcome"] == "hit"
    assert leaf["basis"] == [{"pointer": "/maintainers/0", "via": "remove_relationship",
                              "finding": 0, "relation": "ancestor"}]
    assert container == {**container, "outcome": "miss", "miss": "flagged_below",
                         "flags": ["/data_collectors/0/name"]}
    assert result["review_candidates"] == [{"pointer": "/data_collectors/0/name",
                                            "via": ["review_path", "revise_row"], "findings": [1],
                                            "inside_entries": ["container"]}]


def test_pointer_segments_not_string_prefixes_decide_ancestry():
    o = original(note="n", notes="An example note.")
    a = audit(o, [row("/note", "revise")], [finding("/note")])
    result = scored(a, o, truth(entry("gt", o, "/notes")))
    assert result["paths"][0]["outcome"] == "miss"


def test_misses_not_judged_supported_are_classified():
    o = original()
    a = audit(o, [{"path": "/title", "metadata_reason": "A synthetic metadata value."}])
    result = scored(a, o, truth(entry("meta", o, "/title"), entry("absent", o, "/funders/0/name",
                                                                   kind="omission")))
    meta, absent = result["paths"]
    assert (meta["miss"], meta["rows"], meta["resolves_in_original"]) == ("metadata_only", ["/title"], True)
    assert (absent["miss"], absent["resolves_in_original"]) == ("not_reviewed", False)
    assert result["misses_judged_supported"] == []


_META = {"path": "/maintainers/0", "metadata_reason": "A synthetic metadata value."}


@pytest.mark.parametrize("rows, flagged, expected", [
    # A supported row at the path outranks a flag below it.
    ([row("/maintainers/0")], True,
     {"miss": "judged_supported", "rows": [{"pointer": "/maintainers/0", "relation": "exact"}]}),
    # So does one above it.
    ([row("/maintainers")], True,
     {"miss": "judged_supported", "rows": [{"pointer": "/maintainers", "relation": "ancestor"}]}),
    # A flag below outranks a supported row below.
    ([row("/maintainers/0/name")], True, {"miss": "flagged_below", "flags": ["/maintainers/0/email"]}),
    # A flag below outranks a metadata row at the path.
    ([_META], True, {"miss": "flagged_below", "flags": ["/maintainers/0/email"]}),
    # With no flag below, a supported row below outranks a metadata row at the path.
    ([_META, row("/maintainers/0/name")], False,
     {"miss": "judged_supported", "rows": [{"pointer": "/maintainers/0/name", "relation": "below"}]}),
])
def test_misses_are_classified_in_the_documented_order(rows, flagged, expected):
    """judged_supported (at or above; below only with no flag below), flagged_below,
    metadata_only, not_reviewed — the README's order, pair by pair (#3105)."""
    o = original()
    revise = [row("/maintainers/0/email", "revise")] if flagged else []
    a = audit(o, [*deepcopy(rows), *revise], [finding("/maintainers/0/email")] if flagged else [])
    result = scored(a, o, truth(entry("gt", o, "/maintainers/0")))
    (path,) = result["paths"]
    assert {key: path.get(key) for key in expected} == expected
    listed = [m["path"] for m in result["misses_judged_supported"]]
    assert listed == (["/maintainers/0"] if expected["miss"] == "judged_supported" else [])


def test_supported_rows_below_a_container_entry_are_judged_supported():
    o = original()
    a = audit(o, [row("/maintainers/0/name"), row("/maintainers/0/email")])
    result = scored(a, o, truth(entry("gt", o, "/maintainers/0")))
    assert result["misses_judged_supported"][0]["rows"] == [
        {"pointer": "/maintainers/0/email", "relation": "below"},
        {"pointer": "/maintainers/0/name", "relation": "below"}]


def test_an_audit_of_another_original_is_refused():
    o = original()
    a = audit(original(title="Something else"), [row("/title")])
    with pytest.raises(recall.AuditRecallError, match="source_review.sha256"):
        scored(a, o, truth(entry("gt", o, "/title")))


def grammar_failing_audit(raw_original):
    value = json.loads(audit(raw_original, [row("/title", "revise")], [finding("/title")]))
    value["findings"] = []                       # revise row with no linked finding
    return json.dumps(value).encode()


def test_an_audit_failing_the_grammar_is_refused():
    o = original()
    with pytest.raises(recall.AuditRecallError, match="revise_without_finding"):
        scored(grammar_failing_audit(o), o, truth(entry("gt", o, "/title")))


def test_the_report_carries_pins_and_no_observation_or_audit_prose():
    o = original()
    ground = truth(entry("gt", o, "/maintainers/0/name"), entry("gt-b", o, "/notes"))
    raw = yaml.safe_dump(ground).encode()
    a = audit(o, [row("/maintainers/0/name"), row("/notes", "revise")], [finding("/notes")])
    value = recall.report([{"audit": a, "original": o, "replicate": "rep1", "audit_path": "a.json",
                            "original_path": "o.yaml"}], recall.load_ground_truth(raw),
                          ground_truth_raw=raw, ground_truth_label="gt.yaml", arm="arm")
    assert value["instrument"] == recall.INSTRUMENT
    assert value["instrument_sha256"] == sha(Path(recall.__file__).read_bytes())
    assert value["audit_grammar"] == {"instrument": audit_grammar.INSTRUMENT,
                                      "sha256": sha(Path(audit_grammar.__file__).read_bytes())}
    assert value["ground_truth"]["sha256"] == sha(raw)
    assert value["hit_rule"]["status"].startswith("provisional")
    run = value["replicates"][0]
    assert run["audit"]["sha256"] == sha(a) and run["original"]["sha256"] == sha(o)
    text = json.dumps(value) + recall.render_text(value)
    for prose in ("Synthetic observation", "An illustrative", "Synthetic judgment", "A synthetic audit"):
        assert prose not in text
    assert any("not general audit quality" in line for line in value["limits"])


def test_the_committed_schema_file_is_the_loaders_schema():
    assert SCHEMA_FILE.read_text(encoding="utf-8") == recall.schema_text()


def test_the_readme_example_takes_the_original_from_beside_the_audit():
    """The runs keep original_full.yaml in <run>/evidence/ beside audit.json
    (api_runner.native_evidence_instructions and the audit controls), #3178."""
    text = (SCHEMA_FILE.parent / "README.md").read_text(encoding="utf-8")
    audit_path = re.search(r"--audit (\S+/audit\.json)", text).group(1)
    original_path = re.search(r"--original (\S+/original_full\.yaml)", text).group(1)
    assert audit_path == "<run>/evidence/audit.json"
    assert original_path == "<run>/evidence/original_full.yaml"


#: The issue's proposed list plus ``omission`` (#2930), written out so that a
#: change to KINDS is a change here too.
PROPOSED_KINDS = ("role_placement", "status_scope", "date_scope", "absence_or_self_narration",
                  "quotation_fidelity", "identifier_count", "attribution", "omission", "other")


def test_the_proposed_kinds_are_accepted_and_nothing_else_is():
    o = original()
    assert recall.KINDS == PROPOSED_KINDS
    for kind in PROPOSED_KINDS:
        load(truth(entry("k", o, "/title", kind=kind)))
    for kind in ("misc", "Role_placement", "role placement", "omission ", "", None, 3):
        with pytest.raises(recall.GroundTruthError) as caught:
            load(truth(entry("k", o, "/title", kind=kind)))
        assert [p["at"] for p in caught.value.problems] == ["/entries/0/kind"], kind


class TestCommand:
    def files(self, tmp_path, ground):
        o = original()
        a = audit(o, [row("/maintainers/0/name"), row("/notes", "revise")], [finding("/notes")])
        paths = {"audit": tmp_path / "audit.json", "original": tmp_path / "original_full.yaml",
                 "truth": tmp_path / "truth.yaml"}
        paths["audit"].write_bytes(a)
        paths["original"].write_bytes(o)
        paths["truth"].write_text(yaml.safe_dump(ground(o), sort_keys=False))
        return paths

    def invoke(self, *args):
        from data_sheets_schema.cli.evaluate import evaluate
        return CliRunner().invoke(evaluate, ["audit-recall", *map(str, args)])

    def test_summary_json_and_output_file(self, tmp_path):
        p = self.files(tmp_path, lambda o: truth(entry("gt", o, "/maintainers/0/name")))
        out = self.invoke("--audit", p["audit"], "--original", p["original"], "--ground-truth", p["truth"],
                          "--arm", "example", "--replicate", "rep1", "--output", tmp_path / "report.json")
        assert out.exit_code == 0, out.output
        assert "miss judged supported: gt [role_placement] /maintainers/0/name" in out.output
        assert "review candidate: /notes" in out.output and "provisional" in out.output
        written = json.loads((tmp_path / "report.json").read_text())
        assert written["replicates"][0]["replicate"] == "rep1"
        as_json = self.invoke("--audit", p["audit"], "--original", p["original"],
                              "--ground-truth", p["truth"], "--json")
        assert json.loads(as_json.output)["replicates"][0]["totals"]["paths"] == 1

    def test_refusals_exit_nonzero_with_the_reason(self, tmp_path):
        p = self.files(tmp_path, lambda o: truth({**{k: v for k, v in entry("gt", o, "/title").items()
                                                     if k != "reviewer_role"}, "kind": "misc"}))
        out = self.invoke("--audit", p["audit"], "--original", p["original"], "--ground-truth", p["truth"])
        assert out.exit_code == 1 and "'reviewer_role' is a required property" in out.output
        assert "/entries/0/kind: not one of" in out.output and "'misc'" not in out.output
        p = self.files(tmp_path, lambda o: truth(entry("gt", o, "/title")))
        out = self.invoke("--audit", p["audit"], "--original", p["truth"], "--ground-truth", p["truth"])
        assert out.exit_code == 1 and "not scored" in out.output
        out = self.invoke("--audit", p["audit"], "--audit", p["audit"], "--original", p["original"],
                          "--ground-truth", p["truth"])
        assert out.exit_code == 2 and "one --original for each --audit" in out.output
        before = p["audit"].read_bytes()
        out = self.invoke("--audit", p["audit"], "--original", p["original"], "--ground-truth", p["truth"],
                          "--output", p["audit"])
        assert out.exit_code == 2 and "names an input" in out.output
        assert p["audit"].read_bytes() == before

    @pytest.mark.parametrize("dialect", sorted(DUPLICATED_SECRET))
    def test_a_duplicated_prose_key_never_reaches_the_terminal(self, tmp_path, dialect):
        """The Codex reproduction of #3267, through the command."""
        p = self.files(tmp_path, lambda o: truth(entry("gt", o, "/title")))
        p["truth"].write_bytes(DUPLICATED_SECRET[dialect])
        out = self.invoke("--audit", p["audit"], "--original", p["original"], "--ground-truth", p["truth"])
        assert out.exit_code == 1, out.output
        assert "ground truth refused:\n  /: duplicate mapping key the schema does not declare" in out.output
        assert "Planted" not in out.output

    def test_ground_truth_nested_too_deeply_is_refused_with_the_message(self, tmp_path):
        p = self.files(tmp_path, lambda o: truth(entry("gt", o, "/title")))
        p["truth"].write_bytes(DEEP_TEXTS["json array"])
        out = self.invoke("--audit", p["audit"], "--original", p["original"], "--ground-truth", p["truth"])
        assert out.exit_code == 1, out.output
        assert out.exception is None or isinstance(out.exception, SystemExit), repr(out.exception)
        assert "ground truth refused:\n  /: nested too deeply to read" in out.output

    def test_an_original_with_a_set_value_is_not_scored_with_the_message(self, tmp_path):
        p = self.files(tmp_path, lambda o: truth(entry("gt", o, "/title")))
        o = b"title: T\nx: !!set {a, b}\n"
        p["original"].write_bytes(o)
        p["audit"].write_bytes(audit(o, []))
        p["truth"].write_text(yaml.safe_dump(truth(entry("gt", o, "/title")), sort_keys=False))
        out = self.invoke("--audit", p["audit"], "--original", p["original"], "--ground-truth", p["truth"])
        assert out.exit_code == 1, out.output
        assert out.exception is None or isinstance(out.exception, SystemExit), repr(out.exception)
        assert "not scored: " in out.output and "original is not a readable YAML record: TypeError" in out.output

    def test_an_audit_failing_the_grammar_writes_no_report_and_is_left_unchanged(self, tmp_path):
        p = self.files(tmp_path, lambda o: truth(entry("gt", o, "/title")))
        p["audit"].write_bytes(grammar_failing_audit(p["original"].read_bytes()))
        before = p["audit"].read_bytes()
        report = tmp_path / "report.json"
        out = self.invoke("--audit", p["audit"], "--original", p["original"], "--ground-truth", p["truth"],
                          "--output", report)
        assert out.exit_code == 1 and "not scored" in out.output and "revise_without_finding" in out.output
        assert not report.exists()
        assert p["audit"].read_bytes() == before
