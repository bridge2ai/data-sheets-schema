"""Self-disclaimed typed-container entries (#2913): synthetic, project-neutral
fixtures for the lexicon (check a), the receipt role predicates (check b),
the original-to-final diff, the CLI and the module's boundaries."""
import ast
import copy
import hashlib
import inspect
import json
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from data_sheets_schema import self_disclaimed as sd

LEXICON = sd.load_lexicon()

#: Pins on the lexicon's exact bytes, one per version. Changing the file
#: without a version bump fails here; so does bumping without a pin. v1 was
#: revised in review before it merged (#3080, #3081); nothing committed
#: names its earlier sha (9b1f536b...).
LEXICON_PINS = {1: "728e4e8b87aeefce7c2de27541392e53ee11cbf8d74fe7587309abf227a24a6d"}


def record(**containers):
    return {"id": "https://example.org/ds", "name": "Example dataset", **containers}


def flagged(rec):
    return {f["path"]: [h["rule"] for h in f["hits"]] for f in sd.scan(rec, LEXICON)["flags"]}


def classes(result):
    return {row["path"]: row["classification"] for row in result["lexicon_diff"]["rows"]}


# ------------------------------------------------------------------ check (a)
def test_negation_lexicon_hit_on_the_members_own_prose():
    rec = record(creators=[
        {"name": "Person A", "description": "Named as principal investigator on the award."},
        {"name": "Person B", "description": "Listed on a leadership slide. "
                                            "The slide does not assign this member a project title."}])
    flags = sd.scan(rec, LEXICON)["flags"]
    assert [f["path"] for f in flags] == ["/creators/1"]
    hit = flags[0]["hits"][0]
    assert (hit["rule"], hit["class"], hit["leaf"]) == (
        "role.assignment_negated", "role_disclaimer", "/creators/1/description")
    assert hit["scope"] == "title"


def test_maintainer_whose_caveat_says_no_source_establishes_the_role():
    rec = record(maintainers=[{"name": "Person A", "maintainer_details": "Listed under Contact Us.",
                               "source_caveats": "No source states who hosts or maintains the dataset, "
                                                 "and none assigns a maintainer category."}])
    assert set(flagged(rec)["/maintainers/0"]) == {"role.none_assigns"}


@pytest.mark.parametrize("container,key,text", [
    ("variables", "derivation", "This is stated as planned work rather than as a variable present in the released data."),
    ("instances", "description", "This is stated as a planned data element rather than as a released data type: "
                                 "it is not one of the listed data types."),
    ("splits", "split_details", "This is recorded as a planned provision: no source reports the holdout set as available."),
    ("splits", "split_details", "Both statements are prospective on that page."),
])
def test_presence_disclaimers(container, key, text):
    rec = record(**{container: [{"name": "Entry", key: text}]})
    assert f"/{container}/0" in flagged(rec)


@pytest.mark.parametrize("container,text", [
    # the shapes the naive lexicon hit in the committed corpus
    ("splits", "Recommended splits are provided as a file rather than as physically separated distributions."),
    ("instances", "Per-feature counts are given under distribution_formats rather than as the instance substrate."),
    ("creators", "Those individuals are recorded as study personnel rather than as creators of the dataset."),
    ("creators", "A colleague is named as principal investigator of the study rather than as an individual creator."),
    ("creators", "Named as a co-corresponding author rather than as the project principal investigator."),
    ("instances", "All instances are part of the same prospective data generation project."),
    ("creators", "None of these map onto a CRediT taxonomy term, so credit_roles is left absent."),
    # a role word in scope, but the clause is about other people
    ("data_collectors", "The page describes the process without naming the individual roles of the collecting staff."),
    ("maintainers", "No source names a role for the member institutions."),
])
def test_role_or_presence_wording_about_something_else_is_not_flagged(container, text):
    rec = record(**{container: [{"name": "Entry", "description": text}]})
    assert flagged(rec) == {}


