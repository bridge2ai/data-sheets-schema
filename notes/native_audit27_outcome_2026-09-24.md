# CHORUS native audit27 transport outcome — September 24, 2026

Audit27 stopped before its first worker finished. It produced no accepted
scientific audit. This note records the transport observations published in
the approved [issue #1849 update](https://github.com/bridge2ai/data-sheets-schema/issues/1849#issuecomment-5827577052).
The date follows the operator's Pacific calendar; the update was published
on September 25 UTC.

The execution used commit
[`98cae7e1eb6949daaba4c24e35edfd1123679d9e`](https://github.com/bridge2ai/data-sheets-schema/commit/98cae7e1eb6949daaba4c24e35edfd1123679d9e).
It used the registered bounded retry policy described in the
[audit controls](matched_cborg_2026-09-13/audit_controls/README.md).
The earlier [retry history](native_audit_retry_2026-09-21.md) remains a record
of its own attempts and approvals.

## Observations

| Requests | Outcome | Reservation-to-settlement/stop interval |
| --- | --- | --- |
| First eight | HTTP 200, completed | 3.682–11.444 seconds |
| Next request and six retries | HTTP 500 on all seven | 272.585–276.757 seconds |

The seven failed requests had identical canonical and native-wire bytes.
The repeated request counted 112,946 input tokens and allowed 64,000 output
tokens. Its local read/complete-response limit was 1,200 seconds.

The controller retried under the registered bounded policy, then stopped
when its automatic-debit allowance was exhausted. Runtime closure and a
complete evidence freeze were verified. The first worker did not finish;
these observations do not establish scientific acceptance.

A subsequent read-only CBORG catalogue check listed `stream_timeout: 270.0`
for the registered `claude-opus-5` Vertex route. At that check the route was
reachable, and its registered model capabilities and prices were unchanged.

## Interpretation and next step

The timing is consistent with an upstream timeout. It does not establish
the historical server configuration, deployed LiteLLM version, or exact
terminating component. The intervals include local bookkeeping. The failed
responses have no captured SSE; error bodies were deliberately not drained.
These observations do not establish final usage, provider billing, or the
earlier empty-success log behavior tracked by #1849.

The next transport step is to ask CBORG to trace the retained correlation
IDs and confirm the effective `/v1/messages` timeout and keepalive policy
before another full batch. No support message or new model request was sent
during this outcome review. Issue #1849 remains unresolved.

This is a public summary of reviewed local operational evidence, not a
publication of the underlying request records. Detailed request IDs,
financial evidence and source text remain private. The summary does not
authorize a new attempt or change any registered controls or historical
artifacts.
