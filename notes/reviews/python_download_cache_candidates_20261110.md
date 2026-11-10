# Package download cache inventory, 2026-11-10

Observed 2026-11-10T05:41:23+00:00 to 2026-11-10T05:41:27+00:00. Read-only inventory; no deletion authorized or performed.

Available bytes at report time: 5,732,810,752.

Allocated bytes are inode st_blocks × 512, deduplicated within each root only. APFS sharing and hardlinks mean allocated totals are not guaranteed reclaimed bytes. File timestamps were sampled before header reads; access times may be incomplete or stale.

Excluded: uv/archive-v0, uv/environments-v2, uv/git-v0, uv/builds-v0, editable source caches, Poetry virtualenvs, installed environments, repositories and run evidence. uv wheel/sdist contents are inventoried without calling them disposable download archives.

Narrow proposal for owner consideration: 26 individually listed npm gzip blobs identified by the existing index as Codex downloads, each modified before 2026-11-01 and having one hardlink, total 3,254,362,112 allocated bytes (3.031 GiB). These are download archives, not the installed executables. No deletion is authorized; verify activity again immediately before any approved cleanup.

Together with the three Homebrew archives, this bounded proposal totals 3,895,635,968 allocated bytes (3.628 GiB). That is an allocation estimate, not a guaranteed free-space gain.

| Root | Allocated GiB | Files | Latest file modification UTC | Status |
|---|---:|---:|---|---|
| `/Users/marcin/Library/Caches/pip` | 2.409 | 6314 | 2026-11-08T22:23:40+00:00 | complete; errors=0; symlinks skipped=0 |
| `/Users/marcin/.cache/pip` | 0.000 | 0 | none observed | absent or symlink: not traversed; errors=0; symlinks skipped=0 |
| `/Users/marcin/Library/Caches/pypoetry/artifacts` | 1.264 | 1082 | 2026-10-25T20:51:51+00:00 | complete; errors=0; symlinks skipped=0 |
| `/Users/marcin/.cache/pypoetry/artifacts` | 0.000 | 0 | none observed | absent or symlink: not traversed; errors=0; symlinks skipped=0 |
| `/Users/marcin/.cache/uv/wheels-v5` | 0.004 | 1048 | 2026-11-10T02:18:25+00:00 | complete; errors=0; symlinks skipped=739 |
| `/Users/marcin/.cache/uv/wheels-v7` | 0.005 | 1989 | 2026-11-05T09:19:01+00:00 | complete; errors=0; symlinks skipped=611 |
| `/Users/marcin/.cache/uv/sdists-v9/pypi` | 0.031 | 1363 | 2026-11-08T04:09:43+00:00 | complete; errors=0; symlinks skipped=21 |
| `/Users/marcin/.cache/uv/sdists-v10/pypi` | 0.016 | 859 | 2026-10-25T21:01:53+00:00 | complete; errors=0; symlinks skipped=17 |
| `/Users/marcin/.npm/_cacache/content-v2` | 4.158 | 1515 | 2026-11-08T03:31:27+00:00 | complete; errors=0; symlinks skipped=0 |

## Largest individual candidate files

Headers identify archive formats only; they do not validate complete archive contents. npm package filenames and registry hosts come from existing cache index entries, without network calls or copying request URLs, headers, credentials, or email addresses.

