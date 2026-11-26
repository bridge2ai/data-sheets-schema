"""First-scoring controls for issues 6395, 6406 and 6411, 2026-11-26.

Only synthetic records, fake credentials and committed executable stand-ins run.
The pinned measured executor and exact-file validator remain unchanged. Original
refused payload reads are forbidden while the replacement helper is exercised.
"""
from copy import deepcopy
import json
import os
from pathlib import Path
import signal
import threading
import time
from unittest.mock import patch

import pytest

from tests.test_root_scope_repeats import ROOT, load_module, synthetic_run


HELPER = ROOT / "scripts/adhoc/replace_first_root_scope_scoring_20261126.py"


def replacement_helper():
    return load_module(HELPER, "first_scoring_replacement_controls")


def snapshot(directory):
    return {path.relative_to(directory).as_posix(): path.read_bytes()
            for path in directory.rglob("*") if path.is_file()}


def set_case(tools, **changes):
    path = tools / "case.json"
    case = json.loads(path.read_bytes())
    case.update(changes)
    path.write_text(json.dumps(case) + "\n")


def refused_fixture(directory, monkeypatch, family="rubric10"):
    helper = replacement_helper()
    original_args, tree, tools, evaluation, unused = synthetic_run(directory, family, exit=7)
    first = directory / "runs/synthetic-01"
    first.parent.mkdir()
    original_args.run_directory = first
    scorer = helper.support._load_scorer(tree)
    original = helper.support.in_checkout(tree, scorer.build_plan, original_args)
    with pytest.raises(scorer.ScorerError, match="Codex failed"):
        helper.support.in_checkout(tree, scorer.execute, original, original_args)
    assert helper.read_json(first / "receipt.json")["status"] == "REFUSED"
    set_case(tools, exit=0)
    monkeypatch.setattr(helper.support, "_checkout", lambda root: None)
    args = helper.parser().parse_args([
        "--scoring-root", str(tree), "--refused-run", str(first), "--timeout", "30",
        "--replacement-authorization-reference", "separate synthetic replacement authorization",
        "--plan",
    ])
    return helper, args, original_args, original, tools, evaluation


def no_original_payload_reads(first):
    real_open = Path.open

    def guarded(path, *args, **kwargs):
        if first in path.parents and path not in (first / "plan.json", first / "receipt.json"):
            raise AssertionError("original refused payload must remain unread")
        return real_open(path, *args, **kwargs)

    return patch.object(Path, "open", guarded)


def test_plan_is_metadata_only_and_permits_only_named_runtime_relocation(tmp_path, monkeypatch):
    helper, args, original_args, original, tools, _ = refused_fixture(tmp_path / "plan", monkeypatch)
    first = args.refused_run
    before = snapshot(tmp_path)
    with no_original_payload_reads(first), patch.object(helper.support.subprocess, "Popen",
                                                       side_effect=AssertionError("plan launched a process")):
        job = helper.build_job(args)
    assert snapshot(tmp_path) == before
    assert job["attempt"] == 2 and job["scoring_replicate"] == 1
    assert job["plan"]["output"] == original["output"]
    assert job["plan"]["runner_sha256"] == helper.support.RUNNER_SHA
    assert Path(job["state_directory"]) == first.parent / "first-scoring-remediations" / first.name
    assert Path(job["plan"]["run_directory"]) == first.with_name("synthetic-02")
    for key in ("identity", "inputs", "prompt", "prompt_sha256", "requested", "auth_file",
                "validation_sha256", "executable_sha256", "definition_provenance"):
        assert job["plan"][key] == original[key]
    assert not Path(job["state_directory"]).exists()
    assert not Path(job["plan"]["run_directory"]).exists()