def test_contrast_is_flagged_when_the_sentence_is_about_the_member():
    rec = record(maintainers=[{"name": "Person A", "description": "Listed as a contact rather than as a maintainer."}])
    assert flagged(rec) == {"/maintainers/0": ["role.contrast"]}


def test_date_or_amount_caveat_is_not_flagged():
    """The false-positive guard: a caveat about a period, a date or an amount."""
    for text in ("The grant period is not stated.",
                 "The start date of this member's role is not stated.",
                 "The funding amount for this collector's role is not stated."):
        rec = record(data_collectors=[{"name": "Entry", "collector_details": text}])
        out = sd.scan(rec, LEXICON)
        assert out["flags"] == [], text
    guarded = sd.scan(record(data_collectors=[{"name": "Entry", "collector_details":
                                               "The start date of this member's role is not stated."}]), LEXICON)["guarded"]
    assert [(g["path"], g["guard"]) for g in guarded] == [("/data_collectors/0", "date_amount")]
    assert flagged(record(data_collectors=[{"name": "Entry",
                                            "collector_details": "The role of this member is not stated."}])) \
        == {"/data_collectors/0": ["role.passive_not_stated"]}


def test_attribute_and_subrole_caveats_are_guarded_not_flagged():
    rec = record(creators=[
        {"name": "Entry", "source_caveats": "No source assigns CRediT contributor roles to the creator."},
        {"name": "Other", "source_caveats": "The bundle does not state a principal investigator role for her."}])
    out = sd.scan(rec, LEXICON)
    assert out["flags"] == []
    assert sorted(g["guard"] for g in out["guarded"]) == ["attribute", "subrole"]


@pytest.mark.parametrize("text", [
    "No source assigns her a principal investigator role.",
    "The sources do not assign her a principal investigator role.",
    "The sources do not state whether she holds the principal investigator role.",
    "The sources do not identify her as the corresponding author.",
    "No source names her as the corresponding author.",
])
def test_a_narrower_subrole_after_a_verb_cue_is_guarded(text):
    """A cue that stops at its verb has the sub-role after it (#3080): the
    cue-reading guard could never see it."""
    out = sd.scan(record(creators=[{"name": "Entry", "description": text}]), LEXICON)
    assert out["flags"] == [], text
    assert [g["guard"] for g in out["guarded"]] == ["subrole_object"], text


def test_the_subrole_object_is_read_only_up_to_a_conjunction():
    """The corpus shape: the role disclaimer in the first conjunct still
    flags, the principal-investigator caveat in the second is guarded; and
    a sub-role coordinated after the container's own role is not its object."""
    both = ("The sources state no contribution role for this person and do not identify them "
            "as a principal investigator on the award.")
    out = sd.scan(record(creators=[{"name": "Entry", "description": both}]), LEXICON)
    assert [[h["rule"] for h in f["hits"]] for f in out["flags"]] == [["role.states_no_role"]]
    assert [(g["rule"], g["guard"]) for g in out["guarded"]] == [("role.assignment_negated", "subrole_object")]
    coordinated = "The sources do not state whether she is a creator or only the contact for the award."
    assert flagged(record(creators=[{"name": "Entry", "description": coordinated}])) == {
        "/creators/0": ["role.not_stated_who"]}


@pytest.mark.parametrize("text", [
    "Which category of maintainer this contact represents is not stated.",
    "The maintainer role of this contact is not stated.",
    "The sources do not state this contact's role.",
])
def test_this_contact_is_the_member_not_a_narrower_subrole(text):
    """'this contact' is the member's self-reference; a guard reads it
    blanked (#3080). 'a contact role for this person' still names a sub-role."""
    assert "/maintainers/0" in flagged(record(maintainers=[{"name": "Entry", "description": text}])), text
    out = sd.scan(record(maintainers=[{"name": "Entry", "description":
                                       "The sources do not state a contact role for this person."}]), LEXICON)
    assert out["flags"] == [] and [(g["guard"], g["term"]) for g in out["guarded"]] == [("subrole", "contact")]


