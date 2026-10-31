"""Durable local failure/response latches; not cryptographic authenticity (#5138, #5142).

The append-only chain precedes each mutable ledger/index update. A proved
interrupted update requires explicit acknowledgement; terminal and consumed
control state never grant another call. Launch records anchor resume heads.
"""
from __future__ import annotations

import copy
from contextlib import contextmanager
from datetime import datetime
import hashlib
from functools import lru_cache
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys

from data_sheets_schema import usage_ledger as ledger

FORMAT = "d4d_latch_guard_v1"
OVERRIDE_FORMAT = "d4d_latch_override_v1"
_HEX = re.compile(r"[0-9a-f]{64}")
_MISSING = {"__d4d_latch_missing__": True}

# D70: derived offline with
# git log --all --diff-filter=A --format='%H %cI' -- src/data_sheets_schema/latch_journal.py
# Use ancestry, not wall-clock comparison, when the recorded commit resolves.
D41_COMMIT = "8ab03fda923d2c8caa9a2e65e558be73e92500e9"
D41_COMMITTED_AT = "2026-10-25T22:11:01-07:00"


def _age_git(root, *args):
    env = {**os.environ, "GIT_NO_LAZY_FETCH": "1", "GIT_NO_REPLACE_OBJECTS": "1"}
    return subprocess.run(["git", "--no-replace-objects", "-C", root, *args],
                          env=env, capture_output=True, text=True, timeout=10)


def _resolve_recorded_commit(commit, root):
    result = _age_git(root, "rev-parse", "--verify", "--end-of-options", commit + "^{commit}")
    full = result.stdout.strip().lower()
    if not result.returncode and re.fullmatch(r"[0-9a-f]{40}", full) and full.startswith(commit):
        return full
    return None


@lru_cache(maxsize=4096)
def _resolve_full_commit(commit, root):
    # Full object IDs are immutable. Short prefixes are resolved afresh because
    # new local objects could make an abbreviation ambiguous.
    return _resolve_recorded_commit(commit, root)


@lru_cache(maxsize=128)
def _age_repository_constants(root):
    boundary = _resolve_full_commit(D41_COMMIT, root)
    shallow = _age_git(root, "rev-parse", "--is-shallow-repository")
    return boundary, shallow.stdout.strip() if shallow.returncode == 0 else None


def _commit_age(commit, root):
    if not isinstance(commit, str) or not re.fullmatch(r"[0-9a-fA-F]{4,40}", commit):
        return None
    commit = commit.lower()
    try:
        # Recorded commit evidence must be immutable, never a movable ref.
        full = (_resolve_full_commit(commit, root) if len(commit) == 40
                else _resolve_recorded_commit(commit, root))
        if full is None:
            return None
        boundary, shallow = _age_repository_constants(root)
        if boundary is None:
            return None
        descendant = _age_git(root, "merge-base", "--is-ancestor", boundary, full)
        if descendant.returncode == 0:
            return "post-D41"
        # A shallow graph cannot establish a negative ancestry result.
        if descendant.returncode == 1 and shallow == "false":
            return "pre-D41"
    except (OSError, subprocess.TimeoutExpired):
        pass
    return None


def record_age(record, *, repo_root=None):
    """Positive recorded ancestry, else a strictly earlier recorded timestamp.

    A recent timestamp alone never establishes post-D41 ancestry. Missing
    journal/integrity fields convey no age evidence. No remote Git operation.
    """
    record = record if isinstance(record, dict) else {}
    repo = record.get("repo")
    root = str(repo_root or Path(__file__).resolve().parents[2])
    age = _commit_age(repo.get("commit") if isinstance(repo, dict) else None, root)
    if age:
        return age
    value = record.get("record_generated_at")
    try:
        when = value if isinstance(value, datetime) else datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if when.tzinfo is not None and when < datetime.fromisoformat(D41_COMMITTED_AT):
            return "pre-D41"
    except (ValueError, TypeError):
        pass
    return "age unestablished"


def record_eligibility_problem(record):
    model = record.get("model") if isinstance(record, dict) else None
    if isinstance(model, dict) and "runtime_integrity" in model:
        return eligibility_problem(model["runtime_integrity"])
    age = record_age(record)
    # D73(a): only positive post-D41 evidence gates a missing block. Unknown
    # age remains eligible and is reported separately by each consumer.
    return f"{age}: missing runtime_integrity block" if age == "post-D41" else None


def _record(spec):
    import yaml
    if not spec.provenance_path.exists():
        return {}
    try:
        value = yaml.safe_load(_bytes(spec.provenance_path))
        return value if isinstance(value, dict) and ledger.record_matches(spec, value.get("run")) else {}
    except (ValueError, yaml.YAMLError):
        return {}


def refuse_legacy_execution(spec):
    """Read-only pre-lock refusal; repeat the guard at write/spend boundaries."""
    try:
        events = _events(spec)
    except ledger.UsageLedgerError as exc:
        # Preserve D57 even though this check now precedes launch_record.
        message = re.sub(r'[0-9a-fA-F]{64,}',
                         lambda match: match[0][:8] + '…(unverified, not a resume anchor)', str(exc))
        print(f'latch journal refused: {message} (not a resume anchor)', file=sys.stderr, flush=True)
        raise ledger.UsageLedgerError(message) from None
    own = _mine(spec, events)
    if any(event["kind"] == "legacy_unverifiable" for event in own):
        _fail("previously adopted legacy run is inspection only; legacy recovery never spends")
    if not own:
        path = ledger.ledger_path(spec)
        if path.is_file():
            try:
                data = _json(_bytes(path))
            except (ValueError, TypeError):
                data = {}
            if isinstance(data, dict) and "latch_journal" in data:
                _fail("journal was deleted from a guarded ledger; found=missing journal (not a resume anchor)")
        if path.exists() or path.is_symlink() or _legacy_evidence(spec):
            _fail(f"{record_age(_record(spec))}: artifacts have no journal for the selected run; inspection only; "
                  "relaunch with a new label; legacy recovery never spends")


def _canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("utf-8")


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _fail(message):
    raise ledger.UsageLedgerError(f"latch journal: {message}")


def journal_path(spec) -> Path:
    return spec.metadata_dir / f"{spec.project}_latch_journal.jsonl"


def override_path(spec) -> Path:
    return spec.metadata_dir / f"{spec.project}_latch_override.json"


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _json(raw):
    def invalid(value):
        raise ValueError(f"non-finite JSON number: {value}")
    return json.loads(raw, object_pairs_hook=_pairs, parse_constant=invalid)


