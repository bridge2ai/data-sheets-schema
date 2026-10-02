"""Support judge v2 (#2929): typed verdicts, per-value context, no propagation.

Offline throughout. The client is a recording fake whose `messages.stream`
returns a canned reply, so each request goes through the real
`api_runner._call_with_retry` and the test reads exactly what would be sent.
The documents and the schema are neutral synthetic ones: no study, no
provider call. A fake client cannot judge, so these tests prove what the
judge is *told* and what it will *accept* — whether a model actually returns
`status_shifted` for a status shift is the calibration's question, and that
run is paid (#2929).

Section headers name the acceptance criteria of #2929 they bear on, in that
issue's own numbering (seven criteria). Offline tests reach criteria 1 and 2
only: the instrument itself (criterion 1) and the synthetic-document tests
(criterion 2). Criterion 2's tests show what the judge is sent and that it
accepts each typed verdict; they cannot show a judging outcome. Criteria
3-7 (calibration, run manifest, canary and run, join report, figure
updates) are not covered here.
"""

from __future__ import annotations

import hashlib
import inspect
import json
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest

from data_sheets_schema import evaluation_model, evidence_score
from data_sheets_schema.support_judge import (
    AXIS,
    DECLARATION_FIELDS,
    SUPPORT_V2_SYSTEM,
    VERDICTS,
    PropagationRefused,
    SupportJudgeV2,
    SupportSpecification,
    SupportVerdict,
    VerdictError,
    build_value_context,
    parse_verdict,
)

ROOT = Path(__file__).resolve().parents[2]
JULY_CACHE = ROOT / "data" / "evaluation_llm" / "judgement_cache"

# The bytes of every cache file committed before v2 existed. v2 writes only
# where it is told to; these must never move because of it.
JULY_CACHE_SHA256 = {
    "AI_READI_fitness.jsonl": "dddd5570161b7ae3fe7ad648e4fc4db7f02757875af3b2d4d71e3a56298b1eeb",
    "CHORUS_fitness.jsonl": "41d984db9d0ace58d782157c53b2f78eac769c49188a037cd64f7d038eca76a7",
    "CM4AI.jsonl": "9f177d3e4f023615418db7835fe9f32b50e40e16651183a4daf1eecd4b4dcf3f",
    "CM4AI_fitness.jsonl": "4c97afb04e418bfe2da7c84bb9117052f2e1716009d70dffae6e0d52b9c71077",
    "VOICE_fitness.jsonl": "d64cce858b5206229515c682755f745941fbaa1ac55a70ed7fb5479871f94ca4",
}

# --- a neutral synthetic corpus ------------------------------------------

DOC_A = ("FILE: a_overview.txt\n"
         "The Harbor Survey collects water samples from twelve sites.\n"
         "Sample collection began in 2024 and is complete.\n"
         "A public data portal is planned for a later phase.\n"
         "Steering committee: Dana Reyes (chair), Lee Park.\n")
DOC_B = ("FILE: b_methods.txt\n"
         "Samples are filtered and frozen within two hours.\n"
         "Data files were prepared by Sam Ortiz and Kim Wu.\n")
BUNDLE = DOC_A + "\n" + DOC_B

RECORD = {
    "id": "ex:harbor-survey",
    "title": "Harbor Survey",
    "description": "Water samples from twelve harbor sites.",
    "sites": 12,
    "access": {"description": "Data are available through a public data portal.",
               "claim_status": "fact", "attributed_to": ["a_overview.txt"]},
    "creators": [{"name": "Dana Reyes"}],
    "preparation": {"description": "Samples are filtered and frozen within two hours.",
                    "attributed_to": ["a_overview.txt"]},
    "keywords": ["harbor", "steering"],
    "notes": None,
}

SPECS = {
    "id": "Field: `id`\nDeclared range: uriorcurie",
    "title": "Field: `title`\nDeclared range: string\nSpecification: The dataset's name.",
    "description": "Field: `description`\nDeclared range: string",
    "sites": "Field: `sites`\nDeclared range: integer\nSpecification: Number of sampling sites.",
    "access": ("Field: `access`\nDeclared range: AccessStatement\n"
               "Specification: How the data can be obtained now."),
    "creators": ("Field: `creators`\nDeclared range: Creator (list — many values expected)\n"
                 "Specification: Individuals who created the dataset."),
    "preparation": "Field: `preparation`\nDeclared range: Preparation",
    "keywords": "Field: `keywords`\nDeclared range: string (list — many values expected)",
}
RELATIONSHIP = {"access", "creators", "preparation"}


