"""Import the completed USIUBOT dataset (``usiubot_datasets/``) into the approved-source registry.

How it fits the existing design
-------------------------------
* One dataset *section* (a headed block of a PDF page range or of a web page) becomes one
  source in the ``sources`` collection, keyed ``dataset:<section_id>``. Its passages are the
  dataset's own chunks (max 1000 characters, heading kept with its text), so page numbers,
  section headings and chunk ids survive into the BM25 index.
* Everything is imported as a **draft**. Nothing is approved here: an administrator reviews
  and approves sources in the admin Sources tab (singly or a selected batch). Only approved
  sources are indexed and can be retrieved, exactly as before.
* Re-running the import is safe (refresh): unchanged sections are skipped; changed sections
  are updated, and an approved section whose text changed goes back to draft for re-approval;
  sections that disappeared from the dataset are archived. Administrator edits to a section's
  title or department are kept.
* Only ``official`` (USIU-Africa) and ``external`` (e.g. KUCCPS) records are accepted. External
  sources keep their origin and are always labelled as not USIU-Africa policy.
* Unresolved conflicts and warnings from ``validation_reports/conflict_and_verification_register.csv``
  are attached to every section that the dataset links to them, and shown with answers.
* A dataset folder containing a ``TEST_DATASET`` marker file is a test fixture: its records are
  marked ``is_test`` and can only be imported/retrieved when the app runs in test mode.
"""

import csv
import datetime
import hashlib
import json
import logging
import re
from collections import Counter, OrderedDict
from pathlib import Path

from services.sources import CATEGORIES, SourceError

logger = logging.getLogger(__name__)

TEST_MARKER = "TEST_DATASET"
CHUNK_FILES = ("knowledge_chunks.json", "web_knowledge_chunks.json")
REGISTER = "validation_reports/conflict_and_verification_register.csv"
VALIDATION = "validation_reports/final_validation.json"

# Default department per category (the dataset's own routing model).
CATEGORY_DEPARTMENT = {
    "01": "general_university",
    "02": "academic_programmes",
    "03": "admissions",
    "04": "finance",
    "05": "registrar",
    "06": "general_university",
    "07": "admissions",
    "08": "general_university",
}
# More specific departments, matched against the document id and section heading.
DEPARTMENT_HINTS = (
    (re.compile(r"financial[-_ ]aid|scholarship|bursar", re.I), "admissions"),
    (re.compile(r"library|librar", re.I), "library"),
    (re.compile(r"\bict\b|helpdesk|computer lab|e-?mail account|wi-?fi", re.I), "ict"),
    (re.compile(r"housing|hostel|accommodation|health|counsel|disabilit|student[-_ ]life|dean of students|"
                r"student affairs|discipline|conduct", re.I), "student_affairs"),
    (re.compile(r"commencement|graduation|transcript|calendar|registrar", re.I), "registrar"),
    (re.compile(r"fee|tuition|payment|refund|bank|m-?pesa", re.I), "finance"),
)
PAYMENT_ISSUES = {"V01", "V02", "V03", "V32", "W26"}
PAYMENT_TEXT = re.compile(r"account\s*(number|no\b)|swift|pay\s*bill|a/c\b|branch code", re.I)
WARNING_TYPES = {"conflict", "inconsistency", "outdated", "ambiguity", "document_quality", "missing_source"}


# Issues students are warned about with an answer. The rest (low severity, numbering, a document
# without a public link, which the citation already shows) are visible to administrators only.
USER_WARNING_TYPES = {"conflict", "outdated", "inconsistency"}
USER_WARNING_STATUSES = {"open", "unresolved", "partially_resolved"}


def is_user_warning(row):
    return (row.get("type") in USER_WARNING_TYPES and row.get("status") in USER_WARNING_STATUSES
            and row.get("severity") in ("medium", "high"))


class DatasetError(RuntimeError):
    """The dataset folder is missing or unusable. Messages are safe to show to admins."""


def _date(value):
    if not value or not isinstance(value, str) or not re.match(r"^\d{4}-\d{2}-\d{2}$", value[:10]):
        return None
    try:
        return datetime.datetime.fromisoformat(value[:10]).replace(tzinfo=datetime.timezone.utc)
    except ValueError:
        return None


def department_for(category, document_id="", heading=""):
    """Suggested department of a dataset section (administrators can change it before approving).

    Programme, admissions and eligibility categories keep their department (a counselling
    *programme* is not Student Affairs). Fees and payments go to Finance, except financial aid
    (Admissions and Financial Aid office). Other categories use the hints, then the default.
    """
    default = CATEGORY_DEPARTMENT.get(category, "general_university")
    if category in ("02", "03", "07"):
        return default
    text = f"{document_id} {heading}"
    for pattern, department in DEPARTMENT_HINTS:
        if pattern.search(text):
            if category == "04" and department not in ("admissions", "finance"):
                continue
            if department == "finance" and category != "04":
                continue
            return department
    return default


