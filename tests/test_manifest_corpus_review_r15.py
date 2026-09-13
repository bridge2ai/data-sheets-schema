"""Public run audits verify evidence in the selected corpus from any cwd."""
import shutil

from click.testing import CliRunner
import pytest

from data_sheets_schema import runs
from data_sheets_schema.cli import cli
from tests.test_manifest_corpus_root import project_tree  # noqa: F401
from tests.test_manifest_corpus_review_r13 import artifacts


@pytest.mark.parametrize("caller_kind", ["nested", "foreign", "copy"])
@pytest.mark.parametrize("changed", [False, True])
def test_run_audit_reads_selected_pair_and_report_evidence(project_tree, monkeypatch, caller_kind, changed):
    owner, manifest, bundle = project_tree
    monkeypatch.chdir(owner)
    full, _, report, _ = artifacts(owner, bundle.relative_to(owner), manifest.relative_to(owner))
    recorded = CliRunner().invoke(cli, ["provenance", "record", "--project", "CLINICAL_X",
        "--method", "external", "--label", "run", "--input-bundle", str(bundle.relative_to(owner))])
    assert recorded.exit_code == 0, recorded.output
    caller = owner / "analysis" if caller_kind == "nested" else owner.with_name("audit_caller")
    if caller_kind == "copy":
        shutil.copytree(owner, caller)
    else:
        caller.mkdir()
    if changed:
        for path in (full, report):
            path.write_text(path.read_text() + "\n# Changed in the selected corpus only.\n")
    monkeypatch.chdir(caller)
    # Observe the real readers invoked by the CLI while its manifest context
    # is active; the readers and their filesystem checks are not replaced.
    observed = {"pair": [], "report": []}
    for kind, name in (("pair", "pair_status"), ("report", "report_claim_status")):
        original = getattr(runs, name)
        def capture(*args, _original=original, _kind=kind, **kwargs):
            result = _original(*args, **kwargs)
            observed[_kind].append(result[0])
            return result
        monkeypatch.setattr(runs, name, capture)
    args = [] if caller_kind == "nested" else ["--manifest", str(manifest)]
    result = CliRunner().invoke(cli, [*args, "runs", "check", "--method", "external"])
    assert result.exit_code == 0, (result.output, result.exception)
    assert observed["pair"] and observed["report"], result.output
    assert set(observed["pair"]) == {runs.PAIR_STALE if changed else runs.PAIR_CONSISTENT}
    assert set(observed["report"]) == {runs.CLAIMS_STALE if changed else runs.CLAIMS_CLEAN}
