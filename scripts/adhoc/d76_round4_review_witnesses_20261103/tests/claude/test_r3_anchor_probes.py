# Purpose: adversarial probes of #5213 round 3's retained construction binding
#   (api_runner._REGISTERED_INPUT_BINDINGS / _require_registered_input_spellings):
#   object.__setattr__, copy/deepcopy, pickle, replace, subclasses, lying str/PurePath,
#   id() reuse, registry mutation, mirror replacement, selector flips; each through
#   execute(resume=True/False) with spies on authority (assert_current), lock, date
#   recovery and a trap client. Also: native write_registration with a cached
#   instruction after mutation (a write entry outside the guard list).
# Inputs: synthetic fixtures from tests/. Outputs: printed observations + asserts.
# Date: 2026-11-02. Claude round-3 re-check of PR #5213. Offline. Run at d13c1711e
#   and at 0fa106e4d (where many cases are expected to differ: failing-before).
from dataclasses import dataclass, replace
import copy
import gc
import pickle
from pathlib import Path, PurePosixPath

import pytest
import yaml

from data_sheets_schema import api_runner as api, shared_generation as sg
from tests.test_generation_manifest_identity import external, offline  # noqa: F401
from tests.test_shared_generation_selection import registration_for, selected_spec as shared_v1

R3 = hasattr(api, "_REGISTERED_INPUT_BINDINGS")


class SpendReached(BaseException):
    pass


class Trap:
    def __init__(self):
        object.__setattr__(self, "events", [])

    def __getattr__(self, name):
        self.events.append(name)
        raise SpendReached("client attribute reached: " + name)


def _sg(external, monkeypatch):
    spec = shared_v1(external, registration_for(external))
    monkeypatch.chdir(external.bundle.parent)
    return replace(spec)


def _run(spec, monkeypatch, resume=True):
    calls = []
    real_assert = sg.assert_current
    monkeypatch.setattr(sg, "assert_current", lambda s: (calls.append("authority"), real_assert(s))[1])
    real_lock = api._exclusive_run
    monkeypatch.setattr(api, "_exclusive_run", lambda s: (calls.append("lock"), real_lock(s))[1])
    real_date = api._restore_resume_date
    monkeypatch.setattr(api, "_restore_resume_date", lambda s: (calls.append("date"), real_date(s))[1])
    trap = Trap()
    try:
        api.execute(spec, client=trap, resume=resume)
        outcome = "returned"
    except SpendReached as exc:
        outcome = "SPEND " + str(exc)
    except Exception as exc:  # noqa: BLE001
        outcome = f"refused {type(exc).__name__}: {str(exc)[:110]}"
    monkeypatch.undo()
    return outcome, trap.events, calls


def _report(label, result):
    outcome, events, calls = result
    print(f"{label}: {outcome} | client={events} | sidesteps={calls}")
    return outcome, events, calls


def _refused_clean(result):
    outcome, events, calls = result
    return outcome.startswith("refused") and not events and not calls


@pytest.mark.parametrize("resume", [True, False])
def test_object_setattr(external, monkeypatch, resume):
    spec = _sg(external, monkeypatch)
    object.__setattr__(spec, "bundle", Path(spec.bundle.name))
    r = _report(f"object.__setattr__ resume={resume}", _run(spec, monkeypatch, resume))
    assert _refused_clean(r)


@pytest.mark.parametrize("how", ["copy", "deepcopy"])
def test_copies_keep_binding(external, monkeypatch, how):
    spec = _sg(external, monkeypatch)
    spec.bundle = Path(spec.bundle.name)
    other = copy.copy(spec) if how == "copy" else copy.deepcopy(spec)
    r = _report(f"{how}(mutated)", _run(other, monkeypatch))
    assert _refused_clean(r)


def test_pickle_round_trip(external, monkeypatch):
    spec = _sg(external, monkeypatch)
    try:
        clone = pickle.loads(pickle.dumps(spec))
    except Exception as exc:  # noqa: BLE001
        print("pickle refused at dump/load:", type(exc).__name__, str(exc)[:100])
        return
    r = _report("pickle round trip (unmutated)", _run(clone, monkeypatch))
    assert _refused_clean(r) or not R3


def test_replace_with_decoy(external, monkeypatch):
    spec = _sg(external, monkeypatch)
    decoy = spec.bundle.with_name("decoy-" + spec.bundle.name)
    decoy.write_bytes(spec.bundle.read_bytes())
    with pytest.raises(ValueError) as info:
        replace(spec, bundle=decoy)
    print("replace(bundle=decoy):", info.value)


def test_subclass_skipping_post_init(external, monkeypatch):
    spec = _sg(external, monkeypatch)

    @dataclass
    class Skip(api.RunSpec):
        def __post_init__(self):
            pass

    forged = object.__new__(Skip)
    forged.__dict__.update(spec.__dict__)
    forged.bundle = Path(spec.bundle.name)
    r = _report("subclass without __post_init__", _run(forged, monkeypatch))
    assert _refused_clean(r) or not R3


