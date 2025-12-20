

# Class: DataAnomaly 


_Are there any errors, sources of noise, or redundancies in the dataset?_

__





URI: [data_sheets_schema:DataAnomaly](https://w3id.org/bridge2ai/data-sheets-schema/DataAnomaly)





```mermaid
 classDiagram
    class DataAnomaly
    click DataAnomaly href "../DataAnomaly/"
      DatasetProperty <|-- DataAnomaly
        click DatasetProperty href "../DatasetProperty/"
      
      DataAnomaly : anomaly_details
        
      DataAnomaly : description
        
      DataAnomaly : id
        
      DataAnomaly : name
        
      DataAnomaly : used_software
        
          
    
        
        
        DataAnomaly --> "*" Software : used_software
        click Software href "../Software/"
    

        
      
```





## Inheritance
* [DatasetProperty](DatasetProperty.md)
    * **DataAnomaly**



## Slots

| Name | Cardinality and Range | Description | Inheritance |
| ---  | --- | --- | --- |
| [anomaly_details](anomaly_details.md) | * <br/> [String](String.md) | Details on errors, noise sources, or redundancies in the dataset | direct |
| [id](id.md) | 0..1 <br/> [Uriorcurie](Uriorcurie.md) | An optional identifier for this property | [DatasetProperty](DatasetProperty.md) |
| [name](name.md) | 0..1 <br/> [String](String.md) | A human-readable name for this property | [DatasetProperty](DatasetProperty.md) |
| [description](description.md) | 0..1 <br/> [String](String.md) | A human-readable description for this property | [DatasetProperty](DatasetProperty.md) |
| [used_software](used_software.md) | * <br/> [Software](Software.md) | What software was used as part of this dataset property? | [DatasetProperty](DatasetProperty.md) |





## Usages

| used by | used in | type | used |
| ---  | --- | --- | --- |
| [Dataset](Dataset.md) | [anomalies](anomalies.md) | range | [DataAnomaly](DataAnomaly.md) |
| [DataSubset](DataSubset.md) | [anomalies](anomalies.md) | range | [DataAnomaly](DataAnomaly.md) |







## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | data_sheets_schema:DataAnomaly |
| native | data_sheets_schema:DataAnomaly |






## LinkML Source

<!-- TODO: investigate https://stackoverflow.com/questions/37606292/how-to-create-tabbed-code-blocks-in-mkdocs-or-sphinx -->

### Direct

<details>
```yaml
name: DataAnomaly
description: 'Are there any errors, sources of noise, or redundancies in the dataset?

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
is_a: DatasetProperty
attributes:
  anomaly_details:
    name: anomaly_details
    description: 'Details on errors, noise sources, or redundancies in the dataset.

      '
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/composition
    rank: 1000
    slot_uri: dcterms:description
    domain_of:
    - DataAnomaly
    range: string
    multivalued: true

```
</details>

### Induced

<details>
```yaml
name: DataAnomaly
description: 'Are there any errors, sources of noise, or redundancies in the dataset?

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
is_a: DatasetProperty
attributes:
  anomaly_details:
    name: anomaly_details
    description: 'Details on errors, noise sources, or redundancies in the dataset.

      '
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/composition
    rank: 1000
    slot_uri: dcterms:description
    alias: anomaly_details
    owner: DataAnomaly
    domain_of:
    - DataAnomaly
    range: string
    multivalued: true
  id:
    name: id
    description: An optional identifier for this property.
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/base
    slot_uri: schema:identifier
    alias: id
    owner: DataAnomaly
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
    owner: DataAnomaly
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
    owner: DataAnomaly
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
    owner: DataAnomaly
    domain_of:
    - DatasetProperty
    range: Software
    multivalued: true
    inlined: true
    inlined_as_list: true

```
</details>