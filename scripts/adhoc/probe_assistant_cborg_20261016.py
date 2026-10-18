#!/usr/bin/env python3
"""Probe the assistant's CBORG authentication and configured model count endpoint.

Inputs: CBORG_API_KEY environment variable and the checked-out API model config.
Output: JSON status/model/token count only; never credentials or source documents.
Serves #2088/#5050; 2026-10-16. No generation, retries or GitHub mutation.
"""
from __future__ import annotations

import json
import os

from anthropic import Anthropic, APIStatusError
from data_sheets_schema.api_runner import _model_settings


def main() -> int:
    key = os.environ.get("CBORG_API_KEY")
    if not key:
        print(json.dumps({"status": "missing_credential", "key_env": "CBORG_API_KEY"}))
        return 1
    model = _model_settings()["name"]
    try:
        with Anthropic(api_key=key, base_url="https://api.cborg.lbl.gov", max_retries=0,
                       timeout=45.0) as client:
            counted = client.messages.count_tokens(
                model=model,
                messages=[{"role": "user", "content": "Synthetic D4D assistant connectivity probe."}],
            )
    except APIStatusError as exc:
        print(json.dumps({"status": "provider_rejected", "http_status": exc.status_code,
                          "provider": "CBORG", "model": model}))
        return 1
    except Exception as exc:
        print(json.dumps({"status": "probe_failed", "error_type": type(exc).__name__,
                          "provider": "CBORG", "model": model}))
        return 1
    print(json.dumps({"status": "count_succeeded", "provider": "CBORG", "model": model,
                      "input_tokens": counted.input_tokens,
                      "generation_tested": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
