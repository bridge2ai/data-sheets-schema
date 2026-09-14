"""Deterministic, declared extraction of the Kids First documentation bundle.

This experiment's source adapter is separate from the general D4D pipeline.
It preserves hyperlinks and reads the public catalogue's study-card fields.
It excludes participant identifier mappings in historical release notes.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup
import yaml

HERE = Path(__file__).resolve().parent
PROCESSED = HERE / "processed"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def keep(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_text(encoding="utf-8") != text:
            raise ValueError(f"refusing to change a frozen extraction: {path}")
        return
    with path.open("x", encoding="utf-8") as stream:
        stream.write(text)


def captured(identifier):
    receipt = json.loads((HERE / "captures" / f"{identifier}.json").read_bytes())
    path = HERE / receipt["local_path"]
    if receipt.get("http_status") != 200 or sha(path) != receipt["sha256"]:
        raise ValueError(f"unavailable or changed original source: {identifier}")
    return receipt, path.read_bytes()


def linked_text(element, url):
    element = deepcopy(element)
    for node in element.select("script,style,noscript,nav,aside,form"):
        node.decompose()
    for link in element.select("a[href]"):
        label = link.get_text(" ", strip=True)
        href = urljoin(url, link["href"])
        link.replace_with(f"{label} ({href})" if label and label != href else href)
    return "\n".join(line.strip() for line in element.get_text("\n").splitlines() if line.strip())


def main():
    PROCESSED.mkdir(exist_ok=True)
    sources = []
    extraction = []

    def document(identifier, title, body, receipt, method, source_type="documentation"):
        if len(body.strip()) < 100:
            raise ValueError(f"empty or implausibly short extraction: {identifier}")
        path = PROCESSED / f"{identifier}.txt"
        text = (f"TITLE: {title}\nSOURCE URL: {receipt['url']}\n"
                f"CAPTURED AT: {receipt['retrieved_at']}\n\n{body.strip()}\n")
        keep(path, text)
        sources.append({"id": identifier, "source_type": source_type,
                        "url": receipt["url"], "raw_file": Path(receipt["local_path"]).name,
                        "processed_file": path.name,
                        "captured_at": receipt["retrieved_at"][:10]})
        extraction.append({"id": identifier, "raw_sha256": receipt["sha256"],
                           "processed_sha256": sha(path), "processed_bytes": path.stat().st_size,
                           "method": method, "url": receipt["url"]})

    # Primary article identity and abstract; no full-text availability claim.
    receipt, raw = captured("paper_abstract")
    article = json.loads(raw)["resultList"]["result"][0]
    assert article["doi"] == "10.1016/j.ajhg.2026.07.010"
    body = (f"DOI: https://doi.org/{article['doi']}\nPMID: {article['id']}\n"
            f"First publication date: {article['firstPublicationDate']}\n"
            f"Authors: {article['authorString']}\n\nABSTRACT:\n{article['abstractText']}\n")
    document("paper_abstract", article["title"], body, receipt,
             "Europe PMC indexed article metadata and abstract; full text not captured", "publication abstract")

    for identifier in ["drc_about", "drc_resources", "drc_faqs", "drc_our_data_process",
                       "drc_data_dictionary", "drc_security", "drc_quick_start_guide",
                       "drc_accessing_controlled_data_via_dbgap", "drc_article_release", "nih_faq",
                       "nih_1", "nih_2", "nih_3", "nih_4", "nih_5", "nih_6", "nih_7"]:
        receipt, raw = captured(identifier)
        soup = BeautifulSoup(raw, "html.parser")
        if "commonfund.nih.gov" in receipt["url"]:
            article_node = soup.select_one("article")
            bodies = article_node.select(".field--name-body") if article_node else []
            if article_node and article_node.select(".field--name-field-accordion-content"):
                selected = article_node
                selector = "article including FAQ accordion content"
            else:
                selected = max(bodies, key=lambda node: len(node.get_text()), default=article_node)
                selector = "largest .field--name-body inside article, else article"
        else:
            selected = soup.select_one('[role="main"]')
            selector = '[role="main"]'
        if selected is None or soup.title is None:
            raise ValueError(f"missing main documentation: {identifier}")
        document(identifier, soup.title.get_text(" ", strip=True), linked_text(selected, receipt["url"]),
                 receipt, selector + "; strip executable/navigation/form nodes; preserve link targets")

    # Select the dataset catalogue fields, including values displayed in modals.
    receipt, raw = captured("drc_studies")
    soup = BeautifulSoup(raw, "html.parser")
    studies = []
    for card in soup.select(".publication[data-phs]"):
        accession = card["data-phs"]
        info = {key[5:]: value for key, value in card.attrs.items()
                if key.startswith("data-") and key != "data-notes"}
        info["visible_labels"] = [node.get_text(" ", strip=True) for node in card.select(".pubfilterlabel")]
        info["release_dates"] = {
            node.select_one(".metatitle").get_text(" ", strip=True):
            node.select_one(".metaitem").get_text(" ", strip=True)
            for node in card.select(".pubdate")}
        study_receipt, study_raw = captured("dbgap_" + accession)
        study_soup = BeautifulSoup(study_raw, "html.parser")
        actual_id = study_soup.select_one("#study-id").get_text(" ", strip=True)
        if actual_id.split(".")[0] != accession:
            raise ValueError(f"study page identity mismatch: {accession}")
        info.update(dbgap_captured_accession=actual_id,
                    dbgap_documentation_url=study_receipt["url"],
                    documentation_file=f"processed/dbgap_{accession}.txt",
                    catalogue_source_url=receipt["url"],
                    catalogue_source_sha256=receipt["sha256"],
                    dbgap_source_sha256=study_receipt["sha256"],
                    catalogue_selector=f'.publication[data-phs="{accession}"]')
        sections = []
        allowed = {"Study Description", "Study Inclusion/Exclusion Criteria", "Selected Publications",
                   "Diseases/Traits Related to Study (MeSH terms)", "Study Attribution"}
        for heading in study_soup.select("dl.report > dt"):
            name = heading.get_text(" ", strip=True)
            if name not in allowed:
                continue
            body_node = heading.find_next_sibling("dd")
            if body_node is None:
                raise ValueError(f"missing description body: {accession}/{name}")
            sections.append(name + "\n" + linked_text(body_node, study_receipt["url"]))
        if not sections or not sections[0].startswith("Study Description\n"):
            raise ValueError(f"missing public study description: {accession}")
        title = study_soup.select_one("#study-name").get_text(" ", strip=True)
        body = f"dbGaP accession: {actual_id}\n\n" + "\n\n".join(sections)
        document("dbgap_" + accession, title, body, study_receipt,
                 "declared public study description/eligibility/publication/trait/attribution sections; preserve links",
                 "data resource")
        studies.append(info)
    if len(studies) != 36 or len({row["phs"] for row in studies}) != 36:
        raise ValueError("captured catalogue does not contain the reviewed 36 distinct accessions")
    keep(HERE / "study_catalogue.json", json.dumps({"source_url": receipt["url"],
        "captured_at": receipt["retrieved_at"], "source_sha256": receipt["sha256"],
        "scope": "36 entries in this captured DRC catalogue; not a census of all funded awards",
        "studies": studies}, indent=2, ensure_ascii=False) + "\n")
    blocks = []
    for study in studies:
        blocks.append("\n".join(f"{key}: {json.dumps(value, ensure_ascii=False)}"
                    for key, value in study.items()
                    if key not in {"documentation_file", "catalogue_source_sha256", "dbgap_source_sha256", "catalogue_selector"}))
    document("study_catalogue", "Kids First participating studies — captured DRC catalogue",
             "\n\n".join(blocks), receipt,
             "all 36 .publication[data-phs] cards; all data fields except individual-level historical data-notes; visible labels and dates",
             "data resource catalogue")

    manifest = {"version": 1, "profile": "neutral", "naming": {"KIDS_FIRST": {
        "canonical_label": "Gabriella Miller Kids First Data Resource", "variants": ["Kids First Data Resource"]}},
        "scope": {"KIDS_FIRST": {"referent": "the Kids First Data Resource as a collection of pediatric genomic and clinical studies",
            "referent_id": "https://kidsfirstdrc.org/", "referent_note":
            "Resource-level documentation. The captured DRC catalogue enumerates 36 distinct dbGaP studies. "
            "Keep study-specific populations, eligibility, releases, consent/access and data issues distinct. "
            "NIH award-abstract pages also describe funded projects; funding alone does not establish release. "
            "The nominated AJHG article is represented by its metadata and abstract; full text was unavailable."}},
        "projects": {"KIDS_FIRST": {"bundle": "KIDS_FIRST_preprocessed.txt", "source_dir": "processed",
                                    "raw_dir": "raw", "sources": sources}}}
    keep(HERE / "manifest.yaml", yaml.safe_dump(manifest, sort_keys=False, allow_unicode=True))
    keep(HERE / "extraction.json", json.dumps({"recipe_sha256": sha(Path(__file__)), "documents": extraction,
          "study_count": len(studies), "full_article_captured": False,
          "omissions": ["article full text blocked by publisher", "participant identifier mappings in catalogue data-notes",
                        "individual-level data files and authorized data-access-request listings"]}, indent=2) + "\n")
    print(json.dumps({"source_documents": len(sources), "catalogue_studies": len(studies),
                      "processed_bytes": sum(row["processed_bytes"] for row in extraction),
                      "article_representation": "metadata and abstract"}))


if __name__ == "__main__":
    main()
