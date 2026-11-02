"""Shared helpers for the website part of the USIUBOT dataset (standard library only)."""
import csv
import hashlib
import json
import re
from pathlib import Path

DATASETS = Path(__file__).resolve().parents[1]
PROJECT = DATASETS.parent
WEB = DATASETS / "web_sources"
SNAP = WEB / "snapshots"
COLLECTED = "2026-11-01"

CATEGORY_DIRS = {
    "01": "01_general_university_information",
    "02": "02_academic_programmes",
    "03": "03_admissions_and_applications",
    "04": "04_fees_and_payments",
    "05": "05_registrar_and_academic_administration",
    "06": "06_department_contacts_and_query_routing",
    "07": "07_academic_documents_results_and_verified_eligibility",
    "08": "08_questions_answers_and_unresolved_enquiries",
}
CATEGORY_NAMES = {
    "01": "General University Information",
    "02": "Academic Programmes",
    "03": "Admissions and Applications",
    "04": "Fees and Payments",
    "05": "Registrar and Academic Administration",
    "06": "Department Contacts and Query Routing",
    "07": "Academic Documents, Results and Verified Eligibility",
    "08": "Questions, Answers and Unresolved Enquiries",
}

# The traceability columns carried by every website-derived record (the user's required list).
TRACE = ["record_id", "category_id", "category_name", "topic", "information", "source_title", "source_url",
         "source_file", "page", "section", "date_collected", "publication_date", "academic_year", "source_type",
         "publisher", "verification_status", "review_status", "approval_status", "conflict_or_warning", "issue_ids",
         "evidence_text", "last_checked"]

_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")


def norm(text):
    """Whitespace-normalise and drop markdown link targets and emphasis, for evidence matching."""
    text = _LINK.sub(r"\1", text)
    text = re.sub(r"[*_`]", "", text)
    text = text.replace(" ", " ")
    return re.sub(r"\s+", " ", text).strip()


_snap_cache = {}


def snapshot(page_id):
    if page_id not in _snap_cache:
        p = SNAP / f"{page_id}.md"
        _snap_cache[page_id] = p.read_text(encoding="utf-8") if p.exists() else None
    return _snap_cache[page_id]


def check_evidence(page_id, quote, failures, rid):
    text = snapshot(page_id)
    if text is None:
        failures.append(f"{rid}: snapshot '{page_id}' does not exist")
        return False
    if norm(quote) not in norm(text):
        failures.append(f"{rid}: evidence not found in {page_id}: {quote[:90]!r}")
        return False
    return True


def sha256_text(t):
    return hashlib.sha256(t.encode("utf-8")).hexdigest()


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for block in iter(lambda: f.read(1 << 16), b""):
            h.update(block)
    return h.hexdigest()


def write_csv(path, rows, fields=None):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = []
        for r in rows:
            for k in r:
                if k not in fields:
                    fields.append(k)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="raise")
        w.writeheader()
        for r in rows:
            w.writerow({k: _cell(r.get(k, "")) for k in fields})
    return len(rows)


def _cell(v):
    if v is None:
        return ""
    if isinstance(v, (list, tuple)):
        return "; ".join(str(x) for x in v)
    return v


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def read_csv(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def rel(p):
    return Path(p).resolve().relative_to(DATASETS).as_posix()