def test_success_executes_exact_compared_object_without_rebuild_and_binds_publication(tmp_path, monkeypatch):
    for family in ("rubric10", "rubric20"):
        helper, args, original_args, original, tools, _ = refused_fixture(tmp_path / family, monkeypatch, family)
        before = snapshot(args.refused_run)
        auth_before = original_args.auth_file.read_bytes()
        job = helper.build_job(args)
        scorer = helper.support._load_scorer(args.scoring_root)
        measured_execute = scorer.execute
        received = []

        def execute(compared, invocation):
            received.append(compared)
            assert compared is job["plan"]
            return measured_execute(compared, invocation)

        monkeypatch.setattr(scorer, "execute", execute)
        monkeypatch.setattr(scorer, "main", lambda *unused: pytest.fail("rebuild through main"))
        monkeypatch.setattr(scorer, "build_plan", lambda *unused: pytest.fail("post-comparison rebuild"))
        monkeypatch.setattr(helper.support, "_load_scorer", lambda root: scorer)
        old_handlers = {number: signal.getsignal(number) for number in helper.SIGNALS}
        with no_original_payload_reads(args.refused_run):
            result = helper.execute_job(job, args)
        assert received == [job["plan"]]
        assert snapshot(args.refused_run) == before
        assert original_args.auth_file.read_bytes() == auth_before
        assert {number: signal.getsignal(number) for number in helper.SIGNALS} == old_handlers
        raw = Path(original["output"]).read_bytes()
        assert raw == (tools / "validated-snapshot.json").read_bytes()
        assert result["status"] == "FIRST_SCORING_REPLACEMENT_PUBLISHED"
        assert result["action"] == "replacement"
        assert result["accepted_output_sha256"] == result["validator_input_sha256"] == helper.sha(raw)
        assert result["destination_sha256"] == helper.sha(raw)
        assert helper.read_json(job["manifest_path"]) == result
        claim = helper.read_json(job["claim_path"])
        assert claim["action"] == "replacement" and claim["attempt"] == 2
        assert result["claim_sha256"] == helper.sha(Path(job["claim_path"]).read_bytes())
        for kind in ("plan", "receipt"):
            assert result["actual_" + kind + "_sha256"] == helper.sha(Path(result["actual_" + kind]).read_bytes())
            assert result["refused_attempt"][kind + "_sha256"] == helper.sha(before[kind + ".json"])
        assert not (Path(job["plan"]["codex_home"]) / "auth.json").exists()


def test_changed_scope_between_comparison_and_executor_is_refused_without_rebuild(tmp_path, monkeypatch):
    helper, args, _, _, tools, _ = refused_fixture(tmp_path / "drift", monkeypatch)
    job = helper.build_job(args)
    scorer = helper.support._load_scorer(args.scoring_root)
    original_execute = scorer.execute
    invocation_before = (tools / "invocation.json").read_bytes()

    def drift_then_execute(plan, invocation):
        scope = Path(plan["inputs"]["scope-context.json"]["source"])
        changed = json.loads(scope.read_bytes())
        changed["reason"] += " A changed but otherwise valid reason."
        scope.write_text(json.dumps(changed) + "\n")
        assert plan is job["plan"]
        return original_execute(plan, invocation)

    monkeypatch.setattr(scorer, "execute", drift_then_execute)
    monkeypatch.setattr(helper.support, "_load_scorer", lambda root: scorer)
    with pytest.raises(scorer.ScorerError, match="changed"):
        helper.execute_job(job, args)
    terminal = helper.read_json(job["manifest_path"])
    assert terminal["status"] == "FIRST_SCORING_REPLACEMENT_REFUSED"
    assert terminal["actual_plan_sha256"] is None and terminal["actual_receipt_sha256"] is None
    assert terminal["accepted_output_sha256"] is None
    assert not terminal["destination_exists"]
    assert (tools / "invocation.json").read_bytes() == invocation_before
    assert not Path(job["plan"]["run_directory"]).exists()


