# CBORG API evaluator compatibility — 2026-09-13

Canary preflight found #1761: the direct API rubric evaluators always sent
temperature, including to Opus 5, whose compatibility rule already excludes
that parameter in the generation runner. Both rubrics now share that rule.
The actual request omits unsupported temperature; output metadata records
null and its basis, and the Markdown report describes the effective setting.
Models that accept temperature retain their configured value.

Four strict-client regressions fail on main c5fdcaad8 (both rubrics and two
Opus 5 route spellings), while both Sonnet controls pass. After the fix, all
55 focused API, report-rendering and semantic-contract checks pass. These
tests use synthetic local records and fake provider responses; they incur no
model charge and do not attest a live canary.

This is a request/implementation boundary to include in the next registered
condition. Source rubrics, rendered API system prompts, agent definitions,
generation code and historical evaluations are unchanged. CBORG credentials,
model selection, usage capture and budget remain explicit launch controls.
