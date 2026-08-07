# D4D Agent Playbooks

Repository-local commands and conversational agents for D4D datasheet
generation and schema analysis. The files live under `.claude/` for Claude Code
compatibility, but the generation playbooks are model-neutral and may also be
read and executed by Codex/GPT agents.

## Usage

### Slash Commands

In Claude Code, type the command name to expand the instructions. In Codex/GPT,
tell the agent to read the corresponding command file before execution.

```
/d4d-agent        # Model-neutral project-agent approach (full D4D only)
/d4d-full-core    # Model-neutral four-phase full/core production workflow
/d4d-assistant    # Assistant approach following workflow methodology
/d4d-webfetch     # Live URL fetching with WebFetch + ARTL
/d4d-input-deep-research # Monarch deep-research client over input docs (research-augmented arm)
/d4d-add-mapping  # Add D4D ↔ RO-Crate SSSOM mappings for new classes
```

### Conversational Agents

Invoke agents by mentioning their purpose in conversation or using the Skill tool:

```
# Schema analysis
"Show me D4D schema statistics"           → schema-stats agent
"How many classes are in D4D_Composition?" → d4d-schema-expert agent
"Validate this D4D YAML file"             → d4d-validator agent

# D4D evaluation
"Evaluate this D4D with rubric10"         → d4d-rubric10 agent
"Assess FAIR compliance with rubric20"    → d4d-rubric20 agent
```

## Available Commands

| Command | Method | Input | Output |
|---------|--------|-------|--------|
| `/d4d-agent` | Task tool agents | Preprocessed files | `claudecode/` |
| `/d4d-full-core` | Four phases: full generation, core generation, source/provenance audit, strict full/core reconciliation | Preprocessed files | `claudecode_agent/{version}/` + `claudecode_agent_core/{version}/` + reconciliation reports |
| `/d4d-assistant` | In-session synthesis | Preprocessed files | `claudecode_assistant/` |
| `/d4d-webfetch` | WebFetch + ARTL | Live URLs | `sheets_d4dassistant/` |
| `/d4d-add-mapping` | Schema-driven SSSOM editing | D4D class names | New rows in canonical SSSOM + SKOS files; PR-ready branch |

## Available Agents

### Schema and Validation Agents

| Agent | Purpose | Color |
|-------|---------|-------|
| `schema-stats` | Schema statistics and quality metrics | 🟢 Green |
| `d4d-schema-expert` | Schema structure and field definitions | 🟢 Green |
| `d4d-validator` | D4D YAML validation and error checking | 🔵 Cyan |
| `d4d-provenance-guard` | Prevent factual leakage from older generated D4Ds | Yellow |

### D4D Evaluation Agents

| Agent | Purpose | Color |
|-------|---------|-------|
| `d4d-rubric10` | Quality evaluation using 10-element rubric | 🟣 Purple |
| `d4d-rubric20` | FAIR compliance using 20-question rubric | 🟣 Purple |

## Choosing a Command

- **`/d4d-full-core`**: Best for production runs needing BOTH full D4D and D4D-core records. It generates full from input docs, derives core from docs + full, audits both against current sources, then enforces schema-derived shared-field identity and related-content consistency.
- **`/d4d-agent`**: Best for parallel processing of multiple projects (full D4D only)
- **`/d4d-assistant`**: Best for step-by-step control and debugging
- **`/d4d-webfetch`**: Best when you need fresh content from URLs
- **`/d4d-add-mapping`**: Best when adding a newly-introduced D4D class to the RO-Crate / FAIRSCAPE exchange layer (semantic + structural SSSOM rows + SKOS triples in one workflow)

## Choosing an Agent

- **`schema-stats`**: Get counts, breakdowns, quality metrics about the schema
- **`d4d-schema-expert`**: Understand schema modules, fields, and development
- **`d4d-validator`**: Validate D4D files and fix validation errors
- **`d4d-provenance-guard`**: Enforce current-run evidence boundaries and prohibit reuse of older generated YAML facts
- **`d4d-rubric10`**: Quality-based D4D evaluation (hierarchical rubric)
- **`d4d-rubric20`**: FAIR compliance assessment (detailed questions)
