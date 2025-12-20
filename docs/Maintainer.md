

# Class: Maintainer 


_Who will be supporting/hosting/maintaining the dataset?_

__





URI: [data_sheets_schema:Maintainer](https://w3id.org/bridge2ai/data-sheets-schema/Maintainer)





```mermaid
 classDiagram
    class Maintainer
    click Maintainer href "../Maintainer/"
      DatasetProperty <|-- Maintainer
        click DatasetProperty href "../DatasetProperty/"
      
      Maintainer : description
        
      Maintainer : id
        
      Maintainer : maintainer_details
        
      Maintainer : name
        
      Maintainer : role
        
          
    
        
        
        Maintainer --> "0..1" CreatorOrMaintainerEnum : role
        click CreatorOrMaintainerEnum href "../CreatorOrMaintainerEnum/"
    

        
      Maintainer : used_software
        
          
    
        
        
        Maintainer --> "*" Software : used_software
        click Software href "../Software/"
    

        
      
```





## Inheritance
* [DatasetProperty](DatasetProperty.md)
    * **Maintainer**



## Slots

| Name | Cardinality and Range | Description | Inheritance |
| ---  | --- | --- | --- |
| [role](role.md) | 0..1 <br/> [CreatorOrMaintainerEnum](CreatorOrMaintainerEnum.md) | Role of the maintainer (e | direct |
| [maintainer_details](maintainer_details.md) | * <br/> [String](String.md) | Details on who will support, host, or maintain the dataset | direct |
| [id](id.md) | 0..1 <br/> [Uriorcurie](Uriorcurie.md) | An optional identifier for this property | [DatasetProperty](DatasetProperty.md) |
| [name](name.md) | 0..1 <br/> [String](String.md) | A human-readable name for this property | [DatasetProperty](DatasetProperty.md) |
| [description](description.md) | 0..1 <br/> [String](String.md) | A human-readable description for this property | [DatasetProperty](DatasetProperty.md) |
| [used_software](used_software.md) | * <br/> [Software](Software.md) | What software was used as part of this dataset property? | [DatasetProperty](DatasetProperty.md) |





## Usages

| used by | used in | type | used |
| ---  | --- | --- | --- |
| [Dataset](Dataset.md) | [maintainers](maintainers.md) | range | [Maintainer](Maintainer.md) |
| [DataSubset](DataSubset.md) | [maintainers](maintainers.md) | range | [Maintainer](Maintainer.md) |







## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | data_sheets_schema:Maintainer |
| native | data_sheets_schema:Maintainer |






## LinkML Source

<!-- TODO: investigate https://stackoverflow.com/questions/37606292/how-to-create-tabbed-code-blocks-in-mkdocs-or-sphinx -->

### Direct

<details>
```yaml
name: Maintainer
description: 'Who will be supporting/hosting/maintaining the dataset?

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
is_a: DatasetProperty
attributes:
  role:
    name: role
    description: 'Role of the maintainer (e.g., researcher, platform, organization).

      '
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/maintenance
    slot_uri: schema:maintainer
    domain_of:
    - DataCollector
    - Maintainer
    range: CreatorOrMaintainerEnum
  maintainer_details:
    name: maintainer_details
    description: 'Details on who will support, host, or maintain the dataset.

      '
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/maintenance
    rank: 1000
    slot_uri: dcterms:description
    domain_of:
    - Maintainer
    range: string
    multivalued: true

```
</details>

### Induced

<details>
```yaml
name: Maintainer
description: 'Who will be supporting/hosting/maintaining the dataset?

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
is_a: DatasetProperty
attributes:
  role:
    name: role
    description: 'Role of the maintainer (e.g., researcher, platform, organization).

      '
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/maintenance
    slot_uri: schema:maintainer
    alias: role
    owner: Maintainer
    domain_of:
    - DataCollector
    - Maintainer
    range: CreatorOrMaintainerEnum
  maintainer_details:
    name: maintainer_details
    description: 'Details on who will support, host, or maintain the dataset.

      '
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/maintenance
    rank: 1000
    slot_uri: dcterms:description
    alias: maintainer_details
    owner: Maintainer
    domain_of:
    - Maintainer
    range: string
    multivalued: true
  id:
    name: id
    description: An optional identifier for this property.
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/base
    slot_uri: schema:identifier
    alias: id
    owner: Maintainer
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
    owner: Maintainer
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
    owner: Maintainer
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
    owner: Maintainer
    domain_of:
    - DatasetProperty
    range: Software
    multivalued: true
    inlined: true
    inlined_as_list: true

```
</details>