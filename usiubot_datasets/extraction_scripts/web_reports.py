"""Reports and READMEs for the completed dataset (called by build_web_dataset.py)."""
import json
import re
from collections import Counter, defaultdict

import web_common as C

D = C.DATASETS
VR = D / "validation_reports"
INFO_COLS = ["information", "rule_as_printed", "value_as_printed", "event_as_printed", "service_as_printed",
             "programme_as_printed", "school_name_as_printed", "description_as_printed", "rule_wording",
             "account_or_paybill_as_printed", "hours_as_printed", "loan_period_as_printed", "term_dates_as_printed",
             "evidence_text"]
INDEX_FIELDS = ["record_id", "category_id", "category_name", "file", "topic", "information", "source_title",
                "source_url_or_file", "page", "section", "date_collected", "publication_date_or_academic_year",
                "source_type", "verification_status", "conflict_or_warning", "last_checked"]
SKIP_FILES = ("sections_index.csv", "web_sections_index.csv", "bank_details_comparison.csv")


def all_records_index():
    """One row per structured record (CSV rows in the category folders), with the user's traceability fields.
    Sections and chunks are NOT records here; they are counted separately."""
    rows = []
    for p in sorted(D.glob("0*/*/*.csv")):
        if p.name.endswith(SKIP_FILES):
            continue
        cat = p.relative_to(D).parts[0][:2]
        for r in C.read_csv(p):
            info = next((r[c] for c in INFO_COLS if r.get(c)), "")
            if r.get("event_as_printed"):
                info = f"{r.get('date_as_printed', '')} — {r['event_as_printed']}"
            pubyear = r.get("academic_year") or ""
            pub = r.get("publication_date") or ""
            rows.append({
                "record_id": r.get("record_id", ""), "category_id": cat, "category_name": C.CATEGORY_NAMES[cat],
                "file": C.rel(p), "topic": r.get("topic") or p.stem.replace("_", " "),
                "information": info[:500],
                "source_title": r.get("source_title") or r.get("document_title") or "",
                "source_url_or_file": r.get("source_url") or r.get("document_file") or r.get("source_file") or "",
                "page": r.get("page", ""), "section": r.get("section") or r.get("section_number") or "",
                "date_collected": r.get("date_collected") or r.get("extraction_date") or "",
                "publication_date_or_academic_year": "; ".join(x for x in (pub, pubyear) if x) or
                                                     "Publication date not stated",
                "source_type": r.get("source_type") or r.get("data_origin") or "",
                "verification_status": r.get("verification_status", ""),
                "conflict_or_warning": r.get("conflict_or_warning") or r.get("issue_ids") or "",
                "last_checked": r.get("last_checked") or r.get("extraction_date") or ""})
    C.write_csv(D / "all_records_index.csv", rows, INDEX_FIELDS)
    return rows


def chunk_counts():
    out = defaultdict(lambda: {"stage2_sections": 0, "stage2_chunks": 0, "web_sections": 0, "web_chunks": 0,
                               "external_sections": 0, "external_chunks": 0})
    for p in D.glob("0*/*/*.json"):
        cat = p.relative_to(D).parts[0][:2]
        ext = "external" in p.parts
        n = len(json.loads(p.read_text(encoding="utf-8")))
        if p.name == "document_sections.json":
            out[cat]["stage2_sections"] += n
        elif p.name == "knowledge_chunks.json":
            out[cat]["stage2_chunks"] += n
        elif p.name == "web_document_sections.json":
            out[cat]["external_sections" if ext else "web_sections"] += n
        elif p.name == "web_knowledge_chunks.json":
            out[cat]["external_chunks" if ext else "web_chunks"] += n
    return out