def spec(digest="spec-1"):
    return SupportSpecification(digest=digest, render=lambda s: SPECS[s],
                                relationship=lambda s: s in RELATIONSHIP)


class RecordingClient:
    """`messages.stream` records each request and answers from a queue."""

    def __init__(self, *replies, stop_reason="end_turn"):
        self.replies = list(replies)
        self.stop_reason = stop_reason
        self.requests: list[dict] = []
        outer = self

        class _Messages:
            @staticmethod
            def stream(**kw):
                outer.requests.append(kw)
                text = outer.replies.pop(0)

                class _S:
                    def __enter__(self): return self
                    def __exit__(self, *a): return False
                    def __iter__(self): return iter([SimpleNamespace(type="message_stop")])

                    def get_final_message(self):
                        return SimpleNamespace(
                            content=[SimpleNamespace(type="text", text=text)],
                            usage=SimpleNamespace(input_tokens=1, output_tokens=1,
                                                  cache_read_input_tokens=0,
                                                  cache_creation_input_tokens=0),
                            stop_reason=outer.stop_reason)
                return _S()

        self.messages = _Messages()

    def value_text(self, i=-1) -> str:
        return self.requests[i]["messages"][0]["content"][1]["text"]


def reply(verdict, reason="short reason"):
    return json.dumps({"verdict": verdict, "reason": reason})


def judge(client, **kw):
    kw.setdefault("specification", spec())
    return SupportJudgeV2(client=client, model="judge-m", **kw)


# --- criterion 2 (request side only): what the judge is told about each
# defect class, and that it accepts the verdict. The verdicts are canned. ---

def test_a_status_shift_sends_the_values_own_status_and_the_slot_spec():
    """Source: a portal is planned. Value: data are available through one,
    declared `fact` from a_overview.txt — the declaration is itself wrong."""
    client = RecordingClient(reply("status_shifted"))
    v = judge(client).judge(project="P", record=RECORD, slot="access", bundle=BUNDLE)
    assert v.verdict == "status_shifted"
    sent = client.requests[0]
    text = client.value_text()
    assert sent["system"] == SUPPORT_V2_SYSTEM
    assert SPECS["access"] in text
    assert "/access/claim_status: fact" in text
    assert "Claims to test against the documents, not evidence" in text
    assert "public data portal" in text
    # The documents travel as the cached first block, unchanged.
    assert sent["messages"][0]["content"][0]["text"] == f"# Source documents\n\n{BUNDLE}"
    assert sent["messages"][0]["content"][0]["cache_control"] == {"type": "ephemeral"}


def test_a_leadership_name_placed_under_creators_carries_the_containing_entity():
    client = RecordingClient(reply("relationship_unsupported"))
    v = judge(client).judge(project="P", record=RECORD, slot="creators", bundle=BUNDLE)
    assert v.verdict == "relationship_unsupported"
    text = client.value_text()
    assert "# Containing entity" in text
    assert "id: ex:harbor-survey" in text and "title: Harbor Survey" in text
    assert SPECS["creators"] in text
    assert "name: Dana Reyes" in text


def test_a_wrong_document_attribution_is_sent_as_a_claim_to_test():
    """The value is in b_methods.txt; the record says a_overview.txt."""
    client = RecordingClient(reply("wrong_document"))
    v = judge(client).judge(project="P", record=RECORD, slot="preparation", bundle=BUNDLE)
    assert v.verdict == "wrong_document"
    text = client.value_text()
    assert "/preparation/attributed_to:" in text and "- a_overview.txt" in text


def test_a_caller_supplied_declaration_is_rendered_apart_from_the_value():
    """An audit claim's declaration, passed in, is shown as a claim to test."""
    client = RecordingClient(reply("wrong_document"))
    judge(client).judge(project="P", record=RECORD, slot="sites", bundle=BUNDLE,
                        declarations={"attributed_to": ["b_methods.txt"],
                                      "claim_status": "fact"})
    text = client.value_text()
    assert "'declared: attributed_to':" in text
    assert "'declared: claim_status': fact" in text


