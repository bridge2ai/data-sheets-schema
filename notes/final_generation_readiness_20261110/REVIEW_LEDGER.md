# Implementation review ledger

Findings were recorded before fixes. Local verification is not merge or generation approval. The canonical evidence summary is [RESULTS.md](RESULTS.md); worker handoffs retain their original scope and chronology.

| Issue | Finding | Disposition |
| --- | --- | --- |
| #2975 | Collection-type prose contradicts scalar declaration | Scalar prose corrected; 3.2.1 identities and products regenerated. Broader structural exchange mapping remains outside this PR. |
| #5792 | Native diagnostic cleanup reserve overstated its time cap | Native commit `19e6d99e4` corrected the wrapper; normal receipt re-canary passed. Injected cleanup failure remains untested; native branch is separate. |
| #5793 | Native diagnostic measured interpreter identity only before execution | Native wrapper now measures before/after; re-canary passed. This wrapper is not included in the main-line PR. |
| #5794 | G4 report mislabeled issue identities and source facts | Corrected; deferred issues now match their actual findings. |
| #5795 | Acceptance-guide commands did not match parsers | Corrected against actual parsers; independent re-review passed. |
| #5796 | Guide misstated record shapes and derivation behavior | Creator/Person, Maintainer, permissions, projection and API guard contracts corrected. |
| #5797 | Guide overstated native acceptance evidence | Executed N1 receipt/source-review components distinguished from G1 schema/pair checks and unverified whole-native acceptance. |
| #5798 | G1 draft called unsupported APIs | Rewritten against actual APIs; integrated positive canary and six-node cohort passed. Initial failed attempt is not used as evidence of a production defect. |
| #5799 | G2 helper captured staging/source or wrong toolchain paths | Corrected before generation; relative context/source paths and intended environment verified. |
| #5800 | G2 asserted unchanged digests without comparing them | Before/after comparison now verifies all four API schema digests; release receipt retained. |
| #5801 | G2 helper would delete existing staging evidence | Requires fresh staging/output; preserves earlier evidence. |
| #5802 | Receipt negative could hide unrelated findings | Both cases require an empty findings list; integrated component tests passed. |
| #5803 | Wrong working directory selected the primary checkout | Corrected CWD/module/schema provenance; 24 schema checks passed. Earlier wrong-CWD logs retained outside the repo. |
| #5804 | Artifact helper expected untruncated descriptions and incorrect base comment | Exact serialized expectations corrected; independent source re-review passed. |
| #5805 | Artifact helper discarded unreviewed SSSOM header changes | Compares every header line, allowing only date and exact expected status-count changes; re-review passed. |
| #5806 | Handoffs had stale incidental counts; plan implied cross-route gates | Counts corrected, and native-only gates explicitly apply only to native execution. |
| #5582–#5590 | Nine specificity hits in two historical controllers | Existing open issues; scanner exits 1. Both files are unchanged from base `7233f193ad`. No scanner exemption or blanket clean-audit claim. |
| #5807 | General RDF comparison exceeded its grant; tool timeout backgrounded it | Removed duplicate library comparison, enforced a 120-second comparison/report deadline and guarded scratch location. Independent re-review and final artifact comparison passed; the interrupted attempt remains recorded. |

Main-line delivery includes portable receipt/source-review tests only. It does not import the separate native selection, lifecycle or WP1 implementation. Broader semantic exchange, Core expansion, rubric scoring and corpus migration remain deferred rather than generation prerequisites.
