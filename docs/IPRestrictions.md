

# Class: IPRestrictions 


_Have any third parties imposed IP-based or other restrictions on the data associated with the instances? If so, describe them and note any relevant fees or licensing terms. Maps to DUO terms related to commercial/non-profit use restrictions (NCU, NPU, NPUNCU)._

__





URI: [data_sheets_schema:IPRestrictions](https://w3id.org/bridge2ai/data-sheets-schema/IPRestrictions)





```mermaid
 classDiagram
    class IPRestrictions
    click IPRestrictions href "../IPRestrictions/"
      DatasetProperty <|-- IPRestrictions
        click DatasetProperty href "../DatasetProperty/"
      
      IPRestrictions : description
        
      IPRestrictions : id
        
      IPRestrictions : name
        
      IPRestrictions : restrictions
        
      IPRestrictions : used_software
        
          
    
        
        
        IPRestrictions --> "*" Software : used_software
        click Software href "../Software/"
    

        
      
```





## Inheritance
* [DatasetProperty](DatasetProperty.md)
    * **IPRestrictions**



## Slots

| Name | Cardinality and Range | Description | Inheritance |
| ---  | --- | --- | --- |
| [restrictions](restrictions.md) | * <br/> [String](String.md) | Explanation of third-party IP restrictions | direct |
| [id](id.md) | 0..1 <br/> [Uriorcurie](Uriorcurie.md) | An optional identifier for this property | [DatasetProperty](DatasetProperty.md) |
| [name](name.md) | 0..1 <br/> [String](String.md) | A human-readable name for this property | [DatasetProperty](DatasetProperty.md) |
| [description](description.md) | 0..1 <br/> [String](String.md) | A human-readable description for this property | [DatasetProperty](DatasetProperty.md) |
| [used_software](used_software.md) | * <br/> [Software](Software.md) | What software was used as part of this dataset property? | [DatasetProperty](DatasetProperty.md) |





## Usages

| used by | used in | type | used |
| ---  | --- | --- | --- |
| [Dataset](Dataset.md) | [ip_restrictions](ip_restrictions.md) | range | [IPRestrictions](IPRestrictions.md) |
| [DataSubset](DataSubset.md) | [ip_restrictions](ip_restrictions.md) | range | [IPRestrictions](IPRestrictions.md) |







## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | data_sheets_schema:IPRestrictions |
| native | data_sheets_schema:IPRestrictions |






## LinkML Source

<!-- TODO: investigate https://stackoverflow.com/questions/37606292/how-to-create-tabbed-code-blocks-in-mkdocs-or-sphinx -->

### Direct

<details>
```yaml
name: IPRestrictions
description: 'Have any third parties imposed IP-based or other restrictions on the
  data associated with the instances? If so, describe them and note any relevant fees
  or licensing terms. Maps to DUO terms related to commercial/non-profit use restrictions
  (NCU, NPU, NPUNCU).

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
is_a: DatasetProperty
attributes:
  restrictions:
    name: restrictions
    description: Explanation of third-party IP restrictions.
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/data-governance
    broad_mappings:
    - DUO:0000046
    - DUO:0000045
    slot_uri: dcterms:rights
    domain_of:
    - ExternalResource
    - IPRestrictions
    range: string
    multivalued: true

```
</details>

### Induced

<details>
```yaml
name: IPRestrictions
description: 'Have any third parties imposed IP-based or other restrictions on the
  data associated with the instances? If so, describe them and note any relevant fees
  or licensing terms. Maps to DUO terms related to commercial/non-profit use restrictions
  (NCU, NPU, NPUNCU).

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
is_a: DatasetProperty
attributes:
  restrictions:
    name: restrictions
    description: Explanation of third-party IP restrictions.
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/data-governance
    broad_mappings:
    - DUO:0000046
    - DUO:0000045
    slot_uri: dcterms:rights
    alias: restrictions
    owner: IPRestrictions
    domain_of:
    - ExternalResource
    - IPRestrictions
    range: string
    multivalued: true
  id:
    name: id
    description: An optional identifier for this property.
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/base
    slot_uri: schema:identifier
    alias: id
    owner: IPRestrictions
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
    owner: IPRestrictions
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
    owner: IPRestrictions
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
    owner: IPRestrictions
    domain_of:
    - DatasetProperty
    range: Software
    multivalued: true
    inlined: true
    inlined_as_list: true

```
</details>