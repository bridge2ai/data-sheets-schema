"""Typed-container entries whose own prose disclaims their role or presence (#2913).

A read-only lint that never gates. Each list member of a registered container
is read: `creators`, `maintainers` and `data_collectors` record a role, and
`variables`, `instances` and `splits` record that something is present in the
released data. The lint reads the member's own narrative leaves against a
versioned lexicon (`lexicons/self_disclaimed_v1.yaml`). It flags the member
when one of those leaves says the source does not establish that role or
presence: check (a). The lexicon is scoped. A cue counts only where the
sentence is about the member or names the container's own role or presence.
It does not count where a guard shows the clause is about a date, an amount,
an attribute or a study's design. With a coverage receipt, the lint also
reports check (b) in a bucket of its own: each person-role member that no
receipt snippet addressed to it names in one of its container's role
predicates.

Given the final record as well, the lint diffs the two. It follows each flag
on the original to the final by identity (`receipts.remap_path`, #899) and
classifies it:

- `removal_declared`: an audit finding's `remove_relationship` selects the
  member or an ancestor of it.
- `removed`: the final record no longer carries the entry.
- `named_by_finding`: a finding's `review_paths`, `remove_relationship` or
  `original_full` evidence paths name the member itself or one of its
  placement leaves (`id`, `name`, a maintainer's `role`, ...; the lexicon
  lists them per container).
- `identity_unresolved`: the entry cannot be followed to the final record.
- `self_disclaimed_retained`: none of the above.

A finding that names only the member's prose, a count or an affiliation is
about that value, not the placement. A flag counts as retained whether or
not its disclaimer text survived, because deleting a caveat does not dispose
of the entry. Check (b)'s flags are classified the same way, with
`role_predicate_retained` in place of `self_disclaimed_retained`.

A flag is not a semantic judgement. It says that the entry's own words
disclaim its placement. Whether the source supports the placement is review
work. Nothing reads this output as a gate. evidence_assertions,
anonymous_removals, audit_grammar, source_review and receipts do not import
this module, so their import closures are unchanged.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

import yaml

INSTRUMENT = "self_disclaimed v1 (#2913)"
LEXICON_PATH = Path(__file__).parent / "lexicons" / "self_disclaimed_v1.yaml"
LEXICON_RESOURCE = "src/data_sheets_schema/lexicons/self_disclaimed_v1.yaml"
KINDS = ("person_role", "presence")
SCOPES = ("role", "presence", "self", "none")
CLASSIFICATIONS = ("removal_declared", "removed", "named_by_finding", "identity_unresolved")
NON_CHECKS = (
    "whether the source supports the placement: a flag reads the member's own words, never the bundle",
    "prose outside the member's own narrative leaves: nested objects and other members are not read",
    "check (b) reads only receipt snippets addressed to the member, so a listed author whose snippet "
    "quotes only a name is flagged; receipt coverage is partial",
    "whether a finding that names a member justifies keeping it: the audit grammar has no "
    "keep-justification form",
)

_SENTENCE = re.compile(r"(?<=[.!?;:])\s+")
_CLAUSE = re.compile(r",\s+(?=(?:and|but|so|while|whereas|because|although|though|since)\b)", re.I)
_EXCERPT = 240


@dataclass(frozen=True)
class Pattern:
    id: str
    cls: str
    kinds: frozenset
    cue: str
    scope: str
    guards: tuple


@dataclass(frozen=True)
class Container:
    name: str
    kind: str
    narrative_fields: frozenset
    placement_fields: frozenset    # leaves through which a finding names the placement
    cues: tuple                    # (Pattern, compiled cue) for this container
    role_scope: re.Pattern | None  # role terms, role verbs or assignment nouns
    presence_scope: re.Pattern | None
    role_predicates: re.Pattern | None


def _alternation(terms) -> str:
    if not isinstance(terms, list) or not terms or not all(isinstance(t, str) and t for t in terms):
        raise ValueError("a lexicon term list must be a nonempty list of patterns")
    return "|".join(f"(?:{t})" for t in terms)


def _word(terms) -> re.Pattern:
    return re.compile(rf"\b(?:{_alternation(terms)})\b", re.I)


class Lexicon:
    """The lexicon file, parsed and compiled. `sha256` is of its exact bytes,
    so a run's output names the instrument that produced it."""

    def __init__(self, raw: bytes, *, path: str | None = None):
        data = yaml.safe_load(raw.decode("utf-8"))
        if not isinstance(data, dict) or data.get("instrument") != "self_disclaimed":
            raise ValueError("not a self_disclaimed lexicon")
        if type(data.get("version")) is not int:
            raise ValueError("the lexicon needs an integer version")
        self.version = data["version"]
        self.sha256 = hashlib.sha256(raw).hexdigest()
        self.path = path
        narrative = data["narrative"]
        self._fields = frozenset(narrative["fields"])
        self._suffixes = tuple(narrative["suffixes"])
        placement = frozenset(data["placement"]["fields"])
        self._self = [re.compile(p, re.I) for p in data["self_reference"]]
        self._other = [re.compile(p, re.I) for p in data["other_subject"]]
        self._guards = {}
        for name, guard in data["guards"].items():
            if guard.get("reads") not in ("clause", "before_cue", "cue"):
                raise ValueError(f"guard {name} must read the clause, the text before the cue or the cue")
            self._guards[name] = (guard["reads"], re.compile(guard["regex"], re.I))
        assignment = data["assignment_nouns"]
        patterns = []
        for row in data["patterns"]:
            kinds = frozenset(row["kinds"])
            if not kinds <= set(KINDS) or row["scope"] not in SCOPES:
                raise ValueError(f"pattern {row.get('id')} names an unknown kind or scope")
            if set(row["guards"]) - set(self._guards):
                raise ValueError(f"pattern {row['id']} names an unknown guard")
            patterns.append(Pattern(row["id"], row["class"], kinds, row["cue"],
                                    row["scope"], tuple(row["guards"])))
        if len({p.id for p in patterns}) != len(patterns):
            raise ValueError("pattern ids must be unique")
        self.patterns = tuple(patterns)
        self.containers = {}
        for name, spec in data["containers"].items():
            kind = spec["kind"]
            if kind not in KINDS:
                raise ValueError(f"container {name} has unknown kind {kind!r}")
            role = presence = predicates = None
            fill = {}
            if kind == "person_role":
                fill["role"] = _alternation(spec["role_terms"])
                role = _word(spec["role_terms"] + spec["role_verbs"] + assignment)
                predicates = _word(spec["role_predicates"])
            else:
                fill["presence"] = _alternation(spec["presence_terms"])
                presence = _word(spec["presence_terms"])
            cues = []
            for p in patterns:
                if kind in p.kinds:
                    cue = re.sub(r"\{(role|presence)\}", lambda m: fill[m.group(1)], p.cue)
                    cues.append((p, re.compile(cue, re.I)))
            self.containers[name] = Container(
                name, kind, self._fields | frozenset(spec.get("narrative_fields") or ()),
                placement | frozenset(spec.get("placement_fields") or ()),
                tuple(cues), role, presence, predicates)

    def is_narrative(self, container: Container, key: Any) -> bool:
        return isinstance(key, str) and (key in container.narrative_fields
                                         or key.endswith(self._suffixes))

    def describe(self) -> dict:
        return {"path": self.path, "version": self.version, "sha256": self.sha256}


