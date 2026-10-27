# Installed D38 validation on the N2 restack

Refs #4354, #5170. Tested source: `f2dca0dd1f16769a10f65df96cb96caa2498a7cd`,
source tree `a1b587b4eefb0b310117f2f921567a056bde93fc`. The restack inherits
the actual target `a0e28d8821c69e2d4fe1b75b14e3c2a2140ae4d5` and D38 assets from
`f73764e0685f436a07e802766e16030572d29a18`. This note records installed-asset
and offline full-instruction validation, not public runtime or scientific acceptance.

The frozen two-module helper run passed **27 tests**, zero failures/errors/skips,
one dateutil deprecation warning, **3.35 s**, exit 0. The full offline render then
exited 0 with `verified_installed_assets_and_full_offline_render`. It verified:

- All **13 actual installed assets**: ten ordinary checkout files and three
  module-adjacent omission files. Every positive captured path equals its path in
  the selected checkout; no substituted positive asset root is used. The two
  native-only prompts are checked against preserved N2 authority; the other
  eleven assets also equal the actual target's Git blobs.
- Generic prompt SHA256 `ec081dbb14049449989c56169de7bcd1563076667818c12b78571b5f15acb2db`
  and uniform playbook SHA256 `22a553695536a822e9c7ae877663a9b251c889a6637c637e579c5c6e1c855b2e`.
  Protected `shared_generation.py` and `canonical_hashes.yaml` equal the target.
- The complete **4,433-byte D38 R9 passage**, SHA256
  `d9f7884a03f0480d1ab610118f32850e2d98008fcd67fb51a16a4b7b7ca79a4d`, occurs
  exactly once in each full API25/native26 instruction. The complete extracted
  **25,589-byte uniform sections** are identical, SHA256
  `44a2a05b4e9d410d7628df57cfaeb9dedc532189199e6df85515569e33fec530`.
- Three exact stale-asset refusals: both pre-D38 assets, old generic only and old
  uniform only. These use separate negative fixtures. Actual installed closure
  is recaptured afterward and remains identical.
- **331 committed Python source files** with an ignored-file-inclusive source
  inventory, and **47 loaded project module/namespace origins**. Source and all
  observed inputs stayed unchanged. Existing dependency packages are used with
  site/.pth execution disabled; their complete package bytes are not attested.

The full API/native instructions intentionally differ. Complete text, render
specifications and historical/current diffs are retained for independent review;
see [the instruction-delta review](installed_render_review.md). Shared-rule
identity does not establish equal effective contexts or scientific equivalence.

The original 20261025 render helper remains byte-identical to its historical
source, SHA256 `24c25f12b941d2384d37496098ea80d55732698d83cda10257c500b60d0ea6a6`.
Its unit fixture now reads the exact pre-D38 generic Git blob explicitly, preserving
that helper's historical contract. The new installed helper has SHA256
`c790b541b74a8ae949c999f6419d2be317850ebecc6fa81197fabc2dedf5c832` at the tested head.

## Evidence and reproduction

The original evidence directory remains intact at
`/private/tmp/d4d-n2-restack-installed-d38-20261026/`. Its report SHA256 is
`c18485bc72e1ce659625781ca83f1ffc17213101cd51fd3d313454c91d370771`.
The [retained report](installed_d38_evidence/render-report.json) records the
exact argument values, pinned historical CHORUS inputs, source closure, output
hashes and actual capture paths.

The [manifest](installed_d38_evidence/manifest.json) inventories all 48 render
files and exact log/JUnit copies. The complete [compressed render archive](installed_d38_evidence/installed-render.tar.gz)
is 436,304 bytes, SHA256
`6c2cad8fde6d60cf52322725813c4af419e325fc152074485166684c58274e9e`.
The preservation helper reconstructed every archived file and compared its bytes
with the retained source, then reread the original directory. Original artifacts
were not removed or altered. Extract the archive into a fresh directory; entries
are under `installed-render/`. Preservation covers file bytes and file modes;
archive timestamps are normalized, and directory metadata is not archived.

The focused invocation ran from the selected checkout with
`PYTHONDONTWRITEBYTECODE=1`, `PYTHONPATH=<tree>/src:<tree>`, all three provider-key
variables unset, and the primary checkout's absolute `.venv/bin/python`:

```text
python -m pytest -q -p no:cacheprovider
  --basetemp=/private/tmp/d4d-n2-restack-d38-focused-20261026
  --junitxml=/private/tmp/d4d-n2-restack-d38-focused-20261026.xml
  tests/test_native_n2_installed_d38_20261026.py
  tests/test_native_n2_render_parity_20261025.py
```

The full render used the same absolute interpreter with `-S -P -B`,
`PYTHONPATH=<tree>/src` and
`PYTHONPYCACHEPREFIX=/private/tmp/d4d-n2-restack-installed-d38-20261026/unused-import-cache`.
Its entry point is
[`native_n2_installed_d38_20261026.py`](../../scripts/adhoc/native_n2_installed_d38_20261026.py).
Pass the exact `argv` values in the retained report, changing only the fresh
evidence destination/name, matching cache path, and explicitly selected source
head when performing a new run. Network/provider/native subprocesses are refused
by the helper's offline audit hook.

Preservation is reproducible through
[`preserve_native_n2_d38_evidence_20261026.py`](../../scripts/adhoc/preserve_native_n2_d38_evidence_20261026.py),
with exact arguments and helper hash in its manifest. The evidence delivery adds
documentation and preservation/comparison helpers after the tested source; it is
not a new render/test run. The preservation check confirms unchanged `src/`,
`tests/` and both render helpers against `f2dca0dd1`.

The render uses hypothetical API/native registrations, a pending diagnostic
receipt floor and explicit placeholder native limits. It does not choose future
production caps, establish receipt-v5/A12/A13 compatibility, run a native binary,
authorize a canary, or replace the separate full N2 and public-runtime gates.
