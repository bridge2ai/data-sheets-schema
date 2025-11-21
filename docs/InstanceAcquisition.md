

# Class: InstanceAcquisition 


_Describes how data associated with each instance was acquired  (e.g., directly observed, reported by subjects, inferred)._

__





URI: [data_sheets_schema:InstanceAcquisition](https://w3id.org/bridge2ai/data-sheets-schema/InstanceAcquisition)





```mermaid
 classDiagram
    class InstanceAcquisition
    click InstanceAcquisition href "../InstanceAcquisition/"
      DatasetProperty <|-- InstanceAcquisition
        click DatasetProperty href "../DatasetProperty/"
      
      InstanceAcquisition : description
        
      InstanceAcquisition : id
        
      InstanceAcquisition : name
        
      InstanceAcquisition : used_software
        
          
    
        
        
        InstanceAcquisition --> "*" Software : used_software
        click Software href "../Software/"
    

        
      InstanceAcquisition : was_directly_observed
        
      InstanceAcquisition : was_inferred_derived
        
      InstanceAcquisition : was_reported_by_subjects
        
      InstanceAcquisition : was_validated_verified
        
      
```





## Inheritance
* [NamedThing](NamedThing.md)
    * [DatasetProperty](DatasetProperty.md)
        * **InstanceAcquisition**



## Slots

| Name | Cardinality and Range | Description | Inheritance |
| ---  | --- | --- | --- |
| [description](description.md) | * <br/> [String](String.md) | Free-text description of the acquisition process | direct |
| [was_directly_observed](was_directly_observed.md) | 0..1 <br/> [Boolean](Boolean.md) | Whether the data was directly observed | direct |
| [was_reported_by_subjects](was_reported_by_subjects.md) | 0..1 <br/> [Boolean](Boolean.md) | Whether the data was reported directly by the subjects themselves | direct |
| [was_inferred_derived](was_inferred_derived.md) | 0..1 <br/> [Boolean](Boolean.md) | Whether the data was inferred or derived from other data | direct |
| [was_validated_verified](was_validated_verified.md) | 0..1 <br/> [Boolean](Boolean.md) | Whether the data was validated or verified in any way | direct |
| [used_software](used_software.md) | * <br/> [Software](Software.md) | What software was used as part of this dataset property? | [DatasetProperty](DatasetProperty.md) |
| [id](id.md) | 1 <br/> [Uriorcurie](Uriorcurie.md) | A unique identifier for a thing | [NamedThing](NamedThing.md) |
| [name](name.md) | 0..1 <br/> [String](String.md) | A human-readable name for a thing | [NamedThing](NamedThing.md) |





## Usages

| used by | used in | type | used |
| ---  | --- | --- | --- |
| [Dataset](Dataset.md) | [acquisition_methods](acquisition_methods.md) | range | [InstanceAcquisition](InstanceAcquisition.md) |
| [DataSubset](DataSubset.md) | [acquisition_methods](acquisition_methods.md) | range | [InstanceAcquisition](InstanceAcquisition.md) |







## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | data_sheets_schema:InstanceAcquisition |
| native | data_sheets_schema:InstanceAcquisition |






## LinkML Source

<!-- TODO: investigate https://stackoverflow.com/questions/37606292/how-to-create-tabbed-code-blocks-in-mkdocs-or-sphinx -->

### Direct

<details>
```yaml
name: InstanceAcquisition
description: 'Describes how data associated with each instance was acquired  (e.g.,
  directly observed, reported by subjects, inferred).

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
is_a: DatasetProperty
attributes:
  description:
    name: description
    description: Free-text description of the acquisition process
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/collection
    domain_of:
    - NamedThing
    - Relationships
    - Splits
    - DataAnomaly
    - Confidentiality
    - Deidentification
    - SensitiveElement
    - InstanceAcquisition
    - CollectionMechanism
    - DataCollector
    - CollectionTimeframe
    - DirectCollection
    - PreprocessingStrategy
    - CleaningStrategy
    - LabelingStrategy
    - RawData
    - ExistingUse
    - UseRepository
    - OtherTask
    - FutureUseImpact
    - DiscouragedUse
    - ThirdPartySharing
    - DistributionFormat
    - DistributionDate
    - Maintainer
    - Erratum
    - UpdatePlan
    - RetentionLimits
    - VersionAccess
    - ExtensionMechanism
    - EthicalReview
    - DataProtectionImpact
    - CollectionNotification
    - CollectionConsent
    - ConsentRevocation
    - LicenseAndUseTerms
    - IPRestrictions
    - ExportControlRegulatoryRestrictions
    range: string
    multivalued: true
  was_directly_observed:
    name: was_directly_observed
    description: Whether the data was directly observed
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/collection
    rank: 1000
    domain_of:
    - InstanceAcquisition
    range: boolean
  was_reported_by_subjects:
    name: was_reported_by_subjects
    description: Whether the data was reported directly by the subjects themselves
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/collection
    rank: 1000
    domain_of:
    - InstanceAcquisition
    range: boolean
  was_inferred_derived:
    name: was_inferred_derived
    description: Whether the data was inferred or derived from other data
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/collection
    rank: 1000
    domain_of:
    - InstanceAcquisition
    range: boolean
  was_validated_verified:
    name: was_validated_verified
    description: Whether the data was validated or verified in any way
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/collection
    rank: 1000
    domain_of:
    - InstanceAcquisition
    range: boolean

```
</details>

### Induced

<details>
```yaml
name: InstanceAcquisition
description: 'Describes how data associated with each instance was acquired  (e.g.,
  directly observed, reported by subjects, inferred).

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
is_a: DatasetProperty
attributes:
  description:
    name: description
    description: Free-text description of the acquisition process
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/collection
    alias: description
    owner: InstanceAcquisition
    domain_of:
    - NamedThing
    - Relationships
    - Splits
    - DataAnomaly
    - Confidentiality
    - Deidentification
    - SensitiveElement
    - InstanceAcquisition
    - CollectionMechanism
    - DataCollector
    - CollectionTimeframe
    - DirectCollection
    - PreprocessingStrategy
    - CleaningStrategy
    - LabelingStrategy
    - RawData
    - ExistingUse
    - UseRepository
    - OtherTask
    - FutureUseImpact
    - DiscouragedUse
    - ThirdPartySharing
    - DistributionFormat
    - DistributionDate
    - Maintainer
    - Erratum
    - UpdatePlan
    - RetentionLimits
    - VersionAccess
    - ExtensionMechanism
    - EthicalReview
    - DataProtectionImpact
    - CollectionNotification
    - CollectionConsent
    - ConsentRevocation
    - LicenseAndUseTerms
    - IPRestrictions
    - ExportControlRegulatoryRestrictions
    range: string
    multivalued: true
  was_directly_observed:
    name: was_directly_observed
    description: Whether the data was directly observed
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/collection
    rank: 1000
    alias: was_directly_observed
    owner: InstanceAcquisition
    domain_of:
    - InstanceAcquisition
    range: boolean
  was_reported_by_subjects:
    name: was_reported_by_subjects
    description: Whether the data was reported directly by the subjects themselves
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/collection
    rank: 1000
    alias: was_reported_by_subjects
    owner: InstanceAcquisition
    domain_of:
    - InstanceAcquisition
    range: boolean
  was_inferred_derived:
    name: was_inferred_derived
    description: Whether the data was inferred or derived from other data
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/collection
    rank: 1000
    alias: was_inferred_derived
    owner: InstanceAcquisition
    domain_of:
    - InstanceAcquisition
    range: boolean
  was_validated_verified:
    name: was_validated_verified
    description: Whether the data was validated or verified in any way
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/collection
    rank: 1000
    alias: was_validated_verified
    owner: InstanceAcquisition
    domain_of:
    - InstanceAcquisition
    range: boolean
  used_software:
    name: used_software
    description: What software was used as part of this dataset property?
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/base
    rank: 1000
    alias: used_software
    owner: InstanceAcquisition
    domain_of:
    - DatasetProperty
    range: Software
    multivalued: true
  id:
    name: id
    description: A unique identifier for a thing.
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/base
    rank: 1000
    slot_uri: schema:identifier
    identifier: true
    alias: id
    owner: InstanceAcquisition
    domain_of:
    - NamedThing
    range: uriorcurie
    required: true
  name:
    name: name
    description: A human-readable name for a thing.
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/base
    rank: 1000
    slot_uri: schema:name
    alias: name
    owner: InstanceAcquisition
    domain_of:
    - NamedThing
    range: string

```
</details>