def test_full_comparison_refuses_arbitrary_field_and_shell_drift(tmp_path, monkeypatch):
    helper, args, _, _, _, _ = refused_fixture(tmp_path / "full-plan", monkeypatch)
    job = helper.build_job(args)
    changes = [
        ("prompt", job["plan"]["prompt"] + "\n"),
        ("output", str(tmp_path / "another-publication.json")),
        ("auth_file", str(tmp_path / "another-auth.json")),
        ("commands_shell", ["echo substituted", "echo validator"]),
        ("unexpected_field", str(args.refused_run)),
    ]
    for key, value in changes:
        changed = deepcopy(job)
        changed["plan"][key] = value
        changed["plan_sha256"] = helper.plan_digest(changed["plan"])
        with pytest.raises(ValueError, match="beyond named runtime paths"):
            helper.verify_job(changed)
    copied = deepcopy(job)
    copied["scorer_arguments"] += ["--context", "unregistered.yaml"]
    with pytest.raises(ValueError, match="arguments differ"):
        helper.verify_job(copied)
    changed = deepcopy(job)
    changed["source_head"] = "0" * 40
    with pytest.raises(ValueError, match="source or mode"):
        helper.verify_job(changed)


def test_relocation_does_not_globally_replace_embedded_text(tmp_path, monkeypatch):
    helper, args, _, original, _, _ = refused_fixture(tmp_path / "literal", monkeypatch)
    original["arbitrary_note"] = "Literal original path " + str(args.refused_run)
    expected = helper.relocated_plan(original, args.refused_run.with_name("synthetic-02"))
    assert expected["arbitrary_note"] == original["arbitrary_note"]


def test_existing_recovery_claim_or_second_attempt_blocks_replacement(tmp_path, monkeypatch):
    for existing in ("recovery", "second"):
        helper, args, _, _, _, _ = refused_fixture(tmp_path / existing, monkeypatch)
        job = helper.build_job(args)
        path = Path(job["state_directory"] if existing == "recovery" else job["plan"]["run_directory"])
        path.mkdir(parents=True)
        if existing == "recovery":
            helper.write_json(path / "claim.json", {"action": "recovery"})
        before = snapshot(tmp_path / existing)
        with pytest.raises(ValueError, match="claimed|third attempt"):
            helper.execute_job(job, args)
        assert snapshot(tmp_path / existing) == before


def test_claim_is_exclusive_even_if_recovery_wins_after_preflight(tmp_path, monkeypatch):
    helper, args, _, _, tools, _ = refused_fixture(tmp_path / "race", monkeypatch)
    job = helper.build_job(args)
    real_mkdir = Path.mkdir
    state = Path(job["state_directory"])

    def competing_mkdir(path, *positional, **named):
        if path == state:
            real_mkdir(path)
            helper.write_json(path / "claim.json", {"action": "recovery", "winner": True})
        return real_mkdir(path, *positional, **named)

    invocation_before = (tools / "invocation.json").read_bytes()
    with patch.object(Path, "mkdir", competing_mkdir), pytest.raises(FileExistsError):
        helper.execute_job(job, args)
    assert helper.read_json(state / "claim.json") == {"action": "recovery", "winner": True}
    assert not (state / "manifest.json").exists()
    assert (tools / "invocation.json").read_bytes() == invocation_before


def test_authorization_is_distinct_and_required_before_claim(tmp_path, monkeypatch):
    helper, args, original_args, _, tools, _ = refused_fixture(tmp_path / "authority", monkeypatch)
    job = helper.build_job(args)
    before = snapshot(tmp_path)
    for word in (None, " ", original_args.authorization_reference,
                 " " + original_args.authorization_reference + " "):
        args.replacement_authorization_reference = word
        with pytest.raises(ValueError, match="authorization"):
            helper.execute_job(job, args)
        assert snapshot(tmp_path) == before


def test_failed_attempt_is_terminal_and_cannot_be_retried(tmp_path, monkeypatch):
    helper, args, original_args, _, tools, _ = refused_fixture(tmp_path / "second-refusal", monkeypatch)
    job = helper.build_job(args)
    set_case(tools, exit=9)
    with pytest.raises(ValueError, match="Codex failed"):
        helper.execute_job(job, args)
    terminal = helper.read_json(job["manifest_path"])
    assert terminal["status"] == "FIRST_SCORING_REPLACEMENT_REFUSED"
    assert terminal["actual_plan_sha256"] and terminal["actual_receipt_sha256"]
    assert terminal["accepted_output_sha256"] is None
    assert helper.read_json(terminal["actual_receipt"])["status"] == "REFUSED"
    assert not (Path(job["plan"]["codex_home"]) / "auth.json").exists()
    before = snapshot(tmp_path)
    with pytest.raises(ValueError, match="third attempt"):
        helper.build_job(args)
    args.refused_run = Path(job["plan"]["run_directory"])
    with pytest.raises(ValueError, match="ending -01"):
        helper.build_job(args)
    assert snapshot(tmp_path) == before


