"""U4 offline front-door preparation tests, 2026-11-08.

The saved-probe canary uses actual captured S/R/preparation/composition and
the genuine permission verifier. Only the observation transcripts are
fabricated. No native executable, authentication, socket or provider runs.
Small dispatch tests explicitly stub registration verification; they prove
argument routing/refusal only, never registration or launch acceptance.
"""
from copy import deepcopy
from datetime import datetime, timezone
import json

import pytest

from data_sheets_schema import native_generation as cli
from data_sheets_schema import native_shared_contract as c
from data_sheets_schema import native_shared_permission_orchestration as permission
from data_sheets_schema import native_shared_registration_orchestration as registration
from data_sheets_schema import native_shared_execution_orchestration as execution
from data_sheets_schema import native_permission_probe as probe
from tests.test_native_shared_permissions import (
    authority, command_guidance, declaration, execution_v2, fabricated_manifest,
    inputs, isolated_modules, native_spec, prohibit_real_transports,
    shared_controller, synthetic_declaration,
)
from tests.utils.native_shared_consumer_scope import observe_consumer_calls


@pytest.fixture(scope="module")
def saved_case(tmp_path_factory):
    root = tmp_path_factory.mktemp("u4-genuine-saved-probe").resolve()
    isolation = isolated_modules.__wrapped__()
    names = next(isolation)
    try:
        with pytest.MonkeyPatch.context() as patch:
            from data_sheets_schema import api_runner as api
            patch.setattr(api, "CONCAT_DIR", root / "outputs")
            small = synthetic_declaration.__wrapped__(root, patch)
            doc = declaration.__wrapped__(small, patch)
            spec = native_spec.__wrapped__(doc, root, patch)
            source = inputs.__wrapped__(spec, names, root, patch)
            runtime = c.strict_json(source["runtime_path"].read_bytes())
            runtime["effort"] = "high"
            runtime["auth"]["subscriptionType"] = "max"
            # Fixture limits only, never live stop values.
            runtime["budget_guard_usd"] = "01.50"
            source["runtime_path"].write_bytes(c.canonical(runtime))
            prepared = execution_v2.prepare(source["selection"], source["runtime_path"], **source["kwargs"])
            instruction = root / "instruction.md"
            instruction.write_bytes(prepared["registration"]["instruction"].encode())
            composed = shared_controller.compose(c.canonical(prepared), instruction_path=instruction)
            _, replay, capture = shared_controller.reconstruct_composition(c.canonical(composed))
            selected = capture.document()
            expected = registration.permission_expectation(runtime, composed, replay,
                "Fabricated offline observations, never account or launch evidence."
                + command_guidance(composed["policy"]), root / "future-config",
                authority.dependency_identity())
            manifest = fabricated_manifest(expected, selected, root / "isolated-probes",
                capture.raw(selected["inputs"]["bundle"]["path"]))
            yield {"root": root, "expected": expected, "manifest": manifest,
                   "runtime": runtime, "selection": selected,
                   "render_spec": prepared["registration"]["render_spec"]}
    finally:
        isolation.close()


def choice_document(subject_raw, runtime):
    return {"kind": cli.CHOICE_KIND, "version": 1, "decisions": ["D105", "D106"],
        "account_label": "LBL work Claude Max", "effort": "high", "receipt_instrument": 4,
        "subject_sha256": cli.guard.sha(subject_raw),
        "runtime_sha256": cli.guard.sha(cli.guard.canonical(runtime))}


def saved_paths(tmp_path, saved_case):
    paths = {name: tmp_path.resolve() / (name + ".json")
             for name in ("expectation", "probe", "account-choice")}
    raw = c.canonical(saved_case["expected"])
    paths["expectation"].write_bytes(raw)
    paths["probe"].write_bytes(c.canonical(saved_case["manifest"]))
    paths["account-choice"].write_bytes(c.canonical(choice_document(raw, saved_case["runtime"])))
    return paths


def args_for(command, paths):
    return [command, *(value for name, path in paths.items() for value in ("--" + name, str(path)))]


def no_dispatch(*args, **kwargs):
    pytest.fail("offline front-door test attempted a producer or launch")


