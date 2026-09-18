"""Actual evaluator, SDK streaming and Ledger integration; no network."""
from contextlib import contextmanager
from decimal import Decimal
import importlib.util
import json
from pathlib import Path
import sys
import threading
import time
from types import SimpleNamespace

import anthropic
import httpx
import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "notes/matched_cborg_2026-09-13"))
spec = importlib.util.spec_from_file_location("evaluation_api_under_test", Path(__file__).with_name("api.py"))
api = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api)
from budgeted_cborg import BudgetStop, Ledger
from tests.judge_fixtures import judge_reply

PRICES = {"input": "0.000005", "output": "0.000025",
          "cache_read": "0.0000005", "cache_write": "0.00000625"}


def setup_job(tmp_path, style="grounding", rubric="rubric10", kind="Dataset"):
    record = tmp_path / "record.yaml"
    record.write_text(f"{kind}:\n  id: urn:example:external\n  description: Public clinical data.\n")
    context_path = tmp_path / "context.json"
    context_path.write_text('{}\n')
    bundle = tmp_path / "source.txt"
    bundle.write_text("Public clinical data.\n")
    attempt = tmp_path / "attempt"
    attempt.mkdir()
    manifest = {
        "provider_base_url": "https://api.cborg.lbl.gov", "provider_context_policy": "headroom_bypass_v1",
        "model": {"model": "claude-opus-5"},
        "rubric_dir": str(ROOT / "data/rubric"),
        "prompts_dir": str(ROOT / "src/download/prompts"),
        "budget": {"prices_per_token": PRICES},
    }
    schema = "data_sheets_schema_core_all.yaml" if kind == "CoreDataset" else "data_sheets_schema_all.yaml"
    job = {
        "id": "example_" + style, "style": style, "rubric": rubric,
        "candidate": str(attempt / "output/candidate.json"),
        "project": "EXTERNAL_CLINICAL", "method": "manual", "input": str(record),
        "input_sha256": api.sha(record), "context_path": str(context_path),
        "class_name": kind, "profile": "neutral",
        "schema_path": str(ROOT / "src/data_sheets_schema/schema" / schema),
        "max_tokens": 32000 if style == "direct_api_quality" else 8000,
        "deadline_seconds": 10, "unit_path": "#", "slot": "description",
        "value_sha256": api.value_digest("Public clinical data."), "bundle": str(bundle),
        "expected_request": str(tmp_path / "request.json"),
    }
    if style != "direct_api_quality":
        job["instrument"] = api.slot_instrument(job)
    if style == "subtype":
        job["fitness_job_id"] = "earlier_fitness"
        parent = tmp_path / "fitness.json"
        parent.write_text(json.dumps({
            "version": 1, "job_id": job["fitness_job_id"], "style": "fitness",
            **{key: job[key] for key in ("input_sha256", "unit_path", "slot", "value_sha256")},
            "instrument": api.slot_instrument(dict(job, style="fitness")),
            "judgement": {"fitness": .5, "failure": "form", "reason": "A documented form defect."},
        }))
        job.update(fitness_result=str(parent), fitness_result_sha256=api.sha(parent))
    pins = {str(p): api.sha(p) for p in (record, context_path, bundle)}
    def verify():
        assert all(api.sha(p) == digest for p, digest in pins.items())
    request = api.render_request(manifest, job)
    Path(job["expected_request"]).write_text(json.dumps(request))
    pins[job["expected_request"]] = api.sha(job["expected_request"])
    ledger = Ledger(tmp_path / "billing.json", manifest_sha256="registered", total_cap=400, attempt_cap=5)
    return SimpleNamespace(manifest=manifest, manifest_sha256="registered", job=job,
                           attempt=attempt, ledger=ledger, verify=verify)


