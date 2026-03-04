#!/usr/bin/env python3
"""
Download all MediaWiki History TSV dumps from a Wikimedia "mediawiki_history" directory.

Example:
  python download_mw_history.py \
    --base-url "https://dumps.wikimedia.org/other/mediawiki_history/2026-01/enwiki/" \
    --out "./mw_history_enwiki_2026-01"

Notes:
- Downloads all files ending in .tsv.bz2 found in the directory listing.
- Resumes partial downloads using HTTP Range requests when possible.
"""

import argparse
import os
import re
import sys
import time
from urllib.parse import urljoin
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

TSV_BZ2_RE = re.compile(r'href="([^"]+\.tsv\.bz2)"', re.IGNORECASE)

def fetch_html(url: str) -> str:
    req = Request(url, headers={"User-Agent": "mw-history-downloader/1.0"})
    with urlopen(req, timeout=60) as resp:
        charset = resp.headers.get_content_charset() or "utf-8"
        return resp.read().decode(charset, errors="replace")

def list_files(base_url: str) -> list[str]:
    html = fetch_html(base_url)
    files = TSV_BZ2_RE.findall(html)

    # Some listings include duplicates or full paths; normalize to unique filenames.
    normalized = []
    seen = set()
    for href in files:
        # href might be "2026-01.enwiki.2001-01.tsv.bz2" or "./2026-01...."
        fname = href.split("/")[-1]
        if fname not in seen:
            seen.add(fname)
            normalized.append(fname)

    # Sort for sanity (oldest->newest usually)
    normalized.sort()
    return normalized

def remote_size(url: str) -> int | None:
    """Try to get remote Content-Length via HEAD (falls back to GET headers)."""
    for method in ("HEAD", "GET"):
        try:
            req = Request(url, method=method, headers={"User-Agent": "mw-history-downloader/1.0"})
            with urlopen(req, timeout=60) as resp:
                cl = resp.headers.get("Content-Length")
                return int(cl) if cl else None
        except Exception:
            continue
    return None

def download_one(url: str, out_path: str, retries: int = 5, sleep_s: float = 1.5) -> None:
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    existing = os.path.getsize(out_path) if os.path.exists(out_path) else 0
    total = remote_size(url)

    # If already complete, skip
    if total is not None and existing == total and total > 0:
        print(f"[SKIP] {os.path.basename(out_path)} (already downloaded)")
        return

    attempt = 0
    while True:
        attempt += 1
        try:
            headers = {"User-Agent": "mw-history-downloader/1.0"}
            mode = "wb"
            if existing > 0:
                headers["Range"] = f"bytes={existing}-"
                mode = "ab"

            req = Request(url, headers=headers)
            with urlopen(req, timeout=60) as resp:
                # If server ignored Range, start over
                if existing > 0 and resp.status == 200:
                    print(f"[WARN] Server ignored Range; restarting {os.path.basename(out_path)}")
                    existing = 0
                    mode = "wb"

                # Determine expected total for progress display
                resp_len = resp.headers.get("Content-Length")
                resp_len = int(resp_len) if resp_len else None
                expected_total = (existing + resp_len) if resp_len is not None else total

                print(f"[DOWN] {os.path.basename(out_path)}  ({existing} bytes existing)")
                bytes_written = 0
                t0 = time.time()

                with open(out_path, mode) as f:
                    while True:
                        chunk = resp.read(1024 * 1024)  # 1MB
                        if not chunk:
                            break
                        f.write(chunk)
                        bytes_written += len(chunk)

                        # lightweight progress
                        if expected_total:
                            done = existing + bytes_written
                            pct = 100.0 * done / expected_total if expected_total else 0
                            dt = max(time.time() - t0, 0.001)
                            rate = done / dt / (1024 * 1024)
                            sys.stdout.write(f"\r      {pct:6.2f}%  {rate:6.2f} MB/s")
                            sys.stdout.flush()

                if expected_total:
                    sys.stdout.write("\n")

            # Verify size if known
            final_size = os.path.getsize(out_path)
            if total is not None and final_size != total:
                raise RuntimeError(f"Incomplete download: got {final_size}, expected {total}")

            print(f"[OK]   {os.path.basename(out_path)} ({final_size} bytes)")
            return

        except (HTTPError, URLError, TimeoutError, RuntimeError) as e:
            if attempt >= retries:
                raise
            print(f"[RETRY {attempt}/{retries}] {os.path.basename(out_path)} -> {e}")
            time.sleep(sleep_s)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", required=True,
                    help="Directory URL, e.g. https://dumps.wikimedia.org/other/mediawiki_history/2026-01/enwiki/")
    ap.add_argument("--out", required=True, help="Output folder")
    ap.add_argument("--only-match", default=None,
                    help="Optional regex to filter filenames (e.g. '200[1-9]-|201[0-9]-|202[0-6]-')")
    ap.add_argument("--max-files", type=int, default=None, help="Optional limit for testing")
    args = ap.parse_args()

    base_url = args.base_url
    if not base_url.endswith("/"):
        base_url += "/"

    files = list_files(base_url)
    if not files:
        print("No .tsv.bz2 files found. Double-check the base URL.")
        sys.exit(1)

    if args.only_match:
        filt = re.compile(args.only_match)
        files = [f for f in files if filt.search(f)]

    if args.max_files is not None:
        files = files[:args.max_files]

    print(f"Found {len(files)} files.")
    for i, fname in enumerate(files, 1):
        url = urljoin(base_url, fname)
        out_path = os.path.join(args.out, fname)
        print(f"\n[{i}/{len(files)}] {fname}")
        download_one(url, out_path)

    print("\nAll done.")

if __name__ == "__main__":
    main()