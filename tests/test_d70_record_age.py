"""D70: age requires positive evidence; missing guard fields do not date runs."""
import pytest
from pathlib import Path
import subprocess
from data_sheets_schema import canary, latch_journal as journal
from tests.test_api_latch_guard import clean_integrity, record_with

PRE = "f8c5ac73caba610d40c49aaceddb31ead3590a72"


def test_d41_commit_remains_in_full_repository_ancestry():
    root = Path(__file__).resolve().parents[1]
    shallow = subprocess.check_output(["git", "rev-parse", "--is-shallow-repository"],
                                      cwd=root, text=True).strip()
    if shallow == "true":
        pytest.skip("A shallow repository cannot prove the retained D41 ancestry boundary")
    assert shallow == "false"
    result = subprocess.run(["git", "merge-base", "--is-ancestor", journal.D41_COMMIT, "HEAD"],
                            cwd=root, capture_output=True, text=True)
    assert result.returncode == 0, "#5212 requires a merge commit retaining D41_COMMIT; no squash or rebase"


@pytest.mark.parametrize("commit,stamp,age", [
    (PRE, None, "pre-D41"),
    (PRE.upper(), None, "pre-D41"),
    (journal.D41_COMMIT, "2000-01-01T00:00:00Z", "post-D41"),
    (journal.D41_COMMIT.upper(), "2000-01-01T00:00:00Z", "post-D41"),
    ("d9b69d84d", None, "post-D41"),
    (None, "2026-09-12T12:00:00Z", "pre-D41"),
    ("a" * 40, "2026-09-12T12:00:00Z", "pre-D41"),
    (None, None, "age unestablished"),
    ("a" * 40, journal.D41_COMMITTED_AT, "age unestablished"),
    (None, "2026-09-12", "age unestablished"),
    (None, "bad", "age unestablished"),
])
def test_age_and_consumers(commit, stamp, age):
    record = record_with(clean_integrity())
    record.pop("model")
    record.update(repo={"commit": commit}, record_generated_at=stamp)
    assert journal.record_age(record) == age
    problem = journal.record_eligibility_problem(record)
    assert (problem is None) == (age != "post-D41")
    from data_sheets_schema.evaluation.registered_eval_runner import require_eligible_generation
    if problem:
        with pytest.raises(LookupError, match=age):
            canary._require_eligible_baseline(record, "test")
        with pytest.raises(ValueError, match=age):
            require_eligible_generation(record)
    else:
        canary._require_eligible_baseline(record, "test")
        require_eligible_generation(record)
    result = canary.verdict(canary.checks_from_record(record), {}, baseline_requested=False)
    assert result["record_age"] == age
    assert (result["status"] == canary.OK) == (age != "post-D41")


def test_removed_assisted_block_does_not_restore_eligibility():
    record = record_with({**clean_integrity(), "assisted": True, "evidence_only": True})
    record["repo"] = {"commit": journal.D41_COMMIT}
    assert journal.record_eligibility_problem(record)
    del record["model"]["runtime_integrity"]
    assert "post-D41" in journal.record_eligibility_problem(record)


def test_clean_block_does_not_depend_on_git_availability(monkeypatch):
    monkeypatch.setattr(journal, "record_age", lambda *a, **k: pytest.fail("unnecessary age lookup"))
    assert journal.record_eligibility_problem(record_with(clean_integrity())) is None


def test_short_hash_uses_positive_git_ancestry():
    root = Path(__file__).resolve().parents[1]
    short = subprocess.check_output(["git", "rev-parse", "--short=4", journal.D41_COMMIT],
                                    cwd=root, text=True).strip()
    assert journal.record_age({"repo": {"commit": short},
                               "record_generated_at": "2000-01-01T00:00:00Z"}) == "post-D41"


def repository_with_alternate_objects(tmp_path):
    root = Path(__file__).resolve().parents[1]
    common = subprocess.check_output(["git", "rev-parse", "--git-common-dir"], cwd=root, text=True).strip()
    objects = (root / common / "objects").resolve()
    subprocess.run(["git", "init", "--quiet", str(tmp_path)], check=True)
    (tmp_path / ".git/objects/info/alternates").write_text(str(objects) + "\n")
    return tmp_path


@pytest.mark.parametrize("reference", ["HEAD", "refs/heads/x"])
def test_symbolic_refs_are_unresolvable_recorded_commits(tmp_path, reference):
    root = repository_with_alternate_objects(tmp_path)
    for name in ("HEAD", "refs/heads/x"):
        subprocess.run(["git", "-C", str(root), "update-ref", name, journal.D41_COMMIT], check=True)
    assert subprocess.check_output(["git", "-C", str(root), "rev-parse", reference],
                                   text=True).strip() == journal.D41_COMMIT
    record = {"repo": {"commit": reference}}
    assert journal.record_age(record, repo_root=root) == "age unestablished"
    record["record_generated_at"] = "2000-01-01T00:00:00Z"
    assert journal.record_age(record, repo_root=root) == "pre-D41"


