

# Slot: reviewing_organization 


_Organization that conducted the ethical review (e.g., Institutional Review Board, Ethics Committee, Research Ethics Board). Provides information about the body responsible for ethical oversight._





URI: [schema:provider](http://schema.org/provider)
Alias: reviewing_organization

<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [EthicalReview](EthicalReview.md) | Were any ethical or compliance review processes conducted (e |  no  |






## Properties

* Range: [Organization](Organization.md)




## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | schema:provider |
| native | data_sheets_schema:reviewing_organization |
| exact | schema:provider |




## LinkML Source

<details>
```yaml
name: reviewing_organization
description: Organization that conducted the ethical review (e.g., Institutional Review
  Board, Ethics Committee, Research Ethics Board). Provides information about the
  body responsible for ethical oversight.
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
exact_mappings:
- schema:provider
rank: 1000
slot_uri: schema:provider
alias: reviewing_organization
owner: EthicalReview
domain_of:
- EthicalReview
range: Organization

```
</details>