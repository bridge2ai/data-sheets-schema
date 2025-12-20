

# Class: MissingInfo 


_Is any information missing from individual instances? (e.g., unavailable data)_

__





URI: [data_sheets_schema:MissingInfo](https://w3id.org/bridge2ai/data-sheets-schema/MissingInfo)





```mermaid
 classDiagram
    class MissingInfo
    click MissingInfo href "../MissingInfo/"
      DatasetProperty <|-- MissingInfo
        click DatasetProperty href "../DatasetProperty/"
      
      MissingInfo : description
        
      MissingInfo : id
        
      MissingInfo : missing
        
      MissingInfo : name
        
      MissingInfo : used_software
        
          
    
        
        
        MissingInfo --> "*" Software : used_software
        click Software href "../Software/"
    

        
      MissingInfo : why_missing
        
      
```





## Inheritance
* [DatasetProperty](DatasetProperty.md)
    * **MissingInfo**



## Slots

| Name | Cardinality and Range | Description | Inheritance |
| ---  | --- | --- | --- |
| [missing](missing.md) | * <br/> [String](String.md) | Description of the missing data fields or elements | direct |
| [why_missing](why_missing.md) | * <br/> [String](String.md) | Explanation of why each piece of data is missing | direct |
| [id](id.md) | 0..1 <br/> [Uriorcurie](Uriorcurie.md) | An optional identifier for this property | [DatasetProperty](DatasetProperty.md) |
| [name](name.md) | 0..1 <br/> [String](String.md) | A human-readable name for this property | [DatasetProperty](DatasetProperty.md) |
| [description](description.md) | 0..1 <br/> [String](String.md) | A human-readable description for this property | [DatasetProperty](DatasetProperty.md) |
| [used_software](used_software.md) | * <br/> [Software](Software.md) | What software was used as part of this dataset property? | [DatasetProperty](DatasetProperty.md) |





## Usages

| used by | used in | type | used |
| ---  | --- | --- | --- |
| [Instance](Instance.md) | [missing_information](missing_information.md) | range | [MissingInfo](MissingInfo.md) |







## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | data_sheets_schema:MissingInfo |
| native | data_sheets_schema:MissingInfo |






## LinkML Source

<!-- TODO: investigate https://stackoverflow.com/questions/37606292/how-to-create-tabbed-code-blocks-in-mkdocs-or-sphinx -->

### Direct

<details>
```yaml
name: MissingInfo
description: 'Is any information missing from individual instances? (e.g., unavailable
  data)

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
is_a: DatasetProperty
attributes:
  missing:
    name: missing
    description: 'Description of the missing data fields or elements.

      '
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/composition
    rank: 1000
    slot_uri: dcterms:description
    domain_of:
    - MissingInfo
    range: string
    multivalued: true
  why_missing:
    name: why_missing
    description: 'Explanation of why each piece of data is missing.

      '
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/composition
    rank: 1000
    slot_uri: dcterms:description
    domain_of:
    - MissingInfo
    range: string
    multivalued: true

```
</details>

### Induced

<details>
```yaml
name: MissingInfo
description: 'Is any information missing from individual instances? (e.g., unavailable
  data)

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
is_a: DatasetProperty
attributes:
  missing:
    name: missing
    description: 'Description of the missing data fields or elements.

      '
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/composition
    rank: 1000
    slot_uri: dcterms:description
    alias: missing
    owner: MissingInfo
    domain_of:
    - MissingInfo
    range: string
    multivalued: true
  why_missing:
    name: why_missing
    description: 'Explanation of why each piece of data is missing.

      '
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/composition
    rank: 1000
    slot_uri: dcterms:description
    alias: why_missing
    owner: MissingInfo
    domain_of:
    - MissingInfo
    range: string
    multivalued: true
  id:
    name: id
    description: An optional identifier for this property.
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/base
    slot_uri: schema:identifier
    alias: id
    owner: MissingInfo
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
    owner: MissingInfo
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
    owner: MissingInfo
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
    owner: MissingInfo
    domain_of:
    - DatasetProperty
    range: Software
    multivalued: true
    inlined: true
    inlined_as_list: true

```
</details>