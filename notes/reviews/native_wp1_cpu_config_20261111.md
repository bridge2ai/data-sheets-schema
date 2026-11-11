# Exact private configuration reuse for E1

The 3cc113e2606c same-manifest canary passed and its private config was restored.
The lead authorized preparation of one `cpu-legacy` diagnostic, capped at 900s,
using that same composition and canary; launch awaits the shared runtime slot.
No recomposition, source installation or monitoring arm is included.

`scripts/adhoc/native_wp1_private_config_20261111.py` supports one exact activation
and restoration cycle. It pins the successful canary, contract, composition and
previous restoration witness, requires clean committed tools and verifies native
source/preimages before activation. Original and configured bytes are retained
under the composition's fresh `cpu-diagnostic-config/` directory. Restoration
refuses foreign config bytes. It neither imports source nor launches tests.
Independent read-only review found no blocker at helper SHA-256
`bb9c6f71c634294712520bf43416888171d0f577b9ad506092512bcdb750b17d`.
No runtime check of this helper is claimed at this commit.

Activation, after runtime clearance (change final argument to `restore` afterward):

```sh
/usr/bin/env -i PATH=/usr/bin:/bin:/usr/sbin:/sbin LANG=en_US.UTF-8 /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python -S -P -B /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-native-wp1-preparation-20261111/scripts/adhoc/native_wp1_private_config_20261111.py activate
```

One fixed-node, one-worker CPU diagnostic, only after successful activation:

```sh
/usr/bin/env -i PATH=/usr/bin:/bin:/usr/sbin:/sbin LANG=en_US.UTF-8 U3WP1_MANIFEST=/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/wp1-contract-3cc113e2606c.json /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python -S -P -B /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-native-u1u3/scripts/adhoc/native_wp1_validation_20261110.py cpu-legacy --label e1-observer-baseline-20261111 --canary-out /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/wp1-3cc113e2606c-canary-e1-cpu-equivalence-20261111
```

The existing validator strips credentials, requires the pinned canary, refuses
an existing quiet lock or inherited lease FD, and retains sandbox/deadline/process
cleanup. This is an unqualified CPU diagnostic; no wall-time freshness, accepted
quiet timing or native acceptance is inferred. Do not sum nested inclusive CPU.
If later outcomes diverge, retain equal completed call intervals and phase prefixes
without assigning a ratio to unequal work. The separate read-only collector is
owned by another worker. No fixture-reuse or WP2 branch enters this baseline.
