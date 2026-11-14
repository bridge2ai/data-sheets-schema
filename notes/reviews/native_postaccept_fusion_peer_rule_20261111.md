# #5870: peer-rule encoding repair prepared, not executed

2026-11-11. Helper-only delta from
`254071e053e7879f543b31d1ea84e8b3ea7dfb78`. Production, tests, deadline helper,
Git allowance, fixed selections and budgets remain unchanged. Both failed
canary directories are preserved. No repaired-helper import, compilation,
sandbox probe, retry, affected group or other runtime occurred.

The separately released v2 singleton failed with EPERM at the scripted peer
path, after Git setup. Exact outcome and hashes are in
`native_postaccept_fusion_canary_v2_20261111.md`, SHA
`d592fb5c6a3269c5b04bf1e37671cd659d880e227fc51d5b19f3015f605faa4f`.
Independent artifact review confirms one failure, spawn_count0/child_startedfalse,
matching retained claim/stream hashes and no known PID/PGID1593 in the final
sample. Those cleanup flags reflect an unstarted peer, not successful capture.

## Observed path/encoding and bounded correction

The saved v2 profile serializes doubled backslashes before path hyphens after
`re.escape` followed by JSON encoding. The denied script is the expected
`cases/test_deferred_capture_acceptan0/durable-copy`; its shebang names the
already allowed primary `.venv/bin/python`, whose resolved target is also
already allowed. The lead filed5870 and authorized correcting only the peer
rule's fixed-prefix encoding, without expanding executable scope.

The new recipe:

1. Uses a separate fixed evidence root,
   `d4d-executions/scratch-native-postaccept-fusion-v3-20261111/`.
2. Computes the fixed case prefix and requires a full match of
   `/[A-Za-z0-9_/-]+` before creating the output. Prefixes containing spaces,
   quotes, backslashes, periods or other regex/string metacharacters refuse.
   The actual source-derived prefix contains only the permitted characters.
3. Concatenates that already validated prefix directly into the same anchored
   `^<prefix>/[^/]+/durable-copy$` rule. It no longer passes path hyphens through
   `re.escape`. JSON encoding remains for the SBPL string, but these validated
   prefix bytes require no backslash escapes. The only regex syntax is the
   fixed anchors and one directory-component matcher supplied by the helper.

For the canary, the intended SBPL regex string is exactly:

```
#"^/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-postaccept-fusion-v3-20261111/canary/cases/[^/]+/durable-copy$"
```

This is source-derived expected text, not output of executing the repaired
helper. Only `durable-copy` under one immediate case directory can match;
other output files and deeper descendants do not acquire exec permission.
The existing Python/interpreter and three fixed Git/selector literals remain
unchanged. There is no directory-wide execution allowance, native executable
addition, network permission, write expansion or supervisor change.

The new v3 root was checked absent, including a symlink check, and has not been
created. Non-canary groups consult only its same-source passing canary result;
neither preserved failed run can satisfy that gate. The helper still refuses
nonpositive work time, uses10s work plus20s cleanup reserve and a<=30s acceptance
criterion, and never starts another group automatically. Setup failure times
from v1/v2 cannot size the successful groups or establish performance.

## Frozen review identity

Prepared helper SHA-256:
`b175549261aa28cd5681b23824b51757fbe7fb7c33a8905f6cdc54e123e29227`.
Exact delta `notes/reviews/native_postaccept_fusion_peer_rule_20261111.diff`,
SHA-256 `c67d9e1b2abc372dab9876140757f729411f791e87520abd658c9e286906aa56`.

Source/helper whitespace checks pass; exact archived patch context whitespace
is retained. No syntax or behavioral validation was performed on the new
recipe. This correction is a source proposal for separate review, not proof
that sandbox matching or the canary will pass. Stop pending review and a new
explicit singleton release; no retry or additional runtime is authorized here.
