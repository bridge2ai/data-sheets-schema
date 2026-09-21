"""Experiment transport: conservative request admission and original evidence.

This controller never changes a generation prompt or token ceiling to fit a
budget. An unaffordable next phase stops the attempt. Unknown charges retain
their reservation and stop further requests. Prices are catalogue estimates,
not an assertion about the reconciled CBORG invoice.
"""
from contextlib import contextmanager, nullcontext
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
import math
import time
from pathlib import Path
import uuid

from filelock import FileLock

CBORG_ENDPOINTS = frozenset({'https://api.cborg.lbl.gov', 'https://api-local.cborg.lbl.gov'})


class BudgetStop(RuntimeError):
    pass


#: Ledger basis for a stalled paid request that a registered stall policy
#: counted at its whole reservation inside one attempt (#2150). It mirrors the
#: offline user-authorized debit: the provider fee stays unknown.
STALL_DEBIT_BASIS = "registered_stall_policy_full_reservation_debit"


def retryable_count_error(exc):
    """A token-count failure that is safe to repeat: counting is free and
    idempotent, so a timeout, a dropped connection or a provider 5xx carries
    no charge ambiguity. Anything else (a 4xx, a bad count) is not retried."""
    import anthropic
    return isinstance(exc, (anthropic.APIConnectionError, anthropic.InternalServerError))


def provider_context_headers(manifest):
    """Select only a registered, documented provider control, never arbitrary headers."""
    if "provider_context_policy" not in manifest:
        return {}  # Historical registrations retain their original transport.
    if manifest["provider_context_policy"] != "headroom_bypass_v1":
        raise BudgetStop("unknown registered provider context policy")
    return {"x-headroom-bypass": "true"}


def provider_context_evidence(manifest):
    return {"policy": manifest.get("provider_context_policy", "legacy_provider_default_unpinned"),
            "requested_headers": provider_context_headers(manifest),
            "provider_behavior_independently_observed": False}


