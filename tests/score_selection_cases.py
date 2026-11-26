"""Synthetic accepted-score fixtures for issue 6385, 2026-11-26.

Adapted from the read-only reviewer fx.py and F/G scenarios. Nothing imports or
executes those scripts. Inputs and outputs stay under the caller's test folder.
Only validity and repository path plumbing are substituted in CLI invocations.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner
import yaml

INSTRUMENT = "synthetic-instrument"
METHOD = "claudecode_agent"
MAXIMUM = {"rubric10": 50, "rubric20": 88}
LABELS = (("cfg_rep1", 4), ("cfg_rep2", 9), ("cfg_rep3", 6))


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()
    path.write_bytes(raw)
    return sha(raw)


def snapshot(root):
    return {str(path.relative_to(root)): path.read_bytes()
            for path in sorted(Path(root).rglob("*")) if path.is_file()}


def report(result, name):
    assert result.exit_code == 0, result.output + repr(result.exception)
    return json.JSONDecoder().raw_decode(result.output.split(name + ":\n", 1)[1])[0]


class Case:
    def __init__(self, tmp, *, manifest_projects=("P", "Q")):
        self.tmp = Path(tmp).resolve()
        self.corpus = self.tmp / "corpus"
        self.concat = self.corpus / "data/d4d_concatenated"
        self.receipts = self.tmp / "receipts"
        self.receipts.mkdir(parents=True, exist_ok=True)
        self.manifest = self.tmp / "source-manifest.json"
        write(self.manifest, {"projects": {name: {"sources": []} for name in manifest_projects}})
        self.entries = {}

    def record(self, project, label, slots=4):
        full = self.concat / METHOD / label
        core = self.concat / (METHOD + "_core") / label
        full.mkdir(parents=True, exist_ok=True)
        core.mkdir(parents=True, exist_ok=True)
        value = {"id": "example:" + project + label, "name": "Record", "title": "Title", "description": "Text"}
        value.update({"slot_" + str(i): ["value"] for i in range(slots)})
        path = full / (project + "_d4d.yaml")
        path.write_text(yaml.safe_dump(value), encoding="utf-8")
        (core / (project + "_d4d_core.yaml")).write_text("id: example:record\n", encoding="utf-8")
        (core / (project + "_reconciliation.md")).write_text("# synthetic\n", encoding="utf-8")
        (core / (project + "_provenance.yaml")).write_text(yaml.safe_dump({
            "record_mode": "live", "run": {"method": METHOD, "label": label, "project": project}}), encoding="utf-8")
        return path

    def scoring(self, project, label, family, number, points, *, maximum=None, context=b"context",
                run_name=None, status="VALIDATED_AND_PUBLISHED", manifest=True, root=None, overrides=None):
        root = Path(root) if root else self.receipts
        record = self.concat / METHOD / label / (project + "_d4d.yaml")
        maximum = MAXIMUM[family] if maximum is None else maximum
        run = root / (run_name or f"{project}-{label}-{family}-{number}")
        directory = (self.corpus / "data/evaluation_llm" / (family + "_semantic") / "label_aware" / INSTRUMENT
                     if number == 1 else self.corpus / "data/evaluation_repeats" / INSTRUMENT /
                     ("scoring_rep" + str(number)) / (family + "_semantic"))
        output = directory / (project + "_" + label + "_evaluation.json")
        identity = {"rubric": family + "-semantic", "version": "6.0", "project": project,
                    "method": METHOD, "label": label, "instrument_id": INSTRUMENT,
                    "d4d_file": str(record.relative_to(self.corpus))}
        inputs = {name: {"sha256": sha((family + name).encode())} for name in
                  ("agent-definition.md", "output-schema.json", "evidence-authority.json", "rubric.txt")}
        inputs.update({"record.yaml": {"sha256": sha(record.read_bytes())},
                       "scope-context.json": {"sha256": sha(b"scope" + record.read_bytes())}})
        metadata = {"input_sha256": inputs["record.yaml"]["sha256"], "context_sha256": sha(context),
                    "scope_context_sha256": inputs["scope-context.json"]["sha256"],
                    "rubric_sha256": inputs["rubric.txt"]["sha256"],
                    "instrument_sha256": inputs["agent-definition.md"]["sha256"],
                    "evidence_authority_sha256": inputs["evidence-authority.json"]["sha256"]}
        deterministic = {"metadata": metadata, "evaluation_scope": {"policy": "single_dataset"},
                         "applicability_context": {}}
        prompt = family + project + label
        plan = {"instrument": INSTRUMENT, "identity": identity, "inputs": inputs,
                "run_directory": str(run), "output": str(output), "prompt": prompt,
                "prompt_sha256": sha(prompt.encode()), "runner_sha256": sha(b"runner"),
                "definition_provenance": {"composed_sha256": metadata["instrument_sha256"]},
                "deterministic_fields": deterministic}
        if overrides:
            overrides(plan)
        publication = {**{k: v for k, v in identity.items() if k != "instrument_id"}, **deterministic,
                       "scorer_instrument": {"id": INSTRUMENT, "prompt_sha256": plan["prompt_sha256"],
                                             "runner_sha256": plan["runner_sha256"]},
                       "overall_score": {"total_points": points, "adjusted_max_points": maximum,
                                         "max_points": MAXIMUM[family]}}
        plan_sha = write(run / "plan.json", plan)
        receipt = {"status": status, "plan_sha256": sha(json.dumps(plan, sort_keys=True).encode())}
        output_sha = None
        if status == "VALIDATED_AND_PUBLISHED":
            output_sha = write(output, publication)
            receipt.update(codex_exit=0, validator_exit=0, auth_copy_absent=True, output=str(output),
                           output_sha256=output_sha, validator_input_sha256=output_sha)
        else:
            receipt.update(failure="synthetic refusal")
        receipt_sha = write(run / "receipt.json", receipt)
        entry = {"plan": plan, "receipt": receipt, "publication": publication, "output": output,
                 "run": run, "plan_sha": plan_sha, "receipt_sha": receipt_sha}
        if number > 1 and manifest and status == "VALIDATED_AND_PUBLISHED":
            baseline = self.entry(project, label, family, 1)
            value = {"status": "EXPORTED_VALIDATED_REPEAT", "identity": identity,
                     "scoring_replicate": number, "generation_replicate": int(label.rsplit("rep", 1)[-1]),
                     "actual_plan": str(run / "plan.json"), "actual_plan_sha256": plan_sha,
                     "actual_receipt": str(run / "receipt.json"), "actual_receipt_sha256": receipt_sha,
                     "destination": str(output), "destination_sha256": output_sha,
                     "source_output_sha256": output_sha, "copy_validator_exit": 0,
                     "baseline_plan": str(baseline["run"] / "plan.json"), "baseline_plan_sha256": baseline["plan_sha"],
                     "baseline_receipt": str(baseline["run"] / "receipt.json"), "baseline_receipt_sha256": baseline["receipt_sha"]}
            path = root / "export-manifests" / run.name / "manifest.json"
            write(path, value)
            entry.update(manifest=value, manifest_path=path)
        self.entries[project, label, family, number, run.name] = entry
        return entry

    def entry(self, project="P", label="cfg_rep1", family="rubric10", number=1):
        return self.entries[project, label, family, number, f"{project}-{label}-{family}-{number}"]

    def score_record(self, project, label, r10, r20, **kw):
        for family, values in (("rubric10", r10), ("rubric20", r20)):
            for number, points in enumerate(values, 1):
                self.scoring(project, label, family, number, points, **kw)

    def base(self, *, q_root=None, noisy=False):
        for label, slots in LABELS:
            self.record("P", label, slots)
            self.record("Q", label, slots)
        self.score_record("P", "cfg_rep1", [40, 41, 40], [70, 71, 70])
        self.score_record("P", "cfg_rep2", [35, 35, 36], [62, 62, 63])
        self.score_record("P", "cfg_rep3", [36, 36, 36], [63, 63, 63])
        values = ([20, 35, 48], [40, 60, 85]) if noisy else ([30, 30, 31], [50, 51, 50])
        for label, _ in LABELS:
            self.score_record("Q", label, *values, root=q_root)
        return self

    def refresh(self, entry, *, publication=False, plan=False, receipt=False):
        """Rebind outer hashes, so a negative control isolates its intended check."""
        if publication:
            digest = write(entry["output"], entry["publication"])
            entry["receipt"].update(output_sha256=digest, validator_input_sha256=digest)
            if "manifest" in entry:
                entry["manifest"].update(destination_sha256=digest, source_output_sha256=digest)
            receipt = True
        if plan:
            entry["plan_sha"] = write(entry["run"] / "plan.json", entry["plan"])
            entry["receipt"]["plan_sha256"] = sha(json.dumps(entry["plan"], sort_keys=True).encode())
            if "manifest" in entry:
                entry["manifest"]["actual_plan_sha256"] = entry["plan_sha"]
            receipt = True
        if receipt:
            entry["receipt_sha"] = write(entry["run"] / "receipt.json", entry["receipt"])
            if "manifest" in entry:
                entry["manifest"]["actual_receipt_sha256"] = entry["receipt_sha"]
        if "manifest" in entry:
            write(entry["manifest_path"], entry["manifest"])
        for other in self.entries.values():
            manifest = other.get("manifest")
            if manifest and manifest.get("baseline_plan") == str(entry["run"] / "plan.json"):
                manifest.update(baseline_plan_sha256=entry["plan_sha"], baseline_receipt_sha256=entry["receipt_sha"])
                write(other["manifest_path"], manifest)

    def invoke(self, *, variation=False, roots=None, extra=(), invalid=(), module=None, policy=True):
        from data_sheets_schema import runs as model
        from data_sheets_schema.cli import runs as cli
        module = module or cli
        command = ["score-variation" if variation else "select", "--method", METHOD, "--config", "cfg"]
        if not variation:
            command.extend(["--project", "P"])
        if policy:
            if not variation:
                command.extend(["--score-policy", "score_gap_v1"])
            command.extend(["--score-instrument", INSTRUMENT])
            for root in roots if roots is not None else (self.receipts,):
                command.extend(["--score-receipts", str(root)])
        command.extend(extra)
        with patch.object(model, "CONCAT_DIR", self.concat), \
                patch("data_sheets_schema.registry.selected_manifest", lambda context=None: self.manifest), \
                patch.object(module, "_validates", lambda path: (Path(path).parent.name not in invalid,
                             "invalid (full)" if Path(path).parent.name in invalid else "valid")), \
                patch("data_sheets_schema.cli.provenance._require_repo_root_cwd", lambda name: None):
            return CliRunner().invoke(module.runs, command)
