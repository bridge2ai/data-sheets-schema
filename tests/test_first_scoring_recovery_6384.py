"""Synthetic first-scoring recovery controls, issues 6384/6395, 2026-11-26.

Uses the retained fresh-child shape with replacement content and the measured
Git blob. Only the fake Poetry entrypoint invokes the actual strict validator;
no model executable, real response, credential or measured run is opened.
"""
from argparse import Namespace
from copy import deepcopy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
from unittest.mock import patch

import pytest

from tests.test_root_scope_repeats import synthetic_run, repeat_helper
from tests.test_codex_session_reader_6384 import SessionCase, STARTED, FINISHED


ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "scripts/adhoc/recover_first_scoring_6384_20261126.py"


def helper():
    spec = importlib.util.spec_from_file_location("recovery_controls", PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def snapshot(root):
    return {str(path.relative_to(root)): path.read_bytes() for path in root.rglob("*") if path.is_file()}


def fixture(directory, rubric="rubric20", **changes):
    original_args, tree, tools, evaluation, _ = synthetic_run(directory / "source", rubric, **changes)
    measured = repeat_helper()._load_scorer(tree)
    run = directory / "source-runs" / "synthetic-cell-01"
    run.parent.mkdir()
    original_args.run_directory = run
    plan = repeat_helper().in_checkout(tree, measured.build_plan, original_args)
    shape = SessionCase(directory / "shape")
    run.mkdir()
    for path in shape.run.rglob("*"):
        relative = path.relative_to(shape.run)
        target = run / relative
        if path.is_dir():
            target.mkdir(exist_ok=True)
        else:
            target.write_text(path.read_text().replace(str(shape.run), str(run)))
    for name in plan["inputs"]:
        (run / "working" / name).write_bytes(repeat_helper().in_checkout(tree, measured.input_bytes, plan, name))
    write(run / "plan.json", plan)
    write(run / "raw-response.json", evaluation)
    try:
        measured.session_identity(plan, STARTED, FINISHED)
    except measured.ScorerError as exc:
        failure = type(exc).__name__ + ": " + str(exc)
    else:
        raise AssertionError("synthetic fresh child did not reproduce original refusal")
    receipt = {"status": "REFUSED", "failure": failure, "codex_exit": 0,
               "auth_copy_absent": True, "authorization_reference": "synthetic original call",
               "started_utc": STARTED.isoformat(), "codex_started_utc": STARTED.isoformat(),
               "codex_finished_utc": FINISHED.isoformat(), "finished_utc": FINISHED.isoformat(),
               "plan_sha256": sha(json.dumps(plan, sort_keys=True).encode())}
    write(run / "receipt.json", receipt)
    args = Namespace(original_run=run, recovery_root=directory / "recovery",
                     authorization_reference="synthetic owner recovery decision", dry_run=True,
                     publish=False, publish_validated=False)
    return args, plan, receipt, evaluation, tools


def prepare(tmp_path, monkeypatch, rubric="rubric20", **changes):
    module = helper()
    monkeypatch.setattr(module, "checkout", lambda root: None)
    return module, fixture(tmp_path, rubric, **changes)


def paths(args):
    run = args.original_run
    return (args.recovery_root / run.name,
            run.parent / "first-scoring-remediations" / run.name)


def publish_args(args):
    result = deepcopy(args)
    result.dry_run, result.publish_validated = False, True
    result.authorization_reference = "synthetic separate publication decision"
    return result


def test_real_validator_recovery_both_rubrics_and_original_bytes_unchanged(tmp_path, monkeypatch):
    for rubric in ("rubric10", "rubric20"):
        module, (args, plan, original, evaluation, tools) = prepare(tmp_path / rubric, monkeypatch, rubric)
        before = snapshot(args.original_run)
        args.dry_run, args.publish = False, True
        result = module.perform(args)
        assert result["status"] == "PASS"
        assert snapshot(args.original_run) == before
        assert not (tools / "invocation.json").exists()
        assert not (args.original_run / "candidate_evaluation.json").exists()
        directory, state = paths(args)
        target = Path(plan["output"])
        raw = target.read_bytes()
        assert raw == (directory / "validated-evaluation.json").read_bytes()
        assert raw == (tools / "validated-snapshot.json").read_bytes()
        published = json.loads(raw)
        assert published["overall_score"] == evaluation["overall_score"]
        for key in ("elements", "categories", "metadata", "evaluation_scope", "applicability_context"):
            if key in evaluation:
                assert published[key] == evaluation[key]
        assert published["scorer_instrument"]["runner_sha256"] == module.REVISED_SHA
        assert published["scorer_instrument"]["runner_sha256"] != plan["runner_sha256"]
        assert published["scorer_instrument"]["recovery"]["measured_runner_sha256"] == module.MEASURED_SHA
        manifest = json.loads((directory / "manifest.json").read_bytes())
        assert manifest["kind"] == "FIRST_SCORING_RECOVERY" and manifest["attempt"] == 1
        assert manifest["destination_sha256"] == sha(raw)
        assert manifest["original_pins"]["raw-response.json"] == sha(before["raw-response.json"])
        assert manifest["revised_reader_sha256"] == module.REVISED_SHA
        assert manifest["model_calls"] == 0
        state_manifest = json.loads((state / "manifest.json").read_bytes())
        assert state_manifest["manifest_sha256"] == sha((directory / "manifest.json").read_bytes())
        with pytest.raises(ValueError):
            module.perform(args)


def test_dry_run_success_then_separate_publication_never_revalidates(tmp_path, monkeypatch):
    module, (args, plan, _, _, tools) = prepare(tmp_path, monkeypatch)
    before = snapshot(args.original_run)
    assert module.perform(args)["status"] == "PASS"
    directory, _ = paths(args)
    assert not Path(plan["output"]).exists() and not (directory / "manifest.json").exists()
    validation_evidence = (tools / "real-validator-result.json").read_bytes()
    exporter, guard, revised = module.programs()
    monkeypatch.setattr(exporter, "_validate_staged", lambda *a: pytest.fail("validation ran a second time"))
    monkeypatch.setattr(revised, "session_identity", lambda *a: pytest.fail("identity ran a second time"))
    monkeypatch.setattr(module, "programs", lambda: (exporter, guard, revised))
    assert module.perform(publish_args(args))["status"] == "PASS"
    assert (tools / "real-validator-result.json").read_bytes() == validation_evidence
    assert snapshot(args.original_run) == before


def test_invalid_candidate_refusal_consumes_the_fixed_cell_not_output_root(tmp_path, monkeypatch):
    module, (args, plan, _, evaluation, _) = prepare(tmp_path, monkeypatch)
    evaluation["overall_score"]["total_points"] -= 1
    write(args.original_run / "raw-response.json", evaluation)
    before = snapshot(args.original_run)
    with pytest.raises(ValueError, match="exact-file validation refused"):
        module.perform(args)
    directory, state = paths(args)
    assert json.loads((directory / "recovery-receipt.json").read_bytes())["status"] == "RECOVERY_REFUSED"
    assert (state / "claim.json").exists() and not Path(plan["output"]).exists()
    args.recovery_root = tmp_path / "different-output"
    with pytest.raises(ValueError, match="already claimed"):
        module.perform(args)
    assert snapshot(args.original_run) == before


def test_shared_replacement_state_and_existing_attempt_two_prevent_recovery(tmp_path, monkeypatch, kind):
    module, (args, plan, _, _, _) = prepare(tmp_path, monkeypatch)
    _, state = paths(args)
    if kind == "shared":
        state.mkdir(parents=True)
        write(state / "claim.json", {"action": "replacement"})
    else:
        args.original_run.with_name("synthetic-cell-02").mkdir()
    before = snapshot(args.original_run)
    with pytest.raises(ValueError):
        module.perform(args)
    assert snapshot(args.original_run) == before and not Path(plan["output"]).exists()


def test_ineligible_receipt_or_prior_artifacts_refuse_before_response_read(tmp_path, monkeypatch, kind):
    module, (args, plan, receipt, _, _) = prepare(tmp_path, monkeypatch)
    if kind == "validator":
        receipt.update(failure="ScorerError: exact-file schema/evidence validation failed; no publication", validator_exit=1)
    elif kind == "validator_zero":
        receipt["validator_exit"] = 0
    elif kind == "published":
        receipt["status"] = "VALIDATED_AND_PUBLISHED"
    elif kind == "started":
        receipt["status"] = "STARTED"
    elif kind == "unfinished":
        receipt.pop("finished_utc")
    elif kind == "auth":
        receipt["auth_copy_absent"] = False
    elif kind == "model":
        receipt["evaluation_model"] = {}
    elif kind == "candidate":
        (args.original_run / "candidate_evaluation.json").write_text("synthetic unrelated bytes")
    elif kind == "output":
        target = Path(plan["output"])
        target.parent.mkdir(parents=True)
        target.write_text("earlier publication")
    write(args.original_run / "receipt.json", receipt)
    original_read = module.read
    monkeypatch.setattr(module, "read", lambda path: pytest.fail("ineligible response opened")
                        if Path(path).name == "raw-response.json" else original_read(path))
    with pytest.raises((ValueError, KeyError)):
        module.perform(args)
    assert not paths(args)[1].exists()


def test_missing_or_reused_authorization_never_opens_response(tmp_path, monkeypatch, reference):
    module, (args, _, _, _, _) = prepare(tmp_path, monkeypatch)
    args.authorization_reference = reference
    original_read = module.read
    monkeypatch.setattr(module, "read", lambda path: pytest.fail("unauthorized response opened")
                        if Path(path).name == "raw-response.json" else original_read(path))
    with pytest.raises(ValueError, match="authorization"):
        module.perform(args)
    assert not paths(args)[1].exists()


def test_measured_inputs_and_validation_pins_refuse_before_claim(tmp_path, monkeypatch, kind):
    module, (args, plan, _, _, _) = prepare(tmp_path, monkeypatch)
    if kind == "runner":
        path = Path(plan["runner"])
    elif kind == "validator":
        path = Path(plan["repo_root"]) / "scripts/validate_evaluation_schema.py"
    elif kind == "launcher":
        path = Path(plan["validation_command"][0])
    elif kind == "definition":
        path = Path(plan["repo_root"]) / plan["definition_provenance"]["source_path"]
    else:
        path = Path(plan["inputs"][kind]["source"])
    path.write_bytes(path.read_bytes() + b"\n")
    with pytest.raises(ValueError):
        module.perform(args)
    assert not paths(args)[1].exists() and not Path(plan["output"]).exists()


def test_cli_malformed_metadata_prints_only_refusal_and_reason(tmp_path, monkeypatch, capsys):
    module, (args, _, receipt, _, _) = prepare(tmp_path, monkeypatch)
    del receipt["finished_utc"]
    write(args.original_run / "receipt.json", receipt)
    result = module.main(["--original-run", str(args.original_run), "--recovery-root", str(args.recovery_root),
                          "--authorization-reference", args.authorization_reference, "--dry-run"])
    assert result == 2
    value = json.loads(capsys.readouterr().out)
    assert set(value) == {"status", "reason"} and value["status"] == "REFUSED"
    assert "overall_score" not in value["reason"] and not paths(args)[1].exists()


def test_resume_refuses_bytes_receipt_claim_pins_and_authorization_tampering(tmp_path, monkeypatch, kind):
    module, (args, plan, _, _, _) = prepare(tmp_path, monkeypatch)
    module.perform(args)
    directory, state = paths(args)
    resumed = publish_args(args)
    if kind == "bytes":
        path = directory / "validated-evaluation.json"
        path.chmod(0o600)
        path.write_bytes(path.read_bytes() + b"\n")
    elif kind == "receipt":
        path = directory / "recovery-receipt.json"
        value = json.loads(path.read_bytes())
        value["validator_input_sha256"] = "0" * 64
        write(path, value)
    elif kind == "claim":
        path = state / "claim.json"
        value = json.loads(path.read_bytes())
        value["authorization_reference"] = "tampered decision"
        write(path, value)
    elif kind == "input":
        path = Path(plan["inputs"]["record.yaml"]["source"])
        path.write_bytes(path.read_bytes() + b"\n")
    elif kind == "original":
        path = args.original_run / "raw-response.json"
        path.write_bytes(path.read_bytes() + b"\n")
    elif kind == "authorization":
        resumed.authorization_reference = args.authorization_reference
    elif kind == "other_root":
        resumed.recovery_root = tmp_path / "other-root"
    with pytest.raises((ValueError, OSError)):
        module.perform(resumed)
    assert not Path(plan["output"]).exists()


def test_candidate_drift_during_validation_refuses_without_publication(tmp_path, monkeypatch):
    module, (args, plan, _, _, _) = prepare(tmp_path, monkeypatch, post_validator_drift=True)
    args.dry_run, args.publish = False, True
    before = snapshot(args.original_run)
    with pytest.raises(ValueError, match="changed during validation"):
        module.perform(args)
    assert not Path(plan["output"]).exists() and snapshot(args.original_run) == before


def test_original_response_change_during_validation_refuses(tmp_path, monkeypatch):
    module, (args, plan, _, _, _) = prepare(tmp_path, monkeypatch)
    exporter, guard, revised = module.programs()
    original = exporter._validate_staged
    def change(*values):
        result = original(*values)
        path = args.original_run / "raw-response.json"
        path.write_bytes(path.read_bytes() + b"\n")
        return result
    monkeypatch.setattr(exporter, "_validate_staged", change)
    monkeypatch.setattr(module, "programs", lambda: (exporter, guard, revised))
    with pytest.raises(ValueError, match="original evidence changed"):
        module.perform(args)
    assert not Path(plan["output"]).exists()


def test_identity_and_constructor_use_one_captured_snapshot_despite_temporary_drift(tmp_path, monkeypatch):
    module, (args, plan, _, evaluation, _) = prepare(tmp_path, monkeypatch)
    before = snapshot(args.original_run)
    exporter, guard, revised = module.programs()
    original_identity, original_validation = revised.session_identity, exporter._validate_staged
    def change_identity(*values):
        raw_path = args.original_run / "raw-response.json"
        poisoned = deepcopy(evaluation)
        poisoned["overall_score"]["total_points"] -= 1
        write(raw_path, poisoned)
        stdout = args.original_run / "codex.stdout.jsonl"
        stdout.write_text('{"type":"thread.started","thread_id":"foreign"}\n')
        child = args.original_run / "codex-home/sessions/00-child.jsonl"
        child.write_text(child.read_text().replace("gpt-6-astra", "wrong-model"))
        return original_identity(*values)
    def restore_validation(*values):
        for name, raw in before.items():
            (args.original_run / name).write_bytes(raw)
        return original_validation(*values)
    monkeypatch.setattr(revised, "session_identity", change_identity)
    monkeypatch.setattr(exporter, "_validate_staged", restore_validation)
    monkeypatch.setattr(module, "programs", lambda: (exporter, guard, revised))
    assert module.perform(args)["status"] == "PASS"
    directory, _ = paths(args)
    candidate = json.loads((directory / "validated-evaluation.json").read_bytes())
    assert candidate["overall_score"] == evaluation["overall_score"]
    assert snapshot(args.original_run) == before
    recorded = json.loads((directory / "recovery-receipt.json").read_bytes())
    for entry in recorded["evaluation_model"]["session_logs"]:
        assert entry["sha256"] == sha(before[entry["path"]])


def test_recovery_never_opens_model_binary_or_authentication(tmp_path, monkeypatch):
    module, (args, plan, _, _, _) = prepare(tmp_path, monkeypatch)
    forbidden = {Path(plan["command"][0]), Path(plan["auth_file"])}
    original_read = Path.read_bytes
    def guarded(path):
        if path in forbidden:
            pytest.fail("recovery opened model executable or authentication")
        return original_read(path)
    monkeypatch.setattr(Path, "read_bytes", guarded)
    assert module.perform(args)["status"] == "PASS"


def test_setup_failure_after_claim_is_terminal_and_recorded(tmp_path, monkeypatch):
    module, (args, _, _, _, _) = prepare(tmp_path, monkeypatch)
    directory, state = paths(args)
    original_mkdir = Path.mkdir
    def denied(path, *values, **keywords):
        if path == directory:
            raise PermissionError("synthetic recovery-directory creation refusal")
        return original_mkdir(path, *values, **keywords)
    monkeypatch.setattr(Path, "mkdir", denied)
    with pytest.raises(PermissionError):
        module.perform(args)
    saved = json.loads((state / "failure.json").read_bytes())
    assert saved["status"] == "RECOVERY_REFUSED" and (state / "claim.json").exists()
    args.recovery_root = tmp_path / "other-root"
    with pytest.raises(ValueError, match="already claimed"):
        module.perform(args)


def test_interrupt_after_claim_retains_failure_and_forbids_another_attempt(tmp_path, monkeypatch):
    module, (args, plan, _, _, _) = prepare(tmp_path, monkeypatch)
    exporter, guard, revised = module.programs()
    def interrupted(*values):
        raise KeyboardInterrupt("synthetic interruption")
    monkeypatch.setattr(revised, "session_identity", interrupted)
    monkeypatch.setattr(module, "programs", lambda: (exporter, guard, revised))
    with pytest.raises(KeyboardInterrupt):
        module.perform(args)
    directory, _ = paths(args)
    assert json.loads((directory / "recovery-receipt.json").read_bytes())["status"] == "RECOVERY_REFUSED"
    assert (directory / "failure.json").exists() and not Path(plan["output"]).exists()
    with pytest.raises(ValueError, match="already claimed"):
        module.perform(args)


def test_link_collision_keeps_the_other_publication_and_failure_receipt(tmp_path, monkeypatch):
    module, (args, plan, _, _, _) = prepare(tmp_path, monkeypatch)
    module.perform(args)
    target = Path(plan["output"])
    original_link = os.link
    def collision(source, destination, *values, **keywords):
        if Path(destination) == target:
            target.write_bytes(b"another publisher owns this result\n")
        return original_link(source, destination, *values, **keywords)
    monkeypatch.setattr(module.os, "link", collision)
    with pytest.raises(FileExistsError):
        module.perform(publish_args(args))
    assert target.read_bytes() == b"another publisher owns this result\n"
    directory, _ = paths(args)
    assert (directory / "failure.json").exists() and not (directory / "manifest.json").exists()


def test_failure_after_link_rolls_back_only_the_owned_publication(tmp_path, monkeypatch):
    module, (args, plan, _, _, _) = prepare(tmp_path, monkeypatch)
    module.perform(args)
    original_write = module.write
    def fail(path, value):
        if Path(path).name == "manifest.json":
            raise OSError("synthetic manifest write failure")
        return original_write(path, value)
    monkeypatch.setattr(module, "write", fail)
    with pytest.raises(OSError, match="synthetic manifest"):
        module.perform(publish_args(args))
    assert not Path(plan["output"]).exists()
    assert (paths(args)[0] / "failure.json").exists()


def test_partial_or_completed_claim_write_failure_retains_terminal_refusal(tmp_path, monkeypatch, kind):
    module, (args, plan, _, _, _) = prepare(tmp_path, monkeypatch)
    module.perform(args)
    recovery, state = paths(args)
    before = snapshot(args.original_run)
    original_write = module.write
    def failed_claim(path, value):
        if Path(path).name == "publication-claim.json":
            if kind == "partial":
                with Path(path).open("xb") as output:
                    output.write(b'{"status":')
                    output.flush()
                    os.fsync(output.fileno())
            else:
                original_write(path, value)
            raise OSError("synthetic claim write or readback failure")
        return original_write(path, value)
    monkeypatch.setattr(module, "write", failed_claim)
    with pytest.raises(OSError, match="claim write or readback"):
        module.perform(publish_args(args))
    assert (recovery / "publication-claim.json").exists()
    assert (recovery / "failure.json").exists()
    assert json.loads((recovery / "publication-receipt.json").read_bytes())["status"] == "RECOVERY_PUBLICATION_REFUSED"
    assert json.loads((state / "publication-failure.json").read_bytes())["status"] == "RECOVERY_PUBLICATION_REFUSED"
    assert snapshot(args.original_run) == before and not Path(plan["output"]).exists()
    with pytest.raises(ValueError):
        module.perform(publish_args(args))


def test_losing_publication_claim_race_preserves_the_winners_evidence(tmp_path, monkeypatch):
    module, (args, plan, _, _, _) = prepare(tmp_path, monkeypatch)
    module.perform(args)
    recovery, state = paths(args)
    reserve, failure = recovery / "refusal-reserve.json", recovery / "failure.json"
    original_link = os.link
    winner = {"status": "SYNTHETIC_CONCURRENT_PUBLICATION_CLAIM", "owner": "another controller"}
    winner_bytes = []
    def race(source, destination, *values, **keywords):
        if Path(source) == reserve and Path(destination) == failure:
            original_link(source, destination, *values, **keywords)
            write(recovery / "publication-claim.json", winner)
            winner_bytes.append(snapshot(recovery))
        return original_link(source, destination, *values, **keywords)
    monkeypatch.setattr(module.os, "link", race)
    before = snapshot(args.original_run)
    with pytest.raises(FileExistsError):
        module.perform(publish_args(args))
    assert len(winner_bytes) == 1 and snapshot(recovery) == winner_bytes[0]
    assert not (recovery / "publication-receipt.json").exists()
    assert not (state / "publication-failure.json").exists()
    assert snapshot(args.original_run) == before and not Path(plan["output"]).exists()


def test_output_inside_original_or_checkout_refuses_before_any_claim(tmp_path, monkeypatch, kind):
    module, (args, plan, _, _, _) = prepare(tmp_path, monkeypatch)
    args.recovery_root = args.original_run if kind == "run" else Path(plan["repo_root"])
    before = snapshot(args.original_run)
    with pytest.raises(ValueError, match="protected"):
        module.perform(args)
    assert snapshot(args.original_run) == before and not paths(args)[1].exists()


def _claim_signal_worker(directory, phase, signal_name):
    """Real process signals at issue 6407's two precise post-claim windows."""
    args, plan, _, _, _ = fixture(directory / "fixture")
    module = helper()
    module.checkout = lambda root: None
    if phase == "publication":
        module.perform(args)
        args = publish_args(args)
    recovery, state = paths(args)
    target = state / "claim.json" if phase == "validation" else recovery / "publication-claim.json"
    before = snapshot(args.original_run)
    dispositions = {number: signal.getsignal(number) for number in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP)}
    original_write = module.write
    delivered = []
    def signal_after_claim(path, value):
        result = original_write(path, value)
        if Path(path) == target:
            delivered.append(signal_name)
            os.kill(os.getpid(), getattr(signal, signal_name))
        return result
    module.write = signal_after_claim
    try:
        module.perform(args)
    except InterruptedError:
        pass
    else:
        raise AssertionError("real signal did not refuse recovery")
    assert delivered == [signal_name]
    assert all(signal.getsignal(number) == previous for number, previous in dispositions.items())
    assert snapshot(args.original_run) == before
    assert not Path(plan["output"]).exists() and not (recovery / "manifest.json").exists()
    if phase == "validation":
        receipt = json.loads((recovery / "recovery-receipt.json").read_bytes())
        terminal = json.loads((state / "failure.json").read_bytes())
        assert receipt["status"] == terminal["status"] == "RECOVERY_REFUSED"
        args.recovery_root = directory / "different-recovery-root"
    else:
        receipt = json.loads((recovery / "publication-receipt.json").read_bytes())
        terminal = json.loads((state / "publication-failure.json").read_bytes())
        assert receipt["status"] == terminal["status"] == "RECOVERY_PUBLICATION_REFUSED"
    assert "InterruptedError" in receipt["failure"] and (recovery / "failure.json").exists()
    try:
        module.perform(args)
    except ValueError:
        pass
    else:
        raise AssertionError("interrupted one-use claim allowed another attempt")
    write(directory / "signal-result.json", {"status": "PASS", "signal": signal_name, "phase": phase,
          "terminal_status": terminal["status"], "prior_dispositions_restored": True,
          "original_unchanged": True, "published": False, "retry_refused": True})