def _bytes(path: Path) -> bytes:
    try:
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode):
            _fail(f"not a regular file: {path}")
        return path.read_bytes()
    except OSError as exc:
        _fail(f"cannot read {path}: {exc}")


def _events(spec) -> list[dict]:
    path = journal_path(spec)
    if not path.exists() and not path.is_symlink():
        return []
    raw = _bytes(path)
    if not raw or not raw.endswith(b"\n"):
        _fail(f"empty or truncated journal: expected=nonempty newline-terminated events; found={len(raw)} bytes, trailing_newline={raw.endswith(bytes([10]))}")
    events = []
    previous = None
    try:
        for number, line in enumerate(raw.splitlines(), 1):
            event = _json(line)
            if not isinstance(event, dict):
                raise ValueError("non-object event")
            body = {key: value for key, value in event.items() if key != "sha256"}
            if (set(event) != {"version", "line", "previous_sha256", "identity",
                               "generation_id", "kind", "payload", "sha256"}
                    or type(event["line"]) is not int or event["line"] != number
                    or type(event["version"]) is not int or event["version"] != 1
                    or event["previous_sha256"] != previous
                    or not isinstance(event["identity"], dict)
                    or not isinstance(event["generation_id"], str) or not event["generation_id"]
                    or event["kind"] not in {"generation", "legacy_unverifiable", "latch", "override", "aborted_update"}
                    or not isinstance(event["payload"], dict)
                    or event["sha256"] != _sha(_canonical(body))):
                raise ValueError(f"invalid event at line {number}: expected previous_sha256={previous}, "
                                 f"sha256={_sha(_canonical(body))}, line={number}, version=1; "
                                 f"found previous_sha256={event.get('previous_sha256')}, "
                                 f"sha256={event.get('sha256')}, line={event.get('line')}, version={event.get('version')}")
            previous = event["sha256"]
            events.append(event)
    except (TypeError, ValueError, KeyError) as exc:
        _fail(f"broken chain: expected=valid hash-chained event; found={exc}")
    return events


def _event(spec, data, events, kind, payload):
    body = {"version": 1, "line": len(events) + 1,
            "previous_sha256": events[-1]["sha256"] if events else None,
            "identity": ledger.run_identity(spec), "generation_id": data["generation_id"],
            "kind": kind, "payload": copy.deepcopy(payload)}
    return {**body, "sha256": _sha(_canonical(body))}


def _append(spec, events, event):
    path = journal_path(spec)
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_APPEND | os.O_CREAT | os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0)
    newly_created = not path.exists()
    try:
        descriptor = os.open(path, flags, 0o600)
        with os.fdopen(descriptor, "ab") as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                _fail("journal is not a regular file")
            stream.write(_canonical(event) + b"\n")
            stream.flush()
            os.fsync(stream.fileno())
        if newly_created:
            directory = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
    except OSError as exc:
        _fail(f"cannot append journal: {exc}")
    events.append(event)


def _mine(spec, events, generation=None):
    return [event for event in events
            if event["identity"] == ledger.run_identity(spec)
            and (generation is None or event["generation_id"] == generation)]


def _checkpoint(spec, event):
    return {"path": str(journal_path(spec)), "head_sha256": event["sha256"],
            "line_count": event["line"]}


def _snapshot_key(entry):
    return "snapshot:" + _sha(_canonical([entry.get("usage_id"), entry.get("name"), entry.get("path")]))


def _observations(data):
    result = {"intent:pending_call": copy.deepcopy(data.get("pending_call"))}
    for name in ("report_regate_attempted", "removal_repair_attempted"):
        if data.get(name) is True:
            result[f"allowance:{name}"] = True
    for name in ("typed_audit", "receipt_completion", "removal_repair_admission",
                 "receipt_completion_transcript", "validator_repair_refresh"):
        if name in data:
            result[f"controller:{name}"] = copy.deepcopy(data[name])
    if data.get("receipt_completion_full") is not None:
        result["allowance:receipt_completion_full"] = copy.deepcopy(data["receipt_completion_full"])

    def failures(value, path):
        if isinstance(value, dict):
            for key, child in value.items():
                child_path = [*path, key]
                if key == "failure_type" or (key == "state" and child == "failed"):
                    result["terminal:field:" + _canonical(child_path).decode()] = copy.deepcopy(child)
                failures(child, child_path)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                failures(child, [*path, index])

    for key, value in data.items():
        if key.startswith("latch_") or key == "report_rejections":
            continue
        if key == "failure_type":
            result['terminal:field:["failure_type"]'] = copy.deepcopy(value)
        if key == "state" and value == "failed":
            result['terminal:field:["state"]'] = value
        failures(value, [key])
        if key == "evidence_refusal" and value is not None:
            result["terminal:evidence_refusal"] = copy.deepcopy(value)
        if key in {"typed_audit", "receipt_completion"} and isinstance(value, dict) and value.get("state") == "failed":
            result[f"terminal:{key}"] = copy.deepcopy(value)
    for row in data.get("rows", []):
        if "source_review_admission" in row:
            result[f"admission:{row['usage_id']}"] = copy.deepcopy(row["source_review_admission"])
        if row.get("failure_type") is not None or row.get("state") == "failed":
            result[f"terminal:row:{row['usage_id']}"] = copy.deepcopy(row)
    for name in ("receipt_completion", "typed_audit"):
        value = data.get(name)
        if not isinstance(value, dict):
            continue
        if value.get("response") is not None:
            result[f"response:{name}"] = copy.deepcopy(value["response"])
        for number, stage in enumerate(value.get("stages", [])):
            if isinstance(stage, dict) and stage.get("response") is not None:
                result[f"response:{name}:{number}"] = copy.deepcopy(stage["response"])
    for rejection in data.get("report_rejections", []):
        if not isinstance(rejection, dict) or not isinstance(rejection.get("rejection_id"), str):
            _fail("malformed report rejection history")
        key = f"report:{rejection['rejection_id']}"
        if key in result:
            _fail("duplicate report rejection identity")
        result[key] = copy.deepcopy(rejection)
    for entry in data.get("latch_snapshots", []):
        if (not isinstance(entry, dict) or not isinstance(entry.get("usage_id"), str)
                or not entry["usage_id"] or any(not isinstance(entry.get(key), str) or not entry[key]
                                                for key in ("path", "name", "index_path", "sha256"))
                or not _HEX.fullmatch(entry["sha256"])):
            _fail("malformed saved response pin")
        key = _snapshot_key(entry)
        if key in result:
            _fail("duplicate saved response pin")
        result[key] = copy.deepcopy(entry)
    return result


