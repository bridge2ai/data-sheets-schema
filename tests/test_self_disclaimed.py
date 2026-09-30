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
#: v1 stays loadable for replay; this code reads it as v1's own code did.
V1 = sd.load_lexicon(sd.lexicon_path(1))

#: Pins on the lexicon's exact bytes, one per version. Changing the file
#: without a version bump fails here; so does bumping without a pin. v1 was
#: revised in review before it first merged (#3029), so this PR's commits
#: carry seven earlier byte versions under `version: 1`:
#:   9b1f536ba02afc9971bbe9e28da316ea1c3c90e356bdbcc2c200400259521b04 (e00711d21, first commit)
#:   728e4e8b87aeefce7c2de27541392e53ee11cbf8d74fe7587309abf227a24a6d (387e20653, review round 1)
#:   14428534895e1cec840dde5eec6eb0d06bbeac50e89007573611d89c79d14c35 (cf3d16cb3, review round 2)
#:   56c9abda1c6fea3dcbd5b44372e2e85a5fc38d50c65bffdad4f8f3791f1b54e4 (df35537aa, review round 2)
#:   3b2949e29c7aebef79c6e77894d735c6fa2ce1a0ae8800463374d63fe45a5f3a (7e327b512, review round 3)
#:   626edd8708b519819c3be5f999e638cd18467b5ea857b1beb2fd2b854ab0f0a6 (5705a4f3f, review round 4)
#:   d1628c7e4b574b40c59113969747fc17b7155205668a1d48f28fbeb684994f4c (9607a6416, review round 5)
#: Every output names the sha it ran under, and no committed output, record
#: or note cites any of them (#3161). v2 (#3131, #3244, #3261, #3273) is a
#: new file beside v1, whose bytes are unchanged. v2 was revised in review
#: before it first merged, so this PR's commits carry one earlier byte
#: version under `version: 2`:
#:   6d232ed346308bd7cf97b262aff47cefb869673c55d72fb994411f2c2d34e09a (389436318, first commit)
LEXICON_PINS = {1: "15a1b7ddfa9fa0677d1ab1075dfd2485b5920c32a59cf23d6108fb94b7afcb3a",
                2: "520e2779966f84a827ef0b6f9fdab3a6457cf85cce177a13291661453918dd7d"}


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


@pytest.mark.parametrize("container,text", [
    ("maintainers", "No source identifies the listed contact as the maintainer of the dataset."),
    ("maintainers", "The sources do not identify the program contact as a maintainer."),
    ("maintainers", "No source names this person as the maintainer rather than as a contact."),
    ("maintainers", "The sources do not identify the contact as the dataset's maintainer."),
    ("maintainers", "The sources do not state whether the contact maintains the dataset."),
    ("maintainers", "The contact's role is not stated."),
    ("creators", "The sources do not identify the contact as an author of the dataset."),
    ("creators", "No source names the corresponding contact as a creator."),
])
def test_the_contact_named_as_the_member_is_not_a_subrole(container, text):
    """#3162: 'the contact' as a noun phrase of its own is the member, and the
    role disclaimed is the container's. A sub-role counts only as a
    complement or as the modifier of a role noun or of a principal
    investigator."""
    out = sd.scan(record(**{container: [{"name": "Entry", "description": text}]}), LEXICON)
    assert [f["path"] for f in out["flags"]] == [f"/{container}/0"] and out["guarded"] == [], text


def test_a_passive_cue_is_guarded_by_a_subrole_in_its_clause():
    """#3164: the passive cue's sub-role guard, and the sub-role shapes it
    reads: a modifier of a role noun or of a principal investigator, and a
    complement."""
    for text, term in (("The principal investigator role of this person is not stated.", "principal investigator"),
                       ("Roles other than that of the contact PI are not specified.", "contact"),
                       ("Her creator role, as principal investigator, is not specified.", "as principal investigator")):
        out = sd.scan(record(creators=[{"name": "Entry", "description": text}]), LEXICON)
        assert out["flags"] == [], text
        assert [(g["rule"], g["guard"], g["term"]) for g in out["guarded"]] == [
            ("role.passive_not_stated", "subrole_in_clause", term)], text


@pytest.mark.parametrize("container,text", [
    ("creators", "The website does not name this person as a creator of the dataset."),
    ("creators", "The project homepage does not state who created the dataset."),
    ("maintainers", "The website does not state who maintains the dataset."),
    ("maintainers", "The website does not name this maintainer."),
    ("splits", "This split is not yet available on the project website."),
    ("creators", "The 2024 slide does not assign this member a role."),
    ("creators", "The funding announcement does not name her as an author."),
    ("creators", "No source on the website names this person as a creator."),
    ("creators", "The number of sources is small and none names this person as a creator."),
    ("creators", "The sources do not name her as an author and give no ORCID for her."),
    # a passive cue's object is its subject and its `as` complement
    ("creators", "This person is not recorded as a creator because the website omits her."),
])
def test_the_cited_source_or_incidental_context_is_not_what_is_unstated(container, text):
    """#3158: the date, amount and attribute guards read the cue's object
    (after an active cue, before a passive one), so the source a sentence
    cites and context outside the object do not suppress the hit."""
    out = sd.scan(record(**{container: [{"name": "Entry", "description": text}]}), LEXICON)
    assert [f["path"] for f in out["flags"]] == [f"/{container}/0"] and out["guarded"] == [], text


@pytest.mark.parametrize("container,text,rule", [
    ("splits", "This split, planned for 2025, is not yet released.", "presence.not_yet_released"),
    ("splits", "This split, the 2024 holdout, has not been released.", "presence.not_yet_released"),
    ("splits", "Per the 2024 slide, this split is not yet released.", "presence.not_yet_released"),
    ("variables", "This variable, added in the 2023 revision, is not one of the released fields.",
     "presence.not_member_of"),
    ("creators", "Her role, per the 2024 slide, is not stated.", "role.passive_not_stated"),
])
def test_a_date_modifying_a_passive_subject_is_not_what_is_unstated(container, text, rule):
    """#3210: a passive cue's object is its subject, without an appositive
    or what a comma sets before it, so a year that only modifies the member
    does not guard the hit."""
    out = sd.scan(record(**{container: [{"name": "Entry", "description": text}]}), LEXICON)
    assert out["guarded"] == [], text
    assert [h["rule"] for f in out["flags"] for h in f["hits"]] == [rule], text


