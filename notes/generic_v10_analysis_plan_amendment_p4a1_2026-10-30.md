# generic_v10 analysis plan, P4a amendment 1: schema 3.1.0 under D66

**Status: draft, written by claude (lead) on 2026-10-30.**
- **Not binding until** a Claude reviewer and a Codex CLI pass have reviewed it (each finding filed as an issue) and the owner has ratified it by naming its sha256.
- **The byte figures in §2 are final:** from claude's independent re-review of the G1 fix round (`f7fedae48`), 2026-10-30.

## Authority
- **The plan being amended:** `notes/generic_v10_analysis_plan.md`, ratified at commit `5b17ae079c8eb1fa4abdda3261054bfd22e4c2f1`, sha256 `b4a4f9a596173d3bdeb817b01ea53fb1a1d77574e121c7cecaf6f63b67fd4b4b` (D65), and merged by #5163. That file is not edited; this amendment stands beside it.
- **The plan's step 3:** "Its review checks the composed condition against this ratified text; any deviation needs a P4a amendment before the launch word."
- **D66** (owner, 2026-10-29T00:28:46Z, generality finding F6): the schema's `data_substrate` gets declared, neutral term sources, so a dataset outside Bridge2AI can fill it. It is model-facing, so under D35 it lands before the A21 rebuild.
- **The owner's standing rule,** 2026-10-28T23:37Z: "the methods need to be generalized which also means no specific interventions or fixes unless they are part of a generalized approach".

## 1. What changes in the plan's text
1. **Line 922** ("Schema: 2.0.0 against 3.0.0, and the change in the digest's term source") now reads: "**Schema: 2.0.0 against 3.1.0** (D66), and the change in the digest's term source, which now also offers EDAM Data, EDAM Format and IANA media-type terms for `data_substrate` (see §3)." Its two sub-bullets are unchanged.
2. **Line 1450** ("schema 2.0.0 and 3.0.0 records differ visibly") now reads "**schema 2.0.0 and 3.1.0** records differ visibly".

No other plan text changes. The plan does not mention the `tuned` condition (retired for new runs by D67), and nothing in this amendment selects the new rubric v5 instruments; see §4.

## 2. What changes in the A21 condition: model-facing bytes
**The schema edit** (3.0.0 → 3.1.0):
- `data_substrate` gains the annotation `d4d:termSources: "EDAM Data, EDAM Format, IANA media types"`;
- its description becomes "Type or format of data …" (four edits, +89 bytes);
- the prefix `EDAM: http://edamontology.org/` is declared (G1 review N7).

**What does not move:** no range, constraint or required slot, and validation semantics are unchanged. The release history keeps 3.0.0's hashes.

**How it was measured.** By claude's independent re-review of the G1 fix round (`rev-g1-fix`), capturing CHORUS shared-generation-v1 requests offline at the step-0 base `55c7b94b8` and at G1's head `f7fedae48`:
- the typed-audit requests were built with the runtime's own builders;
- the canonical JSON is `sg.canonical`: sorted keys, compact separators, UTF-8;
- the same capture on the integration target (a scratch main, then the same plus G1) gives identical deltas and leaf edits.

| Request | Base (B) | G1 (B) | Δ | What moves |
|---|---|---|---|---|
| `full` | 227,700 | 227,835 | **+135** | the digest gains " a term from EDAM Data, EDAM Format, IANA media types (the source's own identifier, as an IRI or CURIE, when the documents supply one);" after "`data_substrate` draws from"; the schema catalog's bytes field (1442513 → 1442833) and sha256 (`eb543e15…` → `4b1a98e0…`, 3.1.0's `full_merged_sha256`), which are length-preserving |
| `reconcile_full`, `report` (and, by the shared renderer, `report_regate` and `report_after_repair`) | 467,073 / 589,639 | 467,297 / 589,863 | **+224** | the +135 digest insertion, plus the `data_substrate` description (+89) in the rendered schema context, plus the catalog fields |
| typed-audit omission | 598,307 | 598,485 | **+178** | the +89 description twice (the schema context and the inner typed-stage request), the catalog fields, and the derived binding hashes (0 bytes) |
| typed-audit worker assigned an `instances` path (worker_0002 in this plan) | 352,257 | 352,346 | **+89** | the description, the catalog fields, and the hashes |
| other typed-audit workers (worker_0001, worker_0003) | 353,196 / 346,391 | same | **0** | the catalog fields and hashes only; no prose |
| typed-audit integration | — | — | *(expected +89; not measurable offline)* | it renders the same schema context |

