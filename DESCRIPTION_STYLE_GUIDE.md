# D4D Schema Description Style Guide

## Purpose

This guide establishes consistent standards for writing descriptions in D4D (Datasheets for Datasets) schema modules. Clear, consistent descriptions improve schema usability, documentation quality, and user understanding.

## Element-Specific Patterns

Different schema elements require different description styles based on their purpose and usage:

| Element Type | Structure | Target Length | Examples Needed? | Completeness |
|--------------|-----------|---------------|------------------|--------------|
| **Class** | Complete sentence(s) | 15-30 words | Optional (26% currently) | Explain purpose and context |
| **Attribute** | Complete sentence | 8-15 words | Recommended (target 40%) | Describe what it represents |
| **Slot** | Complete sentence | 10-15 words | Optional (20% currently) | Define the property |
| **Enum** | Complete sentence or fragment | 8-15 words | Rare (5%) | Categorize the value set |
| **Enum Value** | Fragment acceptable | 3-10 words | Only if clarifying | Identify the specific value |

## Quality Criteria

### All Descriptions Should:

✅ **Be technically accurate** - No errors in technical details or standards  
✅ **Use consistent terminology** - Same terms for same concepts across modules  
✅ **Be clear and concise** - Direct language, avoid wordiness  
✅ **Avoid unnecessary jargon** - Use technical terms only when required  
✅ **Include practical context** - Explain when/why to use something  

### Examples Should:

✅ **Show common values/formats** - E.g., `"MIT", "Apache-2.0"` for licenses  
✅ **Clarify ambiguous cases** - When the name alone isn't clear  
✅ **Be brief** - In parentheses or following "e.g."  
✅ **Not repeat the obvious** - Don't explain what's clear from the name  

---

## Writing Guidelines by Element Type

### Classes

**Structure**: Complete sentence(s) describing the class purpose  
**Length**: 15-30 words  
**Format**: Often starts with a question (D4D modules) or statement  
**Examples**: Optional but helpful for abstract concepts

**Good Examples:**

```yaml
Purpose:
  description: "For what purpose was the dataset created?"
  
Software:
  description: "A software program or library."
  
Person:
  description: >-
    An individual human being. This class represents a person in the context
    of a specific dataset. Attributes like affiliation and email represent
    the person's current or most relevant contact information for this dataset.
```

**Pattern**: 
- D4D module classes often phrase as questions to reflect datasheet format
- Base classes use declarative statements
- Multi-sentence descriptions acceptable for complex classes

---

### Attributes

**Structure**: Complete sentence ending with period  
**Length**: 8-15 words  
**Format**: Descriptive statement about what the attribute represents  
**Examples**: Recommended (~40% target) especially for:
- Format specifications (e.g., DOI patterns, version formats)
- Enumerations with many possible values
- Fields where example clarifies usage

**Good Examples:**

```yaml
version:
  description: The version identifier of the software (e.g., "1.0.0", "2.3.1-beta").
  
license:
  description: >-
    The license under which the software is distributed (e.g., "MIT", "Apache-2.0", "GPL-3.0").
  
orcid:
  description: >-
    ORCID (Open Researcher and Contributor ID) - a persistent digital identifier
    for researchers. Format: 0000-0000-0000-0000 (16 digits in groups of 4).
```

**Poor Examples (Too Brief):**

```yaml
# ❌ TOO BRIEF
version:
  description: Software version
  
# ❌ TOO BRIEF
email:
  description: Email address
```

**Pattern**: Subject + verb + object + (optional example)

---

### Slots

**Structure**: Complete sentence ending with period  
**Length**: 10-15 words  
**Format**: Define what the slot represents  
**Examples**: Optional, use when format/pattern needs clarification

**Good Examples:**

```yaml
publisher:
  description: The organization or entity responsible for making the resource available.
  
issued:
  description: Date of formal issuance or publication of the resource.
  
doi:
  description: digital object identifier
  pattern: "10\\.\\d{4,}\\/.+"
```

**Pattern**: Declarative statement about the property's meaning

---

### Enums

