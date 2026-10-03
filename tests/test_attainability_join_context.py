"""Bounded contextual certification, independently enumerated readings (#3678)."""
import hashlib
import importlib.util
import itertools
import json
import os
from pathlib import Path
import random
import re
import subprocess
import sys

import pytest

from data_sheets_schema import attainability as at
from data_sheets_schema.chunking import DEFAULT_RULE


def lines(text):
    return at._lines_by_chunk(text, dict(DEFAULT_RULE))[1]


def measure_module():
    path = Path(__file__).resolve().parents[1] / "scripts/measure_unhyphenated_line_splits.py"
    spec = importlib.util.spec_from_file_location("context_measure", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def legacy_snapshot(module, measurement):
    fixtures = ["a data\nprotection\nim\npact", "con\nsen\nt", "a data-\nprotec-\ntion impact",
                "version 2.0.0", "No relevant content.\n", "v\n2.0.0", "consent\nfrom all"]
    result = []
    for text in fixtures:
        indexed = lines(text)
        result.append({"entries": [module.deterministic_entry(c, indexed) for c in module.CHECKS],
            "joins": [[sorted(module.join_matching_lines(c.pattern, indexed, k)) for c in module.CHECKS]
                      for k in (1, 2)],
            "measure": measurement.measure(text, compare_window=10, joins_per_window=2)})
    return result


def test_default_helpers_derivations_and_measurement_match_complete_parent_capture():
    # Entire public fixture output, captured from ceb5a55d5 before editing.
    raw = json.dumps(legacy_snapshot(at, measure_module()), sort_keys=True).encode()
    assert hashlib.sha256(raw).hexdigest() == "770b4c75590bf5f08ee5db6ec860b750afb2c97f35e2cb58dc69f421acb50ff6"


def oracle(pattern, text, k, width):
    """Enumerate all break assignments, then filter their eligibility.

    Unlike production, no core run chooses/generates the assignments.
    Independent character-to-line provenance supplies hit lines and cuts.
    """
    raw = text.split("\n")
    result = set()
    for left in range(max(1, len(raw) - width + 1)):
        window = raw[left:left + width]
        choices = []
        for a, b in zip(window, window[1:]):
            choices.append(("space", "drop", "keep") if a.rstrip().endswith("-") else
                           ("space", "join") if a.strip() and b.strip() else ("space",))
        for assignment in itertools.product(*choices):
            joined = [i for i, choice in enumerate(assignment) if choice == "join"]
            if not joined:
                continue
            # All joins must fit one K-break run; hyphens outside it must
            # have a uniform reading, independently of the inner choices.
            eligible = False
            for start in range(len(assignment)):
                core = range(start, min(start + k, len(assignment)))
                outer = {assignment[i] for i, s in enumerate(window[:-1])
                         if i not in core and s.rstrip().endswith("-")}
                if all(i in core for i in joined) and len(outer) <= 1:
                    eligible = True
                    break
            if not eligible:
                continue
            rendered, owners, cuts = "", [], []
            for i, body in enumerate(window):
                if i and assignment[i - 1] != "space":
                    body = body.lstrip()
                choice = assignment[i] if i < len(assignment) else "space"
                if choice != "space":
                    body = body.rstrip()
                    if choice == "drop":
                        body = body[:-1]
                rendered += body
                owners.extend([left + i + 1] * len(body))
                if choice == "join":
                    cuts.append(len(rendered))
                if choice == "space":
                    rendered += " "
                    owners.append(None)
            rx = re.compile(pattern)
            for offset in range(len(rendered)):
                match = rx.match(rendered, offset)
                if match and any(match.start() < cut < match.end() for cut in cuts):
                    result.update(n for n in owners[match.start():match.end()] if n is not None)
    return result


def test_context_matches_independent_small_exhaustive_oracle():
    randomizer = random.Random(3678)
    fixtures = ["a data\nprotection\nim\npact assessment", "a da\nta\nprotection\nimpact",
                "a data\nprotec-\ntion\nim\npact", "ab-\n\ncd-\nef\nx\ny",
                " con-\n sen\n t", "v\n2.0.0", "consent\nfrom all", "ir\nβ"]
    pieces = ["co", "n-", "sen", "t", " v", "2.0.0", "", "a data", "im", "pact", " protection"]
    fixtures += ["\n".join(randomizer.choices(pieces, k=randomizer.randrange(2, 7))) for _ in range(70)]
    patterns = [c.pattern for c in at.CHECKS] + [r"ab\s+cd-ef\s+xy", r"irβ", r"t.*v", r"co|con.*t"]
    for text in fixtures:
        for k, width in ((1, 3), (2, 3), (2, 5), (2, 6)):
            for pattern in patterns:
                assert at.join_matching_lines(pattern, lines(text), k, context_lines=width) == oracle(
                    pattern, text, k, width), (text, pattern, k, width)


@pytest.mark.parametrize("text,expected", [
    ("a data\nprotection\nim\npact", {1, 2, 3, 4}),
    ("a da\nta\nprotection\nimpact", {1, 2, 3, 4}),
    ("a data\nprotec-\ntion\nim\npact", {1, 2, 3, 4, 5}),
    ("a data" + "\n" * 8 + "protection im\npact", {1, 9, 10}),
    ("a data" + "\n" * 9 + "protection im\npact", set()),
])
def test_context_before_after_and_physical_window_edges(text, expected):
    assert at.join_matching_lines(at.CHECKS_BY_NAME["ethics_review"].pattern, lines(text), 2,
                                  context_lines=10) == expected


def test_bounds_do_not_claim_arbitrary_mixed_hyphens_or_three_joins():
    consent = at.CHECKS_BY_NAME["consent_text"].pattern
    assert at.join_matching_lines(consent, lines("co\nns\nen\nt"), 2, context_lines=10) == set()
    assert at.join_matching_lines(consent, lines("consent\nfrom all"), 2, context_lines=10) == set()
    # The two distant outer hyphens require different readings. The
    # approved contract is uniform outside the join run, not exhaustive.
    text = "ab-\n\ncd-\nef\nx\ny"
    assert at.join_matching_lines(r"ab\s+cd-ef\s+xy", lines(text), 2, context_lines=10) == set()


@pytest.mark.parametrize("k,w", [(0, 10), (True, 10), (2, 2), (2, True), (2, 3.0)])
def test_invalid_context_bounds_refuse_even_on_empty_input(k, w):
    with pytest.raises(ValueError):
        at.join_matching_lines("x", {}, k, context_lines=w)


def test_actual_cli_refuses_before_writes_and_preserves_existing_bytes(tmp_path):
    source = tmp_path / "neutral.txt"
    source.write_text("a data\nprotection\nim\npact assessment was done")
    document = at.build_document(str(source))
    target = tmp_path / "data/attainability" / at.file_name(document)
    target.parent.mkdir(parents=True)
    target.write_text(at.dump(document))
    before = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    env = {**os.environ, "D4D_MANIFEST": "none", "PYTHONDONTWRITEBYTECODE": "1",
           "PYTHONPATH": str(Path(at.__file__).resolve().parents[1])}
    run = subprocess.run([sys.executable, "-m", "data_sheets_schema.attainability", "derive",
                          "--bundle", str(source), "--write"], cwd=tmp_path, env=env,
                         capture_output=True, text=True)
    assert run.returncode == 1, (run.stdout, run.stderr)
    assert "REFUSED" in run.stdout and "E4.1" in run.stdout and "10 context lines" in run.stdout
    assert {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()} == before


def test_context_measurement_adds_a_column_and_uses_gate_search(tmp_path, capsys):
    module = measure_module()
    text = "a data\nprotection\nim\npact assessment"
    old = module.measure(text, joins_per_window=2)
    new = module.measure(text, joins_per_window=2, join_context_lines=10)
    assert {k: v for k, v in new.items() if k != "moved_with_join_context"} == old
    assert old["moved_if_up_to_k_breaks_join"] == {}
    assert new["moved_with_join_context"] == {"ethics_review": "status"}
    assert set(new["moved_with_join_context"]) == set(at.line_split_gate(lines(text), at.CHECKS))
    for args in (["--join-context-lines", "10"], ["--join-context-lines", "2", "--joins-per-window", "2"]):
        assert module.main(["--no-word-list", "--corpus", str(tmp_path), *args]) == 2
        assert "requires --joins-per-window K" in capsys.readouterr().err


def test_context_report_discloses_exact_bytes_and_fails_unmeasured_version(tmp_path, capsys):
    import yaml
    module = measure_module()
    bundle = tmp_path / "bundle.txt"; bundle.write_text("a data\nprotection\nim\npact")
    pin = hashlib.md5(bundle.read_bytes()).hexdigest()
    (tmp_path / "P_provenance.yaml").write_text(yaml.safe_dump({"inputs": {
        "bundle_path": str(bundle), "bundle_md5": pin}}))
    assert module.main(["--no-word-list", "--corpus", str(tmp_path), "--joins-per-window", "2",
                        "--join-context-lines", "10", "--json"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["rows"][0]["sha256"] == hashlib.sha256(bundle.read_bytes()).hexdigest()
    report["rows"].append({"bundle": "missing", "md5": "0" * 32, "records": 1, "error": "unmeasured"})
    table = module.markdown(report)
    rows = [row for row in table.splitlines() if row.startswith("|")]
    assert len({row.count("|") for row in rows}) == 1
    assert "Moved with 10-line join context" in table and "not measured: unmeasured" in table
    bundle.unlink()
    assert module.main(["--no-word-list", "--corpus", str(tmp_path), "--joins-per-window", "2",
                        "--join-context-lines", "10", "--json"]) == 1
    assert "error" in json.loads(capsys.readouterr().out)["rows"][0]
