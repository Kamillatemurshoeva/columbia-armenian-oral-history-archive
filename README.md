# Columbia Armenian Oral History Archive Scraper — 

This repository contains a Python scraper designed to extract **metadata from the Columbia Armenian Oral History Archive**.

The project is part of **Open Data Armenia**, an initiative that aims to collect, organize, and document **Armenian cultural heritage around the world**.

---

## Open Data Armenia

**Open Data Armenia** is a digital humanities initiative focused on building structured datasets about Armenian cultural heritage preserved in institutions worldwide.

The initiative aims to:

- document Armenian heritage across global archives, libraries, museums, and digital collections
- make Armenian cultural data more discoverable
- support digital humanities and historical research
- create reusable open datasets for scholars, students, and developers
- improve visibility of Armenian historical collections around the world

Repositories in this initiative collect **metadata only**, while original materials remain hosted by their custodial institutions and rights holders.

---

## Project Goals

This repository aims to:

- collect structured metadata about Armenian cultural heritage materials
- improve discoverability of Armenian heritage collections
- support digital humanities research
- document Armenian oral history materials preserved in a major academic archive

The project focuses on **metadata extraction only**, not copying or redistributing original materials.

---

## Data Source

**Platform:** Columbia University Libraries  
**Collection:** Columbia Armenian Oral History Archive  
**Collection dates:** 1968–1977  
**Collection URL:** https://findingaids.library.columbia.edu/archives/cul-5321412_aspace_a06820e02550cf1839ca72f49e0c8ab9

The archive contains oral history material related to Armenian experiences and testimonies, including first-person accounts and archival descriptions.

---

## What the Scraper Does

The script:

1. accesses the archive interface
2. retrieves item links
3. visits each item page
4. extracts structured metadata
5. cleans and normalizes fields
6. exports structured datasets

The scraper collects **metadata only** and links back to the original records.

---

## Exported Data Fields

The dataset contains the following fields when available:

| Field | Description |
|------|-------------|
| title | Item or interview title |
| date_period | Date or period associated with the record |
| author_creator | Creator, interviewee, interviewer, or related name |
| description_abstract | Description, abstract, scope note, or summary |
| box_folder | Box/folder reference when available |
| original_url | Link to the original archival record |

---


## Installation

Clone the repository:

git clone REPOSITORY_URL

Create a virtual environment:

python -m venv .venv

Activate the environment:

source .venv/bin/activate

Install dependencies:

pip install -r requirements.txt

Install Playwright browser support:

playwright install chromium

---

## Usage

Run the scraper:

python main.py

Run the GitHub document generator:

python generate_github_docs.py

The scraper will export:

columbia_armenian_oral_history_archive.csv  
columbia_armenian_oral_history_archive.jsonl  

It may also generate:

debug_links.json

---

## Dataset

The repository includes structured datasets exported in:

- CSV format
- JSONL format

The dataset contains **metadata only** and links back to the original Columbia archival records.

---

## License

See the `LICENSE` file.

---

## Rights Notice

This repository is part of **Open Data Armenia**.

All copyrights to the original collection materials,
including interview recordings, audio materials, transcripts, descriptions,
institutional metadata, and archival records belong to **their respective owners and custodial institutions**.

This repository **does not claim ownership over the original materials**.

The project only collects and structures publicly available metadata.

Users wishing to reuse original materials should consult the source institution's policies and the relevant rights holders.

For additional details, see `DATA_RIGHTS.md`.

---

## Disclaimer

This project is an independent research effort.

It is **not officially affiliated with Columbia University Libraries** unless explicitly stated.

---

## Author

**Open Data Armenia**