def load_lexicon(path: Path = LEXICON_PATH) -> Lexicon:
    """The registered lexicon, or another lexicon file a test names. The
    registered one is named by its repository-relative spelling wherever
    the package is installed."""
    shown = LEXICON_RESOURCE if path == LEXICON_PATH else str(path)
    return Lexicon(path.read_bytes(), path=shown)


# ------------------------------------------------------------------ paths
def pointer(tokens) -> str:
    return "".join("/" + str(t).replace("~", "~0").replace("/", "~1") for t in tokens)


def parse_pointer(value: str) -> tuple[str, ...]:
    if not isinstance(value, str) or not value.startswith("/") or re.search(r"~(?![01])", value):
        raise ValueError(f"not a JSON Pointer: {value!r}")
    return tuple(part.replace("~1", "/").replace("~0", "~") for part in value[1:].split("/"))


def _dotted(tokens) -> str:
    out = ""
    for t in tokens:
        out += f"[{t}]" if isinstance(t, int) else (f".{t}" if out else str(t))
    return out


def _undotted(path: str) -> tuple:
    return tuple(int(p[1:-1]) if p.startswith("[") else p for p in re.findall(r"\w+|\[\d+\]", path))


def members(record: Any, lexicon: Lexicon) -> Iterator[tuple[tuple, Container, dict]]:
    """Every object member of a registered container, at any depth (a nested
    `resources[*]` or `subsets[*]` dataset carries the same slots)."""
    def walk(value, tokens, ancestors):
        if isinstance(value, (dict, list)):
            if id(value) in ancestors:
                raise ValueError("cyclic record")
            ancestors = ancestors | {id(value)}
        if isinstance(value, dict):
            for key, child in value.items():
                spec = lexicon.containers.get(key) if isinstance(key, str) else None
                if spec is not None and isinstance(child, list):
                    for i, member in enumerate(child):
                        if isinstance(member, dict):
                            yield tokens + (key, i), spec, member
                yield from walk(child, tokens + (key,), ancestors)
        elif isinstance(value, list):
            for i, child in enumerate(value):
                yield from walk(child, tokens + (i,), ancestors)
    yield from walk(record, (), frozenset())


