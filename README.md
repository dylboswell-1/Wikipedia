# Wikipedia Dump Pipeline (MediaWiki History)

## Overview
This project downloads and processes Wikipedia edit history data from the MediaWiki History dumps. The data is stored on a Chapman University network share and processed using bash and Python scripts.

---

## Prerequisites
You need ONE of the following:

- Connected to Chapman University network (on-campus), OR
- Connected via BigEdge VPN using Chapman credentials  

Also required:
- bash
- python3

---

## Step 1 — Network Access
If you are off-campus:
1. Open BigEdge VPN client  
2. Log in using Chapman credentials  
3. Confirm connection before continuing  

If you are on-campus, you can skip VPN.

---

## Step 2 — Connect to Network Share
Mount the shared drive:

smb://filersmb.chapman.edu/dpt/wikimedia/Data

### macOS (Finder)
- Open Finder  
- Press Cmd + K  
- Paste the link above  
- Log in with Chapman credentials  

This will mount the drive (typically at):
/Volumes/Data

---

## Step 3 — Navigate to Project Directory
cd /Volumes/dpt/wikimedia

---

## Step 4 — Download Data
bash download_all.sh

---

## Step 5 — Decompress Data
bash decompress.sh

---

## File Structure
/Volumes/Data/
├── wiki-data/
│   ├── *.tsv.bz2
├── wiki-data-decompressed/
│   ├── *.tsv

- wiki-data/ stores compressed dump files  
- wiki-data-decompressed/ stores decompressed .tsv files  

---

## Scripts
- download_all.sh → downloads dump files  
- decompress.sh → decompresses .bz2 files  
- download_wikis.py → handles downloading logic  

---

## Quick Start
# connect to VPN OR be on campus network

# mount share
smb://filersmb.chapman.edu/dpt/wikimedia/Data

# run pipeline
bash download_and_decompress.sh
