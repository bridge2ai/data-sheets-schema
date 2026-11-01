# generic_v10 analysis plan, P4a amendment 1: schema 3.1.0 under D66

**Status: draft v3.1, written by claude (lead) on 2026-10-31.**
- **v1 → v2:** for the 13 findings of the Claude review (`plans/reviews/p4a1_7b7dc67a1_claude_review_2026-10-30.md`) and the 5 of the Codex CLI pass (`plans/reviews/p4a1_7b7dc67a1_codex_review_2026-10-30.md`).
- **v2 → v3:** for the Claude re-review of v2 (N1–N9, sent by message and recorded in STATUS) and the Codex v2 pass (`plans/reviews/p4a1v2_0c702597d_codex_review_2026-10-31.md`).
- **v3:** both narrow re-checks found it ratifiable as is (the Claude re-check by message; Codex at `plans/reviews/p4a1v3_38d9466c8_codex_recheck_2026-10-31.md`).
- **v3.1:** applies the Claude re-check's four optional wording nits only.
- **It is not binding until** a Claude reviewer and a Codex CLI pass re-review it (each finding filed), and the owner ratifies it by naming its sha256 and answering the yes/no list in §7.

## Authority
- **The plan being amended:** `notes/generic_v10_analysis_plan.md`, ratified at commit `5b17ae079c8eb1fa4abdda3261054bfd22e4c2f1`, sha256 `b4a4f9a596173d3bdeb817b01ea53fb1a1d77574e121c7cecaf6f63b67fd4b4b` (D65), and merged by #5163. That file is not edited; this amendment stands beside it.
- **The plan's step 3:** "Its review checks the composed condition against this ratified text; any deviation needs a P4a amendment before the launch word."
- **D66** (owner, 2026-10-29T00:28:46Z, generality finding F6): `data_substrate` gets declared, neutral term sources. It is model-facing, so under D35 it lands before the A21 rebuild.
- **The owner's standing rule** (2026-10-28T23:37Z): "the methods need to be generalized which also means no specific interventions or fixes unless they are part of a generalized approach".
- **Choices that are the lead's, not D66's text,** and so are put to the owner here (§7):
  - declaring the `EDAM` prefix, generality review N7;
  - the exact `data_substrate` description, P4a review finding 4.

## 1. What changes in the plan's text
1. **Line 922** ("Schema: 2.0.0 against 3.0.0, and the change in the digest's term source") now reads:
   > "**Schema: 2.0.0 against 3.1.0** (D66), and the changes in the digest's term sources: `data_topic`'s GO, MeSH, EFO and NCIT (already rendered under 3.0.0's code; absent in v8's code), and, from 3.1.0, `data_substrate`'s EDAM Data, EDAM Format and IANA media types, with the `EDAM` prefix declared (see amendment 1, §3)."

   Its two sub-bullets are unchanged.
2. **Line 1450** ("schema 2.0.0 and 3.0.0 records differ visibly") now reads:
   > "schema 2.0.0 and 3.1.0 records differ visibly, including, where present, `data_substrate` terms in EDAM or IANA form (amendment 1, §3)."

No other plan text changes.

## 2. What changes in the A21 condition: model-facing content
**The schema edit, 3.0.0 → 3.1.0:**
- **Range, `values_from` and validation are unchanged.** No range, constraint or required slot moves; the JSON Schema changes only in the description and the version. The release history keeps 3.0.0's hashes.
- **The annotation:** `data_substrate` gains `d4d:termSources: "EDAM Data, EDAM Format, IANA media types"`.
- **The prefix:** `EDAM: http://edamontology.org/` is declared, in `D4D_Base_import.yaml`, so the core schema sees it too.
- **The description** of `data_substrate`, quoted exactly:
  - **3.0.0:** "Type of data (e.g., raw text, images) as a term from the pinned standards registry. A *term*, not a description: prose characterising the instances — "multimodal per-participant records comprising tabular survey and clinical data" — belongs in `instance_type`, which is ranged `string` for exactly that. Where no registry term fits, prefer omission here and describe it there."
  - **3.1.0:** "Type or format of data (e.g., raw text, images): an EDAM Data or Format term or an IANA media type, written as a CURIE with the schema's declared `EDAM` or `mediatypes` prefix, when the documents supply one; or a term from the selected profile's pinned standards registry. A *term*, not a description: prose characterising the instances — "multimodal per-participant records comprising tabular survey and clinical data" — belongs in `instance_type`, which is ranged `string` for exactly that. Where no declared term fits, prefer omission here and describe it there."
  - **Why this wording:** it asks for the CURIE form that the pinned v10 prompt requires (`d4d_generic_arm_prompt_v10.md:145–156`: a resolver URL in a `uriorcurie` slot whose prefix is declared is a defect). It also keeps the digest's condition, "when the documents supply one".