# ---------------------------------------------------------------- check (a)
def _clause(sentence: str, at: int) -> tuple[int, int]:
    start, end = 0, len(sentence)
    for m in _CLAUSE.finditer(sentence):
        if m.end() <= at:
            start = m.end()
        elif m.start() >= at:
            end = m.start()
            break
    return start, end


def _search(patterns, *texts) -> str | None:
    for text in texts:
        for rx in patterns:
            m = rx.search(text)
            if m:
                return m.group(0)
    return None


def _own_names(member: dict) -> list[re.Pattern]:
    """The member's own name as a self-reference: in full, and by its last
    word when it reads as a personal name ("Jane Doe" -> "Doe")."""
    out = []
    for key in ("name", "variable_name"):
        name = member.get(key)
        if not isinstance(name, str) or len(name.strip()) < 3:
            continue
        name = " ".join(name.split())
        out.append(re.compile(rf"\b{re.escape(name)}\b", re.I))
        words = name.split()
        if 2 <= len(words) <= 4 and all(w[:1].isupper() for w in words) and len(words[-1]) >= 4:
            out.append(re.compile(rf"\b{re.escape(words[-1])}\b"))
    return out


def _judge(lexicon, container, member, pattern, sentence, m) -> dict:
    """One cue match: a flag hit, a guarded hit, or out of scope, with why."""
    before = sentence[:m.start()]
    c0, c1 = _clause(sentence, m.start())
    clause, clause_before = sentence[c0:c1], sentence[c0:m.start()]
    out = {"rule": pattern.id, "class": pattern.cls, "cue": m.group(0)}
    # The clause is about someone or something else ("those individuals ...
    # rather than as creators"): its wording disclaims nothing of the member.
    other = _search(lexicon._other, clause_before, clause)
    if other:
        return {**out, "outcome": "out_of_scope", "reason": "other_subject", "term": other}
    selves = lexicon._self + _own_names(member)
    if pattern.scope == "role":
        term = container.role_scope.search(clause)
        if term is None:
            return {**out, "outcome": "out_of_scope", "reason": "no_role_term"}
        out["scope"] = term.group(0)
    elif pattern.scope == "presence":
        term = _search(selves, before, clause_before)
        if term is None:
            found = container.presence_scope.search(clause)
            term = found.group(0) if found else None
        if term is None:
            return {**out, "outcome": "out_of_scope", "reason": "no_self_or_presence_term"}
        out["scope"] = term
    elif pattern.scope == "self":
        term = _search(selves, before, clause_before)
        if term is None:
            return {**out, "outcome": "out_of_scope", "reason": "no_self_reference"}
        out["scope"] = term
    for name in pattern.guards:
        reads, rx = lexicon._guards[name]
        found = rx.search({"clause": clause, "before_cue": clause_before, "cue": m.group(0)}[reads])
        if found:
            return {**out, "outcome": "guarded", "guard": name, "term": found.group(0)}
    return {**out, "outcome": "flag"}


