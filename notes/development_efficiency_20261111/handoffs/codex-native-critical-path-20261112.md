# Native first-canary critical path — 2026-11-12

The shortest path is one main-targeted U1+U3 integration candidate containing 382f0dfd1ce8 plus PR 5871, followed by accepted protected packets, complete offline path evidence and exact-head review/CI; revised N1 ratification; the two separately authorized D117 probes; a fresh CHORUS registration and reviewed launch packet; then one owner-worded capture → guard → launch sequence. Several listed PRs are already incorporated or preserve tooling/evidence and need not merge separately. Native generation is the main result under D134. Planning at 900 seconds with the unchanged 90-second margin gives an 810-second pre-reservation age limit, but 900 remains the lead's recommendation, not an owner decision. The existing diagnostic does not establish production readiness: it omits four full registration verifications and does not prove post-reservation dispatch or completion.

Read-only snapshot, 2026-11-12 UTC. Native source: 382f0dfd1ce863fdf257a77e2bbb2637dbe2f67b; selected fusion top: 1a137b58860416a31618de44173180d021dfcc61 (PR 5871); current main: 7ad8c9e7295f1575ae9108ea62c12c83b1dd4db1; unratified N1: 754fbfdae10dbe9fe3f4443725cf0fa2a696b49e. PR/CI states below are retained local observations, not refreshed GitHub status.
Path legend: ROOT = /Users/marcin/Documents/VIMSS/ontology/bridge2ai; PRIMARY = ROOT/data-sheets-schema; EXEC = ROOT/d4d-executions; DEV = EXEC/codex-development-efficiency-20261111; REVIEWS = EXEC/plans/reviews. STATUS means PRIMARY/notes/coordination/STATUS.md. N1 means Git object 754fbfdae:notes/generic_v10_analysis_plan_amendment_n1_2026-11-08.md. Source paths and line numbers default to Git object 382f0dfd1ce8; differences at 1a137b588604 are identified.
Absence claims are bounded. Searches included ignored and hidden files (rg -uu) in relevant PRIMARY coordination records, DEV native handoffs/reviews/scripts/docs, EXEC/plans native review records and current native scripts/docs; tracked source was searched through Git objects. Excluded historical run directories and external conversations were not exhaustively searched. No launch-a21 access. Source inspection used Git objects, not a stale working-tree version.
Earlier results are reused, not rerun: DEV/notes/development_efficiency_20261111/handoffs/codex-native-launch-verification-audit.md (SHA-256 cda53553a43331051c684231a3f27ebb4625043283d9ef0ba0ed7b87a44f920f) and codex-native-capture-timing-question.md (SHA-256 e6f3550305727bc181b7599fa9460ed2dce9c7b44f6aa272ecf71ba53cf59d16). No speedup is inferred by subtracting component CPU from production wall time.

**Dependency-ordered gates**

Ranges are rough remaining person-hours for a successful first pass, not elapsed-time promises; substantial newly discovered defects, owner/host/CI queues and model runtime are excluded. Parallel columns show independent preparation lanes, not permission to run them now. Code, amendment and operator preparation can overlap; final evidence must bind the same integrated source and ratified terms. D134 expressly preserves separate run, merge and launch authorizations. There is no defensible launch date until the current-main integration and full path gates have passed.

| ID | Gate | State | Who | Hours | Depends on | Can run in parallel with |
| --- | --- | --- | --- | --- | --- | --- |
| G01 | Adopt native generation as the primary result and plan under the stated 900/90 assumption. | done | lead | 0–0 | none | none |
| G02 | Record the launch-critical issue dispositions without adding every optimization or evidence PR as a gate. | partial | lead | 0.5–1.5 | G01 | G03; G04; G05 |
| G03 | Prepare and independently review revised N1 with 900/90, current-main schema and D126 declarations. | partial | lead | 2–5 | G01 | G04; G05 |
| G04 | Reconcile the selected native ancestry with current main in one reviewable integration candidate. | partial | worker | 4–12 | G01 | G03; G05 |
| G05 | Prepare the minimal v2-only 900-second policy and meaningful boundary fixtures. | not_started | worker | 1.5–4.5 | G01 | G03; G04 |
| G06 | Obtain owner ratification of the revised N1 hash and each ballot item. | not_started | owner | 0.25–0.75 | G03 | G04; G05 |
| G07 | Prepare exact integrated protected-file and scanner comparison packets. | partial | worker | 2.5–8 | G04; G05 | G06; G13 |
| G08 | Approve changed protected postimages and scanner differences by exact identity. | partial | owner | 0.25–0.75 | G07 | G13 |
| G09 | Install the approved packets and freeze a coherent candidate with ratified policy. | not_started | worker | 1.5–4 | G02; G05; G06; G08 | G13 |
| G10 | Authorize the single new final-source boundary diagnostic and its stated scope. | not_started | owner | 0.1–0.25 | G09 | G13 |
| G11 | Demonstrate the genuine boundary and the complete offline public execution/refusal path. | partial | worker | 8.5–25.5 | G10 | G13 |
| G12 | Complete independent adversarial review and full CI on the exact combined candidate. | partial | lead | 2–6 | G11 | G13 |
| G13 | Prepare the production registration/packet builder and fail-fast operator runbook. | partial | worker | 2.5–7 | G01 | G03; G04; G05; G07; G11; G12 |
| G14 | Approve and merge the final combined native PR, then verify merged bytes. | not_started | owner | 0.25–0.75 | G12 | G13 |
| G15 | Freeze the actual binary/provisional runtime and authorize both D117 probe phases. | partial | owner | 1–3 | G06; G14 | none |
| G16 | Complete the observation probe and final bound permission probe on the selected binary. | not_started | worker | 1–3 | G15 | none |
| G17 | Build and offline-verify the fresh production CHORUS registration on merged source. | partial | worker | 2–5 | G13; G16 | none |
| G18 | Obtain both independent exact-registration reviews. | not_started | lead | 2–4 | G17 | none |
| G19 | Freeze the actual owner statement, review bundle and exact one-attempt authorization. | partial | owner | 0.5–2 | G18 | none |
| G20 | Execute the reviewed capture, guard and one-attempt launch sequence. | not_started | owner | 0.25–0.75 | G19 | none |
| G20A | Freeze the blind recall observations before any audit reading. | not_started | lead | 0.5–1 | G20 | none |
| G21 | Verify the saved result and report B0–B5 from immutable evidence. | not_started | worker | 1–3 | G20A | none |
| G22 | Complete blind B6 scientific review and owner B7 acceptance. | not_started | owner | 1.5–4 | G21 | none |