@pytest.mark.parametrize("text", [
    "This split's 2025 release date is not yet available.",
    "Per the codebook, this split's 2025 release date, as listed, is not yet available.",
])
def test_a_date_heading_a_passive_subject_is_still_guarded(text):
    """#3210: the subject keeps the date where the date is what is unstated."""
    out = sd.scan(record(splits=[{"name": "Entry", "description": text}]), LEXICON)
    assert out["flags"] == [], text
    assert [(g["rule"], g["guard"], g["term"]) for g in out["guarded"]] == [
        ("presence.not_yet_released", "date_amount", "2025")], text


@pytest.mark.parametrize("before,subject", [
    ("This split, planned for 2025, ", "This split"),
    ("Per the 2024 slide, this split ", " this split "),
    ("Per the codebook, its date, as listed, ", " its date"),
    ("Planned for 2025, ", "Planned for 2025"),
    ("Its date ", "Its date "),
])
def test_the_passive_subject_span(before, subject):
    s0, s1 = sd._subject(before)
    assert before[s0:s1] == subject


@pytest.mark.parametrize("text,guard,term", [
    # the object names the role, and the attribute is in it
    ("No source assigns CRediT contributor roles to the creator, so credit_roles is left unpopulated.",
     "attribute", "CRediT"),
    ("The sources do not state credit roles for the dataset itself.", "attribute", "credit"),
    # a passive cue's `as` complement
    ("These are not recorded as creator affiliations because the page lists them elsewhere.",
     "attribute", "affiliations"),
    # the licensing role lies outside the object, so the whole clause is read
    ("The preprint's author affiliations instead name another university and do not name the institute.",
     "attribute", "affiliations"),
    ("No source names a further creating team, assigns CRediT roles, or states which individuals did the work.",
     "attribute", "CRediT"),
    # a passive cue's subject
    ("The start date of this member's role is not stated.", "date_amount", "start"),
])
def test_a_date_or_attribute_in_the_object_is_still_guarded(text, guard, term):
    """#3158: the corpus's guarded shapes stay guarded under the object reading."""
    out = sd.scan(record(creators=[{"name": "Entry", "description": text}]), LEXICON)
    assert out["flags"] == [], text
    assert [(g["guard"], g["term"]) for g in out["guarded"]] == [(guard, term)], text


@pytest.mark.parametrize("container,text,rule", [
    ("creators", "The sources do not credit this person as a creator of the dataset.", "role.assignment_negated"),
    ("creators", "The documents did not credit her as an author.", "role.assignment_negated"),
    ("maintainers", "The sources do not credit this organization as a maintainer.", "role.assignment_negated"),
    ("creators", "None of the sources credit this person as a creator.", "role.none_assigns"),
])
def test_the_cue_verb_credit_is_not_the_credit_attribute(container, text, rule):
    """#3157: the attribute guard's 'credit' (CRediT, credit_roles) is never
    read in the cue's own verb."""
    assert flagged(record(**{container: [{"name": "Entry", "description": text}]})) == {f"/{container}/0": [rule]}


@pytest.mark.parametrize("container,text", [
    ("creators", "The slide does not name this member among the creators."),
    ("creators", "The sources do not name this individual among the authors."),
    ("creators", "The paper does not credit this member among its authors."),
    ("maintainers", "The page does not name this member of staff as a maintainer."),
])
def test_the_members_own_self_reference_is_not_another_subject(container, text):
    """#3156: 'this member' / 'this individual' is blanked before the
    other-subject check, as it is for the guards."""
    assert flagged(record(**{container: [{"name": "Entry", "description": text}]})) == {
        f"/{container}/0": ["role.assignment_negated"]}, text
    assert outcomes(container, text.replace("this member", "individual consortium members")
                    .replace("this individual", "individual consortium members")) == [
        ("role.assignment_negated", "out_of_scope", "other_subject")], text


@pytest.mark.parametrize("container,text,term", [
    ("maintainers", "The maintainer's address is not stated.", "address"),
    ("data_collectors", "The collector's address is not stated.", "address"),
    ("maintainers", "The postal address of the maintainer is not given in any source.", "address"),
    ("creators", "The creator's department is not stated.", "department"),
])
def test_a_singular_address_or_a_department_is_an_attribute(container, text, term):
    """#3081: the attribute guard matched only the plural 'addresses'. The
    owner is "the maintainer", not the member's own self-reference: "this
    creator's department" puts nothing in role scope at all (#3251)."""
    out = sd.scan(record(**{container: [{"name": "Entry", "description": text}]}), LEXICON)
    assert out["flags"] == [], text
    assert [(g["guard"], g["term"]) for g in out["guarded"]] == [("attribute", term)]


def test_the_study_design_is_not_the_members_presence():
    """v1 guards it as the study's design; v2's subject scope finds no
    member subject first (#3131)."""
    rec = record(instances=[{"name": "Entry", "description": "The study is prospective."}])
    out = sd.scan(rec, V1)
    assert out["flags"] == [] and [g["guard"] for g in out["guarded"]] == ["design"]
    assert outcomes("instances", "The study is prospective.") == [
        ("presence.prospective_predicate", "out_of_scope", "no_member_subject")]


def test_only_the_members_own_narrative_leaves_are_read():
    """A non-narrative leaf and a nested object's prose are not read. The
    non-narrative value is one that flags when it is read (#3265): `name`
    would not do, since the member's own name is masked as a
    self-reference and its cue then names no role."""
    text = "The source does not name her as a creator."
    assert flagged(record(creators=[{"name": "Person A", "description": text}])) == {
        "/creators/0": ["role.assignment_negated"]}
    rec = record(creators=[{"name": "Person A", "title": text,
                            "affiliations": [{"name": "Org", "description": text}]}])
    assert flagged(rec) == {}