@pytest.mark.parametrize("kind", ["str-subclass", "purepath-subclass"])
def test_lying_path_types(external, monkeypatch, kind):
    spec = _sg(external, monkeypatch)
    shown = str(spec.bundle)
    decoy = spec.bundle.with_name("liar-" + spec.bundle.name)
    decoy.write_bytes(spec.bundle.read_bytes() + b"liar\n")
    if kind == "str-subclass":
        class Liar(str):
            def __fspath__(self):
                return str(decoy)
        spec.bundle = Liar(shown)
    else:
        class LiarPath(PurePosixPath):
            def __fspath__(self):
                return str(decoy)

            def __eq__(self, other):
                return True
            __hash__ = PurePosixPath.__hash__
        spec.bundle = LiarPath(shown)
    r = _report(kind, _run(spec, monkeypatch))
    assert _refused_clean(r)


def test_id_reuse_by_forged_spec(external, monkeypatch):
    spec = _sg(external, monkeypatch)
    state = dict(spec.__dict__)
    target = id(spec)
    del spec
    gc.collect()
    forged = None
    for _ in range(200000):
        candidate = object.__new__(api.RunSpec)
        if id(candidate) == target:
            forged = candidate
            break
        del candidate
    if forged is None:
        print("id reuse: no collision found in 200000 allocations (inconclusive)")
        return
    forged.__dict__.update(state)
    r = _report("forged spec at a reused id", _run(forged, monkeypatch))
    assert _refused_clean(r) or not R3


@pytest.mark.skipif(not R3, reason="round-3 registry absent")
@pytest.mark.parametrize("how", ["clear", "pop", "forge-entry", "monkeypatch-lookup"])
def test_registry_mutation(external, monkeypatch, how):
    import weakref
    spec = _sg(external, monkeypatch)
    spec.bundle = Path(spec.bundle.name)
    if how == "clear":
        api._REGISTERED_INPUT_BINDINGS.clear()
    elif how == "pop":
        api._REGISTERED_INPUT_BINDINGS.pop(id(spec))
    elif how == "forge-entry":
        old = api._input_binding(spec)
        mirror = tuple((n, None if getattr(spec, n) is None else str(getattr(spec, n)))
                       for n in ("bundle", "manifest", "chunk_manifest"))
        spec._registered_input_spellings = mirror
        api._REGISTERED_INPUT_BINDINGS[id(spec)] = (weakref.ref(spec), api._RegisteredInputBinding(
            mirror, old.selectors, None))
    else:
        monkeypatch.setattr(api, "_require_registered_input_spellings", lambda s: None)
    r = _report(f"registry {how}", _run(spec, monkeypatch))
    if how in ("clear", "pop"):
        assert _refused_clean(r)


@pytest.mark.skipif(not R3, reason="round-3 mirror semantics")
@pytest.mark.parametrize("how", ["equal-tuple", "none", "list"])
def test_mirror_replacement(external, monkeypatch, how):
    spec = _sg(external, monkeypatch)
    original = spec._registered_input_spellings
    spec._registered_input_spellings = {"equal-tuple": tuple(tuple(r) for r in original),
                                        "none": None, "list": list(original)}[how]
    r = _report(f"mirror {how}", _run(spec, monkeypatch))
    assert _refused_clean(r)


@pytest.mark.parametrize("selector", ["registered_input_paths", "shared_generation_version",
                                      "shared_generation_registration"])
def test_selector_flip(external, monkeypatch, selector):
    spec = _sg(external, monkeypatch)
    spec.bundle = Path(spec.bundle.name)
    setattr(spec, selector, {"registered_input_paths": True, "shared_generation_version": 0,
                             "shared_generation_registration": None}[selector])
    r = _report(f"selector {selector} flipped + mutated", _run(spec, monkeypatch))
    assert _refused_clean(r)


def test_round2_private_rewrite_witness(external, monkeypatch):
    spec = _sg(external, monkeypatch)
    spec.bundle = Path(spec.bundle.name)
    spec._registered_input_spellings = tuple(
        (n, None if getattr(spec, n) is None else str(getattr(spec, n)))
        for n in ("bundle", "manifest", "chunk_manifest"))
    r = _report("round-2 private rewrite", _run(spec, monkeypatch))
    assert _refused_clean(r)


def test_native_write_registration_with_cached_instruction(external, monkeypatch, tmp_path):
    from data_sheets_schema import native_attribution_registration as nar
    metadata = yaml.safe_load(external.manifest.read_bytes())
    metadata["projects"][external.project]["sources"][0]["processed_file"] = external.bundle.name
    external.manifest.write_text(yaml.safe_dump(metadata))
    monkeypatch.chdir(external.bundle.parent)
    spec = replace(external, condition="generic_v9", render_version=16, runtime="Claude Code",
                   native_source_attribution_version=1, native_source_attribution_max_checks=3)
    _ = spec.instruction                      # cached through the guarded renderer
    spec.bundle = Path(spec.bundle.name)      # mutate after caching
    out = tmp_path / "native-registration.json"
    try:
        result = nar.write_registration(spec, out)
        print("native write_registration after mutation: WROTE", out.exists(),
              "| render_spec bundle:", yaml.safe_load(out.read_text())["render_spec"]["bundle"])
    except Exception as exc:  # noqa: BLE001
        print("native write_registration after mutation: refused", type(exc).__name__, str(exc)[:120],
              "| file exists:", out.exists())
