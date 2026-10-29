"""Evaluation-only joins across declared generation arm vocabularies."""


def normalized_run(run):
    from data_sheets_schema.cli.api import ARMS
    from data_sheets_schema.runs import ARM_BY_METHOD

    aliases = {value: value for value in ARM_BY_METHOD.values()}
    for key, (display, method, *_) in ARMS.items():
        canonical = ARM_BY_METHOD[method]
        aliases[key] = aliases[display] = canonical
    if not isinstance(run, dict) or run.get("arm") not in aliases:
        raise ValueError("unmapped generation arm")
    method = run.get("method")
    if method not in ARM_BY_METHOD:
        raise ValueError("unmapped generation method")
    arm = aliases[run["arm"]]
    if arm != ARM_BY_METHOD[method]:
        raise ValueError("generation arm disagrees with declared method")
    return {"arm": arm, **{key: run.get(key) for key in ("project", "label", "method")}}


def same_run(left, right):
    # Unknown values must fail closed even when both sides contain the same typo.
    try:
        return normalized_run(left) == normalized_run(right)
    except (ValueError, TypeError):
        return False


def blinding_identity(run, provenance_run, comparison_arm, version):
    """Comparison arm is declared; condition and method come from bound runs."""
    condition = provenance_run.get("condition")
    for value in (comparison_arm, condition, run["method"]):
        if not isinstance(value, str) or not value.strip() or value != value.strip():
            raise ValueError("blinding requires declared comparison arm, condition and method")
    replicate = provenance_run.get("replicate")
    if replicate is not None and (type(replicate) is not int or replicate < 1):
        raise ValueError("blinding replicate must be a positive integer when recorded")
    return {"version": version, "arm": comparison_arm, "input_arm": run["arm"],
            "project": run["project"], "label": run["label"], "condition": condition,
            "method": run["method"], "replicate_token": f"rep{replicate}" if replicate else None}


def forbidden_blinding_identities(identity):
    return tuple(identity[key] for key in ("condition", "method", "replicate_token") if identity[key])
