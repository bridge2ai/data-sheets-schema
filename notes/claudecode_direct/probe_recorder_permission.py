"""Observe the runtime's permission decision on the prescribed recorder line (#2282).

The first direct-arm canary was refused `provenance record` under dontAsk,
and the denial event names only the mode. This probe runs the pinned Claude
Code binary against a scripted local provider (no provider key, no model
call, synthetic responses) and issues the recorder line three ways, so the
cause is observed rather than inferred:

- `expansion`: exactly as renderers 9 to 23 render it, ending
  `--prompt-text "${D4D_LAUNCH_INSTRUCTION:?...}"`;
- `literal_path`: the same line with the variable's value written out;
- `env_flag`: the same line ending `--prompt-text-env D4D_LAUNCH_INSTRUCTION`.

Stub CLI modules print a marker, so an admitted line changes nothing. The
three lines share every other byte, including the single-quoted render
specification, so a difference in decision is the ending's; the default run
adds a bisection of the fixture's line.

`--instruction PATH` takes the recorder line from a real rendered
instruction instead, in either ending, and isolates single characters of its
specification (`#`, parentheses, apostrophes). The CLI stub reports whether
`D4D_LAUNCH_INSTRUCTION` reached it; a refusal counts only when the runtime
made it (reason `mode`), and a run passes only if some case was admitted.
Observed on 2026-09-23 (`recorder_permission_probe_2026-09-23.json`): on the
first direct canary's registered line only the expansion is refused; the
same specification re-rendered with `prompt_text_env` is admitted as written
and the stub it launches sees the variable; the fixture's line, whose manifest path
appears twice in its specification, is refused in every ending until the
specification's apostrophes are removed, while one apostrophe in a small
specification is admitted.

Since #2369 the controller refuses, before execution, a prescribed call the
runtime's rules would not admit as written, so an expansion would never reach
the runtime's matcher. The child's controller therefore runs without that
check, and every case records both the runtime's decision and the checked
controller's prediction (`controller_admits`). A case the runtime refused
that the checked controller would have admitted is an under-refusal: under a
launch it would disqualify the run. With `--instruction` the probe fails on
any; on the fixture's own line they are reported, since its apostrophes are
the uncharacterised refusal of #2308.
"""
import argparse
import json
import os
from pathlib import Path
import shlex
import sys
from types import SimpleNamespace

import httpx

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CONTROLS = ROOT / "notes" / "matched_cborg_2026-09-13"
sys.path[:0] = [str(ROOT / "src"), str(CONTROLS), str(CONTROLS / "native_controls")]

from budgeted_cborg import Ledger                                        # noqa: E402
from native_proxy import NativeProxy                                     # noqa: E402
from run_native_canary import execute_child, verified_executable, sha, _classify_command  # noqa: E402
from native_command_policy import command_guidance, permission_arguments  # noqa: E402
import probe_native_permissions as native_probe                          # noqa: E402

ENV_FLAG = "--prompt-text-env D4D_LAUNCH_INSTRUCTION"
EXPANSION = ' --prompt-text "${D4D_LAUNCH_INSTRUCTION:?Set D4D_LAUNCH_INSTRUCTION to the exact saved launch instruction}"'


def split_ending(line):
    """The line without its launch-instruction ending, in either rendered form (#2310)."""
    if line.endswith(" " + ENV_FLAG):
        return line[: -len(" " + ENV_FLAG)]
    head, sep, _ = line.rpartition(' --prompt-text "${D4D_LAUNCH_INSTRUCTION:?')
    if not sep:
        raise RuntimeError("the rendered recorder line ends in neither launch-instruction form")
    return head


