"""One registered API quality or slot judgement, using the shared budget.

Preparation captures the existing evaluator's actual request without constructing
a provider. Execution makes one streamed request and preserves the response before
validation. A clipped JSON prefix is never an accepted new judgement.
"""
from contextlib import contextmanager
from dataclasses import asdict
import hashlib
import json
import math
import os
from pathlib import Path
import re
import threading
from types import SimpleNamespace

from budgeted_cborg import (
    BudgetStop, CappedClient, attempt_identity, write_new,
)
from audit_controls.transport import provider_clients


STYLES = {"direct_api_quality", "grounding", "fitness", "subtype"}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def value_digest(value):
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, ensure_ascii=False, allow_nan=False,
        separators=(",", ":")).encode()).hexdigest()


def strict_json(text):
    def pairs(items):
        out = {}
        for key, value in items:
            if key in out:
                raise ValueError("duplicate JSON key: " + key)
            out[key] = value
        return out

    def invalid(value):
        raise ValueError("nonfinite JSON constant: " + value)

    def finite(value):
        number = float(value)
        if not math.isfinite(number):
            return invalid(value)
        return number

    return json.loads(text, object_pairs_hook=pairs, parse_constant=invalid, parse_float=finite)


def selected_value(job):
    from data_sheets_schema.duplicate_keys import duplicate_keys_in
    from data_sheets_schema.evaluation_context import (
        dataset_units, declared_class, load_document,
    )
    path = Path(job["input"])
    if duplicate_keys_in(path):
        raise ValueError("evaluation input has duplicate YAML keys")
    document, input_sha = load_document(path)
    if input_sha != job["input_sha256"]:
        raise ValueError("evaluation input changed")
    units = dict(dataset_units(document))
    if job["unit_path"] not in units:
        raise ValueError("selected evaluation unit is absent")
    unit = units[job["unit_path"]]
    kind = declared_class(unit)
    if kind is not None and kind != job["class_name"]:
        raise ValueError("selected unit class differs from the registered class")
    slot = job["slot"]
    if slot not in unit or unit[slot] is None or unit[slot] == "" or unit[slot] == [] or unit[slot] == {}:
        raise ValueError("selected slot is absent or empty")
    value = unit[slot]
    if value_digest(value) != job["value_sha256"]:
        raise ValueError("selected slot value changed")
    return value


def slot_instrument(job):
    from data_sheets_schema.evidence_score import (
        FITNESS_SYSTEM, SCORER_SYSTEM, slot_specification_snapshot,
    )
    from data_sheets_schema.form_defects import FORM_SUBTYPE_SYSTEM
    from data_sheets_schema.profiles import profile_named
    system = {"grounding": SCORER_SYSTEM, "fitness": FITNESS_SYSTEM,
              "subtype": FORM_SUBTYPE_SYSTEM}[job["style"]]
    result = {"system_sha256": hashlib.sha256(system.encode()).hexdigest()}
    if job["style"] == "grounding":
        result["bundle_sha256"] = sha(job["bundle"])
    else:
        snapshot = slot_specification_snapshot(
            job["class_name"], Path(job["schema_path"]),
            profile=profile_named(job["profile"]))
        result.update(schema=snapshot[0], specification=snapshot[3])
    return result


def _fitness_failure(job, value, instrument):
    from data_sheets_schema.form_defects import FormFailure, VALUE_CHARS
    path = Path(job["fitness_result"])
    if sha(path) != job["fitness_result_sha256"]:
        raise ValueError("conditional subtype parent changed")
    parent = strict_json(path.read_text())
    if parent.get("style") != "fitness":
        raise ValueError("subtype parent is not a fitness judgement")
    for key in ("input_sha256", "unit_path", "slot", "value_sha256"):
        if parent.get(key) != job[key]:
            raise ValueError("subtype parent selects a different " + key)
    if parent.get("job_id") != job["fitness_job_id"]:
        raise ValueError("subtype parent job differs")
    for key in ("schema", "specification"):
        if parent.get("instrument", {}).get(key) != instrument[key]:
            raise ValueError("subtype parent has a different " + key)
    judgement = parent["judgement"]
    validate_slot_json(judgement, "fitness")
    if judgement["failure"] != "form":
        raise ValueError("subtype is inapplicable to this fitness judgement")
    rendered = json.dumps(value, sort_keys=True, default=str)
    if len(rendered) > VALUE_CHARS:
        raise ValueError("subtype value would be truncated by the legacy classifier")
    return FormFailure(job["project"], job["slot"], rendered,
                       judgement["reason"], judgement["fitness"],
                       schema=instrument["schema"], specification=instrument["specification"])