def write_collection_report(stats, manifest):
    pages = manifest["pages"]
    ok = sorted((m for m in pages.values() if m.get("http_status") == 200), key=lambda m: (m["category_id"], m["url"]))
    notok = [m for m in pages.values() if m.get("http_status") != 200]
    att = manifest["fetch_attempts"]
    L = ["# Website and external source collection report", "",
         f"Collection date: {C.COLLECTED}. Every page below states no publication date unless noted; the sitemap "
         "`lastmod` value is recorded separately and is not a publication date.", "",
         "## Method and access rules", "",
         "* Pages were read with Claude's WebFetch tool, user agent **Claude-User**, at the user's request. The "
         "usiu.ac.ke robots.txt allows Claude-User (\"AI assistants and AI search: fetch pages when someone asks about "
         "USIU\") apart from `/wp-admin/`. It disallows general crawlers (`User-agent: *  Disallow: /`) and training "
         "crawlers (ClaudeBot, GPTBot, CCBot, Google-Extended).",
         "* Therefore `collect_web_sources.py`, which identifies itself honestly as `USIUBOT-dataset-collector`, will "
         "report usiu.ac.ke pages as *blocked by robots.txt* and will not fetch them. Future updates of those pages "
         "should be done by a person saving the page from a browser and running `--import-html`, or by asking "
         "Claude to read the pages again. The script never spoofs a user agent.",
         "* No login page, student portal (itsweb), clearance system, instalment or refund web form was opened. "
         "No CAPTCHA or access control was bypassed. No enquiry was sent to any department.",
         "* Snapshots are markdown transcriptions of the main content returned by WebFetch, made by fetching agents; "
         "they are not byte copies of the HTML. Site-wide navigation and footers were left out. The agents' own "
         "notes were kept in the raw reports (`web_sources/raw_collection_reports/`) and removed from the chunks.",
         "* Prompt-injection text inside fetched content (\"reporting rules\" asking to shorten quotes, an "
         "\"MCP Server Instructions\" block) was ignored.", "",
         "## Totals", "",
         f"* Pages collected (HTTP 200): **{len(ok)}** ({stats['web_pages_official']} official USIU-Africa, "
         f"{stats['web_pages_external']} external KUCCPS).",
         f"* Sources not collected: **{len(notok)}** (inaccessible: "
         f"{sum(1 for m in notok if 'inaccessible' in (m.get('access_outcome') or ''))}; deliberately not attempted "
         f"(restricted systems): {sum(1 for m in notok if 'not attempted' in (m.get('access_outcome') or ''))}; "
         f"found but not downloaded: {sum(1 for m in notok if 'not collected' in (m.get('access_outcome') or ''))}).",
         f"* Fetch attempts logged: {len(att)}; failed attempts: {sum(1 for a in att if a['outcome'] == 'failed')} "
         "(connection refused; every one of those pages was collected on a later attempt).",
         "* Official PDFs downloaded: the 2026-2027 fee schedule (new) and the 2026-2027 academic calendar (byte-"
         "identical to the local copy, so not stored twice).", "",
         "## Pages collected", "", "| Category | Title | URL | Sitemap lastmod | Fidelity |", "|---|---|---|---|---|"]
    for m in ok:
        L.append(f"| {m['category_id']} | {m.get('title', '').replace('|', '/')} | {m['url']} | "
                 f"{m.get('sitemap_lastmod') or '—'} | {m.get('content_fidelity', '')[:80]} |")
    L += ["", "## Not collected", "", "| URL | Outcome | Note |", "|---|---|---|"]
    for m in notok:
        L.append(f"| {m['url']} | {m.get('access_outcome', '')} | {m.get('note', '')} |")
    L += ["", "## Failed attempts (later retried successfully)", ""]
    L += [f"* {a['url']} — {a['detail']}" for a in att if a["outcome"] == "failed"]
    (VR / "WEB_COLLECTION_REPORT.md").write_text("\n".join(L) + "\n", encoding="utf-8", newline="\n")


