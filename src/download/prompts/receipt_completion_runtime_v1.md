# Registered receipt completion runtime policy v1

This separate opt-in condition uses API renderer 8 and receipt instrument v4.
The caller supplies an immutable registration naming this policy, the selected
condition, a positive output-token cap and a positive whole-request byte limit.
No default cap, model, route, spending budget or empirical floor is selected here.
A diagnostic-pilot registration with a pending floor does not pass a production
coverage gate. A registered floor uses an exact integer fraction on final-record
with_receipt / receiptable; zero eligible leaves is not a fabricated 100 percent.

After the full record and any re-addressing finish, the controller preserves the
normalized full, original receipt, effective receipt and complete prior exchange
before admitting at most one receipt-completion call for this generation. Its
one admitted delivery uses the existing bounded transport retry and accounting
rules. No answer retry, full regeneration, or reopening of terminal audit/report,
evidence, source-review or restoration state is permitted. Every attempted
response and usage is retained before parsing. A truncated response is incomplete.
The selected frozen schema must validate the persisted full before this call.

The continuation carries every uncovered receiptable leaf, unchanged input pins,
the complete prior exchange, and the registration. If the explicit output cap is
unsupported or the complete request exceeds the supplied byte/context limits,
refuse before admission; do not shorten the inventory or silently change the cap.
Return exactly one YAML mapping containing only a `rereceipt` list. For EVERY
listed path return exactly one item: {path: ..., receipt: {chunk: cNNN,
snippet: ...}} with a verbatim supporting passage from that exact source chunk,
OR {path: ..., unsupported: true, reason: ...}. Never add, repeat, rename or omit
paths. Never edit any record or the receipt itself. Use only uniquely listed
chunks with status extracted, nothing_relevant or redundant_with, not duplicate_of.
Inspect the surrounding source: quotation verification does not establish support.
A verified reversal of a prior negative status is retained and counted.

Verified partial additions may be preserved, but the result remains incomplete
and no second completion is purchased. Keep all rejected answers, unanswered
paths, unsupported candidates and the fixed phase-1 before/after denominator.
Unsupported means a candidate for subsequent independent audit, not permission
to delete a value. The audit receives every candidate path/reason and the pinned
candidate artifact/input identity. Receipt additions do not certify truth or
resolve scientific support; origin and padding diagnostics remain separate.

Receipt publication checks the pinned before hash and records the exact after
hash. A resumed generation adopts only that recorded result or refuses; it must
not merge twice, overwrite external drift, or regenerate full after lost progress.
Historical renderer-24 preparation remains offline and has its original identity.
