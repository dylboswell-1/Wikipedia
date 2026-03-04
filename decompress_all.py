#!/usr/bin/env python3
"""
Decompress all *.tsv.bz2 files in a directory to *.tsv.

Usage:
  python decompress_all.py --in-dir ./wiki_dumps
  python decompress_all.py --in-dir ./wiki_dumps --delete-original
  python decompress_all.py --in-dir ./wiki_dumps --out-dir ./wiki_tsvs
"""

import argparse
import bz2
import os
from pathlib import Path
import sys
import time

CHUNK_SIZE = 1024 * 1024  # 1 MB

def decompress_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)

    # Stream decompress to avoid loading into memory
    with bz2.open(src, "rb") as fin, open(dst, "wb") as fout:
        while True:
            chunk = fin.read(CHUNK_SIZE)
            if not chunk:
                break
            fout.write(chunk)

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in-dir", required=True, help="Folder containing .tsv.bz2 files")
    ap.add_argument("--out-dir", default=None, help="Where to write .tsv files (default: same as in-dir)")
    ap.add_argument("--delete-original", action="store_true", help="Delete .bz2 after successful decompression")
    ap.add_argument("--skip-existing", action="store_true", default=True, help="Skip if output .tsv already exists")
    args = ap.parse_args()

    in_dir = Path(args.in_dir).expanduser().resolve()
    out_dir = Path(args.out_dir).expanduser().resolve() if args.out_dir else in_dir

    if not in_dir.exists() or not in_dir.is_dir():
        print(f"Error: --in-dir not found or not a directory: {in_dir}", file=sys.stderr)
        return 2

    files = sorted(in_dir.glob("*.tsv.bz2"))
    if not files:
        print(f"No .tsv.bz2 files found in {in_dir}")
        return 0

    print(f"Found {len(files)} files.")
    for i, src in enumerate(files, 1):
        dst = out_dir / src.name[:-4]  # remove trailing ".bz2" -> leaves ".tsv"

        if dst.exists():
            print(f"[SKIP {i}/{len(files)}] {dst.name} already exists")
            continue

        t0 = time.time()
        print(f"[{i}/{len(files)}] Decompressing {src.name} -> {dst.name}")
        try:
            decompress_file(src, dst)
        except Exception as e:
            # If something fails mid-write, remove partial output so retries are clean
            if dst.exists():
                try:
                    dst.unlink()
                except Exception:
                    pass
            print(f"  ERROR: {src.name}: {e}", file=sys.stderr)
            return 1

        dt = max(time.time() - t0, 0.001)
        out_size = dst.stat().st_size
        mb_s = (out_size / (1024 * 1024)) / dt
        print(f"  OK: wrote {out_size} bytes ({mb_s:.2f} MB/s)")

        if args.delete_original:
            try:
                src.unlink()
                print("  Deleted original .bz2")
            except Exception as e:
                print(f"  WARN: could not delete {src.name}: {e}", file=sys.stderr)

    print("Done.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())