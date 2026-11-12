# generic_v10 analysis plan, amendment N1: the native agentic (direct) arm

**Status: draft v11, written by claude (lead) on 2026-11-12. Drafts v1 to v6.1 were written on 2026-11-08.**
- **v1:** an in-place edit of the plan file (PR #5542 head `b187e7160`), reviewed by Claude (review sha256 `6f09cc8e…`).
- **v2:** a separate file (`bc53c1ce…`), re-reviewed by Claude (`37309f2d…`) and Codex CLI (`d49ed159…`).
- **v3:** `e8b475c4…`.
  - Claude re-review: 3 P1, 6 P2, 13 P3, with 33 prior findings resolved and 7 partly.
  - Codex re-review: 1 P1, 3 P2, 1 P3.
- **v3 → v4:** responded to every v3 finding and took in D115 and D116. Codex's R5 was checked and withdrawn.
- **v4:** `9edff5b9…`.
  - Claude re-review: 1 P1, 3 P2, 9 P3; all 27 prior findings resolved.
  - Codex re-review: 1 P2, 1 P3; its v3 findings resolved, and R5 withdrawn as its own error.
- **v4 → v5:** responded to every v4 finding, and took in D117 and D118.
- **v5:** `ece2c8b3…`.
  - Codex re-review: ratifiable as is.
  - Claude re-review: 0 P1, 1 P2, 7 P3; all 15 prior findings resolved.
- **v5 → v6:** fixes that P2 and the seven P3s, and nothing else.
- **v6:** `18f29f83…`. Both narrow re-checks found it ratifiable as is: Claude with three optional wording nits, Codex with none.
- **v6.1:** applies those three wording nits only. Its file sha256 is `741677373008237020d409a7f79365b3e2d0f188a16d996b5defb3a14af050aa`, at commit `754fbfdae10dbe9fe3f4443725cf0fa2a696b49e`. It was never ratified.
- **v6.1 → v7** (commit `2fb0503757db041e009f21dd02a1d57a45a75a88`, file sha256 `8a644c0efb968da23f45c533e757fcd06af495c3d15c73c442c9d4a8c5566a60`): written after the owner's direction D134 and the launch-path timing of D132. It changed:
  - **the freshness age,** from 300 s to 1200 s (N1.5, N1.8(o), N1.9 item 2);
  - **the schema release,** from 3.2.0 to 3.2.1 (N1.1, N1.6, N1.8(h));
  - **the absolute-path difference** the owner accepted in D126, with its redaction (N1.6);
  - **the sequencing,** restated after D131, D133 and D134 (N1.6, N1.8(y));
  - **who runs the registered commands** after the word, and that they run as one sequence (N1.3, N1.5, N1.7, N1.8);
  - **N1.9's opening sentence,** which predated the code;
  - and, unlisted in v7's own header, it **softened v6.1's sentence that the API arm needs its own amendment to change schema.** v8 restores that sentence (N1.1).
- **v7's two re-reviews** both found it ratifiable after listed fixes, with no P1:
  - Claude: 7 P2, 8 P3;
  - Codex CLI: 4 P2, 1 P3.
- **v7 → v8** (commit `98adf23eb96661af33690d6b5593809d8b02a623`, file sha256 `bde0459309ec1d24be35d6098b6ba2dccd962e35c3943f9a4d99688abc2819e7`) responded to every one of those findings and took in the owner's decisions D135 to D137. Besides wording, it:
  - recorded the owner's choice of 1200 s (D136), and required the reservation-to-dispatch time to be measured offline before registration (N1.5, N1.8(ab), N1.9 item 11);
  - required guard preparation to refuse any capture but the last one claimed under the word (N1.5, N1.8(ac), N1.9 item 3), with three new acceptance checks (N1.4(B) row 4);
  - required the registered policy, and not only the guard, to carry the new age (N1.9 item 2);
  - stated that item (y) moves D35's freeze off the A21 roster of 2026-11-11 (N1.6, N1.7);
  - split v7's item (z) into (z) and (aa), bounded the delegated start, and pinned the sequence script (N1.3, N1.5, N1.9 item 10);
  - barred a session that draws on the registered account from starting the sequence, and required every such session to stand down (N1.3);
  - said how redaction is applied without editing a run directory (N1.6).
- **v8's two re-checks** both found it ratifiable after listed fixes, with no P1. Claude: 13 of its 15 findings resolved and 2 partly, with 5 new P2 and 7 new P3. Codex CLI: 16 of the 20 findings resolved and 4 partly, with 3 new P2 and 1 new P3.
- **v8 → v9** (commit `cc00b677737c8bd2e4afda8a67f89e0f87352c8e`, file sha256 `0893d635a49b89a3d756657e5ea7e2bb04fe74363e0d9e54d1d2323d6f563b66`) responded to every one of those. Besides wording, it:
  - **quoted D136's question and answer exactly,** and proposed a new margin, because the answer came before the reviews showed that the stretch the margin covers is untimed;
  - **proposes a margin of 300 s** in place of 90 s, and defines the measurement that checks it (N1.5, N1.8(u), N1.8(ab));
  - **enforces the latest capture a second time,** at the pre-reservation check (N1.5, N1.8(ac), N1.9 item 3);
  - **moves the stand-down rule out of the delegated start** into the host terms, with its own letter and a record, and bars such a session from monitoring (N1.5, N1.6, N1.8(ad));
  - **gives the sequence script's pin a place** in the bundle and in the launch packet (N1.4(B) row 4, N1.9 items 4 and 10);
  - **says when a session started by the author may review** (N1.3, N1.8(ae));
  - **adds a time limit to the direction** and a letter for the redaction record (N1.3, N1.8(af));
  - **makes a "no" to the sequence item mean revise and re-submit,** not three separate commands (N1.8(z));
  - **says the floor rule for native replicates is ratified before this canary launches** (N1.5).
- **v9's two re-checks** both found it ratifiable after listed fixes, with no P1, and every v8 finding resolved or, in one reviewer's reading, two still partly. Claude: 2 new P2 and 6 new P3. Codex CLI: 2 new P2 and 2 new P3.
- **v9 → v10** responds to every one of those. Besides wording, it:
  - **marks the pre-canary ratification of the native production amendment as the lead's proposal,** with its own letter and a place in step 1 (N1.5, N1.8(ah));
  - **defines one adjusted total** for the margin measurement and requires a host that passes D92's gate for the decision (N1.5, N1.8(ab));
  - **refuses a direction to a session that started a reviewer of the registration,** before the start and not at acceptance (N1.3, N1.8(aa));
  - **gives the quiet-account confirmation a key in the owner's statement** and makes the attestation the owner's (N1.4(B) row 4, N1.6, N1.9 item 4);
  - **checks the 30-minute limit** in the script and at acceptance (N1.4(B) row 4, N1.9 item 10);
  - **keeps the script's bytes in the launch packet** so that its hash is recomputed and not self-reported (N1.4(B) row 4, N1.9 item 10);
  - **splits the reviewer-independence item** in two and carries its second half into row B6 (N1.4(B) row 6, N1.8(ae), N1.8(ag));
  - **lists in N1.7** the two things items (ad), (ae) and (ag) change.
- **v10** is commit `127cc0bd69d73fcd21d94978bf5e0ee60e0e950c`, file sha256 `e50777af1aa70b73ec9ab041f0d23c581cbcb56f35d3cb615221ae44f333489f`.
- **v10's two re-checks.** Claude (sha256 `6f73adc68c3fb4e7ca5d96ce045c206fb357f98dd0816aed65cf187a533e06a6`): "v10 can be ratified as is", with no P1, no P2 and 8 P3. Codex CLI (sha256 `48332078b76f1e79572ffe957e4c39fe3ee41a743f77cd199ec3283f7c26c3f6`): ratifiable after listed fixes, with 1 P2 and 4 P3, and no further substantive obstacle after them.
- **v10 → v11** applies every one of those and nothing else:
  - **both 30-minute limits of a delegated start** are recorded, refused by the script and checked at acceptance: after the direction, and after the owner's confirmation of the host state (N1.3, N1.4(B) row 4, N1.6, N1.9 item 10);
  - **the adjusted total** says to use a recorded duration where one exists, for the binary hash and the keep-awake as for the probe commands; the 5 s figures are named as placeholders that can be timed; and the cost of needing a quiet host is stated (N1.5, N1.8(ab));
  - **D136's account** gives the record's two entries on the margin, the lead's summary and the lead's correction of it, and items (u) and (ab) state the arithmetic of a "no" exactly (Authority, N1.8(u));
  - **item (ah)** is worded as its body is ("a native outcome it governs"), is checked when the word is given and not at the registration's review, names its evidence, and says what a "no" leaves without asserting when the floor rule was fixed (N1.5, N1.8(ah));
  - **item (ae)** says which reviews it covers and what a "no" means for this amendment's own reviews (N1.3, N1.8(ae));
  - **N1.5** no longer says the script writes its own sha256;
  - **item (aa)** carries its "no" clause and its two refusals.
- **v11 has not been re-reviewed.** The findings and verdicts listed above are on earlier drafts.
- **It is not binding until:**
  - a Claude reviewer and a Codex CLI pass re-review it, with each finding filed;
  - the owner ratifies it by naming this file's sha256 at a commit and answering each lettered item of N1.8;
  - and it merges only after that word, and before the native registration.
- **Values marked [proposed]** are the lead's choices. They take effect only through N1.8. Unmarked rules are the owner's decisions or the plan's own text, each cited.
- **Review files** live outside the repository, under `d4d-executions/plans/reviews/`. They're cited by sha256:
  - v1 review: `6f09cc8e5f71d052024f0c0046f946a2d071162c3cde6cb377d596f7415e4fa6`;
  - v2 re-reviews: `37309f2dd70a45c8089947fe3256881d0a475fac6920c342a748bac537921e54` and `d49ed15954e5354275668b3dce5863c395a7365ea407d787fff8c43b379b004e`;
  - v3 re-reviews: `1e0bb1cdef678f7464813ac0468f0798c987545b63552158c86c5a6012eca8cb` (Claude) and `5f66e4bea9117d9e2bac0484c5fc41cef65ee0f19cb3d22b4af7b3ab88d67d7b` (Codex);
  - v4 re-reviews: `07311a51cae2a60c11c8f371250792e3176a9a1ba759e353d90cb3e271bae80d` (Claude) and `0408c6f670b880137092ac2a782bbc73ccb973f38d86153fc2b53cdf2d858ac3` (Codex);
  - v5 re-reviews: `a88cf25364db8d80b9b9fac95582c9c73edcf38166e5a4f57e2018f71823b0a9` (Claude) and `73df58bf3fac3b707ce140abb5432c160e34e3df21813361431bf67fb13179e6` (Codex);
  - v7 re-reviews: `2a5a91ad49189f63372d23c2f681e7184ebbbf1c585eba5cab71bb7154f3f0e3` (Claude) and `d26b9993b94fd1d734d5bb8e934fd99675841d6527a071f6ca49721b766d2e80` (Codex);
  - v8 re-checks: `c92d8a952cd4625ddcb9fe0a3e93b61799e9181751538f3b917d8422517f5743` (Claude) and `321a0c7d8f42b4ba18bb6434b883aeca089ea6e6d61ddd0935765a072425bf26` (Codex);
  - v9 re-checks: `f8647bc89947b212878d0b39d6b8f0425af3cf4e529c37507d42922f41c13422` (Claude) and `2736e049b2c14315091d0b07dc41bd3eb5ddcd79e80376173d7bf8a30bf1b90f` (Codex);
  - v10 re-checks: `6f73adc68c3fb4e7ca5d96ce045c206fb357f98dd0816aed65cf187a533e06a6` (Claude) and `48332078b76f1e79572ffe957e4c39fe3ee41a743f77cd199ec3283f7c26c3f6` (Codex);
  - the U4–U7 readiness plan: `07ebb68661512e6f0d4bd04b42523b3930a8ce952f9b89148babf061195d9a6f`.
- **The saved #4354 issue** was fetched 2026-11-08; the issue was last updated 2026-11-07T02:53:46Z. Its body sha256 is `7f6a07a063796414866f282afdd3008a6e9723e2cce816c60eacf5bff21d687c`, computed over the UTF-8 bytes of the API's `body` field with no trailing newline.

## Authority
- **The plan being amended:** `notes/generic_v10_analysis_plan.md`, ratified at commit `5b17ae079c8eb1fa4abdda3261054bfd22e4c2f1` with sha256 `b4a4f9a596173d3bdeb817b01ea53fb1a1d77574e121c7cecaf6f63b67fd4b4b` (D65). That file is not edited; this amendment stands beside it, as P4a amendment 1 does (sha256 `7b1a3e79ee12c33193b0e8c58de8bbfae02a57944aee19830f9a923ec55eccb7`, ratified by D71).
- **Plan item 43** asks for a dated amendment that settles the native decisions before the native registration, without blocking A21.
- **The owner's decisions.** These are excerpts from the coordination record, which is not in the repository. Text in quotation marks is exact; everything else is a summary.
  - **D105:** "Receipts v5 is not activated for final generation." v4 stays the registered instrument. v5's tool-receipt origin and the full→core transformation receipts are "secondary, non-gating measurements".
  - **D106 (resolves D29's effort and account):** "Native effort: explicit `high`" (`--effort high`).
    - The account is the LBL work Claude Max account, first party, the same as the v6 agentic arm, with no API key.
    - "The owner checks the seven-day usage headroom before launch."
    - "The registration records the Claude Code version and binary sha256 and the thinking setting."
  - **D107:** a dated native amendment, drafted by claude with the plan's proposals as defaults, independently reviewed, then ratified by the owner before the native registration. "None of it blocks A21." Its defaults:
    - D09: the pause applies only to the old generic_v9 arm;
    - D11: the binary and hash are pinned at registration;
    - D12: the owner is operator, claude orchestrates, and a Claude-plus-codex review pair reviews;
    - D13: the toolchain exposure, launch flags, runtime-closure fix and receipt origin are pinned;
    - D14: the old spend package is re-validated against subscription usage;
    - D18: a two-week time box from registration;
    - D25: no native canary counts as a replicate;
    - D91 scope and receipt v4;
    - the first canary is CHORUS with one replicate;
    - "the stop rule is any acceptance-row failure or the usage limit".
  - **D109:** the native receipt floor for the CHORUS n=1 canary stays `{state: pending, mode: diagnostic_pilot}`. "The canary counts as "accepted" when every other acceptance row holds. Its policy-v1 floor reading is reported, not gated." "The measured value informs a registered native floor before any native replicate."
  - **D110:** `budget_guard_usd` = 90 (`--max-budget-usd 90`). "It's a backstop, and it's a stop trigger the launch word states."
  - **D111:** "Extra usage (overage) stays disabled on the account for the canary's whole duration." The owner confirms that state in the launch word.
  - **D112 (completes D29's runtime-limit basis, plan §2):** the native canary runs with the 1M context, `CLAUDE_CODE_DISABLE_1M_CONTEXT=0`, pinned from the real-binary probe.
  - **D113 (A13 and D07 for the native cell):**
    - a rule-level rejection of the native canary ends the native shared-v1 cell only, not the API arm's generic_v10;
    - at most two native canary attempts, each with its own label, registration and word;
    - transport or budget stops are distinct from a scientific rejection.
  - **D114 (#4019):** narrow `toolchain()` to the generation agents, so the native run sees no study-specific agent files. This is a code change before the registration.
  - **D115:** `AUTHORIZE_ONE_NATIVE_ATTEMPT` also authorizes up to three admission-capture calls for that attempt.
    - **A capture** is a tiny live Claude Code call on the same account, with the same binary, model, effort and context, a fixed trivial prompt, no repository content, and a capture-only config directory outside every attempt path.
    - A stale or failed capture may be retried under the same word, up to the three.
    - Captures never count against D113's two attempts, and every capture is recorded.
  - **D116 (corrects D112's mechanics; the intent is unchanged):**
    - `limits {contextWindow, maxOutputTokens}` come from the probe's terminal `modelUsage` entry, and the thinking setting from its captured request body. The init line carries neither.
    - The model is requested as `--model claude-opus-5[1m]`, with a declared alias pair that the gates check exactly: requested, init and `modelUsage` are `claude-opus-5[1m]`; returned messages are `claude-opus-5`.
  - **D117:** one separate real-binary probe authorization covers two probe runs, both against the scripted local provider, with no account usage.
    - **The observation probe,** under a provisional runtime, reads the limits from terminal `modelUsage` and the thinking setting from the captured request body.
    - **The bound permission probe,** under the final runtime, has a `limits_basis` that names the observation probe's saved bytes.
    - The first live capture's terminal `modelUsage` limits must equal the registered limits, or the attempt is refused before its reservation.
  - **D118:** admission also requires five-hour utilisation ≤ 0.25, alongside seven-day ≤ 0.50. A mid-run five-hour exhaustion is still possible; it is a usage stop that counts as an attempt.
  - **D126:** "Accept, declare, redact." The native arm keeps absolute local paths in its model-facing instruction; the difference is declared, and the paths are redacted in anything published.
  - **D132:** one native diagnostic run, with no provider or model call. It is the launch-path timing N1.5 cites.
  - **D134:** "we dont even need the API route except for comparison, the native agentic is the main result".
  - **D135:** the scope of a separate amendment that the lead drafts, for native production cells mirroring the API arm's planned matrix. D135 ratifies nothing, and it changes nothing here: this amendment covers the first canary only.
  - **D136:** the owner answered "1 yes 2 yes 3 yes" to three numbered questions. The second, as asked: "Freshness limit at 1200 seconds? Still open; I recommend yes." The lead's earlier statement of that question was "Set the limit to 1200 seconds, with the 90-second margin unchanged?". D136 settles the number 1200. On the margin the record has two entries, and neither is a new owner decision: the lead's original summary, "Item (u), the margin, stays at 90 s.", and the lead's correction of 2026-11-12T08:13:37Z, which says that summary overread the record, because only the lead's earlier wording named the margin. The answer also came before the v7 reviews showed that the stretch the margin covers has never been timed. This draft therefore proposes a margin and asks the owner to ratify it explicitly (N1.8(u)).
  - **D137:** the lead may run the native arm's free offline checks at its discretion. Every provider, model or native-binary call still needs the owner's word each time.
  - **D36:** "Models review; you sign; seed (Recommended)".
    - A fresh Claude session does the blind source review, with a Codex CLI pass. Neither generated nor operated the run.
    - The owner signs each acceptance record.
    - "a second blind model reviewer writes audit-recall observations, pinned to `original_full`'s sha256, before anyone reads the audit".
  - **D43:** "You launch it (Recommended)". The owner runs the exact launch command after giving the word on the sha256. "agy and claude monitor read-only." "The guard and the rule that any assisted run is evidence-only both still apply."
  - **Also applied:**
    - D26 and D27 (the arm and its directories);
    - D53 (nothing is edited inside a run directory);
    - D56 (every retry is a new registration);
    - D65 and D71;
    - D89 (native first);
    - D91 (the declared shared-v1 differences);
    - D93 and D35 (sequencing), with D129, D131 and D133 (N1.6);
    - D98, D99 and D108 (schema 3.2.0's content). Release 3.2.1 adds one description alignment (#2975), merged with PR #5808 under D130.

## Decision status (moved here from the plan's decision table)
| Item | Status after ratification |
|---|---|
| D29 | Effort and account resolved by D106; runtime-limit basis resolved by D112 and D116 (N1.2) |
| D09 remainder, D11, D12, D13, D14, D18 | Settled in N1.3 |
| D25 | Settled by D107's default (N1.3) |
| Plan item 43 | Settled by this amendment |

The plan's own rows (D29 "Pending owner"; D25 and item 43 "Pending: the native amendment") stay as ratified. For readers of the amendment, this table supersedes them.

## N1.1 Scope and condition
- **The arm:** native agentic, also called direct (Track N, D26). Records go under `claudecode_direct{,_core}/<label>/` (D27).
- **Protocol axes, kept separate:**
  - native shared generation v1 (`native_shared_generation_v1`);
  - native renderer 26;
  - native receipt policy v1;
  - execution authority v2;
  - receipt checker instrument 4.

  The first four exist today on native branches only. Their binding bytes are those of **the accepted U1+U3 merge commit on main** (the readiness plan's gate G0), which the registration names. The first native canary uses the declared shared-v1 differences (D91), not BC1 parity.
- **Schema** [proposed]: the released 3.2.1, the release on main at `7ad8c9e7295f1575ae9108ea62c12c83b1dd4db1`. Its content is 3.2.0's (D98, D99, D108) plus one description alignment (#2975, `FileCollection.collection_type`). The native integration is re-validated on it before registration.
  - **The alignment is model-facing on this arm.** `release_history.yaml` records that neither profile's API schema-digest md5 moved. The native arm reads the schema files directly, and the merged file's sha256 did move (`cf4e0992…` to `bc560a3c…`). The description used to say a collection may have multiple types; it now says each `FileCollection` has one `collection_type` value, which is what the slot's scalar declaration already required.
  - For the native arm, this **supersedes D71(a)** ("Schema 3.1.0 as the v10 condition's schema"). The API arm's schema is unchanged by this amendment: a comparison registration that changes the API arm's ratified schema condition needs its own amendment.
  - **P4a amendment 1's native hand-offs are taken up here:**
    - the native arm reads the schema files directly;
    - it has **no write-time normaliser**, so a resolver URL or an EDAM URL written where a CURIE is required stays in the record and is counted as a finding, not rewritten.

    This is a declared difference (N1.6).
- **Receipt instrument:** checker v4 is the registered, gating instrument (D105).
  - The two D105 secondary measures are recorded under their own identities, never pooled with v4 (plan §3a):
    - the **transcript-based receipt origin** (`receipt_origin.py`, `native_receipt_origin.py`; #2933, #4445, #4447). These are not v5's model-written `tool_receipts`.
    - the offline **full→core transformation receipts**.
  - [proposed] The transcript-based receipt origin is the "receipt origin" that D107's D13 default pins: one measurement, named twice.

## N1.2 Runtime and account
- **Runtime:** the Claude Code CLI, with `--effort high` (D106).
- **Runtime limits and model (D112, D116):**
  - `CLAUDE_CODE_DISABLE_1M_CONTEXT` is `"0"`;
  - `--model claude-opus-5[1m]`;
  - the declared alias pair, which the gates check exactly: requested, init and `modelUsage` are `claude-opus-5[1m]`; returned assistant messages are `claude-opus-5`. Any other model string refuses;
  - `limits {contextWindow, maxOutputTokens}` come from the **observation probe's** terminal `modelUsage` entry (D117). The final runtime's `limits_basis` names that probe's saved bytes by sha256, and the bound permission probe then runs under the final runtime. One probe can't supply the limits of the runtime it ran under. The observation probe's provisional runtime must equal the final runtime in every field except `limits`, `limits_basis` and the thinking field;
  - [proposed] **every** live capture's terminal `modelUsage` limits must equal the registered limits. D117 names the first, and checking each one is the stricter reading.
    - A mismatch means the registered limits are wrong, so a re-capture can't cure it. It refuses this registration before any reservation, so no attempt is consumed. A new registration with a new observation probe is needed, and with it a **new probe authorization**, because D117's covers only its two runs.
    - This is also where an account that doesn't serve the 1M build would first show;
  - the live accounting gate refuses any difference from them.
- **The thinking setting** comes from the observation probe's captured request body (D116, D117). It's recorded in a field of the runtime declaration, so it follows the same two-step sequence as the limits (D106). A missing value refuses the registration (N1.9 item 6). The attempt runs with a fresh `CLAUDE_CONFIG_DIR`, so the account's own settings don't carry over.
- **1M entitlement is not yet proven.** The real-binary probe runs against a scripted local provider, so it can't show that the Max account serves the 1M build. The first live evidence is the first capture (N1.5).
- **Auxiliary models** [proposed]: none.
  - **Disclosed risk:** with an empty auxiliary list, any call to another model stops the attempt. The first subscription canary showed none.
  - `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1` is fixed in the policy environment (`native_shared_runtime_values.py`, `POLICY_ENV`); it's not a choice made here.
  - **A fallback model can't be passed,** by construction: the runtime key set is closed, the flag list is fixed, and `model` cannot be a CLI option.
- **Recorded identities, three observations kept apart:**
  - the **requested and init** identity (`claude-opus-5[1m]`);
  - the **returned** identity, per assistant message (`claude-opus-5`);
  - the **terminal accounting key** in `modelUsage` (`claude-opus-5[1m]`).

  Their relationship is the declared pair. The native transport has no per-call request record (criterion 5).
- **Account:** the owner's LBL work Claude Max first-party account. No API key, no CBORG route, no provider fallback.
  - The label "LBL work Claude Max" is public by design: the native outputs emit it as `ACCOUNT_LABEL`.
  - No account identifier or email address appears in any public record.
- **D11:** the registration pins the Claude Code version and binary sha256 (D107).
  - [proposed] The pinned executable is a **durable copy** outside the auto-updater's path, so that an update inside the validity window can't change the pinned sha. This was the 2026-10-25 packet's source recommendation, §4.3.
  - A different binary is a different registration.
- **Declared confound:** effort differs from the API arm, which runs at the provider default (D09, plan §4). It is recorded, not corrected.

## N1.3 The remaining owner items
| Item | Ruling |
|---|---|
| **D09 remainder** | The direct-arm pause applies only to the old generic_v9 arm. It does not apply to this arm (D107). |
| **D12** | The owner is the operator: the owner holds the account, gives the launch word and launches (D43). claude orchestrates. The registration and its packet get an independent Claude review plus an independent Codex CLI review, by neither its author nor its operator (D107). This supersedes generation plan N9's "codex-operator".<br>[proposed] **Delegated start (N1.8(aa)).** After giving the word, the owner may direct the lead to start the command sequence of N1.5 on the owner's host. D133 did this once for A21, by reference and for that launch only; it is not a standing precedent. The limits:<br>• **the owner's own acts stay the owner's:** the coded word, the statement of launch terms, and confirming the host state (AC power, lid, overage disabled);<br>• **the direction** names the registration sha256, is recorded in the coordination record before the start, and covers one start of the sequence, made within 30 minutes of the direction and within 30 minutes of the owner's confirmation of the host state. Both times are recorded. A start later than 30 minutes after the direction, or a restart after a refused capture, needs a new direction; a host confirmation older than 30 minutes needs a fresh confirmation from the owner, not only a fresh direction;<br>• **the starting session must not draw on the registered account** (N1.5's host terms). A direction to a session on that account is refused;<br>• **the starting session started neither reviewer of the registration.** A direction to a session that did is refused, before the start, so that the conflict is not found at acceptance after an attempt is spent;<br>• **the starter holds the operator's duties:** the quiet-window lock, the manual stop by the launch packet's procedure, and the attestation that nothing intervened. The owner may still stop the attempt at any time;<br>• **neither reviewer may be the starting session or a session it started.** The code checks independence only from the author and the bundle's operator (`native_launch_review.py`), so this is checked in the acceptance record, and a failure rejects the attempt as not clean (N1.4(B) row 4).<br>This item needs item (z): without the sequence there is nothing to delegate. Without a direction D43 stands: the owner starts the sequence, and agy and claude monitor read-only, from sessions that do not draw on the registered account.<br>[proposed] **Sessions started by the author (N1.8(ae)).** A fresh session started by the author's session counts as independent of the author for a review of a document or of a registration when it is given the artifacts and none of the author's conclusions, and its report says who started it. A session that started such a reviewer of a registration cannot then be directed to start that registration's sequence (above).<br>[proposed] **Row B6's reviewers (N1.8(ag)).** For the blind source review of a run, neither reviewer is a session started by the session that generated the run or started its sequence. |
| **D13** | The registration pins:<br>• the **toolchain exposure**, narrowed to the generation agents under D114 (#4019);<br>• the **tool allow-list**;<br>• [proposed] the **literal launch argv, recorded verbatim** (#4162's recorded-argv option), including `--safe-mode`;<br>• the **runtime-closure fix**, PR #2922 (#2714), merged 2026-10-17;<br>• the **transcript-based receipt origin** (#4445);<br>• [proposed] the **sequence script** that runs N1.5's steps 5 and 6, pinned by sha256 through the review bundle (N1.9 item 10).<br>[proposed] Any change to these is a new registration. |
| **D14** | The budget is subscription usage, plus a dollar backstop.<br>• **Re-validation, done by this amendment.** The 2026-10-25 packet's sources recommended a starting seven-day utilisation ≤ 0.80, an overage stop or overage disabled, a $90 guard and a 21,600 s deadline. Since then:<br>&nbsp;&nbsp;– the seven-day window was exhausted on 2026-10-24;<br>&nbsp;&nbsp;– D106 named the account;<br>&nbsp;&nbsp;– D110 set the guard;<br>&nbsp;&nbsp;– D111 disabled overage;<br>&nbsp;&nbsp;– D112 chose the 1M context, which spends headroom faster.<br>• **The result is N1.5's terms.** Any later change to them is a revision of this amendment, which the owner approves. |
| **D18** | [proposed] D18's original subject, a time box for #4354's offline acceptance, is closed by this amendment.<br>[proposed] D18 now means a **two-week validity window** for the native registration, counted from the **author date** of the commit that adds the reviewed registration file. A rebase or cherry-pick keeps the author date. After the window, the registration expires and a new one is needed. |
| **D25** | No native canary counts as a replicate (D107). A canary is descriptive feasibility evidence only. |

## N1.4 Acceptance
### (A) Software prerequisites: #4354's criteria 1–7, proved offline before registration
These are quoted verbatim from #4354; the body sha256 is above. They are software proofs, made at U3–U7, and they are not themselves rows on a live attempt.
1. "Bind an explicit native shared-protocol selector, captured prompt/playbook/schema/profile/source/context identities, caller-supplied runtime/receipt/audit limits and supported arm. Missing or conflicting declarations refuse before consuming an attempt. Preserve old default selectors, renderer captures, policy identities, historical registrations and artifacts."
2. "Generate the same selected neutral role/status/date/granularity rules, with each long shared contract paragraph occurring once in the complete native instruction. The native instruction must describe the actual typed-helper protocol and its phases. Preserve applicable checks in every selected request/helper surface; do not claim cross-arm parity solely from a common label."
3. "At the real native supervisor boundary, enforce immutable original full/core/effective receipt and complete typed worker, source-first omission, integration and independently checked assembly. Capture exact requests/replies, phase transitions and available accounting evidence. All registered chunks and workers are mandatory, including negative/redundant receipt chunks. Preserve model-declared candidate merging/drop decisions and their checked lineage."
4. "Carry the exact derived audit into reconciliation, retain complete role-bearing owner context for report/recheck, rederive core and preserve existing schema, pair, removal, attribution correction, final evidence and recorder gates. The final saved result must reconstruct the selected assembly and bind it to this attempt and downstream audit; saved success flags are insufficient."
5. "Retain the reviewed native permission, authority, one-use reservation, timeout/signal, first-error, cleanup and saved-readback contracts. Do not copy API token-count/accounting claims onto a native transport that cannot provide them. Caller limits, unavailable measurements and unsupported combinations must remain explicit. A pending scientific receipt floor cannot become strict success."
6. "Exercise the actual public native adapter with an ordinary Python protocol peer plus genuine offline helpers, including a successful correction path and exact failed readback. Test missing/stale workers, omitted chunks, changed authority, unrelated assembly, corrupt lineage, interruption and terminal/cleanup faults without repeated consumed work. These are synthetic software proofs; no real native executable, auth probe, provider request, permission probe, model, scoring or paid canary is authorized."

   The live canary is authorized only by its own word (N1.5).
7. "Update the public descriptor, guide and specificity scanner to disclose the new supported arm and actual optional/dynamic phases only after complete-path validation. Retain historical bytes and capture source identities before edits. Final independent adversarial review, exact-head full CI and merged-byte verification precede delivery."

### (B) Per-attempt acceptance, judged on the saved result after the attempt ends
[proposed] **The row set.** Plan §5 defers the native rows to this amendment. These are taken from the plan and generation plan N10, not from #4354.
0. **Controller completion.** The saved result reads `state: completed_pending_independent_review` with `runtime_gates_passed: true` over all 15 runtime gates (`native_execution_engine.py`). N1.9 item 9's `audit_counts` row sits inside the `evidence` gate, so the count stays 15. The gates:
   - terminal, shutdown, first_stop;
   - live_attribution, saved_attribution;
   - phase_history, tool_history;
   - schema, pair, receipts, evidence;
   - observation, accounting;
   - runtime_authority, keep_awake.

   The receipts gate uses the structural floors only, so D109's pending floor doesn't block it.
1. **Readback.** An independent `read_final` reconstructs the selected assembly and binds it to this attempt and its downstream audit. This is criterion 4's saved-result property, read on the live attempt's bytes.
2. **Record rows** (the A11 equivalents):
   - the full and core records validate;
   - duplicate keys are 0;
   - the report totals equal `audit_counts` (#4766), through the explicit equality row inside the `evidence` gate (N1.9 item 9);
   - the five phase-1 structural receipt floors that `check_initial` computes (`native_shared_receipts.py`) are each 0:
     - chunks unreviewed;
     - snippets unverified;
     - addressing slips over #891's tolerance of ceil(verified/200);
     - receipts vacuous;
     - receipt findings.
3. **Tool history**, generation plan N10 mapped to the typed protocol [proposed]:
   - **Permission denials:** zero prescribed or unclassifiable denials.
   - **Ordering.** N10's per-chunk file-tool ordering doesn't apply: the typed protocol's phase 1 writes the full record and the whole original receipt in one stage (`native_shared_generation_v1.md`), and chunks are never dispatched one by one. What applies instead, both shown from the saved `phase_history`:
     - the phase-1 receipt is checked before the seal and `derive_core`;
     - the strict receipt check passes before any typed-audit dispatch.
   - **`receipt_chunks_unopened` is reported only.** The instrument counts permitted read-only shell lookups (`sed -n`, `cat`) as unopened, and the native instruction doesn't impose #709's file-tool duty. A missing measurement is reported as unavailable, not zero.
4. **Clean.** The attempt is clean: an assisted attempt is evidence only and never accepted (D43; plan §1 item 1, §5 row 7, §10). [proposed] The native clean checks, with how each is evidenced:
   - **nothing edited inside the run directory (D53):** the saved-readback byte comparison;
   - **no interrupted write:** the saved-readback and stage journal;
   - **the one-use reservation intact:** shown by the orchestration's reservation record;
   - **no manual intervention** between dispatch and the end of the attempt, other than a stop: an operator attestation in the acceptance record;
   - **no override (D56):** there is no override mechanism natively, so this check is satisfied by construction and recorded as such;
   - **the guard's capture is the last one claimed under the word,** both when the guard was prepared and at the pre-reservation check: the recorded index against the recorded claim count at each, and against the retained captures (N1.8(ac));
   - **the sequence script that ran** is the one the review bundle names: the reviewer recomputes the sha256 of the script's bytes saved in the launch packet and compares it with the bundle's key (N1.8(z), N1.9 items 4 and 10);
   - **a delegated start was inside its direction** (N1.8(aa)): the script's recorded start time is within 30 minutes after the direction's recorded time, and within 30 minutes after the recorded time of the owner's confirmation of the host state;
   - **the reviewers are independent of whoever started the sequence** (N1.3's D12 row);
   - **the account was quiet** (N1.8(ad)): the owner's attestation that every session drawing on the registered account stood down from before the capture until the attempt ended.
5. **The native policy-v1 receipt floor** is `{state: pending, mode: diagnostic_pilot}` (D109).
   - `native_shared_receipts.floor()` returns `state: pending`, `passed: False` with its counters. The acceptance record keeps that raw result and labels the row UNMEASURABLE.
   - It doesn't block acceptance, and it is never reported as a strict success.
   - The measured counters inform a registered native floor before any native replicate (D109).
6. **Blind source review (A12, D36).**
   - **Who:** a fresh Claude blind source-review session plus a Codex CLI pass, neither of which generated or operated the run. [proposed] Neither was started by the session that generated the run or started its sequence (N1.8(ag)).
   - **What:** they review the unchanged originals against the frozen bundle. The plan's A12 scope covers "#1782, #1801/#2924, #1815, #1816 and #2924 dates".
   - **The seed (D36):** a second blind model reviewer writes audit-recall observations, pinned to `original_full`'s sha256, before anyone reads the audit.
   - **The row holds** when the review is complete on that scope, no rejecting-class finding is sustained by the owner, and no evidence stays unresolved (plan §6).
7. **The owner signs the acceptance record** (D36), having adjudicated any disagreement (plan §6).

**"Accepted"** means B0–B4, B6 and B7 hold, with B5 reported (D109). The API-only rows don't apply: the full-phase output cap and the CBORG provider route.

**How N1.8 splits these rows:** (i) decides which rows exist; (j) and (k) decide B3's and B4's content. If (j) or (k) is answered no, that row is revised and re-submitted before registration; the other rows stand.

## N1.5 The first canary, its slice and its stop rule
- **What:** CHORUS, n = 1, descriptive feasibility. Not a replicate (D107, D25). Native production cells are the subject of a separate amendment (D135); nothing here registers one.
- **[proposed] Before the launch: the native production amendment is ratified (N1.8(ah)).**
  - **What existing authority says.** The plan fixes the API arm's floor rule "before any pilot runs", and the later amendment "only computes its value" (plan §8). D109 requires that this canary's measured value inform a registered native floor before any native replicate. Neither says when the native floor rule is fixed.
  - **What the lead proposes.** This canary supplies the reading a native replicate floor is computed from. So the rule that computes it, and with it every other rule of the native production amendment (D135), is ratified before this canary launches. Then no rule of that amendment is chosen after a native outcome it governs.
  - **Where it is checked:** at step 4 below. The coded word is not given before that amendment is ratified, and the launch packet cites the owner's recorded ratification of that file's sha256. The registration's review at step 1 does not wait for it.
  - **What it costs:** the first canary waits on the ratification of a second amendment.
  - **What a no leaves:** D109 as it stands. The production amendment then records when its floor rule was fixed relative to the time this canary's outcome became available, and discloses a selection made after the outcome if that is what happened.
  - The canary's own floor stays pending either way (N1.4(B) row 5).
- **Order of events.** Each step needs the code in N1.9 to be accepted first.
  1. **The registration is reviewed, with its inputs complete.**
     - The two independent reviews of the registration and its packet are complete.
     - The exact-head CI evidence (`ci_sha256`) exists.
     - The bound permission probe (`permission_probe_sha256`) exists.
  2. **The owner writes the statement of launch terms.** [proposed] This statement is what D110 and D111 mean by "the launch word states" and "confirms … in the launch word": the coded word's closed fields can't carry those terms, so the word binds them through the bundle. It states:
     - `budget_guard_usd` "90";
     - the deadline;
     - the maximum starting seven-day utilisation (0.50) and five-hour utilisation (0.25, D118);
     - `max_age_seconds` and the margin;
     - the overage state (disabled) and that the account is quiet (N1.8(ad));
     - the keep-awake policy;
     - the context mode;
     - the capture limit (three, D115).
  3. **The bundle is frozen.** The two reviews and the statement are assembled into the review bundle, and its sha256 is taken.
  4. **The owner gives the coded word** `AUTHORIZE_ONE_NATIVE_ATTEMPT`. Its `review_sha256` names that bundle, and its `authorized_at` is a strict UTC timestamp (N1.9 item 4). [proposed] The word is not given before the native production amendment is ratified (N1.8(ah)).
  5. **The owner, or the lead under N1.3's D12 row, runs the registered capture command** (D115; N1.9 item 3).
     - It runs a tiny live call on the same account, binary, model, effort and context, with a fixed trivial prompt, no repository content, and a capture-only config directory outside every attempt path.
     - It saves the runtime's `rate_limit_event` and its terminal result's `modelUsage`, with the sha256 of the word it ran under.
     - A capture reservation allows at most three captures under this word, and records each one, including stale and failed ones.
     - Captures are not attempts.
  6. **Whoever ran step 5 prepares the guard on the latest capture and dispatches.** [proposed] "Latest" is enforced twice: guard preparation refuses any capture but the last one claimed under the word, and the pre-reservation check, under the lock that protects the reservation, refuses a guard whose capture is no longer the last one claimed (N1.8(ac), N1.9 item 3). Without that, the longer age would let an earlier, more favourable capture back a guard after a later capture had been refused. Subscription guard v2 (N1.9 item 2) admits the attempt only if all of these hold:
     - **[proposed] the seven-day utilisation is ≤ 0.50.** It's stricter than the sources' 0.80 because the window was exhausted on 2026-10-24, the 1M context spends faster, and a canary stopped by the usage limit is lost;
     - **the five-hour utilisation is ≤ 0.25** (D118). Both windows must be present, which is implied by D118's bound under fail-closed admission;
     - **[proposed] both windows are allowed.** A nested window is allowed when its `utilization` is a finite JSON number, not a boolean, with 0 ≤ utilisation < 1, and its `resetsAt` is after both capture and dispatch. Saved nested windows carry no per-window status;
     - **[proposed] a further window type is judged by the same rule when it carries `utilization`, and is recorded but not refused when it doesn't;**
     - the top-level status is allowed or allowed_warning, and overage is explicitly false;
     - **[proposed] One freshness rule with two values:** `captured_at` is no earlier than the word's `authorized_at`, and dispatch occurs within `max_age_seconds` = 1200 of `captured_at`. The owner chose the number 1200 on 2026-11-12 (D136); the chronology half is the lead's proposal. Both stay under one lettered item so that the ratification covers them.
       - **Why not 300.** v6.1 proposed 300, the guard's maximum at the time, before any launch-path timing existed. Three diagnostic runs are now retained, all of 2026-11-11, and none passed. The latest (D132, source `382f0dfd1ce8`) reached the pre-reservation check with the observation 306.53 s old. The two earlier sources were refused at a dispatch check, at 318.89 s and 334.86 s. At `382f0dfd1ce8` the launch's process CPU time alone (243 s) exceeds the 210 s the old terms left before the reservation. That run would have needed at least 397 s to pass the checks it reached, with the 90 s margin kept.
       - **What those runs are.** Each is a synthetic software diagnostic on a loaded host: not a quiet-host measurement, not a production sequence, and stopped before the reservation. The latest starts its launch 10.8 s after a synthetic capture. After a real capture event, production also runs the rest of the live capture call, the capture command's own re-verification, the guard command and the launch command's entry verification. None of those has been timed. The Codex hand-off's rows for them sum to 58 to 309 s, which it labels "an ESTIMATE for a responsive host, not a measured production bound".
       - **Sources.** The timing table is `agy4-freshness-value-table-20261112.json` (sha256 `df5c25b061c21c67db7c4ce3b8bef16762c16aef6bafc403d57cbeb50f59c882`) and the estimate is in `codex-native-critical-path-20261112.md` (sha256 `e407a36ed2bd9e904164c00c593bb1e12095548bcc8305e895043997978c7410`), both on branch `codex/native-efficiency-results-20261111` at commit `0f02aa71633d4752fd5a583bc5d16acf94f5c87c`.
       - **Why 1200.** With the 300 s margin proposed below it allows the reservation up to 900 s after the capture event, against roughly 6 to 10 minutes on that estimate. The reading guards a run of up to 21,600 s against starting above the admission bounds; its greatest age at dispatch moves from 5 minutes to 20. **That reasoning assumes no other session uses the registered account between the capture and the dispatch;** the host terms below require it (N1.8(ad)).
       - **The alternative not taken.** Capturing after the launch's own verification would allow a short age. It needs a redesign of the launch's event order and locks. The lead deferred it as a follow-up, not a gate for the first canary.
       - **Tightening.** The first live attempt reports its capture-to-reservation, reservation-to-dispatch and capture-to-dispatch times (N1.6). A smaller value may then be proposed as a revision;
     - **[proposed] a margin at the reservation:** at the pre-reservation check, `captured_at + max_age_seconds − now` is at least 300 s. Drafts v6.1 to v8 said 90 s.
       - **Why this is open again.** The earlier wording of D136's question named the margin as unchanged. The owner's answer came before the v7 reviews showed what follows, so the lead does not treat the margin as settled and puts a value to the owner (N1.8(u)).
       - **Why 300 and not 90.** One registration re-verification took about 27 s in the D132 run, and this stretch holds two. If both probe commands also ran to their 30 s timeouts, those four alone would be a subtotal near 115 s, more than 90, before the durable writes, the binary hash and the keep-awake. 300 s is about 2.6 times that subtotal. A margin that is too small can spend one of the two attempts at the dispatch check; one that is too large only refuses earlier, which costs a capture. With 300 the reservation has to come within 900 s of the capture event, about 1.5 times the top of the estimate above.
       - **What runs in the stretch it covers** (`native_execution_orchestration.py` at `382f0dfd1ce8`, after `before_reservation()` and before the one-use dispatch check): the attempt's durable records and directories, a registration re-verification, keep-awake acquisition, the runtime probe (`--version` and `auth status`, each with a 30 s timeout) with the binary hash, a second registration re-verification, and the authority join.
       - **That stretch has never been timed.** Every retained run was refused before the reservation. For scale: in the D132 run the stretch between the last dispatch check and the pre-reservation check, which holds one re-verification, took 27 s.
       - [proposed] **So it is measured before registration** (N1.8(ab), N1.9 item 11). The offline complete-path proof of N1.4(A) item 6 records the reservation-to-dispatch time under the registered terms. That proof runs the synthetic launch: an ordinary Python peer, no real binary and no keep-awake. Its report names every operation it substitutes or leaves out (the runtime probe's two commands, the hash of the real binary and the keep-awake acquisition) and says how each is timed. A synthetic time is not a production bound. **One adjusted total decides:** the offline time; plus each of the two probe commands at its duration on the pinned binary where an authorized run has recorded one, and otherwise at its 30 s timeout; plus, for the hash of the real binary and for the keep-awake acquisition, each one's recorded duration, or 5 s where none is recorded. Nothing is counted twice: where the offline time already contains a substitute for one of these operations, the report says so and removes the substitute's duration. The two 5 s figures are placeholders: both operations can be timed without a model call, under D137, and the timed values replace them. Only a run on a host that passes D92's gate can show that the margin is large enough (D125), and the largest such run counts. A run on a loaded host is diagnostic: it can show the margin is too small, and nothing more. **What that costs:** a quiet host. D92's gate failed twice on host load on 2026-11-09 (D125), so the helper sessions stand down for the measurement. If the adjusted total exceeds half the margin, item (u) is revised and ratified again before the registration. Timing a command on the real binary still needs its own authorization. A margin that is too small can spend an attempt; one that is too large only refuses earlier, which costs a capture;
     - the capture's terminal `modelUsage` limits equal the registered limits (D117; every capture is checked, as in N1.2);
     - the capture was made under the word the guard binds;
     - **every launch value equals the statement's** (N1.9 item 4). All of these are registration values, and the guard is prepared from them:
       - the guard's seven-day maximum, five-hour maximum, `max_age_seconds` and margin;
       - the runtime's budget, deadline, keep-awake and context mode.
  - [proposed] **Steps 5 and 6 run as one reviewed sequence** (N1.8(z)). One script runs the capture command, the guard command on that capture, and the launch command, with no pause between them. Any refusal or error stops it, and it has **no automatic retry**. A re-capture under D115 is a new start of the whole sequence, made by the owner or under a new direction, and is possible only before the attempt is reserved; a consumed attempt is never retried. The script is reviewed with the registration packet and named by sha256 in the review bundle; it copies its own bytes into the launch packet, with each command's output and its times, and the reviewer recomputes the sha256 from those bytes (N1.9 items 4 and 10). Who starts it is N1.3's D12 row.
  - **A capture that fails the margin** is refused before the attempt's reservation, so it doesn't spend the attempt, and the owner, or the lead under a new direction, re-captures within D115's three.
    - The margin makes a stale-at-dispatch capture unlikely, not impossible.
    - A capture that is fresh at the reservation but stale at dispatch stops the attempt after its reservation. That is an environment stop, an admission failure at the guard's one-use dispatch check, and it counts as an attempt (D113).
  - [proposed] **After three failed captures,** the capture reservation refuses a fourth. The path is a new word for the same registration, if it's still within its validity window. A new word gets three new captures, and no attempt is consumed.
    - This **extends D115**, which says "up to three admission-capture calls for that attempt".
    - A newer word supersedes an earlier one for the same `attempt_id`, so only one word is valid at a time.

  The observation is caller-supplied evidence, not authenticated account state. The threshold is a start-admission rule, not a mid-run allowance.
- **Overage:** disabled for the attempt's whole duration (D111). It's an owner account setting that the statement confirms. `isUsingOverage: false` shows only that no overage was used.
- **Dollar guard:** `runtime.budget_guard_usd: "90"`, a decimal string producing `--max-budget-usd 90` (D110).
  - The runtime enforces it on its own cost estimate.
  - Afterwards, the controller's accounting gate fails the attempt if the reported cost exceeds it.
  - It isn't independently metered billing.
- **Host:**
  - [proposed] the registered keep-awake policy `macos_iokit_ims_v1` (idle, disk and system sleep), on AC power;
  - [proposed] the operator holds the quiet-window lock for the attempt. That's a coordination protocol, not a controller gate, and not proof of a quiet host;
  - [proposed] **the account is quiet (N1.8(ad)).** Every session that draws on the registered account stands down from before the capture until the attempt ends, whoever starts the sequence. Such a session does not monitor the attempt either, because a session spends the account by working: monitoring is by a script or by a session on another account. The owner's statement confirms it and the acceptance record attests it. Nothing in the controller enforces it.
- **What the keep-awake enforces:** a failure to acquire it refuses before dispatch, and a failed release fails the `keep_awake` cleanup gate. A mid-run sleep or loss of the assertion is not detected. Forced sleep, lid closure, thermal or battery policy and power loss aren't prevented.
- **Deadline** [proposed]: 21,600 s (6 h) of wall time from dispatch. That's the sources' value, re-validated in D14.
- **Stops, and who enforces them:**
  - **The controller** stops at the first of:
    - the deadline;
    - subscription guard v2's `observe` stop on any window that is no longer allowed by the rule above, or on overage;
    - any refusal or first error at a supervisor boundary.
  - **The runtime** stops itself at its `--max-budget-usd` estimate.
  - **A mid-run five-hour exhaustion** is a usage stop, and it counts as an attempt (D118, D113). The 6 h deadline crosses at least one five-hour reset, and the 1M context spends faster, so this is possible whatever the admission reading.
  - [proposed] **The owner, as operator (D12),** may stop the attempt manually at any time, by the signal and cleanup procedure the launch packet names.
  - [proposed] **D107's stop rule is read as follows.** The usage limit is the live stop above. "any acceptance-row failure" is judged after the attempt on the saved result, because the rows are properties of that result: a failure rejects the attempt, and it is not a mid-run stop.
- **After a stop or a rejection:**
  - outputs, the stop reason and the guard snapshot are preserved. Every attempt is retained, stopped and rejected ones included (plan §7). For a stopped attempt, the after-run readings are reported as unverified, because saved-observation validation applies only to a completed attempt;
  - **classification (D113):**
    - a **transport, budget or environment stop** (deadline, usage, dollar guard, host) is not a scientific rejection;
    - a **rule-level rejection** under N1.4(B) ends the native shared-v1 cell only, not the API arm's generic_v10;
    - plan §10's API-specific rows (the full-phase cap, `api_usage`, the item 5 rows 5–6) don't apply;
  - **at most two native canary attempts** (D113, D07);
  - a stopped attempt is never resumed or re-run under its label (plan §13, D56, generation plan N9). Any new attempt needs a new label, registration and word, and it counts against the two.
- **What the coded word binds.** Its fields are closed (`native_execution_registration_v2.py`):
  - the binding keys: `registration_sha256`, `attempt_id`, `source_commit` and `dependencies_sha256`;
  - `kind`, `version`, `owner`, `authorized_at` and `word`;
  - `review_sha256`, `ci_sha256` and `permission_probe_sha256`.

  The budget, deadline and keep-awake reach the word through the registration hash. Every other launch term reaches it through `review_sha256`'s bundle. The real-binary probe is authorized separately, and that authorization is not a generation word.
- **Supersessions:** this procedure supersedes generation plan N9's `caffeinate -ims` (now the registered keep-awake policy) and its codex operator (now the owner, or the lead on the owner's direction, D12).

## N1.6 Recording and comparison
**Recorded:**
- the arm, `claudecode_direct`;
- the receipt checker v4 instrument string, and separately the identities of the two D105 secondary measures;
- the effort literal and its basis;
- the thinking setting and its source;
- the runtime limits and their basis (D112, D116);
- the three model observations: requested and init, returned per assistant message, and the terminal accounting key (N1.2);
- the binary version and the sha256 of its pinned copy;
- the account kind and label;
- every capture, with its index and the number of captures claimed under the word, as checked when the guard was prepared and again at the pre-reservation check;
- the capture-to-reservation, reservation-to-dispatch and capture-to-dispatch times;
- who started the command sequence and under which direction, the kind of account the starting session ran on (never an identifier), and the sequence script's sha256;
- the owner's attestation that the sessions drawing on the registered account stood down;
- for a delegated start, the direction's recorded time, the recorded time of the owner's confirmation of the host state, and the script's recorded start time;
- the guard's admission readings (seven-day, five-hour and any further window), its after-run readings (first, last and highest per window; unverified for a stopped attempt), and the guard snapshot.

**The cross-arm contrast** follows plan §1 item 5, with the effort confound of plan §4. Under plan §2 these differences are declared, and the N2 declaration (`be0bd05821256212e89e4d011ba6b30a780e299b`), or the U5 successor that names it by hash, carries them:
- **effort:** explicit high, against the provider default;
- **runtime and transport:** a subscription CLI, not a provider route;
- **tools:** Read, Write and Bash plus the permitted read-only lookups, against the API arm's no-tool boundary;
- **staged exposure:** the typed-helper phases, against the API arm's phase requests;
- **context:** 1M (D112), against the API arm's room;
- **schema:** 3.2.1, against the API arm's ratified 3.1.0, unless the comparison registration moves by its own amendment. For the record: the A21 registration of 2026-11-11 (roster `d49cc352…`) was built and launched on main, which carries 3.2.1, and no API-arm schema amendment is on record. That states what was built; it ratifies nothing, and it is open for the comparison registration;
- **normalisation:** none at write time on the native arm, against the API arm's write-time normaliser;
- **paths:** the native instruction carries absolute local paths: the bundle, the manifest and the chunk manifest, and the interpreter, schema and stage paths. The command-permission and replay contracts require those exact paths (D126). In anything published (records, reviews, papers) they are redacted, and the redaction is recorded (D126). [proposed] Redaction is applied to published copies only: nothing inside the run directory is edited (D53), and each published copy's record names the sha256 of the unredacted original and the classes of path removed (N1.8(af));
- **protocol:** the D91 shared-v1 differences.

**Native ratings** stay deferred until a native canary is accepted under N1.4(B). Their route is chosen by a separately ratified rating registration, not here.

**Sequencing** [proposed, N1.8(y)]: native integration lands first, and the API comparison registration is then rebuilt on native-integrated main (D89, D93, D129). D35's freeze starts at that rebuilt registration, not at the A21 roster of 2026-11-11, and native changes that land before it are not "later" changes.
- **What happened in between.** D131 (2026-11-11) released the hold for one rebuild and recorded: "Consequence under D93: D35's freeze starts at this rebuilt registration. Changes to its pinned files that land afterwards, native ones included, are "later" changes." The A21 registration (roster `d49cc3529a11e60716cde4affc6f5deec521b861576fcae6b961e2f74060dd63`) was built on main `7ad8c9e72` and launched once (D133). It ended on a provider refusal at its first typed-audit call (#5874) and is spent. D134 (2026-11-12) then directed that the native arm is the main result and the API route is for comparison.
- **What a yes to (y) does.** D35 says: "Any later runner change (for example, Track N PRs) needs a CHORUS byte-parity test **and** one step-7 diagnostic CHORUS canary." With the freeze at roster `d49cc352…`, native integration would need both, and the second is a paid run on the API route. A yes moves the freeze to the next rebuilt comparison registration. Native integration then lands without them, and that registration is reviewed in full when it is built.
- **What a no leaves.** D131's consequence stands: native integration changes files that roster pins, so it needs the byte-parity test and the diagnostic canary before it lands.
- **The lead reads D134 as restoring the order above.** The owner has not said so in those words, so it is a lettered item.

## N1.7 What this amendment does not change, and what it does
**Unchanged:**
- the plan file and its sha256 `b4a4f9a5…`;
- the A21 registration of 2026-11-05 and its packet (roster `d4ac7f88…`), which bind that sha256, and the rebuilt A21 registration of 2026-11-11 (roster `d49cc352…`);
- any API-arm registration;
- P4a amendment 1 for the API arm;
- any historical decision or record.

**Changed, for the native arm only:**
- D71(a)'s schema, under N1.1 [proposed];
- generation plan N9's keep-awake form and operator, under N1.5;
- D43's rule on who runs the registered commands, under N1.3's D12 row [proposed], and only when the owner directs it;
- D43's clause "agy and claude monitor read-only", under N1.8(ad) [proposed]: no session that draws on the registered account monitors the attempt, whoever starts the sequence;
- what "independent" means for a reviewer, under N1.8(ae) and N1.8(ag) [proposed].

**Changed, and not only for the native arm:**
- where D35's freeze starts, under N1.6 and N1.8(y) [proposed]. D131 recorded it at the A21 roster of 2026-11-11; a yes moves it to the next rebuilt comparison registration.

## N1.8 Ratification: the owner names this file's sha256 at a commit, and answers each lettered item
Each letter is one decision, and a "yes" adopts exactly the value given.
- **(a)** No auxiliary models, accepting that an auxiliary call stops the attempt (N1.2).
- **(b)** The pinned executable is a durable copy outside the auto-updater's path (N1.2, D11).
- **(c)** D13: the literal launch argv recorded verbatim (#4162).
- **(d)** D13: any change to a pinned item is a new registration.
- **(e)** D13: the transcript-based receipt origin is the "receipt origin" D107 names (N1.1).
- **(f)** D18: its old meaning (the #4354 offline time box) is closed.
- **(g)** D18: the registration is valid for two weeks from its registration commit's author date.
- **(h)** Schema 3.2.1 for the native arm, superseding D71(a) for that arm only (N1.1).
- **(i)** The N1.4(B) row set, B0–B7.
- **(j)** B3: the typed-protocol ordering mapping, with `receipt_chunks_unopened` reported only.
- **(k)** B4: the native clean checks and their evidence.
- **(l)** Admission: starting seven-day utilisation ≤ 0.50. D118's record restates this value; a "no" here supersedes D118's restated 0.50 for this amendment.
- **(m)** Admission: a window is allowed when its utilisation is a finite non-boolean number with 0 ≤ u < 1 and its reset is after capture and dispatch. D118 sets the five-hour bound, and presence of both windows is implied by it.
- **(n)** Admission: a further window judged by the same rule when it carries `utilization`, and recorded but not refused otherwise.
- **(o)** Freshness, one rule with two values: `captured_at` ≥ the word's `authorized_at`, and `max_age_seconds` = 1200 (v6.1 proposed 300; N1.5 gives the timing). The owner chose 1200 on 2026-11-12 (D136). A no requires a revised freshness clause and a renewed ratification before registration; it does not reinstate the earlier 300 s proposal. None of the three retained diagnostic runs passed under 300 s.
- **(p)** Deadline: 21,600 s.
- **(q)** Host: keep-awake `macos_iokit_ims_v1` on AC power, accepting that mid-run loss is undetected.
- **(r)** Host: the quiet-window lock held by the operator for the attempt.
- **(s)** The owner may stop the attempt manually, as operator.
- **(t)** D107's stop rule read as in N1.5: usage is a live stop, and acceptance-row failures are judged after the attempt.
- **(u)** Freshness margin: at least 300 s left at the pre-reservation check (drafts v6.1 to v8 said 90 s; N1.5 gives the reason). D136 settled the age; on the margin the record holds only the lead's summary and the lead's later correction of it (Authority), so the owner is asked here. A no leaves 90 s. With both probe commands unmeasured, their 60 s allowance alone exceeds half of 90, so keeping 90 requires item (ab)'s complete adjusted total to be no greater than 45 s.
- **(v)** After three failed captures: a new word for the same registration within its validity window, with no attempt consumed. This extends D115, and the newer word supersedes the earlier one.
- **(w)** The owner statement is how the word states D110's and D111's terms, bound through the review bundle.
- **(x)** Every capture's limits are cross-checked, not only the first (stricter than D117).
- **(y)** Sequencing: native integration lands first, and the API comparison registration is rebuilt on native-integrated main afterwards. D35's freeze starts at that rebuilt registration, not at the A21 roster of 2026-11-11 (`d49cc352…`), so native integration lands without D35's byte-parity test and paid diagnostic canary (N1.6). This is the lead's reading of D134. A no leaves D131's freeze at that roster.
- **(z)** Operation: the capture, guard and launch commands run as one reviewed sequence with no automatic retry, from a script named by sha256 in the review bundle (N1.5, N1.9 item 10). A no means the provisions that depend on the script are revised and re-submitted before registration: N1.3's D12 and D13 rows, N1.4(B) row 4, N1.5, N1.9 item 10 and item (aa).
- **(aa)** Delegated start: after giving the word, the owner may direct the lead to start that sequence, within the limits of N1.3's D12 row: among them the two 30-minute limits, and the refusal of a direction to a session that started a reviewer of the registration. It needs item (z). A no leaves D43's rule that the owner starts it, subject to item (ad).
- **(ab)** The reservation-to-dispatch time is measured offline before registration, on a host that passes D92's gate. The adjusted total adds each runtime-probe command at its recorded duration on the pinned binary or else its 30 s timeout, and the binary hash and the keep-awake each at its recorded duration or else 5 s. A run on a loaded host can only show that the margin is too small. Above half the margin, item (u) is revised and ratified again (N1.5).
- **(ac)** The guard's capture is the last one claimed under the word: guard preparation refuses any other, the pre-reservation check refuses a guard whose capture is no longer the last one claimed, and each check records the index and the claim count (N1.5, N1.9 item 3).
- **(ad)** The account is quiet: every session that draws on the registered account stands down from before the capture until the attempt ends, and none of them monitors it; the owner's statement confirms it and the owner attests it in the acceptance record (N1.5).
- **(ae)** A fresh session started by the author counts as independent of the author for a review of a document or a registration, when it gets the artifacts and none of the author's conclusions and its report says who started it (N1.3). It covers the reviews this amendment calls for: of this amendment itself and of the native registration and its packet. Item (aa) bars a session that started such a reviewer from starting that registration's sequence. A no means the Claude reviews of this amendment, all of which were started by the author's session, do not count as independent, and a Claude review by a session the author did not start is made before ratification.
- **(af)** The redaction record: redaction on published copies only, each naming the unredacted original's sha256 and the classes of path removed (N1.6).
- **(ag)** For row B6's blind source review, neither reviewer is a session started by the session that generated the run or started its sequence (N1.3, N1.4(B) row 6).
- **(ah)** The native production amendment is ratified before this canary's word is given, so that none of its rules, the floor rule among them, is chosen after a native outcome it governs (N1.5). A no leaves D109 as it stands, and that amendment then records when its floor rule was fixed relative to this canary's outcome.

## N1.9 Code that must exist and be accepted before registration
These are engineering prerequisites, not choices. Drafts v1 to v6.1 said they were to be built as native unit U4b and that none was delivered. As of v11 the U4b work is on native branches only (source `382f0dfd1ce8`). That source carries schema 3.2.0 and does not contain main `7ad8c9e72`; a local merge of it with main exists (`b11931410305`), unpublished. Item 2's 1200 is not met there: the policy and the guard both still say 300. The first full CI run on the native stack (42976790438, head `1a137b588604`) ended in failure: seven jobs stopped at collection (#5875), six shards failed and two were cancelled at the time limit. Its inventory is `lead-ci-run-42976790438-failures-20261112.json` on branch `codex/native-efficiency-results-20261111` at commit `67274cb2eab87c9ff18cc6b1dc0970301059b845`. Which of the items below are complete is established by the final integrated review (N1.4(A) item 7), not by this sentence. The registration cites each one's merged commit.

**The U4b work files** are in `notes/coordination/`. They're not in the repository's tracked tree, so they're cited by sha256:
- the brief `2026-11-08-codex-native-u4b.md`: `af5cb901c0a77f75926d0c6f0e14c6d198ce3415a5cbe87fbce57f567818037e`;
- addendum 1: `ba25e02d942c72baab1c25dc658fc6e4ed431439532083f89f69bc0a2195e90c`;
- addendum 2: `9c8783fa8c108ed190bd498ce5808afa2601efb5ba601dfc4d7176b556f07aee`;
- addendum 3: `4472fde84eb588fde15217294b21c8c48ee2f3f3b40cd88129d83b1157aa0240` (including its item 8, from the v5 review).

Addenda 2 and 3 and D115–D117 supersede the brief's items 3, 5 and 6 and addendum 1's single capture. Where they differ, this list governs.
1. **D114:** `toolchain()` narrowed to the generation agents for the native shared route; the specificity scanner run over the exposed set.
2. **Subscription guard v2** (v1 kept byte-identical):
   - admission requires the seven-day (≤ 0.50) and five-hour (≤ 0.25) windows and applies N1.5's window rule and domain;
   - `max_age_seconds` = 1200 in both places it lives: the registered admission policy requires exactly that value (`native_u4b_policy.py`), and guard v2 permits it (`native_subscription_guard_v2.py`). Both agree with the owner statement (N1.8(o); the value was 300). Guard v1 stays byte-identical;
   - the margin of N1.8(u) at the pre-reservation check: the registered policy requires exactly that value, and it agrees with the owner statement;
   - the capture-limits cross-check on every capture (D117), whose mismatch refuses the registration before any reservation;
   - refusal of a capture made under a word other than the one the guard binds;
   - the chronology check against a parsed `authorized_at`;
   - `observe` stops on any nested window that is no longer allowed;
   - the snapshot keeps the admission and after-run readings, with saved-readback validation; stopped-attempt readings are labelled unverified.
3. **The registered capture command** (D115):
   - a capture-only config directory outside every attempt path;
   - a capture reservation with a maximum of three per word, refusing a fourth;
   - each capture saves its `rate_limit_event`, its terminal `modelUsage` and the sha256 of its word;
   - a newer word supersedes an earlier one for the same `attempt_id`;
   - every capture recorded;
   - captures never consume the attempt's reservation;
   - guard preparation refuses a capture that is not the last one claimed under the word, and the pre-reservation check, under the lock that protects the reservation, refuses a guard whose capture is no longer the last one claimed. Each check records the index and the claim count (N1.8(ac)).
4. **The review bundle and owner statement.** `review_sha256` names a bundle of the two independent reviews, the owner statement and, under N1.8(z), the sequence script's sha256 in a closed key that the reader checks. Under N1.8(ad) the statement carries the owner's confirmation that the account is quiet, in a closed key.
   - The v2 review reader is replaced or extended to accept it. It checks each review's independence from both author and operator, with replay and readback validation.
   - `authorized_at` is a strict ISO-8601 UTC timestamp.
   - An equality check refuses the attempt if any launch value differs from the statement:
     - the guard's seven-day maximum, five-hour maximum, `max_age_seconds` or margin;
     - the runtime's budget, deadline, keep-awake or context mode.
5. **The runtime declaration under D112, D116 and D117:**
   - the two-probe sequence: the observation probe's `limits`, then the bound permission probe under the final runtime, whose `limits_basis` names the observation probe by sha256.
     - A `limits_basis` naming the bound probe itself refuses.
     - So does a provisional runtime that differs from the final one in any field other than `limits`, `limits_basis` and the thinking field;
   - the declared 1M alias pair, gated exactly in the runtime gates **and in the saved-probe verifier** (`native_shared_permissions.py`), with the scripted provider returning `claude-opus-5` in messages;
   - tested on a saved 1M transcript.
6. **The thinking setting:** a required field of the runtime declaration, taken from the observation probe's captured request body. A missing value refuses.
7. **D11's pinned executable:** the durable copy, if N1.8(b) is ratified.
8. **`receipt_chunks_unopened`** wired with its receipt and manifest inputs, reported only.
9. **An explicit `audit_counts` equality row** inside the `evidence` gate: report totals against the derived audit, with the compared artifacts recorded. Missing or mismatched data refuses.
10. **The sequence script** (N1.8(z)): one script that runs the capture command, the guard command on that capture and the launch command, stops on any refusal or error and never retries. It copies its own bytes into the launch packet, with each command's output and its times, so that its sha256 is recomputed by the reviewer and not reported by the script. For a delegated start it takes the direction's recorded time and the recorded time of the owner's confirmation of the host state, and before the capture it refuses to start unless it is within 30 minutes after each. It is reviewed with the registration packet and named by sha256 in the review bundle (item 4).
11. **The reservation-to-dispatch measurement** (N1.8(ab)): the offline complete-path proof records that time under the registered terms, and its report names each substituted operation and how it is timed.
