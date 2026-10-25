"""Offline N2 evidence checks: refuse false parity and hidden/source drift.

These exercise the helper's evidence boundaries, not native launch acceptance.
Refs #4354; 2026-10-25. No provider, actual registration or helper run.
"""
import importlib.util
from importlib.machinery import ModuleSpec
from pathlib import Path
from types import ModuleType

import pytest


ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "scripts/adhoc/native_n2_render_parity_20261025.py"
_spec = importlib.util.spec_from_file_location("native_n2_render_parity_test_helper", HELPER)
helper = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(helper)


@pytest.fixture
def rendered_sections():
    generic = (ROOT / helper.GENERIC).read_bytes()
    r9 = helper.between(generic, helper.R9_START, helper.R9_END, "R9")
    uniform = helper.RULE_START + b"\nBefore the reviewed rule.\n" + r9 + b"\nAfter the reviewed rule.\n"
    api = b"API-only prelude\n" + uniform + b"\n" + helper.RULE_END + b"\nAPI-only tail\n"
    native = b"Native-only prelude\n" + uniform + helper.RULE_END + b"\nNative-only tail\n"
    return generic, api, native, r9


def test_full_reviewed_r9_and_uniform_match_despite_other_package_differences(rendered_sections):
    generic, api, native, r9 = rendered_sections
    result, observed_r9, rules = helper.compare_rules(generic, api, native)
    assert observed_r9 == r9 and len(observed_r9) == 4433
    assert result["r9"]["occurrences"] == {"api25": 1, "native26": 1}
    assert result["uniform"]["identical"] is True
    assert rules.startswith(helper.RULE_START)
    assert api != native  # The result must not claim full-instruction equality.


def test_same_r9_prefix_with_changed_final_qualification_is_not_parity(rendered_sections):
    generic, api, native, r9 = rendered_sections
    changed = r9[:-1] + bytes([r9[-1] ^ 1])
    with pytest.raises(ValueError, match="complete R9 must occur verbatim exactly once"):
        helper.compare_rules(generic, api, native.replace(r9, changed))


def test_duplicate_complete_r9_outside_uniform_section_is_rejected(rendered_sections):
    generic, api, native, r9 = rendered_sections
    with pytest.raises(ValueError, match="complete R9 must occur verbatim exactly once"):
        helper.compare_rules(generic, api + r9, native)


def test_matching_r9_does_not_hide_different_uniform_rule(rendered_sections):
    generic, api, native, _ = rendered_sections
    with pytest.raises(ValueError, match="complete extracted uniform sections differ"):
        helper.compare_rules(generic, api, native.replace(b"Before the reviewed rule.", b"Changed scientific instruction."))


def test_stale_generic_asset_cannot_supply_its_own_expected_passage(rendered_sections):
    generic, api, native, _ = rendered_sections
    with pytest.raises(ValueError, match="not the reviewed R9 source"):
        helper.compare_rules(generic + b"\nchanged\n", api, native)


@pytest.mark.parametrize("value", [b"end start", b"start middle start end", b"start only"])
def test_ambiguous_missing_or_reversed_delimiters_refuse(value):
    with pytest.raises(ValueError, match="markers"):
        helper.between(value, b"start", b"end", "test")


def test_reader_detects_mutation_after_a_pinned_read(tmp_path):
    source = tmp_path.resolve() / "input.json"
    source.write_bytes(b"original")
    reader = helper.Reader()
    assert reader.pin({"path": str(source), "bytes": 8, "sha256": helper.sha(b"original")}) == b"original"
    source.write_bytes(b"different")
    with pytest.raises(ValueError, match="changed between reads"):
        reader.stable()


def test_reader_rejects_symlink_and_wrong_pinned_size(tmp_path):
    source = tmp_path.resolve() / "input.txt"
    source.write_bytes(b"x")
    alias = source.parent / "alias.txt"
    alias.symlink_to(source)
    with pytest.raises(ValueError, match="physical"):
        helper.Reader().read(alias)
    with pytest.raises(ValueError, match="differs from pin"):
        helper.Reader().pin({"path": str(source), "bytes": True, "sha256": helper.sha(b"x")})


@pytest.mark.parametrize("raw", [b'{"x":1,"x":2}', b'{"x":NaN}'])
def test_evidence_json_never_accepts_duplicate_or_nonfinite_values(raw):
    with pytest.raises(ValueError):
        helper.strict_json(raw)


def test_historical_pin_join_requires_one_exact_path():
    path = Path("/fixture/original.json")
    pin = {"path": str(path), "bytes": 1, "sha256": "a" * 64}
    assert helper.unique_pin([pin], path) == pin
    for rows in ([], [pin, pin], [{**pin, "path": "/fixture/other.json"}]):
        with pytest.raises(ValueError, match="one exact input pin"):
            helper.unique_pin(rows, path)


def test_ignored_python_file_is_not_hidden_from_source_roster(tmp_path, monkeypatch):
    tree = tmp_path.resolve()
    (tree / "src" / "ignored").mkdir(parents=True)
    (tree / "src" / "module.py").write_text("VALUE = 1\n")
    (tree / "src" / "ignored" / "shadow.py").write_text("VALUE = 2\n")
    (tree / ".gitignore").write_text("src/ignored/\n")
    head = "a" * 40
    def git(_tree, *args):
        if args[0] == "rev-parse":
            return (head + "\n").encode()
        if args[0] == "diff":
            return b""
        if args[0] == "ls-tree":
            return b"src/module.py\0"
        raise AssertionError("unexpected Git read before roster refusal")
    monkeypatch.setattr(helper, "git", git)
    with pytest.raises(ValueError, match="including ignored files"):
        helper.frozen_source(tree, head, helper.Reader())


def test_foreign_loaded_project_module_fails_source_proof(tmp_path):
    tree = tmp_path.resolve() / "selected"
    (tree / "src").mkdir(parents=True)
    foreign = tmp_path.resolve() / "other.py"
    foreign.write_text("VALUE = 'foreign'\n")
    name = "data_sheets_schema.zz_n2_foreign_source_test"
    module = ModuleType(name)
    module.__spec__ = ModuleSpec(name, None, origin=str(foreign))
    module.__file__ = str(foreign)
    with pytest.raises(ValueError, match="foreign source"):
        helper.module_origins(tree, "a" * 40, helper.Reader(), modules={name: module})


def test_evidence_destination_cannot_reuse_output_or_write_into_source(tmp_path):
    parent = tmp_path.resolve()
    tree = parent / "tree"
    tree.mkdir()
    with pytest.raises(ValueError, match="outside the source"):
        helper.destination(tree, "new", tree)
    (parent / "already-present").mkdir()
    with pytest.raises(ValueError, match="existing evidence"):
        helper.destination(parent, "already-present", tree)
    with pytest.raises(ValueError, match="one component"):
        helper.destination(parent, "../escape", tree)


def test_offline_audit_allows_read_only_git_but_refuses_network_native_and_push():
    helper.offline_audit("subprocess.Popen", ("git", ["git", "--no-replace-objects", "-C", "/fixture", "show", "HEAD:x"]))
    with pytest.raises(RuntimeError, match="network forbidden"):
        helper.offline_audit("socket.connect", ())
    for argv in (["claude", "-p", "text"], ["python", "-m", "provider"], ["git", "push"], ["git", "fetch"]):
        with pytest.raises(ValueError, match="permitted|forbidden"):
            helper.offline_audit("subprocess.Popen", (argv[0], argv))
