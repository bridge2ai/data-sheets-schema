# P4a G1 round 2 evidence tools — 2026-10-30

These helpers serve P4a review findings 1 (complete byte proof), 4 (CURIE
description) and 5 (historical-code profile fallback). Run from this worktree.
They use the already installed project environment, without installing anything.

`capture_requests.py`, `diff_payloads_fast.py`, `corpus_profile_sweep.py`,
`offline_pytest.py`, `check_digest.py` and `owl_delta.py` originate in the
independent review's `d4d-executions/rev-g1r2/tools/` directory. The diff, corpus
sweep and OWL comparison algorithms are unchanged. Capture adds the missing
receipt/report phases and redirects archive reads without changing the archived
carry text. The pytest launcher additionally prints failures immediately; the
digest launcher now fails its process when the CLI fails.

The production edit was followed by the Makefile targets:

```sh
make regen-all gen-core-schema gen-sssom-comprehensive gen-sssom-uri-comprehensive
bash scripts/adhoc/generality_g1_round2/run.sh scripts/adhoc/generality_g1_round2/proof.py release
```

Regeneration used the existing environment's bin directory on PATH and `RUN=`
to avoid creating another Poetry environment. Provider keys were unset.

The main reproduction commands are:

```sh
bash scripts/adhoc/generality_g1_round2/run.sh scripts/adhoc/generality_g1_round2/proof.py base
bash scripts/adhoc/generality_g1_round2/run.sh scripts/adhoc/generality_g1_round2/proof.py head
bash scripts/adhoc/generality_g1_round2/run.sh scripts/adhoc/generality_g1_round2/diff_payloads_fast.py .g1-round2-evidence/capture-base.json .g1-round2-evidence/capture-head.json > .g1-round2-evidence/leaf-diffs.txt
bash scripts/adhoc/generality_g1_round2/run.sh scripts/adhoc/generality_g1_round2/validate.py fixture-canary focused-final collect-final shard-1
bash scripts/adhoc/generality_g1_round2/run.sh scripts/adhoc/generality_g1_round2/check_digest.py
bash scripts/adhoc/generality_g1_round2/run.sh scripts/adhoc/generality_g1_round2/proof.py verify
bash scripts/adhoc/generality_g1_round2/run.sh scripts/adhoc/generality_g1_round2/proof.py report
```

`proof.py base` and `head` sequentially materialize the selected runtime inputs
at the same scratch path inside `.g1-round2-evidence/`. They never switch the
working branch. They read the original archive and create no runner output or
ledger. Base capture must precede head capture. Do not run either concurrently
with the other. The unchanged reviewer diff algorithm can take several minutes
on the inner omission JSON string.

Pytest runs serially through the existing `generality_g1_offline_20261029.py`
harness, which suppresses ambient `.pth` startup, guards child Python network
connections and runs Poetry/LinkML children in the installed environment. The
initial simple review launcher let Poetry try to create an environment; that
was corrected before final acceptance. Basetemps are under
`d4d-executions/rev-g1r2/out/g1-round2-basetemps/`, outside any checkout. Temps
inside this worktree made parent-walking corpus discovery adopt the real corpus
in unrelated fixtures; the sibling location restores CI's fixture topology.

The corpus sweep compares the original `f7fedae48` fallback with the final
fallback over all 286 tracked records. Its raw before/after JSON and checksum
are retained in `.g1-round2-evidence/`. `verify` also checks the actual
`a2a3e157b` commit with a current date, unchanged schema-description suffix, and
the protected digest template/pins/shared-generation source.

The ordinary 1/6 CI shard completed with 3,083 passes, 12 skips and 24 setup
errors: the filesystem sandbox also refused the fixtures' localhost socket
binds. `shard_failures.py` identifies those exact JUnit nodes. After the shard,
the following units use the same launcher, keys unset and external socket/DNS
guard, in an execution context permitting the fake `127.0.0.1` servers:

```sh
bash scripts/adhoc/generality_g1_round2/run.sh scripts/adhoc/generality_g1_round2/shard_failures.py
bash scripts/adhoc/generality_g1_round2/run.sh scripts/adhoc/generality_g1_round2/validate.py shard-loopback-canary
bash scripts/adhoc/generality_g1_round2/run.sh scripts/adhoc/generality_g1_round2/validate.py shard-loopback
```

The canary is checked before the group runs. It persists the relocated index
and tests two synthetic deliveries followed by a captured-only recheck. This
does not test any provider or external transport. The original shard JUnit
and its nonzero exit status remain intact beside the retry evidence.

Raw captures, logs, snapshots, JUnit and the implementation patch stay locally
under `.g1-round2-evidence/`; they are not staged as repository products. The
committed `byte_proof_2026-10-30.md` includes the complete table, per-leaf diff,
identities and final test totals. `report` also writes the requested identical
copy to `d4d-executions/plans/reviews/generality_g1_round2_byte_proof_2026-10-30.md`.