def _latches(events):
    result = {}
    aborted = {digest for event in events if event['kind'] == 'aborted_update'
               for digest in event['payload']['aborted_event_sha256s']}
    for event in events:
        if event["kind"] == "latch" and event['sha256'] not in aborted:
            payload = event["payload"]
            if set(payload) != {"key", "value"} or not isinstance(payload["key"], str):
                _fail("malformed latch event")
            result[payload["key"]] = event
    return result


def _mismatches(spec, data, events):
    observed = _observations(data)
    mismatches = []
    indexes = {}
    for key, event in _latches(events).items():
        expected = event["payload"]["value"]
        found = observed.get(key, _MISSING)
        if found != expected:
            mismatches.append({"event_sha256": event["sha256"], "key": key,
                               "expected": expected, "found": found})
        if key.startswith("snapshot:"):
            path = Path(expected["path"])
            try:
                actual_sha = _sha(_bytes(path))
            except ledger.UsageLedgerError:
                actual_sha = _MISSING
            if actual_sha != expected["sha256"]:
                mismatches.append({"event_sha256": event["sha256"], "key": key + ":bytes",
                                   "expected": expected["sha256"], "found": actual_sha})
            try:
                if expected["index_path"] not in indexes:
                    indexes[expected["index_path"]] = _json(_bytes(Path(expected["index_path"])))
                index = indexes[expected["index_path"]]
                if (index.get("generation_id") != data["generation_id"]
                        or index.get("run_identity") != data["identity"]):
                    raise ValueError("wrong snapshot generation")
                matches = [entry for entry in index["snapshots"]
                           if _snapshot_key(entry) == key]
                actual_entry = matches[0] if len(matches) == 1 else _MISSING
            except (ledger.UsageLedgerError, ValueError, KeyError, TypeError, AttributeError):
                actual_entry = _MISSING
            wanted_entry = {k: v for k, v in expected.items() if k != "index_path"}
            if actual_entry != wanted_entry:
                mismatches.append({"event_sha256": event["sha256"], "key": key + ":index",
                                   "expected": wanted_entry, "found": actual_entry})
    return mismatches


def _acknowledgements(events):
    return [copy.deepcopy(event["payload"]) for event in events
            if event["kind"] in {"override", "aborted_update"}]


def _override(spec, data, required):
    path = override_path(spec)
    if not path.exists() and not path.is_symlink():
        _fail("unacknowledged discrepancy; required event_sha256s=" + ",".join(sorted(required)))
    try:
        raw = _bytes(path)
        value = _json(raw)
        keys = {"format", "identity", "generation_id", "event_sha256s", "authorization", "authorized_by", "authorized_at"}
        if (not isinstance(value, dict) or set(value) != keys
                or value["format"] != OVERRIDE_FORMAT or value["identity"] != data["identity"]
                or value["generation_id"] != data["generation_id"]
                or not isinstance(value["event_sha256s"], list)
                or any(not isinstance(item, str) or not _HEX.fullmatch(item) for item in value["event_sha256s"])
                or len(set(value["event_sha256s"])) != len(value["event_sha256s"])
                or set(value["event_sha256s"]) != set(required)
                or any(not isinstance(value[key], str) or not value[key].strip()
                       for key in ("authorization", "authorized_by", "authorized_at"))):
            raise ValueError("override does not name exactly this identity, generation and discrepancy set")
        when = datetime.fromisoformat(value["authorized_at"].replace("Z", "+00:00"))
        if when.tzinfo is None or when.utcoffset() is None:
            raise ValueError("override time requires a timezone")
    except (ValueError, TypeError, KeyError) as exc:
        _fail(f"invalid explicit override: {exc}")
    return {"path": str(path), "sha256": _sha(raw), "acknowledgement": value}


def _apply_override(spec, data, events, mine, discrepancies):
    prior = _acknowledgements(mine)
    covered = [item for record in prior for item in record.get("discrepancies", [])]
    pending = [item for item in discrepancies if item not in covered]
    if pending:
        try:
            acknowledgement = _override(spec, data, {item["event_sha256"] for item in pending})
        except ledger.UsageLedgerError as exc:
            def bounded(value):
                raw = _canonical(value)
                return value if len(raw) <= 240 else {"type": type(value).__name__,
                    "canonical_bytes": len(raw), "canonical_sha256": _sha(raw)}
            summary = [{"event_sha256": item["event_sha256"], "key": item["key"],
                        "expected": bounded(item["expected"]), "found": bounded(item["found"])}
                       for item in pending[:4]]
            raise ledger.UsageLedgerError(str(exc) + "; discrepancies=" + _canonical(summary).decode()
                                         + (f"; {len(pending) - 4} further discrepancies" if len(pending) > 4 else "")) from exc
        if any(record.get("sha256") == acknowledgement["sha256"] for record in prior):
            _fail("an already-applied override cannot acknowledge a later discrepancy; obtain a new explicit acknowledgement")
        # D56: an acknowledgement that cannot authorize continuation is not
        # recorded, even when the caller only requested provenance or a write.
        if any(key.startswith('terminal:') for key in _latches(mine)):
            _fail("historical terminal failure or evidence rejection remains latched; "
                  "override refused without recording assistance")
        if any(item['key'].startswith(('controller:', 'intent:', 'allowance:', 'admission:'))
               for item in discrepancies):
            _fail("control-state discrepancy cannot authorize a call or refund a consumed allowance; "
                  "override refused without recording assistance")
        acknowledgement["discrepancies"] = copy.deepcopy(pending)
        event = _event(spec, data, events, "override", acknowledgement)
        _append(spec, events, event)
        mine.append(event)
        data["latch_overrides"] = _acknowledgements(mine)
        data["latch_journal"] = _checkpoint(spec, event)
        ledger._write_unlatched(spec, data)
    return mine


def _legacy(spec, data, events):
    # D69: an in-memory evidence binding, never an adoption or a ledger write.
    event = _event(spec, data, events, "legacy_unverifiable",
                   {"ledger_sha256": _sha(_bytes(ledger.ledger_path(spec))),
                    "reason": "historical latches cannot be independently established"})
    mine = [event]
    if override_path(spec).exists():
        acknowledgement = _override(spec, data, {event["sha256"]})
        mine.append(_event(spec, data, [*events, event], "override", acknowledgement))
    return mine


