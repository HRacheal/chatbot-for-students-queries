"""Stage 2 extraction: USIU-Africa Academic Calendar 2026-2027 and Student Handbook.

Run from the project root with the backend virtual environment (no new packages):

    backend/.venv/Scripts/python.exe usiubot_datasets/extraction_scripts/extract_documents.py

What it does
* Opens the two original PDFs read-only ('rb'), checks their SHA-256 against the baseline
  recorded before Stage 2, and checks again after extraction.
* Extracts the text layer with pypdf, page by page (no OCR, no network, no database).
* Writes everything under usiubot_datasets/ only. The output is deterministic: running it
  again reproduces the same files (except the run timestamp in the statistics file).
* Every curated structured row is checked against the PDF text: its evidence quote must
  occur on the stated page. The run stops with an error if any check fails.

Nothing here approves anything: every record is review_status = "draft" and
verification_status = "pending_verification".
"""

import argparse
import csv
import datetime as dt
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

from pypdf import PdfReader

sys.path.insert(0, str(Path(__file__).resolve().parent))
import extraction_config as C  # noqa: E402

DATASETS = Path(__file__).resolve().parents[1]
PROJECT_ROOT = DATASETS.parent
CHUNK_CHARS = 1000  # same chunk size as the app (backend/services/knowledge_base.py CHUNK_SIZE)

MONTHS = ("January|February|March|April|May|June|July|August|September|October|November|December")
DAYS = "Monday|Tuesday|Wednesday|Thursday|Thurday|Friday|Saturday|Sunday"
DAY_FIX = {"Thurday": "Thursday"}
MONTH_NUM = {m: i for i, m in enumerate(MONTHS.split("|"), start=1)}
WEEKDAY = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

HB_HEADING_RE = re.compile(r"^(\d{1,2}(?:\.\d{1,2}){1,3})\.?\s+(\S.*)$")
HB_TOP_RE = re.compile(r"^\d{1,2}\.0\s+[A-Z]")


