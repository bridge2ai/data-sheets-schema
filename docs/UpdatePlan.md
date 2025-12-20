

# Class: UpdatePlan 


_Will the dataset be updated (e.g., to correct labeling errors, add new instances, delete instances)? If so, how often, by whom, and how will these updates be communicated?_

__





URI: [data_sheets_schema:UpdatePlan](https://w3id.org/bridge2ai/data-sheets-schema/UpdatePlan)





```mermaid
 classDiagram
    class UpdatePlan
    click UpdatePlan href "../UpdatePlan/"
      DatasetProperty <|-- UpdatePlan
        click DatasetProperty href "../DatasetProperty/"
      
      UpdatePlan : description
        
      UpdatePlan : frequency
        
      UpdatePlan : id
        
      UpdatePlan : name
        
      UpdatePlan : update_details
        
      UpdatePlan : used_software
        
          
    
        
        
        UpdatePlan --> "*" Software : used_software
        click Software href "../Software/"
    

        
      
```





## Inheritance
* [DatasetProperty](DatasetProperty.md)
    * **UpdatePlan**



## Slots

| Name | Cardinality and Range | Description | Inheritance |
| ---  | --- | --- | --- |
| [frequency](frequency.md) | 0..1 <br/> [String](String.md) | How often updates are planned (e | direct |
| [update_details](update_details.md) | * <br/> [String](String.md) | Details on update plans, responsible parties, and communication methods | direct |
| [id](id.md) | 0..1 <br/> [Uriorcurie](Uriorcurie.md) | An optional identifier for this property | [DatasetProperty](DatasetProperty.md) |
| [name](name.md) | 0..1 <br/> [String](String.md) | A human-readable name for this property | [DatasetProperty](DatasetProperty.md) |
| [description](description.md) | 0..1 <br/> [String](String.md) | A human-readable description for this property | [DatasetProperty](DatasetProperty.md) |
| [used_software](used_software.md) | * <br/> [Software](Software.md) | What software was used as part of this dataset property? | [DatasetProperty](DatasetProperty.md) |





## Usages

| used by | used in | type | used |
| ---  | --- | --- | --- |
| [Dataset](Dataset.md) | [updates](updates.md) | range | [UpdatePlan](UpdatePlan.md) |
| [DataSubset](DataSubset.md) | [updates](updates.md) | range | [UpdatePlan](UpdatePlan.md) |







## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | data_sheets_schema:UpdatePlan |
| native | data_sheets_schema:UpdatePlan |
| exact | rai:dataReleaseMaintenancePlan |






## LinkML Source

<!-- TODO: investigate https://stackoverflow.com/questions/37606292/how-to-create-tabbed-code-blocks-in-mkdocs-or-sphinx -->

### Direct

<details>
```yaml
name: UpdatePlan
description: 'Will the dataset be updated (e.g., to correct labeling errors, add new
  instances, delete instances)? If so, how often, by whom, and how will these updates
  be communicated?

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
exact_mappings:
- rai:dataReleaseMaintenancePlan
is_a: DatasetProperty
attributes:
  frequency:
    name: frequency
    description: How often updates are planned (e.g., quarterly, annually).
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/maintenance
    rank: 1000
    domain_of:
    - UpdatePlan
    range: string
  update_details:
    name: update_details
    description: 'Details on update plans, responsible parties, and communication
      methods.

      '
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/maintenance
    rank: 1000
    slot_uri: dcterms:description
    domain_of:
    - UpdatePlan
    range: string
    multivalued: true

```
</details>

### Induced

<details>
```yaml
name: UpdatePlan
description: 'Will the dataset be updated (e.g., to correct labeling errors, add new
  instances, delete instances)? If so, how often, by whom, and how will these updates
  be communicated?

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
exact_mappings:
- rai:dataReleaseMaintenancePlan
is_a: DatasetProperty
attributes:
  frequency:
    name: frequency
    description: How often updates are planned (e.g., quarterly, annually).
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/maintenance
    rank: 1000
    alias: frequency
    owner: UpdatePlan
    domain_of:
    - UpdatePlan
    range: string
  update_details:
    name: update_details
    description: 'Details on update plans, responsible parties, and communication
      methods.

      '
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/maintenance
    rank: 1000
    slot_uri: dcterms:description
    alias: update_details
    owner: UpdatePlan
    domain_of:
    - UpdatePlan
    range: string
    multivalued: true
  id:
    name: id
    description: An optional identifier for this property.
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/base
    slot_uri: schema:identifier
    alias: id
    owner: UpdatePlan
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
    owner: UpdatePlan
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
    owner: UpdatePlan
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
    owner: UpdatePlan
    domain_of:
    - DatasetProperty
    range: Software
    multivalued: true
    inlined: true
    inlined_as_list: true

```
</details>