def _texts(value) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [v for v in value if isinstance(v, str)]
    return []


def scan(record: Any, lexicon: Lexicon | None = None) -> dict:
    """Check (a) over one record: `flags` (one entry per flagged member, with
    its hits), `guarded` and `out_of_scope` (cue matches that did not count,
    with why), and the number of members read."""
    lexicon = lexicon or load_lexicon()
    flags, guarded, out_of_scope, count = [], [], [], 0
    for tokens, container, member in members(record, lexicon):
        count += 1
        hits = []
        for key, value in member.items():
            if not lexicon.is_narrative(container, key):
                continue
            for text in _texts(value):
                for sentence in _SENTENCE.split(" ".join(text.split())):
                    for pattern, cue in container.cues:
                        for m in cue.finditer(sentence):
                            row = _judge(lexicon, container, member, pattern, sentence, m)
                            row.update(leaf=pointer(tokens + (key,)), sentence=sentence[:_EXCERPT])
                            outcome = row.pop("outcome")
                            if outcome == "flag":
                                hits.append(row)
                            else:
                                (guarded if outcome == "guarded" else out_of_scope).append(
                                    {"path": pointer(tokens), **row})
        if hits:
            flags.append({"path": pointer(tokens), "container": container.name,
                          "kind": container.kind, "hits": hits})
    return {"members_read": count, "flags": flags, "guarded": guarded, "out_of_scope": out_of_scope}


# ---------------------------------------------------------------- check (b)
def role_predicates(record: Any, receipt: dict, lexicon: Lexicon | None = None) -> dict:
    """Check (b): each person-role member is flagged when no `extracted`
    receipt snippet addressed to it (its own path or a path beneath it)
    carries a role predicate of its container — `no_receipt` when no
    snippet is addressed to it at all, `no_role_predicate` otherwise. Run
    it on the record the receipt was written against."""
    lexicon = lexicon or load_lexicon()
    snippets: list[tuple[str, str]] = []
    for entry in receipt.get("chunks") or []:
        if isinstance(entry, dict) and entry.get("status") == "extracted":
            for pair in entry.get("extracted") or []:
                if isinstance(pair, dict) and isinstance(pair.get("snippet"), str):
                    snippets.append((str(pair.get("slot", "")), " ".join(pair["snippet"].split())))
    flags, supported, count = [], 0, 0
    for tokens, container, _member in members(record, lexicon):
        if container.kind != "person_role":
            continue
        count += 1
        path = _dotted(tokens)
        mine = [s for slot, s in snippets
                if slot == path or slot.startswith(path + ".") or slot.startswith(path + "[")]
        if mine and any(container.role_predicates.search(s) for s in mine):
            supported += 1
            continue
        flags.append({"path": pointer(tokens), "container": container.name,
                      "reason": "no_role_predicate" if mine else "no_receipt",
                      "snippets_addressed": len(mine)})
    return {"members_read": count, "supported": supported, "flags": flags}


