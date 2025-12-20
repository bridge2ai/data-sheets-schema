

# Class: ThirdPartySharing 


_Will the dataset be distributed to third parties outside of the entity (e.g., company, institution, organization) on behalf of which the dataset was created?_

__





URI: [data_sheets_schema:ThirdPartySharing](https://w3id.org/bridge2ai/data-sheets-schema/ThirdPartySharing)





```mermaid
 classDiagram
    class ThirdPartySharing
    click ThirdPartySharing href "../ThirdPartySharing/"
      DatasetProperty <|-- ThirdPartySharing
        click DatasetProperty href "../DatasetProperty/"
      
      ThirdPartySharing : description
        
      ThirdPartySharing : id
        
      ThirdPartySharing : is_shared
        
      ThirdPartySharing : name
        
      ThirdPartySharing : used_software
        
          
    
        
        
        ThirdPartySharing --> "*" Software : used_software
        click Software href "../Software/"
    

        
      
```





## Inheritance
* [DatasetProperty](DatasetProperty.md)
    * **ThirdPartySharing**



## Slots

| Name | Cardinality and Range | Description | Inheritance |
| ---  | --- | --- | --- |
| [is_shared](is_shared.md) | 0..1 <br/> [Boolean](Boolean.md) | Boolean indicating whether the dataset is distributed to parties external to ... | direct |
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
| self | data_sheets_schema:ThirdPartySharing |
| native | data_sheets_schema:ThirdPartySharing |






## LinkML Source

<!-- TODO: investigate https://stackoverflow.com/questions/37606292/how-to-create-tabbed-code-blocks-in-mkdocs-or-sphinx -->

### Direct

<details>
```yaml
name: ThirdPartySharing
description: 'Will the dataset be distributed to third parties outside of the entity
  (e.g., company, institution, organization) on behalf of which the dataset was created?

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
is_a: DatasetProperty
attributes:
  is_shared:
    name: is_shared
    description: 'Boolean indicating whether the dataset is distributed to parties
      external to the dataset-creating entity.

      '
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/distribution
    rank: 1000
    slot_uri: dcterms:accessRights
    domain_of:
    - ThirdPartySharing
    range: boolean

```
</details>

### Induced

<details>
```yaml
name: ThirdPartySharing
description: 'Will the dataset be distributed to third parties outside of the entity
  (e.g., company, institution, organization) on behalf of which the dataset was created?

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
is_a: DatasetProperty
attributes:
  is_shared:
    name: is_shared
    description: 'Boolean indicating whether the dataset is distributed to parties
      external to the dataset-creating entity.

      '
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/distribution
    rank: 1000
    slot_uri: dcterms:accessRights
    alias: is_shared
    owner: ThirdPartySharing
    domain_of:
    - ThirdPartySharing
    range: boolean
  id:
    name: id
    description: An optional identifier for this property.
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/base
    slot_uri: schema:identifier
    alias: id
    owner: ThirdPartySharing
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
    owner: ThirdPartySharing
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
    owner: ThirdPartySharing
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
    owner: ThirdPartySharing
    domain_of:
    - DatasetProperty
    range: Software
    multivalued: true
    inlined: true
    inlined_as_list: true

```
</details>