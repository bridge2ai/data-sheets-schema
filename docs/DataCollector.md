

# Class: DataCollector 


_Who was involved in the data collection (e.g., students, crowdworkers, contractors), and how they were compensated._

__





URI: [data_sheets_schema:DataCollector](https://w3id.org/bridge2ai/data-sheets-schema/DataCollector)





```mermaid
 classDiagram
    class DataCollector
    click DataCollector href "../DataCollector/"
      DatasetProperty <|-- DataCollector
        click DatasetProperty href "../DatasetProperty/"
      
      DataCollector : collector_details
        
      DataCollector : description
        
      DataCollector : id
        
      DataCollector : name
        
      DataCollector : role
        
      DataCollector : used_software
        
          
    
        
        
        DataCollector --> "*" Software : used_software
        click Software href "../Software/"
    

        
      
```





## Inheritance
* [DatasetProperty](DatasetProperty.md)
    * **DataCollector**



## Slots

| Name | Cardinality and Range | Description | Inheritance |
| ---  | --- | --- | --- |
| [role](role.md) | 0..1 <br/> [String](String.md) | Role of the data collector (e | direct |
| [collector_details](collector_details.md) | * <br/> [String](String.md) | Details on who collected the data and their compensation | direct |
| [id](id.md) | 0..1 <br/> [Uriorcurie](Uriorcurie.md) | An optional identifier for this property | [DatasetProperty](DatasetProperty.md) |
| [name](name.md) | 0..1 <br/> [String](String.md) | A human-readable name for this property | [DatasetProperty](DatasetProperty.md) |
| [description](description.md) | 0..1 <br/> [String](String.md) | A human-readable description for this property | [DatasetProperty](DatasetProperty.md) |
| [used_software](used_software.md) | * <br/> [Software](Software.md) | What software was used as part of this dataset property? | [DatasetProperty](DatasetProperty.md) |





## Usages

| used by | used in | type | used |
| ---  | --- | --- | --- |
| [Dataset](Dataset.md) | [data_collectors](data_collectors.md) | range | [DataCollector](DataCollector.md) |
| [DataSubset](DataSubset.md) | [data_collectors](data_collectors.md) | range | [DataCollector](DataCollector.md) |







## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | data_sheets_schema:DataCollector |
| native | data_sheets_schema:DataCollector |






## LinkML Source

<!-- TODO: investigate https://stackoverflow.com/questions/37606292/how-to-create-tabbed-code-blocks-in-mkdocs-or-sphinx -->

### Direct

<details>
```yaml
name: DataCollector
description: 'Who was involved in the data collection (e.g., students, crowdworkers,
  contractors), and how they were compensated.

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
is_a: DatasetProperty
attributes:
  role:
    name: role
    description: Role of the data collector (e.g., researcher, crowdworker)
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/collection
    rank: 1000
    domain_of:
    - DataCollector
    - Maintainer
    range: string
  collector_details:
    name: collector_details
    description: 'Details on who collected the data and their compensation.

      '
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/collection
    rank: 1000
    slot_uri: dcterms:description
    domain_of:
    - DataCollector
    range: string
    multivalued: true

```
</details>

### Induced

<details>
```yaml
name: DataCollector
description: 'Who was involved in the data collection (e.g., students, crowdworkers,
  contractors), and how they were compensated.

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
is_a: DatasetProperty
attributes:
  role:
    name: role
    description: Role of the data collector (e.g., researcher, crowdworker)
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/collection
    rank: 1000
    alias: role
    owner: DataCollector
    domain_of:
    - DataCollector
    - Maintainer
    range: string
  collector_details:
    name: collector_details
    description: 'Details on who collected the data and their compensation.

      '
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/collection
    rank: 1000
    slot_uri: dcterms:description
    alias: collector_details
    owner: DataCollector
    domain_of:
    - DataCollector
    range: string
    multivalued: true
  id:
    name: id
    description: An optional identifier for this property.
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/base
    slot_uri: schema:identifier
    alias: id
    owner: DataCollector
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
    owner: DataCollector
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
    owner: DataCollector
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
    owner: DataCollector
    domain_of:
    - DatasetProperty
    range: Software
    multivalued: true
    inlined: true
    inlined_as_list: true

```
</details>