def test_partial_publication_never_becomes_an_accepted_terminal(tmp_path, monkeypatch):
    helper, args, _, _, _, _ = refused_fixture(tmp_path / "partial", monkeypatch)
    job = helper.build_job(args)
    scorer = helper.support._load_scorer(args.scoring_root)

    def partial(plan, invocation):
        output = Path(plan["output"])
        output.parent.mkdir(parents=True)
        output.write_bytes(b"partial synthetic publication")
        raise OSError("synthetic interrupted exclusive publication")

    monkeypatch.setattr(scorer, "execute", partial)
    monkeypatch.setattr(helper.support, "_load_scorer", lambda root: scorer)
    with pytest.raises(OSError, match="interrupted exclusive publication"):
        helper.execute_job(job, args)
    terminal = helper.read_json(job["manifest_path"])
    assert terminal["status"] == "FIRST_SCORING_REPLACEMENT_REFUSED"
    assert terminal["destination_exists"] is True
    assert terminal["accepted_output_sha256"] is None
    assert "output_sha256" not in terminal


def test_claim_write_failure_keeps_consumed_terminal_without_starting_attempt(tmp_path, monkeypatch):
    helper, args, _, _, tools, _ = refused_fixture(tmp_path / "claim-failure", monkeypatch)
    job = helper.build_job(args)
    real_write = helper.write_json

    def failed_claim(path, value):
        if str(path) == job["claim_path"]:
            raise OSError("synthetic claim write failure")
        return real_write(path, value)

    monkeypatch.setattr(helper, "write_json", failed_claim)
    with pytest.raises(OSError, match="claim write failure"):
        helper.execute_job(job, args)
    terminal = helper.read_json(job["manifest_path"])
    assert terminal["status"] == "FIRST_SCORING_REPLACEMENT_REFUSED"
    assert terminal["claim_sha256"] is None
    assert not Path(job["plan"]["run_directory"]).exists()
    with pytest.raises(ValueError, match="already claimed"):
        helper.build_job(args)


def test_partial_attempt_metadata_is_hash_bound_in_terminal_failure(tmp_path, monkeypatch):
    helper, args, _, _, _, _ = refused_fixture(tmp_path / "partial-metadata", monkeypatch)
    job = helper.build_job(args)
    scorer = helper.support._load_scorer(args.scoring_root)

    def interrupted_metadata(plan, invocation):
        run = Path(plan["run_directory"])
        run.mkdir()
        (run / "plan.json").write_bytes(b"{partial")
        (run / "receipt.json").write_bytes(b"")
        raise OSError("synthetic metadata write interruption")

    monkeypatch.setattr(scorer, "execute", interrupted_metadata)
    monkeypatch.setattr(helper.support, "_load_scorer", lambda root: scorer)
    with pytest.raises(OSError, match="metadata write interruption"):
        helper.execute_job(job, args)
    terminal = helper.read_json(job["manifest_path"])
    assert terminal["status"] == "FIRST_SCORING_REPLACEMENT_REFUSED"
    assert terminal["actual_plan_sha256"] == helper.sha(b"{partial")
    assert terminal["actual_receipt_sha256"] == helper.sha(b"")
    assert terminal["accepted_output_sha256"] is None