def _owned_artifact_name(project, name, *, intermediate=False, include_locks=False):
    """Runner artifact names, anchored after the exact project identifier.

    Match the names emitted by usage_ledger, snapshot_store and the runner's
    snapshot producers, including archives and numeric snapshot collisions.
    A bare project prefix is insufficient: P_X is a distinct project from P.
    """
    prefix = re.escape(project) + "_"
    metadata = (r"(?:d4d(?:_core)?\.yaml|reconciliation\.md|provenance\.yaml|"
                r"api_progress\.json|latch_(?:journal\.jsonl|override\.json)|"
                r"api_usage_[0-9a-f]{16}(?:\.previous-[0-9a-f]{32})?\.json|"
                r"reasoning(?:\.previous-[0-9a-f]{32})?\.jsonl)")
    index = r"snapshot_index(?:\.previous-[0-9a-f]{32})?\.json"
    if include_locks and re.fullmatch(
            r"\." + prefix + r"(?:d4d(?:_core)?\.yaml|reconciliation\.md|provenance\.yaml)_api_run\.lock", name):
        return True
    if re.fullmatch(prefix + (index if intermediate else metadata), name):
        return True
    # Atomic JSON writes use .<destination stem>.<temporary suffix>.tmp.
    temporary = (r"snapshot_index" if intermediate else
                 r"(?:api_usage_[0-9a-f]{16}|api_progress)")
    if re.fullmatch(r"\." + prefix + temporary + r"\.[A-Za-z0-9_-]+\.tmp", name):
        return True
    if not intermediate:
        return False
    phase = (r"(?:full|core|audit|reconcile_full|reconcile_core|report|report_regate|"
             r"report_after_repair|repair_full|repair_core|full_readdress|receipt_completion|"
             r"removal_repair_full|typed_audit_worker|typed_audit_omission|typed_audit_integration)")
    bodies = (
        r"(?:full|core|reconcile_full|reconcile_core|coverage_receipt(?:_as_written)?|"
        r"repair_(?:full|core)_r[0-9]+|removal_repair_full)(?:_[0-9]+)?\.yaml",
        r"(?:audit|(?:audit|reconcile|report)_evidence|removal_repair_check|"
        r"receipt_completion_(?:transcript|result|context|inputs|request|response)|"
        r"typed_audit_(?:packet|assembly|[0-9]+_(?:request|context|response)))(?:_[0-9]+)?\.json",
        r"(?:report|report_before_regate)(?:_[0-9]+)?\.md",
        r"(?:" + phase + r"_(?:(?:rejected_)?response_[0-9a-f]{32}|"
        r"unusable_attempt[0-9]+|incomplete_attempt[0-9]+_[0-9]+)|"
        r"removal_repair_response)(?:_[0-9]+)?\.txt",
    )
    return any(re.fullmatch(prefix + pattern, name) for pattern in bodies)


def _legacy_evidence(spec):
    """Inspect exact owned artifact names/identities, including ignored files.

    Surviving artifacts establish residue, never its age. Prefix siblings do
    not belong to this run; positively guarded foreign identities stay separate.
    """
    from data_sheets_schema.snapshot_store import index_path
    import yaml
    events = _events(spec)
    def guarded_foreign(identity):
        if not isinstance(identity, dict) or not ledger.identity_is_foreign(spec, identity):
            return False
        selected = {key: identity.get(key) for key in ledger.run_identity(spec)}
        history = [event for event in events if event["identity"] == selected]
        return (any(event["kind"] == "generation" for event in history)
                and not any(event["kind"] == "legacy_unverifiable" for event in history))
    candidates = [(spec.provenance_path, "run", "yaml"),
                  (spec.metadata_dir / f"{spec.project}_api_progress.json", "run_identity", "json"),
                  (index_path(spec.metadata_dir, spec.project), "run_identity", "json")]
    found = []
    foreign = False
    for path, identity_key, encoding in candidates:
        if not path.exists() and not path.is_symlink():
            continue
        raw = _bytes(path)
        try:
            value = yaml.safe_load(raw) if encoding == "yaml" else _json(raw)
        except (ValueError, yaml.YAMLError):
            value = None
        identity = value.get(identity_key) if isinstance(value, dict) else None
        foreign_label = (isinstance(value, dict) and value.get("label") is not None
                         and value["label"] != spec.label)
        # Older progress omits run_identity but can still positively bind a
        # guarded foreign generation. A label alone cannot establish that.
        if identity is None and foreign_label and value.get("generation_id"):
            identities = [event["identity"] for event in events
                          if event["generation_id"] == value["generation_id"]
                          and event["identity"].get("label") == value["label"]]
            if identities and all(guarded_foreign(item) for item in identities):
                foreign = True
                continue
        if (ledger.identity_is_foreign(spec, identity) or foreign_label) and guarded_foreign(identity):
            foreign = True
            continue
        found.append(str(path))
    if not foreign:
        for path in (spec.full_path, spec.core_path, spec.report_path):
            if path.exists() or path.is_symlink():
                found.append(str(path))
        # Partial/archived deliveries are residue too, even if progress,
        # provenance and the active ledger were all removed (P5).
        for folder in (spec.metadata_dir, spec.metadata_dir / "intermediate"):
            for path in folder.iterdir() if folder.is_dir() else ():
                if not _owned_artifact_name(spec.project, path.name,
                                            intermediate=folder == spec.metadata_dir / "intermediate"):
                    continue
                if path == journal_path(spec):
                    continue  # _events/_mine already selected the guarded identity.
                if path.name.startswith(f"{spec.project}_api_usage_") or path == override_path(spec):
                    try:
                        value = _json(_bytes(path))
                    except (ValueError, ledger.UsageLedgerError):
                        value = None
                    if isinstance(value, dict) and guarded_foreign(value.get("identity")):
                        continue
                if path.is_file() or path.is_symlink():
                    found.append(str(path))
    return found


