"""Reduced retained-session shapes for issue 6384, 2026-11-26.

Structure sources: tab 197's repeat-refusal case2/case3 structural timelines and
22b reader timelines, named in the issue 6384 assignment. Fresh children have
metadata/task/context/settings at lines 1/2/10/11; the second own task/context
occurs at 23/24. The forked comparison has a copied parent prefix and settings
at ordinal 22. Padding replaces omitted message content; all IDs and paths are
synthetic. No retained response, score, credential or candidate is included.

Only session_identity is invoked. These fixtures never invoke a scorer, native
binary, schema validator, build_plan or publication; reader calls preserve all
fixture bytes. The fixture root is pytest's temporary directory, never a run
from either measured series.
"""
from copy import deepcopy
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path

import pytest


MODULE = Path(__file__).resolve().parents[1] / "scripts/adhoc/score_semantic_rubric_codex_20261125.py"
SPEC = importlib.util.spec_from_file_location("session_reader_controls_6384", MODULE)
scorer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(scorer)

ROOT_ID = "synthetic-root-thread"
CHILD_ID = "synthetic-child-thread"
ROOT_TURN = "synthetic-root-turn"
CHILD_TURNS = ("synthetic-child-turn-one", "synthetic-child-turn-two")
CHILD_PATH = "/root/fixture_review"
STAMP = "2026-01-01T00:00:30Z"
STARTED = datetime(2026, 1, 1, tzinfo=timezone.utc)
FINISHED = datetime(2026, 1, 1, 0, 1, tzinfo=timezone.utc)


def row(kind, payload):
    return {"timestamp": STAMP, "type": kind, "payload": payload}


def pad(rows, length):
    while len(rows) < length:
        rows.append(row("event_msg", {"type": "synthetic_content_omitted"}))


def task(turn):
    return row("event_msg", {"type": "task_started", "turn_id": turn,
                            "root_turn_id": ROOT_TURN,
                            "turn_attribution": {"turn_id": turn, "root_turn_id": ROOT_TURN}})


def context(turn, cwd):
    return row("turn_context", {"turn_id": turn, "root_turn_id": ROOT_TURN,
                                "model": scorer.MODEL, "effort": scorer.EFFORT, "cwd": cwd,
                                "synthetic_context_binding": "unchanged parent payload",
                                "synthetic_boolean_binding": True})


def complete(turn):
    return row("event_msg", {"type": "task_complete", "turn_id": turn, "root_turn_id": ROOT_TURN})


def snapshot(directory):
    return {str(path.relative_to(directory)): path.read_bytes()
            for path in directory.rglob("*") if path.is_file()}


