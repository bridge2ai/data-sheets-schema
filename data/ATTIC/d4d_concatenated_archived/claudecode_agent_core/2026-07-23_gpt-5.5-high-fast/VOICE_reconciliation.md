# VOICE D4D Full/Core Reconciliation

# Model: gpt-5.5
# Reasoning effort: high
# Mode: fast
# Temperature: 0.0
# Generated: 2026-07-23

| Field | Full value before reconciliation | Core value before reconciliation | Resolution | File(s) changed |
|---|---|---|---|---|
| id | https://doi.org/10.13026/37yb-1t42 | https://doi.org/10.13026/37yb-1t42 | Set both records to the v3.0.0 DOI supported by the PhysioNet v3.0.0 citation: https://doi.org/10.13026/k81f-qr68. | Full, core |
| doi | 10.13026/37yb-1t42 | 10.13026/37yb-1t42 | Set both records to the v3.0.0 DOI: 10.13026/k81f-qr68. The latest-version DOI remains documented in version_access. | Full, core |
| publisher | Not present in full record | Bridge2AI-Voice Consortium, University of South Florida | Back-ported publisher metadata into the full record and normalized both records to Bridge2AI-Voice Consortium and PhysioNet. | Full, core |
| download_url | Not present in full record | https://physionet.org/content/b2ai-voice/ | Back-ported the PhysioNet download URL into the full record. | Full |
| issued | Not present in either prior record | Not present in either prior record | Added the PhysioNet publication date, December 16, 2025, as 2025-12-16T00:00:00Z in both records. | Full, core |
| preprocessing_strategies | Spectrogram extraction described a 512-point FFT and 513xN dimensions. | Spectrogram extraction described a 512-point FFT and 513xN dimensions. | Corrected both records to v3.0.0 source values: 25ms window, 10ms hop, 400-point FFT, downsampled spectrograms, and 201xT torchaudio_spectrograms.parquet. | Full, core |
| distribution_dates / updates | v3.0.0 release date stated only as 2025. | v3.0.0 release date stated only as 2025. | Updated both records to state that v3.0.0 was published December 16, 2025. | Full, core |
| file_collections / distributions | Full record lacked file_collections for the core distribution facts. | Core distributions included PhysioNet registered-access and controlled-access distribution details. | Back-ported supported distribution facts into full file_collections and added the Synapse raw-audio controlled-access distribution to core. | Full, core |

Overlapping fields checked: 47

Discrepancies found and resolved: 8

Remaining scalar conflicts: 0

Final validation status:
- Full D4D Dataset schema validation: pass
- Core D4D CoreDataset schema validation: pass
- Full D4D term validation: not run; linkml-term-validator executable unavailable in the Poetry environment
