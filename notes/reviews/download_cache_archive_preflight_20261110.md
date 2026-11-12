# Exact npm archive cleanup preflight — proposal only

Observed 2026-11-10T05:45:29+00:00 to 2026-11-10T05:45:48+00:00. **No deletion or cache mutation performed.**

Proposed scope: exactly **26 npm Codex download archives**, 3,254,362,112 allocated bytes (3.031 GiB), and their 26 corresponding npm cache-index entries. Preserve installed executables, environments, the newest observed download, other npm content and all Homebrew archives/aliases.

Manifest: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.temp/generation-eta-20261110/notes/reviews/download_cache_archive_manifest_20261110.json`; SHA-256 `ed3c009c0bebfe30604dd057e1aa7aaff01ea4d0f92b894f2daeb014e9caf266`.

Blockers: 0. All stated narrow guards passed.

## Verified identities and references

- All 26 are non-executable regular files with one hardlink, no target or ancestor symlinks, gzip headers and a readable first tar member. Full SHA-256 is recorded; full SHA-512 equals the npm content-addressed pathname.
- Each archive has exactly one live npm key in the complete local index snapshot; the index remained unchanged through this preflight. No shared-content key would be left dangling by the proposed exact-key removal.
- Every guarded_rm invocation included --dry-run and the exact parent/path; none invoked removal.
- Open-handle check: return code 1, stdout 0 bytes, stderr 0 bytes.
- Inbound symlink scopes: /Users/marcin/.npm, /Users/marcin/Library/Caches/Homebrew, /Users/marcin/.nvm/versions/node/v22.16.0/lib/node_modules/@openai/codex. Text-reference scopes: /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.temp/generation-eta-20261110/src, /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.temp/generation-eta-20261110/scripts, /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.temp/generation-eta-20261110/pyproject.toml, /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.temp/generation-eta-20261110/Makefile, /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.temp/generation-eta-20261110/poetry.lock. Ignored/hidden files were included; the search was not full-home.

## Exact npm operation supported by installed source

Installed npm 10.9.2: `/Users/marcin/.nvm/versions/node/v22.16.0/lib/node_modules/npm/lib/commands/cache.js` lines 104–145 accept `cache clean <key>` (also rm/clear aliases), remove that single index entry and its integrity-addressed content. No --force is required when a key is supplied. With no key, --force enables a whole-cache removal; that wider operation is excluded. The inspected method does not check --dry-run, so do not use npm itself as the dry-run mechanism.

A future authorized action should supply exactly one manifest key per invocation with an explicit `--cache=/Users/marcin/.npm`; use the pinned Node/npm installation and reverify source hashes, candidate hashes, key mapping and handles immediately beforehand. npm may also write its ordinary local diagnostic log. No install, network access, cache verification/garbage collection or broad purge belongs to this proposal.

Canary after approval: `/Users/marcin/.npm/_cacache/content-v2/sha512/62/32/a6adeec394ab254158527e8707b1c8319ed64a6997352d0c922a1eeafa134bf2374af9cf2749649e3e2e7cdf2285348c59f19ff30a47b0b6314dbcea5089` (86,990,848 allocated bytes). Verify that archive and key are absent, siblings remain unchanged, and observed free space increases by approximately its allocation. If that fails, stop before the remaining 25. Once the canary passes, process the remaining exact keys sequentially, stopping on any identity/handle mismatch.

## Homebrew excluded after preflight

- `/Users/marcin/Library/Caches/Homebrew/downloads/16fca3c6850968dd4f578d905c8a9af19cdd1accd73606674ece7764b3e8047b--llvm--23.1.3_1.arm64_tahoe.bottle.tar.gz` — inbound cache alias(es): `/Users/marcin/Library/Caches/Homebrew/llvm--23.1.3_1`
- `/Users/marcin/Library/Caches/Homebrew/downloads/cf1723dbb152ee4dc893a709c87f5e88b014e29e282cb8dc577d621bff2fc108--dssp--4.6.1.arm64_tahoe.bottle.tar.gz` — inbound cache alias(es): `/Users/marcin/Library/Caches/Homebrew/dssp--4.6.1`
- `/Users/marcin/Library/Caches/Homebrew/downloads/6442a2d950abe9d76d29f573a3b501a65765fb4d113113833733a833ce6abfde--boost--1.90.0_1.arm64_tahoe.bottle.tar.gz` — inbound cache alias(es): `/Users/marcin/Library/Caches/Homebrew/boost--1.90.0_1`

Removing those three archive files alone would leave dangling Homebrew cache aliases. They are excluded; this proposal does not add their symlinks to the approval scope.

## Owner approval boundary

The safe-delete skill states: “Delete only what the user named in the current conversation.” A single explicit approval may name the exact 26-file manifest and associated 26 cache-index entries. No deletion approval has been received. Skill: `/Users/marcin/.codex/skills/safe-delete/SKILL.md`.

Estimated 3.031 GiB reclaimed space is conditional. Current availability is volatile; the report does not attribute prior disk-space changes or guarantee future native-run capacity.

## Exact archive list

| Package archive | Allocated bytes | SHA-256 | Absolute path |
|---|---:|---|---|
| codex-0.166.0-darwin-arm64.tgz | 147079168 | `181d2eda8addbeca0b689c996df207293947928bdd9c88a097837ae1c7e69ca5` | `/Users/marcin/.npm/_cacache/content-v2/sha512/e5/f5/87eaaa9422700271100321ec239674710dbe102ded2eae2c1e862673d3ebe2b80001f08f9659e7eac38c701efc8a6b17a2197e2e2b9ebebeb81fbc593715` |
| codex-0.164.0-darwin-arm64.tgz | 140709888 | `9b5a35be1975ceb332eaf274032f375b017ab644ff0165737ead03277fae77cd` | `/Users/marcin/.npm/_cacache/content-v2/sha512/a4/38/b380e500b6adff93701b5051db694d7d5a960a0a36bea05a4d4932caac3423e254d43520ee4cf262a78b90567dbfd448a941da50ac630e40156e235ce700` |
| codex-0.163.0-darwin-arm64.tgz | 137871360 | `1193ff4ce72387a5d6c34820b54a9dc57d007c67a958e8acb4715924facd3c31` | `/Users/marcin/.npm/_cacache/content-v2/sha512/8b/b0/f39366b96869ae18cf5a35981a5154e88d9ff86dce6545fa2ccfef98ed7d811a10e4cfe7324a06c3f8d612d693b17e6d1511b2e2f4f677a40ba523891c87` |
| codex-0.162.1-darwin-arm64.tgz | 136605696 | `fe0370027a05237adc0152b482ad8502321f6f9aff1baca3bfa56588923ba9ad` | `/Users/marcin/.npm/_cacache/content-v2/sha512/61/55/e9839ee2b41b90c63a1f6b2dca0c5e546e7645e18d5998d173502cf465089037e0e77713a337957ceeb9d7bcf682e2a08f3b6125ef80f37b0a013fc2723d` |
| codex-0.161.0-darwin-arm64.tgz | 136093696 | `21c99b848b25ed91b92afadabe3751cc33878d2684f3e2d01cc1782e6d0abc7a` | `/Users/marcin/.npm/_cacache/content-v2/sha512/6a/bc/4a2d8077b8a8dec303a9185a39fcc19ef3ee09ccd075eca21806619f178937414f900b889e5d5530a879905f69d7ac1d41ccd30dd20b40826d401814e0f3` |
| codex-0.160.1-darwin-arm64.tgz | 134324224 | `93121cae6c2fe77cdb20f88f611783dbec77a3e241948ad018da120480a6f296` | `/Users/marcin/.npm/_cacache/content-v2/sha512/e9/99/eef7b3bbf887bf727529b162f1e8d95c3dcec336e8fab00b39f31a6dd3fb4a460c78fb1804f7371ad58af0a905018d440ed477b1b9dca29a686966375694` |
| codex-0.160.0-darwin-arm64.tgz | 134311936 | `fc789bcd655d903f92e1a23c8dc5315ba38f43b3586eafb7bd3b195970b57466` | `/Users/marcin/.npm/_cacache/content-v2/sha512/69/e7/d5e9ca9903644466047fff831cc97969ef32dc4ed8b8088dafde3f4856036774f06fda409e344733d3ba9e7a55dcc0e75214f50a6faae8038f2f6660e0ad` |
| codex-0.159.3-darwin-arm64.tgz | 133849088 | `b2838cc82cfd0a9253bab7abbadec09c71fba46b34742a1338b30ca255f41237` | `/Users/marcin/.npm/_cacache/content-v2/sha512/68/8e/14635e185116312719d12be004e1053e69e9349a0b72ca8ed1c3dacd6c24146044d1434358749cd4f72b658c4446a4f961b777471c8d6ee0d86a1e80c90d` |
| codex-0.159.2-darwin-arm64.tgz | 133844992 | `4e491428fef0a676f8ed1c6b392183c24793940c958fa1e7bd99dbcb982d7cc6` | `/Users/marcin/.npm/_cacache/content-v2/sha512/ed/23/da3c5534b5da9aa50e55120ac5fb06fea7d7717d67cb31730a64c44aa163e7fed2cc6a394c8d80419eef28e95b5a547d831d0ea4a67a794cc92fe5baafae` |
| codex-0.158.0-darwin-arm64.tgz | 133525504 | `7849f8aa87c3956823cef082d83b538980a0ced6e468cca4f39c1cf606ea8dae` | `/Users/marcin/.npm/_cacache/content-v2/sha512/d0/e2/928e5598d63e0b7757d3f3b42db4dc376364ad85c5e2e0672b5921e395e660d67f3a786dfeb21265e0fbfeb22526b012615a53669baad13b862ff19c902e` |
| codex-0.157.0-darwin-arm64.tgz | 133013504 | `8ed1854086533492068d2c103e4b13c627b0def7716d038874f05474cb4fc718` | `/Users/marcin/.npm/_cacache/content-v2/sha512/99/c6/8b6d1fad4e2cccafb9f3c41b1c35f3e91ab7719accb20ea5e7a4f3dddb8d7d617a2b0e22c6a45e509ad036f60514160f69a638598ccf39e11e2d5cd1f355` |
| codex-0.156.1-darwin-arm64.tgz | 131653632 | `89823dd350364d5e0cb8a74c1ea585ec2b7307931d9dc0ac4195b8bc8f9e2dfa` | `/Users/marcin/.npm/_cacache/content-v2/sha512/26/0e/b06dd57ec2631973387013be064b139811995588a5e7e8ac82c3fc9faf3dcf00a143d78c658ee3e8a66761582d7ef08294d9674de5f7665cd3eddaae073c` |
| codex-0.155.1-darwin-arm64.tgz | 127467520 | `93cc218b25b71c8da3edb50a013fbd22acf8f39058fb64083fefff638a084976` | `/Users/marcin/.npm/_cacache/content-v2/sha512/71/8c/7319c451a01ae77321e547c79de325f0728549642d698a91942d2c8990614a5c9c3f52ee7b06496fcdacae029b632488a96a69ce937d827d4924d45d1b2f` |
| codex-0.155.0-darwin-arm64.tgz | 127426560 | `318f79a31f2c0974e0c942eeb11913c20ad292d29f6d704cbfe0a6cb43604cf6` | `/Users/marcin/.npm/_cacache/content-v2/sha512/73/4b/dbb76652e97897abd81090d89cb6eecf1f475e332abf6f0e086bd6dd8a15358891ee1aec02e6f0f8b30538c612d42a84ece2d30e1f061629aa1f15971546` |
| codex-0.145.0-darwin-arm64.tgz | 124211200 | `53ff1055d35ca3dc964e8bedc2431e46c00608f7c8e145b222122648a7a4e3e8` | `/Users/marcin/.npm/_cacache/content-v2/sha512/87/a6/90d14c6768ff2620cffdfea3c01fd30d911962268f3cb68ab54f7e88c4d3362f92525344c56a6bbe3199fb6241600ecae9d117e223ef7b4e6f00555c6ab4` |
| codex-0.151.0-darwin-arm64.tgz | 120942592 | `93659b8bd69c4ecd28ae08e2960c668f64d4760480bebe98841904d447026740` | `/Users/marcin/.npm/_cacache/content-v2/sha512/83/b6/33a5a099182c35f51fe0972def44f8e72ea696ec970102ed96410e9ef0f225bc13e64bf80ca6521451132034eea08bc2ec3f376542d2ea930a1e38e94876` |
| codex-0.150.1-darwin-arm64.tgz | 117538816 | `e5008a5b8d7a22e2ad2922a74783de8f7202b7b886a181e6ddbec7633609c885` | `/Users/marcin/.npm/_cacache/content-v2/sha512/67/ad/7890a488dffa7e60ca2d04933109ce24bd1098120b159a76821ba53c1c3adaa9317161c41843bf41e3f1810814bcf3f2ad69c1c8eaace303ee0cbb90729c` |
| codex-0.154.0-darwin-arm64.tgz | 116502528 | `2a98662d79316a59993c7233e3e25a1aa1d42da4b45904585d33a5a7da1cade1` | `/Users/marcin/.npm/_cacache/content-v2/sha512/1c/ff/ef2421ffb76841f4a83a868b4df548250a527aff3e7ce1f6a5e6510fd780bd80d0200104b8fe44d00bb97957e040dd3ab00cfc083528ee976f1c5fc0185e` |
| codex-0.153.4-darwin-arm64.tgz | 115675136 | `535d301b49131abfda3264f959fb0defa40bbc306976d98ddbc15c424636c55c` | `/Users/marcin/.npm/_cacache/content-v2/sha512/07/5a/a13777dad5acb4474c06ce25ea8304a407989ca580a134a1e1b411df7ffd14b524c2ef3fa5f1a4edbcc9468c7dc4f0712f637fa78c825e94cf42000a155a` |
| codex-0.153.2-darwin-arm64.tgz | 115671040 | `151ecdd90b96af823a2828146bff056c8a5f42d2ab4da63a198fe8a4ad84990b` | `/Users/marcin/.npm/_cacache/content-v2/sha512/f1/c1/0958e216e569d29f6f96d51523735b26dac3751fa34ff9c0ab39eef72266a6532db23a4dd02a364cd927e403d8dfddfaa0c2504d52c96118c7a7da899ce6` |
| codex-0.152.0-darwin-arm64.tgz | 114802688 | `cc26642531cb490dec79e8fc1aace175065e4a9e47410628c869965d8d98d20f` | `/Users/marcin/.npm/_cacache/content-v2/sha512/0c/e9/c303a10a3acf9a472b581f87df22e52eb6893da2fa6f08d6b1f1a69366f041d9b2943e352578bacfd6993e8466ab75da94d724aebd730e7e9eae7d7c8e55` |
| codex-0.152.1-darwin-arm64.tgz | 114790400 | `a780ff1a424724778f85c1ccb4de3b908ad1804ef09260cd8140a2ceb7e2ab12` | `/Users/marcin/.npm/_cacache/content-v2/sha512/1f/c8/b4b991c82ccd19d84a7e32bc82179ac65e65e39974f35dfe592ba6e86cab59736c9fa268b8d99ad05ae610e4fd361f4a0b1bb0798cb69259943e5458236c` |
| codex-0.149.1-darwin-arm64.tgz | 114155520 | `151f8b96af0529c1267e7438d2cbc6d26213922fa017b96540abaf5f07d792d2` | `/Users/marcin/.npm/_cacache/content-v2/sha512/e9/7f/3891309b9d380f209d8475c3ecaefc12d16c6caa96be6c2b301a645fe018e1710e673cc9c10bac8201a08c8febeb6d74078fe2fab1af45691e10926035ab` |
| codex-0.149.0-darwin-arm64.tgz | 114102272 | `d1ebcae20ffd79f64db3ebc3141a90d269a67540927f4405dd4d1a752197a642` | `/Users/marcin/.npm/_cacache/content-v2/sha512/1a/c6/496f3056883e3c4444eb3bc54718040d81f4ab515c48b57645783f3bc2cc1ab4f8b4fa52ae428f03c789cc626399859ad5b70af76a5fdf791ad9c670d5f1` |
| codex-0.147.0-darwin-arm64.tgz | 111202304 | `493de2d788c6ff01de222307c767231c1e6c802d5dd808523550fad6d972f4d3` | `/Users/marcin/.npm/_cacache/content-v2/sha512/04/45/15922396ee42dc472acc2df02bfe1f7017cb11549c990f2e8e1ed567e901835e2bf706f0195536353eef7117b29d21d9185dba78b9ac8dd1a0d041a01427` |
| codex-0.137.0-darwin-arm64.tgz | 86990848 | `af1b4b0d57bce14da2b7f247ad49e484155a040d41f9fdf120e78795d8607195` | `/Users/marcin/.npm/_cacache/content-v2/sha512/62/32/a6adeec394ab254158527e8707b1c8319ed64a6997352d0c922a1eeafa134bf2374af9cf2749649e3e2e7cdf2285348c59f19ff30a47b0b6314dbcea5089` |
