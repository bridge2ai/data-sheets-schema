

# Class: UseRepository 


_Is there a repository that links to any or all papers or systems that use the dataset? If so, provide a link or other access point._

__





URI: [data_sheets_schema:UseRepository](https://w3id.org/bridge2ai/data-sheets-schema/UseRepository)





```mermaid
 classDiagram
    class UseRepository
    click UseRepository href "../UseRepository/"
      DatasetProperty <|-- UseRepository
        click DatasetProperty href "../DatasetProperty/"
      
      UseRepository : description
        
      UseRepository : id
        
      UseRepository : name
        
      UseRepository : repository_details
        
      UseRepository : repository_url
        
      UseRepository : used_software
        
          
    
        
        
        UseRepository --> "*" Software : used_software
        click Software href "../Software/"
    

        
      
```





## Inheritance
* [DatasetProperty](DatasetProperty.md)
    * **UseRepository**



## Slots

| Name | Cardinality and Range | Description | Inheritance |
| ---  | --- | --- | --- |
| [repository_url](repository_url.md) | 0..1 <br/> [Uri](Uri.md) | URL to a repository of known dataset uses | direct |
| [repository_details](repository_details.md) | * <br/> [String](String.md) | Details on the repository of known dataset uses | direct |
| [id](id.md) | 0..1 <br/> [Uriorcurie](Uriorcurie.md) | An optional identifier for this property | [DatasetProperty](DatasetProperty.md) |
| [name](name.md) | 0..1 <br/> [String](String.md) | A human-readable name for this property | [DatasetProperty](DatasetProperty.md) |
| [description](description.md) | 0..1 <br/> [String](String.md) | A human-readable description for this property | [DatasetProperty](DatasetProperty.md) |
| [used_software](used_software.md) | * <br/> [Software](Software.md) | What software was used as part of this dataset property? | [DatasetProperty](DatasetProperty.md) |





## Usages

| used by | used in | type | used |
| ---  | --- | --- | --- |
| [Dataset](Dataset.md) | [use_repository](use_repository.md) | range | [UseRepository](UseRepository.md) |
| [DataSubset](DataSubset.md) | [use_repository](use_repository.md) | range | [UseRepository](UseRepository.md) |







## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | data_sheets_schema:UseRepository |
| native | data_sheets_schema:UseRepository |






## LinkML Source

<!-- TODO: investigate https://stackoverflow.com/questions/37606292/how-to-create-tabbed-code-blocks-in-mkdocs-or-sphinx -->

### Direct

<details>
```yaml
name: UseRepository
description: 'Is there a repository that links to any or all papers or systems that
  use the dataset? If so, provide a link or other access point.

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
is_a: DatasetProperty
attributes:
  repository_url:
    name: repository_url
    description: URL to a repository of known dataset uses.
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/uses
    rank: 1000
    domain_of:
    - UseRepository
    range: uri
  repository_details:
    name: repository_details
    description: 'Details on the repository of known dataset uses.

      '
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/uses
    rank: 1000
    slot_uri: dcterms:description
    domain_of:
    - UseRepository
    range: string
    multivalued: true

```
</details>

### Induced

<details>
```yaml
name: UseRepository
description: 'Is there a repository that links to any or all papers or systems that
  use the dataset? If so, provide a link or other access point.

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
is_a: DatasetProperty
attributes:
  repository_url:
    name: repository_url
    description: URL to a repository of known dataset uses.
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/uses
    rank: 1000
    alias: repository_url
    owner: UseRepository
    domain_of:
    - UseRepository
    range: uri
  repository_details:
    name: repository_details
    description: 'Details on the repository of known dataset uses.

      '
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/uses
    rank: 1000
    slot_uri: dcterms:description
    alias: repository_details
    owner: UseRepository
    domain_of:
    - UseRepository
    range: string
    multivalued: true
  id:
    name: id
    description: An optional identifier for this property.
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/base
    slot_uri: schema:identifier
    alias: id
    owner: UseRepository
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
    owner: UseRepository
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
    owner: UseRepository
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
    owner: UseRepository
    domain_of:
    - DatasetProperty
    range: Software
    multivalued: true
    inlined: true
    inlined_as_list: true

```
</details>