| ID | Required by | Evidence / state basis | Concrete remaining work |
| --- | --- | --- | --- |
| G01 | Owner D134, STATUS:594–607; assignment claude-lead-codex-native-critical-path-20261112.md:12–16. D134 does not ratify freshness. | D134 records native as main result; line 607 labels 900/90 a lead recommendation only. | Keep the assumption distinct from permission; API comparison work is outside this critical path. |
| G02 | None found requiring all eleven PRs, later capture, or an N=10 performance campaign before the first canary. Ignored-inclusive search scope is stated above. Issue 5722 and accepted latency plan v3 still require explicit lead disposition; owner D95 and N1.4(A) require the complete correct path. | DEV/notes/development_efficiency_20261111/handoffs/lead-results.md:43–86; PRIMARY/.temp/generation-eta-20261110/notes/reviews/native_latency_implementation_plan_2026-11-10_v3.md:98–104,135; issue 5722/NL10 record; details below. | Lead records donor supersession and separate tooling/evidence handling; explicitly rescope F1 performance work if deferred while preserving the safety constraint in 5836 and all correctness gates. No issue is silently closed. |
| G03 | Owner D107, STATUS:815–824; N1:20–24,110–111,318–326,344–369; D126, STATUS:699–704. | N1 head 754fbfdae remains unratified at 300/90 and schema 3.2.0; main 7ad8c9e72 declares 3.2.1. Current file hash 741677373008237020d409a7f79365b3e2d0f188a16d996b5defb3a14af050aa cannot bind revised text. | Revise item o and timing rationale, explicitly revise h to the selected release rather than silently ratifying 3.2.0, add the absolute-path difference and redaction obligation, reconcile stale code-status text, obtain two independent rereviews and new file hash at a commit. |
| G04 | Owner D95, STATUS:827–835, requires U1 and U3 together; D129, STATUS:677–680, requires native integration before comparison rebuild. N1.4(A)(7):175 requires final integrated review/CI. | 5839 → 5857 → 5871 exists; merge-base(1a137b588604,7ad8c9e72)=2cfc4666c2d81003d9cf5f432248b4217ef477e1. No retained native-plus-current-main preview found in the ignored-inclusive scope or local ancestry. | Create or revise a main-targeted U1+U3 PR; preserve reviewed ancestry and current-main schema/behavior, classify conflicts and rerun applicable coverage. PR 5839 alone targets an older native anchor. |
| G05 | Planning assumption; N1.8(o/u):360,366 and N1.9:382 explicitly preserve v1. Owner ratification is still G06. | Both active v2 policy constants remain 300 at 382f/1a137; full file inventory below. No freshness change is made by this report. | Two source files, six mandatory test files, the amendment and a superseding operator guide; retain 90 margin, v1 and unrelated clocks. Use 900/901 dispatch and 810/811 reservation tests. Generate new source-bound fixtures rather than editing old evidence. |
| G06 | N1:20–24,344–369; owner D107, STATUS:815–824; D121 conditional N1 merge protocol, STATUS:728–742. | STATUS:604–607 explicitly says N1 unratified and 900 not approved. Earlier green/review evidence belongs to the previous text. | Owner names the revised file SHA-256 at its commit and answers a–x, including 900, unchanged 90 and chosen schema. Merge the ratified amendment under the applicable exact-head protocol before registration; any changed answer requires reconciliation. |
| G07 | Owner D127–D128, STATUS:684–697; N1.4(A)(7):175. | Four protected files on 382f and 1a137 still have preimages; newer API proposal postimage 830eec1e… differs from D127's 3e8b7e5d…. U3-M scanner comparison still has unaccepted drift. | Compute final main-reconciled postimages and itemized scanner delta; preserve four-packet atomicity. Distinguish unchanged approved packets from every changed postimage. Prepare owner review for the API mismatch and any further drift. |
| G08 | Owner D127–D128, STATUS:684–697; protected changes outside approved identities need a fresh owner decision. | D127 approved four historical postimages and D128 a particular comparison, not every later composition. | Owner approves the current exact API postimage and other changed protected bytes if any, plus disposition of scanner differences beyond D128. Prior approval continues only for identical bytes. |
| G09 | D127, STATUS:685–692; N1.9:371–412 requires accepted code before registration. | Private measurement compositions applied packets; the selected source branch did not. No production installation is established. | Apply only approved postimages on the assigned integration branch, verify hashes, commit coherent source and build fresh composition/WP1 contract for that source. Do not reuse the 382f contract. |
| G10 | D134, STATUS:602, preserves owner word for further diagnostics; D132, STATUS:668–675, covered one prior 382f run only. | D132's retained run is complete; its authorization does not transfer to 900 or a new source. | Present one concrete unchanged-profile canary command, source/contract, quiet-host criteria, limits and output location for approval. No added campaign is implied. |
| G11 | N1.4(A)(6–7):172–175, citing issue 4354; D125, STATUS:706–710, retains quiet qualification for timing/acceptance. | D132 retained refusal at age 306.533703 under 300; 5871 has component evidence only. REVIEWS/native_u3m_2026-11-09.md:118–131,164–171,281–297 leaves two public completions, 17 failures and eight groups uncertified. | Run one approved genuine boundary canary first and verify artifacts; qualify any freshness/timing claim. Then complete required public correction, omission, refusal, interrupted cleanup and saved readback cases on the final candidate, including post-reservation dispatch. Resolve failures. A reservation-only pass is insufficient; no automatic N=10 campaign. |
| G12 | N1.4(A)(7):175; owner D92/D95, STATUS:827–848, require independent review and lead signoff; repository review discipline. | Native draft full CI runs are cancelled; current main's green run 43056320723 does not certify the combined head. | Two required independent reviews, issue records and dispositions, exact-head full CI and relevant boundary/scanner/regression suites. Recheck changed code after repairs; retain cancellations as cancellations. |
| G13 | N1.3 D12:158 and N1.5:229–249 require actual artifacts and sequence. None found requiring one wrapper specifically; ignored-inclusive scripts/docs and coordination searches found primitives and synthetic fixtures, not a complete production CHORUS rehearsal. | Production prepare/runtime/registration/review validators exist; tests/utils/native_u4b_fixtures.py:48–90 supplies fictional approvals and CI, not a real packet. | Build truthful templates and an offline rehearsal for real CHORUS inputs, exact paths and outputs; prepare one reviewed sequential wrapper or exact runbook. Do not count fixture reviews/CI as approval. Final binding waits on merged source and probes. |
| G14 | D95/D129 integration order and N1.4(A)(7); D134:602 retains per-PR merge approval. D121 does not grant blanket authority over these later PRs. | No owner-approved merged combined native head established; selected drafts remain an unmerged stack. | Owner approves the concrete reviewed exact head; assigned integrator merges, verifies final source/protected hashes and CI relation, and records supersession. Archive and retain historical branches as required by D96/D97. |
| G15 | D117, STATUS:755–761; N1.9:403–410; durable binary copy conditional on ratified N1.8(b). | native_u4b_probe_sequence.py:105–127 defines the closed authorization; REVIEWS/native_u4b_2026-11-08.md:53–55 says no actual binary copied or invoked in that work. | Choose verified actual binary, account-choice and final source; create durable copy if ratified and exact provisional runtime. Owner authorizes the observation and bound phases against the scripted local provider with their actual artifact identities. |
| G16 | D117/D116, STATUS:755–773; N1.5:229–232 and N1.9:403–409. | No completed final-binary two-phase probe is demonstrated in retained searched records. U4b reports distinguish synthetic tests from real probes. | Observation first; derive limits/thinking and final runtime; bound probe second; validate the sequence and saved transcripts, limits aliases and permission traces. These local-provider probes do not prove account entitlement or quota. |
| G17 | N1.3 D12:158; N1.4(A):165–175; N1.5:229–232; N1.9:372 requires merged commit citations. | Registration primitives exist, but the final source, ratified terms and actual bound probe have not been assembled into a production packet. | Bind exact source/schema/prompt/profile/context/source bundle/runtime/probe, new attempt/evidence paths and owner/operator identities. Commit registration and verify author-date validity, immutable inputs and truthful CI evidence; retain declared shared-v1 differences, v4 primary and D105 secondary measures. |
| G18 | N1.3 D12:158 and N1.5:229–232; D107 operator/review defaults, STATUS:815–824. | No final production packet exists for independent review; fixture reviewer documents are not evidence. | Independent Claude and Codex CLI reviewers, neither author nor operator, inspect the frozen packet and proof. Record review document hashes and resolve rejecting findings before freeze. |
| G19 | D22/D113/D115, STATUS:602,765–777; N1.5:233–243,297–302; N1.9:397–402. | native_launch_review.py validates these joins, but no real final launch bundle/word was demonstrated. | Owner confirms LBL Max/high effort, quota/headroom, 90-dollar backstop, no overage, ratified deadline/host/capture terms; bind both reviews and statement to bundle SHA. Owner issues AUTHORIZE_ONE_NATIVE_ATTEMPT with strict authorization time and exact source/dependency/registration/CI/probe identities. |
| G20 | D115; N1.5:244–264 and N1.8(o/u/v); D113, STATUS:780–783, and D134:602 preserve the two-attempt limit and individual launch words. | Only source and synthetic route evidence inspected; no authorization or actual first native CHORUS attempt established. | Owner operates the reviewed runbook with required host/account state and exact output paths. Capture after word, retain every capture, prepare v2 guard and launch immediately; stop on refusal. At most three authorized captures, no silent retry/new word, and no second attempt without its own registration/word. |
| G20A | D36 and N1.4(B)(B6):212–224 require blind recall observations pinned to original-full bytes before audit exposure. | Requires the new canary's original full output; no seed exists for this unrun attempt. | An independent blind reviewer/model receives only the permitted original source/full artifact, records recall observations and pins their hash to original-full SHA. Preserve blinding before technical audit/report inspection begins; final adjudication follows G21. |
| G21 | N1.4(B):177–211; D109, STATUS:787–791, makes B5 diagnostic rather than blocking. | Requires the real attempted output. Offline proof cannot substitute for its saved readback. | After the blind recall seed is frozen, perform independent read_final and gate/receipt/schema/tool/history/clean checks; retain rejecting outcomes without alteration. Report B5 as UNMEASURABLE pending diagnostic floor, not as a pass. |
| G22 | N1.4(B):212–224; D36 blind recall ordering; D107 and D113 acceptance/stop rules. | No canary result to judge yet; native ratings remain separately deferred under N1.6:328. | Complete fresh independent source review and independent CLI review using the already-frozen blind recall seed; owner adjudicates unresolved/rejecting findings and signs acceptance. B0–B4, B6 and B7 are required; B5 is reported. |

