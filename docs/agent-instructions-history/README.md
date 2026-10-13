# Historical agent instructions

The active entry points are [CLAUDE.md](../../CLAUDE.md) and the
[workflow index](../../.github/workflows/README.md). Read this archive only for a
specific historical protocol, source reference or registered-byte comparison;
it is not automatically included in the active operating guide.

## Preserved snapshots

Both files below are exact byte copies from commit
`df2aa6c663c8d5712e3bd51885a6806f00982d79`, made for #5017 on 2026-10-12.
No heading, warning or link was inserted into the copies. Their original relative
paths assume the repository root or original workflow directory, respectively;
use the original-location GitHub links when resolving those historical links.

| Snapshot | Original immutable location | Bytes | SHA256 |
|---|---|---:|---|
| [Operating guide v1](operating-guide-2026-10-12-v1.md) | [CLAUDE.md](https://github.com/bridge2ai/data-sheets-schema/blob/df2aa6c663c8d5712e3bd51885a6806f00982d79/CLAUDE.md) | 109,384 | `819a967458540ef4a7d320581ddd70659ce2931252caf9c1e90030aa93585475` |
| [Workflow README v1](workflow-readme-2026-10-12-v1.md) | [.github/workflows/README.md](https://github.com/bridge2ai/data-sheets-schema/blob/df2aa6c663c8d5712e3bd51885a6806f00982d79/.github/workflows/README.md) | 4,704 | `42f3feee4390aabb5bc9407cda2ecbeca45155805fa9246c0e2dd5ffd8a3431b` |

These snapshots contain dated counts, timings, old model-selection advice and
superseded operational directions. In particular, their former PR corpus filter,
three-version CI matrix, GitHub MCP assistant route and `make setup` quickstart
are **not current instructions**. Historical evaluation scores are not a present
quality ranking or evidence of calibration. The active guides correct those routes.

## Selective topic index for operating guide v1

| Topic | Historical detail |
|---|---|
| Dataset/release scope and bundle drift | [Scope](operating-guide-2026-10-12-v1.md#dataset-scope-what-a-record-is-about) |
| Chunking and receipt status/measurement | [Chunk manifests](operating-guide-2026-10-12-v1.md#chunk-manifests-receipts-substrate-707), [coverage receipts](operating-guide-2026-10-12-v1.md#coverage-receipts-708) |
| Reconciliation identity joins | [Receipt paths](operating-guide-2026-10-12-v1.md#receipt-paths-after-reconciliation-899) |
| Runtime-scoped canonical records and review packs | [Method directories](operating-guide-2026-10-12-v1.md#method-directories-and-runtime-scoped-canonicals-690-v8-d6) |
| Human dispositions and prior measurement bases | [Dispositions](operating-guide-2026-10-12-v1.md#review-dispositions-903), [canary bases](operating-guide-2026-10-12-v1.md#canary-measurement-and-curator-bases-12011202) |
| Agent definition echo limits | [Definition evidence](operating-guide-2026-10-12-v1.md#proving-which-agent-definition-a-subagent-read-1077) |
| Prompt pins, live sweeps and reasoning evidence | [Prompt registry](operating-guide-2026-10-12-v1.md#canonical-prompt-registry), [reasoning capture](operating-guide-2026-10-12-v1.md#model-reasoning-capture) |
| Evaluation configuration and exact-file validation | [Model selection](operating-guide-2026-10-12-v1.md#evaluation-model-selection-3325), [validation](operating-guide-2026-10-12-v1.md#validating-the-evaluation-artifacts-833) |
| Schema release and profile boundaries | [Release identity](operating-guide-2026-10-12-v1.md#schema-release-identity-1874-and-the-neutral-generation-schema-1875), [profiles](operating-guide-2026-10-12-v1.md#profiles-the-studys-text-and-vocabularies-628-1302) |
| Manifest registry, resource resolution and cache caveats | [Registry](operating-guide-2026-10-12-v1.md#the-manifest-is-the-project-registry-621-623-624-637-1299), [resources](operating-guide-2026-10-12-v1.md#resources-resolve-from-anywhere-and-the-wheel-ships-them-1301-673), [cache](operating-guide-2026-10-12-v1.md#one-parse-per-file-per-process-1203) |

## Instruction boundary

Root operating guidance v2 replaces the default developer context; it does not
replace a registered generation prompt, selected immutable playbook or captured
run input. Those files are unchanged by this documentation reorganization.
Historical registrations retain the hashes/bytes they actually used. Future runs
must identify their actual selected inputs; the existence of a byte-exact archive
does not make a new root-memory hash interchangeable with an old one.

The archive avoids an `@` include and an auto-loaded `CLAUDE.md` filename. Load
only the selected historical section when it is relevant, checking current source
and the run's own registration before acting on a historical procedure.
