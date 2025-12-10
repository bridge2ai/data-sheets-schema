# D4D Agent and GitHub Workflow Unification Plan

**Status**: Planning
**Created**: 2025-12-06
**Goal**: Unify behavior and instructions between local d4d-agent and GitHub Actions D4D Assistant

## Problem Statement

Currently, we maintain **separate instruction files** for D4D generation that should behave identically:

### Current Instruction Files

| File | Purpose | Environment | Tools |
|------|---------|-------------|-------|
| `.claude/commands/d4d-agent.md` | Local slash command | Development | Read, Write, Bash, Grep, Glob, WebFetch |
| `.github/workflows/d4d_assistant_create.md` | Create new D4Ds | GitHub Actions | MCP (GitHub, ARTL, WebSearch, WebFetch) |
| `.github/workflows/d4d_assistant_edit.md` | Edit existing D4Ds | GitHub Actions | MCP (GitHub, ARTL, WebSearch, WebFetch) |

### Issues with Current State

1. **Duplication**: Core D4D extraction methodology duplicated across files
2. **Drift Risk**: Changes to one file may not propagate to others
3. **Maintenance Burden**: Updates require editing multiple files
4. **Inconsistency**: Subtle differences in approach may emerge over time
5. **Testing**: Harder to ensure identical behavior across environments

## Similarities (Should Be Identical)

Both environments should share:

- **D4D Generation Logic**: Document reading, schema interpretation, field extraction
- **Conflict Resolution**: Prefer detailed over generic, merge complementary info
- **Validation Requirements**: Schema validation, term validation
- **Output Format**: YAML structure following D4D schema
- **Quality Standards**: Comprehensive coverage, accurate metadata extraction
- **Error Handling**: Graceful failures, informative error messages

## Differences (Environment-Specific)

### File Output
- **GitHub Actions**: Create pull requests with new/updated YAML files
- **Local Agent**: Write files directly to `data/d4d_*/` directories

### Validation
- **GitHub Actions**: Inline validation checks (may use MCP tools)
- **Local Agent**: Poetry commands (`poetry run linkml-validate`, `poetry run linkml-term-validator`)

### User Communication
- **GitHub Actions**: Comment on GitHub issues and pull requests
- **Local Agent**: Return final report through AgentOutputTool

### Tool Access
- **GitHub Actions**: MCP servers (GitHub, ARTL, WebSearch, WebFetch)
- **Local Agent**: Standard tools (Read, Write, Bash, Grep, Glob, WebFetch)

## Proposed Solutions

### Option 1: Single Instruction File with Conditional Logic (RECOMMENDED)

**Structure:**
```
.github/workflows/d4d_unified_instructions.md
```

**Contents:**
```markdown
# D4D Generation Unified Instructions

## Core D4D Methodology (All Environments)
- Document reading and parsing
- Schema interpretation
- Field extraction logic
- Conflict resolution rules
- Validation requirements

## Environment-Specific Adaptations

### For GitHub Actions Environment
- Use MCP tools for file operations
- Create pull requests for outputs
- Comment on issues with results
- Use GitHub API for validation

### For Local Agent Environment
- Use Write tool for file operations
- Save directly to disk
- Return results via AgentOutputTool
- Use poetry commands for validation
```

**Updates Required:**
- `.claude/commands/d4d-agent.md` → Include unified instructions + "use Local Agent Environment section"
- `.github/workflows/d4d_assistant_create.md` → Include unified instructions + "use GitHub Actions Environment section"
- `.github/workflows/d4d_assistant_edit.md` → Include unified instructions + "use GitHub Actions Environment section"

**Advantages:**
- ✅ Single source of truth for core logic
- ✅ Easy to maintain and update
- ✅ Clear separation of shared vs. environment-specific
- ✅ Simpler file structure

**Disadvantages:**
- ⚠️ Slightly larger instruction file
- ⚠️ Need to read conditional sections carefully

### Option 2: Shared Core + Environment Adapters

**Structure:**
```
.github/workflows/
  core_d4d_methodology.md          # Shared D4D extraction logic
  adapter_github_actions.md         # GitHub-specific: MCP tools, PRs, issues
  adapter_local_agent.md            # Local-specific: file writes, poetry
  d4d_assistant_create.md           # Import core + github adapter
  d4d_assistant_edit.md             # Import core + github adapter

.claude/commands/
  d4d-agent.md                      # Import core + local adapter
```

**Contents Example:**

`core_d4d_methodology.md`:
```markdown
# Core D4D Methodology

## Document Reading
[Shared logic for all environments]

## Schema Interpretation
[Shared logic for all environments]

## Field Extraction
[Shared logic for all environments]

## Conflict Resolution
[Shared logic for all environments]

## Validation
[Shared validation requirements]
```

`adapter_github_actions.md`:
```markdown
# GitHub Actions Adapter

## File Operations
Use MCP GitHub tools to create files in PRs

## Validation
Use inline validation checks

## Communication
Comment on issues and PRs
```

