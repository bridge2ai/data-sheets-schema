# Purpose: adversarial probes of the #5213 round-2 execution boundary (Codex P2 fix,
#   api_runner._require_registered_input_spellings) and the H4 reorder in execute():
#   bypass via the private binding, via disabling selectors, via dataclasses.replace,
#   via the _replay_only init field; refusal order for native/replay/SG specs; dry-run.
# Inputs: synthetic fixtures from tests/ (external, shared-generation v1 registration).
# Outputs: pytest results and printed observations; a trap client records any access.
# Date: 2026-11-01. Claude round-2 re-check of PR #5213. Offline; run at 0fa106e4d and
#   0460a69d8 (where the guard does not exist, so several cases are failing-before).
from dataclasses import replace
import copy
from pathlib import Path

import pytest
import yaml

from data_sheets_schema import api_runner as api
from tests.test_generation_manifest_identity import external, offline  # noqa: F401
from tests.test_shared_generation_selection import registration_for, selected_spec as shared_v1

HAS_GUARD = hasattr(api, "_require_registered_input_spellings")


class SpendReached(BaseException):
    pass


class Trap:
    """Any attribute access on the client is a provider-boundary event."""
    def __init__(self):
        object.__setattr__(self, "events", [])

    def __getattr__(self, name):
        self.events.append(name)
        raise SpendReached("client attribute reached: " + name)


def _sg(external, monkeypatch):
    spec = shared_v1(external, registration_for(external))
    monkeypatch.chdir(external.bundle.parent)
    return replace(spec)


def _run(spec, **kw):
    trap = Trap()
    try:
        api.execute(spec, client=trap, **kw)
        outcome = "returned"
    except SpendReached as exc:
        outcome = "SPEND: " + str(exc)
    except Exception as exc:  # noqa: BLE001
        outcome = f"refused {type(exc).__name__}: {str(exc)[:120]}"
    return outcome, trap.events


@pytest.mark.parametrize("resume", [True, False])
def test_public_mutation_refuses_before_authority_lock_date_or_client(external, monkeypatch, resume):
    spec = _sg(external, monkeypatch)
    calls = []
    from data_sheets_schema import shared_generation as sg
    real_assert = sg.assert_current
    monkeypatch.setattr(sg, "assert_current", lambda s: (calls.append("assert_current"), real_assert(s))[1])
    real_lock = api._exclusive_run
    monkeypatch.setattr(api, "_exclusive_run", lambda s: (calls.append("lock"), real_lock(s))[1])
    real_date = api._restore_resume_date
    monkeypatch.setattr(api, "_restore_resume_date", lambda s: (calls.append("date"), real_date(s))[1])
    spec.bundle = Path(spec.bundle.name)
    outcome, events = _run(spec, resume=resume)
    print("public-mutation", resume, outcome, events, calls)
    assert events == [] and calls == [] and "spelling changed" in outcome


def test_private_binding_replacement_bypasses_the_guard(external, monkeypatch):
    spec = _sg(external, monkeypatch)
    spec.bundle = Path(spec.bundle.name)
    if HAS_GUARD:
        spec._registered_input_spellings = tuple(
            (n, None if getattr(spec, n) is None else str(getattr(spec, n)))
            for n in ("bundle", "manifest", "chunk_manifest"))
    outcome, events = _run(spec)
    print("private-binding-rewrite:", outcome, events)


def test_clearing_private_binding_alone_still_refuses_shared(external, monkeypatch):
    spec = _sg(external, monkeypatch)
    spec.bundle = Path(spec.bundle.name)
    spec._registered_input_spellings = None
    outcome, events = _run(spec)
    print("clear-binding-shared:", outcome, events)
    assert events == [] and "no construction binding" in outcome


def test_explicit_flag_disabled_and_binding_cleared(external, monkeypatch):
    monkeypatch.chdir(external.bundle.parent)
    spec = replace(external, condition="generic_v8", registered_input_paths=True)
    spec.bundle = Path(spec.bundle.name)
    spec.registered_input_paths = False
    spec._registered_input_spellings = None
    outcome, events = _run(spec)
    print("explicit-disabled+cleared:", outcome, events)


