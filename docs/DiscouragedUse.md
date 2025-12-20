

# Class: DiscouragedUse 


_Are there tasks for which the dataset should not be used?_

__





URI: [data_sheets_schema:DiscouragedUse](https://w3id.org/bridge2ai/data-sheets-schema/DiscouragedUse)





```mermaid
 classDiagram
    class DiscouragedUse
    click DiscouragedUse href "../DiscouragedUse/"
      DatasetProperty <|-- DiscouragedUse
        click DatasetProperty href "../DatasetProperty/"
      
      DiscouragedUse : description
        
      DiscouragedUse : discouragement_details
        
      DiscouragedUse : id
        
      DiscouragedUse : name
        
      DiscouragedUse : used_software
        
          
    
        
        
        DiscouragedUse --> "*" Software : used_software
        click Software href "../Software/"
    

        
      
```





## Inheritance
* [DatasetProperty](DatasetProperty.md)
    * **DiscouragedUse**



## Slots

| Name | Cardinality and Range | Description | Inheritance |
| ---  | --- | --- | --- |
| [discouragement_details](discouragement_details.md) | * <br/> [String](String.md) | Details on tasks for which the dataset should not be used | direct |
| [id](id.md) | 0..1 <br/> [Uriorcurie](Uriorcurie.md) | An optional identifier for this property | [DatasetProperty](DatasetProperty.md) |
| [name](name.md) | 0..1 <br/> [String](String.md) | A human-readable name for this property | [DatasetProperty](DatasetProperty.md) |
| [description](description.md) | 0..1 <br/> [String](String.md) | A human-readable description for this property | [DatasetProperty](DatasetProperty.md) |
| [used_software](used_software.md) | * <br/> [Software](Software.md) | What software was used as part of this dataset property? | [DatasetProperty](DatasetProperty.md) |





## Usages

| used by | used in | type | used |
| ---  | --- | --- | --- |
| [Dataset](Dataset.md) | [discouraged_uses](discouraged_uses.md) | range | [DiscouragedUse](DiscouragedUse.md) |
| [DataSubset](DataSubset.md) | [discouraged_uses](discouraged_uses.md) | range | [DiscouragedUse](DiscouragedUse.md) |







## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | data_sheets_schema:DiscouragedUse |
| native | data_sheets_schema:DiscouragedUse |






## LinkML Source

<!-- TODO: investigate https://stackoverflow.com/questions/37606292/how-to-create-tabbed-code-blocks-in-mkdocs-or-sphinx -->

### Direct

<details>
```yaml
name: DiscouragedUse
description: 'Are there tasks for which the dataset should not be used?

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
is_a: DatasetProperty
attributes:
  discouragement_details:
    name: discouragement_details
    description: 'Details on tasks for which the dataset should not be used.

      '
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/uses
    rank: 1000
    slot_uri: dcterms:description
    domain_of:
    - DiscouragedUse
    range: string
    multivalued: true

```
</details>

### Induced

<details>
```yaml
name: DiscouragedUse
description: 'Are there tasks for which the dataset should not be used?

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
is_a: DatasetProperty
attributes:
  discouragement_details:
    name: discouragement_details
    description: 'Details on tasks for which the dataset should not be used.

      '
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/uses
    rank: 1000
    slot_uri: dcterms:description
    alias: discouragement_details
    owner: DiscouragedUse
    domain_of:
    - DiscouragedUse
    range: string
    multivalued: true
  id:
    name: id
    description: An optional identifier for this property.
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/base
    slot_uri: schema:identifier
    alias: id
    owner: DiscouragedUse
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
    owner: DiscouragedUse
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
    owner: DiscouragedUse
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
    owner: DiscouragedUse
    domain_of:
    - DatasetProperty
    range: Software
    multivalued: true
    inlined: true
    inlined_as_list: true

```
</details>