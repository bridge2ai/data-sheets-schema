

# Slot: imputation_method 


_Specific imputation technique used (mean, median, mode, forward fill, backward fill, interpolation, model-based imputation, etc.)._

__





URI: [data_sheets_schema:imputation_method](https://w3id.org/bridge2ai/data-sheets-schema/imputation_method)
Alias: imputation_method

<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [ImputationProtocol](ImputationProtocol.md) | Description of data imputation methodology, including techniques used to hand... |  no  |






## Properties

* Range: [String](String.md)

* Multivalued: True




## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | data_sheets_schema:imputation_method |
| native | data_sheets_schema:imputation_method |




## LinkML Source

<details>
```yaml
name: imputation_method
description: 'Specific imputation technique used (mean, median, mode, forward fill,
  backward fill, interpolation, model-based imputation, etc.).

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
rank: 1000
alias: imputation_method
owner: ImputationProtocol
domain_of:
- ImputationProtocol
range: string
multivalued: true

```
</details>