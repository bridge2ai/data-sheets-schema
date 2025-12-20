

# Slot: access_urls 


_Details of the distribution channel(s) or format(s)._





URI: [dcat:accessURL](http://www.w3.org/ns/dcat#accessURL)
Alias: access_urls

<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [DistributionFormat](DistributionFormat.md) | How will the dataset be distributed (e |  no  |






## Properties

* Range: [String](String.md)

* Multivalued: True




## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | dcat:accessURL |
| native | data_sheets_schema:access_urls |




## LinkML Source

<details>
```yaml
name: access_urls
description: Details of the distribution channel(s) or format(s).
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
rank: 1000
slot_uri: dcat:accessURL
alias: access_urls
owner: DistributionFormat
domain_of:
- DistributionFormat
range: string
multivalued: true

```
</details>