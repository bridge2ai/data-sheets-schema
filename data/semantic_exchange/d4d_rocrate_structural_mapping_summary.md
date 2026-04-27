# D4D to RO-Crate Schema-Structure-Aware Mapping Summary


## SEMANTIC Mappings (7)

- **Dataset.addressing_gaps** → **d4d:addressingGaps**
  - Confidence: 0.6
  - Type compatible: False
  - Notes: slot_uri mapping: d4d:addressingGaps
  - ⚠️ Warnings: Cardinality mismatch: multivalued slot mapping to single value

- **Dataset.informed_consent** → **d4d:informedConsent**
  - Confidence: 0.6
  - Type compatible: False
  - Notes: slot_uri mapping: d4d:informedConsent
  - ⚠️ Warnings: Cardinality mismatch: multivalued slot mapping to single value

- **Dataset.at_risk_populations** → **d4d:atRiskPopulations**
  - Confidence: 0.9
  - Type compatible: True
  - Notes: slot_uri mapping: d4d:atRiskPopulations

- **DataSubset.addressing_gaps** → **d4d:addressingGaps**
  - Confidence: 0.6
  - Type compatible: False
  - Notes: slot_uri mapping: d4d:addressingGaps
  - ⚠️ Warnings: Cardinality mismatch: multivalued slot mapping to single value

- **DataSubset.informed_consent** → **d4d:informedConsent**
  - Confidence: 0.6
  - Type compatible: False
  - Notes: slot_uri mapping: d4d:informedConsent
  - ⚠️ Warnings: Cardinality mismatch: multivalued slot mapping to single value

- **DataSubset.at_risk_populations** → **d4d:atRiskPopulations**
  - Confidence: 0.9
  - Type compatible: True
  - Notes: slot_uri mapping: d4d:atRiskPopulations

- **LabelingStrategy.data_annotation_platform** → **rai:dataAnnotationPlatform**
  - Confidence: 0.9
  - Type compatible: True
  - Notes: slot_uri mapping: rai:dataAnnotationPlatform


## STRUCTURAL Mappings (142)

- **Purpose.name** → **name**
  - Confidence: 1.0
  - Type compatible: True
  - Notes: Mapped via DatasetProperty hierarchy from Purpose

- **Purpose.description** → **description**
  - Confidence: 1.0
  - Type compatible: True
  - Notes: Mapped via DatasetProperty hierarchy from Purpose

- **Task.name** → **name**
  - Confidence: 1.0
  - Type compatible: True
  - Notes: Mapped via DatasetProperty hierarchy from Task

- **Task.description** → **description**
  - Confidence: 1.0
  - Type compatible: True
  - Notes: Mapped via DatasetProperty hierarchy from Task

- **AddressingGap.name** → **name**
  - Confidence: 1.0
  - Type compatible: True
  - Notes: Mapped via DatasetProperty hierarchy from AddressingGap

- **AddressingGap.description** → **description**
  - Confidence: 1.0
  - Type compatible: True
  - Notes: Mapped via DatasetProperty hierarchy from AddressingGap

- **Creator.principal_investigator** → **principalInvestigator**
  - Confidence: 1.0
  - Type compatible: True
  - Notes: Mapped via DatasetProperty hierarchy from Creator

- **Creator.name** → **name**
  - Confidence: 1.0
  - Type compatible: True
  - Notes: Mapped via DatasetProperty hierarchy from Creator

- **Creator.description** → **description**
  - Confidence: 1.0
  - Type compatible: True
  - Notes: Mapped via DatasetProperty hierarchy from Creator

- **FundingMechanism.name** → **name**
  - Confidence: 1.0
  - Type compatible: True
  - Notes: Mapped via DatasetProperty hierarchy from FundingMechanism

... and 132 more