**Structure**: Complete sentence or informative fragment  
**Length**: 8-15 words  
**Format**: Categorize or explain the value set  
**Examples**: Rare (only when the enum name isn't self-explanatory)

**Good Examples:**

```yaml
FormatEnum:
  description: Common file format extensions for data files and documents.
  
EncodingEnum:
  description: Character encoding schemes for text representation in different languages and scripts.
  
BiasTypeEnum:
  description: >-
    Types of bias that may be present in datasets. Values are mapped to the
    Artificial Intelligence Ontology (AIO) bias taxonomy from BioPortal.
```

**Pattern**: Noun phrase describing the category + context if specialized

---

### Enum Values

**Structure**: Fragment acceptable, complete sentence if needed for clarity  
**Length**: 3-10 words  
**Format**: Identify the specific value, add context only if helpful  
**Examples**: Only use when the value needs clarification beyond its name

**Good Examples:**

```yaml
# Brief and clear
CSV:
  description: Comma-Separated Values - tabular data format

# Contextual information added
gzip:
  description: GNU zip compression (commonly used with .gz extension)

# Technical detail for clarity
UTF-8:
  description: Unicode Transformation Format 8-bit (variable-width, most common Unicode encoding)

# Language context for ISO standards
ISO-8859-1:
  description: Latin-1 (Western European languages)
```

**Poor Examples:**

```yaml
# ❌ Too verbose for enum value
CSV:
  description: >-
    Comma-Separated Values is a tabular data format that uses commas to 
    separate individual values and is widely used for data interchange
    between different applications and systems.

# ❌ Too brief when context needed
ISO-8859-1:
  description: Latin-1
```

**Pattern**: 
- Format name + brief purpose (for formats)
- Algorithm + common usage (for compression)
- Standard + language scope (for encodings)

---

## Decision Tree: When to Add Examples

```
Is the property name self-explanatory?
├─ YES → Example optional
└─ NO
    └─ Does it accept multiple formats/values?
        ├─ YES → Add 2-3 examples
        └─ NO
            └─ Does it have a specific pattern/format?
                ├─ YES → Add 1 format example
                └─ NO → Example optional
```

**Always add examples for:**
- Pattern-based fields (DOI, ORCID, version numbers)
- Enumerations with >5 possible values (license types, keywords)
- Fields where format isn't obvious (dates, identifiers)

**Optional examples for:**
- Boolean fields (obvious values)
- Single-format fields (URL, email)
- Self-explanatory names (title, name, description)

---

## Common Patterns

### Format Specifications

```yaml
# Pattern: Type + format explanation + example
doi:
  description: Digital Object Identifier (DOI) in format 10.xxxx/xxxxx
  pattern: "10\\.\\d{4,}\\/.+"
```

### Temporal Fields

```yaml
# Pattern: Purpose + what timestamp represents
created_on:
  description: The date and time when the resource was created.
  range: datetime
```

### Organizational Fields

```yaml
# Pattern: Role + context + example
publisher:
  description: The organization or entity responsible for making the resource available (e.g., "University of California", "NIH", "Zenodo").
```

### Technical Specifications

```yaml
# Pattern: Technology + purpose + context
compression:
  description: >-
    Compression format used, if any (e.g., gzip, bzip2, zip).
```

---

## Anti-Patterns to Avoid

### ❌ Too Brief

```yaml
# Bad
bytes: "Size in bytes"

# Good
bytes: "Size of the data in bytes."
```

### ❌ Redundant with Name

```yaml
# Bad
name: "The name of the thing"

# Good
name: "A human-readable name for a thing."
```

### ❌ Overly Technical Without Context

```yaml
# Bad (for enum value)
ISO-2022-JP:
  description: "JIS X 0208-1983 and JIS X 0201 character encoding"

# Good
ISO-2022-JP:
  description: "ISO-2022 encoding for Japanese"
```

### ❌ Missing Examples When Needed

```yaml
# Bad
keywords:
  description: "Keywords or tags describing the resource."

# Good
keywords:
  description: "Keywords or tags describing the resource (e.g., ['genomics', 'cancer', 'RNA-seq'])."
```

---

## Tools for Validation

### Check Description Quality

```bash
python check_description_quality.py
```

Checks for:
- Missing descriptions
- Too-brief descriptions (<5 words)
- Missing periods on attributes/slots
- Recommended examples not present

### Before Committing

```bash
# Validate schema
make test-schema

# Check quality
python check_description_quality.py

# Regenerate artifacts
make regen-all

# Run tests
make test
```

---

## Revision History

- **2026-04-08**: Initial style guide created based on analysis of 122 recently-added descriptions
- Establishes element-specific patterns
- Defines quality criteria and common patterns
- Provides decision tree for example usage