**Code landing and exact-head CI**

Required source order: older U1/U3 anchor 5f4a8e211826fe7f83ec51e6262d750687216aba → PR 5839 → PR 5857 → selected PR 5871 improvement → current-main reconciliation → approved packet installation → final review/full CI → owner-approved combined merge. This is one main-targeted integration landing, not eleven required PR merges. D95 requires U1+U3 together; no owner decision requiring each listed PR number was found in the ignored-inclusive scope.
Sources: DEV/notes/development_efficiency_20261111/handoffs/lead-results.md:43–86; handoffs/native.md:15–17; handoffs/agy4-cpu-diagnostic.md:4,40–51; reviews/native_capture_ast_integration.md:16–33; reviews/analysis_replacement_ci.md:7–57; handoffs/claude-lead-handoff-20261111.md:119–132; DEV/tmp/pr-native-capture-evidence-body.md:1–11; EXEC/plans/pr4659_decisions_and_recommendations_2026-11-07.md:3–36.
No retained local evidence of the native top merged with 7ad8c9e72 was found in the searched Git ancestry and ignored-inclusive native reports. The recorded 44b8a6595 preview was PR 5808, not native integration. Main run 43056320723 was green on 7ad8c9e72 (DEV/notes/development_efficiency_20261111/reviews/claude_lead_intake_review_20261111.md:212); it does not cover the selected native stack.