def test_validate_probe_uses_saved_bytes_and_never_runs_a_producer(saved_case, tmp_path, monkeypatch, capsys):
    paths = saved_paths(tmp_path, saved_case)
    monkeypatch.setattr(probe, "produce_saved_probe", no_dispatch)
    monkeypatch.setattr(execution, "launch", no_dispatch)
    targets = {("native_shared_permissions", name): () for name in ("_authority", "_trace_body")}
    with observe_consumer_calls(targets) as calls:
        assert cli.main(args_for("validate-probe", paths)) == 0
    result = json.loads(capsys.readouterr().out)
    assert set(targets) <= {key for key, _ in calls}
    assert result["result"]["checked"] is result["result"]["passed"] is True
    assert len(result["result"]["traces"]) == 7
    assert result["effort"] == "high" and result["selected_receipt_instrument"] == 4
    assert "receipt_instrument" not in result
    assert result["command"] == "validate-probe"
    assert "receipt-policy bytes, account identity and launch authorization are not established" in result["verification_scope"]
    assert result["account_choice_sha256"] == c.sha(paths["account-choice"].read_bytes())
    assert "not authenticated" in result["account_choice_basis"]
    assert "observation authenticity" in result["result"]["unassessed"]
    output = tmp_path / "verified-output.json"
    output.write_bytes(c.canonical(result))
    assert output.stat().st_size > 0


@pytest.mark.parametrize("kind", [None, "legacy", "d4d_native_permission_expected", 7])
def test_unknown_expectation_kind_refuses_before_probe_read_or_producer(saved_case, tmp_path, monkeypatch, kind):
    paths = saved_paths(tmp_path, saved_case)
    expected = deepcopy(saved_case["expected"])
    if kind is None:
        del expected["kind"]
    else:
        expected["kind"] = kind
    paths["expectation"].write_bytes(c.canonical(expected))
    paths["probe"].unlink()
    monkeypatch.setattr(probe, "produce_saved_probe", no_dispatch)
    monkeypatch.setattr(permission, "verify_saved_probe", no_dispatch)
    with pytest.raises(ValueError):
        cli.main(args_for("validate-probe", paths))


@pytest.mark.parametrize("field,value", [
    ("kind", "other"), ("version", True), ("version", 2), ("extra", "unknown"),
    ("account_label", "other account"), ("effort", "default"), ("receipt_instrument", 5),
    ("receipt_instrument", True), ("subject_sha256", "0" * 64),
    ("runtime_sha256", "0" * 64), ("decisions", ["D106"]),
])
def test_rehashed_account_choice_cannot_change_selected_intent(saved_case, tmp_path, monkeypatch, field, value):
    paths = saved_paths(tmp_path, saved_case)
    choice = c.strict_json(paths["account-choice"].read_bytes())
    choice[field] = value
    paths["account-choice"].write_bytes(c.canonical(choice))
    monkeypatch.setattr(permission, "verify_saved_probe", no_dispatch)
    with pytest.raises(ValueError, match="account choice"):
        cli.main(args_for("validate-probe", paths))


def test_missing_account_choice_field_refuses(saved_case, tmp_path, monkeypatch):
    paths = saved_paths(tmp_path, saved_case)
    value = c.strict_json(paths["account-choice"].read_bytes())
    del value["runtime_sha256"]
    paths["account-choice"].write_bytes(c.canonical(value))
    monkeypatch.setattr(permission, "verify_saved_probe", no_dispatch)
    with pytest.raises(ValueError, match="account choice"):
        cli.main(args_for("validate-probe", paths))


def test_saved_tampering_reaches_genuine_verifier_and_refuses(saved_case, tmp_path, monkeypatch):
    paths = saved_paths(tmp_path, saved_case)
    changed = deepcopy(saved_case["manifest"])
    del changed["members"]["traces/settled/transcript.jsonl"]
    paths["probe"].write_bytes(c.canonical(changed))
    monkeypatch.setattr(probe, "produce_saved_probe", no_dispatch)
    with pytest.raises(ValueError):
        cli.main(args_for("validate-probe", paths))


