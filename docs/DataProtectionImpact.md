

# Class: DataProtectionImpact 


_Has an analysis of the potential impact of the dataset and its use on data subjects (e.g., a data protection impact analysis) been conducted? If so, please provide a description of this analysis, including the outcomes, and any supporting documentation._

__





URI: [data_sheets_schema:DataProtectionImpact](https://w3id.org/bridge2ai/data-sheets-schema/DataProtectionImpact)





```mermaid
 classDiagram
    class DataProtectionImpact
    click DataProtectionImpact href "../DataProtectionImpact/"
      DatasetProperty <|-- DataProtectionImpact
        click DatasetProperty href "../DatasetProperty/"
      
      DataProtectionImpact : description
        
      DataProtectionImpact : id
        
      DataProtectionImpact : impact_details
        
      DataProtectionImpact : name
        
      DataProtectionImpact : used_software
        
          
    
        
        
        DataProtectionImpact --> "*" Software : used_software
        click Software href "../Software/"
    

        
      
```





## Inheritance
* [DatasetProperty](DatasetProperty.md)
    * **DataProtectionImpact**



## Slots

| Name | Cardinality and Range | Description | Inheritance |
| ---  | --- | --- | --- |
| [impact_details](impact_details.md) | * <br/> [String](String.md) | Details on data protection impact analysis, outcomes, and documentation | direct |
| [id](id.md) | 0..1 <br/> [Uriorcurie](Uriorcurie.md) | An optional identifier for this property | [DatasetProperty](DatasetProperty.md) |
| [name](name.md) | 0..1 <br/> [String](String.md) | A human-readable name for this property | [DatasetProperty](DatasetProperty.md) |
| [description](description.md) | 0..1 <br/> [String](String.md) | A human-readable description for this property | [DatasetProperty](DatasetProperty.md) |
| [used_software](used_software.md) | * <br/> [Software](Software.md) | What software was used as part of this dataset property? | [DatasetProperty](DatasetProperty.md) |





## Usages

| used by | used in | type | used |
| ---  | --- | --- | --- |
| [Dataset](Dataset.md) | [data_protection_impacts](data_protection_impacts.md) | range | [DataProtectionImpact](DataProtectionImpact.md) |
| [DataSubset](DataSubset.md) | [data_protection_impacts](data_protection_impacts.md) | range | [DataProtectionImpact](DataProtectionImpact.md) |







## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | data_sheets_schema:DataProtectionImpact |
| native | data_sheets_schema:DataProtectionImpact |






## LinkML Source

<!-- TODO: investigate https://stackoverflow.com/questions/37606292/how-to-create-tabbed-code-blocks-in-mkdocs-or-sphinx -->

### Direct

<details>
```yaml
name: DataProtectionImpact
description: 'Has an analysis of the potential impact of the dataset and its use on
  data subjects (e.g., a data protection impact analysis) been conducted? If so, please
  provide a description of this analysis, including the outcomes, and any supporting
  documentation.

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
is_a: DatasetProperty
attributes:
  impact_details:
    name: impact_details
    description: 'Details on data protection impact analysis, outcomes, and documentation.

      '
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/ethics
    slot_uri: dcterms:description
    domain_of:
    - FutureUseImpact
    - DataProtectionImpact
    range: string
    multivalued: true

```
</details>

### Induced

<details>
```yaml
name: DataProtectionImpact
description: 'Has an analysis of the potential impact of the dataset and its use on
  data subjects (e.g., a data protection impact analysis) been conducted? If so, please
  provide a description of this analysis, including the outcomes, and any supporting
  documentation.

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
is_a: DatasetProperty
attributes:
  impact_details:
    name: impact_details
    description: 'Details on data protection impact analysis, outcomes, and documentation.

      '
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/ethics
    slot_uri: dcterms:description
    alias: impact_details
    owner: DataProtectionImpact
    domain_of:
    - FutureUseImpact
    - DataProtectionImpact
    range: string
    multivalued: true
  id:
    name: id
    description: An optional identifier for this property.
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/base
    slot_uri: schema:identifier
    alias: id
    owner: DataProtectionImpact
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
    owner: DataProtectionImpact
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
    owner: DataProtectionImpact
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
    owner: DataProtectionImpact
    domain_of:
    - DatasetProperty
    range: Software
    multivalued: true
    inlined: true
    inlined_as_list: true

```
</details>