def _recover_update(spec, data, events, mine):
    """Abort only a prefix-proved, uncommitted update that bought no allowance.

    The acknowledgement and aborted suffix are one durable event. If its ledger
    checkpoint write is interrupted too, replay only that already authorized
    checkpoint update. No terminal/controller/admission/allowance is discarded.
    """
    checkpoint = data.get('latch_journal')
    prefix_end = next((i + 1 for i, event in enumerate(events)
                       if checkpoint == _checkpoint(spec, event)
                       and event['identity'] == data['identity']
                       and event['generation_id'] == data['generation_id']), None)
    expected = _checkpoint(spec, mine[-1])
    error = (f"ledger checkpoint does not match journal head: expected={expected}; found={checkpoint}")
    if prefix_end is None:
        _fail(error)
    prefix = _mine(spec, events[:prefix_end], data['generation_id'])
    suffix = events[prefix_end:]
    if (not suffix or any(e['identity'] != data['identity'] or e['generation_id'] != data['generation_id']
                          for e in suffix)
            or _observations(data) != {k: e['payload']['value'] for k, e in _latches(prefix).items()}
            or _mismatches(spec, data, prefix)
            or data.get('latch_overrides', []) != _acknowledgements(prefix)):
        _fail(error + '; not an intact interrupted-update prefix')
    recovered = suffix[-1] if suffix[-1]['kind'] == 'aborted_update' else None
    pending = suffix[:-1] if recovered else suffix
    if not pending or any(e['kind'] != 'latch' for e in pending):
        _fail(error + '; unsupported interrupted-update suffix')
    prior = _latches(prefix)
    for event in pending:
        key, value = event['payload']['key'], event['payload']['value']
        # A newly committed intent precedes dispatch; returning to None after
        # owner acknowledgement does not refund any separately latched quota.
        new_intent = (key == 'intent:pending_call' and isinstance(value, dict)
                      and prior.get(key, {}).get('payload', {}).get('value') is None)
        if (key.startswith(('terminal:', 'controller:', 'allowance:', 'admission:'))
                or key.startswith('intent:') and not new_intent
                or any(k.startswith('terminal:') for k in prior)):
            _fail(error + '; terminal or consumed control state cannot be aborted')
    digests = [e['sha256'] for e in pending]
    discrepancy = {'event_sha256': pending[-1]['sha256'], 'key': 'interrupted_update',
                   'expected': checkpoint, 'found': _checkpoint(spec, pending[-1])}
    if recovered:
        acknowledgement = recovered['payload']
        if (acknowledgement.get('aborted_event_sha256s') != digests
                or acknowledgement.get('discrepancies') != [discrepancy]
                or set(acknowledgement.get('acknowledgement', {}).get('event_sha256s', [])) != set(digests)):
            _fail(error + '; invalid interrupted-update acknowledgement')
    else:
        acknowledgement = _override(spec, data, set(digests))
        if any(a.get('sha256') == acknowledgement['sha256'] for a in _acknowledgements(prefix)):
            _fail('an already-applied override cannot acknowledge a later interrupted update')
        acknowledgement.update(discrepancies=[discrepancy], aborted_event_sha256s=digests)
        recovered = _event(spec, data, events, 'aborted_update', acknowledgement)
        _append(spec, events, recovered)
        mine.append(recovered)
    data['latch_journal'] = _checkpoint(spec, recovered)
    data['latch_overrides'] = _acknowledgements(mine)
    ledger._write_unlatched(spec, data)


def _validated(spec, *, spending=False, allow_new=False, startup=False, mutation=False):
    events = _events(spec)
    own = _mine(spec, events)
    path = ledger.ledger_path(spec)
    if not path.exists() and not path.is_symlink():
        if own:
            _fail(f"usage ledger deleted while its generation journal survives: expected generation={own[-1]['generation_id']}; found=missing ledger")
        if _legacy_evidence(spec):
            _fail("surviving historical outputs/progress have no usage ledger or latch history; "
                  "relaunch with a new label; historical evidence cannot become a clean resume")
        return None, events, []
    # Strict decoding also rejects duplicate keys before the ordinary shape guard.
    try:
        data = ledger._validate_data(spec, _json(_bytes(path)), path)
    except (ValueError, TypeError) as exc:
        _fail(f"invalid usage ledger: {exc}")
    mine = _mine(spec, events, data["generation_id"])
    if (spending or startup or mutation) and any(e['kind'] == 'legacy_unverifiable' for e in mine):
        _fail("previously adopted legacy run is inspection only; legacy recovery never spends")
    if not own:
        if "latch_journal" in data:
            _fail(f"journal was deleted from a guarded ledger: expected={data['latch_journal']}; found=missing journal")
        if spending or startup or mutation:
            _fail("journal-less run is inspection only; relaunch with a new label; legacy recovery never spends")
        mine = _legacy(spec, data, events)
        return data, events, mine
    else:
        if not mine or own[-1]["generation_id"] != data["generation_id"]:
            _fail(f"current generation does not match the last journaled boundary: expected={own[-1]['generation_id']}; found={data['generation_id']}")
        if data.get("latch_journal") != _checkpoint(spec, mine[-1]):
            _recover_update(spec, data, events, mine)
        if data.get("latch_overrides", []) != _acknowledgements(mine):
            _fail(f"durable override history was changed or removed: expected={_acknowledgements(mine)}; found={data.get('latch_overrides')}")
    discrepancies = _mismatches(spec, data, mine)
    mine = _apply_override(spec, data, events, mine, discrepancies)
    if (spending or startup and discrepancies) and any(key.startswith("terminal:") for key in _latches(mine)):
        _fail("historical terminal failure or evidence rejection remains latched; acknowledgement does not authorize another call")
    if (spending or startup) and any(item["key"].startswith(("controller:", "intent:", "allowance:", "admission:"))
                        for item in discrepancies):
        _fail("acknowledged control-state discrepancy cannot authorize a call or refund a consumed allowance")
    return data, events, mine


def _allowed_transition(key, before, after):
    if key == 'controller:validator_repair_refresh':
        if not isinstance(before, dict) or not isinstance(after, dict):
            return False
        if before.get('checkpoint') != after.get('checkpoint'):
            return before.get('state') == 'accepted' and after.get('state') == 'pending'
        return ((before.get('state'), after.get('state')) in {('pending', 'in_flight'), ('in_flight', 'accepted')}
                and all(after.get(k) == v for k, v in before.items() if k != 'state'))
    return (key.startswith(("controller:", "intent:")) or
            (key.startswith("admission:") and isinstance(before, dict) and isinstance(after, dict)
            and set(before) == set(after) == {"state", "response_sha256"}
            and before["state"] == "pending" and after["state"] == "accepted"
            and before["response_sha256"] == after["response_sha256"]
            and bool(_HEX.fullmatch(str(after["response_sha256"])))))


