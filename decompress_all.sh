#!/bin/bash

set -e

DIR="./wiki_dumps"

count=0
total=$(ls "$DIR"/*.tsv.bz2 2>/dev/null | wc -l)

echo "Found $total compressed files"

for file in "$DIR"/*.tsv.bz2
do
    count=$((count+1))
    
    echo "[$count/$total] Decompressing $(basename "$file")"
    
    bunzip2 "$file"
    
done

echo "All files decompressed."