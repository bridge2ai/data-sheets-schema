# D4D Slash Commands

Custom slash commands for D4D datasheet generation.

## Usage

Type the command name in Claude Code to expand the instructions:

```
/d4d-agent       # Agent approach with Task tool parallelization
/d4d-assistant   # Assistant approach following workflow methodology
/d4d-webfetch    # Live URL fetching with WebFetch + ARTL
```

## Available Commands

| Command | Method | Input | Output |
|---------|--------|-------|--------|
| `/d4d-agent` | Task tool agents | Preprocessed files | `claudecode/` |
| `/d4d-assistant` | In-session synthesis | Preprocessed files | `claudecode_assistant/` |
| `/d4d-webfetch` | WebFetch + ARTL | Live URLs | `sheets_d4dassistant/` |

## Choosing a Command

- **`/d4d-agent`**: Best for parallel processing of multiple projects
- **`/d4d-assistant`**: Best for step-by-step control and debugging
- **`/d4d-webfetch`**: Best when you need fresh content from URLs
