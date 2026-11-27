# Root-scope Codex semantic instrument, 2026-11-25

Instrument: `2026-11-25_codex-gpt-6-astra-ultra-fast_root-scope-v6`. Semantic version: `6.0`.

Issues 6358 and 6360. The owner chose New mode for all 15 records of the
accepted release series. This registration defines the new measurement;
the build assignment authorizes offline checks only. Live canaries and
subsequent scoring need separate owner authorization.

Base source: `483bed03b14a4c70d6e68dad6679631350a12b72`. Accepted data: `0a1bb84d1449edc27822fd76ffcfd1df7e913cd9`.

The evaluator is Codex with gpt-6-astra, ultra reasoning and requested fast
service tier. Each invocation evaluates one original record with one rubric
in a fresh isolated working directory. The controller retains observed
session identity; it does not replace scores or repair their evidence.

The independently supplied scope file has exactly policy, input_sha256 and
reason. Selection is root_dataset_v1, bound to the original file bytes.
Missing, stale, malformed or contradictory scope declarations refuse.
An explicit DatasetCollection or CoreDatasetCollection contradicts this
selection. Every resource child remains structurally validated. No project
name decides selection, and no generated record gains a class declaration.

The result uses aggregation policy single_dataset and exactly one unit at #.
evaluation_scope also records selection_policy: root_dataset_v1; metadata
records the exact caller file's scope_context_sha256. Applicability context
and context_digest retain their existing meanings. Rubric items, score
domains, denominators and frozen v3 evidence-name authority are unchanged.

The existing v3 instrument and versions 4 and 5 retain their own resources
and interpretation. Do not pool this instrument with legacy collection
scores or another model/runtime measurement. Uniform root units do not
assert that all records describe identical underlying release coverage.

Issue 6360: published d4d_file is repository-relative; session log paths
are relative to the run directory and retain their SHA256 values. Other
absolute local paths must not enter the published object. The raw model
response and private runtime evidence stay separate. Relativisation happens
before exact-file validation and byte-bound publication, never afterward.

New outputs are under:

`data/evaluation_llm/RUBRIC_semantic/label_aware/2026-11-25_codex-gpt-6-astra-ultra-fast_root-scope-v6/PROJECT_LABEL_evaluation.json`

Definitions are composed at plan time from the unchanged pinned v3 source
and a pinned JSON list of exact original passages and replacements. Each
original passage must occur exactly once at its replacement step; source,
override and final composed hashes are checked. No new selectable agent
file is registered under .claude/agents/. The model receives the exact
reviewed v6 definition bytes frozen at `26b74b67e52b9b4fe7091ea45a0e86f81c6ef231`.
This revision changes provenance storage only. Its historical validation
example remains byte-identical; the scorer supplies the actual captured
composed definition to its validator instead of that example path.

The source-definition SHA256, override-file SHA256 and composed-definition
SHA256 are recorded together in each plan, prompt descriptor and receipt.
The composed SHA256 remains metadata.instrument_sha256 in the evaluation.

Versioned assets are reproduced by scripts/adhoc/prepare_root_scope_assets_20261125.py.
Use its --check mode for a read-only exact-byte check. Its default mode
creates missing assets and preserves byte-identical ones. The explicit
--refresh-registration option replaces only this note's frozen first-pass
bytes. Original sources and reviewed definitions are read from the pinned
commits. The tables below are generated from those inputs.

| Definition | Source SHA256 | Override SHA256 | Composed SHA256 |
| --- | --- | --- | --- |
| rubric10 | c817aa5fefd91552be68016818c8a87ab91b8798ac96666d975bc61af32c7fb3 | 434a4d065a8d64e5de5405be1715fa4c4232a5fb401a39628fc9a32b6164b024 | 84f42966ae968881aa65263c8d4f32a0ffe6988a85d24ea8d5a933e99ee1354d |
| rubric20 | 35de3a37264e80f48e6e037fed42b6cc586152058d4da6c08bad93b8096f588b | f89b265d3c6585766362b2791c0608be69405299866e26a986efedfba3d3551d | 6beda6a0a46230b9c6128f9251c9eac0b5771f022c10b47cbc752f017432de52 |

| Registered asset | SHA256 |
| --- | --- |
| data/rubric/root_scope_v6/rubric10_definition_overrides.json | 434a4d065a8d64e5de5405be1715fa4c4232a5fb401a39628fc9a32b6164b024 |
| data/rubric/root_scope_v6/rubric20_definition_overrides.json | f89b265d3c6585766362b2791c0608be69405299866e26a986efedfba3d3551d |
| src/download/prompts/rubric10_semantic_v6_schema.json | feaff440ad287a07fd5bd447e7abea3b878a89855c05e6021fcc0ec87e6d2c51 |
| src/download/prompts/rubric20_semantic_v6_schema.json | 9837b1ef5eb231d11b19be7f7744bb09a2e0740d58d9b33b7d4246258dba9642 |
| data/rubric/rubric10.txt | 9a03a8366d1ef2f6e82efe2c7e14c45053739f7e9f7f05c1ca1868d75c986a97 |
| data/rubric/rubric20.txt | c8c0d3a96878d895006a4f287af761635b64cb1fc7968b3256eb7d37db360612 |
| data/rubric/semantic_evidence_authority_v3.json | 0605c742c61f2cc4e13de907f8e09752bde5ebd08d173b31d837c273a4bf3872 |