| Allocated bytes | Apparent bytes | Links | Born UTC | Modified UTC | Accessed UTC | Header | Exact path |
|---:|---:|---:|---|---|---|---|---|
| 148361216 | 148361216 | 1 | 2026-11-08T03:31:12+00:00 | 2026-11-08T03:31:27+00:00 | 2026-11-08T03:31:27+00:00 | gzip (1f8b080000000000) | `/Users/marcin/.npm/_cacache/content-v2/sha512/ed/8b/4c0d95ff8db587f7e7c255083b055b28bfc5af073bb88ae79d5c9103954759c5a4eb617d9b110c07227de9d20c6048c7e6df41c62bdf9b666d5a19265a1f` |
| 147079168 | 147077955 | 1 | 2026-10-30T03:12:22+00:00 | 2026-10-30T03:12:36+00:00 | 2026-10-30T03:12:36+00:00 | gzip (1f8b080000000000) | `/Users/marcin/.npm/_cacache/content-v2/sha512/e5/f5/87eaaa9422700271100321ec239674710dbe102ded2eae2c1e862673d3ebe2b80001f08f9659e7eac38c701efc8a6b17a2197e2e2b9ebebeb81fbc593715` |
| 140709888 | 140709294 | 1 | 2026-10-25T05:03:23+00:00 | 2026-10-25T05:03:35+00:00 | 2026-10-25T05:03:35+00:00 | gzip (1f8b080000000000) | `/Users/marcin/.npm/_cacache/content-v2/sha512/a4/38/b380e500b6adff93701b5051db694d7d5a960a0a36bea05a4d4932caac3423e254d43520ee4cf262a78b90567dbfd448a941da50ac630e40156e235ce700` |
| 137871360 | 137871195 | 1 | 2026-10-16T22:39:37+00:00 | 2026-10-16T22:39:49+00:00 | 2026-10-16T22:39:49+00:00 | gzip (1f8b080000000000) | `/Users/marcin/.npm/_cacache/content-v2/sha512/8b/b0/f39366b96869ae18cf5a35981a5154e88d9ff86dce6545fa2ccfef98ed7d811a10e4cfe7324a06c3f8d612d693b17e6d1511b2e2f4f677a40ba523891c87` |
| 136605696 | 136602385 | 1 | 2026-10-09T20:51:39+00:00 | 2026-10-09T20:51:50+00:00 | 2026-10-09T20:51:50+00:00 | gzip (1f8b080000000000) | `/Users/marcin/.npm/_cacache/content-v2/sha512/61/55/e9839ee2b41b90c63a1f6b2dca0c5e546e7645e18d5998d173502cf465089037e0e77713a337957ceeb9d7bcf682e2a08f3b6125ef80f37b0a013fc2723d` |
| 136093696 | 136091525 | 1 | 2026-10-08T02:31:21+00:00 | 2026-10-08T02:31:34+00:00 | 2026-10-08T02:31:34+00:00 | gzip (1f8b080000000000) | `/Users/marcin/.npm/_cacache/content-v2/sha512/6a/bc/4a2d8077b8a8dec303a9185a39fcc19ef3ee09ccd075eca21806619f178937414f900b889e5d5530a879905f69d7ac1d41ccd30dd20b40826d401814e0f3` |
| 134324224 | 134323627 | 1 | 2026-10-06T01:17:01+00:00 | 2026-10-06T01:17:13+00:00 | 2026-11-10T05:40:21+00:00 | gzip (1f8b080000000000) | `/Users/marcin/.npm/_cacache/content-v2/sha512/e9/99/eef7b3bbf887bf727529b162f1e8d95c3dcec336e8fab00b39f31a6dd3fb4a460c78fb1804f7371ad58af0a905018d440ed477b1b9dca29a686966375694` |
| 134311936 | 134311083 | 1 | 2026-10-02T17:59:06+00:00 | 2026-10-02T17:59:18+00:00 | 2026-11-10T05:40:21+00:00 | gzip (1f8b080000000000) | `/Users/marcin/.npm/_cacache/content-v2/sha512/69/e7/d5e9ca9903644466047fff831cc97969ef32dc4ed8b8088dafde3f4856036774f06fda409e344733d3ba9e7a55dcc0e75214f50a6faae8038f2f6660e0ad` |
| 133849088 | 133847481 | 1 | 2026-10-01T01:37:25+00:00 | 2026-10-01T01:37:36+00:00 | 2026-11-10T05:40:21+00:00 | gzip (1f8b080000000000) | `/Users/marcin/.npm/_cacache/content-v2/sha512/68/8e/14635e185116312719d12be004e1053e69e9349a0b72ca8ed1c3dacd6c24146044d1434358749cd4f72b658c4446a4f961b777471c8d6ee0d86a1e80c90d` |
| 133844992 | 133844825 | 1 | 2026-09-30T03:05:46+00:00 | 2026-09-30T03:05:58+00:00 | 2026-11-10T05:40:21+00:00 | gzip (1f8b080000000000) | `/Users/marcin/.npm/_cacache/content-v2/sha512/ed/23/da3c5534b5da9aa50e55120ac5fb06fea7d7717d67cb31730a64c44aa163e7fed2cc6a394c8d80419eef28e95b5a547d831d0ea4a67a794cc92fe5baafae` |
| 133525504 | 133524491 | 1 | 2026-09-29T06:34:51+00:00 | 2026-09-29T06:35:02+00:00 | 2026-11-10T05:40:21+00:00 | gzip (1f8b080000000000) | `/Users/marcin/.npm/_cacache/content-v2/sha512/d0/e2/928e5598d63e0b7757d3f3b42db4dc376364ad85c5e2e0672b5921e395e660d67f3a786dfeb21265e0fbfeb22526b012615a53669baad13b862ff19c902e` |
| 133013504 | 133011685 | 1 | 2026-09-25T18:49:17+00:00 | 2026-09-25T18:49:28+00:00 | 2026-11-10T05:40:21+00:00 | gzip (1f8b080000000000) | `/Users/marcin/.npm/_cacache/content-v2/sha512/99/c6/8b6d1fad4e2cccafb9f3c41b1c35f3e91ab7719accb20ea5e7a4f3dddb8d7d617a2b0e22c6a45e509ad036f60514160f69a638598ccf39e11e2d5cd1f355` |
| 131653632 | 131652985 | 1 | 2026-09-23T18:11:11+00:00 | 2026-09-23T18:11:23+00:00 | 2026-11-10T05:41:09+00:00 | gzip (1f8b080000000000) | `/Users/marcin/.npm/_cacache/content-v2/sha512/26/0e/b06dd57ec2631973387013be064b139811995588a5e7e8ac82c3fc9faf3dcf00a143d78c658ee3e8a66761582d7ef08294d9674de5f7665cd3eddaae073c` |
| 127467520 | 127465533 | 1 | 2026-09-20T03:40:33+00:00 | 2026-09-20T03:40:44+00:00 | 2026-11-10T05:41:09+00:00 | gzip (1f8b080000000000) | `/Users/marcin/.npm/_cacache/content-v2/sha512/71/8c/7319c451a01ae77321e547c79de325f0728549642d698a91942d2c8990614a5c9c3f52ee7b06496fcdacae029b632488a96a69ce937d827d4924d45d1b2f` |
| 127426560 | 127426335 | 1 | 2026-09-18T00:16:56+00:00 | 2026-09-18T00:17:07+00:00 | 2026-11-10T05:41:09+00:00 | gzip (1f8b080000000000) | `/Users/marcin/.npm/_cacache/content-v2/sha512/73/4b/dbb76652e97897abd81090d89cb6eecf1f475e332abf6f0e086bd6dd8a15358891ee1aec02e6f0f8b30538c612d42a84ece2d30e1f061629aa1f15971546` |
| 124211200 | 124209892 | 1 | 2026-07-22T23:48:54+00:00 | 2026-07-22T23:48:56+00:00 | 2026-07-27T20:21:36+00:00 | gzip (1f8b080000000000) | `/Users/marcin/.npm/_cacache/content-v2/sha512/87/a6/90d14c6768ff2620cffdfea3c01fd30d911962268f3cb68ab54f7e88c4d3362f92525344c56a6bbe3199fb6241600ecae9d117e223ef7b4e6f00555c6ab4` |
| 120942592 | 120938684 | 1 | 2026-08-30T19:05:44+00:00 | 2026-08-30T19:05:47+00:00 | 2026-09-09T00:51:55+00:00 | gzip (1f8b080000000000) | `/Users/marcin/.npm/_cacache/content-v2/sha512/83/b6/33a5a099182c35f51fe0972def44f8e72ea696ec970102ed96410e9ef0f225bc13e64bf80ca6521451132034eea08bc2ec3f376542d2ea930a1e38e94876` |
| 117538816 | 117535191 | 1 | 2026-08-29T01:42:27+00:00 | 2026-08-29T01:42:28+00:00 | 2026-09-09T00:51:56+00:00 | gzip (1f8b080000000000) | `/Users/marcin/.npm/_cacache/content-v2/sha512/67/ad/7890a488dffa7e60ca2d04933109ce24bd1098120b159a76821ba53c1c3adaa9317161c41843bf41e3f1810814bcf3f2ad69c1c8eaace303ee0cbb90729c` |
| 116502528 | 116501639 | 1 | 2026-09-11T01:47:52+00:00 | 2026-09-11T01:48:02+00:00 | 2026-11-10T05:41:09+00:00 | gzip (1f8b080000000000) | `/Users/marcin/.npm/_cacache/content-v2/sha512/1c/ff/ef2421ffb76841f4a83a868b4df548250a527aff3e7ce1f6a5e6510fd780bd80d0200104b8fe44d00bb97957e040dd3ab00cfc083528ee976f1c5fc0185e` |
| 115675136 | 115672312 | 1 | 2026-09-06T08:36:49+00:00 | 2026-09-06T08:36:51+00:00 | 2026-09-09T00:51:56+00:00 | gzip (1f8b080000000000) | `/Users/marcin/.npm/_cacache/content-v2/sha512/07/5a/a13777dad5acb4474c06ce25ea8304a407989ca580a134a1e1b411df7ffd14b524c2ef3fa5f1a4edbcc9468c7dc4f0712f637fa78c825e94cf42000a155a` |
| 115671040 | 115669249 | 1 | 2026-09-04T17:11:00+00:00 | 2026-09-04T17:11:02+00:00 | 2026-09-09T00:51:55+00:00 | gzip (1f8b080000000000) | `/Users/marcin/.npm/_cacache/content-v2/sha512/f1/c1/0958e216e569d29f6f96d51523735b26dac3751fa34ff9c0ab39eef72266a6532db23a4dd02a364cd927e403d8dfddfaa0c2504d52c96118c7a7da899ce6` |
| 114802688 | 114800879 | 1 | 2026-09-01T19:52:44+00:00 | 2026-09-01T19:53:46+00:00 | 2026-09-09T00:51:56+00:00 | gzip (1f8b080000000000) | `/Users/marcin/.npm/_cacache/content-v2/sha512/0c/e9/c303a10a3acf9a472b581f87df22e52eb6893da2fa6f08d6b1f1a69366f041d9b2943e352578bacfd6993e8466ab75da94d724aebd730e7e9eae7d7c8e55` |
| 114790400 | 114790306 | 1 | 2026-09-03T00:59:54+00:00 | 2026-09-03T00:59:56+00:00 | 2026-09-09T00:51:56+00:00 | gzip (1f8b080000000000) | `/Users/marcin/.npm/_cacache/content-v2/sha512/1f/c8/b4b991c82ccd19d84a7e32bc82179ac65e65e39974f35dfe592ba6e86cab59736c9fa268b8d99ad05ae610e4fd361f4a0b1bb0798cb69259943e5458236c` |
| 114155520 | 114152335 | 1 | 2026-08-26T02:26:30+00:00 | 2026-08-26T02:26:32+00:00 | 2026-09-09T00:51:55+00:00 | gzip (1f8b080000000000) | `/Users/marcin/.npm/_cacache/content-v2/sha512/e9/7f/3891309b9d380f209d8475c3ecaefc12d16c6caa96be6c2b301a645fe018e1710e673cc9c10bac8201a08c8febeb6d74078fe2fab1af45691e10926035ab` |
| 114102272 | 114101870 | 1 | 2026-08-21T01:41:32+00:00 | 2026-08-21T01:41:34+00:00 | 2026-08-25T10:27:37+00:00 | gzip (1f8b080000000000) | `/Users/marcin/.npm/_cacache/content-v2/sha512/1a/c6/496f3056883e3c4444eb3bc54718040d81f4ab515c48b57645783f3bc2cc1ab4f8b4fa52ae428f03c789cc626399859ad5b70af76a5fdf791ad9c670d5f1` |
| 111202304 | 111199052 | 1 | 2026-08-18T01:23:17+00:00 | 2026-08-18T01:23:19+00:00 | 2026-08-25T10:27:37+00:00 | gzip (1f8b080000000000) | `/Users/marcin/.npm/_cacache/content-v2/sha512/04/45/15922396ee42dc472acc2df02bfe1f7017cb11549c990f2e8e1ed567e901835e2bf706f0195536353eef7117b29d21d9185dba78b9ac8dd1a0d041a01427` |
| 95911936 | 95907951 | 1 | 2026-08-10T23:16:27+00:00 | 2026-08-10T23:16:27+00:00 | 2026-08-11T00:24:30+00:00 | gzip (1f8b0808c5c24f64) | `/Users/marcin/Library/Caches/pip/http-v2/f/9/c/e/9/f9ce9b83f52c09658d201b8246bbcf08e7b10765997c4778d9cdc9ae.body` |
| 86990848 | 86988487 | 1 | 2026-06-08T18:12:29+00:00 | 2026-06-08T18:12:37+00:00 | 2026-06-10T07:07:58+00:00 | gzip (1f8b080000000000) | `/Users/marcin/.npm/_cacache/content-v2/sha512/62/32/a6adeec394ab254158527e8707b1c8319ed64a6997352d0c922a1eeafa134bf2374af9cf2749649e3e2e7cdf2285348c59f19ff30a47b0b6314dbcea5089` |
| 66531328 | 66530713 | 1 | 2026-10-15T07:46:45+00:00 | 2026-10-15T07:46:45+00:00 | 2026-10-15T07:46:45+00:00 | zip (504b030414000000) | `/Users/marcin/Library/Caches/pip/http-v2/4/8/d/f/4/48df481dd9d7460bf2ba359d42bfe90a23cd179752a9606ae944f4d7.body` |
| 60080128 | 60078598 | 1 | 2026-08-11T06:57:46+00:00 | 2026-08-11T06:57:46+00:00 | 2026-08-25T05:36:05+00:00 | gzip (1f8b080885880965) | `/Users/marcin/Library/Caches/pip/http-v2/f/e/e/3/1/fee31b15a037e76991d5bfc859ad300b6f0ead5e620332f81fd83ef1.body` |
| 46571520 | 46571222 | 1 | 2026-06-10T03:01:39+00:00 | 2026-06-10T03:01:39+00:00 | 2026-06-10T07:07:19+00:00 | zip (504b030414000000) | `/Users/marcin/Library/Caches/pip/http-v2/8/c/e/2/0/8ce20e77a07a745ce0fda0eef43c07614263668d6d145b7bf78d1b66.body` |
| 46247936 | 46247192 | 1 | 2026-06-26T19:30:43+00:00 | 2026-06-26T19:30:43+00:00 | 2026-08-25T05:36:04+00:00 | zip (504b030414000000) | `/Users/marcin/Library/Caches/pip/http-v2/3/3/3/5/f/3335ff1d8a79a735d37043f43e83d4e20f0626e42e1068758a173d9c.body` |
| 45608960 | 45605899 | 1 | 2026-07-21T21:06:22+00:00 | 2026-07-21T21:06:22+00:00 | 2026-08-25T05:36:04+00:00 | zip (504b030414000000) | `/Users/marcin/Library/Caches/pip/http-v2/3/3/6/4/5/3364552366ec479bb19e4a73939451f2ec3002108c453e0bc65e8c6a.body` |
| 42946560 | 42944679 | 1 | 2026-10-07T19:36:55+00:00 | 2026-10-07T19:36:55+00:00 | 2026-10-07T19:37:00+00:00 | zip (504b030414000000) | `/Users/marcin/Library/Caches/pip/http-v2/9/3/4/7/8/93478e4e3db38fa600e849f5eb0ad8e376099fba7bcfe5afce893d31.body` |
| 40480768 | 40479230 | 1 | 2026-08-21T04:53:20+00:00 | 2026-08-21T04:53:20+00:00 | 2026-08-25T05:36:04+00:00 | zip (504b030414000000) | `/Users/marcin/Library/Caches/pip/http-v2/3/3/9/5/a/3395a674017fb333aa1b9cba6bba759d62b8e478c612fc1176975617.body` |
| 40480768 | 40480652 | 1 | 2026-07-04T09:07:17+00:00 | 2026-07-04T09:07:17+00:00 | 2026-08-25T05:36:05+00:00 | zip (504b030414000000) | `/Users/marcin/Library/Caches/pip/http-v2/a/3/5/5/3/a3553cce0d4fb19dfa9577ac263ff9384e5a402acef82ce7629a1e58.body` |
| 35954688 | 35954271 | 1 | 2026-09-08T05:39:15+00:00 | 2026-09-08T05:39:17+00:00 | 2026-09-08T05:39:17+00:00 | zip (504b030414000000) | `/Users/marcin/Library/Caches/pypoetry/artifacts/7c/db/98/92b4d43464b40cb3c6894504daf6b9b8b3d8f6beac0240bfc5b1c1feff/pyarrow-25.0.1-cp310-cp310-macosx_12_0_arm64.whl` |
| 35864576 | 35861559 | 1 | 2026-09-08T04:42:25+00:00 | 2026-09-08T04:42:34+00:00 | 2026-09-08T04:42:34+00:00 | zip (504b030414000000) | `/Users/marcin/Library/Caches/pypoetry/artifacts/b1/66/c4/47182c55802799396cb4df1c29e5afb8a35c622961368865d86c6482aa/pyarrow-25.0.1-cp312-cp312-macosx_12_0_arm64.whl` |
| 34979840 | 34976759 | 1 | 2026-06-05T02:00:00+00:00 | 2026-06-05T02:00:00+00:00 | 2026-06-10T07:07:19+00:00 | zip (504b030414000000) | `/Users/marcin/Library/Caches/pip/http-v2/0/e/c/d/0/0ecd0548575f741d7d0bbdcef91d35c4d5403bd13532949d803d1f55.body` |

