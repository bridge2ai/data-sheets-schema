"""The blind second reading of the 122 Q19 recommendations (#3831, #3871).

The committed second reading must cover exactly the first reading's items and
use only the rubric's classes. The first reading must be the
`_RECOMMENDATIONS_READ` pins and nothing else, and the agreement note's figures
must recompute from the two files. Fixture-only: no corpus walk.
"""
import hashlib
import importlib.util
import json
import re
from collections import Counter
from pathlib import Path

import yaml

from tests.test_q19_rationale_lint import _RECOMMENDATIONS_READ, _pinned

ROOT = Path(__file__).resolve().parents[1]
NOTES = ROOT / "notes"
PACKET = NOTES / "q19_recommendations_3831_packet.json"
RUBRIC = NOTES / "q19_recommendations_3831_rubric.md"
FIRST = NOTES / "q19_recommendations_3831_first_reading.yaml"
SECOND = NOTES / "q19_recommendations_3831_second_reading.yaml"
NOTE = NOTES / "q19_recommendations_blind_agreement_2026-09-30.md"


def _script():
    spec = importlib.util.spec_from_file_location("q19_blind_agreement",
                                                  ROOT / "scripts" / "q19_blind_agreement.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _readings():
    first = yaml.safe_load(FIRST.read_text(encoding="utf-8"))
    second = yaml.safe_load(SECOND.read_text(encoding="utf-8"))
    packet = json.loads(PACKET.read_text(encoding="utf-8"))
    return first, second, packet


def _rubric_classes():
    """The labels the rubric's "How to answer" section allows, in its order."""
    text = RUBRIC.read_text(encoding="utf-8")
    instruction = text[text.index("Use exactly one of these labels"):].split(". ", 1)[0]
    return re.findall(r"`([a-z_]+)`", instruction)


def test_the_files_are_the_bytes_the_second_reader_was_given():
    first, second, packet = _readings()
    assert _sha256(PACKET) == second["packet_sha256"] == first["packet_sha256"]
    assert _sha256(RUBRIC) == second["rubric_sha256"]
    assert packet["n"] == len(packet["items"]) == 122
    assert "not an independent human rater" in second["rater"]


def test_the_second_reading_covers_exactly_the_first_readings_items_with_the_rubrics_classes():
    first, second, packet = _readings()
    classes = _rubric_classes()
    assert classes == ["named_absence", "placement", "criticism", "request"]
    assert second["classes_allowed"] == classes
    ids = [j["id"] for j in second["judgements"]]
    assert len(ids) == len(set(ids))
    assert set(ids) == set(first["classes"]) == {i["id"] for i in packet["items"]}
    assert set(first["classes"].values()) <= set(classes)
    for j in second["judgements"]:
        assert j["class"] in classes, j
        assert isinstance(j["unsure"], bool), j
        assert isinstance(j["reason"], str) and j["reason"].strip(), j


def test_the_first_reading_is_the_pins_applied_to_the_packet():
    """Every class in the first-reading file is the class its sentence's
    fragment pins in `_RECOMMENDATIONS_READ`, so the file cannot drift from
    the pins without this failing."""
    first, _, packet = _readings()
    sentences = {i["id"]: i["sentence"] for i in packet["items"]}
    by_sentence = {s: i for i, s in sentences.items()}
    assert len(by_sentence) == len(sentences)
    pinned = {}
    for kind, fragments in _RECOMMENDATIONS_READ.items():
        for fragment in fragments:
            hits = _pinned(fragment, list(sentences.values()))
            assert len(hits) == 1, (kind, fragment)
            assert by_sentence[hits[0]] not in pinned, fragment
            pinned[by_sentence[hits[0]]] = kind
    assert pinned == first["classes"]
    assert Counter(pinned.values()) == {"named_absence": 1, "placement": 63, "criticism": 18,
                                        "request": 40}


def test_the_notes_figures_recompute_from_the_two_files():
    first, second, packet = _readings()
    script = _script()
    note = NOTE.read_text(encoding="utf-8")
    assert script.note_block(note) == script.render(first, second, packet)

    # Independently of the script: raw agreement, kappa and the disagreement list.
    one = first["classes"]
    two = {j["id"]: j["class"] for j in second["judgements"]}
    n = len(one)
    agree = sum(one[i] == two[i] for i in one)
    c1, c2 = Counter(one.values()), Counter(two.values())
    pe = sum(c1[c] * c2[c] for c in c1) / n ** 2
    kappa = (agree / n - pe) / (1 - pe)
    stated = re.search(r"All four classes: ([0-9.]+) raw \((\d+)/(\d+)\); kappa ([0-9.]+)", note)
    assert stated, "the note states no overall agreement"
    assert (int(stated[2]), int(stated[3])) == (agree, n)
    assert float(stated[1]) == round(agree / n, 3)
    assert float(stated[4]) == round(kappa, 3)
    listed = re.findall(r"^### (q19r-\d{3}): (\w+) \(first\) / (\w+) \(second\)$", note, re.M)
    assert listed == [(i, one[i], two[i]) for i in sorted(one) if one[i] != two[i]]
    misses = {"first": sum(c in ("named_absence", "placement") for c in one.values()),
              "second": sum(c in ("named_absence", "placement") for c in two.values())}
    assert (f"Q19 misses among the 122: {misses['first']} under the first reading, "
            f"{misses['second']} under the second") in note


def test_every_disagreement_carries_both_reasons():
    first, second, _ = _readings()
    two = {j["id"]: j for j in second["judgements"]}
    disagreeing = {i for i, c in first["classes"].items() if two[i]["class"] != c}
    assert set(first["reasons"]) == disagreeing
    assert all(r["basis"] in ("comment", "reconstructed") and r["reason"].strip()
               for r in first["reasons"].values())
