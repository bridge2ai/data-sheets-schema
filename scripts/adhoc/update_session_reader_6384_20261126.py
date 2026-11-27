"""Apply the reviewed ownership-reader revision for issue 6384, 2026-11-26.

Input: the exact measured scorer bytes in this isolated checkout.
Output: revised scorer source only. No run, input, model, or publication access.
The runner hash distinguishes this acceptance revision; semantic inputs stay fixed.
"""
import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TARGET = ROOT / "scripts/adhoc/score_semantic_rubric_codex_20261125.py"
MEASURED = "b2a5c0995d891d4c5179509834b460390b1d921d78b0191965fc4ea3f91c21b9"


def replace_once(source, old, new):
    if source.count(old) != 1:
        raise ValueError("source transformation anchor is absent or nonunique")
    return source.replace(old, new, 1)


def main():
    raw = TARGET.read_bytes()
    if hashlib.sha256(raw).hexdigest() != MEASURED:
        raise ValueError("source is not the unchanged measured reader")
    source = raw.decode()
    source = replace_once(source, 'def owned_turns(rows, ident, child, working_directory):', '''def child_spawn_mode(ident, parent, agent_paths, calls, call_outputs):
    """Use a correlated call owned by the retained parent, never metadata absence."""
    modes = []
    for call_id, (name, arguments, owner) in calls.items():
        if name != "spawn_agent" or owner != parent:
            continue
        require(call_id in call_outputs, "owned tool calls and outputs do not correlate both ways")
        value, output_owner = call_outputs[call_id]
        require(output_owner == owner, "tool call and output belong to different sessions")
        outcome = parse_json(value)
        require(isinstance(outcome, dict), "unrecognized spawn result")
        target = outcome.get("task_name")
        require(isinstance(target, str), "spawn result lacks child identity")
        matching = [key for key, path in agent_paths.items() if key == target or path == target]
        require(len(matching) == 1, "spawned child has no unique session log")
        if matching[0] == ident:
            mode = arguments.get("fork_turns", "all")
            require(isinstance(mode, str) and mode in ("all", "none"), "unknown correlated spawn mode")
            modes.append(mode)
    require(len(modes) == 1, "child lacks one correlated parent-owned spawn")
    return modes[0]


def owned_turns(rows, ident, child, working_directory, *, spawn_mode=None):''')
    source = replace_once(source, '''    Real v2 child logs resume their own history at thread_settings_applied for
    the child's UUID. The optional metadata ordinal points at that exact row;
    inherited parent metadata is not an ownership switch.
''', '''    Explicit fresh spawns own their task/context pairs from the start of the
    log, even when settings follow their first context. Forked/default spawns
    retain the settings boundary, corroborated by optional child metadata.
    This reader revision is identified by the plan/output runner_sha256 (6384).
''')
    source = replace_once(source, '''        start = markers[0]
        ordinal = rows[0]["payload"].get("subagent_history_start_ordinal")
        if ordinal is not None:
            require(type(ordinal) is int and ordinal == start,
                    "child history ordinal does not match its thread marker")
''', '''        require(spawn_mode in ("all", "none"), "child lacks a correlated spawn mode")
        meta = rows[0]["payload"]
        ordinal = meta.get("subagent_history_start_ordinal")
        forked_from = meta.get("forked_from_id")
        if spawn_mode == "none":
            require(forked_from is None and ordinal is None,
                    "fresh spawn contradicts child fork metadata")
        else:
            start = markers[0]
            if forked_from is not None:
                require(forked_from == meta.get("parent_thread_id"),
                        "forked child metadata names another parent")
            if ordinal is not None:
                require(type(ordinal) is int and ordinal == start,
                        "child history ordinal does not match its thread marker")
''')
    source = replace_once(source, '''    inherited_outputs = []
    for path in logs:
''', '''    inherited_outputs = []
    parsed = {}
    for path in logs:
''')
    graph = '''    require(threads[0] in sessions, "root thread lacks its matching session log")
    ancestors = {}
    for ident in sessions:
        seen = set()
        current = ident
        while current != threads[0]:
            require(current in sessions and current not in seen, "foreign or cyclic child ancestry")
            seen.add(current)
            current = sessions[current]
        ancestors[ident] = (seen | {threads[0]}) - {ident}
'''
    source = replace_once(source, graph, '')
    source = replace_once(source, '''        own_start, qualified_contexts = owned_turns(rows, ident, parent is not None, plan["working_directory"])
''', '''        parsed[ident] = (path, raw, rows, meta)
''' + graph + '''    # Process parents before children; copied calls cannot establish a child's
    # spawn mode. Each binding comes from an already qualified owned segment.
    for ident in sorted(sessions, key=lambda key: (len(ancestors[key]), key)):
        path, raw, rows, meta = parsed[ident]
        parent = sessions[ident]
        mode = child_spawn_mode(ident, parent, agent_paths, calls, call_outputs) if parent else None
        own_start, qualified_contexts = owned_turns(
            rows, ident, parent is not None, plan["working_directory"], spawn_mode=mode)
''')
    source = replace_once(source, '''    for inheritor, context in inherited_contexts:
        require(turn_owners.get(context.get("turn_id")) in ancestors[inheritor],
                "inherited context lacks retained ancestor-owned turn evidence")
''', '''    for inheritor, context in inherited_contexts:
        owner = turn_owners.get(context.get("turn_id"))
        require(owner in ancestors[inheritor],
                "inherited context lacks retained ancestor-owned turn evidence")
        require(any(json.dumps(context, sort_keys=True) == json.dumps(payload, sort_keys=True)
                    for payload in owned_contexts[owner]),
                "inherited context differs from retained ancestor-owned payload")
        parent_rows = parsed[sessions[inheritor]][2]
        require(any(row.get("type") == "turn_context"
                    and json.dumps(row["payload"], sort_keys=True) == json.dumps(context, sort_keys=True)
                    for row in parent_rows), "inherited context differs from retained parent payload")
''')
    TARGET.write_text(source)
    if TARGET.read_text() != source:
        raise ValueError("saved source differs")
    print(hashlib.sha256(source.encode()).hexdigest())


if __name__ == "__main__":
    main()
