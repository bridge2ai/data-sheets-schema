# D4D Slash Commands and Agents

Custom slash commands and conversational agents for D4D datasheet generation and schema analysis.

## Usage

### Slash Commands

Type the command name in Claude Code to expand the instructions:

```
/d4d-agent       # Agent approach with Task tool parallelization
/d4d-assistant   # Assistant approach following workflow methodology
/d4d-webfetch    # Live URL fetching with WebFetch + ARTL
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
| `/d4d-assistant` | In-session synthesis | Preprocessed files | `claudecode_assistant/` |
| `/d4d-webfetch` | WebFetch + ARTL | Live URLs | `sheets_d4dassistant/` |

## Available Agents

### Schema and Validation Agents

| Agent | Purpose | Color |
|-------|---------|-------|
| `schema-stats` | Schema statistics and quality metrics | 🟢 Green |
| `d4d-schema-expert` | Schema structure and field definitions | 🟢 Green |
| `d4d-validator` | D4D YAML validation and error checking | 🔵 Cyan |

### D4D Evaluation Agents

| Agent | Purpose | Color |
|-------|---------|-------|
| `d4d-rubric10` | Quality evaluation using 10-element rubric | 🟣 Purple |
| `d4d-rubric20` | FAIR compliance using 20-question rubric | 🟣 Purple |

## Choosing a Command

- **`/d4d-agent`**: Best for parallel processing of multiple projects
- **`/d4d-assistant`**: Best for step-by-step control and debugging
- **`/d4d-webfetch`**: Best when you need fresh content from URLs

## Choosing an Agent

- **`schema-stats`**: Get counts, breakdowns, quality metrics about the schema
- **`d4d-schema-expert`**: Understand schema modules, fields, and development
- **`d4d-validator`**: Validate D4D files and fix validation errors
- **`d4d-rubric10`**: Quality-based D4D evaluation (hierarchical rubric)
- **`d4d-rubric20`**: FAIR compliance assessment (detailed questions)
