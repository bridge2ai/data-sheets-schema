

# Class: OtherTask 


_What other tasks could the dataset be used for?_

__





URI: [data_sheets_schema:OtherTask](https://w3id.org/bridge2ai/data-sheets-schema/OtherTask)





```mermaid
 classDiagram
    class OtherTask
    click OtherTask href "../OtherTask/"
      DatasetProperty <|-- OtherTask
        click DatasetProperty href "../DatasetProperty/"
      
      OtherTask : description
        
      OtherTask : id
        
      OtherTask : name
        
      OtherTask : task_details
        
      OtherTask : used_software
        
          
    
        
        
        OtherTask --> "*" Software : used_software
        click Software href "../Software/"
    

        
      
```





## Inheritance
* [DatasetProperty](DatasetProperty.md)
    * **OtherTask**



## Slots

| Name | Cardinality and Range | Description | Inheritance |
| ---  | --- | --- | --- |
| [task_details](task_details.md) | * <br/> [String](String.md) | Details on other potential tasks the dataset could be used for | direct |
| [id](id.md) | 0..1 <br/> [Uriorcurie](Uriorcurie.md) | An optional identifier for this property | [DatasetProperty](DatasetProperty.md) |
| [name](name.md) | 0..1 <br/> [String](String.md) | A human-readable name for this property | [DatasetProperty](DatasetProperty.md) |
| [description](description.md) | 0..1 <br/> [String](String.md) | A human-readable description for this property | [DatasetProperty](DatasetProperty.md) |
| [used_software](used_software.md) | * <br/> [Software](Software.md) | What software was used as part of this dataset property? | [DatasetProperty](DatasetProperty.md) |





## Usages

| used by | used in | type | used |
| ---  | --- | --- | --- |
| [Dataset](Dataset.md) | [other_tasks](other_tasks.md) | range | [OtherTask](OtherTask.md) |
| [DataSubset](DataSubset.md) | [other_tasks](other_tasks.md) | range | [OtherTask](OtherTask.md) |







## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | data_sheets_schema:OtherTask |
| native | data_sheets_schema:OtherTask |






## LinkML Source

<!-- TODO: investigate https://stackoverflow.com/questions/37606292/how-to-create-tabbed-code-blocks-in-mkdocs-or-sphinx -->

### Direct

<details>
```yaml
name: OtherTask
description: 'What other tasks could the dataset be used for?

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
is_a: DatasetProperty
attributes:
  task_details:
    name: task_details
    description: 'Details on other potential tasks the dataset could be used for.

      '
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/uses
    rank: 1000
    slot_uri: dcterms:description
    domain_of:
    - OtherTask
    range: string
    multivalued: true

```
</details>

### Induced

<details>
```yaml
name: OtherTask
description: 'What other tasks could the dataset be used for?

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
is_a: DatasetProperty
attributes:
  task_details:
    name: task_details
    description: 'Details on other potential tasks the dataset could be used for.

      '
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/uses
    rank: 1000
    slot_uri: dcterms:description
    alias: task_details
    owner: OtherTask
    domain_of:
    - OtherTask
    range: string
    multivalued: true
  id:
    name: id
    description: An optional identifier for this property.
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/base
    slot_uri: schema:identifier
    alias: id
    owner: OtherTask
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
    owner: OtherTask
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
    owner: OtherTask
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
    owner: OtherTask
    domain_of:
    - DatasetProperty
    range: Software
    multivalued: true
    inlined: true
    inlined_as_list: true

```
</details>