| Original record | Input SHA256 | Scope file | Scope SHA256 |
| --- | --- | --- | --- |
| data/d4d_concatenated/claudecode_release/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep1/AI_READI_d4d.yaml | c484d79004bbde58e3ddd04344cd121eb6353b6e39c1973c09266811b68d11d1 | data/evaluation_scope/2026-11-25c/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep1/AI_READI.scope.json | 55ef534185d502bfe988a5f4213edceaff6c07b16dc446613601e17c11939ac9 |
| data/d4d_concatenated/claudecode_release/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep1/CHORUS_d4d.yaml | 0969c1494ff51310f891201cbbef3e2ae7ab531f51c88a4ee8319eb0c7853042 | data/evaluation_scope/2026-11-25c/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep1/CHORUS.scope.json | 945fe24d4a918a8de88187855394e0380e53832b3b4bc70315191dd69f8d9211 |
| data/d4d_concatenated/claudecode_release/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep1/CM4AI_d4d.yaml | c0c59a895768a82ebfa0af089f68032b7a397cee317d8546ef21128d79ecbb60 | data/evaluation_scope/2026-11-25c/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep1/CM4AI.scope.json | d6f6d1f458438200460378e8340a6bc5b5a98ea279f65152e5c759817a3fe366 |
| data/d4d_concatenated/claudecode_release/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep1/VOICE_PEDIATRIC_d4d.yaml | 23edde9730d993c1f810b39863547e000b0e208331389711c967eb456ad2b490 | data/evaluation_scope/2026-11-25c/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep1/VOICE_PEDIATRIC.scope.json | 3a13a01cb8da4b7d034d94ecc60d5107451085e19f95d37d997c1534efeb4a37 |
| data/d4d_concatenated/claudecode_release/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep1/VOICE_d4d.yaml | 0233e4541440f9d82d24ab0a977ed9387dcfa8a1367496de72580363e93335c8 | data/evaluation_scope/2026-11-25c/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep1/VOICE.scope.json | a151d93ad4ba71ec41951135b697c810b619380df0abd8597226b2dd295e5aec |
| data/d4d_concatenated/claudecode_release/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep2/AI_READI_d4d.yaml | f9b00ef92428b287631c29fdd92e4f076f8d938473e6020ff7b01e6527558b53 | data/evaluation_scope/2026-11-25c/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep2/AI_READI.scope.json | 8867b10bd34a2349c3423e781fa1d7ddfa80c198ab233157f609e22a4c4db62a |
| data/d4d_concatenated/claudecode_release/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep2/CHORUS_d4d.yaml | d7217a29e64136b551540446d3490f826a6acca3ebf6f1d235f268aff9db70e0 | data/evaluation_scope/2026-11-25c/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep2/CHORUS.scope.json | 0f0f60f282f7ab9bd773923009f8ea44f5b22449406ac722e14de80754be2d0c |
| data/d4d_concatenated/claudecode_release/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep2/CM4AI_d4d.yaml | a72ed1e8bf24f01558fd6963ac85dedcb85325ae73c5cd5435a750c806dad590 | data/evaluation_scope/2026-11-25c/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep2/CM4AI.scope.json | 97fd349f7a4dab9d2271eee13202e3823f4f8de1eaacb5f67b4b046e82688c87 |
| data/d4d_concatenated/claudecode_release/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep2/VOICE_PEDIATRIC_d4d.yaml | 96896dbd3356076cd3fa47a69879cc3e287bf7a6ad9bf52533e05d4ce4c6e86e | data/evaluation_scope/2026-11-25c/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep2/VOICE_PEDIATRIC.scope.json | b4adac73123cf89135d981fdd943d5d5408d6bd186513c3e5ea63660ecd3c639 |
| data/d4d_concatenated/claudecode_release/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep2/VOICE_d4d.yaml | 1e2d56de81fcd031f9fd12beefcd91bd5a72e5ecb298f06087866272c0a2285d | data/evaluation_scope/2026-11-25c/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep2/VOICE.scope.json | 9661c07f5eae7c341eb511ce60b7e4aaf17072f050a77f4f2375ab2822055e20 |
| data/d4d_concatenated/claudecode_release/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep3/AI_READI_d4d.yaml | a28969e1031a35406a1cb0de3bb58fea97465972cfc00b01781c35f24b650edb | data/evaluation_scope/2026-11-25c/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep3/AI_READI.scope.json | bbed6d964681404de76bdc9b57ac33d48fdf192a0454908ac618e76bbee023da |
| data/d4d_concatenated/claudecode_release/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep3/CHORUS_d4d.yaml | 7832bba06867415666cad64d2e0cdef8353aba8e61736e5c8f27c0997a54cd27 | data/evaluation_scope/2026-11-25c/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep3/CHORUS.scope.json | 07fcbc48fd638b291546510bc7179a3abb25e5cbfde01313a6b4300cbd59c339 |
| data/d4d_concatenated/claudecode_release/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep3/CM4AI_d4d.yaml | 4dbd6119dd17bc0b946e3a7825b5c92cb58cce794adab038794f66b7e01a5cfc | data/evaluation_scope/2026-11-25c/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep3/CM4AI.scope.json | 88cdb052b4f0d8f50e3736b60ed698599e150b40f2a46d649a229df17c8030d1 |
| data/d4d_concatenated/claudecode_release/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep3/VOICE_PEDIATRIC_d4d.yaml | a89b10f4bfc44b8ca32e44004936405c37d0e903510e2b32da699bd6c9f040b5 | data/evaluation_scope/2026-11-25c/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep3/VOICE_PEDIATRIC.scope.json | 45e42965fcb9767b72af130a0a2bf42fde63920a02d777b776cc3890592b185e |
| data/d4d_concatenated/claudecode_release/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep3/VOICE_d4d.yaml | 8a8e7ccc08b14afc0742aa024c6c9e4bbc327fa5ee80247e59d357607e2a316f | data/evaluation_scope/2026-11-25c/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep3/VOICE.scope.json | fa341448618903294454950b3a40dff3b21d57b4ff3a2d05918694a87db10777 |
