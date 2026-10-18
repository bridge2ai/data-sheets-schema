"""The blind second readings of the 122 Q19 recommendations (#3831, #3871).

The second reading of record (made with the rating files step 3b asks about)
and the earlier reading made without them (a recorded deviation) must each
cover exactly the first reading's items and use only the rubric's classes. The
first reading must be the `_RECOMMENDATIONS_READ` pins and nothing else, and
the agreement note's figures must recompute from the files. Fixture-only: no
corpus walk.
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
WITHOUT = NOTES / "q19_recommendations_3831_second_reading_without_sources.yaml"
NOTE = NOTES / "q19_recommendations_blind_agreement_2026-09-30.md"
SOURCES_GIVEN = NOTES / "q19_recommendations_3831_sources_given.yaml"


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
    without = yaml.safe_load(WITHOUT.read_text(encoding="utf-8"))
    return first, second, packet, without


def _rubric_classes():
    """The labels the rubric's "How to answer" section allows, in its order."""
    text = RUBRIC.read_text(encoding="utf-8")
    instruction = text[text.index("Use exactly one of these labels"):].split(". ", 1)[0]
    return re.findall(r"`([a-z_]+)`", instruction)


def test_the_files_are_the_bytes_the_second_readers_were_given():
    first, second, packet, without = _readings()
    for reading in (second, without):
        assert _sha256(PACKET) == reading["packet_sha256"] == first["packet_sha256"]
        assert _sha256(RUBRIC) == reading["rubric_sha256"]
        assert "not an independent human rater" in reading["rater"]
    assert packet["n"] == len(packet["items"]) == 122
    # The reading of record is the one made with the step 3b sources; the
    # other is kept, labelled, as the deviation it is.
    assert second["reading"] == "with_sources"
    assert without["reading"] == "without_sources"
    assert second["second_reading_json_sha256"] != without["second_reading_json_sha256"]
    assert "NOT the second reading of record" in WITHOUT.read_text(encoding="utf-8")


def test_the_rating_files_given_to_the_reader_of_record_are_the_checkouts_bytes():
    """The manifest records the sha256 of each copy the reader of record was
    given under q19_sources/. Its paths are exactly the packet's sources, and
    each hash is this checkout's file. This attests the bytes of the copies;
    which of them the reader opened is its own report."""
    _, _, packet, _ = _readings()
    files = {s["file"] for i in packet["items"] for s in i["sources"]}
    assert len(files) == 84
    given = yaml.safe_load(SOURCES_GIVEN.read_text(encoding="utf-8"))["files"]
    assert set(given) == files
    for path, sha256 in given.items():
        assert re.fullmatch(r"[0-9a-f]{64}", sha256), path
        assert (ROOT / path).is_file(), path
        assert _sha256(ROOT / path) == sha256, path


def test_each_second_reading_covers_exactly_the_first_readings_items_with_the_rubrics_classes():
    first, second, packet, without = _readings()
    classes = _rubric_classes()
    assert classes == ["named_absence", "placement", "criticism", "request"]
    assert set(first["classes"].values()) <= set(classes)
    for reading in (second, without):
        assert reading["classes_allowed"] == classes
        ids = [j["id"] for j in reading["judgements"]]
        assert ids == [i["id"] for i in packet["items"]]  # packet order, each once
        assert set(ids) == set(first["classes"])
        for j in reading["judgements"]:
            assert set(j) == {"id", "class", "unsure", "reason"}, j
            assert j["class"] in classes, j
            assert isinstance(j["unsure"], bool), j
            assert isinstance(j["reason"], str) and j["reason"].strip(), j


def test_the_first_reading_is_the_pins_applied_to_the_packet():
    """Every class in the first-reading file is the class its sentence's
    fragment pins in `_RECOMMENDATIONS_READ`, so the file cannot drift from
    the pins without this failing."""
    first, _, packet, _ = _readings()
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