@pytest.mark.parametrize("changed", ["expectation", "probe", "account-choice"])
def test_verified_inputs_are_reread_before_success_output(saved_case, tmp_path, monkeypatch, capsys, changed):
    paths = saved_paths(tmp_path, saved_case)
    real_verify = permission.verify_saved_probe

    def verify_then_replace(raw, *, expected):
        result = real_verify(raw, expected=expected)
        paths[changed].write_bytes(paths[changed].read_bytes() + b"\n")
        return result

    monkeypatch.setattr(permission, "verify_saved_probe", verify_then_replace)
    with pytest.raises(ValueError, match="input changed"):
        cli.main(args_for("validate-probe", paths))
    assert not capsys.readouterr().out


@pytest.mark.parametrize("command", ["permission-probe", "validate-probe", "prepare-subscription-guard", "launch", "read-final"])
def test_commands_require_explicit_inputs_without_effects(monkeypatch, command):
    monkeypatch.setattr(probe, "produce_saved_probe", no_dispatch)
    monkeypatch.setattr(execution, "launch", no_dispatch)
    monkeypatch.setattr(execution, "read_final", no_dispatch)
    with pytest.raises(SystemExit) as exc:
        cli.main([command])
    assert exc.value.code == 2


@pytest.mark.parametrize("missing", ["review", "ci", "launch-word", "subscription-guard", "subscription-guard-sha256", "account-choice"])
def test_launch_requires_all_authority_arguments_before_any_dispatch(monkeypatch, missing):
    monkeypatch.setattr(execution, "launch", no_dispatch)
    argv = ["launch"]
    for name in ("registration", "review", "ci", "launch-word", "subscription-guard", "subscription-guard-sha256", "account-choice"):
        if name != missing:
            argv += ["--" + name, "/nonexistent/" + name]
    with pytest.raises(SystemExit) as exc:
        cli.main(argv)
    assert exc.value.code == 2


def guard_paths(tmp_path, saved_case, monkeypatch):
    """Routing fixture only: genuine guard, explicitly stubbed E verification."""
    now = 1_800_000_000
    runtime = saved_case["runtime"]
    monkeypatch.setattr(cli.guard, "_now", lambda: now)
    raw = b"routing-only synthetic E, not admission"
    monkeypatch.setattr(registration, "verified", lambda value: {
        "runtime": runtime, "selection": {"render_spec": saved_case["render_spec"]}
    } if value == raw else no_dispatch())
    paths = {name: tmp_path.resolve() / (name + ".json")
             for name in ("registration", "launch-word", "event", "account-choice")}
    paths["registration"].write_bytes(raw)
    paths["launch-word"].write_bytes(b"synthetic word fixture; no human authorization")
    paths["event"].write_bytes(c.canonical({"type": "rate_limit_event", "rate_limit_info": {
        "status": "allowed", "isUsingOverage": False, "rateLimitType": "seven_day",
        "utilization": 0.2, "resetsAt": now + 3600}}))
    paths["account-choice"].write_bytes(c.canonical(choice_document(raw, runtime)))
    argv = args_for("prepare-subscription-guard", paths) + [
        "--captured-at", datetime.fromtimestamp(now, timezone.utc).isoformat().replace("+00:00", "Z"),
        "--max-starting-weekly-utilization", "0.5", "--max-age-seconds", "60",
        "--output", str(tmp_path.resolve() / "guard.json")]
    return paths, argv


def test_prepare_guard_preserves_exact_join_and_never_dispatches(saved_case, tmp_path, monkeypatch, capsys):
    paths, argv = guard_paths(tmp_path, saved_case, monkeypatch)
    monkeypatch.setattr(execution, "launch", no_dispatch)
    monkeypatch.setattr(probe, "produce_saved_probe", no_dispatch)
    assert cli.main(argv) == 0
    output = tmp_path / "guard.json"
    raw = output.read_bytes()
    value = c.strict_json(raw)
    assert value["registration_sha256"] == c.sha(paths["registration"].read_bytes())
    assert value["launch_word_sha256"] == c.sha(paths["launch-word"].read_bytes())
    assert value["event_sha256"] == c.sha(paths["event"].read_bytes())
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["result"]["guard_sha256"] == c.sha(raw)
    with pytest.raises(FileExistsError):
        cli.main(argv)
    assert output.read_bytes() == raw
    guarded = cli.guard.load_guard(output, c.sha(raw), registration_raw=paths["registration"].read_bytes(),
        runtime=saved_case["runtime"], launch_word_path=paths["launch-word"])
    guarded.before_dispatch()
    with pytest.raises(ValueError, match="already consumed"):
        guarded.before_dispatch()