def test_a_word_match_only_value_is_sent_and_unsupported_is_accepted():
    """`steering` appears in the documents; it describes nothing about the data."""
    client = RecordingClient(reply("unsupported"))
    v = judge(client).judge(project="P", record=RECORD, slot="keywords", bundle=BUNDLE)
    assert v.verdict == "unsupported"
    text = client.value_text()
    assert "- steering" in text
    # A scalar, non-relationship slot gets no entity and says it has no declarations.
    assert "# Containing entity" not in text
    assert "None declared." in text


def test_a_canned_supported_reply_parses_unflagged_and_the_value_is_sent():
    """What this shows: a `supported` reply is parsed, not propagated and not
    served from cache, and the request carries the value and its spec. It
    cannot show that a directly stated value is judged supported — the reply
    is canned (#3349)."""
    client = RecordingClient(reply("supported"))
    v = judge(client).judge(project="P", record=RECORD, slot="sites", bundle=BUNDLE)
    assert (v.verdict, v.propagated, v.from_cache) == ("supported", False, False)
    text = client.value_text()
    assert SPECS["sites"] in text
    assert "Record field `sites` asserts:\n\n```yaml\nsites: 12\n```" in text
    assert "# Containing entity" not in text and "None declared." in text


def test_the_prompt_names_every_verdict_and_refuses_deference():
    for verdict in VERDICTS:
        assert f"  {verdict} — " in SUPPORT_V2_SYSTEM
    assert "claims under test, not evidence" in SUPPORT_V2_SYSTEM
    assert "Matching words are not support" in SUPPORT_V2_SYSTEM
    # The sentence that forbids deference itself (#3350).
    assert ("Never accept a value because the record says where it came from "
            "or what state it is in; a declaration the documents do not bear "
            "out is itself a defect.") in SUPPORT_V2_SYSTEM


def test_only_an_explicit_attribution_counts_toward_wrong_document():
    """A derivation link or an identifier inside the value is not a citation
    of the value's source document (#3347)."""
    flat = " ".join(SUPPORT_V2_SYSTEM.split())
    assert ("wrong_document — the fact is in the documents, but not in the "
            "document an explicit attribution for the value names as its "
            "source. Only an attribution counts: a resource the value says it "
            "was derived from, or an identifier inside the value, is not a "
            "citation of a source document.") in flat
    assert "declaration cites" not in flat


def test_every_verdict_parses():
    for verdict in VERDICTS:
        assert parse_verdict(reply(verdict)) == (verdict, "short reason")
    assert parse_verdict("```json\n" + reply("supported") + "\n```")[0] == "supported"


def test_declarations_are_found_at_any_depth():
    record = {"x": [{"a": {"claim_status": "planned"}},
                    {"attributed_to": ["d.txt"]}, {"b": {"source_status": "s"}}]}
    ctx = build_value_context(record, "x", relationship=False)
    assert ctx.declarations == {"/x/0/a/claim_status": "planned",
                                "/x/1/attributed_to": ["d.txt"],
                                "/x/2/b/source_status": "s"}
    assert ctx.entity is None
    assert DECLARATION_FIELDS == ("attributed_to", "claim_status", "source_status")


def test_schema_status_and_derivation_are_not_presented_as_attributions():
    """`status` (publication status) and `was_derived_from`
    (prov:wasDerivedFrom) are resource facts, not the value's source
    document (#3347): they stay in the value and are never listed as its
    declarations."""
    record = {"subsets": [{"name": "features", "status": "Beta",
                           "was_derived_from": "ark:00000/computation-x"}]}
    ctx = build_value_context(record, "subsets", relationship=False)
    assert ctx.declarations == {}
    client = RecordingClient(reply("supported"))
    SupportJudgeV2(client=client, model="judge-m", specification=SupportSpecification(
        digest="s", render=lambda s: "Field: `subsets`", relationship=lambda s: False)
    ).judge(project="P", record=record, slot="subsets", bundle=BUNDLE)
    text = client.value_text()
    head, value = text.split("# Value", 1)
    assert "None declared." in head and "ark:00000" not in head
    assert "was_derived_from: ark:00000/computation-x" in value
    assert "status: Beta" in value


