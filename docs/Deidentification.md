

# Class: Deidentification 


_Is it possible to identify individuals in the dataset, either directly or indirectly (in combination with other data)?_

__





URI: [data_sheets_schema:Deidentification](https://w3id.org/bridge2ai/data-sheets-schema/Deidentification)





```mermaid
 classDiagram
    class Deidentification
    click Deidentification href "../Deidentification/"
      DatasetProperty <|-- Deidentification
        click DatasetProperty href "../DatasetProperty/"
      
      Deidentification : deidentification_details
        
      Deidentification : description
        
      Deidentification : id
        
      Deidentification : identifiable_elements_present
        
      Deidentification : identifiers_removed
        
      Deidentification : method
        
      Deidentification : name
        
      Deidentification : used_software
        
          
    
        
        
        Deidentification --> "*" Software : used_software
        click Software href "../Software/"
    

        
      
```





## Inheritance
* [DatasetProperty](DatasetProperty.md)
    * **Deidentification**



## Slots

| Name | Cardinality and Range | Description | Inheritance |
| ---  | --- | --- | --- |
| [identifiable_elements_present](identifiable_elements_present.md) | 0..1 <br/> [Boolean](Boolean.md) | Indicates whether data subjects can be identified | direct |
| [method](method.md) | 0..1 <br/> [String](String.md) | Method used for de-identification (e | direct |
| [identifiers_removed](identifiers_removed.md) | * <br/> [String](String.md) | List of identifier types removed during de-identification | direct |
| [deidentification_details](deidentification_details.md) | * <br/> [String](String.md) | Details on de-identification procedures and residual risks | direct |
| [id](id.md) | 0..1 <br/> [Uriorcurie](Uriorcurie.md) | An optional identifier for this property | [DatasetProperty](DatasetProperty.md) |
| [name](name.md) | 0..1 <br/> [String](String.md) | A human-readable name for this property | [DatasetProperty](DatasetProperty.md) |
| [description](description.md) | 0..1 <br/> [String](String.md) | A human-readable description for this property | [DatasetProperty](DatasetProperty.md) |
| [used_software](used_software.md) | * <br/> [Software](Software.md) | What software was used as part of this dataset property? | [DatasetProperty](DatasetProperty.md) |





## Usages

| used by | used in | type | used |
| ---  | --- | --- | --- |
| [Dataset](Dataset.md) | [is_deidentified](is_deidentified.md) | range | [Deidentification](Deidentification.md) |
| [DataSubset](DataSubset.md) | [is_deidentified](is_deidentified.md) | range | [Deidentification](Deidentification.md) |







## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | data_sheets_schema:Deidentification |
| native | data_sheets_schema:Deidentification |






## LinkML Source

<!-- TODO: investigate https://stackoverflow.com/questions/37606292/how-to-create-tabbed-code-blocks-in-mkdocs-or-sphinx -->

### Direct

<details>
```yaml
name: Deidentification
description: 'Is it possible to identify individuals in the dataset, either directly
  or indirectly (in combination with other data)?

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
is_a: DatasetProperty
attributes:
  identifiable_elements_present:
    name: identifiable_elements_present
    description: Indicates whether data subjects can be identified.
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/composition
    rank: 1000
    domain_of:
    - Deidentification
    range: boolean
  method:
    name: method
    description: Method used for de-identification (e.g., HIPAA Safe Harbor).
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/composition
    rank: 1000
    domain_of:
    - Deidentification
    range: string
  identifiers_removed:
    name: identifiers_removed
    description: List of identifier types removed during de-identification.
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/composition
    rank: 1000
    domain_of:
    - Deidentification
    range: string
    multivalued: true
  deidentification_details:
    name: deidentification_details
    description: 'Details on de-identification procedures and residual risks.

      '
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/composition
    rank: 1000
    slot_uri: dcterms:description
    domain_of:
    - Deidentification
    range: string
    multivalued: true

```
</details>

### Induced

<details>
```yaml
name: Deidentification
description: 'Is it possible to identify individuals in the dataset, either directly
  or indirectly (in combination with other data)?

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
is_a: DatasetProperty
attributes:
  identifiable_elements_present:
    name: identifiable_elements_present
    description: Indicates whether data subjects can be identified.
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/composition
    rank: 1000
    alias: identifiable_elements_present
    owner: Deidentification
    domain_of:
    - Deidentification
    range: boolean
  method:
    name: method
    description: Method used for de-identification (e.g., HIPAA Safe Harbor).
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/composition
    rank: 1000
    alias: method
    owner: Deidentification
    domain_of:
    - Deidentification
    range: string
  identifiers_removed:
    name: identifiers_removed
    description: List of identifier types removed during de-identification.
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/composition
    rank: 1000
    alias: identifiers_removed
    owner: Deidentification
    domain_of:
    - Deidentification
    range: string
    multivalued: true
  deidentification_details:
    name: deidentification_details
    description: 'Details on de-identification procedures and residual risks.

      '
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/composition
    rank: 1000
    slot_uri: dcterms:description
    alias: deidentification_details
    owner: Deidentification
    domain_of:
    - Deidentification
    range: string
    multivalued: true
  id:
    name: id
    description: An optional identifier for this property.
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/base
    slot_uri: schema:identifier
    alias: id
    owner: Deidentification
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
    owner: Deidentification
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
    owner: Deidentification
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
    owner: Deidentification
    domain_of:
    - DatasetProperty
    range: Software
    multivalued: true
    inlined: true
    inlined_as_list: true

```
</details>