def test_nested_dataset_containers_are_read_with_their_pointer():
    rec = record(resources=[record(creators=[
        {"name": "Person A", "notes": "The slide does not assign this member a role."}])])
    assert list(flagged(rec)) == ["/resources/0/creators/0"]


# ------------------------------------------------------------------ scoping
def outcomes(container, text, name="Entry", lexicon=LEXICON, **leaves):
    """Each cue match in one member's description: (rule, outcome, reason)."""
    out = sd.scan(record(**{container: [{"name": name, **leaves, "description": text}]}), lexicon)
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


@pytest.mark.parametrize("container,text,expected", [
    ("creators", "The abstract does not state the title of the award.",
     [("role.no_role_stated", "title of the award")]),
    ("creators", "The award notice states no title for the project.",
     [("role.states_no_role", "title for the project")]),
    ("maintainers", "The page does not give the position of the server.",
     [("role.assignment_negated", "position of the server"),
      ("role.no_role_stated", "position of the server")]),
    ("data_collectors", "The protocol does not specify the category of device used.",
     [("role.no_role_stated", "category of device used")]),
    # a role verb elsewhere in the clause does not make another thing's title the member's
    ("creators", "The abstract, authored by her, does not state the title of the award.",
     [("role.no_role_stated", "title of the award")]),
])
def test_an_assignment_noun_another_thing_owns_is_not_the_members_role(container, text, expected):
    """#3209: the cue of role.no_role_stated and role.states_no_role always
    holds an assignment noun, so the role scope could not fail for them.
    A title, position or category owned by another thing puts nothing in
    scope, and a cue whose own noun is another thing's is out of scope."""
    out = sd.scan(record(**{container: [{"name": "Entry", "description": text}]}), LEXICON)
    assert out["flags"] == [] and out["guarded"] == [], text
    assert [(o["rule"], o["reason"], o["term"]) for o in out["out_of_scope"]] == [
        (rule, "assignment_noun_of_other", term) for rule, term in expected], text


@pytest.mark.parametrize("container,text,rule", [
    ("creators", "The sources do not state an individual role for this person.", "role.no_role_stated"),
    ("creators", "The sources state no contribution role for this person.", "role.states_no_role"),
    ("creators", "The sources do not state a role for her in the dataset.", "role.no_role_stated"),
    ("creators", "The sources do not state her role.", "role.no_role_stated"),
    ("creators", "The sources do not state a role for the dataset.", "role.no_role_stated"),
    ("creators", "The sources do not state the role of Jane Parker.", "role.no_role_stated"),
    ("maintainers", "The sources do not state which category of maintainer this contact represents.",
     "role.no_role_stated"),
    ("maintainers", "The sources do not state which category of maintainer applies.", "role.no_role_stated"),
])
def test_an_assignment_noun_the_member_owns_still_counts(container, text, rule):
    """#3209: the owner after `of`/`for` is the member's when it is one of
    its self-references or its name, a pronoun, a role term, or (after
    `for`) what a role is held in."""
    rec = record(**{container: [{"name": "Jane Parker", "description": text}]})
    assert flagged(rec) == {f"/{container}/0": [rule]}, text


def test_a_presence_cue_needs_a_self_reference_or_a_presence_term():
    """The presence scope decides the first alone; a presence term in the
    clause licenses the second with no self-reference (#3084)."""
    assert outcomes("instances", "The raw audio was recorded as planned.") == [
        ("presence.recorded_as_planned", "out_of_scope", "no_self_or_presence_term")]
    assert outcomes("splits", "No source reports the holdout set as available.") == [
        ("presence.none_reports_available", "flag", None)]


@pytest.mark.parametrize("container,text,expected", [
    ("splits", "This is recorded as a planned provision.",
     [("presence.recorded_as_planned", "This is"), ("presence.planned_element", "This is")]),
    ("instances", "It is listed as planned.", [("presence.recorded_as_planned", "It")]),
])
def test_a_presence_cue_is_licensed_by_a_self_reference_alone(container, text, expected):
    """#3163: the self-reference half of the presence scope. Neither text
    names a presence term, so only the self-reference licenses the cue."""
    out = sd.scan(record(**{container: [{"name": "Entry", "description": text}]}), LEXICON)
    assert [(h["rule"], h["scope"]) for f in out["flags"] for h in f["hits"]] == expected
    assert not LEXICON.containers[container].presence_scope.search(text)


@pytest.mark.parametrize("container,text,rule", [
    ("splits", "Unlike the planned splits for the next release, this split is complete.",
     "presence.planned_element"),
    ("splits", "The training set is fixed; a planned holdout set is described in the protocol.",
     "presence.planned_element"),
    ("variables", "Complete for all participants; planned measures from wave 2 are listed elsewhere.",
     "presence.planned_element"),
    ("instances", "Some planned data elements were dropped; this instance type is released.",
     "presence.planned_element"),
    # a presence term only inside a self-reference the comma rule rejects
    ("splits", "For this split, the data are recorded as planned.", "presence.recorded_as_planned"),
])
def test_a_presence_term_the_cue_spells_does_not_license_it(container, text, rule):
    """#3230: `presence.planned_element` ends on the planned noun, so the
    presence term it spells cannot be what puts its clause in scope; nor can
    a term inside the member's own self-reference."""
    assert outcomes(container, text) == [(rule, "out_of_scope", "no_self_or_presence_term")]


@pytest.mark.parametrize("container,text,rule,scope", [
    ("splits", "The holdout set is a planned provision.", "presence.planned_element", "holdout set"),
    ("splits", "The project abstract describes the holdout set as a planned provision.",
     "presence.planned_element", "holdout set"),
    ("splits", "This split is a planned split.", "presence.planned_element", "This split"),
    ("splits", "No source reports the holdout set as available.", "presence.none_reports_available",
     "holdout set"),
])
def test_a_presence_term_outside_the_cue_or_in_a_cue_object_still_licenses_it(container, text, rule, scope):
    """#3230: the corpus shape (the term outside the cue), a self-reference,
    and a cue that declares its object inside itself (`object: [cue]`)."""
    out = sd.scan(record(**{container: [{"name": "Entry", "description": text}]}), LEXICON)
    assert [(h["rule"], h["scope"]) for f in out["flags"] for h in f["hits"]] == [(rule, scope)], text