## Exact npm proposal subset

Every path below is included in the narrow allocated-byte sum above. This list is a proposal only.

- `/Users/marcin/.npm/_cacache/content-v2/sha512/e5/f5/87eaaa9422700271100321ec239674710dbe102ded2eae2c1e862673d3ebe2b80001f08f9659e7eac38c701efc8a6b17a2197e2e2b9ebebeb81fbc593715` (147,079,168 allocated bytes; codex-0.166.0-darwin-arm64.tgz (registry host: registry.npmjs.org))
- `/Users/marcin/.npm/_cacache/content-v2/sha512/a4/38/b380e500b6adff93701b5051db694d7d5a960a0a36bea05a4d4932caac3423e254d43520ee4cf262a78b90567dbfd448a941da50ac630e40156e235ce700` (140,709,888 allocated bytes; codex-0.164.0-darwin-arm64.tgz (registry host: registry.npmjs.org))
- `/Users/marcin/.npm/_cacache/content-v2/sha512/8b/b0/f39366b96869ae18cf5a35981a5154e88d9ff86dce6545fa2ccfef98ed7d811a10e4cfe7324a06c3f8d612d693b17e6d1511b2e2f4f677a40ba523891c87` (137,871,360 allocated bytes; codex-0.163.0-darwin-arm64.tgz (registry host: registry.npmjs.org))
- `/Users/marcin/.npm/_cacache/content-v2/sha512/61/55/e9839ee2b41b90c63a1f6b2dca0c5e546e7645e18d5998d173502cf465089037e0e77713a337957ceeb9d7bcf682e2a08f3b6125ef80f37b0a013fc2723d` (136,605,696 allocated bytes; codex-0.162.1-darwin-arm64.tgz (registry host: registry.npmjs.org))
- `/Users/marcin/.npm/_cacache/content-v2/sha512/6a/bc/4a2d8077b8a8dec303a9185a39fcc19ef3ee09ccd075eca21806619f178937414f900b889e5d5530a879905f69d7ac1d41ccd30dd20b40826d401814e0f3` (136,093,696 allocated bytes; codex-0.161.0-darwin-arm64.tgz (registry host: registry.npmjs.org))
- `/Users/marcin/.npm/_cacache/content-v2/sha512/e9/99/eef7b3bbf887bf727529b162f1e8d95c3dcec336e8fab00b39f31a6dd3fb4a460c78fb1804f7371ad58af0a905018d440ed477b1b9dca29a686966375694` (134,324,224 allocated bytes; codex-0.160.1-darwin-arm64.tgz (registry host: registry.npmjs.org))
- `/Users/marcin/.npm/_cacache/content-v2/sha512/69/e7/d5e9ca9903644466047fff831cc97969ef32dc4ed8b8088dafde3f4856036774f06fda409e344733d3ba9e7a55dcc0e75214f50a6faae8038f2f6660e0ad` (134,311,936 allocated bytes; codex-0.160.0-darwin-arm64.tgz (registry host: registry.npmjs.org))
- `/Users/marcin/.npm/_cacache/content-v2/sha512/68/8e/14635e185116312719d12be004e1053e69e9349a0b72ca8ed1c3dacd6c24146044d1434358749cd4f72b658c4446a4f961b777471c8d6ee0d86a1e80c90d` (133,849,088 allocated bytes; codex-0.159.3-darwin-arm64.tgz (registry host: registry.npmjs.org))
- `/Users/marcin/.npm/_cacache/content-v2/sha512/ed/23/da3c5534b5da9aa50e55120ac5fb06fea7d7717d67cb31730a64c44aa163e7fed2cc6a394c8d80419eef28e95b5a547d831d0ea4a67a794cc92fe5baafae` (133,844,992 allocated bytes; codex-0.159.2-darwin-arm64.tgz (registry host: registry.npmjs.org))
- `/Users/marcin/.npm/_cacache/content-v2/sha512/d0/e2/928e5598d63e0b7757d3f3b42db4dc376364ad85c5e2e0672b5921e395e660d67f3a786dfeb21265e0fbfeb22526b012615a53669baad13b862ff19c902e` (133,525,504 allocated bytes; codex-0.158.0-darwin-arm64.tgz (registry host: registry.npmjs.org))
- `/Users/marcin/.npm/_cacache/content-v2/sha512/99/c6/8b6d1fad4e2cccafb9f3c41b1c35f3e91ab7719accb20ea5e7a4f3dddb8d7d617a2b0e22c6a45e509ad036f60514160f69a638598ccf39e11e2d5cd1f355` (133,013,504 allocated bytes; codex-0.157.0-darwin-arm64.tgz (registry host: registry.npmjs.org))
- `/Users/marcin/.npm/_cacache/content-v2/sha512/26/0e/b06dd57ec2631973387013be064b139811995588a5e7e8ac82c3fc9faf3dcf00a143d78c658ee3e8a66761582d7ef08294d9674de5f7665cd3eddaae073c` (131,653,632 allocated bytes; codex-0.156.1-darwin-arm64.tgz (registry host: registry.npmjs.org))
- `/Users/marcin/.npm/_cacache/content-v2/sha512/71/8c/7319c451a01ae77321e547c79de325f0728549642d698a91942d2c8990614a5c9c3f52ee7b06496fcdacae029b632488a96a69ce937d827d4924d45d1b2f` (127,467,520 allocated bytes; codex-0.155.1-darwin-arm64.tgz (registry host: registry.npmjs.org))
- `/Users/marcin/.npm/_cacache/content-v2/sha512/73/4b/dbb76652e97897abd81090d89cb6eecf1f475e332abf6f0e086bd6dd8a15358891ee1aec02e6f0f8b30538c612d42a84ece2d30e1f061629aa1f15971546` (127,426,560 allocated bytes; codex-0.155.0-darwin-arm64.tgz (registry host: registry.npmjs.org))
- `/Users/marcin/.npm/_cacache/content-v2/sha512/87/a6/90d14c6768ff2620cffdfea3c01fd30d911962268f3cb68ab54f7e88c4d3362f92525344c56a6bbe3199fb6241600ecae9d117e223ef7b4e6f00555c6ab4` (124,211,200 allocated bytes; codex-0.145.0-darwin-arm64.tgz (registry host: registry.npmjs.org))
- `/Users/marcin/.npm/_cacache/content-v2/sha512/83/b6/33a5a099182c35f51fe0972def44f8e72ea696ec970102ed96410e9ef0f225bc13e64bf80ca6521451132034eea08bc2ec3f376542d2ea930a1e38e94876` (120,942,592 allocated bytes; codex-0.151.0-darwin-arm64.tgz (registry host: registry.npmjs.org))
- `/Users/marcin/.npm/_cacache/content-v2/sha512/67/ad/7890a488dffa7e60ca2d04933109ce24bd1098120b159a76821ba53c1c3adaa9317161c41843bf41e3f1810814bcf3f2ad69c1c8eaace303ee0cbb90729c` (117,538,816 allocated bytes; codex-0.150.1-darwin-arm64.tgz (registry host: registry.npmjs.org))
- `/Users/marcin/.npm/_cacache/content-v2/sha512/1c/ff/ef2421ffb76841f4a83a868b4df548250a527aff3e7ce1f6a5e6510fd780bd80d0200104b8fe44d00bb97957e040dd3ab00cfc083528ee976f1c5fc0185e` (116,502,528 allocated bytes; codex-0.154.0-darwin-arm64.tgz (registry host: registry.npmjs.org))
- `/Users/marcin/.npm/_cacache/content-v2/sha512/07/5a/a13777dad5acb4474c06ce25ea8304a407989ca580a134a1e1b411df7ffd14b524c2ef3fa5f1a4edbcc9468c7dc4f0712f637fa78c825e94cf42000a155a` (115,675,136 allocated bytes; codex-0.153.4-darwin-arm64.tgz (registry host: registry.npmjs.org))
- `/Users/marcin/.npm/_cacache/content-v2/sha512/f1/c1/0958e216e569d29f6f96d51523735b26dac3751fa34ff9c0ab39eef72266a6532db23a4dd02a364cd927e403d8dfddfaa0c2504d52c96118c7a7da899ce6` (115,671,040 allocated bytes; codex-0.153.2-darwin-arm64.tgz (registry host: registry.npmjs.org))
- `/Users/marcin/.npm/_cacache/content-v2/sha512/0c/e9/c303a10a3acf9a472b581f87df22e52eb6893da2fa6f08d6b1f1a69366f041d9b2943e352578bacfd6993e8466ab75da94d724aebd730e7e9eae7d7c8e55` (114,802,688 allocated bytes; codex-0.152.0-darwin-arm64.tgz (registry host: registry.npmjs.org))
- `/Users/marcin/.npm/_cacache/content-v2/sha512/1f/c8/b4b991c82ccd19d84a7e32bc82179ac65e65e39974f35dfe592ba6e86cab59736c9fa268b8d99ad05ae610e4fd361f4a0b1bb0798cb69259943e5458236c` (114,790,400 allocated bytes; codex-0.152.1-darwin-arm64.tgz (registry host: registry.npmjs.org))
- `/Users/marcin/.npm/_cacache/content-v2/sha512/e9/7f/3891309b9d380f209d8475c3ecaefc12d16c6caa96be6c2b301a645fe018e1710e673cc9c10bac8201a08c8febeb6d74078fe2fab1af45691e10926035ab` (114,155,520 allocated bytes; codex-0.149.1-darwin-arm64.tgz (registry host: registry.npmjs.org))
- `/Users/marcin/.npm/_cacache/content-v2/sha512/1a/c6/496f3056883e3c4444eb3bc54718040d81f4ab515c48b57645783f3bc2cc1ab4f8b4fa52ae428f03c789cc626399859ad5b70af76a5fdf791ad9c670d5f1` (114,102,272 allocated bytes; codex-0.149.0-darwin-arm64.tgz (registry host: registry.npmjs.org))
- `/Users/marcin/.npm/_cacache/content-v2/sha512/04/45/15922396ee42dc472acc2df02bfe1f7017cb11549c990f2e8e1ed567e901835e2bf706f0195536353eef7117b29d21d9185dba78b9ac8dd1a0d041a01427` (111,202,304 allocated bytes; codex-0.147.0-darwin-arm64.tgz (registry host: registry.npmjs.org))
- `/Users/marcin/.npm/_cacache/content-v2/sha512/62/32/a6adeec394ab254158527e8707b1c8319ed64a6997352d0c922a1eeafa134bf2374af9cf2749649e3e2e7cdf2285348c59f19ff30a47b0b6314dbcea5089` (86,990,848 allocated bytes; codex-0.137.0-darwin-arm64.tgz (registry host: registry.npmjs.org))