| PR | Retained head | Disposition | Exact CI evidence |
| --- | --- | --- | --- |
| 5839 | 458887766effe38207a77fea2d8033f1f3e1c7f3 | Carry reviewed ancestry into combined main PR. Existing PR targets native anchor 5f4a8e, not main; supersede its separate landing once covered. | Full 42961942947 cancelled. |
| 5857 | 382f0dfd1ce863fdf257a77e2bbb2637dbe2f67b | Integrated capture/import-facts/adapter candidate; carry into combined PR. | Full 42967472339 cancelled. A component capture/readback proof is not final acceptance. |
| 5871 | 1a137b58860416a31618de44173180d021dfcc61 | Selected fusion improvement above 5857; compose and review in final head. No separate owner requirement for this PR number under 900 was found. | Full 42976790438 cancelled; cheap check 42976790492 passed. Nineteen component cases on 64c612133b5b8fa0972ec2b10dc821f4d81e65c6, then report-only commit; no integrated speedup/freshness proof. |
| 5851 | 459e56bf896a29d854c5d250ce8632d7e2564427 | Already reproduced in 5857 as 3047be2d8a5f78663681b896e699434a7f42f51f. Close as superseded after replacement linkage; no duplicate merge. | Full 42965552735 cancelled; donor-patch equality recorded. |
| 5852 | 89975411d65e42aae5baa2bb92276ad5f9fabf1a | Already reproduced as 033cd731f6d9a854143076a8bd13125d61101f92. Supersede with provenance retained. | Full 42965805390 cancelled; 45 targeted passes do not certify final stack. |
| 5855 | f82e451743086fc4ec45cda044577e7b587c57c1 | Already reproduced as 41135a507d8a00c4cbe83ad51b4fdde8c7c2671f. Supersede with provenance retained. | Full 42967083141 cancelled; donor-patch equality recorded. |
| 5866 | 8bb1e949ccf3ee6ce5698af301238a01935676b5 | Six cleanup/report/provenance files, no production change. Preserve and review separately; can close only with an explicit archival/supersession disposition, not a launch prerequisite. | Exact full-CI run/result not established in retained sources checked. |
| 5840 | 7043f0be145d5a0922cdbd3a73f099e6e9a12a3c | Thirteen preparation/refusal/cleanup/provenance tools on 01bdcb22dad66da1a167595251b23e6352c97ab7. Use reviewed tooling as needed; this historical PR need not separately land before launch. | Full 42962609355 cancelled; cheap 42962609470 passed. |
| 5841 | a36c7174fb35c62a2499ee52918354e57a877d6a | CPU-comparison helper/evidence; retain, handle outside launch critical path. Forks at 3cc113e2606c563236d9c06098c5329ddd027a38. | Full 42964017924 cancelled. |
| 5853 | 76a443ee34103ed18f30041c111f9f2aae1af40e | Main-based report/helper; separate publication/review, not production launch dependency. | 42966522505 cancelled. 42963052291 passed on different head aa86cf0039293a042666751d69dd703a20bfabf5, although tree d5104e82d26fabfe0af981a3c8168b5e03abfdb0 is identical; no status transfer. |
| 4659 | 17aac4c3c82c88cc80c4e1660a1349c1cce92beb | Historical donor, do not merge. D96/D97 (STATUS:543–550): archive head, close as superseded when replacement U1+U3 PR opens; retain source/base branches until native acceptance. | Historical report of five red checks; no current exact-run audit. |


**Four protected packets and scanner acceptance**

The four candidate files remain byte-identical between 382f and 1a137 and are still preimages. Private composition is not installation on the integration branch. Source: REVIEWS/native_u3m_2026-11-09.md:27–61,338; scripts/adhoc/compose_native_u3m_20261109.py:29–47,101–108; D127, STATUS:684–692. Recompute against actual current-main composition before claiming that any postimage still applies.

| Protected target | Candidate SHA-256 | D127 approved SHA-256 | Remaining |
| --- | --- | --- | --- |
| src/data_sheets_schema/shared_generation.py | 94b3cf6845827c8fdf7bf05cc6251e2fb196ceb91ea8ce377f2c9e3b8be3773d | 2ec18e60316423035f88a2a30263c56385bfbbc587303e84e805a8349ab4f781 | Not applied; approved identity retained in historical packet, subject to current-main compatibility. |
| src/data_sheets_schema/api_runner.py | b109cb918a3079a384937ccfad7ab9b195a55713a355f11f848da98fab59596a | 3e8b7e5d3cc13c5ebc508e33f865e9ac484056fde16126118719d740656a4fb7 | Newer proposal postimage 830eec1e12e96f807fa76ea26e066a1923b60380013c424cfa99f0012af0a881 requires fresh owner approval even though proposal patch bytes are unchanged. |
| src/download/prompts/canonical_hashes.yaml | 39b93c009457681a1d8d8b8afee5a869bbd6f5e70b6f4332522db5d7e22d0584 | 543e5cd6dc0da0f622ba2cd11a16a90732e9302a1ed0a4700efb61971299d252 | Not applied; do not change merely to change guard age. |
| tests/utils/run_spec_boundary_contracts.json | a7f96a253a37e994f0c62c7d9b2ab21b0a94d4f342975f84103cd274ef11af72 | b1e0cbd14c533a51b88eacb84b974cb93963e18d8f1fb71ae4ed3228f784d1ce | Not applied; verify exact accepted boundary roster after integration. |

D128 (STATUS:693–697) approved a specific comparison: 5,229 exact, 57 line relocations, six field changes, one nonviolating addition, zero removals and the same nine violation objects. U3-M later recorded 5,244 exact, 57 relocations, six fields and one addition, with 16 API relocation pairs shifted; changed assets include ontology/DUO differences and test-dependency relocations. Its scanner cohort was 45 passed, one failed, one skipped (REVIEWS/native_u3m_2026-11-09.md:79–112). Same violation count is not approval of the other changes. Produce a new exact comparison on the integrated head and obtain the required disposition.

**N1 ratification: remaining choices and settled foundations**

N1 at 754fbfdae is not binding; all 24 items a–x require explicit answers and the revised file hash at a commit. D121's conditional merge allowance for PR 5542 does not ratify it. Existing v6.1 SHA-256 741677373008237020d409a7f79365b3e2d0f188a16d996b5defb3a14af050aa is obsolete once text changes. Earlier records calling the ballot 23 items a–w are stale relative to this exact object.
Current main's schema is 3.2.1: src/data_sheets_schema/schema/data_sheets_schema.yaml:31, data_sheets_schema_all.yaml:8, data_sheets_schema_core.yaml:17, data_sheets_schema_core_all.yaml:18 and D4D_Core.yaml:11 (7ad8c9e72). N1:110–111,324,353 still says 3.2.0. Recommend explicitly choosing current main's 3.2.1 in revised h; its code merge alone is not an N1 answer. Also add D126's absolute-path cross-arm declaration and publication redaction to N1.6:318–326.

