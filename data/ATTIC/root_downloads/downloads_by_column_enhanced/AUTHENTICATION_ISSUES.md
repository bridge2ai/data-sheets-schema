# Google Sheet Input Data - Authentication Issues Analysis

## Full Sheet Contents by Row and Column

| Row | Type | CM4AI | VOICE | AI-READI | CHORUS |
|-----|------|-------|-------|----------|--------|
| 2 | publication | - | - | [BMJ Open PDF](https://bmjopen.bmj.com/content/bmjopen/15/2/e097449.full.pdf) ✅ | - |
| 3 | publication 2 | - | - | [Nature PDF](https://www.nature.com/articles/s42255-024-01165-x.pdf) ✅ | - |
| 4 | preprint | [**BioRxiv PDF**](https://www.biorxiv.org/content/10.1101/2024.05.21.589311v1.full.pdf) **❌ 403** | - | - | - |
| 8 | tutorial | - | - | [AIM-AHEAD Webinar](https://www.aim-ahead.net/media/raekwjgs/aim-ahead-bridge2ai-for-clinical-care-informational-webinar.pdf) ✅ | - |
| 9 | documentation 1 | - | [docs.b2ai-voice.org](https://docs.b2ai-voice.org/) ✅ | [docs.aireadi.org](https://docs.aireadi.org/docs/2/about) ✅ | [**GitHub CHORUS**](https://github.com/chorus-ai#table-of-contents) **❌ Unknown** |
| 10 | documentation 2 | - | - | [Zenodo License](https://zenodo.org/records/10642459/files/AI-READI-LICENSE-v1.0.pdf?download=1) ✅ | - |
| 11 | documentation 3 | - | - | [FAIRhub #2](https://fairhub.io/datasets/2) ✅ | - |
| 12 | IRB | - | [Google Doc](https://docs.google.com/document/d/1gTFzAM-FoYlM_X9qF0s7fXoswmaz8IqN/edit) ✅ | [Google Doc](https://docs.google.com/document/d/1rJsa5kySlBRRNhsO_WY7N3bfSKtqDi-Q/edit) ✅ | - |
| 13 | DUA | - | [**Google Drive**](https://drive.google.com/file/d/1z4zZ_Z_Jb017IoVZn5btJnSLKdEOHZPA/view) **❌ 401** | - | - |
| 14 | License | [Creative Commons](https://creativecommons.org/licenses/by-nc-sa/4.0/deed.en) ✅ | - | - | - |
| 15 | data resource 1 | [Dataverse B35XWX](https://dataverse.lib.virginia.edu/dataset.xhtml?persistentId=doi:10.18130/V3/B35XWX) ✅ | [HealthDataNexus](https://healthdatanexus.ai/content/b2ai-voice/1.0/) ✅ | [FAIRhub #2](https://fairhub.io/datasets/2) ✅ | - |
| 16 | data resource 2 | - | [PhysioNet](https://physionet.org/content/b2ai-voice/1.1/) ✅ | - | - |
| 18 | metadata | [Dataverse F3TD5R](https://dataverse.lib.virginia.edu/dataset.xhtml?persistentId=doi:10.18130/V3/F3TD5R&version=DRAFT) ✅ | - | - | - |
| 21 | (note) | - | VOICE D4D: [docs](https://docs.b2ai-voice.org/) + [GitHub repo](https://github.com/eipm/bridge2ai-docs/tree/main/docs) ✅ | - | - |

## Authentication/Permission Issues (3 total)

### 1. ❌ BioRxiv PDF - Cloudflare Protection
- **Row**: 4
- **Column**: CM4AI
- **Type**: preprint
- **URL**: https://www.biorxiv.org/content/10.1101/2024.05.21.589311v1.full.pdf
- **Error**: `403 Client Error: Forbidden` (Cloudflare bot protection)
- **Issue**: BioRxiv uses Cloudflare challenge that requires JavaScript execution
- **Solution**: **Manual download required**
  1. Open URL in browser: https://www.biorxiv.org/content/10.1101/2024.05.21.589311v1.full.pdf
  2. Save PDF to: `downloads_by_column_enhanced/CM4AI/biorxiv_2024.05.21.589311v1_row4.pdf`
- **Status**: **Requires manual intervention** (Cloudflare blocks automated tools)
- **Note**: PDF will need processing to markdown for concatenation

### 2. ❌ GitHub CHORUS - Unknown Error
- **Row**: 9
- **Column**: CHORUS
- **Type**: documentation 1
- **URL**: https://github.com/chorus-ai#table-of-contents
- **Error**: `Unknown error`
- **Issue**: Unable to access repository (may be private or URL issue with #fragment)
- **Solution**: Repository may require authentication OR the #fragment is causing issues
- **Status**: Needs investigation - may require manual access

### 3. ❌ Google Drive DUA - 401 Unauthorized
- **Row**: 13
- **Column**: VOICE
- **Type**: DUA (Data Use Agreement)
- **URL**: https://drive.google.com/file/d/1z4zZ_Z_Jb017IoVZn5btJnSLKdEOHZPA/view
- **Error**: `401 Client Error: Unauthorized`
- **Issue**: Google Drive file requires authentication/permissions
- **Solution**: File must be shared publicly OR user must download manually with credentials
- **Status**: **Cannot fix programmatically** - requires manual intervention

## Successfully Downloaded (17/20 = 85%)

All other URLs downloaded successfully, including:
- ✅ 2 PDFs from BMJ Open and Nature
- ✅ 2 Dataverse datasets with full tab content (Files, Metadata, Terms, Versions)
- ✅ 2 FAIRhub datasets with tabs
- ✅ 1 HealthDataNexus with 16 comprehensive tabs
- ✅ 1 PhysioNet dataset
- ✅ 2 Google Docs (1 exported as PDF)
- ✅ 1 GitHub repository with README
- ✅ Multiple documentation pages

## Recommendations

1. **BioRxiv (Fixable)**: Update code to add referer header for BioRxiv specifically
2. **GitHub CHORUS (Investigate)**: Check if repository is public and test URL without #fragment
3. **Google Drive (Manual)**: User needs to either:
   - Make file publicly accessible (change sharing settings)
   - Download manually and add to `downloads_by_column_enhanced/VOICE/`
   - Share with the service account if using automation

## Links for Authentication Issues

**For manual download/review:**

1. BioRxiv PDF (CM4AI preprint):
   https://www.biorxiv.org/content/10.1101/2024.05.21.589311v1.full.pdf

2. GitHub CHORUS (documentation):
   https://github.com/chorus-ai#table-of-contents

3. Google Drive DUA (VOICE):
   https://drive.google.com/file/d/1z4zZ_Z_Jb017IoVZn5btJnSLKdEOHZPA/view
