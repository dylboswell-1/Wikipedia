#!/bin/bash

# Wikipedia dump directory
BASE_URL="https://dumps.wikimedia.org/other/mediawiki_history/2026-02/enwiki/"

# Where the files will be saved
OUT_DIR="./wiki_dumps"

# Run the downloader
python3 download_wikis.py \
  --base-url "$BASE_URL" \
  --out "$OUT_DIR"