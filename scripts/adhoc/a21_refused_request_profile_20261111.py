#!/usr/bin/env python3
"""Purpose: describe, read-only, the BC1 typed-audit request that the model
route answered with `stop_reason: refusal` in the A21 run of 2026-11-12
(label 2026-11-11a_claude-opus-5-api-bc1-a21_rep1), next to the requests the
same run had accepted minutes earlier. It establishes what the refused
request contained that the accepted ones did not. It does not establish why
the provider refused: the response carries no reason.

For each request it prints: bytes, sha256, the system text's length, and for
each text block its length, sha256 prefix, first line, and the kinds of JSON
keys or section headings it holds. It then says which blocks of the refused
request also occur, byte for byte, inside an accepted request.

Inputs: the run's `intermediate/` directory (argument 1). Reads only.
Outputs: stdout.
Serves: owner decision D133; the A21 outcome record. Date: 2026-11-11.
"""
import hashlib
import json
import re
import sys
from pathlib import Path


def blocks(req: dict) -> list[str]:
    out = []
    for message in req.get("messages", []):
        content = message.get("content")
        if isinstance(content, str):
            out.append(content)
        else:
            out.extend(b.get("text", "") for b in content if isinstance(b, dict))
    return out


def describe(text: str) -> str:
    first = text.strip().splitlines()[0][:110] if text.strip() else "(empty)"
    kind = "text"
    stripped = text.lstrip()
    if stripped[:1] in "{[":
        try:
            value = json.loads(text)
            if isinstance(value, dict):
                kind = "JSON object, keys: " + ", ".join(list(value)[:14])
            else:
                kind = f"JSON array of {len(value)}"
        except ValueError:
            kind = "JSON-like, not parseable alone"
    else:
        heads = re.findall(r"^#{1,3} .+$", text, flags=re.M)
        if heads:
            kind = f"prose, {len(heads)} headings, e.g. " + " | ".join(h[:50] for h in heads[:4])
    return f"first line: {first!r}; {kind}"


def load(path: Path):
    raw = path.read_bytes()
    return raw, json.loads(raw)


def main() -> int:
    inter = Path(sys.argv[1])
    refused_path = inter / "CHORUS_bc1_audit_0_request.json"
    accepted_paths = [inter / "CHORUS_receipt_completion_request.json"]
    raw, refused = load(refused_path)
    print(f"REFUSED  {refused_path.name}: {len(raw)} bytes, sha256 {hashlib.sha256(raw).hexdigest()}")
    print(f"  model {refused.get('model')}, max_tokens {refused.get('max_tokens')}, thinking {refused.get('thinking')}, "
          f"tools {'yes' if refused.get('tools') else 'no'}, system {len(refused.get('system') or '')} chars")
    refused_blocks = blocks(refused)
    accepted_text = ""
    for path in accepted_paths:
        if not path.exists():
            print(f"ACCEPTED {path.name}: not present")
            continue
        araw, areq = load(path)
        ablocks = blocks(areq)
        system = areq.get("system")
        system_text = system if isinstance(system, str) else json.dumps(system)
        accepted_text += system_text + "\n".join(ablocks)
        print(f"ACCEPTED {path.name}: {len(araw)} bytes, {len(areq.get('messages', []))} messages, "
              f"{len(ablocks)} text blocks, system {len(system_text)} chars")
    # The `full` request is not saved as one file; its transcript is.
    transcript = inter / "CHORUS_receipt_completion_transcript.json"
    if transcript.exists():
        accepted_text += transcript.read_text()
        print(f"ACCEPTED {transcript.name}: {transcript.stat().st_size} bytes (the full phase's exchange, as carried into receipt completion)")
    inputs = inter / "CHORUS_receipt_completion_inputs.json"
    if inputs.exists():
        accepted_text += inputs.read_text()
        print(f"ACCEPTED {inputs.name}: {inputs.stat().st_size} bytes (inputs recorded for receipt completion)")
    print()
    total = sum(len(b) for b in refused_blocks)
    for i, text in enumerate(refused_blocks):
        digest = hashlib.sha256(text.encode()).hexdigest()[:12]
        whole = text in accepted_text
        # JSON-escaped occurrence inside a saved transcript counts as well.
        escaped = json.dumps(text)[1:-1] in accepted_text
        print(f"block {i}: {len(text)} chars ({100 * len(text) / total:.1f}% of the message), sha256 {digest}")
        print(f"  {describe(text)}")
        print(f"  occurs whole in an accepted request of this run: {'yes' if whole or escaped else 'no'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