`adapter_local_agent.md`:
```markdown
# Local Agent Adapter

## File Operations
Use Write tool to save files directly

## Validation
Use poetry run linkml-validate

## Communication
Return results via AgentOutputTool
```

**Advantages:**
- ✅ Maximum modularity
- ✅ Clean separation of concerns
- ✅ Easy to add new environments

**Disadvantages:**
- ⚠️ More complex file structure
- ⚠️ Need to manage imports/references
- ⚠️ Slightly harder to navigate

## Recommendation

**Use Option 1: Single Instruction File with Conditional Logic**

Rationale:
1. **Simpler**: One file to maintain vs. multiple imports
2. **Clearer**: All logic visible in one place
3. **Easier Navigation**: Agent/human can see full context
4. **Proven Pattern**: Similar to how CLAUDE.md handles different scenarios

## Implementation Plan

### Phase 1: Create Unified Core

1. **Create** `.github/workflows/d4d_unified_instructions.md`
   - Extract common D4D generation logic from existing files
   - Structure with clear sections for shared vs. environment-specific

2. **Document Core Methodology**:
   - Document reading and parsing approach
   - Schema field mapping
   - Conflict resolution rules (prefer detailed, merge complementary)
   - Validation requirements (schema + term validation)

### Phase 2: Update Existing Files

3. **Update** `.claude/commands/d4d-agent.md`:
   - Reference unified instructions
   - Add: "Follow the 'Local Agent Environment' sections"
   - Keep slash command-specific metadata (description, usage)

4. **Update** `.github/workflows/d4d_assistant_create.md`:
   - Reference unified instructions
   - Add: "Follow the 'GitHub Actions Environment' sections"
   - Keep GitHub Actions-specific metadata (triggers, scope)

5. **Update** `.github/workflows/d4d_assistant_edit.md`:
   - Reference unified instructions
   - Add: "Follow the 'GitHub Actions Environment' sections"
   - Keep edit-specific workflow details

### Phase 3: Testing and Validation

6. **Test Local Agent**:
   - Run `/d4d-agent` slash command
   - Verify behavior matches previous implementation
   - Check file outputs and validation

7. **Test GitHub Actions** (if possible):
   - Trigger D4D Assistant via issue mention
   - Verify PR creation and validation
   - Check issue/PR comments

8. **Compare Outputs**:
   - Same input documents should produce functionally identical D4D YAMLs
   - Only environment-specific differences (file location, reporting)

## Key Unification Points

### Identical Behavior Requirements

| Aspect | Unified Behavior |
|--------|------------------|
| Document parsing | Same preprocessing, text extraction |
| Schema interpretation | Same field mapping, data types |
| Field extraction | Same completeness criteria |
| Conflict resolution | Same rules (detailed > generic) |
| Validation | Same schema validation requirements |
| Error handling | Same graceful failures, informative messages |

### Environment-Specific Adaptations

| Aspect | GitHub Actions | Local Agent |
|--------|----------------|-------------|
| File output | Create PR with new files | Write to `data/d4d_*/` |
| Validation | Inline checks | `poetry run linkml-validate` |
| Communication | Issue/PR comments | AgentOutputTool report |
| Tool access | MCP (GitHub, ARTL, WebSearch, WebFetch) | Read, Write, Bash, Grep, Glob, WebFetch |

## Success Criteria

- ✅ Single source of truth for D4D generation methodology
- ✅ No duplication of core logic across files
- ✅ Both environments produce functionally identical D4D YAMLs
- ✅ Easy to update core logic in one place
- ✅ Clear documentation of environment-specific adaptations
- ✅ Existing workflows continue to function correctly

## Future Considerations

### Potential Additional Environments

- **Web UI**: Browser-based D4D generation interface
- **CLI Tool**: Direct command-line D4D generation
- **API Service**: HTTP API endpoint for D4D generation

All would follow the same unified core methodology with their own adapters.

### Maintenance Strategy

- **Core Updates**: Changes to D4D methodology update unified instructions only
- **Environment Updates**: Changes to tools/APIs update environment-specific sections
- **Version Control**: Track changes to unified instructions carefully
- **Testing**: Automated tests to ensure environment parity

## Related Files

- `.claude/commands/d4d-agent.md` - Current local slash command
- `.github/workflows/d4d_assistant_create.md` - Current GitHub create workflow
- `.github/workflows/d4d_assistant_edit.md` - Current GitHub edit workflow
- `src/download/prompts/claudecode/d4d_generate_from_sources.md` - D4D generation prompt
- `CLAUDE.md` - Project instructions (example of unified documentation)

## References

- Original question: "would it be possible to have the d4d-agent behave exactly as the github workflow?"
- Current state analysis: Agent and GitHub Action already very similar in approach
- Key insight: Both are autonomous agents with different tool access but same goal