## npm index provenance

complete npm index lookup for selected blob paths; no integrity rehash

- `/Users/marcin/.npm/_cacache/content-v2/sha512/ed/8b/4c0d95ff8db587f7e7c255083b055b28bfc5af073bb88ae79d5c9103954759c5a4eb617d9b110c07227de9d20c6048c7e6df41c62bdf9b666d5a19265a1f`: codex-0.167.0-darwin-arm64.tgz (registry host: registry.npmjs.org)
- `/Users/marcin/.npm/_cacache/content-v2/sha512/e5/f5/87eaaa9422700271100321ec239674710dbe102ded2eae2c1e862673d3ebe2b80001f08f9659e7eac38c701efc8a6b17a2197e2e2b9ebebeb81fbc593715`: codex-0.166.0-darwin-arm64.tgz (registry host: registry.npmjs.org)
- `/Users/marcin/.npm/_cacache/content-v2/sha512/a4/38/b380e500b6adff93701b5051db694d7d5a960a0a36bea05a4d4932caac3423e254d43520ee4cf262a78b90567dbfd448a941da50ac630e40156e235ce700`: codex-0.164.0-darwin-arm64.tgz (registry host: registry.npmjs.org)
- `/Users/marcin/.npm/_cacache/content-v2/sha512/8b/b0/f39366b96869ae18cf5a35981a5154e88d9ff86dce6545fa2ccfef98ed7d811a10e4cfe7324a06c3f8d612d693b17e6d1511b2e2f4f677a40ba523891c87`: codex-0.163.0-darwin-arm64.tgz (registry host: registry.npmjs.org)
- `/Users/marcin/.npm/_cacache/content-v2/sha512/61/55/e9839ee2b41b90c63a1f6b2dca0c5e546e7645e18d5998d173502cf465089037e0e77713a337957ceeb9d7bcf682e2a08f3b6125ef80f37b0a013fc2723d`: codex-0.162.1-darwin-arm64.tgz (registry host: registry.npmjs.org)
- `/Users/marcin/.npm/_cacache/content-v2/sha512/6a/bc/4a2d8077b8a8dec303a9185a39fcc19ef3ee09ccd075eca21806619f178937414f900b889e5d5530a879905f69d7ac1d41ccd30dd20b40826d401814e0f3`: codex-0.161.0-darwin-arm64.tgz (registry host: registry.npmjs.org)
- `/Users/marcin/.npm/_cacache/content-v2/sha512/e9/99/eef7b3bbf887bf727529b162f1e8d95c3dcec336e8fab00b39f31a6dd3fb4a460c78fb1804f7371ad58af0a905018d440ed477b1b9dca29a686966375694`: codex-0.160.1-darwin-arm64.tgz (registry host: registry.npmjs.org)
- `/Users/marcin/.npm/_cacache/content-v2/sha512/69/e7/d5e9ca9903644466047fff831cc97969ef32dc4ed8b8088dafde3f4856036774f06fda409e344733d3ba9e7a55dcc0e75214f50a6faae8038f2f6660e0ad`: codex-0.160.0-darwin-arm64.tgz (registry host: registry.npmjs.org)
- `/Users/marcin/.npm/_cacache/content-v2/sha512/68/8e/14635e185116312719d12be004e1053e69e9349a0b72ca8ed1c3dacd6c24146044d1434358749cd4f72b658c4446a4f961b777471c8d6ee0d86a1e80c90d`: codex-0.159.3-darwin-arm64.tgz (registry host: registry.npmjs.org)
- `/Users/marcin/.npm/_cacache/content-v2/sha512/ed/23/da3c5534b5da9aa50e55120ac5fb06fea7d7717d67cb31730a64c44aa163e7fed2cc6a394c8d80419eef28e95b5a547d831d0ea4a67a794cc92fe5baafae`: codex-0.159.2-darwin-arm64.tgz (registry host: registry.npmjs.org)
- `/Users/marcin/.npm/_cacache/content-v2/sha512/d0/e2/928e5598d63e0b7757d3f3b42db4dc376364ad85c5e2e0672b5921e395e660d67f3a786dfeb21265e0fbfeb22526b012615a53669baad13b862ff19c902e`: codex-0.158.0-darwin-arm64.tgz (registry host: registry.npmjs.org)
- `/Users/marcin/.npm/_cacache/content-v2/sha512/99/c6/8b6d1fad4e2cccafb9f3c41b1c35f3e91ab7719accb20ea5e7a4f3dddb8d7d617a2b0e22c6a45e509ad036f60514160f69a638598ccf39e11e2d5cd1f355`: codex-0.157.0-darwin-arm64.tgz (registry host: registry.npmjs.org)
- `/Users/marcin/.npm/_cacache/content-v2/sha512/26/0e/b06dd57ec2631973387013be064b139811995588a5e7e8ac82c3fc9faf3dcf00a143d78c658ee3e8a66761582d7ef08294d9674de5f7665cd3eddaae073c`: codex-0.156.1-darwin-arm64.tgz (registry host: registry.npmjs.org)
- `/Users/marcin/.npm/_cacache/content-v2/sha512/71/8c/7319c451a01ae77321e547c79de325f0728549642d698a91942d2c8990614a5c9c3f52ee7b06496fcdacae029b632488a96a69ce937d827d4924d45d1b2f`: codex-0.155.1-darwin-arm64.tgz (registry host: registry.npmjs.org)
- `/Users/marcin/.npm/_cacache/content-v2/sha512/73/4b/dbb76652e97897abd81090d89cb6eecf1f475e332abf6f0e086bd6dd8a15358891ee1aec02e6f0f8b30538c612d42a84ece2d30e1f061629aa1f15971546`: codex-0.155.0-darwin-arm64.tgz (registry host: registry.npmjs.org)
- `/Users/marcin/.npm/_cacache/content-v2/sha512/87/a6/90d14c6768ff2620cffdfea3c01fd30d911962268f3cb68ab54f7e88c4d3362f92525344c56a6bbe3199fb6241600ecae9d117e223ef7b4e6f00555c6ab4`: codex-0.145.0-darwin-arm64.tgz (registry host: registry.npmjs.org)
- `/Users/marcin/.npm/_cacache/content-v2/sha512/83/b6/33a5a099182c35f51fe0972def44f8e72ea696ec970102ed96410e9ef0f225bc13e64bf80ca6521451132034eea08bc2ec3f376542d2ea930a1e38e94876`: codex-0.151.0-darwin-arm64.tgz (registry host: registry.npmjs.org)
- `/Users/marcin/.npm/_cacache/content-v2/sha512/67/ad/7890a488dffa7e60ca2d04933109ce24bd1098120b159a76821ba53c1c3adaa9317161c41843bf41e3f1810814bcf3f2ad69c1c8eaace303ee0cbb90729c`: codex-0.150.1-darwin-arm64.tgz (registry host: registry.npmjs.org)
- `/Users/marcin/.npm/_cacache/content-v2/sha512/1c/ff/ef2421ffb76841f4a83a868b4df548250a527aff3e7ce1f6a5e6510fd780bd80d0200104b8fe44d00bb97957e040dd3ab00cfc083528ee976f1c5fc0185e`: codex-0.154.0-darwin-arm64.tgz (registry host: registry.npmjs.org)
- `/Users/marcin/.npm/_cacache/content-v2/sha512/07/5a/a13777dad5acb4474c06ce25ea8304a407989ca580a134a1e1b411df7ffd14b524c2ef3fa5f1a4edbcc9468c7dc4f0712f637fa78c825e94cf42000a155a`: codex-0.153.4-darwin-arm64.tgz (registry host: registry.npmjs.org)
- `/Users/marcin/.npm/_cacache/content-v2/sha512/f1/c1/0958e216e569d29f6f96d51523735b26dac3751fa34ff9c0ab39eef72266a6532db23a4dd02a364cd927e403d8dfddfaa0c2504d52c96118c7a7da899ce6`: codex-0.153.2-darwin-arm64.tgz (registry host: registry.npmjs.org)
- `/Users/marcin/.npm/_cacache/content-v2/sha512/0c/e9/c303a10a3acf9a472b581f87df22e52eb6893da2fa6f08d6b1f1a69366f041d9b2943e352578bacfd6993e8466ab75da94d724aebd730e7e9eae7d7c8e55`: codex-0.152.0-darwin-arm64.tgz (registry host: registry.npmjs.org)
- `/Users/marcin/.npm/_cacache/content-v2/sha512/1f/c8/b4b991c82ccd19d84a7e32bc82179ac65e65e39974f35dfe592ba6e86cab59736c9fa268b8d99ad05ae610e4fd361f4a0b1bb0798cb69259943e5458236c`: codex-0.152.1-darwin-arm64.tgz (registry host: registry.npmjs.org)
- `/Users/marcin/.npm/_cacache/content-v2/sha512/e9/7f/3891309b9d380f209d8475c3ecaefc12d16c6caa96be6c2b301a645fe018e1710e673cc9c10bac8201a08c8febeb6d74078fe2fab1af45691e10926035ab`: codex-0.149.1-darwin-arm64.tgz (registry host: registry.npmjs.org)
- `/Users/marcin/.npm/_cacache/content-v2/sha512/1a/c6/496f3056883e3c4444eb3bc54718040d81f4ab515c48b57645783f3bc2cc1ab4f8b4fa52ae428f03c789cc626399859ad5b70af76a5fdf791ad9c670d5f1`: codex-0.149.0-darwin-arm64.tgz (registry host: registry.npmjs.org)
- `/Users/marcin/.npm/_cacache/content-v2/sha512/04/45/15922396ee42dc472acc2df02bfe1f7017cb11549c990f2e8e1ed567e901835e2bf706f0195536353eef7117b29d21d9185dba78b9ac8dd1a0d041a01427`: codex-0.147.0-darwin-arm64.tgz (registry host: registry.npmjs.org)
- `/Users/marcin/.npm/_cacache/content-v2/sha512/62/32/a6adeec394ab254158527e8707b1c8319ed64a6997352d0c922a1eeafa134bf2374af9cf2749649e3e2e7cdf2285348c59f19ff30a47b0b6314dbcea5089`: codex-0.137.0-darwin-arm64.tgz (registry host: registry.npmjs.org)

