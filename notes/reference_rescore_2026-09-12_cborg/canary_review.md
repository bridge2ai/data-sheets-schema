# CBORG evaluation canary review — 2026-09-12

Accepted for the registered evaluation workflow: CHORUS v7 rep1, rubric10,
rating1. The fresh session ran from 18:35:24Z to 18:45:08Z and produced
**35/50 (70.0%)** on both the fixed and adjusted bases, with no excluded
items. The remaining 55 ratings had not started at this review.

The agent definition is
`66ad623121272099bf94535ae5be2163a5f5005fe895d2bf2bf04c4f90e34864`;
the evaluator quoted the registered release-history check sentence and
recorded that digest. All 50 item headings match the source rubric. The
36 pinned files and all 258 prior evaluation files retain their hashes.

The published JSON and retained candidate match the original evaluator's
last successful absolute Write byte for byte. Their SHA256 is
`8b08357453730a468b3f47f8c0c0315d1ef30fe69ed937a0c95cbf2f9f9d8178`.
Schema, arithmetic, exact-file validator evidence, input identity, runtime
identity and check-echo gates passed. Read paths inspected in the trace are
inside the isolated workspace; the only Write targets its output JSON.
The attempted filesystem-wide search and compound shell commands were
denied. No protected scoring input, schema or validator was rewritten.

The trace initializes Claude Code 2.1.269 with Read, Write and Bash and
`apiKeySource: ANTHROPIC_API_KEY`. The frozen adapter selects the CBORG
endpoint explicitly with the inherited CBORG credential and a fresh CLI
configuration directory. Assistant events identify `claude-opus-5`; CLI
usage maps the requested `claude-opus-5[1m]` selector to that canonical model
and a 1,000,000-token context window. Temperature remains null. The CLI's
`provider: firstParty` is its protocol classification, not evidence that
the request bypassed the configured CBORG endpoint.

CLI-reported cost is **$2.80151575**, below the $5 attempt cap. The earlier
bare-mode failure cost $2.433457 and remains excluded and unchanged. These
are CLI list-price estimates, not a reconciled CBORG invoice.

Review inspected all element totals and applicability, and the evidence
for release history, data derivation, processing software, governance and
social impact. The stated deductions are plausible against the supplied
record. E6.3 distinguishes a prospective roadmap from errata; E6.5 credits
documented upstream sources and derivation. E8.4 names tools that transformed
released data. E4.1 distinguishes missing formal oversight documentation
from the community consultation and social-impact content credited in
E9.5. Missing documentation does not establish missing real-world oversight.
The evaluator did not independently test URL or email reachability; phrases
such as “working addresses” are not a verified availability finding.

Acceptance establishes an intact scoring procedure and retained original
measurement. It does not certify every semantic judgment or repeatability.
Rubric20's textual-provenance rule still needs inspection on the new results.
No score or rationale was edited. Any change to batch launch mode requires
its own registered one-rating canary before fan-out.