| Ballot items / source | Still requires ratification | Already settled or qualification |
| --- | --- | --- |
| a–e, N1:346–350 | No auxiliaries; durable executable copy; literal launch argv; changed pins require new registration; transcript-based receipt origin. | D106 identifies account/effort/binary/thinking; D107 describes receipt origin and review defaults. They do not answer every interpretation. |
| f–h, N1:351–353 | Close old D18 time box; 14-day registration author-date lifetime; exact native schema release. | Current main is 3.2.1, draft says 3.2.0. Revise h explicitly. |
| i–k, N1:354–356 | B0–B7, typed-protocol order and reported-only unopened chunks, clean-run evidence. | D107 sets native amendment/review route; exact row set remains a ballot choice. |
| l–o, N1:357–360 | Seven-day 0.50; numeric window/reset domain; extra windows; capture after authorization and age 900. | D118 settles five-hour 0.25 and restates 0.50, but l is still explicitly a ballot item. D134 does not approve 900. |
| p–t, N1:361–365 | 21,600-second deadline; IOKit keep-awake on AC; operator quiet lock; manual stop; live usage versus post-run acceptance interpretation. | D107 describes stop/operator defaults. D125 still requires genuine quiet qualification for timing/acceptance, not just holding the lock. |
| u–x, N1:366–369 | 90-second reservation margin; new word after three failed captures; terms through owner statement/review bundle; every capture's limits checked. | v expressly extends D115; x is stricter than D117. Neither extension is automatically decided by those D-numbers. |
| D105/D123, STATUS:805–809,717–721 | No new activation decision required for first canary. | v4 primary; v5 tool-origin and v5's own full-to-core transformation receipt secondary and non-gating. Full v5 activation is a later condition. |
| D106/D107, STATUS:810–824 | Apply already chosen account/effort and amendment route. | Explicit high, LBL first-party Max, binary/thinking pinned; owner operator, independent review, CHORUS n=1, not a replicate. |
| D109–D114, STATUS:771–795 | Retain settled backstops and native scope. | Pending diagnostic floor; dollar guard 90; overage disabled; 1M mode; two native attempts/native-cell rejection; narrowed generation toolchain. |
| D115–D118, STATUS:755–773 | Prepare concrete artifacts and authorizations under these decisions. | Up to three captures per attempt word; corrected model/limit/thinking mechanics; two separately authorized local-provider probe phases; five-hour admission 0.25. |
| D126, STATUS:699–704 | Declare the accepted absolute-path difference and redact publication. | No portable-path redesign required before first canary. |


**Direct answer 1: every active 900-second edit, and what stays fixed**

Required code/test edits are two active source files and six test files, plus the amendment and a superseding operator guide. The optional seventh test update is labeled. Historical v1 is explicitly frozen by N1.9:382; the lead's three-source-constant count includes that frozen file and must not be applied literally. Source lines below are at 382f unless marked otherwise.

| File / lines | Required change | Scope |
| --- | --- | --- |
| src/data_sheets_schema/native_u4b_policy.py:16–17,33–39 | max_age_seconds 300 → 900; exact policy equality remains; margin stays 90. | Required source |
| src/data_sheets_schema/native_subscription_guard_v2.py:24,343 | Maximum 300 → 900; rejection text 1..300 → 1..900. | Required source |
| tests/test_native_launch_review.py:22 | Embedded runtime-basis fixture age 300 → 900. | Required test/fixture |
| tests/test_native_subscription_guard_v2.py:35,146,212,240 | Fixture/assertion 900; exact dispatch boundary 900 accepted/901 refused; above-maximum mutation 301 → 901 so it still tests the maximum rather than only equality. | Required test/fixture |
| tests/test_native_u3k_freshness_order.py:57,186 | Both deliberately expired timestamps +301 → +901, preferably registered age plus one. | Required test |
| tests/test_native_u4b_a3_policy.py:21,44,47,59,65,75,163 | Age fixture/full remaining 900; calculate 900 minus remaining; reservation 210 → 810 and failure 211 → 811; final valid dispatch 299 → 899; explicit preparation 900. Preserve remaining values 91/90/89/1/0. | Required test/fixture |
| tests/test_native_u4b_a3_reservation.py:49 (1a137:61) | Capture-age calculation 300 → 900 or derive from registered terms. | Required test |
| tests/test_native_u4b_windows_v2.py:150 | Saved late-dispatch mutation +301 → +901. | Required test |
| tests/test_native_u4b_admission.py:62 | Optional 299 → 899 or registered age minus one; old 299 still tests mismatched policy. Preserve v1 readback at 96–99. | Optional semantic cleanup |
| notes/generic_v10_analysis_plan_amendment_n1_2026-11-08.md:255–256,360,366 (754fbfdae) | N1.5/item o age900; keep item u90; replace no-measured-launch-path rationale with retained diagnostic and its limits; new revision/hash. Also reconcile schema h and D126 as above. | Required amendment |
| notes/native_operator_guide_DRAFT.md:5,20,82 | Supersede or clearly update for current v2 and 900/810; its 300 statements describe historical d258611c5 and must not be retroactively relabeled. | Required current operator documentation |

Fixture audit: git grep of the specified committed tree found no committed JSON/YAML literal freshness fixture requiring a direct 300-to-900 rewrite. This is a tracked-tree statement. Ignored-inclusive rg -uu of retained U3-M/report evidence did find saved runtime/preparation/composition/registration/guard/review/probe artifacts containing 300; preserve them. Their newly generated replacements need new source and output identities, not bulk substitution.
Deriving helpers need no numeric edit: tests/utils/native_u4b_fixtures.py:10–16,53–60; tests/utils/native_synthetic_evidence.py:183; tests/test_native_u3k_profile.py:238–239; tests/test_native_shared_execution_failure.py:114; tests/test_native_u4b_addendum_authority.py:124; tests/test_native_u4b_capture_retries.py:77. Likewise native_generation.py:244 and native_launch_review.py:172–180 use registered terms. Fresh policy propagates through new runtime, preparation, composition, registration, CI/probe evidence, owner statement, review bundle, word, capture and guard. Rebuild source-specific WP1 contract under scripts/adhoc/native_wp1_validation_20261110.py:157–187; do not reuse wp1-contract-382f0dfd1ce8.json.
Keep historical src/data_sheets_schema/native_subscription_guard.py:20,166 and tests/test_native_subscription_guard.py:53 unchanged. Preserve old reports, traces, fixture snapshots, source copies and failures. The four D127 files are not freshness constants and do not need repinning merely because age changes.

