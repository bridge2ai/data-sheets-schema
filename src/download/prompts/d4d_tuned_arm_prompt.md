# D4D tuned-arm generation prompt

The **tuned** arm is defined as the generic arm **plus** one project-specific
block. It is deliberately *not* a second full prompt: duplicating the body would
let the two conditions drift apart in the base, and then the difference between
them would no longer be the thing under test.

So the whole prompt is:

1. the body of `d4d_generic_arm_prompt.md`, unchanged, with the same
   substitutions; then
2. the block in `components/{PROJECT}.md`, inserted verbatim.

Whatever differs between the two conditions is exactly the component block —
that is the property the comparison rests on.

`components/README.md` defines which component types are permitted (`fact`,
`decision-rule`, `referent-pin`) and records why `expectation` is excluded.

A project whose component file declares no components produces a tuned prompt
identical to its generic one. That is a valid outcome — it means the project has
no legitimate GC-specific content — and the runs should still be made, so the
null case is measured rather than assumed.

---

## Substitution fields

Identical to the generic prompt, plus one:

| Field | Meaning |
|---|---|
| `{PROJECT}` | AI_READI, CHORUS, CM4AI, or VOICE |
| `{ARM}` | arm display name |
| `{METHOD}` | output method directory |
| `{BUNDLE}` | the single declared input bundle path |
| `{LABEL}` | run label, e.g. `2026-07-29_claude-opus-5-tuned_rep1` |
| `{MANIFEST_LINE}` | the `# Source manifest:` header line for this arm |
| `{COMPONENTS}` | the contents of `components/{PROJECT}.md` |

---

## Assembly

Execute the "Prompt body" section of `d4d_generic_arm_prompt.md` with the
substitutions above, with these two changes:

**1. Header block.** Replace the two lines

    # Mode: four-phase project agent, generic prompt
    # Prompt: src/download/prompts/d4d_generic_arm_prompt.md (identical for all projects)

with

    # Mode: four-phase project agent, tuned prompt
    # Prompt: src/download/prompts/d4d_tuned_arm_prompt.md
    # Prompt components: src/download/prompts/components/{PROJECT}.md

so a record states which condition produced it and which components applied.

**2. Component block.** After the "UNIFORM DECISION RULES" section and before
the "RETURN:" line, insert:

    PROJECT-SPECIFIC EVIDENCE — the following statements describe this project's
    input set. They are factual claims about the corpus, checkable against
    `data/preprocessed/source_manifest.yaml`. They state nothing about what the
    output should contain, how many slots to populate, or how this record should
    compare to any other.

    {COMPONENTS}

The framing sentence matters: it tells the agent these are claims about the
*inputs*, not targets for the *output*. Without it a factual block reads as an
instruction about what to produce, which is the failure mode the excluded
`expectation` type represents.