@pytest.mark.parametrize("container,text,term", [
    ("maintainers", "The maintainer's address is not stated.", "address"),
    ("data_collectors", "The collector's address is not stated.", "address"),
    ("maintainers", "The postal address of this maintainer is not given in any source.", "address"),
    ("creators", "This creator's department is not stated.", "department"),
])
def test_a_singular_address_or_a_department_is_an_attribute(container, text, term):
    """#3081: the attribute guard matched only the plural 'addresses'."""
    out = sd.scan(record(**{container: [{"name": "Entry", "description": text}]}), LEXICON)
    assert out["flags"] == [], text
    assert [(g["guard"], g["term"]) for g in out["guarded"]] == [("attribute", term)]


def test_the_study_design_is_not_the_members_presence():
    rec = record(instances=[{"name": "Entry", "description": "The study is prospective."}])
    out = sd.scan(rec, LEXICON)
    assert out["flags"] == [] and [g["guard"] for g in out["guarded"]] == ["design"]


def test_only_the_members_own_narrative_leaves_are_read():
    rec = record(creators=[{"name": "The slide does not assign this member a project title",
                            "affiliations": [{"name": "Org", "description":
                                              "The slide does not assign this member a project title."}]}])
    assert flagged(rec) == {}


def test_nested_dataset_containers_are_read_with_their_pointer():
    rec = record(resources=[record(creators=[
        {"name": "Person A", "notes": "The slide does not assign this member a role."}])])
    assert list(flagged(rec)) == ["/resources/0/creators/0"]


# ------------------------------------------------------------------ scoping
def outcomes(container, text, name="Entry"):
    """Each cue match in one member's description: (rule, outcome, reason)."""
    out = sd.scan(record(**{container: [{"name": name, "description": text}]}), LEXICON)
    rows = [(h["rule"], "flag", None) for f in out["flags"] for h in f["hits"]]
    rows += [(g["rule"], "guarded", g["guard"]) for g in out["guarded"]]
    return rows + [(o["rule"], "out_of_scope", o["reason"]) for o in out["out_of_scope"]]


@pytest.mark.parametrize("text,rule", [
    ("Whether the listing contains a typographical error is not stated.", "role.passive_not_stated"),
    ("The source does not indicate whether this is a typographical error.", "role.not_stated_who"),
])
def test_a_role_cue_needs_a_role_term_in_its_clause(text, rule):
    """The role scope decides these alone: no guard term, no other subject (#3084)."""
    assert outcomes("maintainers", text) == [(rule, "out_of_scope", "no_role_term")]


def test_a_presence_cue_needs_a_self_reference_or_a_presence_term():
    """The presence scope decides the first alone; a presence term in the
    clause licenses the second with no self-reference (#3084)."""
    assert outcomes("instances", "The raw audio was recorded as planned.") == [
        ("presence.recorded_as_planned", "out_of_scope", "no_self_or_presence_term")]
    assert outcomes("splits", "No source reports the holdout set as available.") == [
        ("presence.none_reports_available", "flag", None)]


def test_scope_is_read_in_the_clause_holding_the_cue():
    """Clause segmentation (#3084): another subject in an earlier clause does
    not reject a cue, and a role verb in an earlier clause does not license one."""
    assert outcomes("maintainers", "Those individuals are listed on the team page, "
                                   "and the role of this maintainer is not stated.") == [
        ("role.passive_not_stated", "flag", None)]
    assert outcomes("maintainers", "This person maintains the portal, "
                                   "but whether the listing has a typographical error is not stated.") == [
        ("role.passive_not_stated", "out_of_scope", "no_role_term")]