def test_real_sigterm_and_sighup_at_both_claim_windows_save_terminal_refusal(tmp_path, phase, signal_name):
    directory = tmp_path / (phase + "-" + signal_name)
    directory.mkdir()
    command = [sys.executable, "-B", str(Path(__file__).resolve()), "--claim-signal-worker",
               str(directory), phase, signal_name]
    environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1",
                       PYTHONPATH=str(ROOT) + os.pathsep + str(ROOT / "src"))
    result = subprocess.run(command, cwd=ROOT, env=environment, capture_output=True, timeout=120)
    (directory / "worker.stdout.txt").write_bytes(result.stdout)
    (directory / "worker.stderr.txt").write_bytes(result.stderr)
    assert result.returncode == 0, result.stderr.decode(errors="replace")
    receipt = json.loads((directory / "signal-result.json").read_bytes())
    assert receipt["status"] == "PASS" and receipt["signal"] == signal_name
    assert receipt["prior_dispositions_restored"] and receipt["original_unchanged"]
    assert receipt["retry_refused"] and not receipt["published"]


test_shared_replacement_state_and_existing_attempt_two_prevent_recovery = pytest.mark.parametrize(
    "kind", ("shared", "second"))(test_shared_replacement_state_and_existing_attempt_two_prevent_recovery)