# --- criterion 1 (the instrument): malformed and truncated replies are
# rejected ---

@pytest.mark.parametrize("text", [
    "",
    "supported",
    '{"verdict": "supported"}',                                  # no reason
    '{"verdict": "supported", "reason": ""}',                    # empty reason
    '{"verdict": "Supported", "reason": "x"}',                   # wrong spelling
    '{"verdict": "mostly_supported", "reason": "x"}',            # unknown verdict
    '{"verdict": 1, "reason": "x"}',
    '{"verdict": "supported", "reason": "x", "score": 1.0}',     # extra key
    '{"verdict": "supported", "verdict": "unsupported", "reason": "x"}',
    '{"verdict": "supported", "reason": "the documents st',      # truncated
    'Here it is: {"verdict": "supported", "reason": "x"}',       # prose around
    '["supported", "x"]',
    "```json\n" + '{"verdict": "supported", "reason": "x"}',     # open fence
    "```json\n" + '{"verdict": "supported", "reason": "x"}' + "\nok",   # unterminated fence, trailing prose
])
def test_malformed_replies_are_rejected_not_coerced(text):
    with pytest.raises(VerdictError):
        parse_verdict(text)


def test_a_reply_that_hit_max_tokens_is_rejected_even_if_it_parses():
    with pytest.raises(VerdictError):
        parse_verdict(reply("supported"), truncated=True)


def test_the_judge_raises_and_caches_nothing_on_a_truncated_reply(tmp_path):
    cache = tmp_path / "support_v2_2929.jsonl"
    client = RecordingClient(reply("supported"), stop_reason="max_tokens")
    with pytest.raises(VerdictError):
        judge(client, cache_path=cache).judge(project="P", record=RECORD,
                                              slot="sites", bundle=BUNDLE)
    assert not cache.exists()


# --- criterion 1 (the instrument): cache identity, re-read, rejection ---

def test_entries_carry_the_identity_and_reload_without_a_call(tmp_path):
    cache = tmp_path / "support_v2_2929.jsonl"
    first = RecordingClient(reply("supported"))
    judge(first, cache_path=cache).judge(project="P", record=RECORD, slot="sites",
                                         bundle=BUNDLE)
    entry = json.loads(cache.read_text().strip())
    assert entry["axis"] == AXIS == "grounding_v2"
    assert entry["model"] == "judge-m"
    assert entry["rubric"] == evidence_score.digest_of(SUPPORT_V2_SYSTEM)
    assert entry["corpus"] == evidence_score.digest_of(BUNDLE)
    assert entry["specification"] == "spec-1"
    assert entry["propagated"] is False and entry["verdict"] == "supported"

    second = RecordingClient()                     # no replies: a call would fail
    again = judge(second, cache_path=cache)
    v = again.judge(project="P", record=RECORD, slot="sites", bundle=BUNDLE)
    assert (v.verdict, v.from_cache, v.propagated) == ("supported", True, False)
    assert second.requests == [] and again.cache_loaded == 1


@pytest.mark.parametrize("change,dimension", [
    ({"specification": spec("spec-2")}, "specification"),
    ({"model": "judge-other"}, "model"),
])
def test_a_changed_specification_or_model_rejects_the_entry(tmp_path, change, dimension):
    cache = tmp_path / "support_v2_2929.jsonl"
    judge(RecordingClient(reply("supported")), cache_path=cache).judge(
        project="P", record=RECORD, slot="sites", bundle=BUNDLE)
    client = RecordingClient(reply("unsupported"))
    kw = {"specification": change.get("specification", spec()), "cache_path": cache}
    j = SupportJudgeV2(client=client, model=change.get("model", "judge-m"), **kw)
    assert j.judge(project="P", record=RECORD, slot="sites", bundle=BUNDLE).verdict == "unsupported"
    assert j.cache_loaded == 0 and j.cache_skipped == {dimension: 1}
    assert len(client.requests) == 1