@pytest.mark.parametrize("container,text,expected", [
    ("splits", "This split is balanced by site, but the raw images are not released.", "out_of_scope"),
    ("variables", "It is computed from the device stream, but the underlying minute-level data are not yet available.",
     "out_of_scope"),
    ("instances", "Listed in the file manifest, and the raw audio waveforms are not released.", "out_of_scope"),
    ("variables", "It is computed from the device stream, but is not yet available.", "flag"),
    ("variables", "This variable is derived from the stream, and it has not been released.", "flag"),
])
def test_an_earlier_self_reference_counts_only_for_a_clause_without_its_own_subject(container, text, expected):
    """#3082: a self-reference in an earlier clause licenses a cue only when
    the cue's clause elides its subject; 'the raw images are not released'
    is about the images."""
    assert [(rule, outcome) for rule, outcome, _ in outcomes(container, text)] == [
        ("presence.not_yet_released", expected)]


def test_a_none_scope_cue_counts_whatever_its_subject():
    """#3083: presence.prospective_predicate has no subject condition, so it
    flags a caveat about something else that is prospective. Pinned so a
    change to that contract is a deliberate one."""
    assert outcomes("instances", "The consent forms are prospective.") == [
        ("presence.prospective_predicate", "flag", None)]


def test_the_members_own_name_is_a_self_reference():
    """#3086: in full always, by its last word only when that word has at
    least four letters."""
    assert outcomes("creators", "Jane Doe is not a creator of the dataset.", name="Jane Doe") == [
        ("role.not_the_role", "flag", None)]
    assert outcomes("creators", "Doe is not a creator of the dataset.", name="Jane Doe") == [
        ("role.not_the_role", "out_of_scope", "no_self_reference")]
    out = sd.scan(record(creators=[{"name": "Jane Dough", "description": "Dough is not a creator of the dataset."}]),
                  LEXICON)
    assert [h["scope"] for f in out["flags"] for h in f["hits"]] == ["Dough"]


# ------------------------------------------------------------------ check (b)
def receipt(*pairs):
    return {"chunks": [{"id": "c001", "status": "extracted",
                        "extracted": [{"slot": s, "snippet": t} for s, t in pairs]}]}


def test_role_predicate_miss_with_no_lexicon_hit_is_bucket_b_only():
    rec = record(creators=[{"name": "Person A"}, {"name": "Person B"}],
                 maintainers=[{"name": "Person C", "maintainer_details": "Listed under Contact Us."}])
    rcpt = receipt(("creators[0].name", "Principal investigator: Person A"),
                   ("maintainers[0]", "Contact Us\nPerson C, Program Manager"))
    assert sd.scan(rec, LEXICON)["flags"] == []
    out = sd.role_predicates(rec, rcpt, LEXICON)
    assert out["supported"] == 1
    assert [(f["path"], f["reason"]) for f in out["flags"]] == [
        ("/creators/1", "no_receipt"), ("/maintainers/0", "no_role_predicate")]
    hosted = sd.role_predicates(rec, receipt(("maintainers[0].name", "The data are hosted and curated by Person C")), LEXICON)
    assert "/maintainers/0" not in {f["path"] for f in hosted["flags"]}


def test_bucket_b_is_reported_apart_from_the_lexicon_diff():
    rec = record(maintainers=[{"name": "Person C", "maintainer_details": "Listed under Contact Us."}])
    out = sd.diff(rec, copy.deepcopy(rec), receipt=receipt(("maintainers[0]", "Person C, Program Manager")),
                  lexicon=LEXICON)
    assert out["lexicon_diff"]["rows"] == []
    assert [(r["path"], r["classification"]) for r in out["role_predicate_diff"]["rows"]] == [
        ("/maintainers/0", "role_predicate_retained")]


# ------------------------------------------------------------------ the diff
DISCLAIMER = "No source states who maintains the dataset."