**The registration's identity also moves:**
- the full and core schema pins;
- `request_code_sha256` for four files:
  - `api_runner.py` (the D67 tuned refusal);
  - `profile_identity.py` and `provenance.py` (G1 N3);
  - `profiles.py` (F18).

**What nothing else moves:** no other leaf moves in any request, and no `3.x` string appears in any request. The native arm reads the schema files directly, so it also sees the description, the annotation, the prefix and `version: 3.1.0`.

## 3. What this adds to the declared confounds
The v8–v10 comparison already declares the schema version and "the change in the digest's term source" (line 922). It now also includes the following:
- **What v10 records may now carry:** a v10 `data_substrate` value may be an EDAM Data or Format term, or an IANA media type, where v8 offered only the profile's `B2AI_SUBSTRATE` registry.
- **How metrics treat it:** any metric that reads `data_substrate`, such as term validity or registry membership, reports the two term sources separately for v10. It does not adjust or pool them.
- **Blinding:** the identifier forms of the two vocabularies differ, so a blind reviewer may see them. Like the schema-version difference, this is listed among what blinding cannot remove (line 1450).

- **Two measurement effects of the EDAM prefix** (G1 re-review NF2). They are disclosed here; no code changes.
  - **The write-time normaliser** on the API path now compacts an EDAM IRI in a `uriorcurie` slot to a CURIE. For example `http://edamontology.org/format_3752` becomes `EDAM:format_3752`; 3.0.0 kept the IRI. IANA media types already became `mediatypes:` under both versions. Each rewrite is logged in the record's `normalisation.identifier_form` block.
  - **The undeclared-prefix counter** (`grounding.undeclared_prefixes`, which feeds a gated canary row) no longer counts `EDAM:` or `edam:`; under 3.0.0 it did. That row therefore means something slightly different for A21 than for the 3.0.0 CHORUS canaries 2026-10-20a and 2026-10-22a. Any comparison of it across the schema boundary says so.

## 4. Generality changes that leave the plan's text unchanged
These come from the same package (generality G1 and the E3x fixes), under the owner's standing rule. They are recorded here so that the A21 registration review can check them; none needs a plan-text change.
- **Context synthesis, manifest selection and source policy** (G1 F2, F3, F7, F19): the committed omission contexts regenerate byte-identically, so A21's context bytes are unchanged.
- **D67:** `tuned` is refused for new registrations, and historical replay still works.
- **Cost bounds and archive sources** (F10, F11) come from declared or measured data. F10's operational effect on the A21 monitor (G1 review N2) is fixed in code, or covered in the launch packet; it is not model-facing.
- **Profile reading** (F18): an unknown profile is refused, and an undated, profile-less record is refused rather than guessed at. Every committed record is dated, so no historical reading changes.
- **Rubric v5 instruments** (F8) are opt-in and versioned. The plan's E5 options (line 1469: rubric10 3.0; rubric20 3.0 or 4.0) stand. Using v5 anywhere needs its own P4b decision.
- **The evaluation cohort and roster** are declared data (E3x F5), so the plan's E2 and E5 rosters are expressed as declared manifests. This changes no roster membership.

## 5. What does not change
- the estimands;
- the acceptance gates and floors (D37 on the phase-1 snapshot, under D64 item 11);
- the caps and fit gate: D62, with D63's measured ratio of 2.739 bytes per token, keeping the 4.5M CHORUS allowance;
- the $60 slice and the stop rules (D58; D64 items 3, 4, 6, 7 and 16);
- A21's permanently descriptive status (D64 item 29);
- the P4b agenda.

## 6. Procedure
1. The final byte proof is in §2 (done 2026-10-30).
2. A Claude reviewer and a Codex CLI pass review this amendment against the ratified plan and the composed A21 condition. Each finding is filed as an issue.
3. The owner ratifies it by naming its sha256, before the A21 launch word.