def test_receipt_removed_after_acceptance_cannot_receive_published_terminal(tmp_path, monkeypatch):
    helper, args, _, _, _, _ = refused_fixture(tmp_path / "removed-after-acceptance", monkeypatch)
    job = helper.build_job(args)
    real_accepted = helper.support._accepted

    def remove_after_acceptance(plan, plan_path, receipt_path):
        result = real_accepted(plan, plan_path, receipt_path)
        Path(receipt_path).unlink()
        return result

    monkeypatch.setattr(helper.support, "_accepted", remove_after_acceptance)
    with pytest.raises(FileNotFoundError):
        helper.execute_job(job, args)
    terminal = helper.read_json(job["manifest_path"])
    assert terminal["status"] == "FIRST_SCORING_REPLACEMENT_REFUSED"
    assert terminal["actual_receipt_sha256"] is None
    assert terminal["accepted_output_sha256"] is None
    assert terminal["destination_exists"] is True


def test_receipt_changed_to_refused_after_acceptance_cannot_receive_published_terminal(tmp_path, monkeypatch):
    helper, args, _, _, _, _ = refused_fixture(tmp_path / "changed-after-acceptance", monkeypatch)
    job = helper.build_job(args)
    real_accepted = helper.support._accepted

    def change_after_acceptance(plan, plan_path, receipt_path):
        result = real_accepted(plan, plan_path, receipt_path)
        changed = helper.read_json(receipt_path)
        changed["status"] = "REFUSED"
        Path(receipt_path).write_text(json.dumps(changed) + "\n")
        return result

    monkeypatch.setattr(helper.support, "_accepted", change_after_acceptance)
    with pytest.raises(ValueError, match="changed during verification"):
        helper.execute_job(job, args)
    terminal = helper.read_json(job["manifest_path"])
    assert terminal["status"] == "FIRST_SCORING_REPLACEMENT_REFUSED"
    assert terminal["actual_receipt_sha256"] == helper.sha(Path(terminal["actual_receipt"]).read_bytes())
    assert helper.read_json(terminal["actual_receipt"])["status"] == "REFUSED"
    assert terminal["accepted_output_sha256"] is None


def test_every_verified_binding_is_checked_again_before_terminal_publication(tmp_path, monkeypatch):
    for label in ("actual_plan", "actual_receipt", "original_plan", "original_receipt", "claim", "output"):
        helper, args, _, _, _, _ = refused_fixture(tmp_path / label, monkeypatch)
        job = helper.build_job(args)
        paths = {
            "actual_plan": Path(job["plan"]["run_directory"]) / "plan.json",
            "actual_receipt": Path(job["plan"]["run_directory"]) / "receipt.json",
            "original_plan": Path(job["refused_attempt"]["plan_path"]),
            "original_receipt": Path(job["refused_attempt"]["receipt_path"]),
            "claim": Path(job["claim_path"]), "output": Path(job["plan"]["output"]),
        }
        target = paths[label]
        real_hash = helper.retained_metadata_hash
        changed = []

        def drift_at_final_boundary(path):
            if not changed:
                target.write_bytes(target.read_bytes() + b" ")
                changed.append(True)
            return real_hash(path)

        monkeypatch.setattr(helper, "retained_metadata_hash", drift_at_final_boundary)
        with pytest.raises(ValueError, match="binding changed before terminal declaration"):
            helper.execute_job(job, args)
        terminal = helper.read_json(job["manifest_path"])
        assert terminal["status"] == "FIRST_SCORING_REPLACEMENT_REFUSED"
        assert terminal["accepted_output_sha256"] is None
        assert terminal["binding_failures"]
        assert "destination_sha256" not in terminal
        key = {"original_plan": "observed_original_plan_sha256",
               "original_receipt": "observed_original_receipt_sha256",
               "output": "observed_destination_sha256"}.get(label, label + "_sha256")
        assert terminal[key] == helper.sha(target.read_bytes())
        assert terminal[key] != terminal["verified_bindings"][key]


def test_metadata_tampering_or_unfinished_original_is_refused_before_claim(tmp_path, monkeypatch):
    for change in ("status", "finished", "cleanup", "plan"):
        helper, args, _, _, _, _ = refused_fixture(tmp_path / change, monkeypatch)
        receipt_path = args.refused_run / "receipt.json"
        receipt = helper.read_json(receipt_path)
        if change == "status":
            receipt["status"] = "STARTED"
        elif change == "finished":
            receipt.pop("finished_utc")
        elif change == "cleanup":
            receipt["auth_copy_absent"] = False
        else:
            receipt["plan_sha256"] = "0" * 64
        receipt_path.write_text(json.dumps(receipt) + "\n")
        before = snapshot(tmp_path / change)
        with pytest.raises(ValueError):
            helper.build_job(args)
        assert snapshot(tmp_path / change) == before


