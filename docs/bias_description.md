

# Slot: bias_description 


_Detailed description of how this bias manifests in the dataset, including affected populations, features, or outcomes._

__





URI: [dcterms:description](http://purl.org/dc/terms/description)
Alias: bias_description

<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [DatasetBias](DatasetBias.md) | Documents known biases present in the dataset |  no  |






## Properties

* Range: [String](String.md)




## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | dcterms:description |
| native | data_sheets_schema:bias_description |




## LinkML Source

<details>
```yaml
name: bias_description
description: 'Detailed description of how this bias manifests in the dataset, including
  affected populations, features, or outcomes.

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
rank: 1000
slot_uri: dcterms:description
alias: bias_description
owner: DatasetBias
domain_of:
- DatasetBias
range: string

```
</details>