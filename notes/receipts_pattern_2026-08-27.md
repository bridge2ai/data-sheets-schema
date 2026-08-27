# Receipts, not instructions: what DisMech does, and what it means for D4D

Studied 2026-08-27 from `monarch-initiative/dismech` (main, shallow clone;
`CLAUDE.md`, `docs/explanation/design-decisions.md` §6–7,
`docs/deep-research-reference-validation.md`, `src/dismech/
reference_snippet_audit.py`, `preflight_dr.py`, and the `kb/disorders/*.yaml`
evidence blocks). The word "receipt" does not appear in DisMech's design docs;
the pattern does, on every claim.

## The pattern, as DisMech practises it

**A receipt is a machine-checkable artifact attached to a claim that proves
where the claim came from.** DisMech's unit is the `evidence` item:

```yaml
evidence:
- reference: PMID:30707186          # a resolvable identifier
  reference_title: "Early-onset Alzheimer Disease and Its Variants."
  supports: SUPPORT                  # the claimed relation
  snippet: Early-onset Alzheimer disease (AD) is defined as ...   # verbatim
  explanation: ...                   # prose, unvalidated, for the reader
```

and the rule (design decision §6) is: *"Every evidence item must cite a real,
resolvable reference and quote it exactly."* Paraphrase fails validation.

What makes it a receipt rather than an instruction is the six properties
around it:

1. **Deterministic adjudication.** `linkml-reference-validator` checks the
   snippet is an exact substring of the cited reference's text (with a fixed
   normalisation: editorial `[...]` stripped, `...` splits into independently
   matched parts, Greek letters spelled out, case and punctuation folded,
   whitespace collapsed). The model's compliance is not asked for; it is
   measured.