@pytest.mark.parametrize("container,text,term", [
    ("variables", "Two other variables are not part of the public release.", "other variables"),
    ("splits", "The remaining partitions are not one of the released files.", "The remaining partitions"),
    ("instances", "Those data types are not yet released.", "Those data types"),
    ("splits", "Another holdout set is not yet available.", "Another holdout set"),
])
def test_a_subject_naming_other_items_is_another_subject(container, text, term):
    """#3231: the other-subject rule covers other items of a presence
    container's kind, not only other people."""
    out = sd.scan(record(**{container: [{"name": "Entry", "description": text}]}), LEXICON)
    assert out["flags"] == []
    assert {(r["reason"], r["term"]) for r in out["out_of_scope"]} == {("other_subject", term)}, text


@pytest.mark.parametrize("container,text,rule", [
    ("splits", "Unlike the other splits, this split is not yet released.", "presence.not_yet_released"),
    ("instances", "It is not one of the listed data types.", "presence.not_member_of"),
    ("variables", "This variable is not part of the release, unlike the other variables.",
     "presence.not_member_of"),
])
def test_other_items_outside_the_subject_do_not_reject_the_member(container, text, rule):
    """#3231: the other-item check reads the cue's subject alone, so other
    items named as a contrast or as the reference set leave the member's
    own disclaimer counted."""
    assert outcomes(container, text) == [(rule, "flag", None)]


@pytest.mark.parametrize("container,text,rule", [
    ("creators", "These data sets list her as a contact but do not name her as a creator.",
     "role.assignment_negated"),
    ("creators", "The other data sets do not name her as a creator.", "role.assignment_negated"),
    ("maintainers", "Those columns do not identify this person as the maintainer.", "role.assignment_negated"),
    ("data_collectors", "The other instances of the survey do not name this person as a collector.",
     "role.assignment_negated"),
    ("creators", "Such fields do not state a role for this person.", "role.no_role_stated"),
])
def test_a_role_cues_cited_source_is_not_another_item(container, text, rule):
    """#3249: the other-item check is a presence container's. A role cue's
    subject is the source it cites, so a source named with a determiner and
    an item noun leaves the member's role disclaimer counted."""
    assert outcomes(container, text) == [(rule, "flag", None)], text


@pytest.mark.parametrize("text,term", [
    ("No source reports the other splits as available.", "the other splits"),
    ("No source reports those partitions as available.", "those partitions"),
    ("No source reports the remaining partitions as released.", "the remaining partitions"),
])
def test_an_other_item_in_a_cue_that_holds_its_object_is_another_subject(text, term):
    """#3250: `presence.none_reports_available` names the item it reports
    inside the cue; the other-item check reads that item, not the empty
    stretch before "No source"."""
    out = sd.scan(record(splits=[{"name": "Entry", "description": text}]), LEXICON)
    assert out["flags"] == [], text
    assert [(r["rule"], r["reason"], r["term"]) for r in out["out_of_scope"]] == [
        ("presence.none_reports_available", "other_subject", term)]


def test_the_cited_source_of_a_cue_that_holds_its_object_is_not_the_item():
    """#3250: the source "none of the other data sets" is outside the `item`
    group, so it does not reject the member's own presence disclaimer."""
    assert outcomes("splits", "None of the other sets reports the holdout set as available.") == [
        ("presence.none_reports_available", "flag", None)]


@pytest.mark.parametrize("text", [
    "No source from 2024 reports the holdout set as available.",
    "No source in the 2023 bundle reports the holdout set as available.",
    "No document dated 2025 lists the test set as released.",
])
def test_a_date_on_the_cited_source_does_not_guard_the_reported_item(text):
    """#3265: `presence.none_reports_available` declares its object as its
    `item` group, so the date/amount guard reads the reported item, not the
    source the cue cites."""
    assert outcomes("splits", text) == [("presence.none_reports_available", "flag", None)]


@pytest.mark.parametrize("text,term", [
    ("No source reports the 2025 holdout set as available.", "2025"),
    ("No source reports the holdout set release date as available.", "date"),
    ("No source reports the number of test sets as released.", "number"),
])
def test_a_date_or_amount_in_the_reported_item_is_still_guarded(text, term):
    """#3265: what the cue reports as unstated is a date or an amount."""
    out = sd.scan(record(splits=[{"name": "Entry", "description": text}]), LEXICON)
    assert out["flags"] == [] and [(g["guard"], g["term"]) for g in out["guarded"]] == [("date_amount", term)]


def test_an_item_object_needs_the_cue_to_name_an_item_group():
    raw = sd.LEXICON_PATH.read_bytes().replace(b"(?P<item>", b"(?:")
    with pytest.raises(ValueError, match="item"):
        sd.Lexicon(raw)


@pytest.mark.parametrize("text,rule", [
    ("The sources do not give this author's institution.", "role.assignment_negated"),
    ("The sources do not give this author's employer.", "role.assignment_negated"),
    ("This author's institution is not stated.", "role.passive_not_stated"),
    ("The institution of this author is not stated.", "role.passive_not_stated"),
    ("For this creator, the dataset license is not stated.", "role.passive_not_stated"),
])
def test_a_possessor_or_incidental_self_reference_does_not_name_the_role(text, rule):
    """#3251: the role noun inside the member's own self-reference names the
    role only where the self-reference is the cue's object. Owning what is
    unstated, or standing outside the cue's clause object, it reads like
    "her": out of scope for want of a role term."""
    assert outcomes("creators", text) == [(rule, "out_of_scope", "no_role_term")], text
    plain = text.replace("this author's", "her").replace("of this author", "of her") \
        .replace("For this creator", "For her")
    assert outcomes("creators", plain) == [(rule, "out_of_scope", "no_role_term")], plain