**Independent clocks and boundary semantics**


| Rule / source | Effect of 900/90 |
| --- | --- |
| Guard v2 pre-reservation, native_subscription_guard_v2.py:445–447 | Derived maximum age 810 = 900 minus 90; no active source constant 210. Equality at 810 allowed, 811 refused. |
| Actual one-use dispatch, guard v2:419–455 | Independent age at most 900 from original captured timestamp; capture must still be after authorization (362–364). Margin is not another timer or guarantee. |
| Window resets, guard v2:365–366,431–432,467–470,590–592 | Every populated numeric window must reset after capture and actual check/dispatch; live and saved checks continue. A near reset can refuse before age900. |
| Post-reservation, N1:255–264 | 90 retained for keep-awake, runtime probe/binary identity and dispatch. Stale after reservation can consume an attempt. |
| Policy, native_u4b_policy.py:19–20; N1 ballot | 21,600-second runtime deadline, 14-day registration lifetime, 0.50/0.25 thresholds, three captures and two attempts unchanged. |
| Synthetic attempt/helper, tests/test_native_synthetic_profiles.py:57–68; tests/test_native_u3k_profile.py:236 | 900-second synthetic attempt and 180-second helper are independent clocks; do not change them to track quota freshness. |
| WP1 supervisor, native_wp1_validation_20261110.py:49–54; run_native_wp1_20261110.py:147–166,187–189 | 900-second invocation supervisor and child/cleanup allowances unchanged. |
| Unrelated 300/210 literals | tests/test_native_execution.py:47 is an attempt deadline; tests/test_native_u4b_a4_real_events.py:70 uses range(1,210) for 209 events; historical Git helper timeouts and run_native_u1u3_20261108.py:35 cleanup allowance are unrelated and stay unchanged. |


**Direct answer 2: later capture, F1 and issue 5836**

Changing the numerical freshness policy does not close a structural finding or authorize a new acquisition architecture. The recommended shortest path preserves genuine verification, tests the complete path under the ratified terms, and explicitly records which performance work is deferred. The existing accepted work plan still calls F1 a separate gate; this report recommends a lead disposition, not a silent waiver.

| Item | Requirement found | First-canary disposition under 900 |
| --- | --- | --- |
| Later-capture redesign | None found as an owner-required first-canary architecture in the ignored-inclusive coordination/issue/review scope. Earlier timing report: DEV/notes/development_efficiency_20261111/handoffs/codex-native-capture-timing-question.md:19–32,40–66. N1.5:244–264 already permits genuine acquisition after authorization and before guard/launch, with limited recaptures. | Follow-up if the ratified 900/90 path passes genuine production-boundary and complete-path checks. If it cannot, a reviewed redesign may become necessary by evidence. Do not relabel timestamps, refresh an existing guard or move an unverified capture across authority boundaries. |
| Structural U3K-F1 / 5722 | PRIMARY/notes/coordination/issue-bodies/native-latency-plan-review/nl-10.md:9–13 explicitly keeps cheap postacceptance closure separate from timing. Accepted v3 plan:84–104,135 and its lead review:7–15 preserve it. None found making cheapness itself an owner scientific acceptance criterion; N1.4(A):165–175 requires correctness, safety, complete-path tests and review. | Not closed by 900. Recommend explicitly deferring the optimization as an open follow-up, while preserving its refusal/equivalence constraints. Until the lead records that scope change, it remains an unmet gate of the accepted engineering plan. Current full verification may satisfy safety at a higher cost; that must be demonstrated, not assumed. |
| 5836 supplied verified_value bypass | DEV/tmp/review-postaccept-supplied-value.md:3–7 forbids public caller-supplied verdicts replacing authoritative reconstruction. Line 9 expressly says the design finding is not a prerequisite for final D4D generation; mapping in DEV/notes/development_efficiency_20261111/review-post-acceptance-design.md:7. | Safety constraint remains binding for any optimization. No requirement to implement a cheap-verifier design or close this issue before first canary when the chosen path preserves full genuine verification. Keep issue/disposition evidence; review the final fused path for compliance. |
| N=10 quiet-host performance campaign | None found as an owner first-canary prerequisite in the ignored-inclusive records inspected. Prior performance plans contain campaigns; D125 retains quiet qualification for timing/acceptance. | Do not add it to the shortest launch path. Lead should explicitly dispose of older campaign obligations; one approved final-source boundary proof plus complete required correctness/CI coverage is the immediate route. No timing claim under load and no automatic new runs. |

The accepted v3 plan is PRIMARY/.temp/generation-eta-20261110/notes/reviews/native_latency_implementation_plan_2026-11-10_v3.md, SHA-256 fbe0bd80d622576bc4c5305e1a7ef7de857ced28f9a3a8016035b7bde79e3467. Its lead review, native_latency_plan_v3_lead_review_2026-11-10.md:23–28, authorizes planning direction only, not architecture, protected bytes, whole suites or native generation.

**Boundary proof before an attempt**

The retained D132 diagnostic at 382f yielded a genuine pre-reservation refusal: capture age 306.533703 seconds, launch CPU 243.398143 seconds, launch wall 295.745893 seconds and entry lag 10.802291 seconds. These are historical measurements from DEV/notes/development_efficiency_20261111/handoffs/codex-native-capture-timing-question.md:40–52, not acceptance under the proposed 900 source and not an actual production capture→guard→launch measurement. The earlier failed/capped evidence is retained; it is not a pass.
PR 5871 removes a duplicated verification phase. Its component review attributes 11.370907 CPU seconds to the removed row, not the retained 9.980186-second row. There is no measured net integrated speedup on this new head. The earlier launch-verification audit also found no demonstrated safe additional saving from the public full-verification path.
First new run, only after its specific authorization: exact-source genuine pre-reservation boundary canary, newly rebuilt source contract/composition, qualified quiet host for timing, no overlay and saved refusal/one-use/source checks. The existing diagnostic stops at the attempt-mkdir sentinel without making a reservation; it can establish only its pre-reservation age, which must be at most 810 under the proposed terms. Subsequent genuine public-completion testing must separately demonstrate dispatch age at most 900, valid reset windows, completion, saved readback and interruption cleanup. These offline tests use the ordinary Python peer; actual selected-binary behavior remains for D117 and the later owner-worded attempt. The production capture/CLI overhead listed below remains outside the sentinel diagnostic.

