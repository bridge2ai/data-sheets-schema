

# Slot: tool_accuracy 


_Known accuracy or performance metrics for the automated tools (if available). Include metric name and value (e.g., "spaCy F1: 0.95", "GPT-4 Accuracy: 92%")._

__





URI: [data_sheets_schema:tool_accuracy](https://w3id.org/bridge2ai/data-sheets-schema/tool_accuracy)
Alias: tool_accuracy

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
| self | data_sheets_schema:tool_accuracy |
| native | data_sheets_schema:tool_accuracy |




## LinkML Source

<details>
```yaml
name: tool_accuracy
description: 'Known accuracy or performance metrics for the automated tools (if available).
  Include metric name and value (e.g., "spaCy F1: 0.95", "GPT-4 Accuracy: 92%").

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
rank: 1000
alias: tool_accuracy
owner: MachineAnnotationTools
domain_of:
- MachineAnnotationTools
range: string
multivalued: true

```
</details>