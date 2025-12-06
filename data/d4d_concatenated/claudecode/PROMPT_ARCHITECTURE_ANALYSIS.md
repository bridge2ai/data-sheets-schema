# D4D Prompt Architecture Analysis: Aurelian vs Claude Deterministic

**Date:** December 3, 2025
**Analysis:** Architectural Compatibility for Interchangeable Prompts
**Objective:** Enable prompt sharing between Aurelian D4D agent (GPT-5) and Claude Code deterministic approach

## Executive Summary

This analysis reveals that **prompts CAN be made fully interchangeable** between the two D4D metadata extraction approaches, despite significant architectural differences. The key finding is that while the execution frameworks differ, the **prompt content is already compatible** and only requires infrastructure to support external file loading and unified schema injection.

**Key Outcomes:**
- ✅ Prompt content is compatible across both approaches
- ✅ Schema injection can be unified with constructor-based pattern
- ✅ Both approaches can use shared external prompt files
- ✅ **Local schema will be the default** for reproducibility
- ⚠️ Tool-based execution (Aurelian) vs content-embedded execution (Claude) remain different
- ⚠️ Decorator patterns specific to pydantic-ai but can be abstracted

---

## 1. Architectural Overview

### 1.1 Aurelian D4D Agent (pydantic-ai + GPT-5)

**File:** `aurelian/src/aurelian/agents/d4d/d4d_agent.py`

**Architecture Pattern:**
- **Decorator-based agent** with runtime system prompt injection
- **Tool-enabled execution** - agent fetches content via tool calls
- **GitHub schema source** - fetches schema from remote URL at runtime
- **No deterministic settings** - uses model defaults
- **Inline prompt** - system prompt hardcoded in Python file

**Execution Flow:**
```
1. User provides URLs
2. Agent initialization with template prompt (has {schema} placeholder)
3. @d4d_agent.system_prompt decorator fetches schema from GitHub
4. Schema injected into {schema} placeholder at runtime
5. User runs agent with URLs
6. Agent calls @d4d_agent.tool extract_metadata
7. Tool calls process_website_or_pdf for each URL
8. Tool returns concatenated content to agent
9. Agent processes content + schema → generates YAML
```

**Key Features:**
```python
# Lines 13-41 in d4d_agent.py
d4d_agent = Agent(
    model="openai:gpt-5",
    deps_type=D4DConfig,
    system_prompt="""...""",  # Inline with {schema} placeholder
    defer_model_check=True,
)

@d4d_agent.system_prompt
async def add_schema(ctx: RunContext[D4DConfig]) -> str:
    schema = await get_full_schema(ctx)  # Fetches from GitHub
    return schema

@d4d_agent.tool
async def extract_metadata(ctx, urls: List[str]) -> str:
    content = ""
    for url in urls:
        content += await process_website_or_pdf(ctx, url)
    return f"Content: {content}\n\nExtract metadata..."
```

---

### 1.2 Claude Deterministic Approach (pydantic-ai + Claude Sonnet 4.5)

**File:** `src/download/process_concatenated_d4d_claude.py`

**Architecture Pattern:**
- **Constructor-based agent** with pre-loaded prompts
- **Content-embedded execution** - no tool calls, content in user message
- **Local schema file** - reads from version-controlled schema file
- **Deterministic settings** - temperature=0.0, max_tokens=16000
- **External prompt files** - loaded from `.txt` files with version tracking

**Execution Flow:**
```
1. Script initialization loads prompts from external files
2. Script reads local schema file
3. System prompt formatted with schema (replaces {schema})
4. Agent initialized with complete system prompt
5. Script reads concatenated document from disk
6. User prompt formatted with content
7. Single agent.run() call with user_prompt
8. Agent processes system_prompt + user_prompt → generates YAML
9. Script saves output + metadata YAML
```

**Key Features:**
```python
# Lines 114-154 in process_concatenated_d4d_claude.py
class DeterministicConcatenatedD4DProcessor:
    def __init__(self, model="anthropic:claude-sonnet-4-5-20250929"):
        # Load prompts from external files
        self.system_prompt_template, self.system_prompt_hash = load_prompt_file(
            self.prompts_dir, "d4d_concatenated_system_prompt.txt"
        )

        # Load LOCAL schema file
        self.schema_content = self.schema_path.read_text(encoding='utf-8')
        self.schema_hash = calculate_file_hash(self.schema_path)

        # Format system prompt BEFORE agent creation
        self.system_prompt = self.system_prompt_template.format(
            schema=self.schema_content
        )

        # Initialize agent with complete prompt
        self.d4d_agent = Agent(
            model=self.model,
            deps_type=D4DConfig,
            system_prompt=self.system_prompt,  # No {schema} placeholder
            model_settings={
                "temperature": 0.0,  # Deterministic
                "max_tokens": 16000,
            },
            defer_model_check=True,
        )
```

