#!/usr/bin/env python3
"""Registered support for a validator followed by its exact exit-status echo.

This leaves scoring prompts and original traces untouched. Only a completed,
successful own-file validator plus literal EXIT=0/exit=0 can be presented to
the frozen validator gate as the equivalent canonical command.
"""
from __future__ import annotations

import copy
from pathlib import Path
import sys

import reference_rescore_cborg as c

STATUS_NAMES = ("EXIT", "exit")
PERMISSION_RULES = tuple(f'Bash(echo "{name}=$?")' for name in STATUS_NAMES)


def status_command(r, command, rubric, directory):
    if not isinstance(command, str):
        return None
    for name in STATUS_NAMES:
        suffix = f'; echo "{name}=$?"'
        if command.endswith(suffix):
            canonical = command[:-len(suffix)]
            output = r.validator_output_path(canonical, rubric, directory)
            if output is not None:
                return canonical, output, name
    return None


def proven_status_calls(r, events, rubric):
    initializers = [e for e in events if e.get("type") == "system" and e.get("subtype") == "init"]
    terminals = [(i, e) for i, e in enumerate(events) if e.get("type") == "result"]
    if len(initializers) != 1 or len(terminals) != 1:
        return []
    directory = initializers[0].get("cwd")
    terminal_index, terminal = terminals[0]
    if (not isinstance(directory, str) or not Path(directory).is_absolute()
            or terminal.get("subtype") != "success" or terminal.get("is_error") is not False
            or not isinstance(terminal.get("permission_denials"), list)):
        return []
    denied = {x.get("tool_use_id") for x in terminal["permission_denials"] if isinstance(x, dict)}
    uses, results = {}, {}
    for index, event in enumerate(events):
        message = event.get("message")
        if not isinstance(message, dict) or not isinstance(message.get("content"), list):
            continue
        for block in message["content"]:
            if not isinstance(block, dict):
                continue
            if event.get("type") == "assistant" and block.get("type") == "tool_use":
                uses.setdefault(block.get("id"), []).append((index, block))
            if event.get("type") == "user" and block.get("type") == "tool_result":
                results.setdefault(block.get("tool_use_id"), []).append((index, block))
    proven = []
    for key, calls in uses.items():
        if not isinstance(key, str) or not key or key in denied or len(calls) != 1 or len(results.get(key, [])) != 1:
            continue
        use_index, use = calls[0]
        result_index, result = results[key][0]
        args = use.get("input")
        if (use.get("name") != "Bash" or not isinstance(args, dict)
                or args.get("dangerouslyDisableSandbox") or not use_index < result_index < terminal_index
                or result.get("is_error") is not False or not isinstance(result.get("content"), str)):
            continue
        parsed = status_command(r, args.get("command"), rubric, directory)
        if parsed is None:
            continue
        canonical, output, name = parsed
        lines = [line.strip() for line in result["content"].splitlines() if line.strip()]
        if f"VALID {output}: {rubric}" not in lines or not lines or lines[-1] != f"{name}=0":
            continue
        proven.append({"tool_use_id": key, "original_command": args["command"],
                       "canonical_command": canonical, "output": output, "exit_status": 0})
    return proven


def enable(r):
    validate_events = r.evaluator_validated
    validate_candidate = r.validate_candidate

    def validated(events, rubric):
        proofs = {p["tool_use_id"]: p for p in proven_status_calls(r, events, rubric)}
        if not proofs:
            return validate_events(events, rubric)
        normalized = copy.deepcopy(events)
        for event in normalized:
            message = event.get("message")
            if event.get("type") != "assistant" or not isinstance(message, dict) or not isinstance(message.get("content"), list):
                continue
            for block in message["content"]:
                if isinstance(block, dict) and block.get("type") == "tool_use" and block.get("id") in proofs:
                    block["input"]["command"] = proofs[block["id"]]["canonical_command"]
        return validate_events(normalized, rubric)

    def candidate(path, job, manifest, events):
        evidence = validate_candidate(path, job, manifest, events)
        evidence["validator_exit_status_evidence"] = proven_status_calls(r, events, job["rubric"])
        return evidence

    r.evaluator_validated = validated
    r.validate_candidate = candidate


def route_args(args):
    if args[:1] != ["--print"] or args.count("--allowedTools") != 1:
        raise ValueError("the registered evaluator argv is required")
    index = args.index("--allowedTools") + 1
    return [*args[:index], *PERMISSION_RULES, *args[index:]]


if __name__ == "__main__":
    c.route_evaluator(route_args(sys.argv[1:]))
