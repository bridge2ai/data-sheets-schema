"""Check explicit evidence, not semantic entailment (#1801/#1815/#1816).

Version 1 binds quotations to an artifact/path or document/chunk and checks
removal of relationships an audit explicitly rejected. It does not discover
unreported claims or certify semantic conclusions. All inputs are read only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
from typing import Any

import yaml

INSTRUMENT = "evidence_assertions v1 (#1801, #1815, #1816)"
ARTIFACTS = {"original_full", "original_core", "final_full", "final_core"}
MISSING = object()


def load_json(raw: str | bytes):
    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError(f"duplicate evidence JSON key: {key}")
            value[key] = item
        return value
    return json.loads(raw, object_pairs_hook=unique)


def load_record(raw: str) -> dict:
    from data_sheets_schema.duplicate_keys import find_duplicate_keys
    if find_duplicate_keys(raw):
        raise ValueError("artifact has duplicate YAML mapping keys; its location is ambiguous")
    value = yaml.safe_load(raw)
    if not isinstance(value, dict):
        raise ValueError("artifact must be a YAML mapping")
    return value


def _tokens(pointer: str) -> list[str]:
    if not isinstance(pointer, str) or not pointer.startswith("/"):
        raise ValueError("location must be a non-root JSON Pointer, or @header")
    if re.search(r"~(?![01])", pointer):
        raise ValueError("invalid JSON Pointer escape")
    return [part.replace("~1", "/").replace("~0", "~")
            for part in pointer[1:].split("/")]


def _at(value: Any, tokens: list[str]) -> Any:
    for token in tokens:
        if isinstance(value, dict):
            value = value.get(token, MISSING)
        elif isinstance(value, list) and re.fullmatch(r"0|[1-9][0-9]*", token):
            index = int(token)
            value = value[index] if index < len(value) else MISSING
        else:
            return MISSING
    return value


def _fold(text: str) -> str:
    # Fold line wrapping only. Keep punctuation, case and modal verbs.
    return " ".join(text.split())


def _literal(value: Any, quote: str, seen: set[int] | None = None) -> bool:
    if isinstance(value, str):
        return _fold(quote) in _fold(value)
    if value is None or isinstance(value, (bool, int, float)):
        # A scalar is one value: 2 is not evidence of a value of 12.
        return quote.strip() == json.dumps(value, allow_nan=False)
    seen = set() if seen is None else seen
    if id(value) in seen:
        return False
    seen.add(id(value))
    if isinstance(value, dict):
        return any(_literal(v, quote, seen) for v in value.values())
    if isinstance(value, list):
        return any(_literal(v, quote, seen) for v in value)
    return False


def _header(raw: str) -> str:
    lines = []
    for line in raw.splitlines():
        if line.strip() and not line.lstrip().startswith("#"):
            break
        lines.append(line)
    return "\n".join(lines)


def _problem(kind: str, detail: str, **fields) -> dict:
    return {"kind": kind, "detail": detail, **fields}


def check_assertions(claims, *, artifacts: dict[str, str],
                     chunks: dict[str, dict[str, str]]) -> list[dict]:
    """Check declared assertions against caller-selected inputs."""
    if not isinstance(claims, list):
        return [_problem("evidence_contract", "claims must be an array")]
    findings, parsed = [], {}
    for index, claim in enumerate(claims):
        try:
            if not isinstance(claim, dict):
                raise ValueError("each assertion must be an object")
            if "source" in claim:
                if set(claim) != {"source", "chunk", "quote"}:
                    raise ValueError("source assertion needs exactly source, chunk and quote")
                chunk = chunks.get(claim["chunk"])
                if chunk is None or chunk["source"] != claim["source"]:
                    raise ValueError("the named document does not own the named chunk")
                if claim["source"] == "<preamble>":
                    raise ValueError("the bundle preamble is not a source document")
                quote = claim["quote"]
                if not isinstance(quote, str) or not quote.strip():
                    raise ValueError("quote must be nonempty text")
                if _fold(quote) not in _fold(chunk["text"]):
                    findings.append(_problem("source_quote_not_found",
                        "quote is absent from the named document's named chunk",
                        assertion=index, source=claim["source"], chunk=claim["chunk"]))
                continue
            if set(claim) != {"artifact", "path", "op", "quote"}:
                raise ValueError("artifact assertion needs exactly artifact, path, op and quote")
            name, path, op, quote = (claim[k] for k in ("artifact", "path", "op", "quote"))
            if name not in ARTIFACTS or name not in artifacts:
                raise ValueError("the named artifact was not supplied")
            if op not in {"contains", "lacks"} or not isinstance(quote, str) or not quote.strip():
                raise ValueError("op must be contains or lacks, with a nonempty quote")
            if path == "@header":
                value = _header(artifacts[name])
            else:
                if name not in parsed:
                    parsed[name] = load_record(artifacts[name])
                value = _at(parsed[name], _tokens(path))
                if value is MISSING:
                    raise ValueError("artifact path does not exist; absence of a field is not a lost qualifier")
            found = _literal(value, quote)
            if found != (op == "contains"):
                findings.append(_problem("artifact_assertion_contradicted",
                    f"quoted text is {'present' if found else 'absent'} at this exact artifact location",
                    assertion=index, artifact=name, path=path, op=op, quote=quote))
        except (ValueError, TypeError, KeyError, yaml.YAMLError) as exc:
            findings.append(_problem("evidence_contract", str(exc), assertion=index))
    return findings


def check_audit(audit, *, artifacts: dict[str, str], chunks: dict) -> dict:
    """Require evidence for each finding before using its recommendation."""
    problems, count = [], 0
    if not isinstance(audit, dict) or not isinstance(audit.get("findings"), list):
        problems.append(_problem("evidence_contract", "audit.findings must be an array"))
    else:
        for index, finding in enumerate(audit["findings"]):
            if not isinstance(finding, dict):
                problems.append(_problem("evidence_contract", "audit finding must be an object", finding=index))
                continue
            claims = finding.get("evidence")
            if not isinstance(claims, list) or not claims:
                problems.append(_problem("evidence_contract", "every audit finding needs a nonempty evidence array", finding=index))
                continue
            count += len(claims)
            problems += [{**f, "finding": index} for f in
                         check_assertions(claims, artifacts=artifacts, chunks=chunks)]
    return {"instrument": INSTRUMENT, "checked": True,
            "assertions_checked": count, "findings": problems}


def check_relationship_removals(audit, original: dict, final: dict) -> list[dict]:
    """Check declared removal without treating list positions as identity.

    For a list member, identity is a pointer relative to that member, ending
    in id or name. The same identity anywhere in the same final container
    is retained. A non-list relationship must be absent altogether.
    This checks the declared action, not the audit's semantic judgment.
    """
    findings = []
    for index, finding in enumerate(audit.get("findings", [])):
        if not isinstance(finding, dict) or "remove_relationship" not in finding:
            continue
        rule = finding["remove_relationship"]
        try:
            if not isinstance(rule, dict) or set(rule) - {"path", "identity"}:
                raise ValueError("remove_relationship needs path and, for a list member, identity")
            tokens = _tokens(rule["path"])
            old = _at(original, tokens)
            if old is MISSING:
                raise ValueError("unsupported relationship does not exist in the original")
            parent = _at(original, tokens[:-1])
            if isinstance(parent, list):
                identity_tokens = _tokens(rule.get("identity"))
                if identity_tokens[-1] not in {"id", "name"}:
                    raise ValueError("list identity must end in id or name")
                identity = _at(old, identity_tokens)
                if not isinstance(identity, str) or not identity.strip():
                    raise ValueError("original list member has no usable declared identity")
                remaining = _at(final, tokens[:-1])
                if remaining is MISSING:
                    retained = False
                elif not isinstance(remaining, list):
                    raise ValueError("final relationship container changed shape")
                else:
                    retained = any(_at(item, identity_tokens) == identity for item in remaining)
            else:
                if "identity" in rule:
                    raise ValueError("identity is only valid for an indexed list member")
                retained = _at(final, tokens) is not MISSING
            if retained:
                findings.append(_problem("unsupported_relationship_retained",
                    "the audit rejected this relationship, but the final record still asserts it; a disclaimer does not remove it",
                    finding=index, path=rule["path"]))
        except (ValueError, TypeError, KeyError) as exc:
            findings.append(_problem("evidence_contract", str(exc), finding=index))
    return findings


def report_assertions(text: str) -> list:
    """Read one JSON appendix; never infer coverage of free prose."""
    headings = list(re.finditer(r"(?m)^## Evidence assertions[ \t]*$", text))
    if len(headings) != 1:
        raise ValueError("report requires exactly one ## Evidence assertions appendix")
    section = re.split(r"(?m)^## ", text[headings[0].end():], maxsplit=1)[0]
    fence = chr(96) * 3
    match = re.fullmatch(r"\s*" + fence + r"json\s*\n([\s\S]*?)\n" + fence + r"\s*", section)
    if not match:
        raise ValueError("evidence appendix must contain exactly one JSON code block")
    value = load_json(match.group(1))
    if not isinstance(value, dict) or set(value) != {"claims"} or not isinstance(value["claims"], list):
        raise ValueError("evidence appendix must be an object with a claims array")
    return value["claims"]


def source_chunks(bundle: Path, manifest: Path) -> tuple[dict, dict]:
    from data_sheets_schema import chunking
    raw, manifest_raw = bundle.read_bytes(), manifest.read_bytes()
    from data_sheets_schema.duplicate_keys import find_duplicate_keys
    if find_duplicate_keys(manifest_raw.decode("utf-8")):
        raise ValueError("chunk manifest has duplicate YAML mapping keys")
    mapping = yaml.safe_load(manifest_raw)
    chunking.validate_manifest_mapping(mapping, raw, mapping["bundle"])
    chunks = {c["id"]: {"source": c["source"], "text": part}
              for c, part in zip(mapping["chunks"], chunking.chunk_texts(raw.decode("utf-8"), mapping["chunks"]))}
    return chunks, {"bundle": hashlib.sha256(raw).hexdigest(),
                    "chunk_manifest": hashlib.sha256(manifest_raw).hexdigest()}


def check_files(*, audit: Path, bundle: Path, manifest: Path,
                artifacts: dict[str, Path], report: Path | None = None) -> dict:
    """Read exact supplied paths; never discover another run's snapshots."""
    raw_artifacts = {k: p.read_bytes() for k, p in artifacts.items()}
    texts = {k: raw.decode("utf-8") for k, raw in raw_artifacts.items()}
    chunks, pins = source_chunks(bundle, manifest)
    audit_raw = audit.read_bytes()
    parsed = load_json(audit_raw)
    from data_sheets_schema.api_runner import _audit_shape_problem
    shape = _audit_shape_problem(parsed) if isinstance(parsed, dict) else "audit must be an object"
    if shape:
        raise ValueError(shape)
    out = check_audit(parsed, artifacts={k: v for k, v in texts.items() if k.startswith("original_")},
                      chunks=chunks)
    pins["audit"] = hashlib.sha256(audit_raw).hexdigest()
    pins.update({k: hashlib.sha256(raw).hexdigest() for k, raw in raw_artifacts.items()})
    if "original_full" in texts and "final_full" in texts and isinstance(parsed, dict):
        out["findings"] += check_relationship_removals(
            parsed, load_record(texts["original_full"]), load_record(texts["final_full"]))
    if report is not None:
        raw = report.read_bytes()
        pins["report"] = hashlib.sha256(raw).hexdigest()
        try:
            claims = report_assertions(raw.decode("utf-8"))
            out["assertions_checked"] += len(claims)
            out["findings"] += check_assertions(claims, artifacts=texts, chunks=chunks)
        except (ValueError, UnicodeError) as exc:
            out["findings"].append(_problem("evidence_contract", str(exc)))
    out["artifact_sha256"] = pins
    out["scope"] = "Declared evidence only; semantic support and omitted claims require independent review."
    return out


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("audit", "bundle", "manifest", "original-full"):
        parser.add_argument("--" + name, type=Path, required=True)
    for name in ("original-core", "final-full", "final-core", "report"):
        parser.add_argument("--" + name, type=Path)
    args = parser.parse_args(argv)
    artifacts = {k: getattr(args, k) for k in sorted(ARTIFACTS) if getattr(args, k)}
    try:
        result = check_files(audit=args.audit, bundle=args.bundle, manifest=args.manifest,
                             artifacts=artifacts, report=args.report)
    except (OSError, ValueError, KeyError, TypeError, yaml.YAMLError) as exc:
        result = {"instrument": INSTRUMENT, "checked": False,
                  "findings": [_problem("evidence_inputs_unusable", str(exc))]}
    print(json.dumps(result, indent=2))
    return int(not result["checked"] or bool(result["findings"]))


if __name__ == "__main__":
    raise SystemExit(main())
