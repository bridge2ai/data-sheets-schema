"""#5517 D101/D102 quotation authoring, 2026-11-08.
Inputs: round-1 contexts and declared bundles. Outputs: context edits and audit
in the single authorized scratch root. --apply one project is the write canary.
No providers; source offsets and hashes are checked before every write.
"""
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

import yaml
from context_evidence_5517 import sources, location
from data_sheets_schema.evaluation_context import context_digest

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-codex-5517'
BASE = '5ab230659799923741ba24dec1ef3ec06e326ab0'
# Exact excerpts; each is independently cited, including excerpts split by PDF furniture.
QUOTES = {
'ai_readi': {
'human_subjects': ['AI- READI was approved by the Institutional Review Board', 'This dataset contains data from 2280 participants that was collected between July 19, 2023 and May 01, 2025.'],
'regulated_access': ['Accessing the dataset requires several steps, including: Login in through a verified ID system, Agreeing to use the data only for type 2 diabetes related research, Agreeing to the license terms which set certain restrictions and obligations for data usage'],
'shared_dataset': ['All  data  are  stored  and  shared\nusing  FAIRhub'],
'data_collection': ['This dataset contains data from 2280 participants that was collected between July 19, 2023 and May 01, 2025.', 'REDCap is used for collecting patient- reported data from\nquestionnaires  and  the  following  clinical  data  from  the\nvisit: medications assessment, vitals, visual acuity, contrast\nsensitivity, monofilament test results and CBC test results.'],
'data_processing': ['Each CSV file in this directory is a one-to-one mapping to the OMOP CDM tables.', 'WaveForm DataBase (WFDB)'],
'processing_software': ['REDCap is used for collecting patient- reported data from\nquestionnaires  and  the  following  clinical  data  from  the\nvisit: medications assessment, vitals, visual acuity, contrast\nsensitivity, monofilament test results and CBC test results.'],
'ml_training_dataset': ['The current version of the dataset comes with recommended data splits. Because sex, race, and ethnicity data are not being released with the public version of the dataset, the project team has prepared data splits into proportions (70%/15%/15%) that can be used for subsequent training/validation/testing where the validation and test sets are balanced as well as possible for sex, race/ethnicity and diabetes status (no diabetes, prediabetes/lifestyle controlled, oral medication controlled, and insulin controlled).'],
},
'chorus': {
'human_subjects': ['Current Released Dataset\n50,000\nPatient admissions from ICU, PICU, and NICU'],
'regulated_access': ['All participants must sign a licensing agreement included in the registration form before gaining', 'access to the dataset'],
'shared_dataset': ['Current Released Dataset\n50,000\nPatient admissions from ICU, PICU, and NICU', 'Learn of different opportunities to gain hands-on training using the CHoRUS dataset to support the development of transnational AI in clinical care.'],
'data_collection': ['The CHoRUS project is the collection of multi-modal data across 14 different hospitals.'],
'data_processing': ['acquire data, standardize data to the OMOP Common Data Model, transform data using approaches that limit re-identification'],
'processing_software': ['Open source code to geocode OMOP Location entities via DeGauss'],
'ml_training_dataset': ['The dataset will also provision a holdout test set, accessible for model external validation to aid marketplace adoption of AI-developed models for implementation in acute and critical care.'],
},
'cm4ai': {
'human_subjects': ['CM4AI data are distinctive within Bridge2AI in that they are non-clinical (from tissue', 'cultures) and are considered to be de-identified as they cannot be matched, with current\nknowledge, to a human subject.'],
'regulated_access': ['Data packages are licensed under Creative\nCommons CC-BY-NC-SA 4.0 license terms31'],
'shared_dataset': ['Data packages from CM4AI including links to software used in preparing the data, input\ndatasets, dataset schemas, and deep provenance graphs, are available on the CM4AI\nweb portal and will soon be available on the Dataverse NIH approved generalist\nrepository.'],
'data_collection': ['We collected a proteomic SEC–MS dataset in the U2OS cell line according to a previously described procedure'],
'data_processing': ['Specific packages include steps for processing the protein imaging and biophysical interaction datasets (cellmaps_imagedownloader, cellmaps_ppidownloader), embedding the input modalities (cellmaps_image_embedding, cellmaps_ppi_embedding), integrating the modalities (cellmaps_coembedding), constructing the hierarchical cell map (cellmaps_generate_hierarchy) and annotating the cell map with known resources such as GO (cellmaps_hierarchyeval).'],
'processing_software': ['All CM4AI integration and packaging software is freely available and licensed under\nnonrestrictive open-source licenses.'],
'ml_training_dataset': ['Intended Use\nThis dataset is intended for:\nAI-ready datasets to support research in functional genomics\nAI model training'],
},
'kids_first': {
'human_subjects': ['is a single individual who enrolled in a Kids First study and has consented to share biospecimens and data for research and discovery.', 'Not all participants are themselves affected by the condition of interest of their study – for example, some studies enroll parents and siblings who do not have the condition.'],
'regulated_access': ['Controlled-access files require dbGaP approval before access is granted.'],
'shared_dataset': ['Data from more than 30,000 participants annotated with demographic and clinical information related to their diagnoses have been released for secondary research and analysis using the center\'s web-based platforms.'],
'data_collection': ['Around 550 trios were selected for whole genome sequencing as part of the Gabriella Miller Kids First project. Patients with congenital anomalies of the kidney and urinary tract (germline tissues), along with germline DNA from the proband\'s mother and father make up each trio. The trios have been collected as part of the Genetics of Chronic Kidney disease study at Columbia University, which includes international collaborators. Each trio has associated phenotypic data.'],
'data_processing': ['The Kids First Data Resource Center supports cross-study analysis of data files by using a set of standardized bioinformatic workflows. Outputs from a single workflow are harmonized for combined analysis regardless of which Kids First study they are associated with.'],
'processing_software': ['Each of the Kids First DRC bioinformatic workflows is available on GitHub and CAVATICA for user’s own analyses', 'The Kids First DRC is structuring all Kids First data in a FHIR-based data service to make it more compatible with EHR data and other FHIR-based tools and data models.'],
'ml_training_dataset': ['The overarching goal of the Gabriella Miller Kids First Pediatric Research Program is to help researchers uncover new insights into the biology of childhood cancer and congenital anomalies.'],
},
'voice': {
'human_subjects': ['Patients presenting at specialty clinics and institutions were considered for enrollment.', 'If eligible for enrollment, patient consent was sought for the data collection initiative and to share the acquired research data.'],
'regulated_access': ['Only credentialed users who sign the DUA can access the files.'],
'shared_dataset': ['Bridge2AI-Voice v3.1 contains data for 833 participants across five sites in North America.', 'Detailed demographic, clinical, and validated questionnaire data are also made available.'],
'data_collection': ['Data collection was conducted using a custom application on a tablet with a headset used for data collection when possible.'],
'data_processing': ['Raw audio was preprocessed by converting to monaural and resampling to 16 kHz with a Butterworth anti-aliasing filter applied.'],
'processing_software': ['The code used to preprocess the raw audio waveforms into the parquet file and to merge the source data into the phenotype files has been made open source in the\nb2aiprep library'],
'ml_training_dataset': ['Our group aims to develop voice as a biomarker of health used in clinical care. To do so we will generate a large multi-institutional, ethically sourced, and diverse voice database linked to multimodal health biomarkers to fuel voice AI research. We will then build predictive models to assist in screening, diagnosis, and treatment of a broad range of diseases, including several diseases with unmet clinical needs.'],
},
'voice_pediatric': {
'human_subjects': ['Patients/healthy volunteers at the Hospital for Sick Children were considered for enrollment in the study.', 'Following confirmation of eligibility, parental or participant consent was obtained prior to data collection and data sharing.'],
'regulated_access': ['Only credentialed users who sign the DUA can access the files.'],
'shared_dataset': ['Bridge2AI-Voice Pediatric Dataset v1.1.0 contains derived audio features for 23,533 recordings collected from 300 participants aged 2-18.', 'Detailed demographic, clinical, and validated questionnaire data are also made available.'],
'data_collection': ['All data was collected through customized software –\nreproschema-ui –\non tablets.'],
'data_processing': ['torchaudio_mfcc.parquet (n=23533) contains Mel-frequency cepstrum coefficients of dimension 60xT using the same parameters as the mel spectrograms.'],
'processing_software': ['The code used to preprocess the raw audio waveforms into the parquet file and to merge the source data into the phenotype files has been made open source in the\nb2aiprep library'],
'ml_training_dataset': ['Resources such as this project are intended to enable study of developmental norms, create AI-driven tools for early screening, and support clinical insight.', 'Our group aims to develop voice as a biomarker of health used in clinical care. To do so we will generate a large multi-institutional, ethically sourced, and diverse voice database linked to multimodal health biomarkers to fuel voice AI research. We will then build predictive models to assist in screening, diagnosis, and treatment of a broad range of diseases, including several diseases with unmet clinical needs.'],
}}
NEEDS_OWNER = {
('cm4ai', 'regulated_access'): 'Searched the complete declared CM4AI bundle for access, restricted, unrestricted, public, download, license and embargo; inspected licensing, Dataverse access text and release limitations. Licensing alone does not establish absence of access gates; generic Dataverse UI is not a release-specific access assertion. Some datasets are described as under temporary pre-publication embargo. No unambiguous quotation supporting false was identified. D52 value retained.',
('kids_first', 'ml_training_dataset'): 'Searched the complete declared KIDS_FIRST bundle for machine learning, training, AI, model, research and resource; inspected program purpose, portal, workflows and data-use descriptions. Research-purpose text does not directly assert that this is not an ML training dataset. No quotation supporting the negative value was identified. D52 value retained.',
}