---

## 2. Compatibility Analysis

### 2.1 COMPATIBLE: Prompt Content

**Finding:** The actual prompt text is nearly identical in both approaches.

**Aurelian system prompt** (lines 16-39 in `d4d_agent.py`):
```
You are an expert data scientist specializing in extracting metadata from datasets.
You will be provided with a schema that describes the metadata structure for datasets,
and one or more URLs pointing to webpages or PDFs that describe a dataset.
Your task is to extract all relevant metadata from the provided content and output it in
YAML format, strictly following the provided schema. Generate only the YAML document.
Do not respond with any additional commentary. Try to ensure that required fields are
present, but only populate items that you are sure about. Ensure that output is valid YAML.

Below is the complete datasheets for datasets schema:

{schema}

For each URL to a webpage or PDF describing a dataset, you will fetch the
content, extract all the relevant metadata, and output a YAML document...
```

**Claude system prompt** (`src/download/prompts/d4d_concatenated_system_prompt.txt`):
```
You are an expert data scientist specializing in extracting metadata from datasets following the "Datasheets for Datasets" schema.

Below is the complete datasheets for datasets schema:

{schema}

Your task is to analyze the provided concatenated document which contains multiple related dataset documentation files that have been merged together. Extract all relevant dataset metadata to generate a complete YAML document that strictly follows the D4D schema above.

Focus on extracting and synthesizing:
- Dataset identity (id, name, title, description)
- Creators and contributors with affiliations
- Purpose and intended uses
- Data composition and structure
- Collection methodology and timeframe
- Preprocessing and cleaning steps
- Distribution information and formats
- Licensing and terms of use
- Maintenance information
- Access requirements and restrictions
- Funding and grants
- Ethics and human subjects considerations
```

**Differences:**
- **Claude prompt is MORE DETAILED** - includes 13-item checklist
- **Claude prompt mentions "concatenated document"** - Aurelian says "URLs"
- **Both use {schema} placeholder** in the same location
- **Core instructions identical** - "strictly follow schema", "generate only YAML"

**Compatibility Strategy:**
1. Create unified prompt that works for BOTH URL mode and content mode
2. Keep detailed extraction checklist from Claude (improves quality)
3. Remove mode-specific language ("URLs" or "concatenated")
4. Use template variables for mode-specific instructions

---

### 2.2 COMPATIBLE: Schema Placeholder Pattern

**Both approaches use `{schema}` placeholder:**

**Aurelian:**
```python
# Template with placeholder
system_prompt = "...{schema}..."

# Filled by decorator at runtime
@d4d_agent.system_prompt
async def add_schema(ctx):
    return schema_content  # Replaces {schema}
```

**Claude:**
```python
# Template with placeholder
system_prompt_template = "...{schema}..."

# Filled by format() before agent creation
system_prompt = system_prompt_template.format(schema=schema_content)
```

**Compatibility Strategy:**
- Use Claude's constructor-based approach (simpler, more reproducible)
- Support both GitHub and local schema sources
- **Default to local** schema for reproducibility
- Cache schema to avoid repeated I/O

---

### 2.3 INCOMPATIBLE: System Prompt Injection Mechanism

**Aurelian uses @agent.system_prompt decorator:**
```python
@d4d_agent.system_prompt
async def add_schema(ctx: RunContext[D4DConfig]) -> str:
    schema = await get_full_schema(ctx)
    return schema
```

**Claude uses constructor with pre-formatted prompt:**
```python
system_prompt = template.format(schema=schema)
agent = Agent(system_prompt=system_prompt)
```

**Why incompatible:**
- Decorator pattern is pydantic-ai specific
- RunContext is framework feature
- Decorator runs dynamically at each agent execution
- Constructor approach formats once at initialization

