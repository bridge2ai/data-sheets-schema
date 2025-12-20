

# Class: DirectCollection 


_Indicates whether the data was collected directly from the individuals in question or obtained via third parties/other sources._

__





URI: [data_sheets_schema:DirectCollection](https://w3id.org/bridge2ai/data-sheets-schema/DirectCollection)





```mermaid
 classDiagram
    class DirectCollection
    click DirectCollection href "../DirectCollection/"
      DatasetProperty <|-- DirectCollection
        click DatasetProperty href "../DatasetProperty/"
      
      DirectCollection : collection_details
        
      DirectCollection : description
        
      DirectCollection : id
        
      DirectCollection : is_direct
        
      DirectCollection : name
        
      DirectCollection : used_software
        
          
    
        
        
        DirectCollection --> "*" Software : used_software
        click Software href "../Software/"
    

        
      
```





## Inheritance
* [DatasetProperty](DatasetProperty.md)
    * **DirectCollection**



## Slots

| Name | Cardinality and Range | Description | Inheritance |
| ---  | --- | --- | --- |
| [is_direct](is_direct.md) | 0..1 <br/> [Boolean](Boolean.md) | Whether collection was direct from individuals | direct |
| [collection_details](collection_details.md) | * <br/> [String](String.md) | Details on direct vs | direct |
| [id](id.md) | 0..1 <br/> [Uriorcurie](Uriorcurie.md) | An optional identifier for this property | [DatasetProperty](DatasetProperty.md) |
| [name](name.md) | 0..1 <br/> [String](String.md) | A human-readable name for this property | [DatasetProperty](DatasetProperty.md) |
| [description](description.md) | 0..1 <br/> [String](String.md) | A human-readable description for this property | [DatasetProperty](DatasetProperty.md) |
| [used_software](used_software.md) | * <br/> [Software](Software.md) | What software was used as part of this dataset property? | [DatasetProperty](DatasetProperty.md) |










## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | data_sheets_schema:DirectCollection |
| native | data_sheets_schema:DirectCollection |






## LinkML Source

<!-- TODO: investigate https://stackoverflow.com/questions/37606292/how-to-create-tabbed-code-blocks-in-mkdocs-or-sphinx -->

### Direct

<details>
```yaml
name: DirectCollection
description: 'Indicates whether the data was collected directly from the individuals
  in question or obtained via third parties/other sources.

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
is_a: DatasetProperty
attributes:
  is_direct:
    name: is_direct
    description: Whether collection was direct from individuals
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/collection
    rank: 1000
    domain_of:
    - DirectCollection
    range: boolean
  collection_details:
    name: collection_details
    description: 'Details on direct vs. indirect collection methods and sources.

      '
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/collection
    rank: 1000
    slot_uri: dcterms:description
    domain_of:
    - DirectCollection
    range: string
    multivalued: true

```
</details>

### Induced

<details>
```yaml
name: DirectCollection
description: 'Indicates whether the data was collected directly from the individuals
  in question or obtained via third parties/other sources.

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
is_a: DatasetProperty
attributes:
  is_direct:
    name: is_direct
    description: Whether collection was direct from individuals
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/collection
    rank: 1000
    alias: is_direct
    owner: DirectCollection
    domain_of:
    - DirectCollection
    range: boolean
  collection_details:
    name: collection_details
    description: 'Details on direct vs. indirect collection methods and sources.

      '
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/collection
    rank: 1000
    slot_uri: dcterms:description
    alias: collection_details
    owner: DirectCollection
    domain_of:
    - DirectCollection
    range: string
    multivalued: true
  id:
    name: id
    description: An optional identifier for this property.
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/base
    slot_uri: schema:identifier
    alias: id
    owner: DirectCollection
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
    owner: DirectCollection
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
    owner: DirectCollection
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
    owner: DirectCollection
    domain_of:
    - DatasetProperty
    range: Software
    multivalued: true
    inlined: true
    inlined_as_list: true

```
</details>