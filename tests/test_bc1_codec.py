"""BC1 causal representation tests; no provider or scientific acceptance."""
from copy import deepcopy
import hashlib

import pytest

from data_sheets_schema import bc1_codec as c


@pytest.fixture
def dictionary():
    return c.build_dictionary(chunks={"source-chunk-0001": {
        "source": "manual.txt", "text": "prefix é 🧬\r\n" + "complete quoted source wording " * 20}},
        slots=["a_very_long_schema_slot", "short"], classes=["Dataset"])


def candidate(dictionary, body, strings=None):
    return c.canonical({"format": c.FORMAT, "dictionary_sha256": dictionary["sha256"],
                        "strings": strings or [], "body": body})


def test_exact_roundtrip_preserves_values_and_reserved_literal_objects(dictionary):
    value = {"none": None, "false": False, "zero": 0, "float": 1.25,
        "list": ["é", "e\u0301", "\r\n", "🧬", ""],
        c.TAG: ["literal", {c.LITERAL: [["a", "literal content"]]}],
        "repeated": ["full claim with attribution and qualification " * 4] * 9,
        "source": "manual.txt", "chunk": "source-chunk-0001",
        "quote": "complete quoted source wording " * 12,
        "sha256": hashlib.sha256(b"original bytes").hexdigest()}
    raw = c.encode_candidate(value, dictionary=dictionary)
    assert c.canonical(c.decode_candidate(raw, dictionary=dictionary)) == c.canonical(value)
    assert c.encode_candidate(value, dictionary=dictionary) == raw
    assert b'"span"' in raw


@pytest.mark.parametrize("tag,arg,expected", [
    ("chunk", 0, "source-chunk-0001"), ("slot", 0, "a_very_long_schema_slot"),
    ("class", 0, "Dataset"), ("text", 0, "exact text"),
    ("sha256_b64", c.sha256_b64("ab" * 32), "ab" * 32),
])
def test_dictionary_and_digest_tags(dictionary, tag, arg, expected):
    assert c.decode_candidate(candidate(dictionary, {c.TAG: [tag, arg]}, ["exact text"]), dictionary=dictionary) == expected


@pytest.mark.parametrize("arg", [-1, True, 1, 0.0, "0"])
def test_bad_reference_cannot_alias_valid_entry(dictionary, arg):
    with pytest.raises(ValueError):
        c.decode_candidate(candidate(dictionary, {c.TAG: ["chunk", arg]}), dictionary=dictionary)


@pytest.mark.parametrize("body", [
    {c.TAG: ["unknown", 0]}, {c.TAG: ["text", 0], "extra": 1},
    {c.LITERAL: [["a", 1], ["a", 2]]}, {c.LITERAL: [[1, "a"]]},
    {c.TAG: ["sha256_b64", "A" * 42 + "B="]},
    {c.TAG: ["span", {"chunk": 0, "span": [True, 2]}]},
    {c.TAG: ["span", {"chunk": 0, "span": [8, 9]}]},
    {c.TAG: ["span", {"chunk": 0, "span": [0, 1000000]}]},
])
def test_malformed_tags_fail_closed(dictionary, body):
    with pytest.raises(ValueError):
        c.decode_candidate(candidate(dictionary, body), dictionary=dictionary)


def test_utf8_offsets_are_bytes_and_owner_search_is_local(dictionary):
    data = dictionary["chunks"][0]["text"].encode()
    start = data.index("🧬".encode())
    body = {c.TAG: ["span", {"chunk": 0, "span": [start, start + 4]}]}
    assert c.decode_candidate(candidate(dictionary, body), dictionary=dictionary) == "🧬"
    value = {"source": "foreign.txt", "chunk": "source-chunk-0001", "quote": "complete quoted source wording " * 12}
    encoded = c.encode_candidate(value, dictionary=dictionary)
    assert b'"span"' not in encoded
    assert c.decode_candidate(encoded, dictionary=dictionary) == value


def test_dictionary_and_envelope_hashes_are_independently_bound(dictionary):
    encoded = c.encode_candidate({"value": "text"}, dictionary=dictionary)
    changed = deepcopy(dictionary)
    changed["chunks"][0]["text"] += "tampered"
    with pytest.raises(ValueError, match="dictionary"):
        c.decode_candidate(encoded, dictionary=changed)
    other = c.build_dictionary(chunks={"source-chunk-0001": {"source": "manual.txt", "text": "other"}})
    with pytest.raises(ValueError, match="mismatch"):
        c.decode_candidate(encoded, dictionary=other)


def test_raw_and_expanded_caps_are_distinct(dictionary):
    text = "repeated exact statement " * 30
    raw = candidate(dictionary, [{c.TAG: ["text", 0]}] * 100, [text])
    assert len(raw) < 10000
    with pytest.raises(ValueError, match="expanded"):
        c.decode_candidate(raw, dictionary=dictionary, max_decoded_bytes=10000)
    with pytest.raises(ValueError, match="raw JSON"):
        c.decode_candidate(raw + b" " * c.WORKER_BYTES, dictionary=dictionary)
    with pytest.raises(ValueError, match="visible output"):
        c.encode_candidate("x" * 1000, dictionary=dictionary, max_bytes=100)


@pytest.mark.parametrize("raw", [b'{"a":1,"a":2}', b'{"a":NaN}', b'{"a":"\\ud800"}', b'[] trailing'])
def test_strict_parser_refuses_ambiguous_json(raw):
    with pytest.raises(ValueError):
        c.load(raw, byte_limit=1000)


def test_cycles_and_depth_are_bounded_before_encoding(dictionary):
    value = []
    value.append(value)
    with pytest.raises(ValueError, match="cycle"):
        c.encode_candidate(value, dictionary=dictionary)
    value = 0
    for _ in range(c.MAX_DEPTH + 2):
        value = [value]
    with pytest.raises(ValueError, match="depth"):
        c.encode_candidate(value, dictionary=dictionary)


def test_model_cannot_submit_controller_decoded_hash(dictionary):
    value = c.load(candidate(dictionary, {}), byte_limit=1000)
    value["decoded_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="fields"):
        c.decode_candidate(c.canonical(value), dictionary=dictionary)
