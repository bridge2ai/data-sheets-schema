# GC-specific prompt components

The study compares two prompt conditions:

| condition | prompt |
|---|---|
| **generic** | `../d4d_generic_arm_prompt.md` alone — identical text for every project |
| **tuned** | that same text **plus** this directory's block for the project |

The tuned condition is defined as *generic + block* rather than as a second full
prompt, so the two conditions cannot drift apart in the base. Whatever differs
between them is exactly what is in these files, and nothing else.

## Component types

Each block is a sequence of typed sections. Only three types are permitted, and
the type is declared in the heading so the design is auditable from the files
rather than from anyone's description of them.

| type | what it is | evidence |
|---|---|---|
| `fact` | a true statement about *this project's input set* that the agent would otherwise have to infer | load-bearing: VOICE loses ~15 points of three-way agreement without its cohort fact |
| `decision-rule` | how to resolve a choice, where the choice is peculiar to this project | uniform rules belong in the generic base instead — see below |
| `referent-pin` | which entity the record is about, where `Dataset` admits one and the project has several | load-bearing: without CM4AI's pin, `file_collections` collapses from 10 to 0 |

## `expectation` is deliberately excluded

A fourth type exists in the 2026-07-27 prompts and is **not** used here:
statements about what the output should look like or what the result is expected
to be — "expected to be genuinely additive", "largely redundant", "sparse output
is the correct result".

Two reasons. It is the one category with direct evidence of harm: the
healthsheet's density expectation cost ~4 stable slots, and the crate arms'
expectations inflated counts without improving reproducibility. And because the
tuned condition bundles its components into one variant rather than testing them
separately, including a known-harmful component would drag the bundle down for a
reason the design could not then diagnose.

If the effect of expectations needs quantifying, run it as its own condition on
one project. Do not add it here.

## A uniform rule is not a component

"Prefer omission over inference" was a CHORUS-only instruction in the 2026-07-27
prompts, and removing it cost 12 points of agreement — but the fix was to apply
it to *every* project, which is what the generic base now does. A rule that
should hold everywhere belongs in the base. Only put a `decision-rule` here if it
is genuinely specific to one project's evidence.

## Rules for editing

- Every statement must be checkable against `data/preprocessed/source_manifest.yaml`
  or the input bundle. No claims about expected output.
- Editing a file changes the tuned condition for that project. Re-run that
  project's tuned arm afterwards; do not edit to repair a single replicate.
- A project with no legitimate component gets an empty block, and its tuned
  condition is then identical to generic. That is a valid result, not a gap to
  fill.