def test_a_changed_corpus_or_context_is_a_new_question(tmp_path):
    cache = tmp_path / "support_v2_2929.jsonl"
    client = RecordingClient(*(reply("supported") for _ in range(3)))
    j = judge(client, cache_path=cache)
    j.judge(project="P", record=RECORD, slot="creators", bundle=BUNDLE)
    j.judge(project="P", record=RECORD, slot="creators", bundle=DOC_A)
    other = {**RECORD, "id": "ex:another-survey"}      # same value, other entity
    j.judge(project="P", record=other, slot="creators", bundle=BUNDLE)
    assert len(client.requests) == 3
    j.judge(project="P", record=RECORD, slot="creators", bundle=BUNDLE)
    assert len(client.requests) == 3 and j.memo_hits == 1


def test_different_declarations_on_the_same_value_are_different_questions(tmp_path):
    """The declarations are part of the value context's digest, so a verdict
    under one attribution is never served for another."""
    cache = tmp_path / "support_v2_2929_decl.jsonl"
    client = RecordingClient(*(reply("supported") for _ in range(3)))
    j = judge(client, cache_path=cache)
    j.judge(project="P", record=RECORD, slot="sites", bundle=BUNDLE,
            declarations={"attributed_to": ["x.txt"]})
    j.judge(project="P", record=RECORD, slot="sites", bundle=BUNDLE,
            declarations={"attributed_to": ["y.txt"]})
    assert len(client.requests) == 2
    j.judge(project="P", record=RECORD, slot="sites", bundle=BUNDLE,
            declarations={"attributed_to": ["x.txt"]})
    assert len(client.requests) == 2 and j.memo_hits == 1


def test_the_v2_loader_rejects_every_july_cm4ai_entry(tmp_path):
    """The July support entries carry no axis: v2 must never read them."""
    copy = tmp_path / "CM4AI_2929_copy.jsonl"
    shutil.copyfile(JULY_CACHE / "CM4AI.jsonl", copy)
    j = judge(RecordingClient(reply("supported")), cache_path=copy)
    j.judge(project="CM4AI", record=RECORD, slot="sites", bundle=BUNDLE)
    assert j.cache_loaded == 0
    assert j.cache_skipped == {"axis": 116}


def test_a_hand_edited_entry_is_skipped_and_named(tmp_path):
    cache = tmp_path / "support_v2_2929.jsonl"
    judge(RecordingClient(reply("supported")), cache_path=cache).judge(
        project="P", record=RECORD, slot="sites", bundle=BUNDLE)
    good = json.loads(cache.read_text())
    cache.write_text("\n".join([
        json.dumps({**good, "propagated": True}),
        json.dumps({**good, "verdict": "mostly"}),
        "{torn",
    ]) + "\n")
    j = judge(RecordingClient(reply("supported")), cache_path=cache)
    j.judge(project="P", record=RECORD, slot="sites", bundle=BUNDLE)
    assert j.cache_loaded == 0
    assert j.cache_skipped == {"propagated": 1, "verdict": 1, "unreadable": 1}


@pytest.mark.parametrize("edit", [
    lambda e: {k: v for k, v in e.items() if k != "value_context"},
    lambda e: {**e, "slot": 3},
    lambda e: {**e, "value": None},
])
def test_an_entry_missing_its_key_fields_is_skipped_as_key(tmp_path, edit):
    """A context-matching entry without a string slot, value or value_context
    is skipped and named `key`, not loaded and not a crash (#3351)."""
    cache = tmp_path / "support_v2_2929.jsonl"
    judge(RecordingClient(reply("supported")), cache_path=cache).judge(
        project="P", record=RECORD, slot="sites", bundle=BUNDLE)
    good = json.loads(cache.read_text())
    cache.write_text(json.dumps(edit(good)) + "\n" + json.dumps(good) + "\n")
    client = RecordingClient()                     # the good entry answers
    j = judge(client, cache_path=cache)
    v = j.judge(project="P", record=RECORD, slot="sites", bundle=BUNDLE)
    assert v.from_cache and client.requests == []
    assert j.cache_loaded == 1 and j.cache_skipped == {"key": 1}


# --- criterion 1 (the old judge and its cache semantics unchanged) -------

def test_scorer_system_is_byte_identical():
    """SCORER_SYSTEM is part of every v1 grounding entry's identity."""
    text = evidence_score.SCORER_SYSTEM
    assert hashlib.sha256(text.encode("utf-8")).hexdigest() == \
        "9fffbc810698e7209a28ebadcda4a05b30404e2dd96c93d7a3b11adb2e8d81e3"
    assert evidence_score.digest_of(text) == "6dac77cd36e6"
    assert SUPPORT_V2_SYSTEM != text