def test_changed_measured_runner_is_never_loaded(tmp_path, monkeypatch):
    helper, args, _, _, _, _ = refused_fixture(tmp_path / "runner", monkeypatch)
    runner = args.scoring_root / helper.support.RUNNER
    runner.write_bytes(runner.read_bytes() + b"\n# synthetic changed runner\n")
    with pytest.raises(ValueError, match="pinned scorer runner differs"):
        helper.build_job(args)


def signal_case(directory, monkeypatch, number):
    helper, args, original_args, _, tools, _ = refused_fixture(directory, monkeypatch)
    job = helper.build_job(args)
    before = snapshot(args.refused_run)
    auth_before = original_args.auth_file.read_bytes()
    set_case(tools, sleep_seconds=30)
    invocation_path = tools / "invocation.json"
    invocation_path.unlink()
    notices = []

    def signal_when_started():
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            try:
                invocation = json.loads(invocation_path.read_bytes())
            except (FileNotFoundError, json.JSONDecodeError):
                time.sleep(0.01)
                continue
            notices.append(invocation)
            os.kill(os.getpid(), number)
            return

    previous = {item: signal.getsignal(item) for item in helper.SIGNALS}
    sender = threading.Thread(target=signal_when_started, daemon=True)
    sender.start()
    try:
        with pytest.raises(InterruptedError, match="replacement interrupted"):
            helper.execute_job(job, args)
    finally:
        sender.join(timeout=16)
    assert notices and not sender.is_alive()
    invocation = notices[0]
    assert invocation["pgid"] == invocation["pid"] and invocation["pgid"] != os.getpgrp()
    with pytest.raises(ProcessLookupError):
        os.killpg(invocation["pgid"], 0)
    assert {item: signal.getsignal(item) for item in helper.SIGNALS} == previous
    assert original_args.auth_file.read_bytes() == auth_before
    assert snapshot(args.refused_run) == before
    assert not (Path(job["plan"]["codex_home"]) / "auth.json").exists()
    terminal = helper.read_json(job["manifest_path"])
    assert terminal["status"] == "FIRST_SCORING_REPLACEMENT_REFUSED"
    receipt = helper.read_json(terminal["actual_receipt"])
    assert receipt["status"] == "REFUSED" and receipt["auth_copy_absent"] is True
    assert terminal["accepted_output_sha256"] is None


def test_sigterm_stops_fake_child_and_retains_terminal_refusal(tmp_path, monkeypatch):
    signal_case(tmp_path / "term", monkeypatch, signal.SIGTERM)


def test_sighup_stops_fake_child_and_retains_terminal_refusal(tmp_path, monkeypatch):
    signal_case(tmp_path / "hup", monkeypatch, signal.SIGHUP)


def test_sigint_stops_fake_child_and_retains_terminal_refusal(tmp_path, monkeypatch):
    signal_case(tmp_path / "interrupt", monkeypatch, signal.SIGINT)