2. **The source is a tool-written local artifact.** `references_cache/*.md`
   is created only by `just fetch-reference` or the validator, never by hand
   (AGENTS.md's one rule for non-Claude agents). Validation is therefore
   offline, reproducible, and against the bytes the run saw.
3. **Affirmative counting.** `reference_snippet_audit.py` exists because the
   validator printed `Total checks: 0` on every clean run — it counted issues,
   not checks — so a passing run was indistinguishable from a no-op, and that
   caused a misdiagnosis (their #7246/#7252). The audit prints
   `Snippets checked: N/N verified`. **A receipt validator must say how many
   receipts it checked, not only how many failed.**
4. **More than two outcomes.** The audit's `PairOutcome` has five —
   `VERIFIED`, `VERIFIED_RELAXED`, `ABSTRACT_ONLY`, `SKIPPED_PREFIX`,
   `NOT_CACHED` — plus a mismatch record. `VERIFIED_RELAXED` is a match that
   succeeds only under looser folding (ligatures, word boundaries), applied in
   a deliberately narrow pass to excuse *cache-extraction defects*, not to
   forgive the model. `ABSTRACT_ONLY` is the one described as "nothing was
   proved about it either way": the cache held only the abstract, so absence
   is not evidence — and `--strict` fails on it unless `--allow-abstract-only`
   is passed. The point is that "could not check" is its own outcome, never
   folded into pass or fail. This is the distinction our canary gate draws
   with UNMEASURABLE ≠ OK (#613).
5. **Receipts are demanded where the claim is made, not after.** Deep-research
   reports resolve every PMID/DOI, and check every quote attributed to a
   reference that resolved, *as part of generating the report*
   (`deep-research-client[validation]`), because "curate first and check
   later" built entries around sources that did not exist.
6. **The check that tooling cannot do is named, not hidden.** Named Entity
   Confusion — a coherent report about the wrong disease, every PMID real,
   every snippet exact — cannot be caught by receipts; `preflight_dr.py`
   makes the semantic check a required, recorded step with its own verdicts
   (PASS/WARN/FAIL/SKIP). Receipts prove provenance, not relevance.

And one boundary they draw deliberately: bulk-generated *dataset* records
carry **no** evidence block — "an evidence item needs an exact quote from the
cited abstract, and manufacturing those at scale is precisely the fabrication
risk the evidence SOP warns about". Where a receipt cannot be honest, it is
absent, not faked.

**Why receipts beat instructions.** An instruction ("read the whole bundle";
"take identifiers only from the evidence") asks for a behaviour and cannot
tell laziness from compliance. A receipt makes the behaviour leave a mark that
a validator can check. The model can still cheat — it can copy a snippet from
one chunk while inventing the claim — but it has to cheat *deliberately*,
producing a specific falsifiable artifact, rather than merely skipping work.
That converts the dominant failure mode (omission by laziness) into a rarer
one (fabrication by intent) that reviews are already built to catch.

## What D4D already has, in these terms

| D4D mechanism | receipt property | gap |
|---|---|---|
| `grounding.check_run` — external-authority identifiers the record states (ROR, ORCID, DOI, ARK, …) are looked for in the bundle (#547); reported, never fatal (#520) | deterministic, offline, against the declared bundle's bytes; three verdicts (`grounded`/`minted_fragment`/`absent`) | receipts for **registry identifiers only** — `urn:` and bare tokens are out of scope, and a slot's prose value has no receipt |
| `inputs.bundle_md5`, prompt request sha256, schema digest | receipt for *what the run consumed* | says nothing about what it *read* |
| `run_observed.bundle_lines_read` (#700/#701) | an observation of the agent's reads from its transcript | a read is not a consideration; the API arm has 100% "read" by construction and no receipt at all |
| `report_claims` (#546/#684) | deterministic check of two claim forms in the report | parses two forms; `claims_checked: 0` was reported as "0 findings" — exactly DisMech's #7252 |
| `pair_consistency`, derivation (#694) | the core's receipt is the full record itself | complete, by construction |
| `d4d-provenance-guard`, evidence boundary | instruction | no receipt that a prior record was *not* read (only the transcript, post hoc) |

So D4D has receipts for identity of inputs and for identifiers, and
instructions for everything else — including the two things the arm analyses
keep finding: coverage (which parts of the bundle were considered) and
support (which part of the bundle a value came from).

## The design: chunk deterministically, receipt each chunk, validate

Three artifacts and one validator, both runtimes.

**1. Chunk manifest — a pure function of the bundle.** `d4d bundle chunk
--project P` writes `data/preprocessed/chunks/{PROJECT}_chunks.yaml`:

```yaml
bundle: data/preprocessed/concatenated/CHORUS_preprocessed.txt
bundle_md5: 9b2ef4b65d67957f79362266cab0bc7a      # what the 2026-08-24 records pin
rule: {unit: source-document, max_lines: 400, max_bytes: 60000,
       preamble: own-chunk}                          # recorded, re-derivable
chunks:
- id: c000
  source: <preamble>             # the bundle's summary and table of contents
  lines: [1, 16]
  sha256: …
- id: c001
  source: reporter_nih_gov_project-details-10472824_row7.txt   # from the FILE: header
  lines: [17, 300]
  sha256: …
- id: c002
  source: bridge2ai-for-clinical-care-informational-webinar-cohort-2_row9.txt
  ...
```

(Values illustrative except the md5 and source names, which are CHORUS's
real ones; the bundle is 1,699 lines and would yield about eight chunks.)

Chunks follow source-document boundaries in the concatenated bundle — it
carries a summary, a table of contents and a `FILE:/PATH:/SIZE:` header per
document, all inside the hashed bytes — and split long documents into
windows bounded in *both* lines and bytes. Lines alone do not guarantee one
read: the file tool's cap is ~25k tokens, and a 400-line window of AI_READI
today is ~63k characters with single lines of 13k, so `max_bytes` is what
keeps a chunk readable in one call (the cap that silently truncated the v5
agents' reads, #700). The preamble is its own chunk rather than nobody's.
Same bytes + same rule = same manifest, so the manifest is re-derivable and
its hash is a receipt for the chunking.

**2. Coverage receipt — written by the agent, one entry per chunk, as it
reads.** `{PROJECT}_coverage_receipt.yaml` beside the record:

```yaml
bundle_md5: 9b2ef4b65d67957f79362266cab0bc7a   # must equal the manifest's
chunks:
- id: c001
  status: extracted        # extracted | redundant_with | nothing_relevant | duplicate_of
  extracted:
  - slot: funders[0].grant_id
    snippet: "OT2OD032701"       # verbatim from this chunk
  - slot: description
    snippet: "a longitudinal, multimodal ..."
- id: c002
  status: nothing_relevant
  reason: acknowledgements and references only
- id: c003
  status: redundant_with         # relevant, but every fact already receipted
  chunks: [c001]                 # from these chunks — the record cites them
- id: c004
  status: duplicate_of           # the same bytes as another chunk
  of: c001
```

The status vocabulary is closed and every status needs its predicate: an
`extracted` chunk needs at least one (slot, snippet) pair; `nothing_relevant`
needs a reason; `redundant_with` names the chunks whose receipts already
cover its facts (the case the first draft of this vocabulary had no word for
— relevant, but nothing new — which agents would otherwise file under either
neighbour arbitrarily and poison the coverage analysis); `duplicate_of` names
a chunk with the same content. The agent writes the entry
for a chunk **before reading the next one** — the receipt is produced where
the reading happens, not reconstructed at the end (DisMech's property 5).

**3. Claim receipts — the same pairs, indexed by slot.** The coverage
receipt's (slot, chunk, snippet) triples, inverted, are the record's claim
receipts: for each populated slot, which chunk(s) support it and with what
verbatim text. Kept as a sidecar (`{PROJECT}_receipts.yaml`) rather than a
schema change, so the datasheet schema stays domain-neutral. The derived core
(#694) inherits receipts for identically-pathed slots by construction; its
`distributions` are built from the full's `file_collections`, so the
derivation must also map those receipt paths (`file_collections[i]…` →
`distributions[j]…`), and `dialect` and the runner-set slots have no bundle
receipt to inherit. That mapping is a commitment in #708, not a given.

**4. The validator — deterministic, offline, affirmative.** `d4d receipts
check --label L --project P`, written into the provenance record as a
`receipts` block:

- every chunk in the manifest appears exactly once in the coverage receipt,
  and no receipt names a chunk the manifest lacks — `chunks: 47/47 reviewed`;
- the receipt's `bundle_md5` equals the manifest's and the record's;
- every snippet is an exact substring of *its own chunk's* text under
  DisMech's normalisation — `snippets: 212/214 verified` — with the two
  failures listed (chunk, slot, first 60 chars) rather than only counted;
- every `slot` path resolves in the record — `slots: 58/58 resolved` — and
  every populated slot *that can have a bundle receipt* has at least one —
  `slots with a receipt: 55/58`, the three without named. The denominator
  excludes a declared list of runner-set and minted slots (`conforms_to_*`,
  minted fragment ids, normalised dates, `notes`/`source_caveats` where they
  are the run's own commentary); without that list the count is never zero
  and means nothing. The exemption list is data in the validator, not a
  judgement at review time;
- `duplicate_of` targets exist and are not themselves duplicates; every
  `nothing_relevant` carries a reason;
- an outcome per snippet: verified, or mismatched with the reason, or
  **unchecked** where the chunk text could not be loaded — and a
  `checked: 0` result reported as **unmeasured**, never as clean (#684's
  lesson, DisMech's #7252). No "relaxed" verdict: DisMech's exists to excuse
  defects in *its* cache extraction, and here the chunk *is* the source bytes,
  so there is nothing between an exact match and a mismatch to name.

What it does not and cannot check, named in the block as DisMech names NEC:
that a `nothing_relevant` chunk really had nothing (a *judgement*, sampled by
review), and that a verified snippet actually supports the value it is
attached to (a snippet can be real and irrelevant — the laundering case).
Both remain review work; the receipt makes them *specific* review work — a
chunk id and a slot path — instead of "did the agent read the bundle".

**5. How the two runtimes produce it.**

- **Agentic**: the playbook's Phase 1 becomes the receipt protocol — read the
  manifest, then for each chunk read it and write its entry before moving on.
  The #701 "read the whole bundle" rule is subsumed: coverage is no longer an
  instruction the transcript is inspected for afterwards, it is a receipt the
  validator counts. `bundle_lines_read` stays as an independent cross-check —
  a receipt claiming a chunk was reviewed that the transcript never opened is
  the laziness detector. It is sound only if the playbook mandates the file
  tool for chunk reads (a `sed -n`/`cat` read is honest but invisible to the
  detector, which counts `Read` windows only), or the detector learns to
  parse shell reads; #709 does the first and notes the second.
- **API**: the bundle is in context on every call, so coverage is not the
  question — support is. The `full` phase produces the coverage receipt as a
  second document (chunk ids from the manifest are given in the cached
  prefix), validated the same way. That is a prompt/assembly change, so a new
  condition step (v7), registered with its own predictions.

**6. What the receipt changes in the arm analyses.** Three new deterministic,
comparable metrics per run — chunk coverage, snippet verification rate, share
of populated slots with a receipt — plus a cross-check (receipt vs
transcript). The coverage gap #700 measured by transcript forensics becomes a
first-class recorded fact on every run, on both arms, and the
populated-slot gap between arms (CHORUS 49 vs 58) gets a per-slot answer:
which chunk the API arm drew each extra slot from, and whether the agentic
arm marked that chunk `nothing_relevant`.

## Sequencing

Everything above is measurement infrastructure plus a procedure change. In
order, each an issue, all before the next canary:

1. chunk manifest tool (pure function, recorded rule) — #707
2. coverage/claim receipt schema and the validator with affirmative counts
   and three verdicts, written into the provenance record — #708
3. agentic playbook Phase 1 as the receipt protocol; transcript cross-check —
   #709
4. API `full` phase emits the coverage receipt (v7 condition boundary) — #710
5. canary gate reads the receipts block; UNMEASURABLE ≠ OK — folded into #708
6. report-claims (#684) re-expressed as receipts on the report — noted there

Review corrections (#711): the derived-core path mapping, the exemption list,
the `redundant_with` status and the dropped "relaxed" verdict are commitments
in #708; `max_bytes`, the preamble chunk and the purity test in #707; the
Read-tool mandate in #709.

Sources: [monarch-initiative/dismech](https://github.com/monarch-initiative/dismech)
— `CLAUDE.md`, `docs/explanation/design-decisions.md` (§6 Evidence &
provenance policy, §7 Curation process), `docs/deep-research-reference-
validation.md`, `src/dismech/reference_snippet_audit.py`,
`src/dismech/preflight_dr.py`; the `kb/disorders/Alzheimer_Disease.yaml`
evidence block quoted above.
