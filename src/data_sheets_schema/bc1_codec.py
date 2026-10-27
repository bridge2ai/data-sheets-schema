"""BC1 v1 bounded, lossless JSON representation (D44/D45, 2026-10-27).

The model authors only a candidate. Request and decoded-content hashes are
controller attestations in the separately saved response. A codec pass says
nothing about scientific support. All offsets are end-exclusive UTF-8 bytes.
"""
from __future__ import annotations

import base64
from collections import Counter
import hashlib
import json
import math
import re

FORMAT = "bc1_codec_v1"
DICTIONARY = "bc1_dictionary_v1"
TAG = "$bc1"
LITERAL = "$bc1_literal"
MAX_DEPTH = 64
MAX_NODES = 100_000
MAX_DECODED_BYTES = 2_097_152
MAX_DICTIONARY_BYTES = 16_000_000
WORKER_BYTES = 98_304
INTEGRATION_BYTES = 131_072
CARRY_BYTES = 262_144


class CodecError(ValueError):
    pass


def canonical(value):
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True,
                          separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, UnicodeError, RecursionError) as exc:
        raise CodecError("invalid canonical JSON") from exc


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def _exact(value, keys, label):
    if type(value) is not dict or set(value) != set(keys):
        raise CodecError("invalid " + label + " fields")


def _bounds(value, *, byte_limit=MAX_DECODED_BYTES):
    """Count aliases as occurrences, detect cycles, and bound before dumping."""
    pending, count, size = [(value, 0, frozenset())], 0, 0
    while pending:
        item, depth, ancestors = pending.pop()
        count += 1
        if count > MAX_NODES or depth > MAX_DEPTH:
            raise CodecError("JSON node/depth bound exceeded")
        if type(item) in (dict, list):
            if id(item) in ancestors:
                raise CodecError("JSON cycle")
            ancestors = ancestors | {id(item)}
            size += 2 + max(0, len(item) - 1)
            if type(item) is dict:
                for key, child in item.items():
                    if type(key) is not str:
                        raise CodecError("JSON object key must be text")
                    size += len(canonical(key)) + 1
                    pending.append((child, depth + 1, ancestors))
            else:
                pending.extend((child, depth + 1, ancestors) for child in item)
        elif type(item) in (str, int, float, bool, type(None)):
            if type(item) is float and not math.isfinite(item):
                raise CodecError("nonfinite JSON number")
            size += len(canonical(item))
        else:
            raise CodecError("exact JSON types required")
        if size > byte_limit or len(pending) + count > MAX_NODES:
            raise CodecError("JSON decoded byte/node bound exceeded")


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise CodecError("duplicate JSON key")
        result[key] = value
    return result


def load(raw, *, byte_limit):
    if type(raw) is not bytes or not raw or len(raw) > byte_limit:
        raise CodecError("raw JSON byte bound exceeded")
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique,
                           parse_constant=lambda _: (_ for _ in ()).throw(CodecError("nonfinite JSON number")))
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise CodecError("invalid strict JSON") from exc
    _bounds(value, byte_limit=byte_limit)
    return value


