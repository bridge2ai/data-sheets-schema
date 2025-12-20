

# Slot: email 


_The email address of the person. Represents current/preferred contact information in the context of this dataset._





URI: [schema:email](http://schema.org/email)
Alias: email

<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [Person](Person.md) | An individual human being |  no  |






## Properties

* Range: [String](String.md)




## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | schema:email |
| native | data_sheets_schema:email |




## LinkML Source

<details>
```yaml
name: email
description: The email address of the person. Represents current/preferred contact
  information in the context of this dataset.
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
rank: 1000
slot_uri: schema:email
alias: email
owner: Person
domain_of:
- Person
range: string

```
</details>