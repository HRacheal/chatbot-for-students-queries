"""Configuration for the official-website and external-source part of the USIUBOT dataset.

Facts in the curated lists below are quoted from the page snapshots in web_sources/snapshots/. Every
curated record carries an `evidence` string; build_web_dataset.py stops if that string is not found
in the snapshot (whitespace-normalised). Processing notes are kept in separate `note` fields.
"""
import re
from pathlib import Path

DATASETS = Path(__file__).resolve().parents[1]
RAW = DATASETS / "web_sources" / "raw_collection_reports"
COLLECTED = "2026-11-01"

# --------------------------------------------------------------------------------------
# Page inventory: url -> category and notes. Category ids are the eight dataset categories.
# --------------------------------------------------------------------------------------
U = "https://www.usiu.ac.ke"
PAGES = {
    f"{U}/admission-requirements/": {"category": "03"},
    f"{U}/how-to-apply/": {"category": "03"},
    f"{U}/intake/": {"category": "03"},
    f"{U}/admission-fees/": {"category": "03"},
    f"{U}/international-applicants/": {"category": "03"},
    f"{U}/tuition-fees/": {"category": "04", "fidelity": "verbatim main content; fee tables rebuilt row by row "
                                                         "from flattened cells (amount counts matched every row)"},
    f"{U}/admission-fees/fee-payment-refunds/": {"category": "04"},
    f"{U}/financial-aid/": {"category": "04"},
    f"{U}/documents/on-campus-programs-fee-structure/": {"category": "04"},
    f"{U}/academics/academic-calendar/": {"category": "05"},
    f"{U}/documents/academic-calendar-2026-2027/": {"category": "05"},
    f"{U}/documents/academic-calendar-2025-2026/": {"category": "05"},
    f"{U}/pre-registration-check/": {"category": "05"},
    f"{U}/2026-48th-commencement/": {"category": "05"},
    f"{U}/resource-downloads/": {"category": "05", "fidelity": "partial: first 39,416 characters verbatim; the rest "
                                                               "came back as a model summary and is NOT used"},
    f"{U}/academics/undergraduate-programs/": {"category": "02", "fidelity": "condensed: programme cards were listed "
                                                                             "with labels, not as exact card text"},
    f"{U}/academics/masters-programs/": {"category": "02"},
    f"{U}/academics/doctoral-programs/": {"category": "02"},
    f"{U}/academics/short-courses/": {"category": "02"},
    f"{U}/academics/academic-catalog/": {"category": "02"},
    f"{U}/academics/our-schools/": {"category": "02"},
    f"{U}/admission-fees/cbet-realignment/": {"category": "02"},
    f"{U}/about-us/": {"category": "01"},
    f"{U}/about-us/faq/": {"category": "01"},
    f"{U}/about-us/accreditations/": {"category": "01"},
    f"{U}/about-us/vision-mission-values/": {"category": "01"},
    f"{U}/health-wellness/": {"category": "01"},
    f"{U}/student-life/housing-accommodation/": {"category": "01"},
    f"{U}/academics/library-and-e-resources/": {"category": "01"},
    f"{U}/student-life/": {"category": "01"},
    f"{U}/placement-careers/": {"category": "01"},
    f"{U}/disability-inclusion/": {"category": "01"},
    f"{U}/about-us/contact-us/": {"category": "06"},
    "https://www.usiu.ac.ke/wp-sitemap.xml": {"category": "01", "fidelity": "URL list only (page sitemap complete; "
                                                                            "post sitemap not listed)"},
    "https://kuccps.net/": {"category": "03", "source_type": "external",
                            "publisher": "Kenya Universities and Colleges Central Placement Service (KUCCPS)",
                            "fidelity": "relevant passages only, verbatim"},
    "https://kuccps.net/Placem": {"category": "07", "source_type": "external",
                                  "publisher": "Kenya Universities and Colleges Central Placement Service (KUCCPS)",
                                  "fidelity": "relevant passages only, verbatim"},
    "https://kuccps.net/frequently-asked-questions": {"category": "03", "source_type": "external",
                                                      "publisher": "Kenya Universities and Colleges Central Placement "
                                                                   "Service (KUCCPS)",
                                                      "fidelity": "relevant passages only, verbatim"},
}
PROGRAMME_PAGE = re.compile(r"^https://www\.usiu\.ac\.ke/programs/")