def _norm(text):
    return re.sub(r"\s+", " ", (text or "").lower()).strip()


class DatasetImporter:
    def __init__(self, registry, dataset_dir):
        self.registry = registry
        self.dir = Path(dataset_dir) if dataset_dir else None

    # --- reading -----------------------------------------------------------------
    def _check_dir(self):
        if not self.dir or not self.dir.is_dir():
            raise DatasetError("Dataset folder not found. Set DATASET_DIR to the usiubot_datasets folder.")
        if not any(self.dir.glob("0*/*/*knowledge_chunks.json")):
            raise DatasetError("The dataset folder has no knowledge_chunks.json files.")

    @property
    def is_test_dataset(self):
        return bool(self.dir and (self.dir / TEST_MARKER).exists())

    def issues(self):
        path = self.dir / REGISTER
        if not path.exists():
            return {}
        with open(path, encoding="utf-8-sig", newline="") as f:
            return {r["issue_id"]: r for r in csv.DictReader(f)}

    def validation_summary(self):
        path = self.dir / VALIDATION
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return {"validated_at": data.get("validated_at"), "blocking_failures": data.get("blocking_failures"),
                "warnings": data.get("warnings")}

    def load_sections(self):
        """Group every chunk of the dataset by section. Returns ``(sections, report)``."""
        self._check_dir()
        sections = OrderedDict()
        report = Counter()
        seen_text = {}
        duplicates = []
        for path in sorted(self.dir.glob("0*/*/*.json")):
            if path.name not in CHUNK_FILES:
                continue
            folder_origin = "external" if path.parent.name == "external" else "official"
            for chunk in json.loads(path.read_text(encoding="utf-8")):
                report["chunks_read"] += 1
                section_id = chunk.get("section_id") or chunk.get("record_id")
                text = chunk.get("content") or ""
                if not section_id or not text.strip():
                    report["chunks_without_text"] += 1
                    continue
                # Duplicate passages (same text under another section) are indexed only once.
                body = _norm(text.split("\n\n", 1)[-1] if chunk.get("heading_path") else text)
                digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
                if digest in seen_text and seen_text[digest] != section_id:
                    duplicates.append({"chunk_id": chunk.get("chunk_id"), "duplicate_of": seen_text[digest]})
                    continue
                seen_text.setdefault(digest, section_id)
                origin = chunk.get("data_origin") or folder_origin
                if origin != folder_origin:
                    report["origin_mismatch"] += 1
                sec = sections.setdefault(section_id, {"chunks": [], "first": chunk, "origin": origin,
                                                       "file": str(path.relative_to(self.dir).as_posix())})
                sec["chunks"].append(chunk)
        report["sections"] = len(sections)
        report["duplicate_chunks_skipped"] = len(duplicates)
        return sections, dict(report), duplicates

    def build_record(self, section_id, sec, issues):
        first = sec["chunks"][0]
        category = first.get("category_id")
        if category not in CATEGORIES:
            raise SourceError(f"Unknown category {category!r}")
        document_file = first.get("document_file") or ""
        content_type = "pdf" if document_file.lower().endswith(".pdf") else "html"
        heading_path = first.get("heading_path") or []
        heading = first.get("section_heading") or (heading_path[-1] if heading_path else "")
        number = first.get("section_number") or ""
        doc_title = first.get("document_title") or first.get("document_id") or "USIU-Africa source"
        label = heading if not number or str(number).startswith("not numbered") else f"{number} {heading}"
        title = f"{doc_title} — {label}" if label and label not in doc_title else doc_title
        pages = sorted({p for c in sec["chunks"] for p in (c.get("pages") or [c.get("page_start"), c.get("page_end")])
                        if isinstance(p, int)})
        issue_ids = sorted({i for c in sec["chunks"] for i in (c.get("issue_ids") or [])})
        open_issues = []
        for i in issue_ids:
            row = issues.get(i)
            if row and row.get("status") != "resolved" and row.get("type") in WARNING_TYPES:
                open_issues.append({"id": i, "type": row["type"], "status": row.get("status"),
                                    "severity": row.get("severity") or "low",
                                    "user_warning": is_user_warning(row),
                                    "summary": (row.get("summary") or "")[:400]})
        text_all = " ".join(c.get("content", "") for c in sec["chunks"])
        flags = []
        if sec["origin"] == "external":
            flags.append("external_source")
        if PAYMENT_ISSUES & set(issue_ids) or PAYMENT_TEXT.search(text_all):
            flags.append("payment_details")
        if any(i["type"] == "conflict" and i["user_warning"] for i in open_issues):
            flags.append("conflict")
        if any(i["type"] == "outdated" and i["user_warning"] for i in open_issues):
            flags.append("possibly_outdated")
        if open_issues:
            flags.append("unresolved_issue")
        url = first.get("source_url") or None
        if not url and content_type == "pdf":
            flags.append("no_public_url")
        collected = first.get("collection_date") or first.get("extraction_date")
        chunks = [{"chunk_id": c.get("chunk_id") or c.get("record_id"), "text": c["content"],
                   "page_start": c.get("page_start"), "page_end": c.get("page_end"),
                   "section_heading": c.get("section_heading") or heading}
                  for c in sorted(sec["chunks"], key=lambda c: c.get("chunk_index") or 0)]
        dataset = {
            "section_id": section_id,
            "document_id": first.get("document_id"),
            "document_title": doc_title,
            "document_file": document_file or None,
            "page_start": pages[0] if pages else None,
            "page_end": pages[-1] if pages else None,
            "section_heading": heading,
            "section_number": number or None,
            "heading_path": heading_path,
            "publisher": first.get("publisher") or first.get("source_institution"),
            "collected_at": collected,
            "last_checked": first.get("last_checked") or collected,
            "publication_date": first.get("publication_date") or "Publication date not stated",
            "academic_year": first.get("academic_year"),
            "content_fidelity": first.get("content_fidelity"),
            "verification_status": first.get("verification_status", "pending_verification"),
            "issue_ids": issue_ids,
            "issues": open_issues,
            "dataset_file": sec["file"],
        }
        notes = (f"Imported from usiubot_datasets ({sec['file']}). Review the text against the original "
                 f"{'document page' if content_type == 'pdf' else 'web page'} before approving.")
        return {
            "section_id": section_id, "title": title[:300], "url": url,
            "department": department_for(category, first.get("document_id") or "", " ".join(heading_path) or heading),
            "category": category, "data_origin": sec["origin"], "content_type": content_type,
            "retrieved_at": _date(collected), "notes": notes, "dataset": dataset, "chunks": chunks,
            "review_flags": flags, "is_test": self.is_test_dataset,
        }

    # --- import --------------------------------------------------------------------
    def run(self, dry_run=False, actor="dataset-import", archive_missing=True):
        """Import or refresh the dataset. Never approves anything. Returns a report dict."""
        sections, read_report, duplicates = self.load_sections()
        issues = self.issues()
        outcomes = Counter()
        by_category = Counter()
        refused = []
        for section_id, sec in sections.items():
            try:
                record = self.build_record(section_id, sec, issues)
                outcome, _ = self.registry.upsert_dataset_source(record, actor=actor, dry_run=dry_run)
            except SourceError as e:
                refused.append({"section_id": section_id, "error": str(e)})
                continue
            outcomes[outcome] += 1
            by_category[record["category"]] += 1
        archived = []
        if archive_missing and not refused:
            archived = self.registry.archive_missing_dataset_sources(list(sections), actor=actor, dry_run=dry_run)
        report = {
            "dry_run": dry_run,
            "dataset_dir": self.dir.name,
            "test_dataset": self.is_test_dataset,
            "read": read_report,
            "outcomes": dict(outcomes),
            "sections_by_category": dict(sorted(by_category.items())),
            "archived_missing": len(archived),
            "refused": refused[:50],
            "refused_count": len(refused),
            "duplicates_skipped": duplicates[:50],
            "dataset_validation": self.validation_summary(),
            "approved_by_import": 0,
        }
        logger.info("Dataset import (%s): %s", "dry run" if dry_run else "applied", dict(outcomes))
        return report

    def status(self):
        """What the registry holds from the dataset, by status, category and origin."""
        rows = list(self.registry.sources.aggregate([
            {"$match": {"dataset": {"$exists": True}}},
            {"$group": {"_id": {"status": "$status", "category": "$category", "origin": "$data_origin"},
                        "n": {"$sum": 1}}},
        ]))
        by_status, by_category, by_origin = Counter(), {}, Counter()
        for r in rows:
            key = r["_id"]
            by_status[key["status"]] += r["n"]
            by_origin[key.get("origin") or "official"] += r["n"]
            cat = by_category.setdefault(key.get("category"), Counter())
            cat[key["status"]] += r["n"]
        dataset_available = bool(self.dir and self.dir.is_dir())
        return {
            "dataset_available": dataset_available,
            "test_dataset": self.is_test_dataset if dataset_available else False,
            "dataset_validation": self.validation_summary() if dataset_available else None,
            "imported_sections": sum(by_status.values()),
            "by_status": dict(by_status),
            "by_origin": dict(by_origin),
            "by_category": {k: dict(v) for k, v in sorted(by_category.items(), key=lambda kv: str(kv[0]))},
            "categories": CATEGORIES,
        }