class SessionCase:
    def __init__(self, directory, shape="fresh-one", mode="none"):
        self.directory = directory.resolve()
        self.run = self.directory / "synthetic-run"
        self.home = self.run / "codex-home"
        self.working = self.run / "working"
        self.working.mkdir(parents=True)
        self.sessions = self.home / "sessions"
        self.sessions.mkdir(parents=True)
        self.plan = {"run_directory": str(self.run), "codex_home": str(self.home),
                     "working_directory": str(self.working), "identity": {"version": "6.0"}}
        cwd = str(self.working)
        root_meta = row("session_meta", {"id": ROOT_ID, "cwd": cwd, "source": "exec",
                       "originator": "codex_exec", "cli_version": "0.172.0"})
        self.root = [root_meta, task(ROOT_TURN)]
        pad(self.root, 9)
        self.root.append(context(ROOT_TURN, cwd))
        pad(self.root, 21)
        parent_prefix = deepcopy(self.root)
        arguments = {"task_name": "fixture_review", "message": "synthetic reduced task"}
        if mode is not None:
            arguments["fork_turns"] = mode
        self.root.extend([
            row("response_item", {"type": "function_call", "name": "spawn_agent",
                                  "call_id": "synthetic-spawn", "arguments": json.dumps(arguments)}),
            row("response_item", {"type": "function_call_output", "call_id": "synthetic-spawn",
                                  "output": json.dumps({"task_name": CHILD_PATH})}),
        ])
        child_meta = row("session_meta", {"id": CHILD_ID, "cwd": cwd, "parent_thread_id": ROOT_ID,
                         "agent_path": CHILD_PATH, "cli_version": "0.172.0",
                         "source": {"subagent": {"thread_spawn": {
                             "parent_thread_id": ROOT_ID, "agent_path": CHILD_PATH}}}})
        settings = row("event_msg", {"type": "thread_settings_applied", "thread_id": CHILD_ID,
                       "thread_settings": {"model": scorer.MODEL, "reasoning_effort": scorer.EFFORT, "cwd": cwd}})
        if shape == "forked":
            child_meta["payload"]["forked_from_id"] = ROOT_ID
            child_meta["payload"]["subagent_history_start_ordinal"] = 22
            self.child = [child_meta, *parent_prefix, settings, task(CHILD_TURNS[0])]
            pad(self.child, 27)
            self.child.append(context(CHILD_TURNS[0], cwd))
            pad(self.child, 40)
            self.child.append(complete(CHILD_TURNS[0]))
        else:
            self.child = [child_meta, task(CHILD_TURNS[0])]
            pad(self.child, 9)
            self.child.extend([context(CHILD_TURNS[0], cwd), settings])
            if shape == "fresh-two":
                pad(self.child, 21)
                self.child.extend([complete(CHILD_TURNS[0]), task(CHILD_TURNS[1]), context(CHILD_TURNS[1], cwd)])
                pad(self.child, 32)
                self.child.append(complete(CHILD_TURNS[1]))
            else:
                assert shape == "fresh-one"
                pad(self.child, 23)
                self.child.append(complete(CHILD_TURNS[0]))
        # Child sorts before root: ownership must come from the correlated
        # parent session, never incidental filesystem enumeration order.
        self.root_path = self.sessions / "99-root.jsonl"
        self.child_path = self.sessions / "00-child.jsonl"
        self.write()

    def write(self):
        for path, rows in ((self.root_path, self.root), (self.child_path, self.child)):
            path.write_text("".join(json.dumps(item, sort_keys=True) + "\n" for item in rows), encoding="utf-8")
        (self.run / "codex.stdout.jsonl").write_text(json.dumps({"type": "thread.started", "thread_id": ROOT_ID}) + "\n", encoding="utf-8")

    def read(self):
        before = snapshot(self.directory)
        try:
            return scorer.session_identity(self.plan, STARTED, FINISHED)
        finally:
            assert snapshot(self.directory) == before

    def child_context(self, number=0):
        contexts = [item["payload"] for item in self.child if item["type"] == "turn_context"
                    and item["payload"]["turn_id"] in CHILD_TURNS]
        return contexts[number]

    def refuse(self):
        self.write()
        with pytest.raises(scorer.ScorerError):
            self.read()


def test_one_own_turn_fresh_child_before_settings_is_accepted(tmp_path):
    case = SessionCase(tmp_path)
    result = case.read()
    child = next(item for item in result["session_logs"] if item["id"] == CHILD_ID)
    assert child["owned_history_start_ordinal"] == 1
    assert child["owned_turn_ids"] == [CHILD_TURNS[0]]
    assert result["name"] == scorer.MODEL
    assert result["effort"] == scorer.EFFORT


def test_two_own_turn_fresh_child_keeps_pre_settings_and_later_turn(tmp_path):
    case = SessionCase(tmp_path, "fresh-two")
    result = case.read()
    child = next(item for item in result["session_logs"] if item["id"] == CHILD_ID)
    assert child["owned_history_start_ordinal"] == 1
    assert child["owned_turn_ids"] == sorted(CHILD_TURNS)


def test_forked_child_owns_only_post_marker_turns_with_or_without_optional_ordinal(tmp_path):
    for number, mode in enumerate(("all", None)):
        for optional in (True, False):
            case = SessionCase(tmp_path / f"case-{number}-{optional}", "forked", mode)
            if not optional:
                case.child[0]["payload"].pop("forked_from_id")
                case.child[0]["payload"].pop("subagent_history_start_ordinal")
            case.write()
            result = case.read()
            child = next(item for item in result["session_logs"] if item["id"] == CHILD_ID)
            assert child["owned_history_start_ordinal"] == 22
            assert child["owned_turn_ids"] == [CHILD_TURNS[0]]


def test_fresh_parent_turn_id_spoof_is_refused_in_both_observed_shapes(tmp_path):
    for shape in ("fresh-one", "fresh-two"):
        for change_task in (False, True):
            case = SessionCase(tmp_path / f"{shape}-{change_task}", shape)
            case.child_context()["turn_id"] = ROOT_TURN
            if change_task:
                started = case.child[1]["payload"]
                started["turn_id"] = ROOT_TURN
                started["turn_attribution"]["turn_id"] = ROOT_TURN
            case.refuse()


def test_context_without_its_preceding_task_is_refused(tmp_path):
    for shape in ("fresh-one", "fresh-two", "forked"):
        case = SessionCase(tmp_path / shape, shape, "all" if shape == "forked" else "none")
        case.child = [item for item in case.child if not (
            item["type"] == "event_msg" and item["payload"].get("type") == "task_started"
            and item["payload"].get("turn_id") == CHILD_TURNS[0])]
        # Removing an owned row after the fork marker leaves its ordinal intact.
        case.refuse()


