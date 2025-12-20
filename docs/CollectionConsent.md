

# Class: CollectionConsent 


_Did the individuals in question consent to the collection and use of their data? If so, how was consent requested and provided, and what language did individuals consent to?_

__





URI: [data_sheets_schema:CollectionConsent](https://w3id.org/bridge2ai/data-sheets-schema/CollectionConsent)





```mermaid
 classDiagram
    class CollectionConsent
    click CollectionConsent href "../CollectionConsent/"
      DatasetProperty <|-- CollectionConsent
        click DatasetProperty href "../DatasetProperty/"
      
      CollectionConsent : consent_details
        
      CollectionConsent : description
        
      CollectionConsent : id
        
      CollectionConsent : name
        
      CollectionConsent : used_software
        
          
    
        
        
        CollectionConsent --> "*" Software : used_software
        click Software href "../Software/"
    

        
      
```





## Inheritance
* [DatasetProperty](DatasetProperty.md)
    * **CollectionConsent**



## Slots

| Name | Cardinality and Range | Description | Inheritance |
| ---  | --- | --- | --- |
| [consent_details](consent_details.md) | * <br/> [String](String.md) | Details on how consent was requested, provided, and documented | direct |
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
| self | data_sheets_schema:CollectionConsent |
| native | data_sheets_schema:CollectionConsent |






## LinkML Source

<!-- TODO: investigate https://stackoverflow.com/questions/37606292/how-to-create-tabbed-code-blocks-in-mkdocs-or-sphinx -->

### Direct

<details>
```yaml
name: CollectionConsent
description: 'Did the individuals in question consent to the collection and use of
  their data? If so, how was consent requested and provided, and what language did
  individuals consent to?

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
is_a: DatasetProperty
attributes:
  consent_details:
    name: consent_details
    description: 'Details on how consent was requested, provided, and documented.

      '
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/ethics
    rank: 1000
    slot_uri: dcterms:description
    domain_of:
    - CollectionConsent
    range: string
    multivalued: true

```
</details>

### Induced

<details>
```yaml
name: CollectionConsent
description: 'Did the individuals in question consent to the collection and use of
  their data? If so, how was consent requested and provided, and what language did
  individuals consent to?

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
is_a: DatasetProperty
attributes:
  consent_details:
    name: consent_details
    description: 'Details on how consent was requested, provided, and documented.

      '
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/ethics
    rank: 1000
    slot_uri: dcterms:description
    alias: consent_details
    owner: CollectionConsent
    domain_of:
    - CollectionConsent
    range: string
    multivalued: true
  id:
    name: id
    description: An optional identifier for this property.
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/base
    slot_uri: schema:identifier
    alias: id
    owner: CollectionConsent
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
    owner: CollectionConsent
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
    owner: CollectionConsent
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
    owner: CollectionConsent
    domain_of:
    - DatasetProperty
    range: Software
    multivalued: true
    inlined: true
    inlined_as_list: true

```
</details>