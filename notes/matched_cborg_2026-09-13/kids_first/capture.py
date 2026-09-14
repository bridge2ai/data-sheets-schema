"""Capture public documentation with original bytes and dated receipts.

No credentials, participant endpoints, data files or automatic retries.
Re-running a successful capture reuses its verified original bytes.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

HERE = Path(__file__).resolve().parent


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def fetch(identifier, url):
    if not re.fullmatch(r"[a-z0-9_]+", identifier) or urlparse(url).scheme != "https":
        raise ValueError("expected a safe identifier and an HTTPS public source")
    receipt = HERE / "captures" / f"{identifier}.json"
    path = HERE / "raw" / f"{identifier}.raw"
    if receipt.exists():
        old = json.loads(receipt.read_bytes())
        if old["url"] != url:
            raise ValueError("capture identifier already names another URL")
        if old.get("sha256") and (not path.is_file() or sha(path.read_bytes()) != old["sha256"]):
            raise ValueError("original captured bytes changed")
        return old
    info = {"id": identifier, "url": url,
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "purpose": "public documentation and aggregate study metadata"}
    try:
        request = Request(url, headers={"User-Agent": "D4D public documentation source registration"})
        try:
            response = urlopen(request, timeout=45)
        except HTTPError as error:
            response = error
        with response:
            raw = response.read(8_000_001)
            if len(raw) > 8_000_000:
                raise ValueError("public-document response exceeds 8 MB")
            info.update(http_status=response.status, final_url=response.url,
                        content_type=response.headers.get("Content-Type"),
                        etag=response.headers.get("ETag"),
                        last_modified=response.headers.get("Last-Modified"),
                        bytes=len(raw), sha256=sha(raw),
                        local_path=str(path.relative_to(HERE)),
                        status="captured_unreviewed" if response.status == 200 else "http_failure")
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as stream:
            stream.write(raw)
    except Exception as error:
        info.update(status="capture_failure", error_type=type(error).__name__)
    save(receipt, info)
    return info


def capture_many(sources):
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda row: fetch(row["id"], row["url"]), sources))
    for result in results:
        print(json.dumps({k: result.get(k) for k in ("id", "status", "http_status", "bytes")}))
    return results


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_list", type=Path)
    args = parser.parse_args()
    capture_many(json.loads(args.source_list.read_bytes()))