def _check_transcript_transition(spec, previous, data):
    """A pre-seal selector may advance; the independently pinned exchanges stay."""
    previous = previous or {}
    before = previous.get("receipt_completion_transcript", _MISSING)
    after = data.get("receipt_completion_transcript", _MISSING)
    if before == after:
        return
    if any(account.get(name) is not None for account in (previous, data)
           for name in ("receipt_completion", "receipt_completion_full")):
        _fail("receipt transcript selector cannot change after the full seal or completion intent")
    if (not isinstance(after, dict) or set(after) != {"path", "sha256"}
            or not any(entry.get("name") == f"{spec.project}_receipt_completion_transcript.json"
                       and entry.get("path") == after["path"]
                       and entry.get("sha256") == after["sha256"]
                       for entry in previous.get("latch_snapshots", []))):
        _fail("receipt transcript selector requires a previously journaled exchange snapshot")


def _carry_guard_fields(spec, data, previous, mine):
    """Omitted or stale prefixes are carried forward; conflicting bytes refuse."""
    for key in ('latch_snapshots', 'latch_overrides', 'latch_journal'):
        if key in data:
            supplied, persisted = data[key], previous.get(key)
            if key == 'latch_journal':
                compatible = any(supplied == _checkpoint(spec, e) for e in mine)
            else:
                actual = persisted or []
                compatible = isinstance(supplied, list) and supplied == actual[:len(supplied)]
            if not compatible:
                _fail(f'conflicting guard-owned {key}: expected persisted value or prior prefix; found caller mutation')
        if key in previous:
            data[key] = copy.deepcopy(previous[key])
        else:
            data.pop(key, None)


def before_ledger_write(spec, data, *, snapshot=None):
    """Validate persisted state before accepting a caller's proposed mutation."""
    explicit_fresh = data.get("accept_legacy") is False and data.get("rows") == []
    previous, events, mine = _validated(spec, allow_new=explicit_fresh, mutation=True)
    ledger._validate_data(spec, data, ledger.ledger_path(spec))
    same_generation = previous is not None and previous["generation_id"] == data["generation_id"]
    _check_transcript_transition(spec, previous if same_generation else None, data)
    if same_generation:
        _carry_guard_fields(spec, data, previous, mine)
    if snapshot is not None:
        data.setdefault('latch_snapshots', []).append(copy.deepcopy(snapshot))
    if previous is None or previous["generation_id"] != data["generation_id"]:
        if previous is not None and previous["generation_id"] not in data.get("prior_generation_ids", []):
            _fail("new generation omitted its predecessor")
        event = _event(spec, data, events, "generation", {"prior_generation_ids": data.get("prior_generation_ids", [])})
        _append(spec, events, event)
        mine = [event]
    expected = _latches(mine)
    proposed = _observations(data)
    current = _observations(previous) if previous is not None and previous["generation_id"] == data["generation_id"] else {}
    for key, event in expected.items():
        old = event["payload"]["value"]
        new = proposed.get(key, _MISSING)
        allowed = current.get(key, _MISSING) == old and _allowed_transition(key, old, new)
        if (allowed and key == 'controller:validator_repair_refresh'
                and old.get('checkpoint') != new.get('checkpoint')
                and any(e['kind'] == 'latch' and e['payload']['key'] == key
                        and e['payload']['value'].get('checkpoint') == new.get('checkpoint') for e in mine)):
            allowed = False
        if new != old and not allowed:
            # A previously acknowledged observed discrepancy can remain visible;
            # the acknowledgement never permits a different subsequent edit.
            if new != current.get(key, _MISSING):
                _fail(f"attempted removal or rewrite of immutable latch: {key}")
            acknowledged = any(item.get("key") == key and item.get("found") == new
                               for record in _acknowledgements(mine)
                               for item in record.get("discrepancies", []))
            if not acknowledged:
                _fail(f"attempted removal or rewrite of immutable latch: {key}")
    for key, value in proposed.items():
        prior = expected.get(key)
        if prior is None or (prior["payload"]["value"] != value
                             and current.get(key, _MISSING) == prior["payload"]["value"]
                             and _allowed_transition(key, prior["payload"]["value"], value)):
            event = _event(spec, data, events, "latch", {"key": key, "value": value})
            _append(spec, events, event)
            mine.append(event)
    data["latch_journal"] = _checkpoint(spec, mine[-1])
    data["latch_overrides"] = _acknowledgements(mine)


def remember_snapshot(spec, entry, *, index_path):
    """Pin before the mutable index; a failed second write is a visible stop."""
    if entry.get("usage_id") is None:
        return
    _validated(spec)
    data = ledger._read(spec)
    pin = {**entry, "index_path": str(index_path)}
    if _sha(_bytes(Path(pin["path"]))) != pin["sha256"]:
        _fail("response bytes changed before their first journal pin")
    before_ledger_write(spec, data, snapshot=pin)
    ledger._write_unlatched(spec, data)


def _metadata(spec, events, mine):
    overrides = _acknowledgements(mine)
    legacy = [event for event in mine if event['kind'] == 'legacy_unverifiable']
    result = {"format": FORMAT, "verified": bool(mine) and not any(event["kind"] == "legacy_unverifiable" for event in mine),
              "assisted": bool(overrides), "evidence_only": bool(overrides or legacy),
              "overrides": overrides, "authentication": "not_cryptographically_authenticated"}
    if events:
        result["journal"] = {"path": str(journal_path(spec)), "sha256": _sha(_bytes(journal_path(spec))),
                             "head_sha256": events[-1]["sha256"], "line_count": len(events)}
    else:
        result["journal"] = None
    if legacy:
        result["legacy_unverifiable"] = legacy[0]["payload"]
        result["binding_sha256"] = legacy[0]["sha256"]
        result["accounting_completeness"] = "unknown"
        result["record_age"] = record_age(_record(spec))
    return result


def check(spec, *, spending=True, startup=False):
    """Check startup and immediately before each physical provider attempt."""
    # An intact terminal account reaches the runner's detailed refusal at
    # startup; the physical-call boundary always retains the spending check.
    _, events, mine = _validated(spec, spending=spending and not startup,
                                allow_new=not spending, startup=startup)
    return _metadata(spec, events, mine)


def head_sha256(spec):
    events = _events(spec)
    return events[-1]['sha256'] if events else None