def finalization_signal_case(directory, monkeypatch, number, boundary):
    """Inject a real catchable signal at the reviewer's exact masking boundary."""
    helper, args, original_args, original, tools, _ = refused_fixture(directory, monkeypatch)
    job = helper.build_job(args)
    first_before = snapshot(args.refused_run)
    auth_before = original_args.auth_file.read_bytes()
    prior = {item: signal.getsignal(item) for item in helper.SIGNALS}
    actual_mask = signal.pthread_sigmask
    prior_mask = actual_mask(signal.SIG_BLOCK, [])
    actual_write = helper.write_json
    observations = []
    sent = []

    def at_mask_entry(how, numbers):
        if how == signal.SIG_BLOCK:
            observations.append({"claim": Path(job["claim_path"]).exists(),
                                 "manifest": Path(job["manifest_path"]).exists(),
                                 "destination": Path(original["output"]).exists()})
            if len(observations) == 2 and boundary == "mask-entry":
                sent.append(number)
                os.kill(os.getpid(), number)
        return actual_mask(how, numbers)

    def at_manifest_write(path, value):
        first_write = str(path) == job["manifest_path"] and not sent
        if first_write and boundary == "before-write":
            sent.append(number)
            os.kill(os.getpid(), number)
        result = actual_write(path, value)
        if first_write and boundary == "after-write":
            sent.append(number)
            os.kill(os.getpid(), number)
        return result

    restored = False
    try:
        with patch.object(signal, "pthread_sigmask", at_mask_entry), \
                patch.object(helper, "write_json", at_manifest_write), \
                no_original_payload_reads(args.refused_run), \
                pytest.raises(InterruptedError, match="replacement interrupted"):
            helper.execute_job(job, args)
        restored = {item: signal.getsignal(item) for item in helper.SIGNALS} == prior
        assert actual_mask(signal.SIG_BLOCK, []) == prior_mask
        assert not set(signal.sigpending()).intersection(helper.SIGNALS)
    finally:
        for item, disposition in prior.items():
            signal.signal(item, disposition)
        actual_mask(signal.SIG_SETMASK, prior_mask)
    assert restored
    assert sent == [number]
    assert len(observations) == 2
    assert observations[1] == {"claim": True, "manifest": False, "destination": True}
    assert snapshot(args.refused_run) == first_before
    assert original_args.auth_file.read_bytes() == auth_before
    run = Path(job["plan"]["run_directory"])
    assert helper.read_json(run / "receipt.json")["status"] == "VALIDATED_AND_PUBLISHED"
    assert not (Path(job["plan"]["codex_home"]) / "auth.json").exists()
    terminal = helper.read_json(job["manifest_path"])
    assert terminal["status"] == "FIRST_SCORING_REPLACEMENT_REFUSED"
    assert terminal["interruption_signals"] == [number]
    assert terminal["accepted_output_sha256"] is None
    assert "output_sha256" not in terminal and "destination_sha256" not in terminal
    assert terminal["destination_exists"] is True
    assert terminal["observed_destination_sha256"] == helper.sha(Path(original["output"]).read_bytes())
    assert terminal["actual_plan_sha256"] == helper.sha((run / "plan.json").read_bytes())
    assert terminal["actual_receipt_sha256"] == helper.sha((run / "receipt.json").read_bytes())
    archives = list(Path(job["state_directory"]).glob("unaccepted-manifest-*.json"))
    if boundary == "mask-entry":
        assert not archives
    else:
        assert len(archives) == 1
        assert helper.read_json(archives[0])["status"] == "FIRST_SCORING_REPLACEMENT_PUBLISHED"
    with pytest.raises(ValueError, match="third attempt"):
        helper.build_job(args)


def test_sigterm_at_finalizer_mask_entry_is_terminal_and_restores_handlers(tmp_path, monkeypatch):
    finalization_signal_case(tmp_path / "term-entry", monkeypatch, signal.SIGTERM, "mask-entry")


def test_sighup_at_finalizer_mask_entry_is_terminal_and_restores_handlers(tmp_path, monkeypatch):
    finalization_signal_case(tmp_path / "hup-entry", monkeypatch, signal.SIGHUP, "mask-entry")


def test_sigint_at_finalizer_mask_entry_is_terminal_and_restores_handlers(tmp_path, monkeypatch):
    finalization_signal_case(tmp_path / "int-entry", monkeypatch, signal.SIGINT, "mask-entry")


def test_pending_signals_before_manifest_write_are_terminal(tmp_path, monkeypatch):
    for number in (signal.SIGTERM, signal.SIGHUP, signal.SIGINT):
        finalization_signal_case(tmp_path / number.name, monkeypatch, number, "before-write")


def test_pending_signals_after_manifest_write_are_terminal(tmp_path, monkeypatch):
    for number in (signal.SIGTERM, signal.SIGHUP, signal.SIGINT):
        finalization_signal_case(tmp_path / number.name, monkeypatch, number, "after-write")
