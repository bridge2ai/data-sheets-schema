"""Registered, versioned phrase lexicons for deterministic text lints (#2919).

A lexicon is a YAML file under `lexicons/` that names itself, its version and
the instrument it defines, declares the classes it reports, and lists
class-tagged patterns. Each pattern has an id, a regular expression, at least
one example it must match (`parse` refuses a pattern with none, or with a
blank one) and a counterexample it must not. A lexicon that declares
`counterexamples_required: true` has `parse` refuse a pattern without a
counterexample, and `check_registry` requires that declaration of every
registered lexicon except those registered before the rule
(`COUNTEREXAMPLES_OPTIONAL`, #3132): for a pattern without a counterexample
the self-test shows that it matches what it should, not that it misses
anything. The rule is a declaration in the lexicon's bytes rather than a
version number, so the file says which rule its self-test was held to.
A lexicon may also carry a `scope` block that its reader interprets (which
keys of a record it walks, for instance); the loader passes it through.

`lexicons/registry.yaml` pins each registered file by sha256. A change to a
registered file's bytes, comments included, is refused by `load` and fails
`tests/test_lexicons.py`. The change is a new version: a new file beside the
old one and a new registry entry, so a count made under the old bytes can
still be reproduced from them. This is the prompt registry's rule (#432) at
the scale of one data file, and the next lexicons are meant to use it too
(#2913's role/presence negations, #2917's status markers).

Every result computed from a lexicon should carry `Lexicon.identity()`: the
name, version, instrument, file and sha256 of the bytes the patterns were
compiled from. A count reported without them cannot be compared with
another.

The pin rule is not specific to this file shape (#3040). `registered_bytes`,
`check_declared` and `check_pins` hold it for any directory that keeps a
`registry.yaml` of this form, whatever its lexicons parse into:
`container_lexicons/` (#2913) is pinned through them with its own reader.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import yaml

LEXICON_DIR = Path(__file__).parent / "lexicons"
REGISTRY_FILE = "registry.yaml"

#: The only flags a lexicon may name. A flag changes what every pattern
#: matches, so it is part of the lexicon's bytes like the patterns are.
FLAGS = {"IGNORECASE": re.IGNORECASE}

_TOP_KEYS = {"name", "version", "instrument", "counterexamples_required", "flags", "scope", "classes",
             "patterns"}
_PATTERN_KEYS = {"id", "class", "regex", "examples", "counterexamples"}


#: The registered lexicons whose patterns may lack a counterexample: those
#: registered before #3132 made one required. Closed — a lexicon registered
#: since declares `counterexamples_required: true`, and a version of one of
#: these is a new registration, not a member.
COUNTEREXAMPLES_OPTIONAL = frozenset({("absence_self_narration", 1)})


class LexiconError(ValueError):
    """A lexicon file or registry entry that cannot be used as registered."""


@dataclass(frozen=True)
class Pattern:
    id: str
    cls: str
    regex: re.Pattern
    examples: tuple[str, ...] = ()
    counterexamples: tuple[str, ...] = ()


@dataclass(frozen=True)
class Lexicon:
    name: str
    version: int
    instrument: str
    file: str
    sha256: str
    classes: dict[str, str]
    patterns: tuple[Pattern, ...]
    scope: dict[str, Any] = field(default_factory=dict)
    counterexamples_required: bool = False

    def identity(self) -> dict[str, Any]:
        """What a result must carry to say which lexicon produced it."""
        return {"name": self.name, "version": self.version, "instrument": self.instrument,
                "file": self.file, "sha256": self.sha256}


def _read_registry(directory: Path) -> dict[str, list[dict[str, Any]]]:
    path = directory / REGISTRY_FILE
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise LexiconError(f"{path} could not be read: {exc}") from exc
    entries = (data or {}).get("lexicons") if isinstance(data, dict) else None
    if not isinstance(entries, dict):
        raise LexiconError(f"{path} has no `lexicons` mapping")
    for name, versions in entries.items():
        if not isinstance(versions, list) or not versions:
            raise LexiconError(f"{path}: {name!r} lists no registered versions")
        for entry in versions:
            if (not isinstance(entry, dict) or not {"version", "file", "sha256"} <= set(entry)
                    or type(entry["version"]) is not int):
                raise LexiconError(f"{path}: every {name!r} entry needs an integer version, a file and a sha256")
    return entries


def registered(directory: Path = LEXICON_DIR) -> dict[str, list[dict[str, Any]]]:
    """The registry: lexicon name -> its registered versions, as written."""
    return _read_registry(directory)


def parse(raw: bytes, *, file: str) -> Lexicon:
    """Compile a lexicon from its bytes, checking its shape but not its pin.

    `load` is the route for a registered lexicon. This one compiles bytes
    that are not registered — a draft of the next version, or a test's —
    and says what is wrong with their shape.
    """
    try:
        data = yaml.safe_load(raw.decode("utf-8"))
    except (UnicodeDecodeError, yaml.YAMLError) as exc:
        raise LexiconError(f"{file} does not parse: {exc}") from exc
    if not isinstance(data, dict):
        raise LexiconError(f"{file} is not a mapping")
    unknown = set(data) - _TOP_KEYS
    missing = {"name", "version", "instrument", "classes", "patterns"} - set(data)
    if unknown or missing:
        raise LexiconError(f"{file}: unknown keys {sorted(map(str, unknown))}, missing keys {sorted(missing)}")
    if type(data["version"]) is not int or data["version"] < 1:
        raise LexiconError(f"{file}: version must be a positive integer")
    required = data.get("counterexamples_required", False)
    if type(required) is not bool:
        raise LexiconError(f"{file}: counterexamples_required must be true or false")
    classes = data["classes"]
    if not isinstance(classes, dict) or not classes:
        raise LexiconError(f"{file}: `classes` must map each class to its description")
    flags = 0
    for name in data.get("flags") or []:
        if name not in FLAGS:
            raise LexiconError(f"{file}: unknown flag {name!r}; allowed {sorted(FLAGS)}")
        flags |= FLAGS[name]
    patterns: list[Pattern] = []
    seen: set[str] = set()
    for row in data["patterns"] or []:
        if not isinstance(row, dict) or set(row) - _PATTERN_KEYS or not {"id", "class", "regex"} <= set(row):
            raise LexiconError(f"{file}: a pattern needs id, class and regex and nothing but {sorted(_PATTERN_KEYS)}")
        pid = str(row["id"])
        if pid in seen:
            raise LexiconError(f"{file}: pattern id {pid!r} is used twice")
        seen.add(pid)
        if row["class"] not in classes:
            raise LexiconError(f"{file}: pattern {pid!r} names undeclared class {row['class']!r}")
        for key in ("examples", "counterexamples"):
            texts = row.get(key) or []
            if not isinstance(texts, list) or not all(isinstance(t, str) for t in texts):
                raise LexiconError(f"{file}: pattern {pid!r} {key} must be a list of strings "
                                   "(quote a text that contains ': ')")
            if any(not t.strip() for t in texts):
                raise LexiconError(f"{file}: pattern {pid!r} has a blank entry in {key}, which attests nothing")
        if not row.get("examples"):
            # Without one the self-test cannot fail for the pattern: a regex
            # that matches every string, or none, would pass `check_registry`.
            raise LexiconError(f"{file}: pattern {pid!r} lists no examples; a pattern must name at least "
                               "one text it has to match")
        if required and not row.get("counterexamples"):
            raise LexiconError(f"{file}: pattern {pid!r} lists no counterexamples, and this lexicon declares "
                               "counterexamples_required")
        if not isinstance(row["regex"], str):
            raise LexiconError(f"{file}: pattern {pid!r} regex must be a string")
        try:
            compiled = re.compile(row["regex"], flags)
        except re.error as exc:
            raise LexiconError(f"{file}: pattern {pid!r} does not compile: {exc}") from exc
        patterns.append(Pattern(id=pid, cls=row["class"], regex=compiled,
                                examples=tuple(row.get("examples") or ()),
                                counterexamples=tuple(row.get("counterexamples") or ())))
    unused = set(classes) - {p.cls for p in patterns}
    if unused:
        raise LexiconError(f"{file}: classes with no pattern: {sorted(unused)}")
    scope = data.get("scope") or {}
    if not isinstance(scope, dict):
        raise LexiconError(f"{file}: `scope` must be a mapping")
    return Lexicon(name=str(data["name"]), version=data["version"], instrument=str(data["instrument"]),
                   file=file, sha256=hashlib.sha256(raw).hexdigest(), classes=dict(classes),
                   patterns=tuple(patterns), scope=scope, counterexamples_required=required)


def registered_bytes(name: str, version: int | None = None, *,
                     directory: Path = LEXICON_DIR) -> tuple[dict[str, Any], bytes]:
    """A registered file's entry and its bytes, the newest version unless one
    is named; refused when the bytes are not the pinned ones.

    Shared by every registry of this form (#3040): what the bytes parse into
    is the caller's business, and `check_declared` is then its check that
    they name the lexicon and version the entry does.
    """
    versions = _read_registry(directory).get(name)
    if not versions:
        raise LexiconError(f"no lexicon {name!r} is registered in {directory / REGISTRY_FILE}")
    newest = max(e["version"] for e in versions)
    entry = next((e for e in versions if e["version"] == (newest if version is None else version)), None)
    if entry is None:
        raise LexiconError(f"lexicon {name!r} has no registered version {version}")
    path = directory / entry["file"]
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise LexiconError(f"registered lexicon {path} could not be read: {exc.strerror}") from exc
    digest = hashlib.sha256(raw).hexdigest()
    if digest != entry["sha256"]:
        raise LexiconError(
            f"{path} hashes to {digest[:12]}…, not the registered {str(entry['sha256'])[:12]}…; a registered "
            f"lexicon is never edited — add {name}_v{newest + 1}.yaml and a registry entry instead")
    return entry, raw


def check_declared(path: Path, entry_name: str, entry_version: int, declared_name: str,
                   declared_version: int) -> None:
    """Refuse a file that names another lexicon or version than its registry
    entry: a result that claims v1 must have been computed from v1's bytes."""
    if declared_name != entry_name or declared_version != entry_version:
        raise LexiconError(f"{path} declares {declared_name} v{declared_version}; "
                           f"the registry entry is {entry_name} v{entry_version}")


def load(name: str, version: int | None = None, *, directory: Path = LEXICON_DIR) -> Lexicon:
    """A registered lexicon, the newest version unless one is named.

    Refused when the file's bytes are not the registered ones, or when the
    file names another lexicon or version than its registry entry: a result
    that claims v1 must have been computed from v1's bytes.
    """
    entry, raw = registered_bytes(name, version, directory=directory)
    lexicon = parse(raw, file=entry["file"])
    check_declared(directory / entry["file"], name, entry["version"], lexicon.name, lexicon.version)
    return lexicon


def check_pins(directory: Path, load_version: Callable[[str, int], Any],
               check_loaded: Callable[[str, Any], list[str]] | None = None) -> list[str]:
    """The registry checks every registered directory shares (#3040), as
    messages; [] when none.

    Each registered version is loaded through `load_version(name, version)`,
    which is to read it through `registered_bytes` and `check_declared`, so
    its pin and its declared name and version are checked; a `ValueError`
    from it is reported, not raised. The file name must be
    `{name}_v{version}.yaml`, no version is registered twice, and no `.yaml`
    file in the directory is unregistered — an unregistered file is a
    lexicon nothing pins. `check_loaded(name, loaded)` adds a reader's own
    checks for each version that loaded.
    """
    problems: list[str] = []
    try:
        entries = _read_registry(directory)
    except LexiconError as exc:
        return [str(exc)]
    files: set[str] = set()
    for name, versions in sorted(entries.items()):
        numbers = [e["version"] for e in versions]
        if len(numbers) != len(set(numbers)):
            problems.append(f"{name}: a version is registered twice")
        for entry in versions:
            files.add(entry["file"])
            if entry["file"] != f"{name}_v{entry['version']}.yaml":
                problems.append(f"{name} v{entry['version']}: file {entry['file']!r} is not "
                                f"{name}_v{entry['version']}.yaml")
            try:
                loaded = load_version(name, entry["version"])
            except ValueError as exc:
                problems.append(str(exc))
                continue
            if check_loaded is not None:
                problems += check_loaded(name, loaded)
    for path in sorted(directory.glob("*.yaml")):
        if path.name != REGISTRY_FILE and path.name not in files:
            problems.append(f"{path.name} is in {directory} but not registered")
    return problems


def check_registry(directory: Path = LEXICON_DIR) -> list[str]:
    """Every problem with the registered lexicons, as messages; [] when none.

    `check_pins`' checks — each pin against the file's bytes, the file name
    against `{name}_v{version}.yaml`, and that no lexicon file in the
    directory is unregistered — and then each pattern against its own
    examples and counterexamples. Every pattern has at least one example,
    because `load` compiles through `parse`, which refuses a pattern without
    one. Every lexicon but those in `COUNTEREXAMPLES_OPTIONAL` must declare
    `counterexamples_required`, so each of its patterns has a counterexample
    too (#3132).
    """
    def self_test(name: str, lexicon: Lexicon) -> list[str]:
        problems: list[str] = []
        if not lexicon.counterexamples_required and (name, lexicon.version) not in COUNTEREXAMPLES_OPTIONAL:
            problems.append(f"{name} v{lexicon.version}: does not declare `counterexamples_required: true`; "
                            "every lexicon registered after absence_self_narration v1 must (#3132)")
        for pattern in lexicon.patterns:
            for text in pattern.examples:
                if not pattern.regex.search(" ".join(text.split())):
                    problems.append(f"{name} v{lexicon.version} {pattern.id}: does not match its example {text!r}")
            for text in pattern.counterexamples:
                if pattern.regex.search(" ".join(text.split())):
                    problems.append(f"{name} v{lexicon.version} {pattern.id}: matches its counterexample {text!r}")
        return problems

    return check_pins(directory, lambda name, version: load(name, version, directory=directory), self_test)