@contextmanager
def launch_record(spec, expected):
    """D57: print externally retainable heads, requiring the prior launch head.

    This never derives the caller's expectation from the mutable run directory.
    The journal remains locally hashed, not cryptographically authenticated.
    """
    def display(boundary):
        try:
            head = head_sha256(spec)
        except ledger.UsageLedgerError:
            head = 'invalid'
            boundary = 'unverified (not a resume anchor)'
        print(f'latch journal {boundary}: project={spec.project} label={spec.label} '
              f'head_sha256={head or "none"} path={journal_path(spec)}', file=sys.stderr, flush=True)
    try:
        found = head_sha256(spec)
        if expected is not None and (not isinstance(expected, str) or not _HEX.fullmatch(expected)):
            _fail(f'resume journal head: expected=64 lowercase hexadecimal digits; found={expected!r}')
        if found != expected:
            _fail(f'resume journal head: expected={expected or "required from prior launch/monitor record"}; found={found or "missing"}')
    except ledger.UsageLedgerError as exc:
        # No refused diagnostic is a source of anchors, including malformed
        # expectations and hashes embedded in broken-chain errors. Redact the
        # exception too, and suppress its unsafe context in CLI/log tracebacks.
        def redact(message):
            return re.sub(r'[0-9a-fA-F]{64,}',
                          lambda match: match[0][:8] + '…(unverified, not a resume anchor)', message)
        message = redact(str(exc))
        print(redact(f'latch journal refused: project={spec.project} label={spec.label} '
                     f'{message} (not a resume anchor)'), file=sys.stderr, flush=True)
        raise ledger.UsageLedgerError(message) from None
    display('start')
    try:
        yield
    finally:
        display('stop')


def provenance(spec):
    """Expose qualified history without granting permission to continue spending."""
    _, events, mine = _validated(spec)
    return _metadata(spec, events, mine)