**Workaround:**
```python
# Both approaches can use constructor-based pattern
schema = load_schema(source="local")  # or "github"
system_prompt = template.format(schema=schema)
agent = Agent(system_prompt=system_prompt)
```

**Recommendation:** Use constructor-based (Claude style) for:
- ✅ Reproducibility - same schema every run
- ✅ Performance - schema loaded once
- ✅ Simplicity - no decorator magic
- ✅ Provenance - schema hash tracked

---

### 2.4 INCOMPATIBLE: Content Delivery (Tools vs Embedded)

**Aurelian: Tool-based content retrieval**
```python
# Agent expects URLs
@d4d_agent.tool
async def extract_metadata(ctx, urls: List[str]) -> str:
    content = ""
    for url in urls:
        content += await process_website_or_pdf(ctx, url)
    return prompt_with_content
```

**Claude: Pre-loaded content in user message**
```python
# Content loaded before agent.run()
content = input_file.read_text()
user_prompt = template.format(content=content)
result = await agent.run(user_prompt)
```

**Why incompatible:**
- Different execution paradigms
- Aurelian: Agent fetches content (tool calls)
- Claude: Script fetches content (no tools)

**Workaround - Support Both Modes:**
```python
def run_d4d_extraction(agent, input_source, mode="auto"):
    if mode == "auto":
        mode = "url" if input_source.startswith("http") else "content"

    if mode == "url":
        # Aurelian pattern
        result = await agent.run(f"Extract from: {input_source}")
    else:
        # Claude pattern
        content = load_content(input_source)
        user_prompt = template.format(content=content)
        result = await agent.run(user_prompt)

    return result
```

**Recommendation:**
- Support both modes but **default to content mode** for reproducibility
- Content mode ensures deterministic inputs
- URL mode useful for interactive use cases

---

### 2.5 COMPATIBLE: External Prompt Files

**Aurelian currently:** Inline prompts in Python
**Claude currently:** External `.txt` files with YAML headers

**Both CAN use external files:**
```python
# Works for both pydantic-ai Agent() constructors
prompt_file = Path("prompts/d4d_system_prompt.txt")
system_prompt_template = prompt_file.read_text()
system_prompt = system_prompt_template.format(schema=schema)

agent = Agent(
    model=...,
    system_prompt=system_prompt
)
```

**Recommendation:**
- ✅ All prompts in external files
- ✅ Version-controlled in git
- ✅ YAML frontmatter for metadata
- ✅ SHA-256 hashing for provenance

---

### 2.6 COMPATIBLE: Deterministic Settings

**Aurelian currently:** No temperature specified (uses defaults)
**Claude currently:** temperature=0.0, max_tokens=16000

**Both CAN use model_settings:**
```python
Agent(
    model=...,
    system_prompt=...,
    model_settings={
        "temperature": 0.0,
        "max_tokens": 16000
    }
)
```

**Recommendation:**
- **Default to temperature=0.0** for reproducibility
- Make configurable via parameter
- Document expected behavior with different temperatures

---

### 2.7 INCOMPATIBLE: Schema Source (GitHub vs Local)

**Aurelian:** Fetches from GitHub every run
- URL: `https://raw.githubusercontent.com/bridge2ai/data-sheets-schema/main/...`
- Runtime retrieval
- Always latest version

**Claude:** Reads local file once
- Path: `src/data_sheets_schema/schema/data_sheets_schema_all.yaml`
- Initialization-time retrieval
- Version-controlled version

**Trade-offs:**

| Feature | GitHub | Local |
|---------|--------|-------|
| **Reproducibility** | ❌ Changes over time | ✅ Fixed to repo version |
| **Performance** | ❌ Network latency | ✅ Instant |
| **Latest features** | ✅ Always current | ❌ Requires git pull |
| **Offline use** | ❌ Requires network | ✅ Works offline |
| **Provenance** | ⚠️ URL + timestamp | ✅ Git commit hash |

**Workaround:**
```python
def load_schema(source="local", path=None):
    if source == "local":
        path = path or "src/data_sheets_schema/schema/data_sheets_schema_all.yaml"
        return Path(path).read_text()
    elif source == "github":
        url = "https://raw.githubusercontent.com/bridge2ai/..."
        return requests.get(url).text
    else:
        return Path(source).read_text()  # Custom path
```

**Recommendation:**
- **Default to local** for reproducibility (user preference)
- Make source configurable
- Cache GitHub schema for performance
- Track source in metadata

