# Manual Downloads Required

Due to authentication/protection mechanisms, **3 files** need to be downloaded manually:

## 1. BioRxiv PDF (CM4AI) - CLOUDFLARE PROTECTION

**File needed**: `downloads_by_column_enhanced/CM4AI/biorxiv_2024.05.21.589311v1_row4.pdf`

**Steps to download**:
1. Open in browser: https://www.biorxiv.org/content/10.1101/2024.05.21.589311v1.full.pdf
2. Wait for Cloudflare challenge to complete (if shown)
3. PDF should automatically download
4. Save as: `biorxiv_2024.05.21.589311v1_row4.pdf`
5. Move to: `downloads_by_column_enhanced/CM4AI/`

**Note**: This PDF will need processing to markdown for concatenation with other documents.

---

## 2. Google Drive File (VOICE DUA) - AUTHENTICATION REQUIRED

**File needed**: `downloads_by_column_enhanced/VOICE/drive_google_com_1z4zZ_Z_Jb017IoVZn5btJnSLKdEOHZPA_row13.pdf`

**Steps to download**:
1. Open in browser: https://drive.google.com/file/d/1z4zZ_Z_Jb017IoVZn5btJnSLKdEOHZPA/view
2. Log in to Google account if required
3. Download file (click Download button)
4. Save to: `downloads_by_column_enhanced/VOICE/`

**Alternative**: Change file sharing to "Anyone with the link" to enable programmatic access.

---

## 3. GitHub CHORUS Repository - INVESTIGATION NEEDED

**URL**: https://github.com/chorus-ai#table-of-contents

**Status**: Unknown error - may be private or URL fragment causing issues

**Steps**:
1. Open in browser: https://github.com/chorus-ai
2. If accessible, download repository documentation or README
3. Save to: `downloads_by_column_enhanced/CHORUS/`

---

## Summary

| File | Column | Issue | Solution |
|------|--------|-------|----------|
| BioRxiv PDF | CM4AI | Cloudflare protection | Click link in browser |
| Google Drive | VOICE | Authentication | Login and download |
| GitHub CHORUS | CHORUS | Unknown | Investigate/manual |

## After Manual Download

Once files are manually downloaded, process them with:

```bash
poetry run python src/download/validated_d4d_wrapper.py \
  -i downloads_by_column_enhanced \
  -o data/extracted_by_column_enhanced
```