@pytest.mark.parametrize("container,text,rule,scope", [
    ("maintainers", "The sources do not name this maintainer.", "role.assignment_negated", "maintainer"),
    ("maintainers", "This maintainer is not named in any source.", "role.passive_not_stated", "maintainer"),
    ("creators", "No source names this author.", "role.none_assigns", "author"),
])
def test_a_self_reference_that_is_the_cues_object_still_names_the_role(container, text, rule, scope):
    """#3251: the self-reference that is itself what the cue says is unstated
    keeps licensing role scope."""
    out = sd.scan(record(**{container: [{"name": "Entry", "description": text}]}), LEXICON)
    assert [(h["rule"], h["scope"]) for f in out["flags"] for h in f["hits"]] == [(rule, scope)], text


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


@pytest.mark.parametrize("container,text", [
    ("instances", "Given the consent terms, the raw audio recordings are not released."),
    ("variables", "Given the privacy rules, the underlying minute-level data are not yet available."),
    ("splits", "Given the site structure, the raw images are not distributed."),
    ("instances", "Listed in the file manifest, the raw audio waveforms are not released."),
    ("splits", "For this split, the raw images are not released."),
])
def test_an_introductory_self_reference_does_not_license_a_clause_with_its_own_subject(container, text):
    """#3159: a self-reference a comma separates from the cue counts only
    when the stretch after the comma has no subject of its own."""
    assert outcomes(container, text) == [("presence.not_yet_released", "out_of_scope", "no_self_reference")]


@pytest.mark.parametrize("container,text,rule,scope", [
    ("instances", "Listed in the file manifest, it is not yet released.", "presence.not_yet_released", "Listed"),
    ("variables", "This variable, per the codebook, is not yet released.", "presence.not_yet_released",
     "This variable"),
    ("creators", "This person is listed on the slide, but is not named as a creator.", "role.not_the_role",
     "This person"),
])
def test_a_self_reference_across_a_comma_counts_where_the_cue_has_no_subject_of_its_own(container, text, rule, scope):
    """#3159: an elided subject after the comma (a pronoun, an auxiliary)
    keeps the self-reference, as for an earlier clause (#3082)."""
    out = sd.scan(record(**{container: [{"name": "Entry", "description": text}]}), LEXICON)
    assert (rule, scope) in [(h["rule"], h["scope"]) for f in out["flags"] for h in f["hits"]], text


@pytest.mark.parametrize("container,text,rule,scope", [
    ("splits", "This is not yet released.", "presence.not_yet_released", "This"),
    ("splits", "This was not yet released.", "presence.not_yet_released", "This"),
    ("instances", "After review, it is not yet released.", "presence.not_yet_released", "it"),
    ("splits", "It is derived from the pilot, but it is not yet released.", "presence.not_yet_released", "it"),
    ("creators", "This is not a creator of the dataset.", "role.not_the_role", "This"),
    ("creators", "According to the slide, she is not a creator.", "role.not_the_role", "she"),
])
def test_a_subject_pronoun_before_an_auxiliary_led_cue_is_a_self_reference(container, text, rule, scope):
    """#3265: a cue that opens on its auxiliary ("is not yet released")
    leaves "This is" without its verb, so the pronoun alone right before
    the cue is the self-reference."""
    out = sd.scan(record(**{container: [{"name": "Entry", "description": text}]}), LEXICON)
    assert [(h["rule"], h["scope"]) for f in out["flags"] for h in f["hits"]] == [(rule, scope)], text


@pytest.mark.parametrize("container,text", [
    ("splits", "A version of it is not released."),
    ("splits", "This is balanced, but the raw images are not released."),
    ("instances", "Given the consent terms for it, the raw audio is not released."),
])
def test_a_pronoun_that_is_not_the_cues_subject_is_not_a_self_reference(container, text):
    """#3265: the pronoun counts only as the cue's own subject, not as the
    object of `of`/`for` or in a clause with a subject of its own."""
    assert outcomes(container, text) == [("presence.not_yet_released", "out_of_scope", "no_self_reference")]


def test_a_none_scope_cue_counts_whatever_its_subject():
    """#3083: in v1 presence.prospective_predicate has no subject condition,
    so it flags a caveat about something else that is prospective. Pinned so
    a change to that contract is a deliberate one: v2 is that change (#3131)."""
    assert outcomes("instances", "The consent forms are prospective.", lexicon=V1) == [
        ("presence.prospective_predicate", "flag", None)]
    assert outcomes("instances", "The consent forms are prospective.") == [
        ("presence.prospective_predicate", "out_of_scope", "no_member_subject")]


V3_SPLIT = "Both statements are prospective on that page, and neither gives split sizes or a splitting procedure."


@pytest.mark.parametrize("container,text,scope", [
    # the v3 direct canary's final /splits/0 split_details, verbatim (#3131)
    ("splits", V3_SPLIT, "statements"),
    ("splits", "The descriptions are all prospective.", "descriptions"),
    ("splits", "Mentions of the holdout set remain prospective.", "holdout set"),
    ("splits", "References to this split are prospective.", "this split"),
    ("splits", "Descriptions of this split are prospective.", "this split"),
    ("splits", "Both of the two source statements are prospective.", "statements"),
    ("splits", "The statements on the program page are prospective.", "statements"),
    ("splits", "This split remains prospective.", "This split"),
    ("instances", "It is prospective.", "It"),
    ("splits", "The holdout set is still prospective.", "holdout set"),
    ("variables", "Per the protocol, the measures are prospective.", "measures"),
])
def test_a_subject_cue_counts_a_statement_self_or_presence_subject(container, text, scope):
    """#3131: `presence.prospective_predicate` has `subject` scope in v2. A
    self-reference, a source-statement subject (with a topic that is the
    member) or a presence-term subject licenses it."""
    out = sd.scan(record(**{container: [{"name": "Entry", "description": text}]}), LEXICON)
    assert [(h["rule"], h["scope"]) for f in out["flags"] for h in f["hits"]] == [
        ("presence.prospective_predicate", scope)], text