def maintainer(caveat=True):
    member = {"name": "Person C", "maintainer_details": "Listed under Contact Us."}
    if caveat:
        member["source_caveats"] = DISCLAIMER
    return member


def finding(**extra):
    return {"severity": "medium", "record": "full", "slot": "maintainers", "issue": "synthetic",
            "evidence": [{"artifact": "original_full", "path": "/description", "op": "contains", "quote": "x"}],
            **extra}


def test_caveat_deleted_while_the_entry_is_kept_is_retained():
    """The v3 shape: a finding names only the caveat, reconciliation deletes
    the caveat and keeps the entry. Deleting the disclaimer disposes of nothing."""
    original = record(maintainers=[maintainer()])
    final = record(maintainers=[maintainer(caveat=False)])
    audit = {"findings": [finding(review_paths=["/maintainers/0/source_caveats"])]}
    out = sd.diff(original, final, audit=audit, lexicon=LEXICON)
    row = out["lexicon_diff"]["rows"][0]
    assert (row["path"], row["classification"], row["final_path"]) == (
        "/maintainers/0", "self_disclaimed_retained", "/maintainers/0")
    assert row["still_flagged_in_final"] is False
    assert out["final"]["flags"] == []
    kept = sd.diff(original, copy.deepcopy(original), audit=audit, lexicon=LEXICON)["lexicon_diff"]["rows"][0]
    assert (kept["classification"], kept["still_flagged_in_final"]) == ("self_disclaimed_retained", True)


def test_a_keep_named_by_a_finding_is_not_retained():
    original = record(maintainers=[maintainer()])
    audit = {"findings": [finding(slot="maintainers", review_paths=["/maintainers/0/name"])]}
    out = sd.diff(original, copy.deepcopy(original), audit=audit, lexicon=LEXICON)
    row = out["lexicon_diff"]["rows"][0]
    assert (row["classification"], row["findings_naming_member"]) == ("named_by_finding", [0])
    evidence = {"findings": [finding(evidence=[{"artifact": "original_full", "path": "/maintainers/0",
                                                "op": "contains", "quote": "Person C"}])]}
    assert classes(sd.diff(original, copy.deepcopy(original), audit=evidence, lexicon=LEXICON)) == {
        "/maintainers/0": "named_by_finding"}
    core_only = {"findings": [finding(evidence=[{"artifact": "original_core", "path": "/maintainers/0",
                                                 "op": "contains", "quote": "Person C"}])]}
    assert classes(sd.diff(original, copy.deepcopy(original), audit=core_only, lexicon=LEXICON)) == {
        "/maintainers/0": "self_disclaimed_retained"}


def test_declared_removal_is_removal_declared_and_never_retained():
    original = record(maintainers=[maintainer()])
    audit = {"findings": [finding(review_paths=["/maintainers/0/name"],
                                  remove_relationship={"path": "/maintainers/0", "identity": "/name"})]}
    gone = sd.diff(original, record(), audit=audit, lexicon=LEXICON)
    row = gone["lexicon_diff"]["rows"][0]
    assert (row["classification"], row["final_path"], row["findings_declaring_removal"]) == (
        "removal_declared", None, [0])
    kept = sd.diff(original, copy.deepcopy(original), audit=audit, lexicon=LEXICON)
    row = kept["lexicon_diff"]["rows"][0]
    assert (row["classification"], row["final_path"]) == ("removal_declared", "/maintainers/0")
    assert kept["lexicon_diff"]["counts"]["self_disclaimed_retained"] == 0


def test_a_removal_declared_on_an_ancestor_covers_the_member():
    """#3087: `remove_relationship` on the container selects every member."""
    original = record(maintainers=[maintainer()])
    audit = {"findings": [finding(remove_relationship={"path": "/maintainers"})]}
    for final in (record(), copy.deepcopy(original)):
        row = sd.diff(original, final, audit=audit, lexicon=LEXICON)["lexicon_diff"]["rows"][0]
        assert (row["classification"], row["findings_declaring_removal"]) == ("removal_declared", [0])
    sibling = {"findings": [finding(remove_relationship={"path": "/maintainer"})]}
    assert classes(sd.diff(original, record(), audit=sibling, lexicon=LEXICON)) == {"/maintainers/0": "removed"}