- **The release identity bound by this amendment:** 3.1.0's full merged sha256 `9a821e6a08e8fe8c6b0e2fd1d4bef9e5d4ee3740722b81ab7620c315287bc8da` and core merged sha256 `2bb8827c45a4dac40e834064a65c95cfc13d258b129c3aa1b9cbccba9ef624db` (G1 round 2, `31a086e0f`). The binding is to these, not to a commit, because G1 lands on main by cherry-pick.

**Where the change reaches a request.** These are rules, not one run's figures:
- **The digest insertion** is record-independent. After "`data_substrate` draws from" the digest gains exactly " a term from EDAM Data, EDAM Format, IANA media types (the source's own identifier, as an IRI or CURIE, when the documents supply one);", which is 135 bytes, in every request that carries the digest: `full`, its receipt completion, and the reconcile and report family. No typed-audit request (worker, omission or integration) carries the digest.
- **The description** appears wherever a request renders the schema context with `data_substrate` retained:
  - on the shared-v1 route:
    - the reconcile and report family, and the omission's outer schema context, when the record has an Instance owner;
    - the omission's inner typed request, always;
    - each worker assigned a `data_substrate` leaf;
  - **on BC1's route (A21's condition, D58/D59): every typed-audit request,** because BC1's context keeps the full reachable descriptions whatever a worker is assigned (`bc1_context.py`).
- **The schema catalog's** bytes and sha256 fields change, keeping their length, in every request that carries them. Identity pins move as described below.

**The measurement on the shared-v1 route** is a regression proof of G1's delta, not A21's route. It was captured offline by G1 round 2 (`plans/reviews/generality_g1_round2_byte_proof_2026-10-30.md`):
- the step-0 base `55c7b94b8` against `31a086e0f`;
- the carries are the archived 2026-10-22a CHORUS intermediates;
- the typed-audit requests come from the runtime builders;
- the JSON is canonical; only the deltas carry over, because absolute sizes depend on the label and path.

| Phase | Δ bytes | Status |
|---|---|---|
| `full` | +135 | measured |
| `full_receipt_completion` | +135 | measured |
| `reconcile_full`, `report`, `report_after_repair`, `report_regate` | +324 | measured |
| typed-audit omission | +378 | measured |
| typed-audit worker assigned `data_substrate` (worker_0002 in these carries) | +189 | measured |
| other typed-audit workers | 0 | measured |
| typed-audit integration | +189 | expected (needs responses; not capturable offline) |
| `repair_full`, `full_readdress` | — | not invoked in these carries |
| core, `reconcile_core`, `repair_core` | — | deterministic, no model call |

**On BC1's route, A21's actual condition.** This was measured offline (`plans/reviews/bc1_route_byte_proof_2026-10-31.md`; tools in `plans/reviews/bc1_route_byte_proof_tools_2026-10-31/`):
- **Before:** BC1's integration packet `d00acf1e7` at schema 3.0.0 (full `eb543e15…`, core `09907cf8…`). **After:** the same, with exactly G1's schema-source changes, regenerated to 3.1.0 (full `9a821e6a…`, core `2bb8827c…`, matching the identity bound above).
- **The carries:** the same 2026-10-22a CHORUS carries.
- **The protected file:** the packet renders only with the reviewed `shared_generation.py` integration proposal. It was applied identically before and after, in a disposable scratch copy only.

| Request (BC1 route) | Δ bytes |
|---|---|
| `full`, `full_receipt_completion` | +135 |
| `reconcile_full`, `report` | +324 |
| typed-audit omission, every worker, and every integration request (group and final, every cap and escape scenario) | **+624** each |
| `report_regate`, `report_after_repair` | +324 expected (the same renderer as `report`); re-captured at the registration review |
| `repair_full`, `full_readdress` | covered by the registration review's re-capture |

**Per occurrence:**
- the digest insertion: +135;
- the `data_substrate` description: +189;
- **the `d4d:termSources` annotation: +123 per catalog.** BC1's typed requests carry both the full and the core catalog with slot definitions intact; the shared-v1 route trims annotations;
- the prefix declaration: 0;
- the catalog pin and hash fields: 0 net.

