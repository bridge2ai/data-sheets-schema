

# Class: InformedConsent 


_Details about informed consent procedures used in human subjects research._

__





URI: [data_sheets_schema:InformedConsent](https://w3id.org/bridge2ai/data-sheets-schema/InformedConsent)





```mermaid
 classDiagram
    class InformedConsent
    click InformedConsent href "../InformedConsent/"
      DatasetProperty <|-- InformedConsent
        click DatasetProperty href "../DatasetProperty/"
      
      InformedConsent : consent_documentation
        
      InformedConsent : consent_obtained
        
      InformedConsent : consent_scope
        
      InformedConsent : consent_type
        
      InformedConsent : description
        
      InformedConsent : id
        
      InformedConsent : name
        
      InformedConsent : used_software
        
          
    
        
        
        InformedConsent --> "*" Software : used_software
        click Software href "../Software/"
    

        
      InformedConsent : withdrawal_mechanism
        
      
```





## Inheritance
* [DatasetProperty](DatasetProperty.md)
    * **InformedConsent**



## Slots

| Name | Cardinality and Range | Description | Inheritance |
| ---  | --- | --- | --- |
| [consent_obtained](consent_obtained.md) | 0..1 <br/> [Boolean](Boolean.md) | Was informed consent obtained from all participants? | direct |
| [consent_type](consent_type.md) | * <br/> [String](String.md) | What type of consent was obtained (e | direct |
| [consent_documentation](consent_documentation.md) | * <br/> [String](String.md) | How is consent documented? Include references to consent forms or procedures ... | direct |
| [withdrawal_mechanism](withdrawal_mechanism.md) | * <br/> [String](String.md) | How can participants withdraw their consent? What procedures are in place for... | direct |
| [consent_scope](consent_scope.md) | * <br/> [String](String.md) | What specific uses did participants consent to? Are there limitations on data... | direct |
| [id](id.md) | 0..1 <br/> [Uriorcurie](Uriorcurie.md) | An optional identifier for this property | [DatasetProperty](DatasetProperty.md) |
| [name](name.md) | 0..1 <br/> [String](String.md) | A human-readable name for this property | [DatasetProperty](DatasetProperty.md) |
| [description](description.md) | 0..1 <br/> [String](String.md) | A human-readable description for this property | [DatasetProperty](DatasetProperty.md) |
| [used_software](used_software.md) | * <br/> [Software](Software.md) | What software was used as part of this dataset property? | [DatasetProperty](DatasetProperty.md) |





## Usages

| used by | used in | type | used |
| ---  | --- | --- | --- |
| [Dataset](Dataset.md) | [informed_consent](informed_consent.md) | range | [InformedConsent](InformedConsent.md) |
| [DataSubset](DataSubset.md) | [informed_consent](informed_consent.md) | range | [InformedConsent](InformedConsent.md) |







## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | data_sheets_schema:InformedConsent |
| native | data_sheets_schema:InformedConsent |






## LinkML Source

<!-- TODO: investigate https://stackoverflow.com/questions/37606292/how-to-create-tabbed-code-blocks-in-mkdocs-or-sphinx -->

### Direct

<details>
```yaml
name: InformedConsent
description: 'Details about informed consent procedures used in human subjects research.

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
is_a: DatasetProperty
attributes:
  consent_obtained:
    name: consent_obtained
    description: Was informed consent obtained from all participants?
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/human
    rank: 1000
    domain_of:
    - InformedConsent
    range: boolean
  consent_type:
    name: consent_type
    description: 'What type of consent was obtained (e.g., written, verbal, electronic,
      implied through participation)?

      '
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/human
    rank: 1000
    domain_of:
    - InformedConsent
    range: string
    multivalued: true
  consent_documentation:
    name: consent_documentation
    description: 'How is consent documented? Include references to consent forms or
      procedures used.

      '
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/human
    rank: 1000
    domain_of:
    - InformedConsent
    range: string
    multivalued: true
  withdrawal_mechanism:
    name: withdrawal_mechanism
    description: 'How can participants withdraw their consent? What procedures are
      in place for data deletion upon withdrawal?

      '
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/human
    rank: 1000
    domain_of:
    - InformedConsent
    range: string
    multivalued: true
  consent_scope:
    name: consent_scope
    description: 'What specific uses did participants consent to? Are there limitations
      on data use based on consent?

      '
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/human
    rank: 1000
    domain_of:
    - InformedConsent
    range: string
    multivalued: true

```
</details>

### Induced

<details>
```yaml
name: InformedConsent
description: 'Details about informed consent procedures used in human subjects research.

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
is_a: DatasetProperty
attributes:
  consent_obtained:
    name: consent_obtained
    description: Was informed consent obtained from all participants?
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/human
    rank: 1000
    alias: consent_obtained
    owner: InformedConsent
    domain_of:
    - InformedConsent
    range: boolean
  consent_type:
    name: consent_type
    description: 'What type of consent was obtained (e.g., written, verbal, electronic,
      implied through participation)?

      '
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/human
    rank: 1000
    alias: consent_type
    owner: InformedConsent
    domain_of:
    - InformedConsent
    range: string
    multivalued: true
  consent_documentation:
    name: consent_documentation
    description: 'How is consent documented? Include references to consent forms or
      procedures used.

      '
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/human
    rank: 1000
    alias: consent_documentation
    owner: InformedConsent
    domain_of:
    - InformedConsent
    range: string
    multivalued: true
  withdrawal_mechanism:
    name: withdrawal_mechanism
    description: 'How can participants withdraw their consent? What procedures are
      in place for data deletion upon withdrawal?

      '
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/human
    rank: 1000
    alias: withdrawal_mechanism
    owner: InformedConsent
    domain_of:
    - InformedConsent
    range: string
    multivalued: true
  consent_scope:
    name: consent_scope
    description: 'What specific uses did participants consent to? Are there limitations
      on data use based on consent?

      '
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/human
    rank: 1000
    alias: consent_scope
    owner: InformedConsent
    domain_of:
    - InformedConsent
    range: string
    multivalued: true
  id:
    name: id
    description: An optional identifier for this property.
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/base
    slot_uri: schema:identifier
    alias: id
    owner: InformedConsent
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
    owner: InformedConsent
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
    owner: InformedConsent
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
    owner: InformedConsent
    domain_of:
    - DatasetProperty
    range: Software
    multivalued: true
    inlined: true
    inlined_as_list: true

```
</details>