---

## 3. Model-Specific Considerations

### 3.1 GPT-5 vs Claude Sonnet 4.5

**Analysis Finding:** NO model-specific prompt differences detected.

**Evidence:**
- Claude prompt header says: `Model: Claude Sonnet 4.5 / GPT-5`
- Both models process same prompt format
- Both support temperature parameter
- Both support max_tokens parameter
- Both generate YAML output successfully

**Tested Configurations:**
- ✅ GPT-5 with Claude-style prompts (works)
- ✅ Claude with Aurelian-style prompts (works)
- ✅ Both with temperature=0.0 (works)

**Recommendation:** Use same prompts for both models.

---

## 4. Unified Prompt Architecture Design

### 4.1 Shared Prompt Files Structure

```
src/download/prompts/
├── shared/                                    # NEW: Unified prompts
│   ├── d4d_system_prompt.txt                 # Unified system prompt
│   ├── d4d_user_prompt_content_mode.txt      # For pre-loaded content
│   ├── d4d_user_prompt_url_mode.txt          # For URL-based workflow
│   └── prompt_versions.yaml                   # Version tracking
├── aurelian/                                  # Legacy Aurelian prompts
│   └── d4d_system_prompt.txt                 # Original Aurelian
├── claude/                                    # Legacy Claude prompts
│   ├── d4d_concatenated_system_prompt.txt    # Original
│   └── d4d_concatenated_user_prompt.txt
└── determinism_settings.yaml                  # Configuration
```

### 4.2 Unified System Prompt (Best of Both)

**Combines:**
- Aurelian's clarity and simplicity
- Claude's detailed extraction checklist
- Mode-agnostic language
- {schema} placeholder for injection

**Template:**
```
---
Prompt Name: D4D Unified System Prompt
Version: 2.0.0
Last Updated: 2025-12-03
Model: Claude Sonnet 4.5 / GPT-5 / Claude Opus
Schema: Datasheets for Datasets (D4D) LinkML Schema
Mode: Universal (supports URL mode and content mode)
---

You are an expert data scientist specializing in extracting metadata from datasets following the "Datasheets for Datasets" (D4D) schema.

Below is the complete datasheets for datasets schema:

{schema}

Your task is to extract all relevant dataset metadata from the provided documentation and generate a complete YAML document that strictly follows the D4D schema above.

Focus on extracting and synthesizing these key elements:
- Dataset identity: id, name, title, and comprehensive description
- Creators and contributors: names, affiliations, roles (CRediT taxonomy), and contact information
- Purpose and intended uses: primary objectives and recommended applications
- Tasks and gaps addressed: specific research questions and problems solved
- Data composition: types of instances, relationships, and structural details
- Collection methodology: mechanisms, timeframes, and data sources
- Collection team: who collected the data and their organizational affiliations
- Preprocessing and cleaning: steps taken, tools used, and raw data availability
- Distribution information: formats, licenses, and access methods
- Licensing and terms of use: copyright, restrictions, and compliance requirements
- Maintenance information: update schedule, versioning, and retention policies
- Access requirements: authentication, approval processes, and barriers
- Funding and grants: sponsoring organizations and grant identifiers
- Ethics and human subjects: IRB approval, consent procedures, privacy protections

When multiple documentation sources describe the same dataset:
1. Merge complementary information from all sources
2. Prefer more detailed and specific information over generic descriptions
3. Keep the most comprehensive descriptions
4. Combine all relevant metadata sections without duplication

Important guidelines:
- Generate ONLY valid YAML output without any additional commentary
- Ensure all required fields are populated where information is available in the source
- If specific information is not available in the source documents, omit those fields rather than making assumptions
- Use null or omit fields for missing information rather than placeholder text
- Ensure output is valid YAML syntax
- Follow the schema exactly - use correct field names and data types
```

### 4.3 User Prompt Templates

**Content Mode** (`d4d_user_prompt_content_mode.txt`):
```
---
Prompt Name: D4D User Prompt - Content Mode
Version: 2.0.0
Mode: Content Mode (pre-loaded documentation)
---

Please analyze the following documentation and generate a comprehensive D4D YAML document.

Project: {project_name}
Source: {input_filename}

Documentation to analyze:
{content}

Generate a single, comprehensive D4D YAML document that extracts all available information from the documentation above. Follow the D4D schema exactly and create the most complete dataset documentation possible.
```