def recorder_cases(instruction_text, instruction_path):
    """The rendered recorder line and its two variants."""
    line = next(l.strip() for l in instruction_text.splitlines()
                if " -m data_sheets_schema.cli provenance record" in l and "--prompt-text" in l)
    head = split_ending(line)
    line = head + EXPANSION
    stem, sep2, payload = head.rpartition(" --render-spec-json ")
    if not sep2:
        raise RuntimeError("the rendered recorder line carries no render specification")
    prefix = line.split(" provenance record", 1)[0] + " provenance record"
    literal = " --prompt-text " + shlex.quote(str(instruction_path))
    inner = payload[1:-1]                      # the JSON between the single quotes
    return [{"id": "expansion", "command": line},
            {"id": "literal_path", "command": head + literal},
            {"id": "env_flag", "command": head + " " + ENV_FLAG},
            # bisection: which part of the line the matcher refuses
            {"id": "bare", "command": prefix + " --project EXTERNAL"},
            {"id": "stem_only", "command": stem},
            {"id": "stem_literal", "command": stem + literal},
            {"id": "stem_trivial_spec", "command": stem + " --render-spec-json '{}'" + literal},
            {"id": "stem_small_spec", "command": stem + " --render-spec-json '{\"condition\":\"generic_v9\"}'" + literal},
            {"id": "stem_half_payload", "command": stem + " --render-spec-json " + shlex.quote(inner[: len(inner) // 2]) + literal}]


def isolation_cases(line, instruction_path):
    """Cases on one real rendered recorder line that isolate single characters in its payload."""
    head = split_ending(line)
    stem, _, payload = head.rpartition(" --render-spec-json ")
    prefix = line.split(" provenance record", 1)[0] + " provenance record"
    spec = json.loads(shlex.split(payload)[0])
    literal = " --prompt-text " + shlex.quote(str(instruction_path))

    def with_spec(value, suffix=" " + ENV_FLAG):
        return stem + " --render-spec-json " + shlex.quote(json.dumps(value, sort_keys=True, separators=(",", ":"))) + suffix

    no_hash = {k: (v.replace("#", "") if isinstance(v, str) else v) for k, v in spec.items()}
    no_parens = {k: (v.replace("(", "").replace(")", "") if isinstance(v, str) else v) for k, v in spec.items()}
    neither = {k: (v.replace("#", "").replace("(", "").replace(")", "") if isinstance(v, str) else v) for k, v in spec.items()}
    return [{"id": "real_as_given", "command": line},
            {"id": "real_expansion", "command": head + EXPANSION},
            {"id": "real_literal_path", "command": head + literal},
            {"id": "real_env_flag", "command": head + " " + ENV_FLAG},
            {"id": "real_env_flag_no_hash", "command": with_spec(no_hash)},
            {"id": "real_env_flag_no_parens", "command": with_spec(no_parens)},
            {"id": "real_env_flag_neither", "command": with_spec(neither)},
            {"id": "tiny_hash_after_space", "command": prefix + " --render-spec-json '{\"a\":\"# x\"}'"},
            {"id": "tiny_hash_no_space", "command": prefix + " --render-spec-json '{\"a\":\"x#y\"}'"},
            {"id": "tiny_parens", "command": prefix + " --render-spec-json '{\"a\":\"x (y)\"}'"},
            {"id": "tiny_apostrophe", "command": prefix + " --render-spec-json " + shlex.quote('{"a":"child\'s manifest"}')},
            {"id": "real_env_flag_no_apostrophe", "command": with_spec(
                {k: (v.replace("'", "") if isinstance(v, str) else v) for k, v in spec.items()})},
            # The same specification joined to its option (`--opt='{…}'`): one
            # argument of two pieces, which the runtime reads as brace
            # expansion (#2308); the checked controller refuses it too.
            {"id": "real_env_flag_equals_form", "command": stem + " --render-spec-json=" + shlex.quote(
                json.dumps(spec, sort_keys=True, separators=(",", ":"))) + " " + ENV_FLAG}]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--claude-executable", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="a fresh directory for the probe's files")
    parser.add_argument("--instruction", type=Path, default=None,
                        help="a rendered instruction whose recorder line is isolated character by character")
    args = parser.parse_args()
    root = args.output.resolve()
    root.mkdir(parents=True, exist_ok=False)
    work = root / "work"
    work.mkdir()
    job, policy = native_probe.fixture(work)
    # The runtime's own matcher is what this probe observes (#2369).
    runtime_policy = {k: v for k, v in policy.items() if k != "literal_admission"}
    instruction = Path(job["instruction"])
    cases = recorder_cases(instruction.read_text(encoding="utf-8"), instruction)
    if args.instruction is not None:
        real = next(l.strip() for l in args.instruction.read_text(encoding="utf-8").splitlines()
                    if " -m data_sheets_schema.cli provenance record" in l and "--prompt-text" in l)
        if shlex.split(real)[0] != policy["python"]:
            # The allow rules name this interpreter; a line naming another
            # would be refused by the controller, never reaching the
            # runtime's matcher, and would observe nothing (#2309).
            raise SystemExit(f"the instruction's interpreter is not this probe's ({policy['python']}); "
                             "run the probe with the interpreter the instruction names")
        cases = isolation_cases(real, instruction)
    # The CLI stub reports whether the variable reached the child.
    (work / "data_sheets_schema" / "cli.py").write_text(
        'import os\nprint("CLI_STUB_OK", "LAUNCH_VARIABLE_SET" if os.environ.get("D4D_LAUNCH_INSTRUCTION") else "LAUNCH_VARIABLE_UNSET")\n')
    (root / "cases.json").write_text(json.dumps(cases, indent=2) + "\n")
    (root / "policy.json").write_text(json.dumps(policy, indent=2) + "\n")
    (root / "runtime_policy.json").write_text(json.dumps(runtime_policy, indent=2) + "\n")
    cli = str(args.claude_executable.resolve(strict=True))
    pin = {"claude_executable": cli, "pinned_files": {cli: sha(cli)}}
    calls = []

    def respond(request):
        body = json.loads(request.content)
        calls.append(body)
        n = sum(bool(call.get("tools")) for call in calls)
        if body.get("tools") and n <= len(cases):
            case = cases[n - 1]
            block = {"type": "tool_use", "id": case["id"], "name": "Bash",
                     "input": {"command": case["command"], "description": "Synthetic recorder permission case"}}
        else:
            block = {"type": "text", "text": "OFFLINE_COMPLETE" if body.get("tools") else "Offline probe"}
        tool = block["type"] == "tool_use"
        start = {**block, "input" if tool else "text": {} if tool else ""}
        delta = ({"type": "input_json_delta", "partial_json": json.dumps(block["input"])} if tool
                 else {"type": "text_delta", "text": block["text"]})
        events = [
            {"type": "message_start", "message": {"id": f"offline_{len(calls)}", "type": "message", "role": "assistant",
                                                  "model": body["model"], "content": [], "stop_reason": None,
                                                  "stop_sequence": None, "usage": {"input_tokens": 100, "output_tokens": 0}}},
            {"type": "content_block_start", "index": 0, "content_block": start},
            {"type": "content_block_delta", "index": 0, "delta": delta},
            {"type": "content_block_stop", "index": 0},
            {"type": "message_delta", "delta": {"stop_reason": "tool_use" if tool else "end_turn", "stop_sequence": None},
             "usage": {"output_tokens": 12}},
            {"type": "message_stop"}]
        raw = "".join(f"event: {e['type']}\ndata: {json.dumps(e)}\n\n" for e in events).encode()
        return httpx.Response(200, content=raw, headers={"content-type": "text/event-stream"})

    sdk = SimpleNamespace(messages=SimpleNamespace(count_tokens=lambda **kw: SimpleNamespace(input_tokens=100)))
    ledger = Ledger(root / "ledger.json", manifest_sha256="offline-recorder-permission-only")
    proxy = NativeProxy(sdk=sdk, ledger=ledger, attempt="offline", evidence=root / "requests", model="claude-opus-5",
                        prices={"input": .000005, "output": .000025, "cache_read": .0000005, "cache_write": .00000625},
                        verify=lambda: None, provider_key="offline-synthetic-key", base_url="https://api.cborg.lbl.gov",
                        upstream=httpx.Client(transport=httpx.MockTransport(respond)))
    env = {k: v for k, v in os.environ.items() if k in {"PATH", "HOME", "SHELL", "TMPDIR", "LANG", "LC_ALL", "TERM"}}
    config = root / "config"
    config.mkdir()
    env.update(CLAUDE_CONFIG_DIR=str(config), CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC="1", DISABLE_TELEMETRY="1",
               CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS="1", ANTHROPIC_API_KEY=proxy.token, PYTHONPATH=str(work),
               D4D_LAUNCH_INSTRUCTION=str(instruction))
    prompt = root / "probe_instruction.txt"
    prompt.write_text("Perform the synthetic offline recorder permission probe.\n")
    argv = [cli, "--print", "--safe-mode", "--restricted", "--strict-mcp-config", "--no-session-persistence",
            "--model", "claude-opus-5", "--name", "d4d-offline-recorder-permission", "--disable-slash-commands",
            "--max-budget-usd", "5", "--prompt-suggestions", "false", "--output-format", "stream-json", "--verbose",
            "--permission-mode", "dontAsk", "--tools", "Read,Write,Bash", *permission_arguments(runtime_policy),
            "--system-prompt", "Synthetic offline capability probe. Do not access other files or networks."
            + command_guidance(policy)]
    with proxy.running() as url:
        env["ANTHROPIC_BASE_URL"] = url
        code = execute_child(argv, proxy=proxy, instruction=prompt, attempt=root, cwd=work, env=env,
                             deadline_seconds=120, verify_launch=lambda: verified_executable(pin),
                             command_policy=runtime_policy)
    events = [json.loads(line) for line in (root / "transcript.jsonl").read_text(encoding="utf-8").splitlines()
              if line.strip()]
    terminals = [e for e in events if e.get("type") == "result"]
    denied = {d["tool_use_id"] for d in (terminals[0].get("permission_denials", []) if terminals else [])}
    results = {c["tool_use_id"]: c for e in events if isinstance(e.get("message"), dict)
               for c in e["message"].get("content", []) if isinstance(c, dict) and c.get("type") == "tool_result"}
    reasons = {e.get("tool_use_id"): e.get("decision_reason_type") for e in events
               if e.get("type") == "system" and e.get("subtype") == "permission_denied"}

    def text(result):
        content = result.get("content")
        return content if isinstance(content, str) else json.dumps(content)

    observed = [{"id": c["id"], "denied": c["id"] in denied, "denial_reason": reasons.get(c["id"]),
                 "ran_cli_stub": c["id"] in results and "CLI_STUB_OK" in text(results[c["id"]]),
                 "child_saw_variable": c["id"] in results and "LAUNCH_VARIABLE_SET" in text(results[c["id"]]),
                 "result_head": (text(results[c["id"]])[:160] if c["id"] in results else None),
                 "controller_admits": _classify_command(c["command"], policy["python"], set(), policy)[0] == "prescribed"}
                for c in cases]
    under = [o["id"] for o in observed if o["denied"] and o["denial_reason"] == "mode" and o["controller_admits"]]
    over = [o["id"] for o in observed if not o["denied"] and not o["controller_admits"]]
    # A refusal counts only when the runtime's own matcher made it (reason
    # `mode`); an admitted case counts only when the child ran and saw the
    # variable. Anything else observed nothing.
    summary = {"exit_code": code, "terminal_results": len(terminals), "cases": observed,
               # At least one case must be admitted, so a run that refused
               # everything (another interpreter, a broken rule) observed nothing.
               "passed": len(terminals) == 1 and any(not o["denied"] for o in observed) and all(
                   (o["denied"] and o["denial_reason"] == "mode" and not o["ran_cli_stub"])
                   or (not o["denied"] and o["ran_cli_stub"] and o["child_saw_variable"]) for o in observed)
                   and (args.instruction is None or not under),
               # Runtime refusals the checked controller would have let
               # through (disqualifying under a launch), and runtime
               # admissions it refuses first (one retry, never disqualifying).
               "under_refusals": under, "over_refusals": over,
               "instruction_sha256": sha(args.instruction) if args.instruction is not None else None,
               "allow_rules": [r for r in policy.get("allowed_tools", []) if "provenance record" in r],
               "scripted_requests": len(calls), "real_provider_requests": 0, "runtime_sha256": sha(cli),
               "cases_sha256": sha(root / "cases.json"), "transcript_sha256": sha(root / "transcript.jsonl")}
    (root / "result.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
