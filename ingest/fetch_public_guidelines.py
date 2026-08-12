"""
Fetch authoritative, openly-licensed clinical guideline PDFs into a folder for
review, then ingest them with ingest_documents.py.

WHY a separate step: for a clinical tool you must *review and approve* source
material before it becomes answerable. This script only downloads; it does not
auto-ingest. You review the files, confirm licensing for your use, then run the
ingestion with the right metadata (department, effective/expiry dates, etc.).

Usage:
    python ingest/fetch_public_guidelines.py                 # uses the built-in manifest
    python ingest/fetch_public_guidelines.py --manifest my_sources.json --out-dir ./public_guidelines

Then, after reviewing the downloaded files:
    python ingest/ingest_documents.py --input-dir ./public_guidelines \
        --department "Guidelines" --approval-status approved \
        --effective-date 2026-01-01 --version WHO/CDC

LICENSING — read before redistributing:
  * CDC materials: generally U.S. Government works, public domain (verify per page).
  * WHO publications: typically CC BY-NC-SA 3.0 IGO — attribution + non-commercial.
  * StatPearls (NCBI Bookshelf): open access, often CC BY.
  Always confirm the exact license on each document and that your use complies.
  These are examples; replace the manifest with the exact PDF URLs you have vetted.
"""
import argparse
import json
import os
import urllib.request

# Template manifest. Replace the URLs with the exact, vetted PDF links you intend
# to use. `url` must point at a downloadable file (usually a .pdf).
DEFAULT_MANIFEST = [
    {
        "doc_id": "WHO-BEC-2018",
        "title": "WHO Basic Emergency Care (BEC)",
        "source": "World Health Organization",
        "license": "CC BY-NC-SA 3.0 IGO (verify)",
        "url": "https://REPLACE-WITH-VETTED-URL/who-basic-emergency-care.pdf",
    },
    {
        "doc_id": "CDC-INFECTION-CONTROL",
        "title": "CDC Healthcare Infection Control Guidance",
        "source": "Centers for Disease Control and Prevention",
        "license": "U.S. Gov / public domain (verify)",
        "url": "https://REPLACE-WITH-VETTED-URL/cdc-infection-control.pdf",
    },
]


def fetch(entry, out_dir):
    url = entry["url"]
    if "REPLACE-WITH-VETTED-URL" in url:
        print(f"  SKIP {entry['doc_id']}: placeholder URL — edit the manifest with a real, vetted PDF link.")
        return False
    fname = os.path.join(out_dir, f"{entry['doc_id']}.pdf")
    if os.path.exists(fname):
        print(f"  exists, skipping: {fname}")
        return True
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "clinical-kb-fetcher/1.0"})
        with urllib.request.urlopen(req, timeout=60) as r, open(fname, "wb") as f:
            f.write(r.read())
        print(f"  downloaded: {fname}  ({entry.get('source','')}, license: {entry.get('license','?')})")
        return True
    except Exception as e:  # noqa: BLE001
        print(f"  FAILED {entry['doc_id']}: {e}")
        return False


def main():
    ap = argparse.ArgumentParser(description="Download openly-licensed clinical guideline PDFs for review + ingestion.")
    ap.add_argument("--manifest", default=None, help="JSON file: list of {doc_id,title,source,license,url}")
    ap.add_argument("--out-dir", default="./public_guidelines", help="Where to save downloaded PDFs")
    args = ap.parse_args()

    manifest = DEFAULT_MANIFEST
    if args.manifest:
        with open(args.manifest) as f:
            manifest = json.load(f)

    os.makedirs(args.out_dir, exist_ok=True)
    print(f"Fetching {len(manifest)} source(s) into {args.out_dir} ...")
    ok = sum(fetch(e, args.out_dir) for e in manifest)
    # write provenance manifest alongside the files
    with open(os.path.join(args.out_dir, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"\nDone: {ok}/{len(manifest)} available in {args.out_dir}.")
    print("Next: review the PDFs + confirm licensing, then ingest, e.g.:")
    print(f'  python ingest/ingest_documents.py --input-dir "{args.out_dir}" '
          f'--department Guidelines --approval-status approved --effective-date 2026-01-01')


if __name__ == "__main__":
    main()