def build():
    audit = []
    proposals = {}
    for project, predicates in QUOTES.items():
        path = ROOT / f'data/context/{project}_context.yaml'
        old = subprocess.check_output(['git', 'show', f'{BASE}:{path.relative_to(ROOT)}'], text=True)
        ctx = yaml.safe_load(old)
        bundle_path, bundle, manifest = sources(project)
        assert hashlib.sha256(bundle_path.read_bytes()).hexdigest() == manifest['bundle_sha256']
        assert set(predicates) == set(ctx)
        new = old
        for predicate, quotes in predicates.items():
            entry = ctx[predicate]
            original = entry['evidence']
            owner = re.findall(r'\[curator_assertion:[^]]+\]', original)
            notes = NEEDS_OWNER.get((project, predicate))
            parts = owner.copy()
            if notes:
                parts += ['[needs_owner: true]', '[search_notes] ' + json.dumps(notes)]
            locations = []
            for quote in quotes:
                loc, ids = location(project, quote)
                parts.append('[chunks: ' + ', '.join(ids) + '] ' + json.dumps(quote, ensure_ascii=False))
                locations.append(loc)
            evidence = ' '.join(parts)
            entry['evidence'] = evidence
            block = re.search(rf'(?ms)^{predicate}:\n.*?(?=^\w+:|\Z)', new).group()
            # Refresh redundant chunk comments as well as the actual evidence.
            ids = sorted(set(re.findall(r'c\d{3}', ' '.join(locations))))
            updated = re.sub(r'  # chunks: \[[^]]+\]', '  # chunks: [' + ', '.join(ids) + ']', block)
            updated = re.sub(r'^  evidence:.*$', lambda _: '  evidence: ' + json.dumps(evidence, ensure_ascii=False), updated, flags=re.M)
            new = new.replace(block, updated)
            audit.append(dict(project=project, predicate=predicate, value=entry['value'], evidence=evidence, quotations=quotes, locations=locations, state='needs_owner' if notes else 'quoted', search_notes=notes, bundle=str(bundle_path.relative_to(ROOT)), bundle_sha256=manifest['bundle_sha256']))
        assert yaml.safe_load(new) == ctx
        proposals[project] = new
    return audit, proposals

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', default='none', choices=['none', 'all', *QUOTES])
    args = parser.parse_args()
    assert not (ROOT.parent / 'plans/native_quiet_window.lock').exists()
    audit, proposals = build()
    (SCRATCH / 'r2-audit.json').write_text(json.dumps(audit, indent=2, ensure_ascii=False) + '\n')
    for project, text in proposals.items():
        if args.apply in ('all', project):
            path = ROOT / f'data/context/{project}_context.yaml'
            path.write_text(text)
            assert path.read_text() == text
    print(f'{len(audit)} entries; {sum(r["state"] == "needs_owner" for r in audit)} needs_owner; applied {args.apply}')
