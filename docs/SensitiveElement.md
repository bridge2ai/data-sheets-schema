

# Class: SensitiveElement 


_Does the dataset contain data that might be considered sensitive (e.g., race, sexual orientation, religion, biometrics)?_

__





URI: [data_sheets_schema:SensitiveElement](https://w3id.org/bridge2ai/data-sheets-schema/SensitiveElement)





```mermaid
 classDiagram
    class SensitiveElement
    click SensitiveElement href "../SensitiveElement/"
      DatasetProperty <|-- SensitiveElement
        click DatasetProperty href "../DatasetProperty/"
      
      SensitiveElement : description
        
      SensitiveElement : id
        
      SensitiveElement : name
        
      SensitiveElement : sensitive_elements_present
        
      SensitiveElement : sensitivity_details
        
      SensitiveElement : used_software
        
          
    
        
        
        SensitiveElement --> "*" Software : used_software
        click Software href "../Software/"
    

        
      
```





## Inheritance
* [DatasetProperty](DatasetProperty.md)
    * **SensitiveElement**



## Slots

| Name | Cardinality and Range | Description | Inheritance |
| ---  | --- | --- | --- |
| [sensitive_elements_present](sensitive_elements_present.md) | 0..1 <br/> [Boolean](Boolean.md) | Indicates whether sensitive data elements are present | direct |
| [sensitivity_details](sensitivity_details.md) | * <br/> [String](String.md) | Details on sensitive data elements present and handling procedures | direct |
| [id](id.md) | 0..1 <br/> [Uriorcurie](Uriorcurie.md) | An optional identifier for this property | [DatasetProperty](DatasetProperty.md) |
| [name](name.md) | 0..1 <br/> [String](String.md) | A human-readable name for this property | [DatasetProperty](DatasetProperty.md) |
| [description](description.md) | 0..1 <br/> [String](String.md) | A human-readable description for this property | [DatasetProperty](DatasetProperty.md) |
| [used_software](used_software.md) | * <br/> [Software](Software.md) | What software was used as part of this dataset property? | [DatasetProperty](DatasetProperty.md) |





## Usages

| used by | used in | type | used |
| ---  | --- | --- | --- |
| [Dataset](Dataset.md) | [sensitive_elements](sensitive_elements.md) | range | [SensitiveElement](SensitiveElement.md) |
| [DataSubset](DataSubset.md) | [sensitive_elements](sensitive_elements.md) | range | [SensitiveElement](SensitiveElement.md) |







## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | data_sheets_schema:SensitiveElement |
| native | data_sheets_schema:SensitiveElement |
| exact | rai:personalSensitiveInformation |






## LinkML Source

<!-- TODO: investigate https://stackoverflow.com/questions/37606292/how-to-create-tabbed-code-blocks-in-mkdocs-or-sphinx -->

### Direct

<details>
```yaml
name: SensitiveElement
description: 'Does the dataset contain data that might be considered sensitive (e.g.,
  race, sexual orientation, religion, biometrics)?

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
exact_mappings:
- rai:personalSensitiveInformation
is_a: DatasetProperty
attributes:
  sensitive_elements_present:
    name: sensitive_elements_present
    description: Indicates whether sensitive data elements are present.
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/composition
    rank: 1000
    domain_of:
    - SensitiveElement
    range: boolean
  sensitivity_details:
    name: sensitivity_details
    description: 'Details on sensitive data elements present and handling procedures.

      '
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/composition
    rank: 1000
    slot_uri: dcterms:description
    domain_of:
    - SensitiveElement
    range: string
    multivalued: true

```
</details>

### Induced

<details>
```yaml
name: SensitiveElement
description: 'Does the dataset contain data that might be considered sensitive (e.g.,
  race, sexual orientation, religion, biometrics)?

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
exact_mappings:
- rai:personalSensitiveInformation
is_a: DatasetProperty
attributes:
  sensitive_elements_present:
    name: sensitive_elements_present
    description: Indicates whether sensitive data elements are present.
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/composition
    rank: 1000
    alias: sensitive_elements_present
    owner: SensitiveElement
    domain_of:
    - SensitiveElement
    range: boolean
  sensitivity_details:
    name: sensitivity_details
    description: 'Details on sensitive data elements present and handling procedures.

      '
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/composition
    rank: 1000
    slot_uri: dcterms:description
    alias: sensitivity_details
    owner: SensitiveElement
    domain_of:
    - SensitiveElement
    range: string
    multivalued: true
  id:
    name: id
    description: An optional identifier for this property.
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/base
    slot_uri: schema:identifier
    alias: id
    owner: SensitiveElement
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
    owner: SensitiveElement
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
    owner: SensitiveElement
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
    owner: SensitiveElement
    domain_of:
    - DatasetProperty
    range: Software
    multivalued: true
    inlined: true
    inlined_as_list: true

```
</details>