So each BC1 typed request adds 2×189 + 2×123 = 624. The integration rows are offline sizing scenarios with placeholder future responses, and BC1's `reconcile_full` and `report` used the empty-future audit-carry scenario. The schema-only deltas depend on neither.

**At the registration review** (plan step 3), the composed A21 head is re-captured the same way, before (G1's schema commits reverted on a scratch copy) and after. Any change that does not split wholly into these kinds and sizes is a deviation, needing a further amendment before the launch word.

**The registration identity** moves through the full and core schema pins, and through `request_code_sha256` for `api_runner.py` (the D67 `tuned` refusal), `profile_identity.py`, `provenance.py` and `profiles.py` (G1 N3 and F18).

**Outside A21's API generation wire.** These changes are disclosed here; their existing authorization boundaries are unchanged:
- **The native arm** reads the schema files directly, so it sees the description, the annotation, the prefix and `version: 3.1.0`. The consequences belong to the native amendment (item 43).
- **The fitness-judge specification** (`evidence_score.py`) renders slot descriptions and term sources. The support judge stays excluded from the predictions pending calibration (plan lines 1801–1807).
- **Interactive and native examples:** G1 neutralised them, and changed the `d4d-review-record` agent text and its `_preimages.json` pin. That agent has no verdict role (plan §16).
- **Human-readable rendering:** the "Diabetes Status" grouping was dropped. It is rendering only, and both arms are alike.

## 3. What this adds to the declared confounds, and how it is measured
**The comparator.** A21's registered canary baseline is v8 `2026-09-04f` on schema 2.0.0 (plan line 1186). The 3.0.0 CHORUS canaries 2026-10-20a and 2026-10-22a are evidence only (D40).

**A21's acceptance rules are unchanged.** Under D64 item 30 (plan lines 1021–1024), comparing the pilot with v8's worst on these metrics is evidence, not a rejection gate.

**The prefix tables now differ between the arms.** v8's code, 2.0.0 and 3.0.0 declare the same 38 prefixes; 3.1.0 adds `EDAM`. This qualifies plan lines 949 (Grounding) and 954 ("Form: current on both sides"). On the API arm, the prefix declaration itself is not rendered in any request; the 3.1.0 description names the `EDAM` and `mediatypes` prefixes to the model. The prefix also changes persisted identifier form, through the write-time rewrite below, and that form can enter later request carries, as well as changing measurement.

**Four measurement effects.** A changed count in any of these is not improved grounding or term membership:
- **The write-time normaliser** on the API path now compacts an EDAM IRI in a `uriorcurie` slot to a CURIE, so `http://edamontology.org/format_3752` becomes `EDAM:format_3752`. IANA media types became `mediatypes:` under every version. Each rewrite is logged in the record's `normalisation.identifier_form`.
- **The undeclared-prefix counter** (`grounding.undeclared_prefixes`, which the canary reads) no longer counts `EDAM:` or `edam:`.
- **The resolver-URL detector:** `http://edamontology.org/…` in a `uriorcurie` slot is now a `resolver_url_in_identifier_slot` finding (`grounding.declared_bases_of`). On the API arm, the normaliser compacts the scalar and list spellings it supports before checking, so those EDAM URLs do not count. Forms it skips, such as a YAML block scalar (`api_runner.normalise_identifier_form`), survive and can still be findings. The native arm has no normaliser, so there an EDAM URL is a new finding (item 43). Observed counts are reported as observed, separately from this mechanism.
- **Identifier classification** (`identifiers.classify`, used by the identifier audit, `d4d runs identifiers`):
  - **What moves:** under 3.1.0, `EDAM:format_3752` is `CURIE_DECLARED`; under 2.0.0 and 3.0.0 it was `CURIE_UNDECLARED`, which counts as unresolvable. So the audit's offenders, its unresolvable total and share, and its per-slot counts change, across every identifier-ranged slot and not only `data_substrate`.
  - **Case:** classification is case-sensitive, so lower-case `edam:` stays undeclared there. The canary's undeclared-prefix counter lowercases, and excludes both.
  - **Which schema it reads:** `identifiers.audit` uses the schema it is given, by default the installed full schema. So a default current-schema audit of the corpus can reclassify historical records. The provenance-aware form and grounding checks recover the run's own schema (`run_schema.identifier_rules`) and report any fallback.
  - **What it does not establish:** declaring a prefix establishes neither ontology membership nor source support.

**The semantic broadening.** "Type" became "Type or format", so v10 may record a data format where v8 recorded a data type.

**The reporting rule: supplementary and descriptive only.** Any report of `data_substrate` values may tabulate them by source (B2AI_SUBSTRATE, EDAM, mediatypes, other IRI or CURIE, prose). That tabulation is supplementary: it changes no registered primary numerator, denominator, pool, threshold or gate, and binds no P4b choice (items 40 and 41).

## 4. Changes that leave the plan's text unchanged
These are recorded so that the registration review can check them.
- **Context synthesis, manifest selection and source policy** (G1 F2, F3, F7, F19). The committed omission contexts regenerate byte-identically, so A21's context bytes are unchanged.
- **D67:** `tuned` is refused for new registrations, and historical replay still works.
- **Cost bounds** (F10) come from declared or measured data, resolved in code (`52c64dfbd`). The A21 operator readout bounds the first `full` call from the registration at $8.65.
- **Archive sources** (F11) are declared per project.
- **Profile reading** (F18; G1 round 2):
  - an unknown profile is refused;
  - a profile-less record reads as the historical study profile **when its recorded `repo.commit` does not descend from the profiles commit `e78e4bb56`**;
  - the date is a secondary signal, used only where no commit is recorded;
  - with neither, the record is refused;
  - reading by commit needs a local checkout, a resolvable object and unshallow history (main's CI fetches full history). A missing object is accepted only through a provenance witness at `e78e4bb56^` that records the same commit. Otherwise the record is refused, so this reading depends on the environment. A21's records carry `schema.profile`, so A21 is unaffected.

  So D64 item 14(d)'s new run of the historical v8 code reads as the study profile, as the v8 comparators do. The 286 committed records read as before.
- **Rubric v5** (F8). **This amendment does not authorize v5.** v5 is outside line 1469 and item 41's options. Substituting it into any registered comparison would need its own reviewed and ratified prospective analysis amendment, before any governed confirmatory outcome, plus its evaluation registration and word. It is not an ordinary P4b choice. It is distinct from the receipts instrument v5, which is inactive.
- **A dependency (G1 review N6):** BC1's source parser rejects the new term-source names. G2 fixes it before the A21 registration is rebuilt. If G2 slipped past the rebuild, the fix would be a post-freeze runner change under D35. A21 (bridge2ai) is unaffected either way. A neutral registration refused before G2 lands is an engineering refusal, not item 38's "admission refuses it".
- **The `data_topic` prefix gap:** GO, MeSH, EFO and NCIT stay undeclared, so `MESH:` still counts as an undeclared prefix while `EDAM:` does not. Unless the owner answers (f) in §7 otherwise, this is deferred to the next condition and filed as an issue.

## 5. What does not change
- the estimands;
- the acceptance gates and floors (D37 on the phase-1 snapshot; D64 item 11);
- D62's caps and fit gate, with D63's measured ratio of 2.739 bytes per token (STATUS log, 2026-10-29T09:32Z) keeping the 4.5M CHORUS allowance;
- the $60 slice and the stop rules (D58; D64 items 3–7);
- the analysis rule for missing data and a complete n=3 (D64 item 16);
- A21's permanently descriptive status (D64 item 29);
- the P4b agenda (items 38–41) and the later items 42–43.

## 6. Procedure and order
1. Re-review by a Claude reviewer and a Codex CLI pass; each finding is filed, and marked fixed here or deferred.
2. **The owner ratifies by naming this file's sha256,** with the §7 answers.
3. **This file is merged on main before the A21 registration hash is put to the owner** (plan step 3; the generation plan's P4 gate).
4. The registration review then captures the BC1-route table on the composed A21 head, and checks it against §2.

## 7. For the owner: yes or no
- **(a)** Schema 3.1.0 as the v10 condition's schema.
- **(b)** Declaring the `EDAM` prefix (N7; beyond D66's text).
- **(c)** The exact `data_substrate` description, and the exact digest insertion, both quoted in §2.
- **(d)** The added confounds, the four measurement effects (including the identifier audit's reclassification), and the supplementary reporting rule, all in §3.
- **(e)** Accepting that the undeclared-prefix and resolver-URL rows read different prefix tables on the two arms. This is evidence-only for A21 under D64 item 30.
- **(f)** Deferring the `data_topic` prefix gap to the next condition.
