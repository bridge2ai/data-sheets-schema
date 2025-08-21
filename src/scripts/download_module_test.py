import requests

# Updated dictionary mapping each label to its public Google Docs URL.
docs = {
    "D4D - Minimal": "https://docs.google.com/document/d/1JXDX_GEPje24ibG-mZaVSBYmjYAMZUGNoj0JaaKQ44c/edit?usp=drivesdk",
    "D4D - Metadata": "https://docs.google.com/document/d/1VgIk418dG-MMqwmaNwXeYWUJmM07hGEKkkXCxJpR4K0/edit?usp=drivesdk",
    "D4D - Data Governance": "https://docs.google.com/document/d/14nJ8PGLx_MKIhRXcMjELRWUXpw1lgFA-fMDmmmHOOvU/edit?usp=drivesdk",
    "D4D - Ethics": "https://docs.google.com/document/d/1ae54itDf-pCXd-r05s4DA0GivBuFz6tsokPqjjacwQk/edit?usp=drivesdk",
    "D4D - Maintenance": "https://docs.google.com/document/d/1jieYwBw_iCnaLJRcTi0ZQv39ZJGtsZI0xghr85SF96w/edit?usp=drivesdk",
    "D4D - Distribution": "https://docs.google.com/document/d/1DXE43aCTgEols8gW1SwnFsIswq0oD2en4rS8qvVpXzs/edit?usp=drivesdk",
    "D4D - Uses": "https://docs.google.com/document/d/1n6PE4zc5myX1zC49XeWNpQmIDnfYLoppkd85xfM4jIk/edit?usp=drivesdk",
    "D4D - Preprocessing": "https://docs.google.com/document/d/1_uYqQVBB6YVJNki7OwOeIaAMHP28_4vV73cpANxJJHM/edit?usp=drivesdk",
    "D4D - Composition": "https://docs.google.com/document/d/1PeTsag7NZCBRe-RjJjKYTQtakc3RWJixwrjAGvBkARA/edit?usp=drivesdk",
    "D4D - Collection": "https://docs.google.com/document/d/1Q79gwEtAIvsiXAmzIKu5BpiQ39rbp3JAijiucpobABM/edit?usp=drivesdk",
    "D4D - Motivation": "https://docs.google.com/document/d/1k7FsVsZKS_W6N_erfnq49SHV4JbuNhJXvH7vLAd1hUI/edit?usp=drivesdk",
    "D4D - Human": "https://docs.google.com/document/d/1chaelMfa1gcXH3wDt1aZiigQutHks3cYJU3WhnKfP2E/edit?usp=drivesdk"
}

for label, url in docs.items():
    # Extract the document ID from the URL (the string between '/d/' and the next '/')
    try:
        doc_id = url.split("/d/")[1].split("/")[0]
    except IndexError:
        print(f"Could not extract document ID for {label}")
        continue

    # Construct the export URL to download the document as plain text.
    export_url = f"https://docs.google.com/document/d/{doc_id}/export?format=txt"
    response = requests.get(export_url)
    
    if response.status_code == 200:
        # Replace " - " with "_" then any remaining spaces with "_" and use .yaml as the extension.
        filename = label.replace(" - ", "_").replace(" ", "_") + ".yaml"
        with open(filename, "wb") as f:
            f.write(response.content)
        print(f"Saved {filename}")
    else:
        print(f"Failed to download {label}. HTTP status code: {response.status_code}")

