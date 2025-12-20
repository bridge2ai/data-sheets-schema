

# Class: AddressingGap 


_Was there a specific gap that needed to be filled by creation of the dataset?_





URI: [data_sheets_schema:AddressingGap](https://w3id.org/bridge2ai/data-sheets-schema/AddressingGap)





```mermaid
 classDiagram
    class AddressingGap
    click AddressingGap href "../AddressingGap/"
      DatasetProperty <|-- AddressingGap
        click DatasetProperty href "../DatasetProperty/"
      
      AddressingGap : description
        
      AddressingGap : id
        
      AddressingGap : name
        
      AddressingGap : response
        
      AddressingGap : used_software
        
          
    
        
        
        AddressingGap --> "*" Software : used_software
        click Software href "../Software/"
    

        
      
```





## Inheritance
* [DatasetProperty](DatasetProperty.md)
    * **AddressingGap**



## Slots

| Name | Cardinality and Range | Description | Inheritance |
| ---  | --- | --- | --- |
| [response](response.md) | 0..1 <br/> [String](String.md) | Short explanation of the knowledge or resource gap that this dataset was inte... | direct |
| [id](id.md) | 0..1 <br/> [Uriorcurie](Uriorcurie.md) | An optional identifier for this property | [DatasetProperty](DatasetProperty.md) |
| [name](name.md) | 0..1 <br/> [String](String.md) | A human-readable name for this property | [DatasetProperty](DatasetProperty.md) |
| [description](description.md) | 0..1 <br/> [String](String.md) | A human-readable description for this property | [DatasetProperty](DatasetProperty.md) |
| [used_software](used_software.md) | * <br/> [Software](Software.md) | What software was used as part of this dataset property? | [DatasetProperty](DatasetProperty.md) |





## Usages

| used by | used in | type | used |
| ---  | --- | --- | --- |
| [Dataset](Dataset.md) | [addressing_gaps](addressing_gaps.md) | range | [AddressingGap](AddressingGap.md) |
| [DataSubset](DataSubset.md) | [addressing_gaps](addressing_gaps.md) | range | [AddressingGap](AddressingGap.md) |







## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | data_sheets_schema:AddressingGap |
| native | data_sheets_schema:AddressingGap |






## LinkML Source

<!-- TODO: investigate https://stackoverflow.com/questions/37606292/how-to-create-tabbed-code-blocks-in-mkdocs-or-sphinx -->

### Direct

<details>
```yaml
name: AddressingGap
description: Was there a specific gap that needed to be filled by creation of the
  dataset?
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
is_a: DatasetProperty
attributes:
  response:
    name: response
    description: Short explanation of the knowledge or resource gap that this dataset
      was intended to address.
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/motivation
    slot_uri: dcterms:description
    domain_of:
    - Purpose
    - Task
    - AddressingGap
    range: string

```
</details>

### Induced

<details>
```yaml
name: AddressingGap
description: Was there a specific gap that needed to be filled by creation of the
  dataset?
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
is_a: DatasetProperty
attributes:
  response:
    name: response
    description: Short explanation of the knowledge or resource gap that this dataset
      was intended to address.
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/motivation
    slot_uri: dcterms:description
    alias: response
    owner: AddressingGap
    domain_of:
    - Purpose
    - Task
    - AddressingGap
    range: string
  id:
    name: id
    description: An optional identifier for this property.
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/base
    slot_uri: schema:identifier
    alias: id
    owner: AddressingGap
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
    owner: AddressingGap
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
    owner: AddressingGap
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
    owner: AddressingGap
    domain_of:
    - DatasetProperty
    range: Software
    multivalued: true
    inlined: true
    inlined_as_list: true

```
</details>