def test_llm_slot_scorer_and_its_parser_are_byte_identical():
    """v2 is added beside v1, never by editing it. An intended v1 change
    updates these pins in the same commit, on purpose. #3325 adds model-selection
    disclosure; the prompt, parser, context fingerprint and legacy cache reuse
    are unchanged and independently tested."""
    pins = {
        evidence_score.LLMSlotScorer:
            "6a93ddf5500fc2012d13232e109f576ebdcdb182e0fa4d84ce83ea23f3774478",
        evidence_score._parse_judgement:
            "fc96fcbd3fd9499e3d098d63bd11d9ac85ccddc35961f617119c603f9d7d9781",
        evidence_score.JudgementContext:
            "8f17331176d5c9d626ecba0292fbec597b94b0a9cce78e17d0570a581e91beac",
    }
    for obj, pin in pins.items():
        assert hashlib.sha256(inspect.getsource(obj).encode("utf-8")).hexdigest() == pin, obj


def _july_digests() -> dict[str, str]:
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(JULY_CACHE.iterdir()) if p.is_file()}


def test_the_july_caches_hash_identically_and_v2_does_not_touch_them(tmp_path):
    assert _july_digests() == JULY_CACHE_SHA256
    client = RecordingClient(*(reply("supported") for _ in range(8)))
    judge(client, cache_path=tmp_path / "support_v2_2929.jsonl").judge_record(
        project="CM4AI", record=RECORD, bundle=BUNDLE)
    assert _july_digests() == JULY_CACHE_SHA256


# --- criterion 1 (the instrument): never propagated ---------------------

def test_verdicts_cannot_be_marked_propagated():
    with pytest.raises(TypeError):
        SupportVerdict(slot="s", verdict="supported", reason="r", propagated=True)


def test_the_judge_refuses_the_propagating_plan():
    j = judge(RecordingClient())
    with pytest.raises(PropagationRefused):
        j.as_slot_scorer()
    recs = {"rep1": {"sites": 12}, "rep2": {"sites": 13}}
    plan = evidence_score.build_plan("P", recs)
    with pytest.raises(TypeError):
        evidence_score.run_plan(plan, recs, BUNDLE, j)


def test_judge_record_judges_each_populated_value_of_that_record_once():
    populated = [s for s in RECORD if RECORD[s] is not None]
    client = RecordingClient(*(reply("supported") for _ in populated))
    verdicts = judge(client).judge_record(project="P", record=RECORD, bundle=BUNDLE)
    assert [v.slot for v in verdicts] == populated
    assert "notes" not in populated
    assert not any(v.propagated for v in verdicts)
    assert len(client.requests) == len(populated)
    # Each request carries that slot's own value, read from this record.
    for request, slot in zip(client.requests, populated):
        assert f"Record field `{slot}` asserts" in request["messages"][0]["content"][1]["text"]


def test_an_empty_value_or_missing_bundle_is_refused():
    j = judge(RecordingClient())
    with pytest.raises(ValueError):
        j.judge(project="P", record=RECORD, slot="notes", bundle=BUNDLE)
    with pytest.raises(ValueError):
        j.judge(project="P", record=RECORD, slot="sites", bundle="")


# --- the model and the real specification ---------------------------------

def test_the_model_resolves_through_the_evaluation_setting(monkeypatch):
    monkeypatch.setattr(evaluation_model, "evaluation_model_settings",
                        lambda: {"name": "evaluator-x", "basis": "test"})
    j = SupportJudgeV2(client=RecordingClient(), specification=spec())
    assert j._resolve()[1] == "evaluator-x" and j.model_basis == "test"
    assert SupportJudgeV2(client=RecordingClient(), model="m")._resolve()[1] == "m"


def test_the_default_specification_is_the_fitness_judges():
    """One specification for both axes: same rendering, same digest (#1261)."""
    s = SupportSpecification.from_schema()
    _, inventory, vocabulary, digest = evidence_score.slot_specification_snapshot()
    assert s.digest == digest
    assert s.render("creators") == evidence_score._render_slot_spec(
        "creators", inventory, vocabulary)
    assert "Declared range: Creator" in s.render("creators")
    assert s.relationship("creators") and not s.relationship("title")
