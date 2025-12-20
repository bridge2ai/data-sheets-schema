

# Slot: notification_details 


_Details on how individuals were notified about data collection._

__





URI: [dcterms:description](http://purl.org/dc/terms/description)
Alias: notification_details

<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [CollectionNotification](CollectionNotification.md) | Were the individuals in question notified about the data collection? If so, p... |  no  |






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
| native | data_sheets_schema:notification_details |




## LinkML Source

<details>
```yaml
name: notification_details
description: 'Details on how individuals were notified about data collection.

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
rank: 1000
slot_uri: dcterms:description
alias: notification_details
owner: CollectionNotification
domain_of:
- CollectionNotification
range: string
multivalued: true

```
</details>