def test_replace_after_mutation_revalidates(external, monkeypatch):
    spec = _sg(external, monkeypatch)
    original = spec.bundle
    spec.bundle = Path(spec.bundle.name)
    healed = replace(spec)
    print("replace(relative):", healed.bundle, getattr(healed, "_registered_input_spellings", "n/a"))
    assert healed.bundle == original
    decoy = original.with_name("decoy-" + original.name)
    decoy.write_bytes(original.read_bytes())
    spec.bundle = decoy
    with pytest.raises(ValueError, match="source selection differs"):
        replace(spec)


def test_replay_flag_via_replace_and_copy(external, monkeypatch):
    spec = _sg(external, monkeypatch)
    spec.bundle = Path(spec.bundle.name)
    outcome, events = _run(replace(spec, _replay_only=True))
    print("replace(_replay_only=True):", outcome, events)
    assert events == [] and "historical prompt replay cannot execute" in outcome
    outcome, events = _run(copy.copy(spec))
    print("copy.copy(mutated):", outcome, events)
    assert events == [] and ("spelling changed" in outcome or not HAS_GUARD)


def _native(external, monkeypatch):
    metadata = yaml.safe_load(external.manifest.read_bytes())
    metadata["projects"][external.project]["sources"][0]["processed_file"] = external.bundle.name
    external.manifest.write_text(yaml.safe_dump(metadata))
    monkeypatch.chdir(external.bundle.parent)
    return replace(external, condition="generic_v9", render_version=16, runtime="Claude Code",
                   native_source_attribution_version=1, native_source_attribution_max_checks=3)


def test_order_native_offline_refusal_precedes_the_guard(external, monkeypatch):
    spec = _native(external, monkeypatch)
    spec.bundle = Path(spec.bundle.name)
    outcome, events = _run(spec)
    print("native mutated, shipped order:", outcome, events)
    assert events == [] and "native source attribution is offline-only" in outcome
    if HAS_GUARD:
        # Reverse order (guard first) would also refuse, with the guard's diagnostic.
        with pytest.raises(ValueError, match="spelling changed"):
            api._require_registered_input_spellings(spec)


def test_order_historical_replay_precedes_the_guard(external, monkeypatch):
    spec = _sg(external, monkeypatch)
    replay = api.RunSpec.from_render_spec(spec.render_spec(), project=spec.project,
                                          method=spec.method, label=spec.label)
    replay.bundle = Path(replay.bundle.name)
    outcome, events = _run(replay)
    print("replay mutated:", outcome, events)
    assert events == [] and "historical prompt replay cannot execute" in outcome
    if HAS_GUARD:
        assert api._require_registered_input_spellings(replay) is None   # guard skips replay


def test_dry_run_is_guarded_and_free(external, monkeypatch):
    spec = _sg(external, monkeypatch)
    outcome, events = _run(spec, dry_run=True)
    print("dry-run unmutated:", outcome[:60], events)
    assert events == [] and outcome == "returned"
    spec.bundle = Path(spec.bundle.name)
    outcome, events = _run(spec, dry_run=True)
    print("dry-run mutated:", outcome, events)
    assert events == [] and "spelling changed" in outcome


class TwoFaced:
    """os.PathLike whose str() is the bound spelling but whose fspath is a decoy."""
    def __init__(self, shown, actual):
        self.shown, self.actual = str(shown), str(actual)

    def __str__(self):
        return self.shown

    def __fspath__(self):
        return self.actual


@pytest.mark.parametrize("kind", ["shared", "explicit"])
def test_pathlike_with_matching_str_but_other_fspath(external, monkeypatch, kind):
    if kind == "shared":
        spec = _sg(external, monkeypatch)
    else:
        monkeypatch.chdir(external.bundle.parent)
        spec = replace(external, condition="generic_v8", registered_input_paths=True)
    decoy = spec.bundle.with_name("two-faced-" + spec.bundle.name)
    decoy.write_bytes(spec.bundle.read_bytes() + b"decoy\n")
    spec.bundle = TwoFaced(spec.bundle, decoy)
    if HAS_GUARD:
        try:
            api._require_registered_input_spellings(spec)
            print(kind, "two-faced pathlike: guard PASSED")
        except ValueError as exc:
            print(kind, "two-faced pathlike: guard refused:", exc)
    outcome, events = _run(spec)
    print(kind, "two-faced pathlike execute:", outcome, events)