## Visible open handles

One non-root lsof snapshot; absence is not proof of future non-use or visibility into every process. Active npm/package jobs may open files after this snapshot.

```json
{
  "returncode": 0,
  "stderr": "",
  "handles": []
}
```

## Preserved Homebrew three-archive result

Reverified with `scripts/adhoc/inspect_download_cache_candidates_20261110.py --verify-candidates`. The three archives total 641,273,856 allocated bytes (611.566 MiB), consistent with the initial 611.6 MiB result. All three headers are gzip and each has one hardlink. The Boost archive has an access timestamp older than 180 days, which is only a staleness signal. lsof return code 1 with empty stdout/stderr means no matching visible open files in that snapshot, not a future-use guarantee.

```json
{
  "candidates": [
    {
      "path": "/Users/marcin/Library/Caches/Homebrew/downloads/16fca3c6850968dd4f578d905c8a9af19cdd1accd73606674ece7764b3e8047b--llvm--23.1.3_1.arm64_tahoe.bottle.tar.gz",
      "allocated_bytes": 457068544,
      "apparent_bytes": 457065756,
      "hardlinks": 1,
      "birth_utc": "2026-10-09T17:31:29+00:00",
      "mtime_utc": "2026-10-09T17:31:29+00:00",
      "atime_utc_before_header_read": "2026-10-09T17:31:29+00:00",
      "magic_hex": "1f8b"
    },
    {
      "path": "/Users/marcin/Library/Caches/Homebrew/downloads/cf1723dbb152ee4dc893a709c87f5e88b014e29e282cb8dc577d621bff2fc108--dssp--4.6.1.arm64_tahoe.bottle.tar.gz",
      "allocated_bytes": 122880000,
      "apparent_bytes": 122878849,
      "hardlinks": 1,
      "birth_utc": "2026-07-07T13:03:22+00:00",
      "mtime_utc": "2026-07-07T13:03:22+00:00",
      "atime_utc_before_header_read": "2026-07-07T13:03:22+00:00",
      "magic_hex": "1f8b"
    },
    {
      "path": "/Users/marcin/Library/Caches/Homebrew/downloads/6442a2d950abe9d76d29f573a3b501a65765fb4d113113833733a833ce6abfde--boost--1.90.0_1.arm64_tahoe.bottle.tar.gz",
      "allocated_bytes": 61325312,
      "apparent_bytes": 61322435,
      "hardlinks": 1,
      "birth_utc": "2026-02-08T06:05:56+00:00",
      "mtime_utc": "2026-02-08T06:05:56+00:00",
      "atime_utc_before_header_read": "2026-02-08T06:05:56+00:00",
      "magic_hex": "1f8b"
    }
  ],
  "allocated_bytes_sum": 641273856,
  "allocated_mib_sum": 611.56640625,
  "lsof_returncode": 1,
  "lsof_stdout": "",
  "lsof_stderr": ""
}
```

Provenance helpers: `scripts/adhoc/inspect_download_cache_candidates_20261110.py` and `scripts/adhoc/inspect_python_download_caches_20261110.py`.

## Limitations and proposed scope

Only confirmed npm gzip blobs or explicit wheel/source archive files are individual download candidates. No uv extracted tree is proposed for deletion. npm content cache is distinct from installed node_modules, but deletion still requires explicit owner approval and a fresh activity/handle check. Cache index entries may refer to content removed individually, so prefer the package manager cleanup mechanism after reviewing active installers. Do not run cleanup while an installer is using the cache.

Atime age alone is not disposal authority; no full-home absence or exhaustive safe-space claim is made. Missing roots were checked directly, independent of gitignore.