def test_identity_unresolved_precedes_named_by_finding():
    """#3087: an entry that cannot be followed is identity_unresolved even
    when a finding names it; remap_path reports it ambiguous (two final
    entries tie on overlap, neither at its index)."""
    split = {"split_details": "This split is recorded as a planned provision.", "size": "10"}
    original = record(splits=[split])
    final = record(splits=[{"split_details": "Other.", "size": "0"},
                           {"split_details": split["split_details"], "size": "99"},
                           {"split_details": "Other.", "size": "10"}])
    audit = {"findings": [finding(slot="splits", review_paths=["/splits/0"])]}
    row = sd.diff(original, final, audit=audit, lexicon=LEXICON)["lexicon_diff"]["rows"][0]
    assert (row["classification"], row["identity_basis"], row["findings_naming_member"]) == (
        "identity_unresolved", "ambiguous", [0])


def test_identity_is_followed_across_reordering_and_removal():
    a = {"name": "Person A", "notes": "The slide does not assign this member a role."}
    b = {"name": "Person B", "notes": "Principal investigator on the award."}
    c = {"name": "Person C", "notes": "The slide does not assign this member a title."}
    out = sd.diff(record(creators=[a, b, c]), record(creators=[b, a]), lexicon=LEXICON)
    rows = {r["path"]: (r["classification"], r["final_path"], r["identity_basis"])
            for r in out["lexicon_diff"]["rows"]}
    assert rows == {"/creators/0": ("self_disclaimed_retained", "/creators/1", "by_name"),
                    "/creators/2": ("removed", None, "removed")}
    assert out["final_only"] == []
    # read at the entry's final path, not its original one (#3085)
    assert [r["still_flagged_in_final"] for r in out["lexicon_diff"]["rows"]] == [True, False]


def test_a_container_emptied_or_nulled_in_the_final_is_removed():
    original = record(maintainers=[maintainer()])
    for final in (record(maintainers=[]), record(maintainers=None), record()):
        assert classes(sd.diff(original, final, lexicon=LEXICON)) == {"/maintainers/0": "removed"}


def test_a_nested_member_under_a_nulled_ancestor_is_removed():
    """#3088: nulling or emptying any list above the member removes it, as
    nulling its own container does."""
    original = record(resources=[record(maintainers=[maintainer()])])
    for final in (record(resources=None), record(resources=[]), record(),
                  record(resources=[record(maintainers=None)])):
        assert classes(sd.diff(original, final, lexicon=LEXICON)) == {
            "/resources/0/maintainers/0": "removed"}, final


def test_a_flag_new_in_the_final_is_reported_final_only():
    out = sd.diff(record(maintainers=[maintainer(caveat=False)]), record(maintainers=[maintainer()]),
                  lexicon=LEXICON)
    assert out["lexicon_diff"]["rows"] == [] and out["final_only"] == ["/maintainers/0"]


# ------------------------------------------------------------------ instrument
def test_lexicon_bytes_are_pinned_per_version():
    raw = sd.LEXICON_PATH.read_bytes()
    assert LEXICON.version in LEXICON_PINS, "a new lexicon version needs a pin"
    assert hashlib.sha256(raw).hexdigest() == LEXICON_PINS[LEXICON.version], \
        "the lexicon changed without a version bump"
    assert sd.LEXICON_PATH.name == f"self_disclaimed_v{LEXICON.version}.yaml"
    assert LEXICON.describe() == {"path": sd.LEXICON_RESOURCE, "version": LEXICON.version,
                                  "sha256": LEXICON_PINS[LEXICON.version]}


