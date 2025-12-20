

# Slot: tools 


_List of automated annotation tools with their versions. Format each entry as "ToolName version" (e.g., "spaCy 3.5.0", "NLTK 3.8", "GPT-4 turbo"). Use "unknown" for version if not available (e.g., "Custom NER Model unknown")._

__





URI: [data_sheets_schema:tools](https://w3id.org/bridge2ai/data-sheets-schema/tools)
Alias: tools

<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [MachineAnnotationTools](MachineAnnotationTools.md) | Automated or machine-learning-based annotation tools used in dataset creation... |  no  |






## Properties

* Range: [String](String.md)

* Multivalued: True




## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | data_sheets_schema:tools |
| native | data_sheets_schema:tools |




## LinkML Source

<details>
```yaml
name: tools
description: 'List of automated annotation tools with their versions. Format each
  entry as "ToolName version" (e.g., "spaCy 3.5.0", "NLTK 3.8", "GPT-4 turbo"). Use
  "unknown" for version if not available (e.g., "Custom NER Model unknown").

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
rank: 1000
alias: tools
owner: MachineAnnotationTools
domain_of:
- MachineAnnotationTools
range: string
multivalued: true

```
</details>