| Required proof | Existing evidence / gap | Next bounded evidence |
| --- | --- | --- |
| Public correction completion | REVIEWS/native_u3m_2026-11-09.md:164–171 leaves tests/test_native_shared_execution.py::test_actual_public_correction_three_workers_and_saved_completion uncertified. | Same production public adapter, ordinary Python peer, genuine offline helpers, persisted completion and independent read_final, no stand-ins. |
| Public omissions/all chunk statuses | Same report leaves tests/test_native_shared_execution_variant.py::test_actual_public_merged_omissions_and_all_chunk_statuses uncertified. | One verified genuine unit before expanding; verify selected source omission accounting and actual saved output. |
| Refusal, failed readback and interruption | Seventeen required failure cases and eight remaining groups enumerated in U3-M:118–131,281–297; old counts are not final-head certification. | Missing/stale workers, omitted chunks, unrelated assembly/authority, corrupt lineage and interrupted terminal cleanup; verify side effects and no unauthorized reuse. |
| Full integrated software/scanner coverage | Execution-v2 554, policy423 and U4b1099-pass/1-fail cohorts are older, overlapping snapshots; later refusal repair does not certify all remaining cohorts. | Current-main combined full CI, exact source/protected bytes and accepted scanner comparison; independent review of final repaired head. |

D125's quiet-host qualification is separate from the operator's lock. A lock coordinates workers but does not prove low foreign load. A21 is excluded from this work, and neither its completed run nor its authorization transfers to native.

**D117 probes and production packet readiness**


| Part | What exists | What remains |
| --- | --- | --- |
| D117 observation then bound permission | native_generation.py:96–107,155–179 and native_u4b_probe_sequence.py:105–127,338–440 define authorization and producers; scripted loopback uses a dummy key (141–155). Bound phase has seven permission traces plus version check. | Actual selected-binary runs are not demonstrated by retained reports (REVIEWS/native_u4b_2026-11-08.md:53–55,395–406,461,485). Prepare exact authorization; observation defines limits/thinking, then final runtime/bound probe; validate saved sequence. |
| Probe versus subscription boundary | D117 no account usage, D116 model aliases/limits/thinking; N1.9:403–409. | Local-provider probes do not establish actual account entitlement/quota or remote generation. Scripted probes report scripted API-key source; actual subscription capture must use the registered first-party route and no API key. |
| Native CHORUS registration | native_execution_registration_v2.py:225 prepare; native_u4b_runtime.py:202 prepare_runtime; native_shared_registration_orchestration.py:31–64 registration/composition checks. | Real builder inputs, final merged source/schema/assets/toolchain/runtime/probe and attempt paths, committed registration and author-date check; no final production rehearsal established. |
| Review bundle, owner statement and launch word | native_launch_review.py:67–133 verifies registration-addition commit/validity; 152–225 validates terms; 228–301 checks bundle/word, reviewer roles and owner/operator joins. | Real independent reviews, owner terms and exact-head CI evidence. tests/test_native_shared_execution.py:28–85 and tests/utils/native_u4b_fixtures.py:48–90 use invented fixture CI/reviewers; cannot promote them into approval. |
| Operator wrapper/rehearsal | Three CLI commands exist; no combined operator wrapper found in scoped ignored-inclusive scripts/docs search. | One reviewed fail-fast script is feasible without protocol changes. Offline-rehearse path/JSON/manifest/digest plumbing with truthful artifacts, then bind final packet. No implicit capture retries, new word or second attempt. |

These are distinct authorizations: revised N1; changed protected/scanner packets; new diagnostic; actual D117 probes; merge of a concrete reviewed head; exact native one-attempt word; and later acceptance signature. Preparing the packet does not exercise any of them.

**Exact operator sequence — unexecuted template**

The source-supported CLI sequence below can be packaged in one reviewed script. It is not a ready launch command: NATIVE_PYTHON, REGISTRATION, REVIEW_BUNDLE, LAUNCH_WORD, CAPTURE_ROOT, ACCOUNT_CHOICE, PACKET, GUARD and CI_EVIDENCE must be bound to the approved production packet and verified interpreter/environment. No actual values or credentials are supplied here. CAPTURE_ROOT must be the exact registered request directory; capture returns the numbered slot's manifest. PACKET outputs must be new, permitted paths and never overwrite retained evidence.
Source: native_generation.py:63–81,117–140,206–247,259–265. jq is an explicit wrapper dependency to check during offline rehearsal. One script removes human pauses but does not remove registration reconstruction. Each step stops on failure; output JSON must be parsed and artifacts verified. Up to three captures are permitted only under the ratified word/terms; do not add an automatic retry loop.

```sh
set -euo pipefail

"$NATIVE_PYTHON" -m data_sheets_schema.native_generation \
  capture-subscription-event \
  --registration "$REGISTRATION" \
  --review "$REVIEW_BUNDLE" \
  --launch-word "$LAUNCH_WORD" \
  --output-directory "$CAPTURE_ROOT" \
  --account-choice "$ACCOUNT_CHOICE" \
  > "$PACKET/capture-command.json"

CAPTURE_MANIFEST=$(jq -er '.result.capture_manifest' "$PACKET/capture-command.json")

"$NATIVE_PYTHON" -m data_sheets_schema.native_generation \
  prepare-subscription-guard-v2 \
  --registration "$REGISTRATION" \
  --review "$REVIEW_BUNDLE" \
  --launch-word "$LAUNCH_WORD" \
  --capture "$CAPTURE_MANIFEST" \
  --output "$GUARD" \
  --account-choice "$ACCOUNT_CHOICE" \
  > "$PACKET/guard-command.json"

GUARD_SHA256=$(jq -er '.result.guard_sha256' "$PACKET/guard-command.json")

"$NATIVE_PYTHON" -m data_sheets_schema.native_generation \
  launch \
  --registration "$REGISTRATION" \
  --review "$REVIEW_BUNDLE" \
  --ci "$CI_EVIDENCE" \
  --launch-word "$LAUNCH_WORD" \
  --subscription-guard "$GUARD" \
  --subscription-guard-sha256 "$GUARD_SHA256" \
  --account-choice "$ACCOUNT_CHOICE" \
  > "$PACKET/launch-command.json"
```

