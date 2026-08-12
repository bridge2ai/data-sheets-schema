# Decision: generated prose is American English (#502)

**Decided 2026-08-12.** From Camille Nebeker's review: *"Standardize on American
English in the D4D generated docs ie no 'programme'."*

## The rule

Generated prose uses American English — `program`, `organization`, `analyze`,
`license`, `center`, `labeling`, `enrollment` — and so do identifiers the run
mints. Three carve-outs:

1. **Quoted source text keeps its original spelling.** Americanising a quote
   corrupts evidence, which is the one thing the provenance guard exists to
   prevent.
2. **Proper nouns keep their spelling.** "Wellcome Trust Sanger Centre" is a
   name, not prose.
3. **Identifiers copied from a source keep the source's spelling.** An id taken
   from a crate or a DOI is a token. Only minted ids follow house style.

## Where it lives, and why not in the condition prompts

**In the playbook** (`.claude/commands/d4d-full-core.md`, uniform decision
rules), not in `d4d_generic_arm_prompt*.md`.

Editing a condition prompt rotates its pin, and v1's pin is what the fifteen
records of the 2026-08-11 canonical arm hashed. Rotating it would move all
fifteen from `canonical` to `superseded` — reported, not failed, but a real
degradation of the baseline #516 was generated to establish. Verified after the
change: `prompts check --strict` exits 0, `runs check --strict` exits 0, and all
five projects still read `canonical`.

House style is also orthogonal to what the conditions differ on. v1 against v3
is about structured-slot population and defect counts; spelling does not enter
it, so the rule does not belong in the axis being compared.

## The gap this leaves, named rather than hidden

**The API path does not read the playbook.** `d4d api run` renders a condition
prompt and nothing else, so API-generated records are unaffected by this rule.

That is deliberate for now and it is a real limitation:

- Production datasheets come from the agentic path (`claudecode_agent`), which
  this covers.
- The API path is the experimental arm for §6, and adding a style rule to it
  while that comparison is pending is the change #517 exists to warn about — a
  prompt edit mid-comparison makes the arms non-comparable.

When the §6 arms are complete, the rule should move into the condition prompts
as part of whatever version rotation follows, so both paths carry it.

## Measured at the time of the decision

Across the canonical set (`d4d evaluate spelling`):

```
1345 occurrences in generated prose
  43 in text quoted from a bundle (left alone)
   8 inside an `id`
```

All 8 identifiers are minted, not copied — `d4d:VOICE-purpose-programme`,
`chorus:related-bridge2ai-programme`, `#instance-programme-aggregate` — so every
one violates the rule as stated. One is mixed: a real DOI with a minted
fragment, where the offending span is the part the run composed.

The 43 quoted occurrences are the reason this is not a find-and-replace. The
bundles contain `licence` 13 times and `programme` 6, and one line shows both at
once — the record's own prose says *programme* while the text it quotes says
*Program*.

## What this does not settle

- **Existing records are not rewritten.** The 1345 occurrences stand. Editing
  them would make a record state prose no run produced, the same objection as
  #520. New runs comply; old records are evidence of what was generated.
- `d4d evaluate spelling` cannot tell a minted id from a copied one, and the
  rule turns on that distinction. It has not yet mattered — all 8 are minted —
  but a real identifier containing `licence` would be a false positive.
- Nothing here is enforced at generation time. The checker reports; no gate
  fails a run for saying `programme`.