test_ineligible_receipt_or_prior_artifacts_refuse_before_response_read = pytest.mark.parametrize(
    "kind", ("validator", "validator_zero", "published", "started", "unfinished", "auth", "model", "candidate", "output"))(
    test_ineligible_receipt_or_prior_artifacts_refuse_before_response_read)
test_missing_or_reused_authorization_never_opens_response = pytest.mark.parametrize(
    "reference", (None, "", " ", "synthetic original call", " synthetic original call "))(
    test_missing_or_reused_authorization_never_opens_response)
test_measured_inputs_and_validation_pins_refuse_before_claim = pytest.mark.parametrize(
    "kind", ("runner", "validator", "launcher", "definition", "record.yaml", "output-schema.json", "evidence-authority.json"))(
    test_measured_inputs_and_validation_pins_refuse_before_claim)
test_resume_refuses_bytes_receipt_claim_pins_and_authorization_tampering = pytest.mark.parametrize(
    "kind", ("bytes", "receipt", "claim", "input", "original", "authorization", "other_root"))(
    test_resume_refuses_bytes_receipt_claim_pins_and_authorization_tampering)
test_output_inside_original_or_checkout_refuses_before_any_claim = pytest.mark.parametrize(
    "kind", ("run", "checkout"))(test_output_inside_original_or_checkout_refuses_before_any_claim)
test_partial_or_completed_claim_write_failure_retains_terminal_refusal = pytest.mark.parametrize(
    "kind", ("partial", "completed"))(test_partial_or_completed_claim_write_failure_retains_terminal_refusal)
test_real_sigterm_and_sighup_at_both_claim_windows_save_terminal_refusal = pytest.mark.parametrize(
    "phase,signal_name", (("validation", "SIGTERM"), ("validation", "SIGHUP"),
                          ("publication", "SIGTERM"), ("publication", "SIGHUP")))(
    test_real_sigterm_and_sighup_at_both_claim_windows_save_terminal_refusal)


if __name__ == "__main__":
    if len(sys.argv) != 5 or sys.argv[1] != "--claim-signal-worker":
        raise SystemExit("only the synthetic claim-signal worker is supported")
    _claim_signal_worker(Path(sys.argv[2]), sys.argv[3], sys.argv[4])