def test_lexicon_is_generic():
    text = sd.LEXICON_PATH.read_text(encoding="utf-8").lower()
    for token in ("chorus", "ai-readi", "ai_readi", "voice", "cm4ai", "bridge2ai", "fairhub",
                  "physionet", "reporter", "nih", "webinar"):
        assert token not in text, token


def test_registered_containers_and_fields_are_schema_slots():
    from data_sheets_schema.resources import resource_path
    from data_sheets_schema.schema_view import shared_view
    view = shared_view(resource_path("src/data_sheets_schema/schema/data_sheets_schema_all.yaml"))
    for name, container in LEXICON.containers.items():
        slot = view.induced_slot(name, "Dataset")
        assert slot.multivalued and slot.range in view.all_classes(), name
        declared = {s.name for s in view.class_induced_slots(slot.range)}
        assert container.narrative_fields - {"notes"} <= declared | {"notes"}, name
        assert container.placement_fields <= declared, name


def test_modules_the_audit_imports_do_not_import_this_one():
    """The audit and native import closures stay as registered (#2913)."""
    from data_sheets_schema import (anonymous_removals, audit_grammar, evidence_assertions, receipts,
                                    source_review)
    for module in (evidence_assertions, anonymous_removals, audit_grammar, source_review, receipts):
        tree = ast.parse(inspect.getsource(module))
        names = [a.name for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))
                 for a in n.names] + [n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
        assert not any("self_disclaimed" in n for n in names), module.__name__


# ------------------------------------------------------------------ CLI
def write(path: Path, value, *, as_json=False) -> Path:
    path.write_text(json.dumps(value) if as_json else yaml.safe_dump(value, sort_keys=False), encoding="utf-8")
    return path


def test_cli_prints_json_and_never_gates(tmp_path):
    from data_sheets_schema.cli.review import review
    original = write(tmp_path / "original.yaml", record(maintainers=[maintainer()]))
    final = write(tmp_path / "final.yaml", record(maintainers=[maintainer(caveat=False)]))
    audit = write(tmp_path / "audit.json", {"findings": [finding()]}, as_json=True)
    rcpt = write(tmp_path / "receipt.yaml", receipt(("maintainers[0]", "Person C, Program Manager")))
    result = CliRunner().invoke(review, ["self-disclaimed", "--original", str(original), "--final", str(final),
                                         "--audit", str(audit), "--receipt", str(rcpt)])
    assert result.exit_code == 0, result.output
    out = json.loads(result.output)
    assert (out["instrument"], out["gating"]) == (sd.INSTRUMENT, False)
    assert out["lexicon"]["sha256"] == LEXICON_PINS[1]
    assert out["inputs"]["original"]["sha256"] == hashlib.sha256(original.read_bytes()).hexdigest()
    assert out["counts"]["lexicon_diff"]["self_disclaimed_retained"] == 1
    assert out["counts"]["role_predicate_diff"]["role_predicate_retained"] == 1
    alone = CliRunner().invoke(review, ["self-disclaimed", "--original", str(original)])
    assert alone.exit_code == 0 and json.loads(alone.output)["counts"]["original_flags"] == 1


def test_cli_refuses_an_audit_without_a_final_and_an_ambiguous_record(tmp_path):
    from data_sheets_schema.cli.review import review
    original = write(tmp_path / "original.yaml", record())
    audit = write(tmp_path / "audit.json", {"findings": []}, as_json=True)
    result = CliRunner().invoke(review, ["self-disclaimed", "--original", str(original), "--audit", str(audit)])
    assert result.exit_code != 0 and "final record" in result.output
    dup = tmp_path / "dup.yaml"
    dup.write_text("name: a\nname: b\n", encoding="utf-8")
    result = CliRunner().invoke(review, ["self-disclaimed", "--original", str(dup)])
    assert result.exit_code != 0 and "duplicate" in result.output and "original" in result.output
