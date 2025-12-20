

# Class: DistributionDate 


_When will the dataset be distributed?_

__





URI: [data_sheets_schema:DistributionDate](https://w3id.org/bridge2ai/data-sheets-schema/DistributionDate)





```mermaid
 classDiagram
    class DistributionDate
    click DistributionDate href "../DistributionDate/"
      DatasetProperty <|-- DistributionDate
        click DatasetProperty href "../DatasetProperty/"
      
      DistributionDate : description
        
      DistributionDate : id
        
      DistributionDate : name
        
      DistributionDate : release_dates
        
      DistributionDate : used_software
        
          
    
        
        
        DistributionDate --> "*" Software : used_software
        click Software href "../Software/"
    

        
      
```





## Inheritance
* [DatasetProperty](DatasetProperty.md)
    * **DistributionDate**



## Slots

| Name | Cardinality and Range | Description | Inheritance |
| ---  | --- | --- | --- |
| [release_dates](release_dates.md) | * <br/> [String](String.md) | Dates or timeframe for dataset release | direct |
| [id](id.md) | 0..1 <br/> [Uriorcurie](Uriorcurie.md) | An optional identifier for this property | [DatasetProperty](DatasetProperty.md) |
| [name](name.md) | 0..1 <br/> [String](String.md) | A human-readable name for this property | [DatasetProperty](DatasetProperty.md) |
| [description](description.md) | 0..1 <br/> [String](String.md) | A human-readable description for this property | [DatasetProperty](DatasetProperty.md) |
| [used_software](used_software.md) | * <br/> [Software](Software.md) | What software was used as part of this dataset property? | [DatasetProperty](DatasetProperty.md) |





## Usages

| used by | used in | type | used |
| ---  | --- | --- | --- |
| [Dataset](Dataset.md) | [distribution_dates](distribution_dates.md) | range | [DistributionDate](DistributionDate.md) |
| [DataSubset](DataSubset.md) | [distribution_dates](distribution_dates.md) | range | [DistributionDate](DistributionDate.md) |







## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | data_sheets_schema:DistributionDate |
| native | data_sheets_schema:DistributionDate |






## LinkML Source

<!-- TODO: investigate https://stackoverflow.com/questions/37606292/how-to-create-tabbed-code-blocks-in-mkdocs-or-sphinx -->

### Direct

<details>
```yaml
name: DistributionDate
description: 'When will the dataset be distributed?

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
is_a: DatasetProperty
attributes:
  release_dates:
    name: release_dates
    description: 'Dates or timeframe for dataset release. Could be a one-time release
      date or multiple scheduled releases.

      '
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/distribution
    rank: 1000
    slot_uri: dcterms:available
    domain_of:
    - DistributionDate
    range: string
    multivalued: true

```
</details>

### Induced

<details>
```yaml
name: DistributionDate
description: 'When will the dataset be distributed?

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
is_a: DatasetProperty
attributes:
  release_dates:
    name: release_dates
    description: 'Dates or timeframe for dataset release. Could be a one-time release
      date or multiple scheduled releases.

      '
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/distribution
    rank: 1000
    slot_uri: dcterms:available
    alias: release_dates
    owner: DistributionDate
    domain_of:
    - DistributionDate
    range: string
    multivalued: true
  id:
    name: id
    description: An optional identifier for this property.
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/base
    slot_uri: schema:identifier
    alias: id
    owner: DistributionDate
    domain_of:
    - NamedThing
    - DatasetProperty
    range: uriorcurie
  name:
    name: name
    description: A human-readable name for this property.
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/base
    slot_uri: schema:name
    alias: name
    owner: DistributionDate
    domain_of:
    - NamedThing
    - DatasetProperty
    range: string
  description:
    name: description
    description: A human-readable description for this property.
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/base
    slot_uri: schema:description
    alias: description
    owner: DistributionDate
    domain_of:
    - NamedThing
    - DatasetProperty
    - DatasetRelationship
    range: string
  used_software:
    name: used_software
    description: What software was used as part of this dataset property?
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/base
    rank: 1000
    alias: used_software
    owner: DistributionDate
    domain_of:
    - DatasetProperty
    range: Software
    multivalued: true
    inlined: true
    inlined_as_list: true

```
</details>