@pytest.mark.parametrize("container,text,reason", [
    # the three false-positive shapes #3131 names, all flagged by v1
    ("instances", "The consent process is prospective.", "no_member_subject"),
    ("splits", "Enrollment of the pediatric arm remains prospective.", "no_member_subject"),
    ("variables", "The follow-up schedule is prospective.", "no_member_subject"),
    # a self-reference that owns the subject is not the subject
    ("splits", "This split's schedule is prospective.", "no_member_subject"),
    ("splits", "The consent process for this split is prospective.", "no_member_subject"),
    # a statement about something else
    ("splits", "Statements about the consent process are prospective.", "statement_about_other"),
    ("instances", "Descriptions of the consent materials are prospective.", "statement_about_other"),
    ("splits", "The references to the consent process are prospective.", "statement_about_other"),
    # a statement noun that does not head the subject (#3560)
    ("splits", "The consent process described in both statements is prospective.", "no_member_subject"),
    ("splits", "The consent process mentioned in the statements is prospective.", "no_member_subject"),
    ("splits", "Consent in the statements is prospective.", "no_member_subject"),
])
def test_a_subject_cue_about_something_else_is_out_of_scope(container, text, reason):
    assert outcomes(container, text, lexicon=V1) == [("presence.prospective_predicate", "flag", None)]
    assert outcomes(container, text) == [("presence.prospective_predicate", "out_of_scope", reason)], text


def test_a_subject_cue_on_an_amount_is_guarded():
    """#3131: the pattern's object is its subject, so "split sizes" is an
    amount, not the split's presence."""
    out = sd.scan(record(splits=[{"name": "Entry", "description": "The split sizes are prospective."}]), LEXICON)
    assert out["flags"] == [] and [(g["guard"], g["term"]) for g in out["guarded"]] == [("date_amount", "sizes")]


def test_the_subject_scope_needs_a_statement_subject_block():
    with pytest.raises(ValueError, match="no statement_subject"):
        edited_lexicon(lambda d: d.pop("statement_subject"))
    with pytest.raises(ValueError, match="`topic` group"):
        edited_lexicon(lambda d: d["statement_subject"].update(topic=r"\s+about\s+.+"))
    with pytest.raises(ValueError, match="outside a presence container"):
        edited_lexicon(lambda d: pattern_row(d, "presence.prospective_predicate").update(
            kinds=["person_role", "presence"]))


# ------------------------------------------------------ another item (#3244)
EXTERNAL = "The external test set is described as planned rather than as a released split."


@pytest.mark.parametrize("leaves", [
    {"name": "Internal validation set"},
    {"name": "Internal test set"},
    {"name": "Validation split"},
    {"name": "Entry", "id": "https://example.org/ds#internal_validation"},
    {"name": "Entry", "id": "doi:10.1234/x#training-split"},
    {"variable_name": "internal_validation_split"},
])
def test_a_presence_term_whose_qualifier_disagrees_with_the_member_is_another_item(leaves):
    """#3244: the member's name tokens or id fragment name a qualifier on an
    axis the presence noun phrase also names, and none is shared."""
    rows = outcomes("splits", EXTERNAL, **leaves)
    assert rows == [("presence.recorded_as_planned", "out_of_scope", "other_qualified_item"),
                    ("presence.contrast_released", "out_of_scope", "other_qualified_item")], leaves
    assert outcomes("splits", EXTERNAL, lexicon=V1, **leaves) == [
        ("presence.recorded_as_planned", "flag", None), ("presence.contrast_released", "flag", None)]


@pytest.mark.parametrize("leaves", [
    {"name": "External test set"},
    {"name": "Holdout set"},          # names test/holdout: shared on that axis
    {"name": "Entry"},                # names no qualifier: v1's reading
    {"name": "Entry", "id": "https://example.org/ds"},
    # only the id's fragment is its identity: the base's qualifiers are not (#3564)
    {"name": "Entry", "id": "https://example.org/internal-validation#split-1"},
    {},
])
def test_a_presence_term_that_agrees_or_cannot_be_told_apart_still_licenses(leaves):
    assert outcomes("splits", EXTERNAL, **leaves) == [
        ("presence.recorded_as_planned", "flag", None), ("presence.contrast_released", "flag", None)], leaves


def test_another_qualified_item_reported_or_in_the_clause_does_not_license():
    """#3244: in the `item` a cue reports, and as the presence term the
    clause fallback would read."""
    out = sd.scan(record(splits=[{"name": "Training split",
                                  "description": "No source reports the test set as available."}]), LEXICON)
    assert [(r["reason"], r["term"]) for r in out["out_of_scope"]] == [("other_qualified_item", "the test set")]
    assert outcomes("splits", "The data are recorded as planned for the external test set.",
                    name="Internal validation set") == [
        ("presence.recorded_as_planned", "out_of_scope", "no_self_or_presence_term")]
    # the member's own name is a self-reference and blanked, so the agreeing
    # phrase is another spelling of it
    assert outcomes("splits", "The data are recorded as planned for the internal validation set.",
                    name="Internal validation split") == [("presence.recorded_as_planned", "flag", None)]


def test_the_item_qualifiers_block_is_validated():
    with pytest.raises(ValueError, match="two or more alternatives"):
        edited_lexicon(lambda d: d["item_qualifiers"].update(axes=[["external"]]))
    with pytest.raises(ValueError, match="nonnegative integer"):
        edited_lexicon(lambda d: d["item_qualifiers"].update(words=-1))


# ------------------------------------------- a self-reference in the item (#3261)
@pytest.mark.parametrize("text,scope", [
    ("No source reports this split as available.", "this split"),
    ("No document lists it as released.", "it"),
    ("None of the pages describes this partition as complete.", "this partition"),
])
def test_a_self_reference_in_the_reported_item_licenses_the_cue(text, scope):
    """#3261: `presence.none_reports_available` declares
    `self_reference_in: [item]` in v2."""
    out = sd.scan(record(splits=[{"name": "Entry", "description": text}]), LEXICON)
    assert [(h["rule"], h["scope"]) for f in out["flags"] for h in f["hits"]] == [
        ("presence.none_reports_available", scope)], text
    assert outcomes("splits", text, lexicon=V1) == [
        ("presence.none_reports_available", "out_of_scope", "no_self_or_presence_term")]


