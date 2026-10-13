# D4D Assistant Setup

This directory contains instruction files for the D4D Assistant, which helps create and edit Datasheets for Datasets (D4D) via GitHub Actions.

## Instruction Files

- **`d4d_assistant_create.md`** - Instructions for creating new D4D datasheets
- **`d4d_assistant_edit.md`** - Instructions for editing existing D4D datasheets

These files guide the D4D Assistant through workflows for metadata extraction, YAML generation, validation, and pull request creation.

## MCP Server Configuration

The D4D Assistant requires Model Context Protocol (MCP) servers to be configured. These are already set up in the repository:

### Configured MCP Servers

**`.mcp.json`** (at repository root):
```json
{
  "mcpServers": {
    "github": {
      "type": "http",
      "url": "https://api.githubcopilot.com/mcp/"
    },
    "artl": {
      "command": "uvx",
      "args": ["artl-mcp"]
    }
  }
}
```

**`.claude/settings.json`**:
- Enables project MCP servers with `enableAllProjectMcpServers: true`
- Allows MCP tool usage with permissions for `mcp__github__*` and `mcp__artl__*`
- Includes permissions for `WebSearch` and `WebFetch` tools

### What Each MCP Server Does

1. **GitHub MCP** (`mcp__github__*`)
   - Create branches, commits, and pull requests
   - Comment on issues and PRs
   - Read repository files and structure
   - Manage labels and milestones

2. **ARTL MCP** (`mcp__artl__*`)
   - Search and retrieve academic literature about datasets
   - Find papers by DOI, PMID, or PMCID
   - Extract metadata from academic publications
   - Useful for finding dataset documentation in scholarly articles

3. **WebSearch** (built-in)
   - Search the web for dataset documentation
   - Find official dataset pages and documentation
   - Discover related resources

4. **WebFetch** (built-in)
   - Fetch content from URLs
   - Download and extract text from PDFs
   - Access API documentation

## First-Time Setup

When running the D4D Assistant for the first time:

1. **Approve Project MCP Servers**
   - Claude Code will prompt to approve MCP servers from `.mcp.json`
   - Accept the project MCP servers (GitHub and ARTL)

2. **Authenticate GitHub MCP (if needed)**
   - If GitHub MCP requires OAuth, use `/mcp` command
   - Follow browser prompts to authenticate
   - Authentication is stored securely and refreshed automatically

3. **Install ARTL MCP**
   - The ARTL MCP server uses `uvx artl-mcp`
   - Ensure `uvx` (uv tool runner) is available on your system
   - Install with: `pip install uv` or follow [uv installation guide](https://docs.astral.sh/uv/)

## Troubleshooting

### MCP Server Not Starting

If you see errors like "Connection closed" or "MCP server failed to start":

1. **Check uvx availability**:
   ```bash
   which uvx
   uvx --version
   ```

2. **Test ARTL MCP manually**:
   ```bash
   uvx artl-mcp
   ```

3. **Reset MCP configuration**:
   ```bash
   claude mcp reset-project-choices
   ```

### Authentication Issues

If GitHub MCP fails to authenticate:

1. Use `/mcp` command in Claude Code
2. Select "Authenticate" for GitHub
3. Complete OAuth flow in browser
4. Use "Clear authentication" if you need to re-authenticate

### Permission Denied

If you see permission errors:

1. Check `.claude/settings.json` has MCP permissions enabled
2. Ensure `enableAllProjectMcpServers: true` is set
3. Restart Claude Code to apply configuration changes

## Manual MCP Management

You can also manage MCP servers via CLI:

```bash
# List configured servers
claude mcp list

# Get details for a specific server
claude mcp get github

# Add a new server (example)
claude mcp add --transport http notion https://mcp.notion.com/mcp

# Remove a server
claude mcp remove server-name
```

For more information, see the [Claude Code MCP documentation](https://code.claude.com/docs/en/mcp).

## D4D Assistant Capabilities

With these MCP servers configured, the D4D Assistant can:

- ✅ Create new D4D datasheets from URLs and documentation
- ✅ Edit existing D4D YAML files based on user requests
- ✅ Search academic literature for dataset papers
- ✅ Fetch content from web pages and PDFs
- ✅ Create pull requests with changes
- ✅ Comment on GitHub issues with status updates
- ✅ Validate YAML against the D4D schema
- ✅ Generate HTML previews of datasheets

## Security Note

MCP servers execute code and access external services. The configured servers are:

- **GitHub MCP**: Official Anthropic-maintained server for GitHub operations
- **ARTL MCP**: Academic literature search tool (`uvx artl-mcp`)
- **WebSearch/WebFetch**: Built-in Claude Code tools

These are trusted sources, but always review MCP server configurations before approving them.