# ----------------------------------------------------------------- the diff
def _finding_pointers(audit: Any) -> tuple[list, list, int]:
    """(removals, naming, unreadable): each a list of (finding index, tokens).
    A finding names a path through `review_paths`, `remove_relationship` and
    its `original_full` evidence; other artifacts index other records."""
    if not isinstance(audit, dict) or not isinstance(audit.get("findings"), list):
        raise ValueError("audit.findings must be an array")
    removals, naming, unreadable = [], [], 0

    def take(index, value, into):
        nonlocal unreadable
        try:
            tokens = parse_pointer(value)
        except ValueError:
            unreadable += 1
            return
        for target in into:
            target.append((index, tokens))

    for index, finding in enumerate(audit["findings"]):
        if not isinstance(finding, dict):
            continue
        rule = finding.get("remove_relationship")
        if isinstance(rule, dict) and "path" in rule:
            take(index, rule["path"], (removals, naming))
        paths = finding.get("review_paths")
        for value in paths if isinstance(paths, list) else []:
            take(index, value, (naming,))
        evidence = finding.get("evidence")
        for entry in evidence if isinstance(evidence, list) else []:
            if isinstance(entry, dict) and entry.get("artifact") == "original_full" and "path" in entry:
                if entry["path"] != "@header":
                    take(index, entry["path"], (naming,))
    return removals, naming, unreadable


def _names_member(member: tuple, named: tuple, container: Container) -> bool:
    """The finding path is the member, or runs through one of its placement
    leaves (`/creators/1/name`, `/maintainers/0/role`). A path to its prose
    (`/maintainers/0/source_caveats`) names what the prose says, not the
    placement: v3's bundle-wide-absence finding named that caveat, and
    reconciliation deleted the caveat and kept the entry (#2913)."""
    if named == member:
        return True
    return (len(named) > len(member) and named[:len(member)] == member
            and named[len(member)] in container.placement_fields)


def _follow(tokens: tuple, original: Any, final: Any) -> tuple[tuple | None, str]:
    """Where the member sits in the final record, joined by identity."""
    from data_sheets_schema.receipts import remap_path
    moved = remap_path(_dotted(tokens), original, final)
    if moved["path"] is not None:
        return _undotted(moved["path"]), moved["basis"]
    if moved["basis"] in ("entry_dropped", "leaf_dropped"):
        return None, "removed"
    holder = remap_path(_dotted(tokens[:-1]), original, final)
    if holder["path"] is None and holder["basis"] in ("entry_dropped", "leaf_dropped"):
        return None, "removed"
    if holder["path"] is not None:
        value: Any = final
        for t in _undotted(holder["path"]):
            value = value[t]
        if value is None or value == []:
            return None, "removed"
    return None, moved["basis"]


def classify(flags: list, original: Any, final: Any, *, audit: Any = None,
             final_flags: list | None = None, retained: str = "self_disclaimed_retained",
             lexicon: Lexicon | None = None) -> dict:
    """Each flag on the original, followed to the final and classified."""
    lexicon = lexicon or load_lexicon()
    removals, naming, unreadable = _finding_pointers(audit) if audit is not None else ([], [], 0)
    still = {f["path"] for f in final_flags or []}
    rows, counts = [], {k: 0 for k in (*CLASSIFICATIONS, retained)}
    for flag in flags:
        tokens = parse_pointer(flag["path"])
        member = tuple(int(t) if re.fullmatch(r"0|[1-9][0-9]*", t) else t for t in tokens)
        container = lexicon.containers[flag["container"]]
        where, basis = _follow(member, original, final)
        declared = sorted({i for i, p in removals if len(p) <= len(tokens) and tokens[:len(p)] == p})
        named = sorted({i for i, p in naming if _names_member(tokens, p, container)})
        if declared:
            outcome = "removal_declared"
        elif where is None and basis == "removed":
            outcome = "removed"
        elif where is None:
            outcome = "identity_unresolved"
        elif named:
            outcome = "named_by_finding"
        else:
            outcome = retained
        counts[outcome] += 1
        final_path = pointer(where) if where is not None else None
        row = {"path": flag["path"], "container": flag["container"], "classification": outcome,
               "final_path": final_path, "identity_basis": basis,
               "findings_declaring_removal": declared, "findings_naming_member": named}
        if final_flags is not None:
            row["still_flagged_in_final"] = final_path in still if final_path else False
        rows.append(row)
    return {"rows": rows, "counts": counts, "audit_pointers_unreadable": unreadable}


