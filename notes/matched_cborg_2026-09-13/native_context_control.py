"""Opt-in continuation integration for bounded, recoverable native context.

This proves recoverability and particular completed Read ranges only. It does
not certify complete current-context coverage or scientific acceptance.
"""
from pathlib import Path
import shlex

from budgeted_cborg import BudgetStop
import native_context as frames


def documents(manifest):
    return {"instruction": manifest["job"]["instruction"], **manifest["inputs"]}


def paths(manifest):
    if "context_recovery" not in manifest:
        return {}
    try:
        return frames.bounded_paths(manifest["context_recovery"])
    except (KeyError, TypeError, ValueError) as error:
        raise BudgetStop("invalid bounded context recovery identity") from error


def prepare(manifest, destination, enabled):
    if type(enabled) is not bool:
        raise BudgetStop("context recovery requires an explicit boolean")
    if enabled:
        try:
            manifest["context_recovery"] = frames.prepare_context(
                Path(destination) / "recovery", documents(manifest))
        except (OSError, TypeError, ValueError) as error:
            raise BudgetStop("cannot prepare exact bounded context recovery") from error
        manifest["job"]["readable_inputs"] = sorted(
            set(manifest["job"]["readable_inputs"]) | set(paths(manifest)))


def render_system(manifest, original):
    if "context_recovery" not in manifest:
        return original
    job = manifest["job"]
    if manifest["kind"] == "d4d_native_audit_continuation":
        current = ("Current stage: Phase 3 audit only. Write only the new audit at "
                   + job["audit_path"] + ".\nThe single terminal validator is: "
                   + shlex.join(job["validator_argv"]) + "\n")
    elif manifest["kind"] == "d4d_native_finalization":
        current = ("Current stage: Phase 4 finalization only. Native writable artifacts: "
                   + job["full_path"] + " and " + job["report_path"]
                   + ". The trusted helper derives " + job["core_path"] + ".\n"
                   + "Derivation command: " + shlex.join(job["derive_argv"]) + "\n"
                   + "First closing check: " + shlex.join(job["check_argv"][0]) + "\n"
                   + "A successful first check ends checking. Only if its result explicitly permits the one "
                   + "ordinary closing repair may you repair, derive the core again, rewrite the report, "
                   + "and invoke the second closing check: " + shlex.join(job["check_argv"][1]) + "\n"
                   + "Source/evidence failure is terminal. No further repair or check is permitted.\n")
    else:
        raise BudgetStop("unsupported bounded native context stage")
    current += "In the recovery index, instruction is this current authoritative task; parent_instruction is historical reference only.\n"
    return original + "\nPersistent registered context recovery\n" + current + frames.render_recovery(manifest["context_recovery"])


def validate(manifest, registration_path):
    if "context_recovery" not in manifest:
        return
    try:
        block = manifest["context_recovery"]
        expected = Path(registration_path).parent / "recovery"
        if any(Path(path).parent != expected for path in paths(manifest)):
            raise ValueError("recovery files must use this fresh registration directory")
        frames.validate_context(block, documents(manifest), manifest["pinned_files"])
    except (OSError, KeyError, TypeError, ValueError) as error:
        raise BudgetStop("bounded native context differs from the exact registered documents") from error


def read_result(manifest, files, call, event, result):
    if "context_recovery" not in manifest or call.get("name") != "Read":
        return None
    payload = call["input"]
    path = str(files.target(payload.get("file_path")))
    if path not in paths(manifest) or files.classify("Read", payload)[0] != "prescribed":
        return None  # An out-of-range request is merely a denied exploration.
    try:
        value = frames.validate_read(manifest["context_recovery"], path,
            payload.get("offset"), payload.get("limit"), event, result)
    except (OSError, KeyError, TypeError, ValueError) as error:
        raise BudgetStop("bounded context Read is missing, changed, truncated or untyped") from error
    return {"tool_use_id": call["id"], **value}
