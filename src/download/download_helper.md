# Download Helper - Troubleshooting Guide

## bioRxiv/medRxiv Downloads

If downloads from bioRxiv or medRxiv fail with 403 errors, here are some solutions:

### 1. Updated Script
The enhanced_sheet_downloader.py now includes:
- Browser-like User-Agent headers
- Proper referer headers for academic sites
- Respectful delays between downloads

### 2. Manual Download Links
If automated downloads still fail, you can:

1. **For bioRxiv papers**: Replace the URL pattern
   - Original: `https://www.biorxiv.org/content/10.1101/2024.05.21.589311v1`
   - PDF link: `https://www.biorxiv.org/content/10.1101/2024.05.21.589311v1.full.pdf`
   - Alternative: Use the "Download PDF" button on the page

2. **Use wget with proper headers**:
   ```bash
   wget --user-agent="Mozilla/5.0" \
        --referer="https://www.biorxiv.org/" \
        -O "paper.pdf" \
        "https://www.biorxiv.org/content/10.1101/2024.05.21.589311v1.full.pdf"
   ```

3. **Use curl**:
   ```bash
   curl -H "User-Agent: Mozilla/5.0" \
        -H "Referer: https://www.biorxiv.org/" \
        -L -o "paper.pdf" \
        "https://www.biorxiv.org/content/10.1101/2024.05.21.589311v1.full.pdf"
   ```

### 3. Alternative Approaches

1. **Browser Extension**: Use a browser extension like DownThemAll
2. **Browser Developer Tools**: 
   - Open the PDF in your browser
   - Right-click → Save As
   - Or use browser's download manager

### 4. Respect Rate Limits

Academic publishers implement these protections to:
- Prevent server overload
- Ensure fair access for all users
- Protect copyright content

Always:
- Add delays between downloads (2-5 seconds)
- Download only what you need
- Respect robots.txt files
- Consider using the site's API if available

### 5. bioRxiv Specific Tips

bioRxiv provides several download options:
- **PDF**: Full formatted paper
- **Supplementary Files**: Often in a separate ZIP
- **Data**: Sometimes linked to external repositories

The script now handles these better, but manual download may still be needed for some content.