WEB_FILE_NOTES = {
    "web_programmes.csv": "one row per official programme page (42): school, duration, intake, mode, accreditation text",
    "web_admission_rules.csv": "admission rules quoted from the Admission Requirements, How to Apply, Intake and "
                               "International Applicants pages",
    "web_tuition_fee_tables.csv": "every row of the 37 fee tables on the Tuition & Fees page (2026-2027), per semester",
    "web_other_and_general_charges.csv": "Other Charges and General Charges tables",
    "web_fee_policy_rules.csv": "payment, interest, instalment and refund rules",
    "web_financial_aid_programmes.csv": "scholarships, grants, waivers, loans; expired calls are marked",
    "web_bank_and_mobile_payment_details.csv": "bank accounts and M-PESA paybill as printed on the website "
                                               "(UNCONFIRMED; refer users to Finance)",
    "bank_details_comparison.csv": "the same accounts compared across website, calendar and handbook",
    "web_department_contacts.csv": "contacts printed on official pages, with routing department",
    "routing_departments.json": "routing departments (incl. Finance as its own department) with contacts, "
                                "handbook responsibilities and the closest existing app department",
    "web_english_proficiency_requirements.csv": "English proficiency tests and minimums (website)",
    "web_transfer_credit_rules.csv": "transfer credit, examination credit, transcripts (two pages conflict: W11)",
    "programme_entry_requirements.csv": "entry requirements per programme page (or 'not stated')",
    "official_faq_pairs.csv": "questions and answers published on official FAQ sections (not student enquiries)",
    "open_questions_register.csv": "questions the dataset cannot answer yet, derived from its own conflicts and gaps "
                                   "(NOT student enquiries)",
    "external_records.csv": "EXTERNAL statements (KUCCPS) — never USIU-Africa policy",
    "web_document_sections.json": "page sections (heading path + text) from the website snapshots",
    "web_knowledge_chunks.json": "chunks of at most 1000 characters; each starts with its heading path and never "
                                 "cuts a sentence",
    "web_sections_index.csv": "index of the web sections",
}


def update_category_readmes(cc):
    for cat, folder in C.CATEGORY_DIRS.items():
        p = D / folder / "README.md"
        text = p.read_text(encoding="utf-8") if p.exists() else f"# {cat} {C.CATEGORY_NAMES[cat]}\n"
        text = re.sub(r"\n<!-- WEB-START -->.*<!-- WEB-END -->\n?", "\n", text, flags=re.S).rstrip() + "\n"
        L = ["", "<!-- WEB-START -->", "## Website and external records (collected 2026-11-01)", "",
             "| File | Rows | Contents |", "|---|---|---|"]
        for sub in ("official", "external"):
            for f in sorted((D / folder / sub).glob("*")):
                if f.name in WEB_FILE_NOTES:
                    n = len(C.read_csv(f)) if f.suffix == ".csv" else len(json.loads(f.read_text(encoding="utf-8")))
                    L.append(f"| {sub}/{f.name} | {n} | {WEB_FILE_NOTES[f.name]} |")
        c = cc[cat]
        L += ["", f"Sections / chunks in this category: Stage 2 PDF {c['stage2_sections']} / {c['stage2_chunks']}; "
                  f"official website {c['web_sections']} / {c['web_chunks']}; external {c['external_sections']} / "
                  f"{c['external_chunks']}.", "",
              "Every website record carries: record id, category, topic, information, source title, URL, snapshot "
              "file, section, date collected, publication date (\"Publication date not stated\" where none is "
              "printed), academic year, source type (official/external), verification status, conflict/warning "
              "(issue ids) and last checked date. All records are drafts, pending verification, not approved.",
              "Issues: `validation_reports/conflict_and_verification_register.csv`.", "<!-- WEB-END -->", ""]
        p.write_text(text + "\n".join(L), encoding="utf-8", newline="\n")