def test_v4_choice_cannot_bless_rehashed_v5_registration_metadata(saved_case, tmp_path, monkeypatch):
    changed = {**saved_case, "render_spec": deepcopy(saved_case["render_spec"])}
    recorded = changed["render_spec"]
    receipt = recorded["native_shared_receipt_policy"]
    policy = c.strict_json(receipt["raw_json"].encode())
    policy["receipt_instrument_version"] = 5
    raw = c.canonical(policy)
    receipt.update(raw_json=raw.decode(), sha256=c.sha(raw))
    selected = recorded["native_shared_generation_registration"]
    document = c.strict_json(selected["raw_json"].encode())
    document["receipt_policy"].update(sha256=c.sha(raw), bytes=len(raw))
    selected_raw = c.canonical(document)
    selected.update(raw_json=selected_raw.decode(), sha256=c.sha(selected_raw))
    _, argv = guard_paths(tmp_path, changed, monkeypatch)
    with pytest.raises(ValueError, match="native receipt policy"):
        cli.main(argv)
    assert not (tmp_path / "guard.json").exists()


@pytest.mark.parametrize("mutation", ["stale", "overage", "missing_word", "account_changed", "replaced_word"])
def test_guard_refusal_does_not_create_output(saved_case, tmp_path, monkeypatch, mutation):
    paths, argv = guard_paths(tmp_path, saved_case, monkeypatch)
    if mutation == "stale":
        monkeypatch.setattr(cli.guard, "_now", lambda: 1_800_000_061)
    elif mutation == "overage":
        event = c.strict_json(paths["event"].read_bytes())
        event["rate_limit_info"]["isUsingOverage"] = True
        paths["event"].write_bytes(c.canonical(event))
    elif mutation == "missing_word":
        paths["launch-word"].unlink()
    else:
        original = cli.guard.prepare_guard
        target = paths["account-choice" if mutation == "account_changed" else "launch-word"]
        def prepare_then_replace(**kwargs):
            result = original(**kwargs)
            target.write_bytes(target.read_bytes() + b"\n")
            return result
        monkeypatch.setattr(cli.guard, "prepare_guard", prepare_then_replace)
    with pytest.raises((ValueError, FileNotFoundError)):
        cli.main(argv)
    assert not (tmp_path / "guard.json").exists()


def test_bad_registration_refuses_without_guard_or_native_side_effects(tmp_path, monkeypatch):
    paths = {name: tmp_path.resolve() / (name + ".json")
             for name in ("registration", "launch-word", "event", "account-choice")}
    for path in paths.values():
        path.write_bytes(b"{}")
    argv = args_for("prepare-subscription-guard", paths) + [
        "--captured-at", "2026-11-08T00:00:00Z", "--max-starting-weekly-utilization", "0.5",
        "--max-age-seconds", "60", "--output", str(tmp_path.resolve() / "guard.json")]
    monkeypatch.setattr(execution, "launch", no_dispatch)
    monkeypatch.setattr(probe, "produce_saved_probe", no_dispatch)
    with pytest.raises(ValueError):
        cli.main(argv)
    assert not (tmp_path / "guard.json").exists()


def test_read_final_routes_offline_without_launch(saved_case, tmp_path, monkeypatch, capsys):
    raw = b"routing-only E; saved completion is tested in the execution suite"
    path = tmp_path / "registration.json"
    path.write_bytes(raw)
    choice = tmp_path / "choice.json"
    choice.write_bytes(c.canonical(choice_document(raw, saved_case["runtime"])))
    monkeypatch.setattr(registration, "verified", lambda value: {
        "runtime": saved_case["runtime"], "selection": {"render_spec": saved_case["render_spec"]}
    } if value == raw else no_dispatch())
    monkeypatch.setattr(execution, "launch", no_dispatch)
    calls = []
    def read(value):
        calls.append(value)
        return {"kind": "routing-only-saved-result"}
    monkeypatch.setattr(execution, "read_final", read)
    assert cli.main(["read-final", "--registration", str(path), "--account-choice", str(choice)]) == 0
    assert calls == [raw]
    assert json.loads(capsys.readouterr().out)["result"] == {"kind": "routing-only-saved-result"}