def test_every_owned_context_keeps_model_effort_and_working_directory_checks(tmp_path):
    for shape, mode, own_turns in (("fresh-one", "none", 1), ("fresh-two", "none", 2), ("forked", "all", 1)):
        for number in range(own_turns):
            for field, value in (("model", "different-model"), ("effort", "low"), ("cwd", "/synthetic/outside")):
                case = SessionCase(tmp_path / f"{shape}-{number}-{field}", shape, mode)
                case.child_context(number)[field] = value
                case.refuse()


def test_fresh_and_forked_children_keep_settings_and_marker_guards(tmp_path):
    for shape, mode in (("fresh-one", "none"), ("fresh-two", "none"), ("forked", "all")):
        for change in ("missing", "thread", "model", "reasoning_effort", "cwd"):
            case = SessionCase(tmp_path / f"{shape}-{change}", shape, mode)
            marker = next(item for item in case.child
                          if item["payload"].get("type") == "thread_settings_applied")
            if change == "missing":
                marker["payload"]["type"] = "synthetic_unrecognized_settings"
            elif change == "thread":
                marker["payload"]["thread_id"] = "foreign-thread"
            else:
                marker["payload"]["thread_settings"][change] = "synthetic-wrong-value"
            case.refuse()


def test_child_without_retained_log_is_refused(tmp_path):
    case = SessionCase(tmp_path)
    case.child_path.unlink()
    with pytest.raises(scorer.ScorerError):
        case.read()


def test_missing_optional_metadata_alone_never_proves_freshness(tmp_path):
    for mode in ("all", None):
        for shape in ("fresh-one", "fresh-two"):
            case = SessionCase(tmp_path / f"{mode}-{shape}", shape, mode)
            assert "forked_from_id" not in case.child[0]["payload"]
            assert "subagent_history_start_ordinal" not in case.child[0]["payload"]
            case.refuse()


def test_explicit_fresh_spawn_cannot_disguise_inherited_metadata(tmp_path):
    for number, (field, value) in enumerate((("forked_from_id", ROOT_ID),
                                           ("subagent_history_start_ordinal", 22),
                                           ("subagent_history_start_ordinal", 1))):
        case = SessionCase(tmp_path / f"case-{number}")
        case.child[0]["payload"][field] = value
        case.refuse()


def test_forked_context_requires_full_parent_owned_payload_not_only_turn_id(tmp_path):
    for field, value in (("synthetic_context_binding", "changed only in copied payload"),
                         ("synthetic_boolean_binding", 1)):
        case = SessionCase(tmp_path / field, "forked", "all")
        inherited = next(item["payload"] for item in case.child if item["type"] == "turn_context"
                         and item["payload"]["turn_id"] == ROOT_TURN)
        inherited[field] = value
        case.refuse()


def test_forked_inherited_context_without_an_owned_child_turn_is_refused(tmp_path):
    case = SessionCase(tmp_path, "forked", "all")
    case.child[0]["payload"].pop("forked_from_id")
    case.child[0]["payload"].pop("subagent_history_start_ordinal")
    case.child = [item for item in case.child if item["payload"].get("turn_id") not in CHILD_TURNS]
    case.refuse()


def test_missing_or_cross_thread_spawn_correlation_is_refused(tmp_path):
    for variation in ("missing-call", "missing-output", "child-output", "wrong-parent"):
        case = SessionCase(tmp_path / variation)
        if variation == "missing-call":
            case.root = [item for item in case.root if item["payload"].get("type") != "function_call"]
        elif variation == "missing-output":
            case.root = [item for item in case.root if item["payload"].get("type") != "function_call_output"]
        elif variation == "child-output":
            output = case.root.pop()
            case.child.append(output)
        else:
            case.child[0]["payload"]["parent_thread_id"] = "unretained-parent"
            case.child[0]["payload"]["source"]["subagent"]["thread_spawn"]["parent_thread_id"] = "unretained-parent"
        case.refuse()


def test_fresh_owned_context_root_turn_and_timestamp_must_match(tmp_path):
    for variation in ("root-turn", "before-start", "after-finish"):
        case = SessionCase(tmp_path / variation)
        if variation == "root-turn":
            case.child_context()["root_turn_id"] = "different-root-turn"
        else:
            own_row = next(item for item in case.child if item["type"] == "turn_context")
            own_row["timestamp"] = "2025-12-31T23:59:59Z" if variation == "before-start" else "2026-01-01T00:01:01Z"
        case.refuse()