def mock_sdk(context, *, defect=None, block=None):
    calls = []
    def respond(request):
        body = json.loads(request.content)
        calls.append((request.url.path, body))
        if request.url.path.endswith("/count_tokens"):
            return httpx.Response(200, json={"input_tokens": 500})
        if block is not None:
            block.wait(3)
        if defect == "transport":
            raise httpx.ConnectError("offline failure")
        style = context.job["style"]
        if style == "direct_api_quality":
            contract = json.loads(body["messages"][0]["content"].split("```json\n")[1].split("\n```")[0])
            value = judge_reply(contract, context.job["rubric"], "EXTERNAL_CLINICAL", "manual")
            if defect == "arithmetic":
                value["overall_score"]["total_points"] = 999
        elif style == "subtype":
            value = {"subtype": "other", "reason": "Another form defect."}
        else:
            value = {"supported": 1, "reason": "Source says this."} if style == "grounding" else {
                "fitness": 1, "failure": "none", "reason": "Appropriate description."}
            if defect == "domain":
                value["supported" if style == "grounding" else "fitness"] = True
        text = json.dumps(value)
        if defect == "json":
            text = text[:-1]
        if defect == "duplicate":
            if style == "direct_api_quality":
                text = text.replace('"total_points": 0', '"total_points": 99, "total_points": 0', 1)
            else:
                text = '{"supported":0,"supported":1,"reason":"duplicate"}'
        if defect == "trailing":
            text = "```json\n" + text + "\n```\nUnregistered trailing text."
        events = [
            {"type": "message_start", "message": {"id": "msg_offline", "type": "message", "role": "assistant",
                "model": "wrong" if defect == "model" else "claude-opus-5", "content": [],
                "stop_reason": None, "stop_sequence": None,
                "usage": {"input_tokens": 500, "output_tokens": 0}}},
            {"type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}},
            {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": text}},
            {"type": "content_block_stop", "index": 0},
            {"type": "message_delta", "delta": {"stop_reason": "max_tokens" if defect == "max_tokens" else "end_turn",
                "stop_sequence": None}, "usage": {"output_tokens": 100}},
        ]
        if defect != "stop":
            events.append({"type": "message_stop"})
        wire = "".join("event: " + e["type"] + "\ndata: " + json.dumps(e) + "\n\n" for e in events)
        return httpx.Response(200, content=wire, headers={"content-type": "text/event-stream"})
    sdk = anthropic.Anthropic(api_key="offline", base_url="https://offline.invalid", max_retries=0,
                             http_client=httpx.Client(transport=httpx.MockTransport(respond)))
    return sdk, calls


@pytest.mark.parametrize("style", ["grounding", "fitness", "subtype", "direct_api_quality"])
@pytest.mark.parametrize("kind", ["Dataset", "CoreDataset"])
def test_real_library_request_stream_and_accounting(tmp_path, style, kind):
    context = setup_job(tmp_path, style, kind=kind)
    sdk, calls = mock_sdk(context)
    try:
        result = api.execute_job(context, client=sdk)
    finally:
        sdk.close()
    assert len(calls) == 2
    assert calls[0][0].endswith("/count_tokens") and calls[1][0].endswith("/messages")
    sent = dict(calls[1][1]); assert sent.pop("stream") is True
    assert sent == json.loads(Path(context.job["expected_request"]).read_text())
    candidate = json.loads(result["candidate_path"].read_text())
    if style == "direct_api_quality":
        assert candidate["metadata"]["response_transport"] == "streaming"
        assert candidate["metadata"]["d4d_file_hash"] == context.job["input_sha256"]
    else:
        assert candidate["instrument"] == context.job["instrument"]
        assert candidate["value_sha256"] == context.job["value_sha256"]
        assert candidate["judgement"]["reason"]
    state = json.loads(context.ledger.path.read_text())
    assert len(state["requests"]) == 1 and state["requests"][0]["status"] == "settled"
    assert Decimal(state["requests"][0]["cost_usd"]) == Decimal("0.005")
    assert len(list((context.attempt / "requests").glob("*/response.json"))) == 1
    assert len((context.attempt / "response_events.jsonl").read_text().splitlines()) >= 6


@pytest.mark.parametrize("defect", ["stop", "max_tokens", "json", "domain", "duplicate", "model", "transport"])
def test_failed_slot_retains_evidence_and_never_retries(tmp_path, defect):
    context = setup_job(tmp_path)
    sdk, calls = mock_sdk(context, defect=defect)
    try:
        with pytest.raises(Exception):
            api.execute_job(context, client=sdk)
    finally:
        sdk.close()
    assert len(calls) == 2
    assert not Path(context.job["candidate"]).exists()
    row, = json.loads(context.ledger.path.read_text())["requests"]
    assert row["status"] == ("pending" if defect in {"stop", "transport"} else
                              "protocol_failure" if defect == "model" else "settled")
    if row["status"] == "settled":
        assert Decimal(row["cost_usd"]) == Decimal("0.005")


@pytest.mark.parametrize("defect", ["stop", "max_tokens", "arithmetic", "transport", "duplicate", "trailing", "json"])
def test_quality_canary_failure_preserves_costs_without_second_call(tmp_path, defect):
    context = setup_job(tmp_path, "direct_api_quality", rubric="rubric20")
    sdk, calls = mock_sdk(context, defect=defect)
    try:
        with pytest.raises(Exception):
            api.execute_job(context, client=sdk)
    finally:
        sdk.close()
    assert len(calls) == 2 and not Path(context.job["candidate"]).exists()
    assert len(json.loads(context.ledger.path.read_text())["requests"]) == 1


def test_drift_is_refused_before_provider_or_token_count(tmp_path):
    context = setup_job(tmp_path)
    Path(context.job["input"]).write_text("id: changed\n")
    sdk, calls = mock_sdk(context)
    try:
        with pytest.raises(AssertionError):
            api.execute_job(context, client=sdk)
    finally:
        sdk.close()
    assert calls == [] and not context.ledger.path.exists()


@pytest.mark.parametrize("style", ["grounding", "direct_api_quality"])
def test_deadline_freezes_late_worker_without_late_settlement(tmp_path, style):
    context = setup_job(tmp_path, style)
    context.job["deadline_seconds"] = .05
    block = threading.Event()
    sdk, calls = mock_sdk(context, block=block)
    try:
        with pytest.raises(Exception, match="wall clock"):
            api.execute_job(context, client=sdk)
        frozen = context.ledger.path.read_bytes()
        assert json.loads(frozen)["requests"][0]["status"] == "pending"
        block.set()
        time.sleep(.15)
        assert context.ledger.path.read_bytes() == frozen
        assert not Path(context.job["candidate"]).exists()
        assert not (context.attempt / "response_events.jsonl").exists()
        assert len(calls) == 2
    finally:
        block.set()
        sdk.close()


def test_remaining_sequence_allocation_is_still_enforced(tmp_path):
    context = setup_job(tmp_path)
    with context.ledger.transaction() as state:
        state["requests"] = [{"id": "historical", "attempt": "prior", "status": "settled", "cost_usd": "399.99"}]
    sdk, calls = mock_sdk(context)
    try:
        with pytest.raises(BudgetStop, match="remaining budget"):
            api.execute_job(context, client=sdk)
    finally:
        sdk.close()
    assert len(calls) == 1 and calls[0][0].endswith("count_tokens")
    assert len(json.loads(context.ledger.path.read_text())["requests"]) == 1
    assert not Path(context.job["candidate"]).exists()


def test_production_client_cleanup_cannot_undo_wall_clock_bound(tmp_path, monkeypatch):
    context = setup_job(tmp_path, "direct_api_quality")
    context.job["deadline_seconds"] = .05
    response_release, close_release = threading.Event(), threading.Event()
    sdk, calls = mock_sdk(context, block=response_release)
    original_close = sdk.close
    sdk.close = lambda: close_release.wait(5)
    monkeypatch.setenv("CBORG_API_KEY", "offline")
    monkeypatch.setattr(api, "cborg_client", lambda *args, **kwargs: sdk)
    started = time.monotonic()
    try:
        with pytest.raises(Exception, match="wall clock"):
            api.execute_job(context)
        assert time.monotonic() - started < 2
        cleanup = json.loads((context.attempt / "client_cleanup.json").read_text())
        assert cleanup == {"completed": False}
        frozen = context.ledger.path.read_bytes()
        close_release.set(); response_release.set()
        time.sleep(.15)
        assert context.ledger.path.read_bytes() == frozen
        assert not Path(context.job["candidate"]).exists()
        assert len(calls) == 2
    finally:
        close_release.set(); response_release.set()
        original_close()


@pytest.mark.parametrize("mutation", ["failure", "schema", "slot", "input_sha256", "job_id"])
def test_subtype_parent_drift_or_inapplicability_precedes_provider(tmp_path, mutation):
    context = setup_job(tmp_path, "subtype", kind="CoreDataset")
    parent_path = Path(context.job["fitness_result"])
    parent = json.loads(parent_path.read_text())
    if mutation == "failure":
        parent["judgement"]["failure"] = "substance"
    elif mutation == "schema":
        parent["instrument"]["schema"] = "a-different-instrument"
    else:
        parent[mutation] = "different"
    parent_path.write_text(json.dumps(parent))
    # Even rebinding the parent file hash cannot conceal wrong parent identity.
    context.job["fitness_result_sha256"] = api.sha(parent_path)
    sdk, calls = mock_sdk(context)
    try:
        with pytest.raises(ValueError, match="subtype"):
            api.execute_job(context, client=sdk)
    finally:
        sdk.close()
    assert calls == []


def test_repeated_slots_use_fresh_ratings_on_one_shared_ledger(tmp_path):
    contexts = []
    for rating in (1, 2):
        folder = tmp_path / str(rating); folder.mkdir()
        context = setup_job(folder, "fitness", kind="CoreDataset")
        context.job["id"] += "_rating" + str(rating)
        if contexts:
            context.ledger = contexts[0].ledger
        sdk, calls = mock_sdk(context)
        try:
            api.execute_job(context, client=sdk)
        finally:
            sdk.close()
        assert len(calls) == 2
        contexts.append(context)
    rows = json.loads(contexts[0].ledger.path.read_text())["requests"]
    assert len(rows) == len({row["attempt"] for row in rows}) == len({row["id"] for row in rows}) == 2
    assert sum(Decimal(row["cost_usd"]) for row in rows) == Decimal("0.01")
