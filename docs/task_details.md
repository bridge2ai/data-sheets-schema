

# Slot: task_details 


_Details on other potential tasks the dataset could be used for._

__





URI: [dcterms:description](http://purl.org/dc/terms/description)
Alias: task_details

<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [OtherTask](OtherTask.md) | What other tasks could the dataset be used for? |  no  |






## Properties

* Range: [String](String.md)

* Multivalued: True




## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | dcterms:description |
| native | data_sheets_schema:task_details |




## LinkML Source

<details>
```yaml
name: task_details
description: 'Details on other potential tasks the dataset could be used for.

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
rank: 1000
slot_uri: dcterms:description
alias: task_details
owner: OtherTask
domain_of:
- OtherTask
range: string
multivalued: true

```
</details>