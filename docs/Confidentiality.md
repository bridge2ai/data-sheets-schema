

# Class: Confidentiality 


_Does the dataset contain data that might be confidential (e.g., protected by legal privilege, patient data, non-public communications)?_

__





URI: [data_sheets_schema:Confidentiality](https://w3id.org/bridge2ai/data-sheets-schema/Confidentiality)





```mermaid
 classDiagram
    class Confidentiality
    click Confidentiality href "../Confidentiality/"
      DatasetProperty <|-- Confidentiality
        click DatasetProperty href "../DatasetProperty/"
      
      Confidentiality : confidential_elements_present
        
      Confidentiality : confidentiality_details
        
      Confidentiality : description
        
      Confidentiality : id
        
      Confidentiality : name
        
      Confidentiality : used_software
        
          
    
        
        
        Confidentiality --> "*" Software : used_software
        click Software href "../Software/"
    

        
      
```





## Inheritance
* [DatasetProperty](DatasetProperty.md)
    * **Confidentiality**



## Slots

| Name | Cardinality and Range | Description | Inheritance |
| ---  | --- | --- | --- |
| [confidential_elements_present](confidential_elements_present.md) | 0..1 <br/> [Boolean](Boolean.md) | Indicates whether any confidential data elements are present | direct |
| [confidentiality_details](confidentiality_details.md) | * <br/> [String](String.md) | Details on confidential data elements and handling procedures | direct |
| [id](id.md) | 0..1 <br/> [Uriorcurie](Uriorcurie.md) | An optional identifier for this property | [DatasetProperty](DatasetProperty.md) |
| [name](name.md) | 0..1 <br/> [String](String.md) | A human-readable name for this property | [DatasetProperty](DatasetProperty.md) |
| [description](description.md) | 0..1 <br/> [String](String.md) | A human-readable description for this property | [DatasetProperty](DatasetProperty.md) |
| [used_software](used_software.md) | * <br/> [Software](Software.md) | What software was used as part of this dataset property? | [DatasetProperty](DatasetProperty.md) |





## Usages

| used by | used in | type | used |
| ---  | --- | --- | --- |
| [Dataset](Dataset.md) | [confidential_elements](confidential_elements.md) | range | [Confidentiality](Confidentiality.md) |
| [DataSubset](DataSubset.md) | [confidential_elements](confidential_elements.md) | range | [Confidentiality](Confidentiality.md) |







## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | data_sheets_schema:Confidentiality |
| native | data_sheets_schema:Confidentiality |






## LinkML Source

<!-- TODO: investigate https://stackoverflow.com/questions/37606292/how-to-create-tabbed-code-blocks-in-mkdocs-or-sphinx -->

### Direct

<details>
```yaml
name: Confidentiality
description: 'Does the dataset contain data that might be confidential (e.g., protected
  by legal privilege, patient data, non-public communications)?

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
is_a: DatasetProperty
attributes:
  confidential_elements_present:
    name: confidential_elements_present
    description: Indicates whether any confidential data elements are present.
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/composition
    rank: 1000
    domain_of:
    - Confidentiality
    range: boolean
  confidentiality_details:
    name: confidentiality_details
    description: 'Details on confidential data elements and handling procedures.

      '
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/composition
    rank: 1000
    slot_uri: dcterms:description
    domain_of:
    - Confidentiality
    range: string
    multivalued: true

```
</details>

### Induced

<details>
```yaml
name: Confidentiality
description: 'Does the dataset contain data that might be confidential (e.g., protected
  by legal privilege, patient data, non-public communications)?

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
is_a: DatasetProperty
attributes:
  confidential_elements_present:
    name: confidential_elements_present
    description: Indicates whether any confidential data elements are present.
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/composition
    rank: 1000
    alias: confidential_elements_present
    owner: Confidentiality
    domain_of:
    - Confidentiality
    range: boolean
  confidentiality_details:
    name: confidentiality_details
    description: 'Details on confidential data elements and handling procedures.

      '
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/composition
    rank: 1000
    slot_uri: dcterms:description
    alias: confidentiality_details
    owner: Confidentiality
    domain_of:
    - Confidentiality
    range: string
    multivalued: true
  id:
    name: id
    description: An optional identifier for this property.
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/base
    slot_uri: schema:identifier
    alias: id
    owner: Confidentiality
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
    owner: Confidentiality
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
    owner: Confidentiality
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
    owner: Confidentiality
    domain_of:
    - DatasetProperty
    range: Software
    multivalued: true
    inlined: true
    inlined_as_list: true

```
</details>