The owner remains the operator under the proposed/ratified N1 route. A valid word may cover this uninterrupted sequence; it does not permit arbitrary new configuration, refreshed timestamps, unregistered paths, new source or extra generation attempts. Runtime limits and host/account state must still pass at the actual boundary.

**Direct answer 3: production post-capture work omitted by the synthetic diagnostic**

The synthetic diagnostic constructs an already-created guard and directly invokes synthetic_launch (tests/test_native_u3k_profile.py:208–257). It does not time the real capture command, guard CLI or outer launch CLI. At least four additional full shared-registration verifications occur in production after the selected event timestamp: capture post-event authority, guard CLI entry, saved capture read, and launch CLI entry.
Every range below is an ESTIMATE for a responsive host, not a measured production bound or timeout guarantee. CPU/filesystem stalls and manual delay have no established finite upper bound. They are incremental steps, not a reason to subtract CPU seconds from the historical diagnostic wall time. The diagnostic's roughly 10–20 thread-CPU seconds per full verification informs only the scale of these estimates. No new timing run was performed.

| Extra production step | Source at 382f | ESTIMATE, seconds | Bound qualification |
| --- | --- | --- | --- |
| Drain terminal result/EOF and await child exit after selected quota event | native_subscription_capture.py:202–252; timestamp241–245 | 0–60 | 60 is the whole subprocess-loop deadline, not an overall return guarantee or necessarily 60 after the selected event. |
| Reap child/process group and close streams | native_subscription_capture.py:186–199,256–269; native_permission_probe.py:317–338 | 0–4 | Normal timeout accounting only; scheduler stalls can exceed it. |
| Full post-event authority reconstruction | native_subscription_capture.py:547–549; _authority141–145 | 15–60 | Full verification #1 outside synthetic launch; CPU evidence is not production wall evidence. |
| Validate terminal limits/success and hash/write durable stream, observation and manifest | native_subscription_capture.py:554–584 | 1–5 | Filesystem completion has no established upper bound. |
| Guard CLI entry/review verification, saved capture reconstruction, guard encoding/write | native_generation.py:206–246; native_subscription_capture.py:685–701 | 25–100 | Includes two extra full verifications (#2 and #3), excluding import overhead listed below. |
| Launch CLI registration/account-choice verification before shared launch entry | native_generation.py:206–217,259–264 | 15–60 | Extra full verification #4; measured shared-launch interval starts later. |
| Interpreter/import startup and JSON parsing/command handoff | Three separate module invocations | 2–15 | Exclude verification already counted; capture-process imports before the event are not charged again. |
| Operator transitions | N1.5:244–249; proposed reviewed sequential wrapper | 0–5 with wrapper | Manual pauses are unbounded. A wrapper must be rehearsed; none was established as complete. |

Also outside the pre-reservation diagnostic is the post-reservation region: durable attempt/evidence records, directories, further unchanged checks, keep-awake, runtime --version/auth status/binary identity, a further launch check and actual one-use dispatch (native_execution_orchestration.py:389–442). N1:255–264 keeps 90 seconds for this region; the two runtime commands each have their own 30-second limit. The 90-second margin is neither a guaranteed completion time nor a replacement for reset checks. Full-path proof must show that dispatch still passes.
Under 900 the historical 306.533703-second synthetic age is below810 arithmetically, but it is not evidence that the full production sequence or post-reservation tail fits. No new production total or guaranteed headroom is claimed.

**After the attempt: B0–B7 and who judges**

Source: N1.4(B):177–224. These are post-run acceptance duties, not prerequisites that could already be satisfied before the first result exists. The first attempt is a CHORUS n=1 canary, not a final replicate or an authorization for the six-project batch. A rejecting native result follows D113's native-only two-attempt policy; a new attempt still needs its own registration and word. Freeze the blind recall seed first (G20A), before G21 reads the derived audit; complete B6 adjudication after the technical readback.

| Row | Required evidence | Judge | Acceptance role |
| --- | --- | --- | --- |
| B0 | Completed-pending-independent-review result, runtime_gates_passed true and all 15 runtime gates, retained terminal/history/accounting/authority/keep-awake evidence. | Controller reports; independent reviewer verifies saved result. | Required |
| B1 | Independent read_final reconstructs selected assembly and joins attempt/downstream audit. | Independent reviewer. | Required |
| B2 | Full/core validation; duplicate keys zero; report totals equal derived audit counts; five prescribed structural receipt counters meet zero floors. | Independent reviewer using saved artifacts/validators. | Required |
| B3 | No prescribed/unclassifiable permission denials; receipt checks before seal/derive and typed audit; unopened chunks reported accurately, not converted into a zero floor. | Independent reviewer of phase/tool history. | Required |
| B4 | Clean immutable run; no interrupted write, consumed-identity reuse or manual modification/override; operator intervention attestation. | Reviewer checks bytes/journals, operator attests, owner adjudicates. | Required |
| B5 | Raw policy-v1 receipt floor as pending diagnostic pilot, labeled UNMEASURABLE. | Reviewer records. | Reported, not a strict-success gate under D109 |
| B6 | Fresh blind source review plus independent CLI review; second blind model recall observations pinned to original-full hash before reading audit; rejecting findings resolved/adjudicated. | Independent Claude and Codex CLI reviewers, independent of generator/operator; owner adjudicates. | Required |
| B7 | Signed acceptance record bound to final immutable evidence and review outcome. | Owner. | Required |

Native ratings remain deferred until native canary acceptance and a separately ratified rating registration (N1:328). No need to implement the later rating route or activate receipts v5 as the primary instrument before this first canary.

**Provenance and reproduction**

The JSON is the gate ledger and the source of every table above. The helper validates gate fields, dependency order and the no-at-sign constraint; it runs no repository production code.

```sh
env -i PATH=/usr/bin:/bin:/usr/sbin:/sbin HOME=/var/empty \
  /opt/homebrew/Caskroom/miniforge/base/bin/python3.13 -S -B \
  scripts/adhoc/render_native_critical_path_20261112.py
```

Helper: `scripts/adhoc/render_native_critical_path_20261112.py`.
Only the requested JSON, Markdown and this helper were written. No run, test, source edit, configuration change, provider/native call, GitHub action or STATUS edit was performed; launch-a21 was not accessed.