**URL Mode** (`d4d_user_prompt_url_mode.txt`):
```
---
Prompt Name: D4D User Prompt - URL Mode
Version: 2.0.0
Mode: URL Mode (agent fetches content)
---

Please extract D4D metadata from the following dataset documentation source(s).

Project: {project_name}
Documentation URL(s): {urls}

Fetch the content from the provided URL(s), analyze all documentation, and generate a single comprehensive D4D YAML document that follows the schema exactly.
```

---

## 5. Implementation: D4DPromptLoader

### 5.1 Unified Prompt Loading Infrastructure

**File:** `src/download/prompt_loader.py`

**Features:**
- Load prompts from external files
- Support multiple prompt sets (shared, aurelian, claude)
- Schema injection with configurable source (local/github)
- Schema caching for performance
- SHA-256 hashing for provenance
- Metadata generation for reproducibility

**API Design:**
```python
class D4DPromptLoader:
    def __init__(
        self,
        prompts_dir: Path,
        prompt_set: str = "shared",      # "shared", "aurelian", "claude"
        schema_source: str = "local",     # "local", "github", or path
        schema_path: Optional[Path] = None
    ):
        """Initialize prompt loader with configuration."""

    def load_system_prompt(self) -> tuple[str, dict]:
        """
        Load system prompt with schema injected.
        Returns: (formatted_prompt, metadata)
        """

    def load_user_prompt(self, mode: str = "content", **kwargs) -> str:
        """
        Load and format user prompt.
        mode: "content" or "url"
        kwargs: Template variables (project_name, content, urls, etc.)
        """

    def get_schema(self) -> str:
        """Get schema content (cached)."""

    def get_metadata(self) -> dict:
        """Get complete provenance metadata."""
```

**Usage Example:**
```python
# Initialize loader
loader = D4DPromptLoader(
    prompts_dir=Path("src/download/prompts"),
    prompt_set="shared",
    schema_source="local"  # DEFAULT per user requirement
)

# Load system prompt (with schema injected)
system_prompt, metadata = loader.load_system_prompt()

# Create agent
agent = Agent(
    model="anthropic:claude-sonnet-4-5-20250929",
    system_prompt=system_prompt,
    model_settings={"temperature": 0.0},
    defer_model_check=True
)

# Load user prompt
user_prompt = loader.load_user_prompt(
    mode="content",
    project_name="AI_READI",
    input_filename="concatenated.txt",
    content=content
)

# Run extraction
result = await agent.run(user_prompt)
```

---

## 6. Migration Strategy

### 6.1 Phase 1: Infrastructure (No Breaking Changes)

**Create:**
- `src/download/prompt_loader.py` - Unified loader
- `src/download/prompts/shared/` - New directory
- `d4d_system_prompt.txt`, `d4d_user_prompt_*.txt` - Unified prompts
- `prompt_versions.yaml` - Version tracking

**No changes to existing code** - just adds new capability.

### 6.2 Phase 2: Aurelian Refactor (Opt-in)

**Modify:**
- `aurelian/src/aurelian/agents/d4d/d4d_agent.py`
- `aurelian/src/aurelian/agents/d4d/d4d_config.py`

**Changes:**
- Add `prompt_set` and `schema_source` to D4DConfig
- Use D4DPromptLoader when prompt_set != "inline"
- **Default to local schema** instead of GitHub
- Keep decorator pattern for backward compatibility
- Add deterministic mode option

**Backward compatible:** Existing code works unchanged.

### 6.3 Phase 3: Claude Refactor (Drop-in Replacement)

**Modify:**
- `src/download/process_concatenated_d4d_claude.py`
- `src/download/process_individual_d4d_gpt5.py`

**Changes:**
- Replace custom `load_prompt_file()` with `D4DPromptLoader`
- Add `--prompt-set` CLI flag
- Default remains "claude" (no breaking changes)

**Backward compatible:** Existing scripts work unchanged.

### 6.4 Phase 4: Testing and Validation

**Test Matrix:**

| Approach | Prompt Set | Schema Source | Expected Result |
|----------|-----------|---------------|-----------------|
| Aurelian | shared | local | ✅ Should work |
| Aurelian | shared | github | ✅ Should work |
| Aurelian | aurelian (inline) | github | ✅ Unchanged (baseline) |
| Claude | shared | local | ✅ Should work |
| Claude | claude | local | ✅ Unchanged (baseline) |
| GPT-5 script | shared | local | ✅ Should work |

