# Claude Code D4D Generation Prompts

This directory contains instruction files for D4D datasheet generation using Claude Code with deterministic settings.

## Slash Commands (Moved)

**Slash commands are in `.claude/commands/`** (standard Claude Code location):

```
.claude/commands/
├── README.md
├── d4d-agent.md       # /d4d-agent - Task tool agents
├── d4d-assistant.md   # /d4d-assistant - In-session synthesis
└── d4d-webfetch.md    # /d4d-webfetch - WebFetch + ARTL
```

Usage: Type `/d4d-agent`, `/d4d-assistant`, or `/d4d-webfetch` in Claude Code.

## Three Generation Approaches

| Approach | Method | Input | Workflow | Output Location |
|----------|--------|-------|----------|-----------------|
| **Agent Deterministic** | Task tool with agents | Preprocessed files | Custom | `claudecode/` |
| **Assistant Deterministic** | In-session synthesis | Preprocessed files | `.github/workflows/` | `claudecode_assistant/` |
| **GitHub Actions Workflow** | WebFetch + ARTL | Live URL fetch | `.github/workflows/` | `sheets_d4dassistant/` |

Both **Assistant Deterministic** and **GitHub Actions Workflow** follow the methodology defined in `.github/workflows/d4d_assistant_create.md`. The key difference is input source: preprocessed files vs. live URL fetching.

## Instruction Files (This Directory)

These files are used by Python scripts and provide detailed workflow instructions:

- **`d4d_deterministic_create.md`** - Instructions for creating new D4D datasheets
- **`d4d_deterministic_edit.md`** - Instructions for editing existing D4D datasheets
- **`d4d_generate_from_sources.md`** - Overview of source document generation

## Deterministic Settings

All approaches use these settings for reproducibility:

- **Temperature**: 0.0 (maximum determinism)
- **Schema**: `src/data_sheets_schema/schema/data_sheets_schema_all.yaml`
- **Validation**: Required before completion
- **Field handling**: Prefer `null` or omission for unknown values

## Input Sources

### Preprocessed Files (Agent & Assistant approaches)

```
data/preprocessed/concatenated/sources/
├── AI_READI_sources_concatenated.txt
├── CM4AI_sources_concatenated.txt
├── VOICE_sources_concatenated.txt
└── CHORUS_sources_concatenated.txt

data/preprocessed/individual/{PROJECT}/
└── {source_file}.txt
```

### Live URLs (GitHub Actions approach)

| Project | Primary URLs |
|---------|--------------|
| AI_READI | https://docs.aireadi.org, https://fairhub.io/datasets/2 |
| CM4AI | https://cm4ai.org, https://doi.org/10.18130/V3/B35XWX |
| VOICE | https://docs.b2ai-voice.org, https://doi.org/10.13026/249v-w155 |
| CHORUS | https://chorus4ai.org |

## Output Locations Summary

```
data/
├── d4d_concatenated/
│   ├── claudecode/                    # Agent Deterministic
│   ├── claudecode_assistant/          # Assistant Deterministic
│   ├── gpt5/                          # GPT-5 (alternative LLM)
│   └── curated/                       # Manual curation
├── d4d_individual/
│   ├── claudecode/{PROJECT}/          # Agent Deterministic
│   └── claudecode_assistant/{PROJECT}/ # Assistant Deterministic
└── sheets_d4dassistant/               # GitHub Actions Workflow
```

## Validation

All approaches require validation before completion:

```bash
poetry run linkml-validate \
  -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset <file>
```

## Related Documentation

- **Slash Commands**: `.claude/commands/`
- **Schema**: `src/data_sheets_schema/schema/data_sheets_schema_all.yaml`
- **Validation**: `make validate-d4d FILE=<file>`
- **HTML Preview**: `src/html/human_readable_renderer.py`
- **Determinism Notes**: `notes/DETERMINISM.md`
- **GitHub Actions Workflow**: `.github/workflows/d4d_assistant_create.md`