def cborg_client(manifest, api_key, *, max_retries, http_client=None):
    """Use the same registered headers for generation and SDK token counting."""
    import anthropic
    kwargs = {"api_key": api_key, "base_url": manifest["provider_base_url"],
              "max_retries": max_retries, "default_headers": provider_context_headers(manifest)}
    if http_client is not None:
        kwargs["http_client"] = http_client
    return anthropic.Anthropic(**kwargs)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def write_new(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")


def now():
    return datetime.now(timezone.utc).isoformat()


def money(value):
    return Decimal(str(value))


class Ledger:
    def __init__(self, path, *, manifest_sha256, total_cap=200, attempt_cap=5,
                 attempt_caps_usd=None):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = FileLock(str(self.path) + ".lock", timeout=0)
        self.identity = {"manifest_sha256": manifest_sha256,
                         "additional_cap_usd": str(total_cap), "attempt_cap_usd": str(attempt_cap)}
        self.total_cap, self.attempt_cap = money(total_cap), money(attempt_cap)
        if not all(value.is_finite() and value > 0 for value in (self.total_cap, self.attempt_cap)):
            raise BudgetStop("budget caps must be finite and positive")
        if attempt_caps_usd is None:
            attempt_caps_usd = {}
        if not isinstance(attempt_caps_usd, dict):
            raise BudgetStop("attempt cap overrides must be a mapping")
        self.attempt_caps_usd = {}
        for attempt, value in attempt_caps_usd.items():
            if not isinstance(attempt, str) or not attempt or attempt.strip() != attempt:
                raise BudgetStop("attempt cap override lacks an exact attempt identity")
            try:
                cap = money(value)
            except (ArithmeticError, TypeError, ValueError) as exc:
                raise BudgetStop("attempt cap override is not a valid amount") from exc
            if not cap.is_finite() or cap <= 0 or cap > self.total_cap:
                raise BudgetStop("attempt cap override must be positive and within the sequence cap")
            self.attempt_caps_usd[attempt] = cap
        if self.attempt_caps_usd:
            self.identity["attempt_caps_usd"] = {
                attempt: str(cap) for attempt, cap in sorted(self.attempt_caps_usd.items())}

    def limit_for_attempt(self, attempt):
        return self.attempt_caps_usd.get(attempt, self.attempt_cap)

    @contextmanager
    def transaction(self):
        with self.lock:
            state = json.loads(self.path.read_bytes()) if self.path.exists() else {**self.identity, "requests": []}
            if (any(state.get(k) != v for k, v in self.identity.items())
                    or state.get("attempt_caps_usd", {}) != self.identity.get("attempt_caps_usd", {})):
                raise BudgetStop("ledger registration or budget changed")
            yield state
            temporary = self.path.with_suffix(".tmp")
            temporary.write_text(json.dumps(state, indent=2) + "\n")
            temporary.replace(self.path)

    def reserve(self, attempt, estimate, request_sha256):
        estimate = money(estimate)
        if not estimate.is_finite() or estimate <= 0:
            raise BudgetStop("request reservation must be finite and positive")
        with self.transaction() as state:
            self._check_stopped(state, attempt)
            if any(row["status"] != "settled" for row in state["requests"]):
                raise BudgetStop("an earlier charge is pending or unknown; reconcile before continuing")
            total = sum((money(row["cost_usd"]) for row in state["requests"]), Decimal(0))
            used = sum((money(row["cost_usd"]) for row in state["requests"] if row["attempt"] == attempt), Decimal(0))
            cap = self.limit_for_attempt(attempt)
            if estimate <= 0 or total + estimate > self.total_cap or used + estimate > cap:
                reason = f"request reserve ${estimate} exceeds remaining budget: attempt ${cap-used}, sequence ${self.total_cap-total}"
                state.setdefault("stopped_attempts", {})[attempt] = {
                    "stopped_at": now(), "reason": reason,
                    "denied_request_sha256": request_sha256,
                    "denied_reservation_usd": str(estimate), "paid_request": False}
                ticket = None
            else:
                ticket = uuid.uuid4().hex
                state["requests"].append({"id": ticket, "attempt": attempt,
                    "request_sha256": request_sha256, "reserved_at": now(),
                    "reserved_usd": str(estimate), "attempt_cap_usd": str(cap), "status": "pending"})
        # Raise after the transaction commits, or the stop event is lost.
        if ticket is None:
            raise BudgetStop(reason)
        return ticket

    @staticmethod
    def _check_stopped(state, attempt):
        stop = state.get("stopped_attempts", {}).get(attempt)
        if stop:
            raise BudgetStop(f"attempt previously stopped: {stop['reason']}")

    def check_attempt(self, attempt):
        with self.transaction() as state:
            self._check_stopped(state, attempt)

    def require_resolved(self, attempt):
        with self.transaction() as state:
            self._check_stopped(state, attempt)
            if any(row["status"] != "settled" for row in state["requests"]):
                raise BudgetStop("an earlier charge is pending or unknown; reconcile before continuing")

    def stop_attempt(self, attempt, reason):
        with self.transaction() as state:
            state.setdefault("stopped_attempts", {}).setdefault(
                attempt, {"stopped_at": now(), "reason": reason})

    def continue_from(self, checkpoint, *, expected_sha256, expected_cost_usd):
        """Carry charges exactly once without changing the allocation or default cap.

        Any per-attempt exception belongs to the new registration's exact job
        identity; the prior checkpoint remains the evidence for its own caps.
        """
        raw = Path(checkpoint).read_bytes()
        if digest(raw) != expected_sha256:
            raise BudgetStop("prior billing checkpoint changed")
        previous = json.loads(raw)
        if any(previous.get(k) != self.identity[k] for k in ("additional_cap_usd", "attempt_cap_usd")):
            raise BudgetStop("prior billing checkpoint has different budget caps")
        if not isinstance(previous.get("manifest_sha256"), str) or not previous["manifest_sha256"]:
            raise BudgetStop("prior billing checkpoint lacks its registration identity")
        rows = previous.get("requests")
        if not isinstance(rows, list) or any(not isinstance(row, dict) or row.get("status") != "settled" for row in rows):
            raise BudgetStop("prior billing contains an unresolved charge")
        identifiers = [row.get("id") for row in rows]
        if any(not isinstance(i, str) or not i for i in identifiers) or len(set(identifiers)) != len(identifiers):
            raise BudgetStop("prior billing request identities are missing or duplicated")
        costs = [money(row.get("cost_usd", "NaN")) for row in rows]
        if any(not cost.is_finite() or cost < 0 for cost in costs):
            raise BudgetStop("prior billing charge is invalid")
        total = sum(costs, Decimal(0))
        expected = money(expected_cost_usd)
        if not expected.is_finite() or total != expected or total > self.total_cap:
            raise BudgetStop("prior billing total differs from the registered continuation")
        identity = {"checkpoint_sha256": expected_sha256,
                    "manifest_sha256": previous["manifest_sha256"],
                    "cost_usd": str(total), "requests": len(rows)}
        with self.transaction() as state:
            if "continued_from" in state:
                if state["continued_from"] != identity or state["requests"][:len(rows)] != rows:
                    raise BudgetStop("continued billing history changed")
            else:
                if state["requests"]:
                    raise BudgetStop("cannot replace existing requests with a prior checkpoint")
                state.update(continued_from=identity, requests=rows)

    def settle(self, ticket, actual, *, response_sha256, usage, protocol_failure=None):
        actual = money(actual)
        if not actual.is_finite() or actual < 0:
            raise BudgetStop("invalid response charge; reservation retained")
        with self.transaction() as state:
            row = next(row for row in state["requests"] if row["id"] == ticket)
            if row["status"] != "pending":
                raise BudgetStop("charge already settled")
            status = "protocol_failure" if protocol_failure else (
                "settled" if actual <= money(row["reserved_usd"]) else "over_reservation")
            row.update(status=status,
                       cost_usd=str(actual), settled_at=now(), response_sha256=response_sha256, usage=usage)
            if protocol_failure:
                row["protocol_failure"] = protocol_failure
        if protocol_failure:
            raise BudgetStop(protocol_failure)
        if row["status"] != "settled":
            raise BudgetStop("observed charge exceeded its conservative reservation; stop and reconcile")

    def debit_unconfirmed(self, ticket, *, maximum, evidence):
        """Count a stalled request at its whole reservation and keep going (#2150).

        The reservation is an upper bound on the provider fee, so the budget
        can only be over-counted. Nothing is released and no provider charge
        is asserted. At most `maximum` such debits are allowed per attempt;
        beyond that the row stays pending and the attempt stops as before.
        """
        if type(maximum) is not int or maximum < 0:
            raise BudgetStop("stall allowance must be a non-negative whole number")
        with self.transaction() as state:
            row = next(row for row in state["requests"] if row["id"] == ticket)
            if row["status"] != "pending":
                raise BudgetStop("charge already settled")
            prior = sum(1 for other in state["requests"] if other["attempt"] == row["attempt"]
                        and other.get("settlement_basis") == STALL_DEBIT_BASIS)
            allowed = prior < maximum
            if allowed:
                row.update(status="settled", cost_usd=row["reserved_usd"], settled_at=now(),
                           settlement_basis=STALL_DEBIT_BASIS, stall_index=prior + 1,
                           stall_evidence=evidence, provider_charge_confirmed=False,
                           provider_charge_usd=None, provider_usage_is_final=False,
                           released_excess_reservation_usd="0")
        if not allowed:
            raise BudgetStop("registered stall allowance is exhausted; reservation retained")
        return prior + 1


class CappedMessages:
    def __init__(self, client, *, ledger, attempt, evidence, model, prices, verify, initial_request=None,
                 mutation_guard=None, count_attempts=1, count_pause=None):
        if type(count_attempts) is not int or not 1 <= count_attempts <= 5:
            raise BudgetStop("token-count attempts must be a whole number from 1 to 5")
        self.count_attempts = count_attempts
        self.count_pause = count_pause or time.sleep
        self.count_retries = 0
        self.client, self.ledger, self.attempt = client, ledger, attempt
        self.evidence, self.model, self.prices = Path(evidence), model, prices
        self.verify = verify
        self.initial_request = initial_request
        self.requests_started = 0
        self.stop_reason = None
        self.mutation_guard = mutation_guard or (lambda phase: nullcontext())

    def prepare(self, request):
        if self.stop_reason is not None:
            raise BudgetStop(f"attempt previously stopped: {self.stop_reason}")
        with self.stopping_on_error():
            with self.mutation_guard("admit"):
                self.ledger.check_attempt(self.attempt)
            return self._prepare(request)

    @contextmanager
    def stopping_on_error(self):
        try:
            yield
        except Exception as exc:
            # The runner may catch repair/report exceptions and continue.
            # Preserve the first refusal across calls AND controller restarts.
            if self.stop_reason is None:
                self.stop_reason = str(exc) if isinstance(exc, BudgetStop) else type(exc).__name__
            with self.mutation_guard("settle"):
                self.ledger.stop_attempt(self.attempt, self.stop_reason)
            raise

    def require_active(self):
        if self.stop_reason is not None:
            raise BudgetStop(self.stop_reason)
        self.ledger.require_resolved(self.attempt)

    def _prepare(self, request):
        self.verify()
        if request.get("model") != self.model:
            raise BudgetStop("model differs from registration")
        if self.requests_started == 0 and self.initial_request is not None and request != self.initial_request:
            raise BudgetStop("first request differs from the registered original request")
        # Only the registered five-minute cache rate is available here.
        def check(value):
            if isinstance(value, dict):
                cache = value.get("cache_control")
                if cache and cache.get("ttl") not in (None, "5m"):
                    raise BudgetStop("unregistered cache lifetime")
                for item in value.values():
                    check(item)
            elif isinstance(value, list):
                for item in value:
                    check(item)
        check(request)
        count_args = {k: v for k, v in request.items() if k in {"model", "system", "messages", "tools", "tool_choice", "thinking"}}
        count = self.count_tokens(count_args)
        if type(count) is not int or count < 0:
            raise BudgetStop("provider returned no usable input count")
        ceiling = request.get("max_tokens")
        if type(ceiling) is not int or ceiling <= 0:
            raise BudgetStop("request lacks an output token ceiling")
        # Reserve all counted input at the larger uncached/cache-write price,
        # with 20% + 1024 tokens margin. Never assume a cache hit in advance.
        input_bound = math.ceil(count * 1.2) + 1024
        estimate = (input_bound * max(money(self.prices["input"]), money(self.prices["cache_write"]))
                    + ceiling * money(self.prices["output"]))
        raw = (json.dumps(request, sort_keys=True, ensure_ascii=False) + "\n").encode()
        # The native runtime supplies a short lifecycle lock here, after the
        # network token count. Shutdown can then close admission atomically
        # without blocking on a provider response (#1768).
        with self.mutation_guard("admit"):
            try:
                ticket = self.ledger.reserve(self.attempt, estimate, digest(raw))
            except BudgetStop as exc:
                folder = self.evidence.parent / "denied_requests" / uuid.uuid4().hex
                folder.mkdir(parents=True, exist_ok=False)
                (folder / "request.json").write_bytes(raw)
                write_new(folder / "admission.json", {
                    "input_count": count, "input_bound": input_bound,
                    "output_ceiling": ceiling, "required_reservation_usd": str(estimate),
                    "denied_at": now(), "reason": str(exc), "paid_request": False})
                raise
            self.requests_started += 1
            folder = self.evidence / ticket
            folder.mkdir(parents=True, exist_ok=False)
            (folder / "request.json").write_bytes(raw)
            write_new(folder / "admission.json", {"input_count": count, "input_bound": input_bound,
                      "output_ceiling": ceiling, "reserved_usd": str(estimate), "token_count_at": now()})
        return ticket, folder

    def count_tokens(self, fields):
        """The provider's input count, repeated only under a registered
        allowance and only for failures that cannot have cost anything."""
        for attempt in range(1, self.count_attempts + 1):
            try:
                return self.client.messages.count_tokens(**fields).input_tokens
            except Exception as exc:
                if attempt == self.count_attempts or not retryable_count_error(exc):
                    raise
                self.count_retries += 1
                self.evidence.mkdir(parents=True, exist_ok=True)
                with (self.evidence / "count_retries.jsonl").open("a", encoding="utf-8") as out:
                    out.write(json.dumps({"at": now(), "failed_try": attempt,
                                          "error_type": type(exc).__name__}) + "\n")
                self.count_pause(min(2 ** attempt, 10))

    def debit_stall(self, ticket, *, maximum, evidence):
        with self.mutation_guard("settle"):
            return self.ledger.debit_unconfirmed(ticket, maximum=maximum, evidence=evidence)

    def finish(self, ticket, folder, response, *, stream_complete=None):
        with self.stopping_on_error(), self.mutation_guard("settle"):
            return self._finish(ticket, folder, response, stream_complete=stream_complete)

    def _finish(self, ticket, folder, response, *, stream_complete=None):
        value = response.model_dump(mode="json")
        write_new(folder / "response.json", value)
        terminal_reasons = {"end_turn", "max_tokens", "stop_sequence", "tool_use", "pause_turn",
                            "refusal", "model_context_window_exceeded"}
        if stream_complete is False or value.get("stop_reason") not in terminal_reasons:
            raise BudgetStop("response completion is unverified; original response and reservation retained")
        usage = value.get("usage") or {}
        if not all(type(usage.get(k)) is int and usage[k] >= 0 for k in ("input_tokens", "output_tokens")):
            raise BudgetStop("response usage is missing; reservation retained")
        fields = {"input": "input_tokens", "output": "output_tokens",
                  "cache_read": "cache_read_input_tokens", "cache_write": "cache_creation_input_tokens"}
        if any(usage.get(field) is not None and (type(usage[field]) is not int or usage[field] < 0)
               for field in fields.values()):
            raise BudgetStop("invalid response token counts; reservation retained")
        actual = sum((money(usage.get(field) or 0) * money(self.prices[rate])
                      for rate, field in fields.items()), Decimal(0))
        failure = ("returned model differs from the registered identifier; response and estimated charge retained"
                   if value.get("model") != self.model else None)
        self.ledger.settle(ticket, actual, response_sha256=digest((folder / "response.json").read_bytes()),
                           usage=usage, protocol_failure=failure)
        return response

    def create(self, **request):
        with self.stopping_on_error():
            ticket, folder = self.prepare(request)
            return self.finish(ticket, folder, self.client.messages.create(**request))

    @contextmanager
    def stream(self, **request):
        with self.stopping_on_error(), self._stream(**request) as observed:
            yield observed

    @contextmanager
    def _stream(self, **request):
        ticket, folder = self.prepare(request)
        owner = self
        with self.client.messages.stream(**request) as wrapped:
            class ObservedStream:
                result = None
                saw_stop = False
                exhausted = False

                def __iter__(self):
                    for event in wrapped:
                        if getattr(event, "type", None) == "message_stop":
                            self.saw_stop = True
                        yield event
                    self.exhausted = True

                def get_final_message(self):
                    if self.result is None:
                        # Even a caller that goes directly to the final message
                        # must establish completeness through the observed stream.
                        if not self.exhausted:
                            for _ in self:
                                pass
                        self.result = owner.finish(ticket, folder, wrapped.get_final_message(),
                                                   stream_complete=self.saw_stop)
                    return self.result

                def __getattr__(self, name):
                    return getattr(wrapped, name)

            yield ObservedStream()


class CappedClient:
    def __init__(self, client, **kwargs):
        self.messages = CappedMessages(client, **kwargs)


def registered_attempt_caps(manifest, manifest_sha256):
    """Bind optional per-job caps to exact attempts in this registration."""
    budget = manifest["budget"]
    per_job = budget.get("per_job_attempt_usd", {})
    if not isinstance(per_job, dict):
        raise BudgetStop("registered per-job attempt caps must be a mapping")
    caps = {}
    if per_job:
        jobs = manifest.get("generation", {}).get("jobs", [])
        if not isinstance(jobs, list) or any(not isinstance(job, dict) for job in jobs):
            raise BudgetStop("per-job caps require a valid registered job roster")
        identifiers = [job.get("id") for job in jobs]
        if (any(not isinstance(name, str) or not name for name in identifiers)
                or len(set(identifiers)) != len(identifiers)):
            raise BudgetStop("per-job caps require unique registered job identities")
        if any(name not in identifiers for name in per_job):
            raise BudgetStop("attempt cap override names an unregistered job")
        caps = {attempt_identity(manifest_sha256, name): cap for name, cap in per_job.items()}
    return caps


def open_ledger(manifest, manifest_sha256):
    """Use the hash-bound sequence ledger even if the registration is copied."""
    budget = manifest["budget"]
    location = budget.get("ledger_path")
    if not isinstance(location, str) or not location:
        raise BudgetStop("registration lacks a canonical sequence ledger path")
    path = Path(location)
    if not path.is_absolute() or str(path.resolve()) != location:
        raise BudgetStop("registered sequence ledger path is not absolute and canonical")
    caps = registered_attempt_caps(manifest, manifest_sha256)
    ledger = Ledger(path, manifest_sha256=manifest_sha256,
                    total_cap=budget["additional_usd"], attempt_cap=budget["per_attempt_usd"],
                    attempt_caps_usd=caps)
    prior = budget.get("continuation")
    if prior is not None:
        if manifest["pinned_files"].get(prior["checkpoint"]) != prior["sha256"]:
            raise BudgetStop("prior billing checkpoint is not pinned by this registration")
        ledger.continue_from(prior["checkpoint"], expected_sha256=prior["sha256"],
                             expected_cost_usd=prior["cost_usd"])
    return ledger


def attempt_identity(manifest_sha256, job):
    return f"{manifest_sha256}:{job}"