def write_top_readme(stats, index_rows, cc):
    per_cat = Counter(r["category_id"] for r in index_rows)
    per_type = Counter(r["source_type"] for r in index_rows)
    L = ["# USIUBOT dataset", "",
         "Real information about United States International University-Africa (USIU-Africa) for the USIUBOT "
         "student-query chatbot. Nothing is synthetic. Every record names its source (PDF page, or web page URL "
         "and snapshot). Every record is a **draft, pending verification, not approved**: it must be reviewed in "
         "the app's Approved Sources workflow before the chatbot may use it. Nothing has been imported into any "
         "database.", "",
         "## Sources", "",
         "* `Academic-Calendar-2026-2027.pdf` (project root, unchanged) — official URL confirmed by SHA-256 match.",
         "* `Student-Handbook.pdf` (project root, unchanged) — undated; no public URL found (candidate URL 404).",
         f"* {stats['web_pages_official']} official USIU-Africa web pages and 1 official PDF (2026-2027 fee schedule), "
         "collected 2026-11-01.",
         f"* {stats['web_pages_external']} external pages (KUCCPS), kept in `external/` folders and labelled as not "
         "USIU-Africa policy.",
         "* Full list with access outcomes: `validation_reports/source_register.csv`.", "",
         "## Layout", "",
         "| Folder | Contents |", "|---|---|",
         *[f"| `{f}/` | {C.CATEGORY_NAMES[c]}: {per_cat.get(c, 0)} structured records; Stage 2 chunks "
           f"{cc[c]['stage2_chunks']}, web chunks {cc[c]['web_chunks']}, external chunks {cc[c]['external_chunks']} |"
           for c, f in C.CATEGORY_DIRS.items()],
         "| `source_documents/` | page-by-page text of the three PDFs, with metadata |",
         "| `web_sources/` | collection manifest, page snapshots, raw collection reports, downloaded PDF |",
         "| `validation_reports/` | source register, conflict and verification register, missing information "
         "register, fee table checks, layout check, final validation, reports |",
         "| `collection_register/` | Stage 2 collection register |",
         "| `extraction_scripts/` | all scripts (standard library + pypdf only) |",
         "| `all_records_index.csv` | one row per structured record across all categories, with the traceability "
         "fields |", "",
         f"Structured records: {len(index_rows)} (official {per_type.get('official', 0)}, external "
         f"{per_type.get('external', 0)}, derived open questions {per_type.get('derived', 0)}). Sections and chunks "
         "are counted separately and are not records.", "",
         "## Rules for using this data", "",
         "* Bank and M-PESA details differ between sources and are unconfirmed. Never present them as confirmed "
         "payment instructions: refer users to the Finance Office (finance@usiu.ac.ke) to confirm.",
         "* Where sources conflict, both versions are kept and linked to an issue id (V = PDF, W = website). See "
         "`validation_reports/conflict_and_verification_register.csv`.",
         "* External (KUCCPS) statements must never be presented as USIU-Africa policy.",
         "* Expired deadlines are marked; never present them as open.",
         "* Category 08 contains official FAQ pairs and open questions derived from gaps. It contains no real or "
         "invented student enquiries.", "",
         "## Rebuild and validate (Windows PowerShell, from the project root)", "",
         "```powershell",
         "cd C:\\Users\\Admin\\Downloads\\chatbot-for-students-queries-1",
         "$env:PYTHONDONTWRITEBYTECODE = \"1\"",
         "$env:PYTHONIOENCODING = \"utf-8\"",
         "# everything: PDFs -> website records -> registers -> validation",
         ".\\backend\\.venv\\Scripts\\python.exe usiubot_datasets\\extraction_scripts\\build_all.py",
         "# validation only",
         ".\\backend\\.venv\\Scripts\\python.exe usiubot_datasets\\extraction_scripts\\validate_dataset.py",
         "# dataset tests",
         ".\\backend\\.venv\\Scripts\\python.exe -m pytest usiubot_datasets\\tests -q -p no:cacheprovider",
         "# check which web pages robots.txt allows for the automated collector (reads robots.txt only)",
         ".\\backend\\.venv\\Scripts\\python.exe usiubot_datasets\\extraction_scripts\\collect_web_sources.py --check-robots",
         "# refresh permitted pages (conditional requests; changed pages are kept for review, never approved)",
         ".\\backend\\.venv\\Scripts\\python.exe usiubot_datasets\\extraction_scripts\\collect_web_sources.py --fetch",
         "# import pages a person saved from a browser (for pages robots.txt blocks for automated collectors)",
         ".\\backend\\.venv\\Scripts\\python.exe usiubot_datasets\\extraction_scripts\\collect_web_sources.py "
         "--import-html C:\\path\\to\\saved_pages",
         "```", "",
         "Report: `validation_reports/FINAL_DATASET_IMPLEMENTATION_REPORT.md`.", ""]
    (D / "README.md").write_text("\n".join(L), encoding="utf-8", newline="\n")