def test_hex_named_ref_must_resolve_to_its_own_prefix(tmp_path):
    root = repository_with_alternate_objects(tmp_path)
    subprocess.run(["git", "-C", str(root), "update-ref", "refs/heads/abcd", journal.D41_COMMIT], check=True)
    assert not journal.D41_COMMIT.startswith("abcd")
    record = {"repo": {"commit": "abcd"}}
    assert journal.record_age(record, repo_root=root) == "age unestablished"
    record["record_generated_at"] = "2000-01-01T00:00:00Z"
    assert journal.record_age(record, repo_root=root) == "pre-D41"


@pytest.mark.parametrize("commit", ["abc", "a" * 41, "HEAD~1", "--all", "f8c5ac73c^{commit}"])
def test_non_commit_identifiers_use_only_timestamp_evidence(commit):
    record = {"repo": {"commit": commit}}
    assert journal.record_age(record) == "age unestablished"
    record["record_generated_at"] = "2000-01-01T00:00:00Z"
    assert journal.record_age(record) == "pre-D41"


def test_negative_ancestry_in_shallow_history_uses_timestamp_fallback(tmp_path):
    root = repository_with_alternate_objects(tmp_path)
    source = Path(__file__).resolve().parents[1]
    post = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=source, text=True).strip()
    subprocess.run(["git", "-C", str(root), "update-ref", "HEAD", post], check=True)
    (root / ".git/shallow").write_text(post + "\n")
    for commit in (journal.D41_COMMIT, post):
        subprocess.run(["git", "-C", str(root), "cat-file", "-e", commit + "^{commit}"], check=True)
    negative = subprocess.run(["git", "-C", str(root), "merge-base", "--is-ancestor",
                               journal.D41_COMMIT, post], capture_output=True)
    assert negative.returncode == 1  # Both objects exist, but the intervening graph is cut.
    record = {"repo": {"commit": post}}
    assert journal.record_age(record, repo_root=root) == "age unestablished"
    record["record_generated_at"] = "2000-01-01T00:00:00Z"
    assert journal.record_age(record, repo_root=root) == "pre-D41"
    record["record_generated_at"] = journal.D41_COMMITTED_AT
    assert journal.record_age(record, repo_root=root) == "age unestablished"


def test_missing_git_binary_uses_timestamp_fallback(tmp_path, monkeypatch):
    monkeypatch.setenv("PATH", str(tmp_path / "no-git-binary"))
    record = {"repo": {"commit": journal.D41_COMMIT}}
    assert journal.record_age(record, repo_root=tmp_path) == "age unestablished"
    record["record_generated_at"] = "2000-01-01T00:00:00Z"
    assert journal.record_age(record, repo_root=tmp_path) == "pre-D41"


def test_git_availability_and_topology_are_revalidated(tmp_path, monkeypatch):
    root = repository_with_alternate_objects(tmp_path)
    actual = subprocess.run
    calls = []

    def observed(command, **kwargs):
        calls.append(tuple(command[4:]))
        return actual(command, **kwargs)

    monkeypatch.setattr(subprocess, "run", observed)
    for commit in (PRE, PRE.upper(), PRE):
        assert journal.record_age({"repo": {"commit": commit}}, repo_root=root) == "pre-D41"
    for commit in (PRE, journal.D41_COMMIT):
        assert calls.count(("rev-parse", "--verify", "--end-of-options", commit + "^{commit}")) == 3
    assert calls.count(("rev-parse", "--is-shallow-repository")) == 3
    assert calls.count(("merge-base", "--is-ancestor", journal.D41_COMMIT, PRE)) == 3


def test_missing_objects_are_rechecked_when_local_alternate_arrives(tmp_path):
    root = repository_with_alternate_objects(tmp_path)
    alternate = root / ".git/objects/info/alternates"
    saved = alternate.read_bytes()
    alternate.unlink()
    record = {"repo": {"commit": journal.D41_COMMIT}}
    assert journal.record_age(record, repo_root=root) == "age unestablished"
    alternate.write_bytes(saved)
    assert journal.record_age(record, repo_root=root) == "post-D41"


def test_full_repository_can_become_shallow_in_the_same_process(tmp_path):
    root = repository_with_alternate_objects(tmp_path)
    post = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    assert journal.record_age({"repo": {"commit": PRE}}, repo_root=root) == "pre-D41"
    (root / ".git/shallow").write_text(post + "\n")
    assert journal.record_age({"repo": {"commit": post}}, repo_root=root) == "age unestablished"


@pytest.mark.parametrize("consumer", [canary.baseline_for, canary.report_basis])
def test_unknown_baseline_age_is_reported_without_changing_metrics(tmp_path, capsys, consumer):
    import yaml
    baseline = record_with(clean_integrity())
    baseline.pop("model")
    path = tmp_path / "claudecode_api_core/baseline-rep1/P_provenance.yaml"
    path.parent.mkdir(parents=True)
    path.write_text(yaml.safe_dump(baseline))
    unknown = consumer("P", "baseline", "claudecode_api", tmp_path)
    assert "baseline age unestablished (eligible)" in capsys.readouterr().err
    baseline["repo"] = {"commit": PRE}
    path.write_text(yaml.safe_dump(baseline))
    assert consumer("P", "baseline", "claudecode_api", tmp_path) == unknown
    assert "age unestablished" not in capsys.readouterr().err