def page_info(url):
    if url in PAGES:
        return PAGES[url]
    if PROGRAMME_PAGE.match(url):
        return {"category": "02"}
    return {}


# Pages that could not be collected, or were deliberately not attempted.
FAILED_ONLY = [
    {"page_id": "cue.or.ke__home", "url": "https://www.cue.or.ke/", "http_status": None, "source_type": "external",
     "publisher": "Commission for University Education (CUE)", "category_id": "01",
     "access_outcome": "inaccessible: TLS error 'unable to verify the first certificate'",
     "note": "CUE list of accredited universities and the foreign-qualification equation procedure could not be "
             "read. Not retried (certificate error, not a transient failure)."},
    {"page_id": "knqa.go.ke__home", "url": "https://www.knqa.go.ke/", "http_status": 500, "source_type": "external",
     "publisher": "Kenya National Qualifications Authority (KNQA)", "category_id": "07",
     "access_outcome": "inaccessible: HTTP 500 Internal Server Error (robots.txt also returned 500)"},
    {"page_id": "assets__file__266ac45d-student-handbook.pdf",
     "url": "https://www.usiu.ac.ke/assets/file/266ac45d-student-handbook.pdf", "http_status": 404,
     "source_type": "official", "publisher": "USIU-Africa", "category_id": "01",
     "access_outcome": "inaccessible: HTTP 404 Not Found",
     "note": "Candidate URL for the Student Handbook (from the app's official links catalogue). No other public "
             "handbook link was found in the pages collected."},
    {"page_id": "itsweb.usiu.ac.ke", "url": "https://itsweb.usiu.ac.ke/pls/prodi41/w99pkg.mi_login",
     "http_status": None, "source_type": "official", "publisher": "USIU-Africa", "category_id": "05",
     "access_outcome": "not attempted: student portal login (restricted system)"},
    {"page_id": "clear.usiu.ac.ke", "url": "https://clear.usiu.ac.ke/", "http_status": None,
     "source_type": "official", "publisher": "USIU-Africa", "category_id": "04",
     "access_outcome": "not attempted: online clearance system (restricted system)"},
    {"page_id": "webapp__defer-payment", "url": "https://www.usiu.ac.ke/webapp/defer-payment/", "http_status": None,
     "source_type": "official", "publisher": "USIU-Africa", "category_id": "04",
     "access_outcome": "not attempted: online instalment-plan application (requires student details)"},
    {"page_id": "webapp__tuition-refund", "url": "https://www.usiu.ac.ke/webapp/tuition-refund/", "http_status": None,
     "source_type": "official", "publisher": "USIU-Africa", "category_id": "04",
     "access_outcome": "not attempted: online refund application (requires student details)"},
    {"page_id": "wp-content__uploads__2026__01__Academic-Catalog-2024-2026.pdf",
     "url": "https://www.usiu.ac.ke/wp-content/uploads/2026/01/Academic-Catalog-2024-2026.pdf", "http_status": None,
     "source_type": "official", "publisher": "USIU-Africa", "category_id": "02",
     "access_outcome": "not collected: link found on the Academic Catalog page; not downloaded in this run "
                       "(further technical work)"},
]

# Reports with a layout the generic splitter cannot read.
def _tuition(text):
    body = text.split("- HTTP: 200 OK", 1)[1]
    body = "- HTTP: 200 OK" + body.split("## Unsure or flagged", 1)[0]
    return [("https://www.usiu.ac.ke/tuition-fees/", body)]


