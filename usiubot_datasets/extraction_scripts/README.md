# Extraction scripts

```
backend/.venv/Scripts/python.exe usiubot_datasets/extraction_scripts/extract_documents.py --extraction-date 2026-11-01
```

Run from the project root. Uses only packages already installed in the backend virtual environment (pypdf, langchain-text-splitters). No network, no database, no OCR.

- `extract_documents.py`: reads both PDFs read-only, checks their SHA-256 before and after, extracts sections, chunks, calendar events and tables, and writes everything in this folder tree. It regenerates all outputs (deterministic for a given extraction date).
- `extraction_config.py`: layout fixes for the handbook (headings, two-column text moved into place, placeholders), the category mapping, the curated structured rows, the issues and the coverage list. Every curated row has an evidence quote; the run stops if any quote is not found on its page.

Known limits: the text layer has no table structure, so tables are kept as lines; paragraph breaks after numbered lists are not always recoverable (words are never changed); scanned images would need OCR (none are present: every page with content has a text layer).