def _invoke(manifest, job, client, attempt=None):
    """Use the instrument implementation for both preparation and execution."""
    style = job["style"]
    if style not in STYLES:
        raise ValueError("unknown API evaluation style")
    model = manifest["model"]["model"]
    if style == "direct_api_quality":
        from data_sheets_schema.evaluation.evaluate_d4d_llm import (
            D4DLLMEvaluator, LLMEvaluationConfig,
        )
        from data_sheets_schema.evaluation_context import load_context
        config = LLMEvaluationConfig(
            model=model, max_tokens=job["max_tokens"], stream=True,
            rubric_dir=Path(manifest["rubric_dir"]),
            prompts_dir=Path(manifest["prompts_dir"]),
            schema_path=Path(job["schema_path"]),
            error_dir=attempt / "errors" if attempt else Path("/unused-evaluation-capture-errors"),
            attempts_dir=attempt / "library_ratings" if attempt else None)
        evaluator = D4DLLMEvaluator(
            config, context=load_context(Path(job["context_path"])), client=client)
        result = evaluator.evaluate_file(
            Path(job["input"]), job["project"], job["method"], job["rubric"])
        return result[job["rubric"]], None

    from data_sheets_schema.evidence_score import LLMSlotScorer, LLMSlotFitnessScorer
    from data_sheets_schema.form_defects import FormSubtypeClassifier
    from data_sheets_schema.profiles import profile_named
    value = selected_value(job)
    instrument = slot_instrument(job)
    if instrument != job["instrument"]:
        raise ValueError("slot instrument differs from registration")
    options = dict(client=client, model=model, max_tokens=job["max_tokens"])
    # Fresh instances and caches make every repeat a new independent request.
    if attempt:
        options.update(cache_path=attempt / "slot_cache.jsonl")
    if style == "grounding":
        scorer = LLMSlotScorer(**options)
        result = asdict(scorer(project=job["project"], slot=job["slot"],
                               value=value, bundle=Path(job["bundle"]).read_text()))
    elif style == "fitness":
        scorer = LLMSlotFitnessScorer(
            **options, class_name=job["class_name"], schema_path=Path(job["schema_path"]),
            profile=profile_named(job["profile"]))
        result = asdict(scorer(project=job["project"], slot=job["slot"], value=value))
    else:
        scorer = FormSubtypeClassifier(
            **options, class_name=job["class_name"], schema_path=Path(job["schema_path"]),
            profile=profile_named(job["profile"]),
            schema=instrument["schema"], specification=instrument["specification"])
        subtype, reason = scorer(_fitness_failure(job, value, instrument))
        result = {"subtype": subtype, "reason": reason}
    if scorer.calls != 1 or scorer.memo_hits:
        raise ValueError("a new rating must contain exactly one independent judgement")
    return result, instrument


class _CapturedRequest(Exception):
    pass


class _CaptureMessages:
    def __init__(self):
        self.requests = []

    @contextmanager
    def stream(self, **request):
        self.requests.append(request)
        raise _CapturedRequest("offline request capture")
        yield  # pragma: no cover


def render_request(manifest, job):
    """Capture actual library rendering; never construct or contact a provider."""
    capture = _CaptureMessages()
    try:
        _invoke(manifest, job, SimpleNamespace(messages=capture))
    except Exception as exc:
        current = exc
        while current is not None and not isinstance(current, _CapturedRequest):
            current = current.__cause__ or current.__context__
        if current is None:
            raise
    if len(capture.requests) != 1:
        raise ValueError("offline preparation did not capture exactly one request")
    return capture.requests[0]