# ----------------------------------------------------------------------------- helpers
def norm(text):
    return re.sub(r"\s+", " ", text or "").strip()


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def write_text(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def write_json(path, data):
    write_text(path, json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def write_csv(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="raise")
        w.writeheader()
        for row in rows:
            w.writerow({k: ("; ".join(map(str, v)) if isinstance(v, list) else v) for k, v in row.items()})


def cat_dir(cat_id):
    return DATASETS / C.CATEGORIES[cat_id][0]


class Evidence:
    """Checks that quoted evidence occurs on the stated page."""

    def __init__(self, pages_by_doc):
        # A word hyphenated at a line break ("audio-\nvisual") is compared as "audio-visual".
        self.pages = {doc: {n: norm(re.sub(r"(\w)-[ \t]*\n\s*", r"\1-", t)) for n, t in pages.items()}
                      for doc, pages in pages_by_doc.items()}
        self.checked = 0
        self.failures = []

    def check(self, doc, page, quote, where):
        self.checked += 1
        if norm(quote) not in self.pages[doc].get(page, ""):
            self.failures.append(f"{where}: quote not found on {doc} page {page}: {quote!r}")
        return norm(quote)


# ----------------------------------------------------------------------------- PDF reading
def read_pdf(path):
    with open(path, "rb") as f:
        reader = PdfReader(f)
        meta = reader.metadata or {}
        pages = {i: (p.extract_text() or "") for i, p in enumerate(reader.pages, start=1)}
        info = {
            "page_count": len(reader.pages),
            "encrypted": reader.is_encrypted,
            "pdf_creation_date": str(meta.get("/CreationDate", "")) or None,
            "pdf_modification_date": str(meta.get("/ModDate", "")) or None,
            "pdf_producer": str(meta.get("/Producer", "")) or None,
        }
    return pages, info


def pdf_date(value):
    m = re.match(r"D:(\d{4})(\d{2})(\d{2})", value or "")
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else None


# ----------------------------------------------------------------------------- common record
def base_record(doc_id, extraction_date):
    d = C.DOCUMENTS[doc_id]
    return {
        "data_origin": "official",
        "source_institution": C.INSTITUTION,
        "document_id": doc_id,
        "document_title": d["title"],
        "document_file": d["file"],
        "source_url": d["source_url"],
        "source_url_status": d["source_url_status"],
        "candidate_source_url": d["candidate_source_url"],
        "publication_date": d["publication_date"],
        "academic_year": d["academic_year"],
        "extraction_date": extraction_date,
    }


def status_fields():
    return {"review_status": "draft", "verification_status": "pending_verification", "approval_status": "not_approved"}


# ----------------------------------------------------------------------------- chunking
def split_long(text, limit=CHUNK_CHARS):
    """Split one paragraph longer than ``limit`` (same splitter family the app uses, no overlap)."""
    if len(text) <= limit:
        return [text]
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    splitter = RecursiveCharacterTextSplitter(chunk_size=limit, chunk_overlap=0,
                                              separators=["\n", ". ", "; ", ", ", " ", ""], keep_separator="end")
    return [p.strip() for p in splitter.split_text(text) if p.strip()]


def pack_chunks(paragraphs, limit=CHUNK_CHARS):
    """Greedy-pack (page, text) paragraphs into chunks of at most ``limit`` characters."""
    pieces = [(page, part) for page, text in paragraphs for part in split_long(text, limit)]
    chunks, cur, cur_len = [], [], 0
    for page, text in pieces:
        add = len(text) + (1 if cur else 0)
        if cur and cur_len + add > limit:
            chunks.append(cur)
            cur, cur_len = [], 0
            add = len(text)
        cur.append((page, text))
        cur_len += add
    if cur:
        chunks.append(cur)
    return [("\n".join(t for _, t in c), sorted({p for p, _ in c})) for c in chunks]


# ----------------------------------------------------------------------------- handbook
def hb_clean_lines(page_no, text):
    lines = [ln.rstrip() for ln in text.split("\n")]
    out = []
    for i, ln in enumerate(lines):
        s = norm(ln)
        if not s:
            continue
        if i < 4 and (s == "USIU-Africa Student Handbook" or s == str(page_no)):
            continue
        out.append(s)
    return out


def hb_reflow(lines):
    """Join wrapped lines into paragraphs without changing any words."""
    paragraphs, cur = [], ""
    marker = re.compile(r"^(\d+\.\s|\d+\.\d*\s|[a-z]\.\s|●|•|\*|Step \d|NOTE|Note:|Contacts?:|Disclaimer:)")
    def caps(s):
        letters = [c for c in s if c.isalpha()]
        return len(s) < 60 and len(letters) >= 4 and all(c.isupper() for c in letters)

    for ln in lines:
        if not cur:
            cur = ln
            continue
        if marker.match(ln) or cur.endswith(":") or caps(ln) or caps(cur):
            paragraphs.append(cur)
            cur = ln
            continue
        last = cur.split(" ")[-1]
        joins_without_space = (cur.endswith("-") and not cur.endswith(" -")) or cur.endswith("/") or (
            cur.endswith(".") and ("://" in last or "@" in last or last.startswith("www")))
        cur = cur + ln if joins_without_space else cur + " " + ln
    if cur:
        paragraphs.append(cur)
    return paragraphs


def reorder_page(page_no, lines):
    """Put a page's text blocks under their printed headings (see HB_PAGE_READING_ORDER)."""
    spec = C.HB_PAGE_READING_ORDER[page_no]
    remaining = [ln for ln in lines if ln not in spec["drop"]]
    out, used = [], 0
    for label, first, last in spec["blocks"]:
        i = next(k for k, ln in enumerate(remaining) if ln.startswith(norm(first)))
        j = next(k for k in range(i, len(remaining)) if remaining[k] == norm(last))
        out.append(label)
        out.extend(remaining[i:j + 1])
        used += j - i + 1
    if used != len(remaining):
        raise RuntimeError(f"Page {page_no} reading order does not use every line ({used} of {len(remaining)})")
    return out


def section_sort_key(number):
    if number == "cover":
        return (0,)
    if number == "contact":
        return (99,)
    return tuple(int(x) for x in number.split("."))


def process_handbook(pages, extraction_date, issues_by_section):
    doc = C.HB
    stream = []  # (page, line)
    top_headings, placeholders_found = [], []
    for page_no in sorted(pages):
        if page_no in C.HB_SKIP_PAGES:
            continue
        drops = {norm(x) for x in C.HB_DROP_LINES.get(page_no, [])}
        page_lines = hb_clean_lines(page_no, pages[page_no])
        if page_no in C.HB_PAGE_READING_ORDER:
            page_lines = reorder_page(page_no, page_lines)
        for ln in page_lines:
            if ln in drops:
                continue
            if HB_TOP_RE.match(ln):
                top_headings.append({"page": page_no, "heading_as_printed": ln})
                continue
            stream.append((page_no, ln))

    # Relocations (two-column layout).
    moved = defaultdict(list)
    reloc_report = []
    for r in C.HB_RELOCATIONS:
        idx = [i for i, (p, ln) in enumerate(stream) if p == r["page"]]
        start = next(i for i in idx if stream[i][1].startswith(r["start"]))
        end = next(i for i in idx if i >= start and stream[i][1] == norm(r["end"]))
        moved[r["to"]].extend(stream[start:end + 1])
        reloc_report.append({**r, "lines_moved": end - start + 1})
        stream = stream[:start] + [(None, None)] * (end - start + 1) + stream[end + 1:]
    stream = [(p, ln) for p, ln in stream if p is not None]

    forced = {(f["page"]): f for f in C.HB_FORCED_STARTS}
    extra = {(e["page"], e["startswith"]): e for e in C.HB_EXTRA_HEADINGS}
    sections, cur = [], None
    first_line_of_page = set()
    seen_pages = set()
    for i, (p, _) in enumerate(stream):
        if p not in seen_pages:
            first_line_of_page.add(i)
            seen_pages.add(p)

    def start(number, heading, page, note=None):
        nonlocal cur
        cur = {"number": number, "heading": heading, "lines": [], "first_page": page, "notes": [], "flags": []}
        if note:
            cur["notes"].append(note)
        sections.append(cur)

    skip_next = None
    for i, (p, ln) in enumerate(stream):
        if skip_next is not None and ln == skip_next:
            skip_next = None
            continue
        skip_next = None
        if i in first_line_of_page and p in forced:
            f = forced[p]
            start(f["number"], f["heading"], p, f.get("note"))
        ex = next((e for (pg, sw), e in extra.items() if pg == p and ln.startswith(sw)), None)
        m = HB_HEADING_RE.match(ln)
        if ex:
            start(ex["number"], ex["heading"], p)
            skip_next = ex.get("continuation")
            if ex.get("inline"):
                rest = ln[len(ex["startswith"]):].strip()
                if rest:
                    cur["lines"].append((p, rest))
            continue
        cur_major = int(cur["number"].split(".")[0]) if cur and cur["number"][0].isdigit() else 0
        if (m and 1 <= int(m.group(1).split(".")[0]) <= 14 and int(m.group(1).split(".")[0]) >= cur_major
                and not m.group(2)[0].islower()):  # e.g. "4.30 p.m." on page 28 is not a heading
            number = m.group(1)
            first = m.group(2).strip()
            full = C.HB_HEADING_OVERRIDES.get(number)
            if full:
                rest = norm(full[len(first):]) if full.startswith(first) else None
                if rest:
                    skip_next = rest
                heading = full
            else:
                heading = first
            start(number, heading, p)
            continue
        if cur is None:
            raise RuntimeError(f"Handbook text before the first section on page {p}: {ln!r}")
        placeholder = C.HB_PLACEHOLDERS.get(p)
        if placeholder and ln == placeholder:
            cur["flags"].append("placeholder_text_in_source")
            cur["notes"].append(f"The PDF prints the placeholder '{placeholder}' on page {p} here; it was removed "
                                f"from the content (issue V06).")
            placeholders_found.append({"page": p, "text": placeholder, "section": cur["number"]})
            continue
        cur["lines"].append((p, ln))

    for number, lines in moved.items():
        target = next(s for s in sections if s["number"] == number)
        target["lines"].extend(lines)
        target["flags"].append("reconstructed_from_two_column_layout")
        target["notes"].append("Part of this section's text was moved into place because the two-column layout puts "
                               "it elsewhere in the PDF text layer. Compare with the PDF before approval.")

    # Duplicate section numbers are kept apart.
    counts = Counter(s["number"] for s in sections if s["number"] not in ("12.0",))
    occurrence = Counter()
    for s in sections:
        occurrence[(s["number"], s["heading"])] += 1
        s["occurrence"] = occurrence[(s["number"], s["heading"])]
    seen_numbers = Counter()
    for s in sections:
        seen_numbers[s["number"]] += 1
        s["number_occurrence"] = seen_numbers[s["number"]]
        if counts.get(s["number"], 0) > 1:
            s["flags"].append("duplicate_section_number_in_source")

    order = {id(s): k for k, s in enumerate(sections)}
    sections.sort(key=lambda s: (section_sort_key(s["number"]), order[id(s)]))

    section_records, chunk_records = [], []
    for s in sections:
        if s["number"] == "2":
            s["flags"].append("layout_order_uncertain")
            s["flags"].append("reconstructed_from_two_column_layout")
            s["notes"].append(C.HB_PAGE_READING_ORDER[7]["note"])
        by_page = defaultdict(list)
        for p, ln in s["lines"]:
            by_page[p].append(ln)
        paragraphs = []
        # keep moved lines after the section's own lines, page by page in stream order
        seen = []
        for p, ln in s["lines"]:
            if p not in seen:
                seen.append(p)
        for p in seen:
            paragraphs.extend((p, para) for para in hb_reflow(by_page[p]))
        content = "\n".join(t for _, t in paragraphs)
        pages_used = sorted({p for p, _ in s["lines"]}) or [s["first_page"]]
        suffix = "" if s["number_occurrence"] == 1 else f"-dup{s['number_occurrence']}"
        sub = ""
        if s["number"] == "12.0":
            sub = "" if s["heading"] == "Campus Safety and Security" else "-" + re.sub(r"[^a-z]+", "-", s["heading"].lower()).strip("-")[:30]
            suffix = ""
        section_id = f"HB-{s['number']}{suffix}{sub}"
        major = s["number"].split(".")[0]
        parent = C.HB_MAJOR_HEADINGS.get(major, "")
        cat = C.hb_category(s["number"])
        issue_ids = sorted(set(issues_by_section.get((doc, s["number"]), [])) | set(issues_by_section.get((doc, "*"), [])))
        chunks = pack_chunks(paragraphs) if paragraphs else []
        rec = {
            "record_id": section_id, "record_type": "document_section", "section_id": section_id,
            "category_id": cat, "category_name": C.CATEGORIES[cat][1],
            **base_record(doc, extraction_date),
            "page_start": pages_used[0], "page_end": pages_used[-1], "pages": pages_used,
            "section_number": s["number"] if s["number"] not in ("cover", "contact", "2") else
            {"cover": "not numbered (cover page)", "contact": "not numbered", "2": "not printed"}[s["number"]],
            "section_heading": s["heading"], "parent_section_heading": parent,
            "content": content, "content_chars": len(content), "chunk_count": len(chunks),
            **status_fields(),
            "flags": sorted(set(s["flags"])), "issue_ids": issue_ids, "processing_notes": s["notes"],
        }
        section_records.append(rec)
        for n, (text, pgs) in enumerate(chunks, start=1):
            chunk_records.append({
                "record_id": f"{section_id}-c{n:02d}", "record_type": "knowledge_chunk", "section_id": section_id,
                "chunk_id": f"{section_id}-c{n:02d}", "chunk_index": n, "chunk_count": len(chunks),
                "category_id": cat, "category_name": C.CATEGORIES[cat][1],
                **base_record(doc, extraction_date),
                "page_start": pgs[0], "page_end": pgs[-1], "pages": pgs,
                "section_number": rec["section_number"], "section_heading": s["heading"],
                "parent_section_heading": parent,
                "content": text, "content_chars": len(text), "content_sha256": sha256_text(text),
                **status_fields(),
                "flags": rec["flags"], "issue_ids": issue_ids,
            })
    detected = [{"section_number": r["section_number"], "section_heading": r["section_heading"],
                 "page_start": r["page_start"], "category_id": r["category_id"]} for r in section_records]
    return section_records, chunk_records, {"top_level_headings_in_text": top_headings,
                                            "placeholders_found": placeholders_found,
                                            "relocations": reloc_report, "sections_detected": detected}


# ----------------------------------------------------------------------------- calendar
def cal_lines(text):
    lines = [norm(ln.replace("•\t", "• ")) for ln in text.split("\n")]
    lines = [ln for ln in lines if ln]
    date_only = re.compile(rf"^({MONTHS})\s*\d{{1,2}}(\s*-\s*(({MONTHS})\s*)?\d{{1,2}})?$")
    changed = True
    while changed:
        changed = False
        for i in range(len(lines) - 1):
            if lines[i].endswith("-") or date_only.match(lines[i]):
                lines[i] = norm(lines[i] + " " + lines[i + 1])
                del lines[i + 1]
                changed = True
                break
    return lines


ENTRY_RE = re.compile(
    rf"^(?P<m1>{MONTHS})\s*(?P<d1>\d{{1,2}})(?:\s*-\s*(?:(?P<m2>{MONTHS})\s*)?(?P<d2>\d{{1,2}}))?\s+"
    rf"(?P<day1>{DAYS})(?:\s*-\s*(?P<day2>{DAYS}))?\s*(?P<rest>.*)$")
RECESS_RE = re.compile(r"^(?P<sem>.+?) Academic Recess\s*[-–]\s*(?P<range>.+)$")
TERM_RE = re.compile(rf"^(?P<m1>{MONTHS})\s*(?P<d1>\d{{1,2}})\s*[-–]\s*(?P<m2>{MONTHS})\s*(?P<d2>\d{{1,2}})\s*\((?P<weeks>\d+) Weeks\)$")


def classify_event(text):
    t = text.lower()
    if "application deadline" in t:
        return "admission_application_deadline", "03"
    if "orientation" in t:
        return "orientation", "01"
    if any(k in t for k in ("payment of fees", "interest", "tuition charge", "refund", "financial clearance",
                            "late registration fee applies", "add/drop fee")):
        return "fees_and_charges", "04"
    if "grades due" in t:
        return "grades", "05"
    if "graduation" in t or "commencement" in t:
        return "graduation", "05"
    if "exam" in t:
        return "examinations", "05"
    if "placement test" in t:
        return "placement_tests", "05"
    if "withdraw" in t:
        return "withdrawal", "05"
    if "register" in t or "registration" in t or "course addition" in t:
        return "registration", "05"
    if "award ceremony" in t:
        return "academic_awards", "05"
    if "holiday" in t or "offices closed" in t or "offices are closed" in t or "recess" in t:
        return "holidays_and_breaks", "01"
    if "hostel" in t:
        return "accommodation", "01"
    if "instruction" in t:
        return "semester_dates", "01"
    return "university_events", "01"


# Which recorded issues concern which calendar events: (issue, page or None, test(event text, date)).
EVENT_ISSUE_RULES = [
    ("V04", None, lambda t, d: "75% refund" in t or "tuition charge on dropped courses" in t.lower()),
    ("V17", None, lambda t, d: "Graduation and certificate application" in t),
    ("V18", 2, lambda t, d: "recess" in t.lower()),
    ("V19", 2, lambda t, d: "MID-SEMESTER EXAM WEEK" in t or ("Mashujaa" in t) or (d == dt.date(2026, 10, 20))),
    ("V21", 4, lambda t, d: d == dt.date(2027, 7, 5)),
    ("V28", None, lambda t, d: "interest" in t.lower()),
]


def iso(year, month_name, day):
    return dt.date(year, MONTH_NUM[month_name], int(day))


def process_calendar(pages, extraction_date, issues_by_section):
    doc = C.CAL
    events, terms, weekday_issues = [], [], []
    for page_no, year in C.CAL_SEMESTER_YEARS.items():
        lines = cal_lines(pages[page_no])
        semester = lines[0].title()
        term = TERM_RE.match(lines[1])
        entries = []
        recess = None
        for ln in lines[2:]:
            r = RECESS_RE.match(ln)
            if r:
                recess = ln
                continue
            m = ENTRY_RE.match(ln)
            if m:
                items = [x.strip() for x in m.group("rest").split("•")]
                items = [x for x in items if x] or [""]
                entries.append({"m": m, "items": items})
            elif ln.startswith("•"):
                entries[-1]["items"].extend(x.strip() for x in ln.split("•") if x.strip())
            else:
                entries[-1]["items"][-1] = norm(entries[-1]["items"][-1] + " " + ln)
        t_start = iso(year, term.group("m1"), term.group("d1"))
        t_end = iso(year, term.group("m2"), term.group("d2"))
        rec_m = re.search(rf"({MONTHS}) (\d{{1,2}})(?:, (\d{{4}}))? [-–] ({MONTHS}) (\d{{1,2}})(?:, (\d{{4}}))?", recess)
        r_start = iso(int(rec_m.group(3) or year), rec_m.group(1), rec_m.group(2))
        r_end = iso(int(rec_m.group(6) or year), rec_m.group(4), rec_m.group(5))
        terms.append({
            "record_id": f"CAL-TERM-{semester.split()[0].upper()}", "semester": semester,
            "term_dates_as_printed": lines[1], "start_date": t_start.isoformat(), "end_date": t_end.isoformat(),
            "weeks_as_printed": term.group("weeks"), "recess_as_printed": recess,
            "recess_start": r_start.isoformat(), "recess_end": r_end.isoformat(), "page": page_no,
            **base_record(doc, extraction_date), **status_fields(),
            "issue_ids": sorted(issues_by_section.get((doc, f"page-{page_no}"), [])),
        })
        n = 0
        for e in entries:
            m = e["m"]
            start = iso(year, m.group("m1"), m.group("d1"))
            end = iso(year, m.group("m2") or m.group("m1"), m.group("d2")) if m.group("d2") else None
            day1 = DAY_FIX.get(m.group("day1"), m.group("day1"))
            day2 = DAY_FIX.get(m.group("day2"), m.group("day2")) if m.group("day2") else None
            problems = []
            if WEEKDAY[start.weekday()] != day1:
                problems.append(f"{start.isoformat()} is a {WEEKDAY[start.weekday()]}; the calendar says {day1}")
            if end and day2 and WEEKDAY[end.weekday()] != day2:
                problems.append(f"{end.isoformat()} is a {WEEKDAY[end.weekday()]}; the calendar says {day2}")
            if m.group("day1") in DAY_FIX:
                problems_note = f"Day name printed as '{m.group('day1')}' (typing error)."
            else:
                problems_note = ""
            date_text = m.group(0)[:m.start("day1")].strip()
            day_text = m.group(0)[m.start("day1"):m.end("day2") if m.group("day2") else m.end("day1")]
            for item in e["items"]:
                n += 1
                note = problems_note
                if re.search(r"continues (through|until)", item):
                    note = (note + " " if note else "") + (
                        "Printed as a bullet under the date row above; the end date of this period is the one "
                        "stated in the event text, not end_date.")
                topic, cat = classify_event(item)
                eid = f"CAL-{semester.split()[0].upper()}-{n:02d}"
                issue_ids = {"V22"} | {iid for iid, pg, test in EVENT_ISSUE_RULES
                                       if (pg is None or pg == page_no) and test(item, start)}
                if problems:
                    issue_ids.add("V20")
                    weekday_issues.append({"event_id": eid, "page": page_no, "date_as_printed": date_text,
                                           "day_as_printed": day_text, "event": item, "problem": "; ".join(problems)})
                events.append({
                    "record_id": eid, "academic_year": "2026-2027", "semester": semester,
                    "date_as_printed": date_text, "day_as_printed": day_text,
                    "start_date": start.isoformat(), "end_date": end.isoformat() if end else "",
                    "event_as_printed": item, "topic": topic, "category_id": cat,
                    "weekday_check": "; ".join(problems) if problems else "ok",
                    "page": page_no, **base_record(doc, extraction_date), **status_fields(),
                    "issue_ids": sorted(issue_ids), "notes": note,
                })

    # Text sections (one per page) for retrieval.
    section_records, chunk_records = [], []
    for page_no, heading, cat in C.CAL_PAGES:
        lines = cal_lines(pages[page_no]) if page_no in C.CAL_SEMESTER_YEARS else \
            [norm(ln.replace("•\t", "• ")) for ln in pages[page_no].split("\n") if norm(ln)]
        content = "\n".join(lines)
        sid = f"CAL-p{page_no}"
        issue_ids = sorted(set(issues_by_section.get((doc, f"page-{page_no}"), [])) | set(issues_by_section.get((doc, "*"), [])))
        flags = ["high_risk_payment_details"] if page_no in (5, 6) else []
        chunks = pack_chunks([(page_no, ln) for ln in lines])
        section_records.append({
            "record_id": sid, "record_type": "document_section", "section_id": sid,
            "category_id": cat, "category_name": C.CATEGORIES[cat][1], **base_record(doc, extraction_date),
            "page_start": page_no, "page_end": page_no, "pages": [page_no],
            "section_number": "not numbered (calendar page)", "section_heading": heading,
            "parent_section_heading": "Academic Calendar 2026-2027", "content": content,
            "content_chars": len(content), "chunk_count": len(chunks), **status_fields(),
            "flags": flags, "issue_ids": issue_ids,
            "processing_notes": ["Line breaks kept as printed (calendar tables). Bullet characters normalised."],
        })
        for n, (text, pgs) in enumerate(chunks, start=1):
            chunk_records.append({
                "record_id": f"{sid}-c{n:02d}", "record_type": "knowledge_chunk", "section_id": sid,
                "chunk_id": f"{sid}-c{n:02d}", "chunk_index": n, "chunk_count": len(chunks),
                "category_id": cat, "category_name": C.CATEGORIES[cat][1], **base_record(doc, extraction_date),
                "page_start": page_no, "page_end": page_no, "pages": pgs,
                "section_number": "not numbered (calendar page)", "section_heading": heading,
                "parent_section_heading": "Academic Calendar 2026-2027", "content": text,
                "content_chars": len(text), "content_sha256": sha256_text(text), **status_fields(),
                "flags": flags, "issue_ids": issue_ids,
            })

    # M-PESA purpose codes (page 6).
    codes = []
    p6 = [norm(ln.replace("•\t", "• ")) for ln in pages[6].split("\n") if norm(ln)]
    code_re = re.compile(r"^•\s*([A-Z&]+)\s*[-–]\s*(.+)$")
    for i, ln in enumerate(p6):
        m = code_re.match(ln)
        if m and m.group(1) not in ("For",):
            desc = m.group(2)
            if desc.endswith("(Account") and i + 1 < len(p6):
                desc = desc + " " + p6[i + 1]
            codes.append((m.group(1), desc, ln))
    tuit = next(ln for ln in p6 if "use the code" in ln)
    codes.insert(0, ("TUIT", "Tuition Fee, Graduation fee, Diploma replacement and any other fee payment", tuit))
    code_rows = [{
        "record_id": f"MPESA-CODE-{code.replace('&', 'AND')}", "purpose_code": code, "description_as_printed": desc,
        "account_number_format_as_printed": "Student ID – (hyphen) then purpose code", "page": 6,
        "evidence_text": ev, **base_record(doc, extraction_date), **status_fields(),
        "issue_ids": ["V32"] if code == "MUS" else [],
    } for code, desc, ev in codes]
    return section_records, chunk_records, events, terms, weekday_issues, code_rows


# ----------------------------------------------------------------------------- curated tables
def curated_tables(ev, extraction_date):
    out = {}
    out["profile"] = [{
        "record_id": f"PROFILE-{i:02d}", "field": r["field"], "value_as_printed": ev.check(r["doc"], r["page"], r["evidence"], r["field"]),
        "page": r["page"], "section_number": r["section"], **base_record(r["doc"], extraction_date), **status_fields(),
        "issue_ids": r.get("issues", []) + (["V24"] if r["section"] == "2" and r["field"] in ("vision", "mission") else []),
        "notes": r.get("notes", ""),
    } for i, r in enumerate(C.UNIVERSITY_PROFILE, start=1)]

    out["service_hours"] = [{
        "record_id": f"HOURS-{i:02d}", "service": s, "period_as_printed": per, "days_as_printed": days,
        "hours_as_printed": hours, "page": page, "section_number": sec,
        "evidence_text": ev.check(C.HB, page, evid, f"service hours {s}"), **base_record(C.HB, extraction_date),
        **status_fields(), "issue_ids": [],
    } for i, (s, per, days, hours, page, sec, evid) in enumerate(C.SERVICE_HOURS, start=1)]

    out["library_loans"] = [{
        "record_id": f"LOAN-{i:02d}", "borrower_category": who, "items_as_printed": items, "loan_period_as_printed": per,
        "page": 28, "section_number": "7.3.4", "evidence_text": ev.check(C.HB, 28, evid, f"loan {who}"),
        **base_record(C.HB, extraction_date), **status_fields(),
        "notes": "PDF text layer prints 'No borr owing'." if who == "Others" else "",
    } for i, (who, items, per, evid) in enumerate(C.LIBRARY_LOANS, start=1)]

    out["admission_conditions"] = [{
        "record_id": f"ADM-COND-{i:02d}", "topic": topic, "rule_as_printed": ev.check(C.HB, page, evid, topic),
        "page": page, "section_number": sec, **base_record(C.HB, extraction_date), **status_fields(),
        "issue_ids": ["V07"],
    } for i, (topic, sec, page, evid) in enumerate(C.ADMISSION_CONDITIONS, start=1)]

    english = ev.check(C.HB, 16, C.ENGLISH_EVIDENCE, "English proficiency")
    out["english"] = [{
        "record_id": f"ELIG-ENG-{i:02d}", "programme_id": "NOT_PROGRAMME_SPECIFIC",
        "applies_to_as_printed": "Applicants from non-English speaking countries",
        "qualification_type": "English language proficiency test", "test_as_printed": test,
        "minimum_score_or_grade": minimum, "rule_wording": rule,
        "combination_rule": "Any one of the listed tests ('or').", "required_subjects": "Not applicable",
        "page": 16, "section_number": "5.2.1", "evidence_text": english, **base_record(C.HB, extraction_date),
        **status_fields(), "last_verified_date": "", "issue_ids": ["V16", "V07"],
    } for i, (test, minimum, rule) in enumerate(C.ENGLISH_REQUIREMENTS, start=1)]

    out["financial_aid"] = [{
        "record_id": f"FINAID-{i:02d}", "programme_as_printed": ev.check(C.HB, page, name, name),
        "listed_under": {"5.2.7": "Financial Aid Programs for Undergraduate Students",
                         "5.2.8": "Financial Aid Programs for Graduate Students",
                         "5.2.9": "Financial Aid Programs for Undergraduate and Graduate Students",
                         "5.2.10": "Externally Funded Financial Aid Programs"}[sec],
        "eligible_level": level, "page": page, "section_number": sec, **base_record(C.HB, extraction_date),
        **status_fields(), "issue_ids": ["V07"],
        "notes": "Amounts, deadlines and selection criteria are not printed. Forms: https://www.usiu.ac.ke/financial-aid (page 18).",
    } for i, (name, level, sec, page) in enumerate(C.FINANCIAL_AID, start=1)]

    out["fee_rules"] = []
    for i, (topic, sec, page, evid) in enumerate(C.FEE_RULES, start=1):
        issues = {"3.4": ["V01"], "3.8": ["V04"], "3.10": ["V29"] if "7th day" in evid else [],
                  "3.2": ["V28"] if "1.5%" in evid else [], "3.11": ["V28"]}.get(sec, [])
        out["fee_rules"].append({
            "record_id": f"FEE-RULE-{i:02d}", "topic": topic, "rule_as_printed": ev.check(C.HB, page, evid, topic),
            "page": page, "section_number": sec, **base_record(C.HB, extraction_date), **status_fields(),
            "issue_ids": issues + ["V07"],
        })

    out["bank"] = []
    for (rid, doc, page, bank, branch, cur, acct, name, codes, evid) in C.BANK_DETAILS:
        issues = ["V01", "V02", "V03"] if doc == C.HB else ["V02", "V03", "V22"]
        if rid.startswith("MPESA"):
            issues = ["V22"] if doc == C.CAL else ["V01"]
        out["bank"].append({
            "record_id": rid, "channel_as_printed": bank, "branch_as_printed": branch, "currency": cur,
            "account_or_paybill_as_printed": acct, "account_name_as_printed": name, "codes_as_printed": codes,
            "validity_as_printed": "valid as at May 2024" if doc == C.HB else "Academic Calendar 2026-2027 (no separate date)",
            "page": page, "evidence_text": ev.check(doc, page, evid, rid), **base_record(doc, extraction_date),
            **status_fields(), "risk_level": "HIGH — payment details; never show to users until Finance confirms them",
            "issue_ids": issues,
        })

    out["registrar_services"] = [{
        "record_id": f"REG-SVC-{i:02d}", "service_as_printed": ev.check(C.HB, 14, s, s), "page": 14,
        "section_number": "4.3", "section_heading": "Services offered by the Registrar.",
        **base_record(C.HB, extraction_date), **status_fields(), "issue_ids": ["V07"],
    } for i, s in enumerate(C.REGISTRAR_SERVICES, start=1)]

    out["contacts"] = [{
        "record_id": cid, "office_as_printed": office, "maps_to_usiubot_enquiry_department": maps or "(none)",
        "contact_type": ctype, "value_as_printed": value, "page": page, "section_number": sec or "",
        "evidence_text": ev.check(doc, page, evid, cid), **base_record(doc, extraction_date), **status_fields(),
        "verification_note": "Printed in an official USIU-Africa document; not independently verified.",
        "issue_ids": issues + (["V07"] if doc == C.HB else ["V22"]),
    } for (cid, doc, page, sec, office, maps, ctype, value, evid, issues) in C.CONTACTS]

    out["routing"] = {}
    for dept, info in C.ROUTING_REFERENCE.items():
        out["routing"][dept] = {
            "usiubot_department_key": dept, "department_name": info["label"],
            "documented_responsibilities": [
                {"quote": ev.check(d, p, q, f"routing {dept}"), "document_id": d, "page": p, "section_number": s}
                for (d, p, s, q) in info["responsibilities"]],
            "contact_record_ids": info["contacts"],
            "official_email_verified": False, "official_telephone_verified": False,
            "working_hours": "Not stated in either document",
            "escalation_procedure": "Not stated in either document",
            "verification_status": "pending_verification", "review_status": "draft",
            "notes": info.get("notes", ""), "see_also": info.get("see_also", ""),
        }
    return out


def schools_table(hb_pages, ev, extraction_date):
    rows = []
    for ln in hb_pages[7].split("\n"):
        m = re.match(r"^•\s*(.+?)\s*\(([A-Z]+)\)\s*$", ln.strip())
        if m:
            rows.append({
                "record_id": f"SCHOOL-{m.group(2)}", "school_name_as_printed": m.group(1), "abbreviation": m.group(2),
                "page": 7, "section_heading": "OUR SCHOOLS", "evidence_text": ev.check(C.HB, 7, ln, m.group(2)),
                **base_record(C.HB, extraction_date), **status_fields(), "issue_ids": ["V07"],
                "notes": "Programmes offered by the school are not listed in either document.",
            })
    return rows


# ----------------------------------------------------------------------------- issues
def build_issues(ev, numbering_findings, weekday_issues):
    rows = []
    for it in C.ISSUES:
        quotes = [f"{d} p{p}: \"{ev.check(d, p, q, it['id'])}\"" for d, p, q in it["evidence"]]
        rows.append({"issue_id": it["id"], "type": it["type"], "severity": it["severity"],
                     "requires_admin_decision": "yes" if it["admin_decision"] else "no",
                     "documents": sorted({d for d, _, _ in it["evidence"]} | {d for d, _ in it["affects"]}),
                     "pages": sorted({p for _, p, _ in it["evidence"]}),
                     "summary": it["summary"], "evidence": quotes, "recommended_action": it["action"],
                     "detected_by": "manual review during extraction (evidence checked automatically)"})
    if numbering_findings:
        rows.append({"issue_id": "V11", "type": "numbering", "severity": "low", "requires_admin_decision": "no",
                     "documents": [C.HB], "pages": sorted({f["page"] for f in numbering_findings}),
                     "summary": "Handbook section numbering problems: " + "; ".join(f["finding"] for f in numbering_findings),
                     "evidence": [], "recommended_action": "Note only; sections are kept separate and in printed order.",
                     "detected_by": "automatic check"})
    if weekday_issues:
        rows.append({"issue_id": "V20", "type": "inconsistency", "severity": "medium", "requires_admin_decision": "yes",
                     "documents": [C.CAL], "pages": sorted({w["page"] for w in weekday_issues}),
                     "summary": "Calendar date and day name disagree: " + "; ".join(sorted({
                         f"{w['date_as_printed']} {w['day_as_printed']} ({w['problem']}; affects "
                         f"{sum(1 for x in weekday_issues if x['date_as_printed'] == w['date_as_printed'])} events)"
                         for w in weekday_issues})),
                     "evidence": [], "recommended_action": "Registrar to confirm the correct date. Both the printed "
                                                          "date and day are kept unchanged in calendar_events.csv.",
                     "detected_by": "automatic check (weekday computed from the printed date and academic year)"})
    return rows


def numbering_check(section_records):
    findings = []
    numbers = [r["section_number"] for r in section_records if re.match(r"^\d", r["section_number"])]
    dup = [n for n, k in Counter(numbers).items() if k > 1 and n != "12.0"]
    for n in dup:
        pages = [r["page_start"] for r in section_records if r["section_number"] == n]
        findings.append({"page": pages[0], "finding": f"section number {n} is used twice (pages {', '.join(map(str, pages))})"})
    present = set(numbers)
    for n in sorted(present, key=section_sort_key):
        parts = n.split(".")
        if len(parts) >= 2 and parts[-1].isdigit() and int(parts[-1]) > 1:
            prev = ".".join(parts[:-1] + [str(int(parts[-1]) - 1)])
            if prev not in present:
                page = next(r["page_start"] for r in section_records if r["section_number"] == n)
                findings.append({"page": page, "finding": f"no section is numbered {prev} (the next number printed is {n}, page {page})"})
    titles = Counter(r["section_heading"] for r in section_records)
    for t, k in titles.items():
        if k > 1:
            nums = [r["section_number"] for r in section_records if r["section_heading"] == t]
            findings.append({"page": next(r["page_start"] for r in section_records if r["section_heading"] == t),
                             "finding": f"heading '{t}' is used for sections {', '.join(nums)}"})
    return findings


# ----------------------------------------------------------------------------- writing
def section_review_md(cat_id, sections):
    name = C.CATEGORIES[cat_id][1]
    out = [f"# {name} — extracted sections for review\n",
           "Status of every section: **draft / pending verification / not approved**. Content is the PDF text layer "
           "(wrapped lines joined; words unchanged). Processing notes are listed separately from the content.\n"]
    for s in sections:
        out.append(f"\n---\n\n## {s['section_heading']}\n")
        out.append(f"- Record: `{s['record_id']}`  \n- Document: {s['document_title']} (`{s['document_file']}`)  \n"
                   f"- Pages: {', '.join(map(str, s['pages']))}  \n- Section number: {s['section_number']}  \n"
                   f"- Parent section: {s['parent_section_heading']}  \n- Chunks: {s['chunk_count']}  \n"
                   f"- Status: {s['review_status']} / {s['verification_status']}  \n"
                   f"- Flags: {', '.join(s['flags']) or 'none'}  \n- Issues: {', '.join(s['issue_ids']) or 'none'}\n")
        if s["processing_notes"]:
            out.append("\n*Processing notes (not part of the document):*\n")
            out.extend(f"\n- {n}" for n in s["processing_notes"])
            out.append("\n")
        out.append("\n**Extracted content:**\n\n")
        out.append("\n".join("> " + ln if ln else ">" for ln in s["content"].split("\n")) + "\n")
    return "".join(out)


EVENT_FIELDS = ["record_id", "academic_year", "semester", "date_as_printed", "day_as_printed", "start_date",
                "end_date", "event_as_printed", "topic", "category_id", "weekday_check", "page", "data_origin",
                "source_institution", "document_id", "document_title", "document_file", "source_url",
                "source_url_status", "candidate_source_url", "publication_date", "extraction_date",
                "review_status", "verification_status", "approval_status", "issue_ids", "notes"]
META_TAIL = ["data_origin", "source_institution", "document_id", "document_title", "document_file", "source_url",
             "source_url_status", "candidate_source_url", "publication_date", "academic_year", "extraction_date",
             "review_status", "verification_status", "approval_status"]


def fields_of(rows):
    first = list(rows[0].keys())
    return [k for k in first if k not in META_TAIL] + [k for k in META_TAIL if k in first]


STATUS_TEXT = ("Every record is `review_status: draft`, `verification_status: pending_verification`, "
               "`approval_status: not_approved`, `data_origin: official`. Nothing has been imported into the app "
               "or any database.")


def md_table(header, rows):
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    out += ["| " + " | ".join(str(c).replace("|", "\\|").replace("\n", " ") for c in r) + " |" for r in rows]
    return "\n".join(out) + "\n"


def write_readmes(stats, structured, by_cat_sections, issues, xdate, integrity):
    issue_by_id = {i["issue_id"]: i for i in issues}
    for cid, (folder, name) in C.CATEGORIES.items():
        files = []
        if by_cat_sections.get(cid):
            files += ["document_sections.json", "knowledge_chunks.json", "sections_for_review.md", "sections_index.csv"]
        files += sorted(structured.get(cid, {}))
        pc = stats["per_category"][cid]
        rows = []
        for f in files:
            n = pc["sections"] if f in ("document_sections.json", "sections_index.csv", "sections_for_review.md") else \
                pc["chunks"] if f == "knowledge_chunks.json" else len(structured[cid][f])
            rows.append((f"`official/{f}`", n, C.FILE_DESCRIPTIONS.get(f, "")))
        cat_issues = sorted({i for s in by_cat_sections.get(cid, []) for i in s["issue_ids"]} |
                            {i for rows_ in structured.get(cid, {}).values() for r in rows_ for i in r.get("issue_ids", [])},
                            key=lambda x: int(x[1:]))
        text = [f"# {cid} {name}\n\n", C.CATEGORY_NOTES[cid], "\n\n", STATUS_TEXT, "\n\n## Files\n\n"]
        text.append(md_table(["File", "Records", "Contents"], rows) if rows else "No records: see the note above.\n")
        text.append("\n`external/` is empty (no external sources were collected in Stage 2). `metadata/category_metadata.json` "
                    "holds counts and coverage.\n\n## Coverage of the information this category needs\n\n")
        text.append(md_table(["Information", "Status", "Notes"],
                             [(i, st, n) for i, st, _, n in C.COVERAGE[cid]]))
        if cat_issues:
            text.append("\n## Issues affecting records in this folder\n\n")
            text.append(md_table(["Issue", "Severity", "Summary"],
                                 [(i, issue_by_id[i]["severity"], issue_by_id[i]["summary"]) for i in cat_issues if i in issue_by_id]))
            text.append("\nFull details: `../validation_reports/validation_issues.csv`.\n")
        write_text(DATASETS / folder / "README.md", "".join(text))

    write_text(DATASETS / "source_documents" / "README.md",
               "# Source documents\n\nOne folder per original PDF. The PDFs themselves stay in the project root, "
               "unchanged and not copied (see `../validation_reports/pdf_integrity.json`).\n\n"
               "- `document_metadata.json`: file name, SHA-256, size, page count, PDF metadata dates, title, "
               "institution, academic year, publication date, source URL status, table of contents (handbook) and "
               "layout-processing log.\n- `extracted_text_by_page.md`: the raw text layer exactly as pypdf returned "
               "it, page by page. This is the reference for checking every extracted record.\n")

    write_text(DATASETS / "extraction_scripts" / "README.md",
               "# Extraction scripts\n\n```\nbackend/.venv/Scripts/python.exe usiubot_datasets/extraction_scripts/"
               "extract_documents.py --extraction-date 2026-11-01\n```\n\n"
               "Run from the project root. Uses only packages already installed in the backend virtual environment "
               "(pypdf, langchain-text-splitters). No network, no database, no OCR.\n\n"
               "- `extract_documents.py`: reads both PDFs read-only, checks their SHA-256 before and after, "
               "extracts sections, chunks, calendar events and tables, and writes everything in this folder tree. "
               "It regenerates all outputs (deterministic for a given extraction date).\n"
               "- `extraction_config.py`: layout fixes for the handbook (headings, two-column text moved into place, "
               "placeholders), the category mapping, the curated structured rows, the issues and the coverage "
               "list. Every curated row has an evidence quote; the run stops if any quote is not found on its page.\n\n"
               "Known limits: the text layer has no table structure, so tables are kept as lines; paragraph breaks "
               "after numbered lists are not always recoverable (words are never changed); scanned images would "
               "need OCR (none are present: every page with content has a text layer).\n")

    pc = stats["per_category"]
    lines = ["# USIUBOT datasets (Stage 2)\n\n",
             f"Extracted on {xdate} from two local PDFs in the project root: `Academic-Calendar-2026-2027.pdf` and "
             "`Student-Handbook.pdf`. ", STATUS_TEXT, "\n\n",
             "## Layout\n\n```\nusiubot_datasets/\n├── 01_ … 08_<category>/\n│   ├── official/   extracted records "
             "(official USIU-Africa documents only)\n│   ├── external/   empty: external sources are kept apart here\n"
             "│   ├── metadata/   category_metadata.json (counts, coverage)\n│   └── README.md\n"
             "├── source_documents/   raw text by page + document metadata (PDFs are not copied)\n"
             "├── collection_register/collection_register.csv\n├── extraction_scripts/\n└── validation_reports/\n```\n\n"
             "There is no testing or synthetic data anywhere in this folder.\n\n## Counts\n\n",
             md_table(["Category", "Sections", "Chunks", "Structured rows"],
                      [(f"{cid} {C.CATEGORIES[cid][1]}", pc[cid]["sections"], pc[cid]["chunks"],
                        sum(pc[cid]["structured"].values())) for cid in C.CATEGORIES]),
             f"\nTotal: {stats['sections_total']} sections, {stats['chunks_total']} chunks, "
             f"{stats['structured_rows_total']} structured rows, {stats['issues_total']} recorded issues.\n\n"
             "## Record fields\n\nEvery record carries: `data_origin`, `source_institution`, `document_id`, "
             "`document_title`, `document_file`, `source_url` (null: not confirmed), `source_url_status`, "
             "`candidate_source_url`, `publication_date`, `academic_year`, `extraction_date`, page(s), section "
             "number and heading (sections/chunks), `review_status`, `verification_status`, `approval_status`, "
             "`issue_ids`. Values marked *as printed* are copied from the PDF; processing notes are kept in "
             "separate `notes` / `processing_notes` fields.\n\n"
             "Start with `validation_reports/STAGE2_EXTRACTION_REPORT.md`.\n"]
    write_text(DATASETS / "README.md", "".join(lines))

    # Stage 2 report (generated part).
    sev = {"high": 0, "medium": 1, "low": 2}
    rep = ["# Stage 2 extraction report (generated)\n\n", f"Extraction date: {xdate}. {STATUS_TEXT}\n\n",
           "## Documents\n\n",
           md_table(["Document", "Pages", "Sections", "Chunks", "Characters"],
                    [(v["file"], v["pages"], v["sections"], v["chunks"], v["content_chars"])
                     for v in stats["documents"].values()]),
           f"\nCalendar events: {stats['calendar_events']} · semester terms: {stats['calendar_terms']} · "
           f"structured rows: {stats['structured_rows_total']} · evidence quotes checked: "
           f"{stats['evidence_quotes_checked']} (failures: {stats['evidence_failures']}) · duplicate chunks: "
           f"{stats['duplicate_chunk_hashes']} · largest chunk: {stats['largest_chunk_chars']} characters.\n\n"
           "## Structured files\n\n",
           md_table(["File", "Rows"], sorted(stats["structured_rows"].items())),
           "\n## Issues (sorted by severity)\n\n",
           md_table(["Issue", "Type", "Severity", "Admin decision", "Summary", "Recommended action"],
                    [(i["issue_id"], i["type"], i["severity"], i["requires_admin_decision"], i["summary"],
                      i["recommended_action"]) for i in sorted(issues, key=lambda i: (sev[i["severity"]], int(i["issue_id"][1:])))]),
           "\n## PDF integrity\n\n",
           md_table(["File", "SHA-256 (baseline = before = after)", "Unchanged"],
                    [(f, v["after_run"], v["unchanged"]) for f, v in integrity["files"].items()]),
           ]
    write_text(DATASETS / "validation_reports" / "STAGE2_EXTRACTION_REPORT.md", "".join(rep))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--extraction-date", default=dt.date.today().isoformat())
    args = ap.parse_args()
    xdate = args.extraction_date

    # 1. Integrity before.
    before = {}
    for d in C.DOCUMENTS.values():
        path = PROJECT_ROOT / d["file"]
        before[d["file"]] = {"sha256": sha256_file(path), "size_bytes": path.stat().st_size,
                             "modified": dt.datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds")}
        if before[d["file"]]["sha256"] != C.BASELINE_SHA256[d["file"]]:
            sys.exit(f"STOP: {d['file']} differs from the Stage 2 baseline hash.")

    # 2. Read.
    pages, info = {}, {}
    for doc_id, d in C.DOCUMENTS.items():
        pages[doc_id], info[doc_id] = read_pdf(PROJECT_ROOT / d["file"])
    ev = Evidence(pages)

    issues_by_section = defaultdict(list)
    for it in C.ISSUES:
        for doc, sec in it["affects"]:
            issues_by_section[(doc, sec)].append(it["id"])

    hb_sections, hb_chunks, hb_layout = process_handbook(pages[C.HB], xdate, issues_by_section)
    cal_sections, cal_chunks, events, terms, weekday_issues, mpesa = process_calendar(pages[C.CAL], xdate, issues_by_section)
    tables = curated_tables(ev, xdate)
    schools = schools_table(pages[C.HB], ev, xdate)
    numbering = numbering_check(hb_sections)
    issues = build_issues(ev, numbering, weekday_issues)

    # Emails present in the PDFs must all be accounted for.
    emails_found = set()
    for doc_id in C.DOCUMENTS:
        for t in pages[doc_id].values():
            t2 = re.sub(r"@usiu\.\s+ac\.ke", "@usiu.ac.ke", t)
            emails_found |= set(re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[a-z]{2,}", t2))
    emails_recorded = {c["value_as_printed"] for c in tables["contacts"] if c["contact_type"] == "email"}
    unaccounted = sorted(emails_found - emails_recorded - set(C.EMAILS_NOT_CONTACTS))
    if unaccounted:
        ev.failures.append(f"Email addresses in the PDFs without a contact record: {unaccounted}")

    if ev.failures:
        sys.exit("STOP: evidence checks failed:\n  " + "\n  ".join(ev.failures))

    # 3. Write source documents (raw text layer by page) and metadata.
    for doc_id, d in C.DOCUMENTS.items():
        folder = DATASETS / "source_documents" / doc_id
        body = [f"# {d['title']} — extracted text layer by page\n\n",
                f"Original file (not copied, not modified): `{d['file']}` in the project root.  \n",
                f"Extraction: {C.EXTRACTION_TOOL}, {xdate}. Text exactly as returned by pypdf, page by page. "
                "Two-column pages may appear out of reading order; see the category datasets for the "
                "reconstructed sections.\n"]
        for n in sorted(pages[doc_id]):
            body.append(f"\n\n## PDF page {n}\n\n```text\n{pages[doc_id][n].rstrip()}\n```\n")
        write_text(folder / "extracted_text_by_page.md", "".join(body))
        meta = {
            "document_id": doc_id, **{k: v for k, v in d.items()}, "source_institution": C.INSTITUTION,
            "data_origin": "official", "file_location": f"project root / {d['file']}",
            "sha256": before[d["file"]]["sha256"], "size_bytes": before[d["file"]]["size_bytes"],
            **info[doc_id], "pdf_creation_date_parsed": pdf_date(info[doc_id]["pdf_creation_date"]),
            "pdf_modification_date_parsed": pdf_date(info[doc_id]["pdf_modification_date"]),
            "pdf_metadata_note": "PDF file metadata dates describe the file, not an official publication date.",
            "pages_with_text": sum(1 for t in pages[doc_id].values() if len(t.strip()) >= 30),
            "pages_without_text": [n for n, t in pages[doc_id].items() if len(t.strip()) < 30],
            "extraction_tool": C.EXTRACTION_TOOL, "extraction_date": xdate,
            "review_status": "draft", "verification_status": "pending_verification", "approval_status": "not_approved",
        }
        if doc_id == C.HB:
            meta["table_of_contents"] = [{"title_as_printed": t, "toc_page": tp, "actual_start_page": ap}
                                         for t, tp, ap in C.HB_TOC]
            meta["layout_processing"] = hb_layout
        write_json(folder / "document_metadata.json", meta)

    # 4. Category datasets.
    all_sections = hb_sections + cal_sections
    all_chunks = hb_chunks + cal_chunks
    dup_hashes = [h for h, k in Counter(c["content_sha256"] for c in all_chunks).items() if k > 1]
    by_cat_sections = defaultdict(list)
    by_cat_chunks = defaultdict(list)
    for s in all_sections:
        by_cat_sections[s["category_id"]].append(s)
    for c in all_chunks:
        by_cat_chunks[c["category_id"]].append(c)

    structured = defaultdict(dict)  # cat -> filename -> rows
    for e in events:
        structured[e["category_id"]].setdefault("calendar_events.csv", []).append(e)
    structured["01"]["semester_terms.csv"] = terms
    structured["01"]["university_profile.csv"] = tables["profile"]
    structured["01"]["service_hours.csv"] = tables["service_hours"]
    structured["01"]["library_loan_periods.csv"] = tables["library_loans"]
    structured["02"]["schools.csv"] = schools
    structured["03"]["admission_conditions.csv"] = tables["admission_conditions"]
    structured["04"]["fee_policy_rules.csv"] = tables["fee_rules"]
    structured["04"]["financial_aid_programmes.csv"] = tables["financial_aid"]
    structured["04"]["bank_and_mobile_payment_details.csv"] = tables["bank"]
    structured["04"]["mpesa_purpose_codes.csv"] = mpesa
    structured["05"]["registrar_services.csv"] = tables["registrar_services"]
    structured["06"]["department_contacts.csv"] = tables["contacts"]
    structured["07"]["english_proficiency_requirements.csv"] = tables["english"]

    file_counts = {}
    for cat_id, (folder_name, cat_name) in C.CATEGORIES.items():
        base = cat_dir(cat_id)
        off = base / "official"
        secs = by_cat_sections.get(cat_id, [])
        chs = by_cat_chunks.get(cat_id, [])
        if secs:
            write_json(off / "document_sections.json", secs)
            write_json(off / "knowledge_chunks.json", chs)
            write_text(off / "sections_for_review.md", section_review_md(cat_id, secs))
            write_csv(off / "sections_index.csv", [{
                "record_id": s["record_id"], "document_id": s["document_id"], "section_number": s["section_number"],
                "section_heading": s["section_heading"], "page_start": s["page_start"], "page_end": s["page_end"],
                "content_chars": s["content_chars"], "chunk_count": s["chunk_count"], "flags": s["flags"],
                "issue_ids": s["issue_ids"], "review_status": s["review_status"],
                "verification_status": s["verification_status"]} for s in secs],
                ["record_id", "document_id", "section_number", "section_heading", "page_start", "page_end",
                 "content_chars", "chunk_count", "flags", "issue_ids", "review_status", "verification_status"])
        for fname, rows in sorted(structured.get(cat_id, {}).items()):
            if rows:
                write_csv(off / fname, rows, EVENT_FIELDS if fname == "calendar_events.csv" else fields_of(rows))
        if cat_id == "06":
            write_json(off / "department_routing_reference.json", {
                "description": "The five USIUBOT enquiry departments, with what the two official documents say about "
                               "them. Draft; nothing here is verified.",
                **base_record(C.HB, xdate), "documents_used": [C.HB, C.CAL],
                "departments": tables["routing"],
                "observation": "The documents also name a Finance Office (finance@usiu.ac.ke, calendar pages 6-7) and "
                               "many student-life offices that are not USIUBOT enquiry departments.",
            })
        file_counts[cat_id] = {"sections": len(secs), "chunks": len(chs),
                               "structured": {k: len(v) for k, v in structured.get(cat_id, {}).items()}}
        write_text(base / "external" / "README.md",
                   f"# {cat_name} — external data\n\nEmpty. No external (non-USIU-Africa) sources were collected in "
                   "Stage 2. External material, when added, goes here and is never mixed with `official/`.\n")
        write_json(base / "metadata" / "category_metadata.json", {
            "category_id": cat_id, "category_name": cat_name, "folder": folder_name, "extraction_date": xdate,
            "documents_contributing": sorted({s["document_id"] for s in secs} |
                                             {r["document_id"] for rows in structured.get(cat_id, {}).values() for r in rows}),
            "section_records": len(secs), "knowledge_chunks": len(chs),
            "structured_files": {k: len(v) for k, v in structured.get(cat_id, {}).items()},
            "coverage": [{"information": i, "status": st, "documents": docs, "notes": n} for i, st, docs, n in C.COVERAGE[cat_id]],
            "review_status": "draft", "verification_status": "pending_verification",
        })

    # 5. Validation outputs.
    vr = DATASETS / "validation_reports"
    write_csv(vr / "validation_issues.csv", issues,
              ["issue_id", "type", "severity", "requires_admin_decision", "documents", "pages", "summary", "evidence",
               "recommended_action", "detected_by"])
    write_csv(vr / "calendar_weekday_check.csv", weekday_issues or [{"event_id": "", "page": "", "date_as_printed": "",
                                                                     "day_as_printed": "", "event": "", "problem": "none found"}],
              ["event_id", "page", "date_as_printed", "day_as_printed", "event", "problem"])
    missing = [{"category_id": cid, "category_name": C.CATEGORIES[cid][1], "information": i, "status": st,
                "documents": docs, "notes": n} for cid, items in C.COVERAGE.items() for i, st, docs, n in items
               if st != "Extracted"]
    write_csv(vr / "missing_information.csv", missing, ["category_id", "category_name", "information", "status", "documents", "notes"])

    after = {d["file"]: sha256_file(PROJECT_ROOT / d["file"]) for d in C.DOCUMENTS.values()}
    integrity = {"checked_at": dt.datetime.now().isoformat(timespec="seconds"),
                 "files": {f: {"baseline_sha256": C.BASELINE_SHA256[f], "before_run": before[f]["sha256"],
                               "after_run": after[f], "unchanged": C.BASELINE_SHA256[f] == before[f]["sha256"] == after[f],
                               "size_bytes": before[f]["size_bytes"], "modified": before[f]["modified"]}
                           for f in after},
                 "access_mode": "read-only ('rb'); files were not copied, renamed or written"}
    write_json(vr / "pdf_integrity.json", integrity)
    if not all(v["unchanged"] for v in integrity["files"].values()):
        sys.exit("STOP: an original PDF changed during the run.")

    stats = {
        "extraction_date": xdate,
        "documents": {doc_id: {"file": d["file"], "pages": info[doc_id]["page_count"],
                               "sections": sum(1 for s in all_sections if s["document_id"] == doc_id),
                               "chunks": sum(1 for c in all_chunks if c["document_id"] == doc_id),
                               "content_chars": sum(s["content_chars"] for s in all_sections if s["document_id"] == doc_id)}
                      for doc_id, d in C.DOCUMENTS.items()},
        "calendar_events": len(events), "calendar_terms": len(terms),
        "structured_rows": {f"{cid}/{f}": len(r) for cid, files in structured.items() for f, r in files.items()},
        "structured_rows_total": sum(len(r) for files in structured.values() for r in files.values()),
        "routing_reference_departments": len(tables["routing"]),
        "sections_total": len(all_sections), "chunks_total": len(all_chunks),
        "chunk_size_max_chars": CHUNK_CHARS, "largest_chunk_chars": max(c["content_chars"] for c in all_chunks),
        "duplicate_chunk_hashes": len(dup_hashes),
        "evidence_quotes_checked": ev.checked, "evidence_failures": len(ev.failures),
        "emails_in_pdfs": len(emails_found), "emails_without_contact_record": unaccounted,
        "issues_total": len(issues), "issues_by_severity": dict(Counter(i["severity"] for i in issues)),
        "issues_requiring_admin_decision": sum(1 for i in issues if i["requires_admin_decision"] == "yes"),
        "per_category": file_counts,
        "records_by_status": {"draft": len(all_sections) + len(all_chunks) + sum(len(r) for f in structured.values() for r in f.values()),
                              "approved": 0},
        "data_origin": {"official": "all records", "external": 0, "synthetic": 0},
    }
    write_json(vr / "extraction_statistics.json", stats)

    # 6. Collection register.
    reg = []
    n = 0
    for cid, items in C.COVERAGE.items():
        for info_req, st, docs, note in items:
            n += 1
            titles = "; ".join(C.DOCUMENTS[d]["title"] for d in docs) or "—"
            files = "; ".join(f"project root / {C.DOCUMENTS[d]['file']}" for d in docs) or "—"
            years = "; ".join(C.DOCUMENTS[d]["academic_year"] for d in docs) or "—"
            pubs = "; ".join(f"{C.DOCUMENTS[d]['title']}: {C.DOCUMENTS[d]['publication_date']}" for d in docs) or "—"
            reg.append({
                "Dataset ID": f"DS-{cid}-{n:03d}", "Dataset category": f"{cid} {C.CATEGORIES[cid][1]}",
                "Information required": info_req, "Source title": titles, "Source URL or document": files,
                "Source institution": C.INSTITUTION if docs else "—",
                "Data type": "PDF text sections and structured CSV" if docs else "—",
                "Collection date": xdate if docs else "—", "Publication date": pubs, "Effective academic year": years,
                "Verification status": {"Extracted": "Extracted; Pending verification",
                                        "Partially extracted": "Extracted (partial); Pending verification",
                                        "Unavailable": "Unavailable"}[st],
                "Approval status": "Not approved (draft)" if docs else "—",
                "Synthetic or real": "Real (official USIU-Africa document)" if docs else "—",
                "Notes": note + ("" if docs else " Needs another official source."),
            })
    write_csv(DATASETS / "collection_register" / "collection_register.csv", reg, list(reg[0].keys()))

    write_readmes(stats, structured, by_cat_sections, issues, xdate, integrity)

    print(json.dumps({k: stats[k] for k in ("sections_total", "chunks_total", "calendar_events", "structured_rows_total",
                                            "evidence_quotes_checked", "issues_total", "duplicate_chunk_hashes")}, indent=1))


if __name__ == "__main__":
    main()