def _external(text):
    a = text.split("(a) Homepage", 1)[1].split("(b) Placem page", 1)[0]
    b = text.split("(b) Placem page", 1)[1].split("(c) FAQ page", 1)[0]
    c = text.split("(c) FAQ page", 1)[1].split("Point to flag", 1)[0]
    return [("https://kuccps.net/", "- HTTP outcome: 200 OK (https://kuccps.ac.ke redirected 301 to https://kuccps.net/)\n"
             "- Page title: \"Homepage | KUCCPS\"\n\n(a) Homepage" + a),
            ("https://kuccps.net/Placem", "- HTTP outcome: 200 OK\n- Page title: \"Placem | KUCCPS\"\n\n(b) Placem page" + b),
            ("https://kuccps.net/frequently-asked-questions",
             "- HTTP outcome: 200 OK\n- Page title: \"Frequently Asked Questions | KUCCPS\"\n\n(c) FAQ page" + c)]


def _sitemap(text):
    return [("https://www.usiu.ac.ke/wp-sitemap.xml", text)]


def _none(text):
    return []


REPORT_SPECIAL = {
    "a7f44d533384865ac_2.md": _tuition,
    "a080f0e73a9307e08_0.md": _external,
    "a36761f27f495a59e_0.md": _sitemap,
    "a8ba91fb5f6a2e479_0.md": _none,       # PDF downloads: recorded in DOWNLOADS
    "ac510e07666687356_0.md": _none,       # all attempts failed; the same pages were collected later
}
SKIP_BLOCKS = {"a7f44d533384865ac_0.md": ("https://www.usiu.ac.ke/tuition-fees/",)}  # summary only; see _2
PREFERRED_REPORT = {}


def _sitemap_lastmod():
    p = RAW / "a36761f27f495a59e_0.md"
    out = {}
    if p.exists():
        for m in re.finditer(r"^\s*(https://www\.usiu\.ac\.ke/\S*)\s+(\d{4}-\d{2}-\d{2})T", p.read_text(encoding="utf-8"), re.M):
            out[m.group(1)] = m.group(2)
    return out


SITEMAP_LASTMOD = _sitemap_lastmod()

# Snapshot text after these markers is not page content (model summary) and is excluded.
SNAPSHOT_TRUNCATE = {"resource-downloads": "Model-extracted summary of the remaining"}

# Official PDFs downloaded from the website on 2026-11-01.
DOWNLOADS = [
    {"document_id": "usiu_fee_schedule_2026_2027",
     "url": "https://www.usiu.ac.ke/wp-content/uploads/2026/03/USIU-Africa-Free-Structure-2026-2027.pdf",
     "landing_page": "https://www.usiu.ac.ke/documents/on-campus-programs-fee-structure/",
     "title": "Fee Schedule 2026 - 2027 Academic Year (Effective September 1, 2026)",
     "file": "web_sources/downloads/USIU-Africa-Free-Structure-2026-2027.pdf",
     "sha256": "33d8f0d58491c159a18bb13242926f37afe0759b5448195090d76b0fe03e2dd9",
     "academic_year": "2026-2027", "category": "04",
     "note": "File name spelling 'Free-Structure' is as published. PDF metadata: created 2026-10-29 (Adobe InDesign)."},
    {"document_id": "usiu_academic_calendar_2026_2027",
     "url": "https://www.usiu.ac.ke/wp-content/uploads/2026/04/Academic-Calendar-2026-2027.pdf",
     "landing_page": "https://www.usiu.ac.ke/documents/academic-calendar-2026-2027/",
     "title": "Academic Calendar 2026 – 2027 (Current)",
     "file": None,  # identical to the local Academic-Calendar-2026-2027.pdf; not stored twice
     "sha256": "618711f96eb9efd55d744341175a0b39a75087e8d2c8f692340bc0bb9067512f",
     "academic_year": "2026-2027", "category": "05",
     "note": "Downloaded copy is byte-identical (same SHA-256, 735,918 bytes) to the local calendar PDF in the "
             "project root, so the local copy IS the published official file."},
]
