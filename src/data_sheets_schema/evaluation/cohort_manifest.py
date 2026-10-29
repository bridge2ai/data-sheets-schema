"""Declared evaluation cohorts; no project, comparator or replicate defaults."""
from pathlib import Path
from string import Formatter

from . import registered_eval_runner as runner

FORMAT = "evaluation_cohort_v1"


def read_cohort(path):
    """Expand explicit cells into exact run identities, retaining the file pin.

    A cell names arm, projects, replicates, label_template, method, condition
    and input_arm. Only {project} and {replicate} substitution is permitted.
    Multiple cells can declare different comparator labels for one arm.
    """
    path = Path(path).absolute()
    raw = runner._read(path)
    doc = runner._yaml(raw)
    if not isinstance(doc, dict) or set(doc) != {"format", "cells"} or doc["format"] != FORMAT:
        raise ValueError("requires evaluation_cohort_v1 with cells")
    if not isinstance(doc["cells"], list) or not 1 <= len(doc["cells"]) <= 1000:
        raise ValueError("cohort requires 1..1000 cells")
    records, identities = [], set()
    required = {"arm", "projects", "replicates", "label_template", "method", "condition", "input_arm"}
    for cell in doc["cells"]:
        if not isinstance(cell, dict) or set(cell) != required:
            raise ValueError("cohort cell requires " + ", ".join(sorted(required)))
        for name in ("arm", "label_template", "method", "condition", "input_arm"):
            value = cell[name]
            if (not isinstance(value, str) or not value or value.strip() != value
                    or len(value) > 4096 or any(ord(c) < 32 for c in value)):
                raise ValueError("cohort identities must be bounded nonempty unpadded strings")
        projects, replicates = cell["projects"], cell["replicates"]
        if (not isinstance(projects, list) or not projects
                or any(not isinstance(p, str) or not p or p.strip() != p
                       or any(c in p for c in "/\\*?[]") for p in projects)
                or len(set(projects)) != len(projects)):
            raise ValueError("cohort projects must be unique literal names")
        if (not isinstance(replicates, list) or not replicates
                or any(type(r) is not int or r < 1 for r in replicates)
                or len(set(replicates)) != len(replicates)):
            raise ValueError("cohort replicates must be unique positive integers")
        for _, field, spec, conversion in Formatter().parse(cell["label_template"]):
            if field is not None and (field not in {"project", "replicate"} or spec or conversion):
                raise ValueError("cohort label_template only accepts project and replicate fields")
        for project in projects:
            for replicate in replicates:
                label = cell["label_template"].format(project=project, replicate=replicate)
                if any(c in label for c in "/\\*?[]") or label in {".", ".."}:
                    raise ValueError("cohort labels must be literal path components")
                identity = (cell["arm"], project, label)
                if identity in identities or len(records) >= 1000:
                    raise ValueError("duplicate or oversized cohort")
                identities.add(identity)
                records.append({"arm": cell["arm"], "project": project, "label": label,
                                "replicate": replicate, "method": cell["method"],
                                "condition": cell["condition"], "input_arm": cell["input_arm"]})
    return sorted(records, key=lambda r: (r["arm"], r["project"], r["label"])), runner.shared.file_pin(path, raw)
