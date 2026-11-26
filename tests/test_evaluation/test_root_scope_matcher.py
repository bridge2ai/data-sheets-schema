"""Check composed instruction text with the real audit matcher, issue 6371.

2026-11-26. Inputs are pinned definitions, overrides and scanner token sources.
Poisoned replacements stay in memory; import-failure fixtures use pytest scratch.
No instrument files, evaluation outputs or model processes are changed.
"""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from unittest.mock import patch

import pytest

from data_sheets_schema.root_scope_definition import DEFINITION_PINS, compose_definition


ROOT = Path(__file__).resolve().parents[2]
SCANNER = ROOT / ".claude/skills/d4d-generation-specificity-audit/scan.py"


def load_matcher(path=SCANNER):
    """Import the actual matcher; missing code or token classes must fail."""
    spec = importlib.util.spec_from_file_location("root_scope_matcher_6371", path)
    if spec is None or spec.loader is None:
        raise ImportError("scanner matcher has no import loader")
    scanner = importlib.util.module_from_spec(spec)
    # The scanner's dataclass definitions need the module during execution.
    with patch.dict(sys.modules, {spec.name: scanner}):
        spec.loader.exec_module(scanner)
    assert callable(scanner.load_tokens) and callable(scanner.match_text)
    tokens = scanner.load_tokens(ROOT)
    assert {token.category for token in tokens} == set(scanner.CATEGORIES)
    assert tokens
    return scanner, tokens


def pinned_replacements(rubric):
    pins = DEFINITION_PINS[rubric]
    raw = (ROOT / pins["overrides_path"]).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == pins["overrides_sha256"]
    return json.loads(raw)["replacements"]


def assert_clean_replacements(replacements, scanner, tokens):
    for index, pair in enumerate(replacements):
        matches = scanner.match_text(pair["replacement"], tokens)
        assert not matches, f"replacement {index} adds token matches: {matches}"


def match_identities(text, scanner, tokens):
    # Position shifts are expected; identity, duplicates and order must remain.
    return [(token.category, token.pattern, token.source, matched)
            for _, _, token, matched in scanner.match_text(text, tokens)]


def test_each_override_replacement_has_zero_matches_in_every_token_class():
    scanner, tokens = load_matcher()
    for rubric in DEFINITION_PINS:
        assert_clean_replacements(pinned_replacements(rubric), scanner, tokens)


def test_composed_definitions_keep_the_pinned_v3_ordered_match_identities():
    scanner, tokens = load_matcher()
    for rubric, pins in DEFINITION_PINS.items():
        source = (ROOT / pins["source_path"]).read_bytes()
        assert hashlib.sha256(source).hexdigest() == pins["source_sha256"]
        composed, provenance = compose_definition(rubric, repo_root=ROOT)
        assert hashlib.sha256(composed).hexdigest() == pins["composed_sha256"]
        assert provenance == pins
        original = match_identities(source.decode("utf-8"), scanner, tokens)
        assert original, "a matcher that observes no source tokens cannot pass"
        assert match_identities(composed.decode("utf-8"), scanner, tokens) == original


def test_poisoning_any_replacement_is_detected_for_each_token_class():
    scanner, tokens = load_matcher()
    seeds = {"gc_project": "AI_READI", "bridge2ai_program": "Bridge2AI",
             "biomedical_clinical": "clinical"}
    assert set(seeds) == set(scanner.CATEGORIES)
    for category, seed in seeds.items():
        assert {token.category for _, _, token, _ in scanner.match_text(seed, tokens)} == {category}
        for rubric in DEFINITION_PINS:
            original = pinned_replacements(rubric)
            for index in range(len(original)):
                poisoned = copy.deepcopy(original)
                poisoned[index]["replacement"] += "\n" + seed + "\n"
                # Check the exact cleanliness assertion, without a composition
                # hash check masking a matcher failure or any on-disk edit.
                with pytest.raises(AssertionError, match=f"replacement {index} adds token matches"):
                    assert_clean_replacements(poisoned, scanner, tokens)
                assert pinned_replacements(rubric) == original


def test_matcher_import_failure_propagates_instead_of_skipping(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_matcher(tmp_path / "missing_scanner.py")
    failing = tmp_path / "failing_scanner.py"
    failing.write_text("raise ImportError('synthetic matcher import failure')\n")
    with pytest.raises(ImportError, match="synthetic matcher import failure"):
        load_matcher(failing)
    with patch("importlib.util.spec_from_file_location", return_value=None):
        with pytest.raises(ImportError, match="scanner matcher has no import loader"):
            load_matcher()