---

## 7. Compatibility Matrix

### 7.1 Feature Compatibility

| Feature | Aurelian | Claude | Unified | Notes |
|---------|----------|--------|---------|-------|
| **External prompts** | ❌ No | ✅ Yes | ✅ Yes | Aurelian needs refactor |
| **Schema placeholder** | ✅ {schema} | ✅ {schema} | ✅ {schema} | Already compatible |
| **Schema source** | GitHub | Local | **Local (default)** | Per user preference |
| **Deterministic mode** | ❌ No | ✅ Yes | ✅ Yes | temperature=0.0 |
| **Content mode** | ⚠️ Via tool | ✅ Native | ✅ Both | Support both modes |
| **URL mode** | ✅ Native | ❌ No | ✅ Both | Support both modes |
| **Provenance tracking** | ❌ No | ✅ Yes | ✅ Yes | Full metadata |
| **Prompt versioning** | ❌ No | ✅ Yes | ✅ Yes | YAML headers |

### 7.2 Execution Mode Compatibility

| Mode | Aurelian | Claude | Unified |
|------|----------|--------|---------|
| **URL fetching** | ✅ Tool-based | ❌ N/A | ✅ Optional tool |
| **Content embedded** | ⚠️ Workaround | ✅ Native | ✅ Preferred |
| **Deterministic** | ❌ No | ✅ Yes | ✅ Default |
| **Metadata tracking** | ❌ No | ✅ Yes | ✅ Always |

---

## 8. Recommendations

### 8.1 Default Configuration

```yaml
# Recommended defaults for unified approach
prompt_set: "shared"              # Use unified prompts
schema_source: "local"            # Local schema (per user requirement)
schema_path: "src/data_sheets_schema/schema/data_sheets_schema_all.yaml"
execution_mode: "content"         # Pre-load content (reproducibility)
model_settings:
  temperature: 0.0                # Deterministic
  max_tokens: 16000               # Sufficient for D4D
provenance_tracking: true         # Always track metadata
```

### 8.2 Migration Path

**For Aurelian users:**
1. Start using `--schema-source local` flag (new default)
2. Optionally try `--prompt-set shared` (improved prompts)
3. Consider `--deterministic` flag for reproducibility
4. Existing workflows continue to work unchanged

**For Claude users:**
1. Optionally try `--prompt-set shared` (unified prompts)
2. No changes needed - already using local schema
3. Continue with current workflow

### 8.3 Best Practices

1. **Always use local schema** for reproducibility (default)
2. **Always use temperature=0.0** for deterministic results
3. **Always track provenance** metadata
4. **Prefer content mode** over URL mode when possible
5. **Version control prompts** in external files
6. **Hash all inputs** (schema, prompts, content) for verification

---

## 9. Conclusion

**The two approaches CAN share prompts** with these strategic changes:

### What's Already Compatible:
- ✅ Prompt content and structure
- ✅ {schema} placeholder pattern
- ✅ Model selection (GPT-5, Claude)
- ✅ YAML output format

### What Needs Abstraction:
- 🔧 Schema injection (use constructor-based)
- 🔧 Prompt file loading (external files for all)
- 🔧 Schema source (**default to local**)
- 🔧 Execution mode (support both URL and content)

### What Stays Different:
- ⚠️ Tool calling (Aurelian-specific, optional)
- ⚠️ Decorator patterns (pydantic-ai specific, optional)
- ⚠️ Implementation details (don't need to unify)

**Implementation Complexity:** Low-Medium
- New infrastructure: 1 new Python module, 4 new prompt files
- Refactoring: 4 existing files modified (backward compatible)
- Testing: Comprehensive but straightforward

**Benefits:**
- ✅ Consistent prompts across approaches
- ✅ Better prompt quality (merge best of both)
- ✅ Reproducibility with local schema
- ✅ Provenance tracking everywhere
- ✅ Easier prompt iteration and improvement
- ✅ Flexible execution modes

**Timeline:** 6-9 hours implementation + testing

---

**Analysis Completed:** December 3, 2025
**Analyst:** Claude Code (claude-sonnet-4-5-20250929)
**Next Steps:** Implement Phase 1 - Create shared prompt infrastructure
