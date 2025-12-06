# Claude Code Hooks

This directory contains hooks that run automatically during Claude Code tool operations.

## Overview

Hooks are Python scripts that execute before or after Claude Code tool operations. They provide validation, warnings, and enforcement of project conventions.

**Note**: All hooks in this project are configured to **warn only** - they do not block operations. This allows for flexibility while still providing helpful feedback.

## Hooks

### validate_d4d_yaml_hook.py

**Type**: PostToolUse
**Triggers**: Edit, Write operations on `*_d4d.yaml` files
**Purpose**: Validates D4D YAML data files against the LinkML schema

**What it does**:
1. Detects when a D4D YAML file is edited or created
2. Runs `linkml-validate` against the D4D schema
3. Reports validation errors as warnings

**Example output**:
```
D4D validation passed: data/d4d_concatenated/claudecode/VOICE_d4d.yaml
```

Or on error:
```
Warning: D4D validation warnings for data/d4d_concatenated/claudecode/VOICE_d4d.yaml:
- ERROR: 'invalid_value' is not a valid value for DataUsePermissionEnum
```

### protect_schema_hook.py

**Type**: PreToolUse
**Triggers**: Edit, Write operations on protected paths
**Purpose**: Warns about editing auto-generated files

**Protected paths**:
- `src/data_sheets_schema/datamodel/` - Auto-generated Python datamodel
- `src/data_sheets_schema/schema/data_sheets_schema_all.yaml` - Merged schema
- `project/jsonschema/` - Generated JSON Schema
- `project/owl/` - Generated OWL ontology
- `project/jsonld/` - Generated JSON-LD context
- `project/shacl/` - Generated SHACL shapes
- `project/graphql/` - Generated GraphQL schema
- `project/excel/` - Generated Excel templates

**Example output**:
```
Warning: Editing protected file: src/data_sheets_schema/datamodel/data_sheets_schema.py
         This is an auto-generated Python datamodel. Edit the schema YAML files instead and run 'make gen-project'.
```

### term_validator_hook.py

**Type**: PostToolUse
**Triggers**: Edit, Write operations on `D4D_*.yaml` schema files
**Purpose**: Validates ontology term references in schema files

**What it does**:
1. Detects when a D4D schema module is edited
2. Runs `linkml-term-validator validate-schema` on the full merged schema
3. Reports invalid ontology term references as warnings

**Example output**:
```
Ontology term validation passed for schema
```

Or on error:
```
Warning: Ontology term validation warnings:
- Term DUO:9999999 not found in Data Use Ontology
```

## Configuration

Hooks are configured in `.claude/settings.json`:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/validate_d4d_yaml_hook.py"
          },
          {
            "type": "command",
            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/term_validator_hook.py"
          }
        ]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/protect_schema_hook.py"
          }
        ]
      }
    ]
  }
}
```

## Hook Behavior

### Warn Only Mode

All hooks exit with code 0 regardless of validation results. This means:
- Warnings are displayed but do not block operations
- Claude Code can continue working even if validation fails
- Users see feedback but retain full control

To change to blocking mode, modify hooks to `sys.exit(2)` on validation failure.

### Environment Variables

Hooks use:
- `CLAUDE_PROJECT_DIR` - Project root directory (set automatically by Claude Code)

### Dependencies

Hooks require:
- Python 3.x
- Poetry (for running LinkML tools)
- LinkML packages:
  - `linkml` (for linkml-validate)
  - `linkml-term-validator` (for ontology term validation)

## Testing Hooks

Run hooks manually to test:

```bash
# Test D4D YAML validation
echo '{"tool_name": "Edit", "tool_input": {"file_path": "data/d4d_concatenated/claudecode/VOICE_d4d.yaml"}}' | \
  CLAUDE_PROJECT_DIR=$PWD python .claude/hooks/validate_d4d_yaml_hook.py

# Test protected file warning
echo '{"tool_name": "Write", "tool_input": {"file_path": "src/data_sheets_schema/datamodel/test.py"}}' | \
  CLAUDE_PROJECT_DIR=$PWD python .claude/hooks/protect_schema_hook.py

# Test term validation
echo '{"tool_name": "Edit", "tool_input": {"file_path": "src/data_sheets_schema/schema/D4D_Composition.yaml"}}' | \
  CLAUDE_PROJECT_DIR=$PWD python .claude/hooks/term_validator_hook.py
```

## Adding New Hooks

1. Create a Python script in `.claude/hooks/`
2. Read JSON input from stdin with tool information
3. Process and validate as needed
4. Print output messages (stdout for info, stderr for warnings)
5. Exit with code 0 (warn only) or 2 (block)
6. Add configuration to `.claude/settings.json`

### Hook Input Format

```json
{
  "tool_name": "Edit",
  "tool_input": {
    "file_path": "/path/to/file",
    "old_string": "...",
    "new_string": "..."
  }
}
```

### Exit Codes

- `0` - Success / Continue (warn only mode)
- `2` - Block operation (strict mode)