def build_dictionary(*, chunks, slots=(), classes=()):
    """Derive IDs only from the caller's already pinned chunk/schema closure."""
    if type(chunks) is not dict:
        raise CodecError("explicit chunk mapping required")
    rows = []
    for identity in sorted(chunks):
        row = chunks[identity]
        if type(identity) is not str or not identity or type(row) is not dict:
            raise CodecError("invalid source chunk")
        source, text = row.get("source"), row.get("text")
        if type(source) is not str or not source or type(text) is not str:
            raise CodecError("invalid chunk source/text")
        rows.append({"id": identity, "source": source, "text": text,
                     "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()})
    def names(values):
        values = list(values)
        if any(type(s) is not str or not s for s in values):
            raise CodecError("invalid schema dictionary names")
        return sorted(set(values))
    value = {"format": DICTIONARY, "chunks": rows, "slots": names(slots), "classes": names(classes)}
    _bounds(value, byte_limit=MAX_DICTIONARY_BYTES)
    return {**value, "sha256": digest(value)}


def validate_dictionary(dictionary):
    _exact(dictionary, {"format", "chunks", "slots", "classes", "sha256"}, "dictionary")
    if dictionary["format"] != DICTIONARY or type(dictionary["chunks"]) is not list:
        raise CodecError("unsupported dictionary")
    _bounds(dictionary, byte_limit=MAX_DICTIONARY_BYTES)
    chunks = {}
    for row in dictionary["chunks"]:
        _exact(row, {"id", "source", "text", "sha256"}, "chunk dictionary")
        if type(row["id"]) is not str or row["id"] in chunks:
            raise CodecError("duplicate/invalid chunk dictionary id")
        chunks[row["id"]] = {"source": row["source"], "text": row["text"]}
    rebuilt = build_dictionary(chunks=chunks, slots=dictionary["slots"], classes=dictionary["classes"])
    if canonical(rebuilt) != canonical(dictionary):
        raise CodecError("dictionary identity/order mismatch")


def sha256_b64(value):
    if type(value) is not str or not re.fullmatch("[0-9a-f]{64}", value):
        raise CodecError("exact lowercase SHA-256 required")
    return base64.b64encode(bytes.fromhex(value)).decode("ascii")


def _unsha(value):
    if type(value) is not str or len(value) != 44:
        raise CodecError("invalid sha256_b64")
    try:
        raw = base64.b64decode(value, validate=True)
    except (ValueError, UnicodeError) as exc:
        raise CodecError("invalid sha256_b64") from exc
    if len(raw) != 32 or base64.b64encode(raw).decode("ascii") != value:
        raise CodecError("noncanonical sha256_b64")
    return raw.hex()


def decode_candidate(raw, *, dictionary, max_bytes=WORKER_BYTES,
                     max_decoded_bytes=MAX_DECODED_BYTES):
    validate_dictionary(dictionary)
    envelope = load(raw, byte_limit=max_bytes)
    _exact(envelope, {"format", "dictionary_sha256", "strings", "body"}, "candidate")
    if envelope["format"] != FORMAT or envelope["dictionary_sha256"] != dictionary["sha256"]:
        raise CodecError("candidate format/dictionary mismatch")
    strings = envelope["strings"]
    if type(strings) is not list or any(type(s) is not str for s in strings) or len(set(strings)) != len(strings):
        raise CodecError("invalid text dictionary")
    # Each expansion is charged before constructing an output collection/span.
    count, size = 0, 0
    def charge(n):
        nonlocal size
        size += n
        if size > max_decoded_bytes:
            raise CodecError("expanded byte bound exceeded")
    def scalar(item):
        charge(len(canonical(item)))
        return item
    def ordinal(value, rows):
        if type(value) is not int or not 0 <= value < len(rows):
            raise CodecError("dictionary ordinal invalid")
        return rows[value]
    def visit(item, depth=0):
        nonlocal count
        count += 1
        if count > MAX_NODES or depth > MAX_DEPTH:
            raise CodecError("expanded node/depth bound exceeded")
        if type(item) is dict:
            if TAG in item:
                _exact(item, {TAG}, "tag")
                tag = item[TAG]
                if type(tag) is not list or len(tag) != 2 or type(tag[0]) is not str:
                    raise CodecError("invalid codec tag")
                kind, arg = tag
                if kind == "text":
                    return scalar(ordinal(arg, strings))
                if kind in ("chunk", "slot", "class"):
                    rows = dictionary[{"chunk": "chunks", "slot": "slots", "class": "classes"}[kind]]
                    value = ordinal(arg, rows)
                    return scalar(value["id"] if kind == "chunk" else value)
                if kind == "sha256_b64":
                    return scalar(_unsha(arg))
                if kind == "span":
                    _exact(arg, {"chunk", "span"}, "span")
                    chunk = ordinal(arg["chunk"], dictionary["chunks"])
                    bounds = arg["span"]
                    if type(bounds) is not list or len(bounds) != 2 or any(type(n) is not int for n in bounds):
                        raise CodecError("invalid span offsets")
                    start, end = bounds
                    data = chunk["text"].encode("utf-8")
                    if not 0 <= start <= end <= len(data) or end - start + size > max_decoded_bytes:
                        raise CodecError("span byte bound exceeded")
                    try:
                        value = data[start:end].decode("utf-8", errors="strict")
                    except UnicodeError as exc:
                        raise CodecError("span splits UTF-8") from exc
                    return scalar(value)
                raise CodecError("unknown codec tag")
            if LITERAL in item:
                _exact(item, {LITERAL}, "literal escape")
                pairs = item[LITERAL]
                if type(pairs) is not list:
                    raise CodecError("invalid literal pairs")
            else:
                pairs = list(item.items())
            charge(2 + max(0, len(pairs) - 1))
            result = {}
            for pair in pairs:
                if type(pair) not in (list, tuple) or len(pair) != 2 or type(pair[0]) is not str or pair[0] in result:
                    raise CodecError("invalid/duplicate literal key")
                key, child = pair
                charge(len(canonical(key)) + 1)
                result[key] = visit(child, depth + 1)
            return result
        if type(item) is list:
            charge(2 + max(0, len(item) - 1))
            return [visit(child, depth + 1) for child in item]
        return scalar(item)
    result = visit(envelope["body"])
    _bounds(result, byte_limit=max_decoded_bytes)
    return result


def encode_candidate(value, *, dictionary, max_bytes=WORKER_BYTES,
                     max_decoded_bytes=MAX_DECODED_BYTES):
    """Deterministic optimization; source spans search only adjacent named evidence."""
    validate_dictionary(dictionary)
    _bounds(value, byte_limit=max_decoded_bytes)
    counts = Counter()
    pending = [value]
    while pending:
        item = pending.pop()
        if type(item) is str and len(item.encode("utf-8")) >= 24:
            counts[item] += 1
        elif type(item) is dict:
            pending.extend(item[k] for k in sorted(item, reverse=True))
        elif type(item) is list:
            pending.extend(reversed(item))
    strings = []
    for text, n in counts.items():
        ref = {TAG: ["text", len(strings)]}
        if n > 1 and (n - 1) * len(canonical(text)) > n * len(canonical(ref)) + 1:
            strings.append(text)
    text_ids = {text: i for i, text in enumerate(strings)}
    chunk_ids = {row["id"]: i for i, row in enumerate(dictionary["chunks"])}
    slot_ids = {text: i for i, text in enumerate(dictionary["slots"])}
    class_ids = {text: i for i, text in enumerate(dictionary["classes"])}
    def visit(item, key=None, parent=None):
        if type(item) is str:
            options = [item]
            if item in text_ids:
                options.append({TAG: ["text", text_ids[item]]})
            ids = chunk_ids if key == "chunk" else slot_ids if key in ("slot", "slot_chain") else class_ids if key in ("class", "root_class", "owner_class") else {}
            if item in ids:
                options.append({TAG: [{"chunk": "chunk", "slot": "slot", "slot_chain": "slot"}.get(key, "class"), ids[item]]})
            if key and (key == "sha256" or key.endswith("_sha256")) and re.fullmatch("[0-9a-f]{64}", item):
                options.append({TAG: ["sha256_b64", sha256_b64(item)]})
            if key == "quote" and type(parent) is dict and parent.get("chunk") in chunk_ids:
                index = chunk_ids[parent["chunk"]]
                chunk = dictionary["chunks"][index]
                if parent.get("source") == chunk["source"]:
                    data, needle = chunk["text"].encode("utf-8"), item.encode("utf-8")
                    start = data.find(needle)
                    if start >= 0:
                        options.append({TAG: ["span", {"chunk": index, "span": [start, start + len(needle)]}]})
            return min(options, key=lambda option: len(canonical(option)))
        if type(item) is dict:
            values = {k: visit(item[k], k, item) for k in sorted(item)}
            return {LITERAL: [[k, v] for k, v in values.items()]} if TAG in item or LITERAL in item else values
        if type(item) is list:
            return [visit(child, key, parent) for child in item]
        return item
    raw = canonical({"format": FORMAT, "dictionary_sha256": dictionary["sha256"],
                     "strings": strings, "body": visit(value)})
    if len(raw) > max_bytes:
        raise CodecError("visible output byte bound exceeded")
    decoded = decode_candidate(raw, dictionary=dictionary, max_bytes=max_bytes,
                               max_decoded_bytes=max_decoded_bytes)
    if canonical(decoded) != canonical(value):
        raise CodecError("deterministic round-trip mismatch")
    return raw


def contract():
    return {"format": FORMAT, "candidate_fields": ["format", "dictionary_sha256", "strings", "body"],
            "tags": ["text", "chunk", "slot", "class", "sha256_b64", "span"],
            "rule": "Return a strict JSON candidate. Copy dictionary_sha256 from the request. $bc1 is [tag, argument]; text/chunk/slot/class use zero-based integer IDs. sha256_b64 holds canonical base64 of exactly32 digest bytes. span uses {chunk: integer, span: [start,end]} with end-exclusive UTF-8 byte offsets. Escape literal objects containing $bc1 or $bc1_literal as {$bc1_literal:[[key,value],...]}. Every decoded claim, reason, attribution, status and evidence assertion is required. Literal strings are always allowed. The controller alone hashes newly authored decoded output."}