def verify_completed_legacy(record_path, *, evidence_root, recorded_root):
    """Read-only verification of generic_v6 API records with a request spec.

    Other API conditions (including v7/v8) and agentic records are unsupported.
    D73(b) deliberately retains this narrow scope; it does not currently cover
    the committed historical campaign records.

    The explicit root mapping changes only file lookup, never captured bytes or
    instruction substitutions. Inventory covers selected-project artifacts and
    their bound inputs, including the ordinary split full/core layout, rather
    than unrelated projects sharing a capture root. No execution, lock, repair
    or usage initializer is reachable. Shared/receipt controllers require their
    own future verifier.
    Returns a separate evidence-only envelope; never restamps the old record.
    """
    import yaml
    from data_sheets_schema import api_runner as api
    from data_sheets_schema.provenance import check_record
    from data_sheets_schema.duplicate_keys import duplicate_keys_in

    root, old = Path(evidence_root).resolve(), Path(recorded_root)
    path = Path(record_path).absolute()
    if not old.is_absolute() or ".." in old.parts or not path.is_relative_to(root):
        _fail("verification requires absolute evidence and recorded roots")

    def safe(item):
        if not item.is_relative_to(root) or ".." in item.parts:
            _fail("verification path escapes the evidence root")
        for ancestor in (item, *item.parents):
            if ancestor.is_symlink():
                _fail("verification refuses symlinks")
            if ancestor == root:
                break
        return item

    raw_record = _bytes(safe(path))
    if duplicate_keys_in(path):
        _fail("duplicate keys in legacy provenance")
    record = yaml.safe_load(raw_record)
    if not isinstance(record, dict) or record_age(record) != "pre-D41":
        _fail("completed legacy verification requires positive pre-D41 age evidence")
    run = record.get("run") or {}
    model = record.get("model") or {}
    if "runtime_integrity" in model:
        _fail("guarded history cannot enter legacy verification")
    request = (record.get("prompts") or {}).get("request") or {}
    rendered = request.get("spec") or {}
    if run.get("condition") != "generic_v6" or any(rendered.get(key) for key in (
            "shared_generation_version", "receipt_completion_version", "removal_repair_version")):
        _fail("legacy verifier currently supports generic_v6 only; other controllers are unaddressed")
    issues, failure = check_record(record)
    if issues or failure:
        _fail(f"legacy provenance conformance failed: {failure or issues}")
    replay = api.RunSpec.from_render_spec(rendered, **{k: run[k] for k in ("project", "method", "label")})
    if _sha(replay.instruction.encode()) != request.get("sha256"):
        _fail("legacy instruction binding changed")

    def local(value):
        source = Path(value)
        if not source.is_absolute() or not source.is_relative_to(old) or ".." in source.parts:
            _fail(f"evidence path is outside recorded root: {value}")
        return safe(root / source.relative_to(old))

    outputs = {role: local(record["outputs"][role]["path"]) for role in ("full", "core", "report")}
    project, method, label = (run[key] for key in ("project", "method", "label"))
    expected_names = {"full": f"{project}_d4d.yaml", "core": f"{project}_d4d_core.yaml",
                      "report": f"{project}_reconciliation.md"}
    if (path.name != f"{project}_provenance.yaml"
            or any(outputs[role].name != name for role, name in expected_names.items())
            or outputs["core"].parent != path.parent or outputs["report"].parent != path.parent):
        _fail("legacy output ownership mismatch")
    full_dir, metadata_dir = outputs["full"].parent, path.parent
    if full_dir != metadata_dir and not (
            full_dir.name == metadata_dir.name == label
            and full_dir.parent.name == method and metadata_dir.parent.name == method + "_core"
            and full_dir.parent.parent == metadata_dir.parent.parent):
        _fail("legacy output layout is not the recorded flat or split layout")
    for role in ("full", "core"):
        if local(record["validation"]["artifacts"][role]["path"]) != outputs[role]:
            _fail("legacy validation binding names a different output")
    if local(record["report_claims"]["artifacts"]["report"]["path"]) != outputs["report"]:
        _fail("legacy report binding names a different output")
    if local(record["companions"]["reasoning_log"]["path"]) != metadata_dir / f"{project}_reasoning.jsonl":
        _fail("legacy reasoning binding names a different run artifact")

    inputs = record["inputs"]
    intermediates = record.get("intermediates") or []
    if not intermediates:
        _fail("missing completed intermediate bindings")
    for entry in intermediates:
        item = local(entry["path"])
        if (not item.is_relative_to(metadata_dir / "intermediate")
                or not _owned_artifact_name(project, item.name, intermediate=True)):
            _fail("legacy intermediate ownership mismatch")
    bindings = [
        {"path": inputs["bundle_path"], "md5": inputs.get("bundle_md5"), "sha256": inputs.get("bundle_sha256")},
        inputs["source_manifest"], inputs["chunks"],
        *record["validation"]["artifacts"].values(), record["report_claims"]["artifacts"]["report"],
        record["companions"]["reasoning_log"], *intermediates]
    bound = {path, *(local(entry["path"]) for entry in bindings)}

    def inventory():
        candidates = set(bound)
        for directory in {full_dir, metadata_dir}:
            for item in directory.rglob("*"):
                if _owned_artifact_name(project, item.name,
                        intermediate=item.parent == metadata_dir / "intermediate", include_locks=True) and (
                        not item.is_dir() or item.is_symlink()):
                    candidates.add(item)
        return {str(item.relative_to(root)): _sha(_bytes(safe(item))) for item in sorted(candidates)}

    before = inventory()
    if before[str(path.relative_to(root))] != _sha(raw_record):
        _fail("legacy provenance changed during verification")
    if any(name.endswith("_latch_journal.jsonl") for name in before):
        _fail("guarded history cannot enter legacy verification")
    if any(name.endswith("_api_progress.json") for name in before):
        _fail("legacy run is incomplete: progress survives")

    def verify(entry):
        if not isinstance(entry, dict) or not entry.get("path"):
            _fail("missing legacy file binding")
        item = local(entry["path"])
        if str(item.relative_to(root)) not in before:
            _fail("legacy snapshot binding is outside the selected run evidence")
        raw = _bytes(item)
        hashes = {key: entry[key] for key in ("sha256", "md5") if entry.get(key)}
        if not hashes or any(hashlib.new(key, raw).hexdigest() != value for key, value in hashes.items()):
            _fail(f"legacy file hash mismatch: {entry['path']}")

    for entry in bindings:
        verify(entry)
    repo = Path(__file__).resolve().parents[2]
    for role in ("full", "core"):
        schema = record["schema"]
        schema_path = Path(schema[role + "_path"])
        if schema_path.is_absolute() or ".." in schema_path.parts:
            _fail("invalid schema resource path")
        if _sha(_bytes(repo / schema_path)) != schema[role + "_sha256"]:
            _fail("legacy schema binding changed")
    usage = record.get("api_usage")
    if not isinstance(usage, list) or not {"full", "audit", "reconcile_full", "report"}.issubset(
            {row.get("phase") for row in usage}):
        _fail("missing completed phase accounting")
    accounted = {row.get("usage_id") for row in usage}
    generation = run.get("generation_id")
    identity = {k: run.get(k) for k in ("project", "label", "method", "condition")}
    expected_inputs = {
        "bundle": {"path": inputs["bundle_path"], "sha256": _sha(_bytes(local(inputs["bundle_path"])))},
        **{key: {"path": inputs[key]["path"], "sha256": _sha(_bytes(local(inputs[key]["path"])))}
           for key in ("source_manifest", "chunks")},
        "profile": {"name": record["schema"]["profile"], "digest_md5": record["schema"]["digest_md5"]},
        "instruction": {"render_version": replay.render_version, "sha256": request["sha256"], "spec": rendered}}
    # Current local completion checks cannot repair or call a provider.
    # Accounting helpers read metadata only. Validation uses the independently
    # mapped output paths, which may live in different default-layout folders.
    replay.out_dir = metadata_dir
    if api._unrecorded_reasoning(replay, record):
        _fail("unaccounted legacy reasoning usage")
    if api._unrecorded_abandoned(replay, record):
        _fail("unaccounted legacy abandoned usage")
    validation = api.validate_outputs(api.ValidationInputs(outputs["full"], outputs["core"]))
    if validation:
        _fail(f"legacy outputs fail current validation: {validation}")
    for name in before:
        item = root / name
        if "_api_usage_" in item.name and item.suffix == ".json":
            data = ledger._validate_data(replay, _json(_bytes(item)), item)
            if any(k in data for k in ("latch_journal", "latch_overrides", "latch_snapshots")):
                _fail("guarded ledger cannot enter legacy verification")
            if data.get("identity") != identity or data.get("generation_id") != generation:
                _fail("unaccounted legacy ledger identity")
            if data.get("rows") != usage or data.get("pending_call") or data.get("evidence_refusal"):
                _fail("incomplete or inconsistent legacy accounting")
            if (ledger._identity_differs(data.get("input_identity"), expected_inputs)
                    or data.get("pending_snapshot_activation") or data.get("pending_reasoning_archive")
                    or any(key.startswith("terminal:") for key in _observations(data))):
                _fail("legacy ledger input or completion state is inconsistent")
        if "_snapshot_index" in item.name and item.suffix == ".json":
            index = _json(_bytes(item))
            if index.get("run_identity") != identity or index.get("generation_id") != generation:
                _fail("unaccounted legacy snapshot generation")
            if index.get("version") != 1 or ledger._identity_differs(index.get("input_identity"), expected_inputs):
                _fail("legacy snapshot input identity is inconsistent")
            for entry in index["snapshots"]:
                verify(entry)
                if entry.get("usage_id") and entry["usage_id"] not in accounted:
                    _fail("unaccounted legacy snapshot attempt")
    if before != inventory():
        _fail("legacy evidence changed during verification")
    return {"already_complete": True, "legacy_unverifiable": True, "evidence_only": True,
            "campaign_eligible": False, "age": "pre-D41", "new_calls": 0,
            "accounting_completeness": "unknown", "observed_usage": usage,
            "record_sha256": _sha(raw_record), "evidence_sha256": _sha(_canonical(before)),
            "verified_files": before,
            "verification_scope": "selected-project full/metadata artifacts and explicitly bound input files",
            "recorded_root": str(old), "evidence_root": str(root),
            "verification": "recorded identity, instruction, schema, files and observed accounting"}


def eligibility_problem(block):
    """Pure final-campaign eligibility guard; callers decide legacy handling."""
    if not isinstance(block, dict) or block.get("format") != FORMAT:
        return "runtime integrity metadata is malformed or has an unsupported format"
    if type(block.get("verified")) is not bool or not block["verified"]:
        return "runtime integrity history is unverified"
    if type(block.get("assisted")) is not bool or block["assisted"]:
        return "runtime integrity history is assisted or malformed"
    if type(block.get("evidence_only")) is not bool or block["evidence_only"]:
        return "runtime integrity history is evidence-only or malformed"
    if block.get("overrides") != []:
        return "runtime integrity history contains an override or lacks its acknowledgement inventory"
    journal = block.get("journal")
    if (not isinstance(journal, dict) or set(journal) != {"path", "sha256", "head_sha256", "line_count"}
            or not isinstance(journal["path"], str) or not journal["path"].strip()
            or any(not isinstance(journal[key], str) or not _HEX.fullmatch(journal[key])
                   for key in ("sha256", "head_sha256"))
            or type(journal["line_count"]) is not int or journal["line_count"] < 1
            or block.get("authentication") != "not_cryptographically_authenticated"):
        return "runtime integrity journal metadata is incomplete or invalid"
    return None