def validate_slot_json(value, style):
    if not isinstance(value, dict):
        raise ValueError("slot response must be one complete JSON object")
    key = {"grounding": "supported", "fitness": "fitness", "subtype": "subtype"}[style]
    required = {key, "reason"} | ({"failure"} if style == "fitness" else set())
    if set(value) != required:
        raise ValueError("slot response has missing or unexpected fields")
    if not isinstance(value["reason"], str) or not value["reason"].strip():
        raise ValueError("slot response requires a reason")
    if style == "subtype":
        from data_sheets_schema.form_defects import SUBTYPES
        if value[key] not in SUBTYPES:
            raise ValueError("unknown form subtype")
    elif type(value[key]) not in (int, float) or not math.isfinite(value[key]) or not 0 <= value[key] <= 1:
        raise ValueError("slot score must be finite and between zero and one")
    if style == "fitness" and value["failure"] not in {"none", "form", "target", "substance"}:
        raise ValueError("unknown fitness failure class")
    return value


class _Lifetime:
    def __init__(self):
        self.lock = threading.RLock()
        self.closed = False

    @contextmanager
    def guard(self, phase):
        with self.lock:
            if self.closed:
                raise BudgetStop("evaluation attempt evidence is frozen")
            yield

    def freeze(self):
        with self.lock:
            self.closed = True


class _JournalMessages:
    """Record original streamed events beneath the existing budget wrapper."""
    def __init__(self, messages, path, lifetime):
        self.messages, self.path, self.lifetime = messages, path, lifetime

    def count_tokens(self, **request):
        return self.messages.count_tokens(**request)

    @contextmanager
    def stream(self, **request):
        owner = self
        with self.messages.stream(**request) as source:
            class Stream:
                def __iter__(self):
                    for event in source:
                        value = event.model_dump(mode="json")
                        with owner.lifetime.guard("evidence"):
                            with owner.path.open("a") as out:
                                out.write(json.dumps(value, ensure_ascii=False) + "\n")
                        yield event

                def __getattr__(self, name):
                    return getattr(source, name)
            yield Stream()


class _CompleteMessages:
    def __init__(self, messages, style):
        self.messages, self.style = messages, style
        self.started = 0
        self.response = None
        self.judgement = None
        self.events = []

    @contextmanager
    def stream(self, **request):
        if self.started:
            raise BudgetStop("one evaluation job cannot issue another model request")
        self.started += 1
        owner = self
        with self.messages.stream(**request) as source:
            class Stream:
                def __iter__(self):
                    for event in source:
                        owner.events.append(event)
                        yield event

                def get_final_message(self):
                    response = source.get_final_message()
                    if response.stop_reason not in {"end_turn", "stop_sequence"}:
                        raise ValueError("provider did not finish the judgement")
                    owner.response = response
                    text = "".join(block.text for block in response.content if block.type == "text").strip()
                    # Fences are a representation, never partial JSON salvage.
                    match = re.fullmatch(r"```(?:json)?\s*\n(.*)\n```", text, re.S)
                    if match:
                        text = match[1]
                    value = strict_json(text)
                    if not isinstance(value, dict):
                        raise ValueError("evaluation response must be one JSON object")
                    if owner.style != "direct_api_quality":
                        owner.judgement = validate_slot_json(value, owner.style)
                    return response

                def __getattr__(self, name):
                    return getattr(source, name)
            yield Stream()


class _QualityMessages:
    """Use the shared stream watchdog before the quality library parses scores.

    The library receives the actual already observed events and response. It
    makes no second call. On timeout, only the guarded transport worker remains;
    no evaluator/parser worker can publish a late score after the attempt stops.
    """
    def __init__(self, complete):
        self.complete = complete

    @contextmanager
    def stream(self, **request):
        from data_sheets_schema.api_runner import _call_with_retry
        if set(request) - {"model", "max_tokens", "temperature", "system", "messages"}:
            raise ValueError("unregistered direct-quality request settings")
        response = _call_with_retry(
            SimpleNamespace(messages=self.complete),
            temperature=request.get("temperature"),
            **{key: request[key] for key in ("model", "max_tokens", "system", "messages")})
        observed = self.complete.events

        class Replay:
            def __iter__(self):
                return iter(observed)

            def get_final_message(self):
                return response

        yield Replay()