def diff(original: Any, final: Any, *, audit: Any = None, receipt: dict | None = None,
         lexicon: Lexicon | None = None) -> dict:
    """The original-to-final diff of check (a) and, with a receipt, of check
    (b). `final_only` lists final flags no original flag maps to."""
    lexicon = lexicon or load_lexicon()
    before, after = scan(original, lexicon), scan(final, lexicon)
    lexical = classify(before["flags"], original, final, audit=audit,
                       final_flags=after["flags"], lexicon=lexicon)
    mapped = {row["final_path"] for row in lexical["rows"] if row["final_path"]}
    out = {"original": before, "final": after, "lexicon_diff": lexical,
           "final_only": [f["path"] for f in after["flags"] if f["path"] not in mapped]}
    if receipt is not None:
        checked = role_predicates(original, receipt, lexicon)
        out["role_predicate"] = checked
        out["role_predicate_diff"] = classify(checked["flags"], original, final, audit=audit,
                                              retained="role_predicate_retained", lexicon=lexicon)
    return out


# ------------------------------------------------------------------ files
def check_files(original: Path, final: Path | None = None, audit: Path | None = None,
                receipt: Path | None = None, *, lexicon: Lexicon | None = None) -> dict:
    """The report `d4d review self-disclaimed` prints. Reads exactly the
    files named, records each one's sha256, and writes nothing. `gating` is
    always false. A record with duplicate mapping keys is refused: which
    value a path names would be ambiguous."""
    from data_sheets_schema.evidence_assertions import load_json, load_record
    from data_sheets_schema.receipts import load_receipt
    if audit is not None and final is None:
        raise ValueError("an audit is read against an original/final pair; pass the final record too")
    lexicon = lexicon or load_lexicon()
    inputs: dict[str, dict] = {}

    def read(name, path, parse):
        if path is None:
            return None
        raw = path.read_bytes()
        inputs[name] = {"path": str(path), "sha256": hashlib.sha256(raw).hexdigest()}
        try:
            return parse(raw)
        except (ValueError, yaml.YAMLError) as exc:
            raise ValueError(f"{name} {path}: {exc}") from exc

    before = read("original", original, lambda raw: load_record(raw.decode("utf-8")))
    after = read("final", final, lambda raw: load_record(raw.decode("utf-8")))
    parsed_audit = read("audit", audit, load_json)
    parsed_receipt = read("receipt", receipt, lambda raw: load_receipt(receipt, raw=raw))
    out = {"instrument": INSTRUMENT, "lexicon": lexicon.describe(), "gating": False,
           "inputs": inputs, "non_checks": list(NON_CHECKS)}
    if after is None:
        out["original"] = scan(before, lexicon)
        if parsed_receipt is not None:
            out["role_predicate"] = role_predicates(before, parsed_receipt, lexicon)
    else:
        out.update(diff(before, after, audit=parsed_audit, receipt=parsed_receipt, lexicon=lexicon))
    out["counts"] = _counts(out)
    return out


def _counts(out: dict) -> dict:
    counts = {"original_flags": len(out["original"]["flags"]),
              "original_guarded": len(out["original"]["guarded"]),
              "original_out_of_scope": len(out["original"]["out_of_scope"])}
    if "final" in out:
        counts["final_flags"] = len(out["final"]["flags"])
        counts["final_only"] = len(out["final_only"])
        counts["lexicon_diff"] = out["lexicon_diff"]["counts"]
    if "role_predicate" in out:
        counts["role_predicate_flags"] = len(out["role_predicate"]["flags"])
    if "role_predicate_diff" in out:
        counts["role_predicate_diff"] = out["role_predicate_diff"]["counts"]
    return counts