@pytest.mark.parametrize("text,rule", [
    # the #3230 comma-rule case stays out of scope
    ("For this split, the data are recorded as planned.", "presence.recorded_as_planned"),
    # a self-reference in the item that owns what is reported
    ("No source reports the consent form for this split as available.", "presence.none_reports_available"),
])
def test_a_self_reference_outside_the_reported_item_or_owning_it_does_not(text, rule):
    assert outcomes("splits", text) == [(rule, "out_of_scope", "no_self_or_presence_term")]


def test_self_reference_in_is_validated():
    with pytest.raises(ValueError, match="outside item"):
        edited_lexicon(lambda d: pattern_row(d, "presence.none_reports_available").update(
            self_reference_in=["cue"]))
    with pytest.raises(ValueError, match="outside presence scope"):
        edited_lexicon(lambda d: pattern_row(d, "presence.none_reports_available").update(scope="self"))
    # an `item` self-reference on a cue with no `item` group (#3563)
    with pytest.raises(ValueError, match="in an `item` group its cue lacks"):
        edited_lexicon(lambda d: pattern_row(d, "presence.recorded_as_planned").update(
            self_reference_in=["item"]))


@pytest.mark.parametrize("container,text", [
    ("creators", "This person is not necessarily a creator of the dataset."),
    ("maintainers", "A project contact is not necessarily its maintainer."),
])
def test_role_not_necessarily_needs_no_self_reference(container, text):
    """#3164: the `none`-scope role cue names the container's role itself,
    so it counts with or without a self-reference."""
    assert outcomes(container, text) == [("role.not_necessarily", "flag", None)]
    assert outcomes(container, text.replace("necessarily", "always")) == []


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


@pytest.mark.parametrize("snippet,supported", [
    ("Data maintenance: Person C", True),
    ("Person C is responsible for maintenance of the dataset", True),
    ("Maintained by Person C", True),
    ("Person C, Program Manager", False),
])
def test_the_maintainer_predicates_read_the_noun_maintenance(snippet, supported):
    """#3160: the predicate spelled 'maintain...ance' matched only the
    misspelling 'maintainance'."""
    rec = record(maintainers=[{"name": "Person C"}])
    out = sd.role_predicates(rec, receipt(("maintainers[0]", snippet)), LEXICON)
    assert out["supported"] == int(supported), snippet


def test_bucket_b_is_reported_apart_from_the_lexicon_diff():
    rec = record(maintainers=[{"name": "Person C", "maintainer_details": "Listed under Contact Us."}])
    out = sd.diff(rec, copy.deepcopy(rec), receipt=receipt(("maintainers[0]", "Person C, Program Manager")),
                  lexicon=LEXICON)
    assert out["lexicon_diff"]["rows"] == []
    assert [(r["path"], r["classification"]) for r in out["role_predicate_diff"]["rows"]] == [
        ("/maintainers/0", "role_predicate_retained")]


def test_bucket_b_reads_the_receipt_against_the_original():
    """#3164: the receipt was written against the original, so its slot
    paths are the original's. Person C is receipted at maintainers[1] and
    sits at maintainers[0] in the final; read against the final, the receipt
    would address nobody."""
    original = record(maintainers=[{"name": "Person A"}, {"name": "Person C"}])
    final = record(maintainers=[{"name": "Person C"}])
    out = sd.diff(original, final, receipt=receipt(("maintainers[1]", "Person C, Program Manager")),
                  lexicon=LEXICON)
    assert [(f["path"], f["reason"]) for f in out["role_predicate"]["flags"]] == [
        ("/maintainers/0", "no_receipt"), ("/maintainers/1", "no_role_predicate")]
    assert [(r["path"], r["classification"], r["final_path"]) for r in out["role_predicate_diff"]["rows"]] == [
        ("/maintainers/0", "removed", None), ("/maintainers/1", "role_predicate_retained", "/maintainers/0")]


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


def test_a_shared_caveat_does_not_join_two_different_people():
    """#3265: remap_path joins an entry with no key match by scalar overlap,
    and a caveat two maintainers share is such a scalar. Alice is not
    retained as Betty: deleted, she is unresolved (her entry may also have
    been renamed), and replaced, Betty is a final-only flag."""
    alice = {"name": "Alice Adams", "source_caveats": DISCLAIMER}
    betty = {"name": "Betty Baker", "source_caveats": DISCLAIMER}
    deleted = sd.diff(record(maintainers=[alice, betty]), record(maintainers=[betty]), lexicon=LEXICON)
    assert [(r["path"], r["classification"], r["final_path"], r["identity_basis"])
            for r in deleted["lexicon_diff"]["rows"]] == [
        ("/maintainers/0", "identity_unresolved", None, "identity_conflict"),
        ("/maintainers/1", "self_disclaimed_retained", "/maintainers/0", "by_name")]
    assert deleted["lexicon_diff"]["counts"]["self_disclaimed_retained"] == 1
    replaced = sd.diff(record(maintainers=[alice]), record(maintainers=[betty]), lexicon=LEXICON)
    assert classes(replaced) == {"/maintainers/0": "identity_unresolved"}
    assert replaced["final_only"] == ["/maintainers/0"]


def test_a_resolver_url_and_its_curie_are_one_identity():
    """The identity check compares keys as remap_path does: #974's
    normaliser rewrites a resolver URL to its CURIE, the same entry."""
    member = {"id": "https://doi.org/10.1/x", "source_caveats": DISCLAIMER}
    final = {"id": "doi:10.1/x", "source_caveats": DISCLAIMER}
    assert sd._identity(member, final) == "agrees"
    assert sd._identity({"name": "A B"}, {"name": "C D"}) == "conflicts"
    assert sd._identity({"name": "A B"}, {"id": "x"}) == "unknown"


