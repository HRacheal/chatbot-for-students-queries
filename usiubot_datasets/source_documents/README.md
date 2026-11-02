# Source documents

One folder per original PDF. The PDFs themselves stay in the project root, unchanged and not copied (see `../validation_reports/pdf_integrity.json`).

- `document_metadata.json`: file name, SHA-256, size, page count, PDF metadata dates, title, institution, academic year, publication date, source URL status, table of contents (handbook) and layout-processing log.
- `extracted_text_by_page.md`: the raw text layer exactly as pypdf returned it, page by page. This is the reference for checking every extracted record.
