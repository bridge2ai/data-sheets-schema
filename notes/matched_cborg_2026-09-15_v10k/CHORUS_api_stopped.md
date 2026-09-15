# CHORUS API v10k stopped attempt — 2026-09-15

The first v10k API generation request ended with `RemoteProtocolError` at
09:24:14 UTC. No D4D text was delivered, and no full/core pair exists to review.
The matched agentic canary and all later generation/evaluation remain unstarted.
This outcome does not assess the scientific effectiveness of the shared evidence
fixes. Keep #1801, #1815 and #1816 open. Follow-up: [#1831](https://github.com/bridge2ai/data-sheets-schema/issues/1831).

[PR #1819](https://github.com/bridge2ai/data-sheets-schema/pull/1819) merged the
reviewed implementation. [PR #1830](https://github.com/bridge2ai/data-sheets-schema/pull/1830)
merged the reviewed v10k registration. The frozen launch commit is
`19a5248e4d1fd2dd8e0b28b794b1c315c7915778`; its independent registration review
approved and [all required CI checks passed](https://github.com/bridge2ai/data-sheets-schema/actions/runs/34950148567).
Fresh launch preflight verified code, inputs, historical files, model catalogue,
accounting and the current active goal's authorization. The earlier v10j approval
was not reused. The local launch-review receipt has SHA256
`ef0f652cef0884c0ae770165fee9c80bf6004abcda97e52df5a178888978a743`.

The attempt started at 09:17:29 UTC. Its one admitted generation request used a
live input count of 44,446, a conservative input bound of 54,360 and an output
ceiling of 128,000. The $3.539750 reservation was within the $6.78 attempt cap.
The controller stopped durably after the connection failed. It did not retry.
All 12 original files were copied and hash-verified, including the exact request,
admission, incomplete snapshot, usage ledger and result. The frozen execution
checkout and originals remain unchanged. [The sanitized outcome](CHORUS_api_stopped.json)
records original-file hashes and evidence identities.

The incomplete snapshot records zero content characters and partial usage of
12,365 uncached input tokens, 32,828 cache-write tokens and seven output tokens.
A read-only CBORG spend-log lookup found a matching entry reporting $0.267175,
`status: success`, empty response content and the same seven output tokens.
Model, time, usage, system, reasoning settings and output ceiling match. Three
long request text fields have explicit database-elision markers with matching
prefixes, suffixes and omitted lengths; the stored log cannot establish full
payload equality. CBORG's [usage guide](https://cborg.lbl.gov/api_faq/) describes
provider spending records, and LiteLLM documents [individual transaction logs](https://github.com/BerriAI/litellm-docs/blob/main/docs/proxy/cost_tracking.md).

The provider entry is retained as an accounting observation, not confirmation of
complete billable usage or successful generation. The original $3.539750
reservation remains pending. Prior settled token-price estimates total
$29.391638, leaving $167.068612 uncommitted from the additional $200 after that
reservation. No zero charge, final seven-token usage or completed response was
invented to release the stop.

Obtain conclusive accounting and review the transport failure before a fresh
attempt. Any retry needs a distinct registered attempt, unchanged preserved
originals, a reviewed launch receipt and a recalculated cumulative budget. Do
not resume the stopped identity automatically or reduce the declared workload
silently. Only independent acceptance of unchanged API originals can gate the
matched agentic canary. The current native arm uses pinned Claude Code and this
repository's CLI; Aurelian is not a runtime requirement of that path.