def test_two_originals_followed_to_one_final_entry_are_not_both_retained():
    """#3265: keyless entries both joined by overlap to the one survivor.
    Neither identity is confirmed by a key, so under v1 neither is retained
    (v2 lets a strictly greater overlap decide, #3273, below)."""
    one = {"split_details": "This split is recorded as a planned provision.", "size": "10"}
    two = {"split_details": one["split_details"], "size": "20"}
    out = sd.diff(record(splits=[one, two]), record(splits=[dict(one)]), lexicon=V1)
    assert [(r["path"], r["classification"], r["identity_basis"]) for r in out["lexicon_diff"]["rows"]] == [
        ("/splits/0", "identity_unresolved", "shared_final_entry"),
        ("/splits/1", "identity_unresolved", "shared_final_entry")]
    # the one whose key agrees keeps the survivor; the other does not
    a = {"name": "Split A", "split_details": one["split_details"]}
    b = {"name": "Split B", "split_details": one["split_details"]}
    kept = sd._resolve_all(record(splits=[a, b]), record(splits=[{**a, "size": "1"}]), LEXICON)
    assert kept == {("splits", 0): ((("splits", 0)), "same"), ("splits", 1): (None, "identity_conflict")}


def test_two_keyless_originals_on_one_final_entry_resolve_by_strictly_greater_overlap():
    """#3273: in v2 the keyless member whose scalar leaves overlap the
    survivor strictly more keeps it; v1 left both unresolved (above), and a
    tie still does."""
    one = {"split_details": "This split is recorded as a planned provision.", "size": "10"}
    two = {"split_details": one["split_details"], "size": "20"}
    out = sd.diff(record(splits=[one, two]), record(splits=[dict(one)]), lexicon=LEXICON)
    assert [(r["path"], r["classification"], r["final_path"], r["identity_basis"])
            for r in out["lexicon_diff"]["rows"]] == [
        ("/splits/0", "self_disclaimed_retained", "/splits/0", "shared_final_entry_by_overlap"),
        ("/splits/1", "identity_unresolved", None, "shared_final_entry")]
    v1 = sd.diff(record(splits=[one, two]), record(splits=[dict(one)]), lexicon=V1)
    assert {r["identity_basis"] for r in v1["lexicon_diff"]["rows"]} == {"shared_final_entry"}
    # the member further down wins as well; a tie leaves both unresolved
    moved = sd._resolve_all(record(splits=[two, one]), record(splits=[dict(one)]), LEXICON)
    assert moved == {("splits", 0): (None, "shared_final_entry"),
                     ("splits", 1): (("splits", 0), "shared_final_entry_by_overlap")}
    tie = sd._resolve_all(record(splits=[{**one, "size": "20"}, {**one, "size": "30"}]),
                          record(splits=[dict(one)]), LEXICON)
    assert set(tie.values()) == {(None, "shared_final_entry")}


def test_the_overlap_rule_does_not_apply_where_members_identity_keys_agree():
    """#3273, #3562: `scalar_overlap` resolves only where no member's
    identity keys agree. Two members whose keys both agree with the one
    survivor stay unresolved even though one overlaps it strictly more."""
    one = {"id": "ex:s1", "split_details": "This split is recorded as a planned provision.", "size": "10"}
    two = {**one, "size": "20"}
    both = sd._resolve_all(record(splits=[one, two]), record(splits=[dict(one)]), LEXICON)
    assert both == {("splits", 0): (None, "shared_final_entry"),
                    ("splits", 1): (None, "shared_final_entry")}


def test_shared_final_entry_resolve_by_is_validated():
    for bad in ([], ["scalar_overlap"], ["identity_keys", "size"], ["identity_keys", "identity_keys"]):
        with pytest.raises(ValueError, match="resolve_by"):
            edited_lexicon(lambda d: d["shared_final_entry"].update(resolve_by=bad))


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
    assert LEXICON.version == max(LEXICON_PINS), "the loader reads the newest version"
    assert LEXICON.describe() == {"path": sd.LEXICON_RESOURCE, "version": LEXICON.version,
                                  "sha256": LEXICON_PINS[LEXICON.version]}


def test_every_lexicon_version_is_kept_pinned_and_loadable():
    """#3131: an earlier version stays byte for byte and loads for replay,
    named by its repository-relative spelling."""
    files = sorted(p.name for p in sd.LEXICON_DIR.glob("*.yaml"))
    assert files == [f"self_disclaimed_v{v}.yaml" for v in sorted(LEXICON_PINS)]
    for version, sha in LEXICON_PINS.items():
        loaded = sd.load_lexicon(sd.lexicon_path(version))
        assert loaded.describe() == {"path": f"src/data_sheets_schema/container_lexicons/self_disclaimed_v{version}.yaml",
                                     "version": version, "sha256": sha}
    assert V1.resolve_by == ("identity_keys",) and not V1._axes and V1._statement is None


def edited_lexicon(edit):
    data = yaml.safe_load(sd.LEXICON_PATH.read_text(encoding="utf-8"))
    edit(data)
    return sd.Lexicon(yaml.safe_dump(data, sort_keys=False).encode("utf-8"))


def pattern_row(data, pattern_id):
    return next(row for row in data["patterns"] if row["id"] == pattern_id)


def test_a_guard_reading_the_object_needs_the_pattern_to_declare_one():
    """A pattern whose guard reads `object` must say where its object lies,
    in the parts the code reads; a guard must read a part the code knows."""
    assert edited_lexicon(lambda d: None).patterns == LEXICON.patterns
    with pytest.raises(ValueError, match="declares none"):
        edited_lexicon(lambda d: pattern_row(d, "role.assignment_negated").pop("object"))
    with pytest.raises(ValueError, match="declares an object outside"):
        edited_lexicon(lambda d: pattern_row(d, "role.assignment_negated").update(object=["after_cue"]))
    with pytest.raises(ValueError, match="must read one of"):
        edited_lexicon(lambda d: d["guards"]["subrole_object"].update(reads="after_cue"))


def test_the_assignment_owner_block_is_validated():
    """#3209: the owner reader needs a positive word window and a pattern
    that captures its preposition."""
    with pytest.raises(ValueError, match="positive integer"):
        edited_lexicon(lambda d: d["assignment_owner"].update(words=0))
    with pytest.raises(ValueError, match="one group"):
        edited_lexicon(lambda d: d["assignment_owner"].update(after=r"\s+(?:of|for)\s+"))


@pytest.mark.parametrize("version", sorted(LEXICON_PINS))
def test_lexicon_is_generic(version):
    text = sd.lexicon_path(version).read_text(encoding="utf-8").lower()
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
    assert out["lexicon"]["sha256"] == LEXICON_PINS[LEXICON.version]
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