def _kappa(one, two):
    """Cohen's kappa and raw agreement, independently of the script."""
    n = len(one)
    agree = sum(one[i] == two[i] for i in one)
    c1, c2 = Counter(one.values()), Counter(two.values())
    pe = sum(c1[c] * c2[c] for c in c1) / n ** 2
    return agree, n, (agree / n - pe) / (1 - pe)


def _stated(section):
    found = re.search(r"All four classes: ([0-9.]+) raw \((\d+)/(\d+)\); kappa ([0-9.]+)", section)
    assert found, "the section states no overall agreement"
    return found


def _section(note, heading):
    start = note.index(heading)
    nxt = note.find("\n### ", start + 1)
    return note[start:nxt if nxt != -1 else len(note)]


def test_the_notes_figures_recompute_from_the_files():
    first, second, packet, without = _readings()
    script = _script()
    note = NOTE.read_text(encoding="utf-8")
    assert script.note_block(note) == script.render(first, second, packet, without)

    one = first["classes"]
    two = {j["id"]: j["class"] for j in second["judgements"]}
    wo = {j["id"]: j["class"] for j in without["judgements"]}
    misses = lambda m: sum(c in ("named_absence", "placement") for c in m.values())  # noqa: E731

    # Independently of the script: each pair's raw agreement and kappa, and
    # every disagreement listed in its section.
    record = _section(note, "### The second reading of record")
    agree, n, kappa = _kappa(one, two)
    stated = _stated(record)
    assert (int(stated[2]), int(stated[3])) == (agree, n)
    assert float(stated[1]) == round(agree / n, 3)
    assert float(stated[4]) == round(kappa, 3)
    listed = re.findall(r"^#### (q19r-\d{3}): (\w+) \(first\) / (\w+) \(second\)$", record, re.M)
    assert listed == [(i, one[i], two[i]) for i in sorted(one) if one[i] != two[i]]
    assert (f"Q19 misses among the 122: {misses(one)} under the first reading, "
            f"{misses(two)} under the second") in record

    deviation = _section(note, "### The reading made without the step 3b sources")
    agree, n, kappa = _kappa(one, wo)
    stated = _stated(deviation)
    assert (int(stated[2]), int(stated[3]), float(stated[4])) == (agree, n, round(kappa, 3))
    rows = re.findall(r"^\| (q19r-\d{3}) \| (\w+) \| (\w+)(?: \(unsure\))? \|", deviation, re.M)
    assert rows == [(i, one[i], wo[i]) for i in sorted(one) if one[i] != wo[i]]

    between = _section(note, "### The two second readings against each other")
    agree, n, kappa = _kappa(wo, two)
    stated = _stated(between)
    assert (int(stated[2]), int(stated[3]), float(stated[4])) == (agree, n, round(kappa, 3))
    changed = re.findall(r"^#### (q19r-\d{3}): (\w+) \(without\) / (\w+) \(with\)", between, re.M)
    assert changed == [(i, wo[i], two[i]) for i in sorted(one) if wo[i] != two[i]]


def test_the_reading_of_record_is_the_one_the_note_headlines():
    """The headline figures are the reading of record's, not the deviation's."""
    first, second, packet, without = _readings()
    script = _script()
    one = first["classes"]
    r = script.agreement(one, script.classes_of(second))
    block = script.note_block(NOTE.read_text(encoding="utf-8"))
    first_line = next(line for line in block.splitlines() if line.startswith("- All four classes"))
    assert f"kappa {r['all']['kappa']:.3f}" in first_line
    assert r["all"]["kappa"] != script.agreement(one, script.classes_of(without))["all"]["kappa"]


def test_every_disagreement_carries_both_reasons():
    """The first reading gives a reason for exactly the items either second
    reading classes differently."""
    first, second, _, without = _readings()
    disagreeing = set()
    for reading in (second, without):
        two = {j["id"]: j for j in reading["judgements"]}
        disagreeing |= {i for i, c in first["classes"].items() if two[i]["class"] != c}
    assert set(first["reasons"]) == disagreeing
    assert all(r["basis"] in ("comment", "reconstructed") and r["reason"].strip()
               for r in first["reasons"].values())
