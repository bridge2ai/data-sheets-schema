# BC1 D63 implementation and validation scope

2026-10-29. Wave7 Task 5; local packet, not publication or generation approval.
The root Codex session controls the serial test slot and STATUS log.

The packet now uses `bc1_input_sizing_v4` and the explicit calibration identity
`d63_exact_request_pair_d62_future_v1`. The request term uses the exact reported
integer pair 1,185,329 canonical payload bytes / 432,784 input tokens. The
floating point bytes/token field remains a display value; it does not control
rounding. For request-floor bytes R and future wire delta U:

```
Q = ceil(5*U/4) for visible_cap_measured_escape, otherwise U
estimate = ceil(R*432784/1185329 + Q*4/7)
```

The code evaluates both ceilings with integers, retaining one outer ceiling.
It does not ceil each token component separately, scale request bytes by the
escape factor, or change D62's response ratio 1.75, escape factor 1.25,
floor/caps gating, advisory scenarios, per-call guards, or aggregate allowance.
The existing 4,500,000-input-token A21 allowance is unchanged. D63 changes the
generic BC1 request term, with no new project or arm conditional.

The provenance records the reported agy observation at 2026-10-29T04:48:47Z,
the original request SHA-256
`c2087a5a3ad9eddae8d42393a96d71a9d200bee749d02b76e75ee286311f70c9`,
the frozen request's model, CBORG base URL and count operation. The evidence is
the lead/agy report, not a newly acquired raw SDK response. The numerator is
canonical logical-payload JSON, not HTTP framing; the denominator is pre-call
count tokens, not D62's settled input/cache usage. Transfer to other requests
remains a planning assumption. No count call was made.

Strict registration contract, code identity, sidecar format and calibration
comparisons reject old D62 sidecars and forged estimates. Historical sidecars
and their evidence remain untouched. New tests check the exact observed pair,
ceiling boundaries, future-only escaping, integers above floating point's exact
range, and rejection of altered calibration, source identity and row estimates.
The prior end-to-end formula assertion now uses independent `Fraction`
arithmetic for the new request term.

The existing completed-run 4M/600k refusal fixture is deliberately unchanged
until its outcome is observed under the new policy. If its numerical premise
has moved, the fix must establish a real just-below-current boundary and keep
both CLI/library refusal and no-write assertions; accepting a formerly failing
number does not justify deleting the obligation.

## Separate cache hypothesis

The extracted omission formatter is absent from BC1's explicit cache dependency
roster. `tests/test_wave7_bc1_formatter_cache.py` warms a real derivation, proves
unchanged cached and uncached equivalence, then replaces only `_render_prepared`
with a distinctive refusal. Both paths must refuse, and the two optional pure
caches must clear. No cache implementation has been changed. Execute and retain
the original causal failure before any bounded dependency-roster repair.

## Validation status

Implementation and regression tests are prepared; execution is pending the
root's serial slot and the protected proposal applied only in a fresh archive.
No full collection, full CI-layout suite, provider-fit, timing, canary, scientific
support or merge-readiness claim follows from these source edits.

A separate read-only review by the delegated protected-proposal reviewer found
no blocking source finding in the integer formula, provenance/sidecar guards,
new regressions or proposal helper. It confirmed the F6 omission source is
byte-identical to the lead's resolved file (SHA-256
`cd17fed4c330320511519c5757f29666021d6639b8998ac9dc4c5a244a67b03c`).
That static review is not test execution.

The independently reviewed proposal helper was executed once. Its nonempty
diff is SHA-256 `274411de3448c32be0600bec33fd794bce747e24bffa7eff6dede01eb568c719`
and its JSON proof is `908635a46ec19e0312b21715c37b450471d05ad1a8a00d0b20c0931d923d6966`.
It preserves all six BC1 hooks over exact #5212/A14/A13 source, including the
two A13 asset pin corrections and D41's unique journal dependency. Removing
the six hooks yields exact #5212 source, while removing them from the BC1
baseline yields exact pre-BC1 source. Syntax was parsed without importing or
executing production code. The proposed protected source/re-pin SHA-256 is
`94b3cf6845827c8fdf7bf05cc6251e2fb196ceb91ea8ce377f2c9e3b8be3773d`.
The branch source remains
`1c4436b5ea689fcd674c848a722dd9a86495692ad83401682f3d805f49acb6d6`;
no protected patch or re-pin has been applied here.
