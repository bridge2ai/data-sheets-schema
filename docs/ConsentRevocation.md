

# Class: ConsentRevocation 


_If consent was obtained, were the consenting individuals provided with a mechanism to revoke their consent in the future or for certain uses? If so, please describe._

__





URI: [data_sheets_schema:ConsentRevocation](https://w3id.org/bridge2ai/data-sheets-schema/ConsentRevocation)





```mermaid
 classDiagram
    class ConsentRevocation
    click ConsentRevocation href "../ConsentRevocation/"
      DatasetProperty <|-- ConsentRevocation
        click DatasetProperty href "../DatasetProperty/"
      
      ConsentRevocation : description
        
      ConsentRevocation : id
        
      ConsentRevocation : name
        
      ConsentRevocation : revocation_details
        
      ConsentRevocation : used_software
        
          
    
        
        
        ConsentRevocation --> "*" Software : used_software
        click Software href "../Software/"
    

        
      
```





## Inheritance
* [DatasetProperty](DatasetProperty.md)
    * **ConsentRevocation**



## Slots

| Name | Cardinality and Range | Description | Inheritance |
| ---  | --- | --- | --- |
| [revocation_details](revocation_details.md) | * <br/> [String](String.md) | Details on consent revocation mechanisms and procedures | direct |
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
| self | data_sheets_schema:ConsentRevocation |
| native | data_sheets_schema:ConsentRevocation |






## LinkML Source

<!-- TODO: investigate https://stackoverflow.com/questions/37606292/how-to-create-tabbed-code-blocks-in-mkdocs-or-sphinx -->

### Direct

<details>
```yaml
name: ConsentRevocation
description: 'If consent was obtained, were the consenting individuals provided with
  a mechanism to revoke their consent in the future or for certain uses? If so, please
  describe.

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
is_a: DatasetProperty
attributes:
  revocation_details:
    name: revocation_details
    description: 'Details on consent revocation mechanisms and procedures.

      '
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/ethics
    rank: 1000
    slot_uri: dcterms:description
    domain_of:
    - ConsentRevocation
    range: string
    multivalued: true

```
</details>

### Induced

<details>
```yaml
name: ConsentRevocation
description: 'If consent was obtained, were the consenting individuals provided with
  a mechanism to revoke their consent in the future or for certain uses? If so, please
  describe.

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
is_a: DatasetProperty
attributes:
  revocation_details:
    name: revocation_details
    description: 'Details on consent revocation mechanisms and procedures.

      '
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/ethics
    rank: 1000
    slot_uri: dcterms:description
    alias: revocation_details
    owner: ConsentRevocation
    domain_of:
    - ConsentRevocation
    range: string
    multivalued: true
  id:
    name: id
    description: An optional identifier for this property.
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/base
    slot_uri: schema:identifier
    alias: id
    owner: ConsentRevocation
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
    owner: ConsentRevocation
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
    owner: ConsentRevocation
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
    owner: ConsentRevocation
    domain_of:
    - DatasetProperty
    range: Software
    multivalued: true
    inlined: true
    inlined_as_list: true

```
</details>