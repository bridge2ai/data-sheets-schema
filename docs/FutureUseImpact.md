

# Class: FutureUseImpact 


_Is there anything about the dataset's composition or collection that might impact future uses or create risks/harm (e.g., unfair treatment, legal or financial risks)? If so, describe these impacts and any mitigation strategies._

__





URI: [data_sheets_schema:FutureUseImpact](https://w3id.org/bridge2ai/data-sheets-schema/FutureUseImpact)





```mermaid
 classDiagram
    class FutureUseImpact
    click FutureUseImpact href "../FutureUseImpact/"
      DatasetProperty <|-- FutureUseImpact
        click DatasetProperty href "../DatasetProperty/"
      
      FutureUseImpact : description
        
      FutureUseImpact : id
        
      FutureUseImpact : name
        
      FutureUseImpact : used_software
        
          
    
        
        
        FutureUseImpact --> "*" Software : used_software
        click Software href "../Software/"
    

        
      
```





## Inheritance
* [NamedThing](NamedThing.md)
    * [DatasetProperty](DatasetProperty.md)
        * **FutureUseImpact**



## Slots

| Name | Cardinality and Range | Description | Inheritance |
| ---  | --- | --- | --- |
| [description](description.md) | * <br/> [String](String.md) | Details regarding the possible future impacts or risks of use | direct |
| [used_software](used_software.md) | * <br/> [Software](Software.md) | What software was used as part of this dataset property? | [DatasetProperty](DatasetProperty.md) |
| [id](id.md) | 1 <br/> [Uriorcurie](Uriorcurie.md) | A unique identifier for a thing | [NamedThing](NamedThing.md) |
| [name](name.md) | 0..1 <br/> [String](String.md) | A human-readable name for a thing | [NamedThing](NamedThing.md) |





## Usages

| used by | used in | type | used |
| ---  | --- | --- | --- |
| [Dataset](Dataset.md) | [future_use_impacts](future_use_impacts.md) | range | [FutureUseImpact](FutureUseImpact.md) |
| [DataSubset](DataSubset.md) | [future_use_impacts](future_use_impacts.md) | range | [FutureUseImpact](FutureUseImpact.md) |







## Identifier and Mapping Information






### Schema Source


* from schema: https://w3id.org/bridge2ai/data-sheets-schema




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | data_sheets_schema:FutureUseImpact |
| native | data_sheets_schema:FutureUseImpact |






## LinkML Source

<!-- TODO: investigate https://stackoverflow.com/questions/37606292/how-to-create-tabbed-code-blocks-in-mkdocs-or-sphinx -->

### Direct

<details>
```yaml
name: FutureUseImpact
description: 'Is there anything about the dataset''s composition or collection that
  might impact future uses or create risks/harm (e.g., unfair treatment, legal or
  financial risks)? If so, describe these impacts and any mitigation strategies.

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
is_a: DatasetProperty
attributes:
  description:
    name: description
    description: Details regarding the possible future impacts or risks of use.
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/uses
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

```
</details>

### Induced

<details>
```yaml
name: FutureUseImpact
description: 'Is there anything about the dataset''s composition or collection that
  might impact future uses or create risks/harm (e.g., unfair treatment, legal or
  financial risks)? If so, describe these impacts and any mitigation strategies.

  '
from_schema: https://w3id.org/bridge2ai/data-sheets-schema
is_a: DatasetProperty
attributes:
  description:
    name: description
    description: Details regarding the possible future impacts or risks of use.
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/uses
    alias: description
    owner: FutureUseImpact
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
  used_software:
    name: used_software
    description: What software was used as part of this dataset property?
    from_schema: https://w3id.org/bridge2ai/data-sheets-schema/base
    rank: 1000
    alias: used_software
    owner: FutureUseImpact
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
    owner: FutureUseImpact
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
    owner: FutureUseImpact
    domain_of:
    - NamedThing
    range: string

```
</details>