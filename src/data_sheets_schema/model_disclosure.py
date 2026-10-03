"""Explicit per-rating declared model identities, without scoring (#4299).

This is association of supplied local evidence, not provider authentication.
No generation model is inferred from a method, file name or evaluator metadata.
Historical ratings and the registered semantic report are never rewritten.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
import hashlib
import html
import io
import json
from pathlib import Path
import re
from typing import Iterable

import yaml

from data_sheets_schema.duplicate_keys import find_duplicate_keys
from data_sheets_schema.evaluation_model import model_family, same_family_label
from data_sheets_schema.semantic_comparison import evaluator_key

VERSION = "model-disclosure-v1"
DISCLAIMER = (
    "These are declared model families associated with explicitly supplied local evidence, "
    "not provider-authenticated identities. Same-family status does not measure self-preference, "
    "calibration or evaluator independence. Rows are individual ratings; none are pooled. "
    "Scores and historical reports are unchanged."
)
# Unknown declared evaluator types are retained but do not certify an LLM family.
LLM_TYPES = frozenset({"semantic_llm_judge", "llm_as_judge", "llm_judge", "llm"})


class DisclosureError(ValueError):
    """The supplied files cannot be reported without contradicting their identity."""


@dataclass(frozen=True)
class GenerationBinding:
    evaluation: Path
    input: Path
    provenance: Path


@dataclass(frozen=True)
class Captured:
    path: str
    resolved: Path
    raw: bytes

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.raw).hexdigest()


class _Capture:
    def __init__(self):
        self.files: dict[Path, Captured] = {}
        self.inodes: dict[tuple[int, int], bytes] = {}

    def read(self, path: Path) -> Captured:
        resolved = path.resolve()
        if resolved not in self.files:
            with path.open("rb") as stream:
                import os
                st = os.fstat(stream.fileno())
                key = (st.st_dev, st.st_ino)
                if key not in self.inodes:
                    self.inodes[key] = stream.read()
                raw = self.inodes[key]
            self.files[resolved] = Captured(str(path), resolved, raw)
        return self.files[resolved]


def _json(raw: bytes, label: str) -> dict:
    def pairs(items):
        value = {}
        for key, item in items:
            if key in value:
                raise DisclosureError(f"{label}: duplicate JSON key {key!r}")
            value[key] = item
        return value

    def constant(value):
        raise DisclosureError(f"{label}: non-finite JSON value {value}")

    value = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=pairs, parse_constant=constant)
    if not isinstance(value, dict):
        raise DisclosureError(f"{label}: expected a JSON object")
    return value


def _provenance(snapshot: Captured) -> dict:
    text = snapshot.raw.decode("utf-8-sig")
    try:
        if find_duplicate_keys(text, strict=True):
            raise DisclosureError(f"{snapshot.path}: duplicate provenance keys")
        value = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise DisclosureError(f"{snapshot.path}: malformed provenance YAML") from exc
    if not isinstance(value, dict):
        raise DisclosureError(f"{snapshot.path}: expected a provenance mapping")
    return value


def _text(value) -> str | None:
    return value if isinstance(value, str) and value.strip() and value == value.strip() else None


def _mapping(value, field: str) -> dict:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise DisclosureError(f"{field}: expected an object")
    return value


def _hash(value, algorithm: str, raw: bytes, field: str) -> dict:
    # d4d_file_hash is SHA256 in the legacy rubric schema and both hybrid
    # writers. The legacy output templates also admit the explicit prefix.
    # A bare 32-character value is NOT silently interpreted as MD5.
    size = {"sha256": 64, "md5": 32}[algorithm]
    pattern = rf"(?:{algorithm}:)?([0-9a-fA-F]{{{size}}})"
    matched = re.fullmatch(pattern, value) if isinstance(value, str) else None
    if matched is None:
        raise DisclosureError(f"{field}: expected a {algorithm} digest")
    actual = hashlib.new(algorithm, raw).hexdigest()
    if matched.group(1).lower() != actual:
        raise DisclosureError(f"{field}: supplied input bytes disagree with recorded hash")
    return {"field": field, "algorithm": algorithm, "recorded": value, "actual": actual}


def _declared_path(value, root: Path, field: str) -> Path:
    if _text(value) is None:
        raise DisclosureError(f"{field}: expected a nonempty path")
    p = Path(value)
    return (p if p.is_absolute() else root / p).resolve()


def _association(doc: dict, input_file: Captured, provenance: dict,
                 root: Path) -> dict:
    metadata = _mapping(doc.get("metadata"), "evaluation.metadata")
    hashes = []
    for key in ("input_sha256", "d4d_file_hash"):
        if key in metadata:
            hashes.append(_hash(metadata[key], "sha256", input_file.raw, f"metadata.{key}"))
    if "input_sha256" in doc:
        hashes.append(_hash(doc["input_sha256"], "sha256", input_file.raw, "input_sha256"))
    evaluation_bound = bool(hashes)
    checked_paths = []
    for owner, prefix in ((doc, ""), (metadata, "metadata.")):
        for key in ("d4d_file", "input_file", "input_path"):
            if key not in owner:
                continue
            value = owner[key]
            target = _declared_path(value, root, prefix + key)
            # Old API rubrics record only d4d_path.name. Basename equality
            # cannot associate a rating alone; require its verified hash too.
            basename = isinstance(value, str) and Path(value).name == value
            if basename:
                if value != input_file.resolved.name:
                    raise DisclosureError(f"{prefix + key}: supplied input basename disagrees with evaluation")
                path_basis = "basename_with_verified_hash" if hashes else "basename_only_unbound"
            else:
                if target != input_file.resolved:
                    raise DisclosureError(f"{prefix + key}: supplied input path disagrees with evaluation")
                evaluation_bound = True
                path_basis = "root_anchored_path"
            checked_paths.append({"field": prefix + key, "recorded": value, "basis": path_basis})

    outputs = _mapping(provenance.get("outputs"), "provenance.outputs")
    matched = []
    for kind in ("full", "core"):
        if kind not in outputs:
            continue
        output = _mapping(outputs[kind], f"provenance.outputs.{kind}")
        if "path" not in output:
            continue
        if _declared_path(output["path"], root, f"provenance.outputs.{kind}.path") == input_file.resolved:
            matched.append((kind, output))
    if len(matched) > 1:
        raise DisclosureError("provenance declares the input as both full and core")
    if not matched and any(isinstance(outputs.get(k), dict) and "path" in outputs[k] for k in ("full", "core")):
        raise DisclosureError("supplied input path disagrees with provenance full/core outputs")
    if matched:
        kind, output = matched[0]
        for algo in ("sha256", "md5"):
            if algo in output:
                hashes.append(_hash(output[algo], algo, input_file.raw, f"outputs.{kind}.{algo}"))
        if "bytes" in output and (type(output["bytes"]) is not int or output["bytes"] != len(input_file.raw)):
            raise DisclosureError(f"outputs.{kind}.bytes: supplied input size disagrees with provenance")
    else:
        kind = None

    run = _mapping(provenance.get("run"), "provenance.run")
    run_fields, missing = [], []
    for key in ("project", "method", "label"):
        if key in doc:
            if _text(doc[key]) is None:
                raise DisclosureError(f"evaluation.{key}: expected a nonempty identity")
            if key not in run:
                missing.append(f"provenance.run.{key} absent")
            elif run[key] != doc[key]:
                raise DisclosureError(f"provenance.run.{key} disagrees with evaluation")
            else:
                run_fields.append(key)
    if not evaluation_bound:
        missing.append("evaluation has no verified hash or unambiguous input path")
    if not matched:
        missing.append("provenance has no matching full/core output path")
    model = provenance.get("model")
    generator = None
    if isinstance(model, dict):
        # Invalid nonempty preferred identifiers do not silently use another
        # field. Missing/null/blank model falls back to the recorded name.
        selected = model.get("model") or model.get("name")
        generator = _text(selected)
    if generator is None:
        missing.append("provenance generation model absent or malformed")
    associated = not missing
    return {"generator": generator if associated else None,
            "association_status": "associated" if associated else "unknown",
            "association_basis": "captured_supplied_provenance_path_and_run_identity" if associated else "insufficient_binding",
            "association_reasons": missing,
            "binding_checks": {"root": str(root), "input_paths": checked_paths,
                               "hashes": hashes, "run_fields": run_fields, "output_kind": kind,
                               "provenance_capture": "supplied_local_bytes_not_provider_authenticated"}}


def build_report(paths: Iterable[Path], *, bindings: Iterable[GenerationBinding] = (),
                 root: Path | None = None) -> dict:
    """Capture named files once and retain every rating in caller order.

    Relative recorded paths use the explicit root (default current directory),
    never a guessed corpus tree. File arguments themselves use normal caller
    paths. Duplicate ratings remain separate rows; a binding applies to every
    occurrence of the same evaluation path. Contradictions refuse the report.
    """
    paths = [Path(p) for p in paths]
    if not paths:
        raise DisclosureError("name at least one evaluation")
    root = (root or Path.cwd()).resolve()
    named = {p.resolve() for p in paths}
    bound = {}
    for binding in bindings:
        key = Path(binding.evaluation).resolve()
        if key not in named:
            raise DisclosureError("generation binding names an evaluation outside the report")
        if key in bound:
            raise DisclosureError("more than one binding supplied for an evaluation")
        bound[key] = binding
    captures = _Capture()
    evaluation_docs, provenance_docs = {}, {}
    rows = []
    for index, path in enumerate(paths, 1):
        evaluation = captures.read(path)
        if evaluation.resolved not in evaluation_docs:
            evaluation_docs[evaluation.resolved] = _json(evaluation.raw, str(path))
        doc = evaluation_docs[evaluation.resolved]
        model = doc.get("model")
        model = model if isinstance(model, dict) else {}
        key = _text(evaluator_key({"model": model}))
        declarations = {name: owner["evaluation_type"] for name, owner in
                        (("model", model), ("top_level", doc)) if "evaluation_type" in owner}
        type_basis = "model" if "model" in declarations else "top_level" if declarations else "unrecorded"
        raw_type = declarations.get(type_basis)
        evaluation_type = _text(raw_type)
        type_conflict = (len(declarations) == 2 and
                         json.dumps(declarations["model"], sort_keys=True) !=
                         json.dumps(declarations["top_level"], sort_keys=True))
        family_allowed = not type_conflict and (raw_type is None or evaluation_type in LLM_TYPES)
        family_key = key if family_allowed else None
        row = {"rating": index, "evaluation_path": str(path), "evaluation_resolved_path": str(evaluation.resolved),
               "evaluation_sha256": evaluation.sha256, "project": _text(doc.get("project")),
               "method": _text(doc.get("method")), "label": _text(doc.get("label")),
               "rubric": _text(doc.get("rubric")), "rubric_version": _text(doc.get("version")),
               "evaluator": key, "evaluator_display": _text(model.get("name")) or key,
               "evaluation_type": evaluation_type, "evaluation_type_basis": type_basis,
               "evaluation_type_declarations": declarations, "evaluation_type_conflict": type_conflict,
               "evaluator_family": model_family(family_key),
               "evaluator_family_basis": "declared_model_identifier" if family_key else "unknown_or_non_llm_evaluator",
               "input_path": None, "input_sha256": None, "provenance_path": None,
               "provenance_sha256": None, "generator": None, "generator_family": None,
               "same_family": "unknown", "association_status": "unknown", "association_basis": "no_binding_supplied",
               "association_reasons": ["no explicit generation binding supplied"], "binding_checks": None}
        if evaluation.resolved in bound:
            binding = bound[evaluation.resolved]
            input_file = captures.read(Path(binding.input))
            provenance_file = captures.read(Path(binding.provenance))
            row.update(input_path=str(input_file.resolved), input_sha256=input_file.sha256,
                       provenance_path=str(provenance_file.resolved), provenance_sha256=provenance_file.sha256)
            if provenance_file.resolved not in provenance_docs:
                provenance_docs[provenance_file.resolved] = _provenance(provenance_file)
            row.update(_association(doc, input_file, provenance_docs[provenance_file.resolved], root))
            row["generator_family"] = model_family(row["generator"])
            row["same_family"] = same_family_label(family_key, row["generator"])
        rows.append(row)
    return {"version": VERSION, "disclaimer": DISCLAIMER, "root": str(root), "rows": rows,
            "captured_files": [{"path": str(c.resolved), "sha256": c.sha256, "bytes": len(c.raw)}
                               for c in captures.files.values()]}


def render(report: dict, format: str = "markdown") -> str:
    """All formats carry the same per-rating fields, with no aggregation."""
    if format == "json":
        return json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    if format not in {"markdown", "csv"}:
        raise DisclosureError("format must be markdown, csv or json")
    rows = report["rows"]
    columns = ["report_version", "disclaimer", *rows[0]]
    values = [[report["version"], report["disclaimer"], *row.values()] for row in rows]

    def cell(value):
        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)
        return "unknown" if value is None else str(value)

    if format == "csv":
        out = io.StringIO(newline="")
        writer = csv.writer(out)
        writer.writerow(columns)
        writer.writerows([[cell(v) for v in row] for row in values])
        return out.getvalue()

    def escaped(value):
        text = html.escape(cell(value), quote=False)
        text = re.sub(r"([\\`*_{}\[\]()])", r"\\\1", text)
        return text.replace("|", "&#124;").replace("\r\n", "\n").replace("\r", "\n").replace("\n", "<br>")

    lines = [f"# Model disclosure ({VERSION})", "", DISCLAIMER, ""]
    for index, row in enumerate(values, 1):
        lines.extend([f"## Rating {index}", "", "| Field | Recorded value |", "|---|---|"])
        lines.extend(f"| {escaped(key)} | {escaped(value)} |" for key, value in zip(columns, row))
        lines.append("")
    return "\n".join(lines) + "\n"


def write_report(report: dict, output: Path, *, format: str = "markdown") -> None:
    """Publish only to a new file; existing files and aliases are never replaced."""
    text = render(report, format)
    target = output.resolve()
    for item in report["captured_files"]:
        source = Path(item["path"])
        if target == source or output.exists() and source.exists() and output.samefile(source):
            raise DisclosureError("output aliases a captured input")
    # Exclusive creation also closes the hardlink/symlink race after the guard.
    with output.open("x", encoding="utf-8", newline="") as stream:
        stream.write(text)
