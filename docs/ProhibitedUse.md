

# Class: ProhibitedUse 


_Explicit statement of prohibited or forbidden uses for this dataset. Stronger than DiscouragedUse - these are uses that are explicitly not permitted by license, ethics, or policy. Aligns with RO-Crate "Prohibited Uses" field._

__





URI: [data_sheets_schema:ProhibitedUse](https://w3id.org/bridge2ai/data-sheets-schema/ProhibitedUse)





```mermaid
 classDiagram
    class ProhibitedUse
    click ProhibitedUse href "../ProhibitedUse/"
      DatasetProperty <|-- ProhibitedUse
        click DatasetProperty href "../DatasetProperty/"
      
      ProhibitedUse : description
        
      ProhibitedUse : id
        
      ProhibitedUse : name
        
      ProhibitedUse : prohibition_reason
        
      ProhibitedUse : used_software
        
          
    
        
        
        ProhibitedUse --> "*" Software : used_software
        click Software href "../Software/"
    

        
      
```





## Inheritance
* [DatasetProperty](DatasetProperty.md)
    * **ProhibitedUse**



## Slots

| Name | Cardinality and Range | Description | Inheritance |
| ---  | --- | --- | --- |
| [prohibition_reason](prohibition_reason.md) | * <br/> [String](String.md) | Reason why this use is prohibited (e | direct |
| [id](id.md) | 0..1 <br/> [Uriorcurie](Uriorcurie.md) | An optional identifier for this property | [DatasetProperty](DatasetProperty.md) |
| [name](name.md) | 0..1 <br/> [String](String.md) | A human-readable name for this property | [DatasetProperty](DatasetProperty.md) |
| [description](description.md) | 0..1 <br/> [String](String.md) | A human-readable description for this property | [DatasetProperty](DatasetProperty.md) |
| [used_software](used_software.md) | * <br/> [Software](Software.md) | What software was used as part of this dataset property? | [DatasetProperty](DatasetProperty.md) |





## Usages

| used by | used in | type | used |
| ---  | --- | --- | --- |
| [Dataset](Dataset.md) | [prohibited_uses](prohibited_uses.md) | range | [ProhibitedUse](ProhibitedUse.md) |
| [DataSubset](DataSubset.md) | [prohibited_uses](prohibited_uses.md) | range | [ProhibitedUse](ProhibitedUse.md) |







## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | data_sheets_schema:ProhibitedUse |
| native | data_sheets_schema:ProhibitedUse |






## LinkML Source

<!-- TODO: investigate https://stackoverflow.com/questions/37606292/how-to-create-tabbed-code-blocks-in-mkdocs-or-sphinx -->

### Direct

<details>
```yaml
name: ProhibitedUse
description: 'Explicit statement of prohibited or forbidden uses for this dataset.
  Stronger than DiscouragedUse - these are uses that are explicitly not permitted
  by license, ethics, or policy. Aligns with RO-Crate "Prohibited Uses" field.

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
is_a: DatasetProperty
attributes:
  prohibition_reason:
    name: prohibition_reason
    description: Reason why this use is prohibited (e.g., license restriction, ethical
      concern, privacy risk, legal constraint).
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/uses
    rank: 1000
    domain_of:
    - ProhibitedUse
    range: string
    multivalued: true

```
</details>

### Induced

<details>
```yaml
name: ProhibitedUse
description: 'Explicit statement of prohibited or forbidden uses for this dataset.
  Stronger than DiscouragedUse - these are uses that are explicitly not permitted
  by license, ethics, or policy. Aligns with RO-Crate "Prohibited Uses" field.

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
is_a: DatasetProperty
attributes:
  prohibition_reason:
    name: prohibition_reason
    description: Reason why this use is prohibited (e.g., license restriction, ethical
      concern, privacy risk, legal constraint).
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/uses
    rank: 1000
    alias: prohibition_reason
    owner: ProhibitedUse
    domain_of:
    - ProhibitedUse
    range: string
    multivalued: true
  id:
    name: id
    description: An optional identifier for this property.
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/base
    slot_uri: schema:identifier
    alias: id
    owner: ProhibitedUse
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
    owner: ProhibitedUse
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
    owner: ProhibitedUse
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
    owner: ProhibitedUse
    domain_of:
    - DatasetProperty
    range: Software
    multivalued: true
    inlined: true
    inlined_as_list: true

```
</details>