def close_client_bounded(client):
    """A provider socket close must not undo the stream's wall-clock bound."""
    state = {"completed": False}

    def close():
        try:
            client.close()
        except BaseException as exc:
            state["error_type"] = type(exc).__name__
        finally:
            state["completed"] = True

    worker = threading.Thread(target=close, name="evaluation-client-close", daemon=True)
    worker.start()
    worker.join(1)
    return dict(state)


def execute_job(context, *, client=None):
    """Called only after common registration, gate and ledger checks."""
    from data_sheets_schema import api_runner
    manifest, job, attempt = context.manifest, context.job, context.attempt
    context.verify()
    expected = strict_json(Path(job["expected_request"]).read_text())
    if render_request(manifest, job) != expected:
        raise ValueError("actual evaluator request differs from registration")
    if expected.get("model") != manifest["model"]["model"] or expected.get("max_tokens") != job["max_tokens"]:
        raise ValueError("request model or output ceiling differs")
    lifetime = _Lifetime()
    sdk = client
    if sdk is None:
        key = os.environ.get("CBORG_API_KEY")
        if not key:
            raise ValueError("CBORG_API_KEY is required")
        # Both token counting and evaluation streaming use this same client.
        sdk, _ = provider_clients(manifest, key)
    old_attempts = api_runner.MAX_ATTEMPTS
    old_deadline = api_runner.PHASE_WALL_CLOCK_SECONDS
    try:
        journal = SimpleNamespace(messages=_JournalMessages(sdk.messages, attempt / "response_events.jsonl", lifetime))
        capped = CappedClient(
            journal, ledger=context.ledger,
            attempt=attempt_identity(context.manifest_sha256, job["id"]),
            evidence=attempt / "requests", model=manifest["model"]["model"],
            prices=manifest["budget"]["prices_per_token"], verify=context.verify,
            initial_request=expected, mutation_guard=lifetime.guard)
        complete = _CompleteMessages(capped.messages, job["style"])
        api_runner.MAX_ATTEMPTS = 1
        api_runner.PHASE_WALL_CLOCK_SECONDS = job["deadline_seconds"]
        messages = _QualityMessages(complete) if job["style"] == "direct_api_quality" else complete
        result, instrument = _invoke(
            manifest, job, SimpleNamespace(messages=messages), attempt)
        if complete.started != 1 or complete.response is None:
            raise ValueError("evaluation lacks a completed independent request")
        if instrument is not None:
            # The subtype library shortens reasons for its historical cache.
            # Retain the entire valid new response in this condition's candidate.
            result = {
                "version": 1, "job_id": job["id"], "style": job["style"],
                **{key: job[key] for key in ("input_sha256", "unit_path", "slot", "value_sha256")},
                "instrument": instrument, "judgement": complete.judgement,
            }
        context.verify()
        capped.messages.require_active()
        candidate = Path(job["candidate"])
        write_new(candidate, result)
        return {
            "candidate_path": candidate,
            "validation": {"passed": True, "complete_response": True,
                           "independent_requests": 1, "style": job["style"]},
            "runtime": {"model": complete.response.model, "transport": "streaming",
                        "max_tokens": job["max_tokens"], "automatic_retries": 0},
            "evidence": {"response_events_sha256": sha(attempt / "response_events.jsonl"),
                         "expected_request_sha256": sha(job["expected_request"])},
        }
    finally:
        lifetime.freeze()
        api_runner.MAX_ATTEMPTS = old_attempts
        api_runner.PHASE_WALL_CLOCK_SECONDS = old_deadline
        if client is None and hasattr(sdk, "close"):
            write_new(attempt / "client_cleanup.json", close_client_bounded(sdk))
