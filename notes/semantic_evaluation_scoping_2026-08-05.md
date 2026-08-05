# Semantic evaluation coverage: the decision, and why

Closes the open half of #287. Both preconditions it named are met: canonical
records are marked for three of four projects, and the prompt config is ready to
choose (v3 stamps itself correctly since #337; v4 exists since #338).

## Both options are runnable

```
d4d evaluate plan                    # one record per project
d4d evaluate plan --all-replicates   # every replicate of the canonical config
```

Today that is 12 against 20. Neither number is written anywhere — both are
derived from the canonical marks (#315), and both move on their own as projects
gain records.

The widened figure is 20 rather than 36 because **four of the nine replicates do
not validate** and are excluded (#344):

    AI_READI rep2, rep3    invalid
    CM4AI    rep1, rep3    invalid

The canonical mark exists because that replicate validates — the selection
criterion is "full and core both validate against the current schema" — and
siblings inherit none of it. Scoring an invalid record and pooling it into a
variance estimate would measure validation failure as quality variance, which is
the opposite of what the estimate is for.

That also sharpens the cost comparison below: the widened run is 1.7x, not 3x.

## Recommendation: canonical-only

**What replicate spread buys.** A within-config variance estimate: how much two
runs of the same prompt on the same bundle differ. That is a real quantity and
the fitness axis already reports it.

**What it does not buy.** Any improvement in resolving *between-config*
differences. #169 measured that directly — the between-config delta was −2.9
against a replicate standard deviation of 10.9, and ~110 projects would be
needed. More replicates of the same four projects narrow the standard error of
each arm's mean, but the limit here is the project sample, not the replicate
count. Three times the calls does not move the comparison the study is for.

**What it costs.** 3x, and the semantic path is the expensive one — an LLM judge
per record per rubric.

**The asymmetry that decides it.** If the canonical-only result turns out to
need a variance estimate, the replicates are still on disk and
`--all-replicates` runs them later. The reverse is not true: calls spent now
cannot be unspent. Run the cheap one first.

## What would change the recommendation

If the manuscript claims a *between-config* semantic difference, neither option
supports it at four projects and the honest answer is to not make the claim.
Widening the project set would; widening the replicate set would not.

If the claim is about within-config stability — "the same prompt produces
consistent records" — then `--all-replicates` is the right run and 36 is the
number.

## Not decided here

Which config to evaluate. That follows the generation decision (v3, or v3 and
v4), and evaluating before that settles means evaluating twice.
