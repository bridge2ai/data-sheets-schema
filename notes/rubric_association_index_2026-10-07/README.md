# Captured rubric association, issue #4639

The existing planners captured `rubric_join_jobs`, but the support/fitness index
did not compare those result declarations with the selected record. The opt-in
index v3 checks that association from captured bytes and retains each primary
job's missing, conflicting or unsupported state in the denominator.

The normal fitness descriptor captures only its own reconstruction inputs.
An explicit `--rubric-plan` therefore supplies missing rubric blobs from the
exact plan named by the descriptor; it cannot substitute another manifest or
follow historical paths. Rechecking the resulting index requires no original
plan directory.

This is an engineering association check, not rubric acceptance, score
extraction or a campaign result. Instrument hashes remain declared identities;
no canonical resource-byte authentication is inferred. Human review, empirical
calibration and paid-run holds remain unchanged. Parents #2929, #3342 and #3343
remain open.

Independent review finding [#4645](https://github.com/bridge2ai/data-sheets-schema/issues/4645)
identified an optional roster output hash that was not compared with captured
result bytes. The correction retains the exact declaration, reports a valid
hash conflict as `mismatched`, and preserves malformed-pin diagnostics alongside
other conflicts. Missing results remain missing. This adds a declared byte
identity check without implying authenticated evaluator execution.

See [the command and state contract](../../docs/top-level-fitness-results.md#captured-rubric-identity-declarations-index-v3).

Independent review and the coordinator's serialized ten-module run completed:
**279 passed**, with zero failures, errors, skips or reported warnings. The
pytest terminal summary reported 274.21 seconds; the JUnit suite records
274.134 seconds. Existing loopback transport fixtures were authorized; no
external provider call, scientific rating or historical rescoring was performed.

The tested commit is `713bc5deca8a2fa5c2ed66d78b195ee521bb55bb`, with tree
`5e5d9d529a9624bb87f31482951e161cfd0d98e3`. The
[validation record](validation.json) pins 31 focused production, dependency,
test and repository configuration files. Each listed working file was compared
with its bytes in the tested commit after the run; every SHA-256 hash agrees.
This is not a complete imported-code or installed-environment snapshot.

The retained external `support-rubric-tests-01.xml` is 47,978 bytes with SHA-256
`035c0e1d6691fdeed56478f709f5260c32b16d227be7ec1a533c0084f87431df`.
Its counts, durations, module membership and hash were independently inspected.
The command, interpreter version and absence of pytest warnings are attributed
to the coordinator's completed run, rather than a second test execution.

Coverage includes default v1/v2 compatibility, v3 support-ledger coexistence,
explicit additional raw-plan identity, selected roster membership, relocated
recheck, alias/context/scope mismatches, malformed or missing results, forged
flags, and the optional output-pin conflict from #4645. These checks establish
captured declaration association only. They do not validate rubric schemas,
scores, arithmetic, provider execution or scientific rating acceptance.
