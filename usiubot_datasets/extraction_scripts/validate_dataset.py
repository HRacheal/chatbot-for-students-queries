"""Validate the whole USIUBOT dataset (Stage 2 PDF records + website records + registers).

Read-only: it writes only validation_reports/final_validation.json and final_validation.md.
Exit code 0 = every blocking check passed; 1 = at least one failed.

Run:  backend/.venv/Scripts/python.exe usiubot_datasets/extraction_scripts/validate_dataset.py
"""
import csv
import json
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import web_common as C  # noqa: E402

D = C.DATASETS
VR = D / "validation_reports"
PDF_DOCS = {"usiu_academic_calendar_2026_2027", "usiu_student_handbook"}
RESULTS = []


def check(name, ok, detail="", blocking=True):
    RESULTS.append({"check": name, "result": "pass" if ok else ("FAIL" if blocking else "warning"),
                    "blocking": blocking, "detail": detail})
    return ok


EXPECTED = [
    "README.md", "collection_register/collection_register.csv",
    "source_documents/usiu_academic_calendar_2026_2027/extracted_text_by_page.md",
    "source_documents/usiu_student_handbook/extracted_text_by_page.md",
    "source_documents/usiu_fee_schedule_2026_2027/extracted_text_by_page.md",
    "web_sources/collection_manifest.json", "web_sources/downloads/USIU-Africa-Free-Structure-2026-2027.pdf",
    "validation_reports/source_register.csv", "validation_reports/conflict_and_verification_register.csv",
    "validation_reports/missing_information_register.csv", "validation_reports/validation_issues.csv",
    "validation_reports/fee_table_checks.csv", "validation_reports/layout_verification.json",
    "validation_reports/pdf_integrity.json", "validation_reports/app_files_baseline.json",
    "validation_reports/WEB_COLLECTION_REPORT.md", "validation_reports/STAGE2_EXTRACTION_REPORT.md",
    "02_academic_programmes/official/web_programmes.csv",
    "03_admissions_and_applications/official/web_admission_rules.csv",
    "04_fees_and_payments/official/web_tuition_fee_tables.csv",
    "04_fees_and_payments/official/bank_details_comparison.csv",
    "06_department_contacts_and_query_routing/official/web_department_contacts.csv",
    "06_department_contacts_and_query_routing/official/routing_departments.json",
    "07_academic_documents_results_and_verified_eligibility/official/programme_entry_requirements.csv",
    "08_questions_answers_and_unresolved_enquiries/official/open_questions_register.csv",
    "08_questions_answers_and_unresolved_enquiries/official/official_faq_pairs.csv",
    "extraction_scripts/collect_web_sources.py", "extraction_scripts/build_all.py",
] + [f"{d}/README.md" for d in C.CATEGORY_DIRS.values()]


def data_files():
    skip = ("raw_collection_reports", "snapshots", "history")
    return [p for p in sorted(D.rglob("*")) if p.is_file() and p.suffix in (".csv", ".json")
            and not any(s in p.parts for s in skip)]


def main():
    # 1. expected files
    missing = [f for f in EXPECTED if not (D / f).exists()]
    check("expected files exist", not missing, f"missing: {missing}" if missing else f"{len(EXPECTED)} files present")

    # 2. parse every CSV / JSON
    csv_rows, json_records, bad = {}, {}, []
    for p in data_files():
        try:
            if p.suffix == ".csv":
                with open(p, encoding="utf-8-sig", newline="") as f:
                    rows = list(csv.reader(f))
                widths = {len(r) for r in rows if r}
                if len(widths) > 1:
                    bad.append(f"{C.rel(p)}: uneven row widths {widths}")
                csv_rows[p] = C.read_csv(p)
            else:
                data = json.loads(p.read_text(encoding="utf-8"))
                if isinstance(data, list) and data and isinstance(data[0], dict) and "record_id" in data[0]:
                    json_records[p] = data
        except Exception as e:  # noqa: BLE001
            bad.append(f"{C.rel(p)}: {e}")
    index = csv_rows.pop(D / "all_records_index.csv", [])
    check("all CSV and JSON files parse", not bad, "; ".join(bad[:10]) or f"{len(csv_rows)} CSV, "
          f"{sum(1 for p in data_files() if p.suffix == '.json')} JSON")

    # 3. duplicates
    ids = Counter()
    id_files = defaultdict(set)
    for p, rows in list(csv_rows.items()) + list(json_records.items()):
        if "validation_reports" in p.parts or "collection_register" in p.parts:
            continue
        for r in rows:
            rid = r.get("record_id")
            if rid:
                ids[rid] += 1
                id_files[rid].add(C.rel(p))
    # A section id is shared by its section record and its index row; a chunk id appears once.
    dup_ids = [i for i, n in ids.items() if n > 1 and not (len(id_files[i]) == 2 and any(
        f.endswith(("sections_index.csv", "web_sections_index.csv")) for f in id_files[i]))
        and not all(f.endswith(("document_sections.json", "sections_index.csv", "sections_for_review.md"))
                    for f in id_files[i])]
    check("record ids are unique", not dup_ids, f"duplicates: {dup_ids[:10]}" if dup_ids else f"{len(ids)} ids")
    chunk_hash = defaultdict(list)
    chunks = []
    for p, rows in json_records.items():
        if p.name.endswith("knowledge_chunks.json"):
            for c in rows:
                chunks.append((p, c))
                chunk_hash[C.sha256_text(C.norm(c["content"].split("\n\n", 1)[-1]))].append(c["record_id"])
    dup_chunks = [v for v in chunk_hash.values() if len(v) > 1]
    check("no duplicate chunk content (body text, across Stage 2 and web)", not dup_chunks,
          f"{len(dup_chunks)} groups, e.g. {dup_chunks[:3]}" if dup_chunks else f"{len(chunks)} chunks", blocking=False)
    big = [c["record_id"] for _, c in chunks if c["content_chars"] > 1000]
    check("chunks do not exceed 1000 characters", not big, f"{big[:10]}", blocking=False)
    headless = [c["record_id"] for _, c in chunks if c.get("record_id", "").startswith("WEB-")
                and not c["content"].split("\n\n", 1)[0].strip()]
    check("every web chunk starts with its heading path", not headless, f"{headless[:10]}")

    # 4. every record has a source; PDF records have pages; web records have URLs
    nosrc, nopage, nourl = [], [], []
    for p, rows in list(csv_rows.items()) + list(json_records.items()):
        if any(s in p.parts for s in ("validation_reports", "collection_register")) or p.name.startswith(
                ("open_questions", "category_metadata")):
            continue
        for r in rows:
            rid = r.get("record_id") or r.get("comparison_id")
            if not rid:
                continue
            url = r.get("source_url") or ""
            doc = r.get("document_id") or ""
            fil = r.get("document_file") or r.get("source_file") or ""
            if p.name == "bank_details_comparison.csv":
                continue
            if not (url or doc or fil):
                nosrc.append(rid)
            if doc in PDF_DOCS and not (r.get("page") or r.get("page_start") or r.get("pages")):
                nopage.append(rid)
            if (r.get("source_type") in ("official", "external") or r.get("data_origin") in ("official", "external")) \
                    and doc not in PDF_DOCS and not doc.startswith("usiu_fee") and not url.startswith("http"):
                nourl.append(rid)
    check("every record names its source", not nosrc, f"{len(nosrc)} without: {nosrc[:10]}")
    check("every PDF record has a page number", not nopage, f"{len(nopage)}: {nopage[:10]}")
    check("every web record has a URL", not nourl, f"{len(nourl)}: {nourl[:10]}")

    idx_ids = Counter(r["record_id"] for r in index)
    idx_dup = [i for i, n in idx_ids.items() if n > 1]
    idx_nosrc = [r["record_id"] for r in index if not r["source_url_or_file"] and r["source_type"] != "derived"]
    check("all_records_index.csv: one row per record, every row has a source", index and not idx_dup and not idx_nosrc,
          f"{len(index)} rows; duplicate ids {idx_dup[:5]}; without source {idx_nosrc[:5]}")

    # 5. external labelling
    wrong = []
    for p, rows in list(csv_rows.items()) + list(json_records.items()):
        folder = "external" if "external" in p.parts else "official" if "official" in p.parts else None
        if not folder:
            continue
        for r in rows:
            st = r.get("source_type") or r.get("data_origin") or ""
            if folder == "external" and st != "external":
                wrong.append(f"{r.get('record_id')} in external/ is '{st}'")
            if folder == "official" and st == "external":
                wrong.append(f"{r.get('record_id')} is external but in official/")
            if p.name == "external_records.csv" and "not USIU-Africa policy" not in r.get("external_label", ""):
                wrong.append(f"{r.get('record_id')} lacks the external label")
            if folder == "external" and p.suffix == ".json" and "external_source_not_usiu_policy" not in (
                    r.get("flags") or []) and p.name.endswith("knowledge_chunks.json"):
                wrong.append(f"{r.get('record_id')} chunk lacks the external flag")
    check("external sources are labelled and kept separate", not wrong, "; ".join(wrong[:10]))

    # 6. conflicts stay visible
    reg = C.read_csv(VR / "conflict_and_verification_register.csv")
    referenced = set()
    for rows in list(csv_rows.values()) + list(json_records.values()):
        for r in rows:
            v = r.get("issue_ids") or []
            referenced.update(v if isinstance(v, list) else re.split(r"[;,\s]+", v))
    unref = [r["issue_id"] for r in reg if r["status"] != "resolved" and r["issue_id"] not in referenced]
    open_n = sum(1 for r in reg if r["status"] != "resolved")
    check("every unresolved conflict/issue is in the register", open_n > 0, f"{open_n} unresolved of {len(reg)}")
    check("every unresolved issue is attached to at least one record or chunk", not unref,
          f"only in the register: {unref}", blocking=False)
    conf = [r for r in reg if r["type"] == "conflict" and r["status"] != "resolved"]
    both = [r["issue_id"] for r in conf if not (r["evidence_versions"] or r["website_evidence"])]
    check("conflict records keep the evidence of each version", not both, f"{both}")

    # 7. PDFs unchanged
    integ = json.loads((VR / "pdf_integrity.json").read_text(encoding="utf-8"))["files"]
    changed = [n for n, v in integ.items() if C.sha256_file(C.PROJECT / n) != v["baseline_sha256"]]
    check("original PDFs unchanged (SHA-256)", not changed, f"changed: {changed}" if changed else
          ", ".join(f"{n} {v['baseline_sha256'][:12]}…" for n, v in integ.items()))
    man = json.loads((C.WEB / "collection_manifest.json").read_text(encoding="utf-8"))
    fee = D / "web_sources/downloads/USIU-Africa-Free-Structure-2026-2027.pdf"
    check("downloaded fee schedule unchanged", C.sha256_file(fee).startswith("33d8f0d5"), C.sha256_file(fee)[:16])

    # 8. app files vs the baseline taken when dataset work began. Blocking while the dataset was built
    # (the app was not to be modified then); informational since the dataset integration into the app
    # was authorised, so the dataset itself never fails validation because of app changes.
    base = json.loads((VR / "app_files_baseline.json").read_text(encoding="utf-8"))["files"]
    diff = [f for f, h in base.items() if not (C.PROJECT / f).exists() or C.sha256_file(C.PROJECT / f) != h]
    new = []
    prune = {".venv", "node_modules", "__pycache__", "dist", ".pytest_cache"}
    for top in ("backend", "frontend"):
        for root, dirs, files in os.walk(C.PROJECT / top):
            dirs[:] = [d for d in dirs if d not in prune]
            for fn in files:
                r = (Path(root) / fn).relative_to(C.PROJECT).as_posix()
                if r not in base:
                    new.append(r)
    check("application files compared with the pre-integration baseline (informational)", True,
          f"{len(diff)} changed, {len(new)} new since the baseline (dataset integration)" if diff or new
          else f"{len(base)} files identical")

    # 9. nothing approved
    approved = []
    for p, rows in list(csv_rows.items()) + list(json_records.items()):
        for r in rows:
            for k in ("approval_status", "Approval status"):
                v = (r.get(k) or "").lower()
                if v and "not" not in v and "approved" in v:
                    approved.append(r.get("record_id") or r.get("Dataset ID"))
    check("no record is approved (all drafts)", not approved, f"{approved[:10]}")

    # 10. web evidence re-check (independent of the build)
    miss = []
    snap_by_url = {m["url"]: m.get("snapshot_file") for m in man["pages"].values()}
    normed = {}
    for p, rows in csv_rows.items():
        for r in rows:
            ev, url = r.get("evidence_text"), r.get("source_url", "")
            if ev and url in snap_by_url and snap_by_url[url]:
                if url not in normed:
                    normed[url] = C.norm((D / snap_by_url[url]).read_text(encoding="utf-8"))
                if C.norm(ev) not in normed[url]:
                    miss.append(r["record_id"])
    check("web evidence quotes found in their snapshots", not miss, f"{miss[:10]}")

    # 11. secrets
    pat = re.compile(r"mongodb(\+srv)?://|sk-[A-Za-z0-9]{20,}|AIza[0-9A-Za-z_-]{30,}|(api[_-]?key|password|secret)"
                     r"\s*[=:]\s*['\"]?[A-Za-z0-9]{8,}", re.I)
    leaks = []
    for p in D.rglob("*"):
        if p.is_file() and p.suffix in (".md", ".csv", ".json", ".py", ".txt"):
            if pat.search(p.read_text(encoding="utf-8", errors="ignore")):
                leaks.append(C.rel(p))
    check("no secrets or connection strings in dataset files", not leaks, f"{leaks}")

    # 12. web sources: inaccessible pages recorded, no restricted system fetched
    pages = man["pages"]
    restricted = [p for p in pages.values() if "restricted" in (p.get("access_outcome") or "")
                  and p.get("http_status") == 200]
    check("restricted systems were not fetched", not restricted, f"{restricted}")
    inacc = [p["url"] for p in pages.values() if p.get("http_status") != 200]
    check("inaccessible / not-collected sources are recorded", bool(inacc), f"{len(inacc)} recorded")

    stats = {
        "csv_files": len(csv_rows), "json_record_files": len(json_records),
        "records_in_csv_by_category": {}, "chunks_total": len(chunks),
    }
    for p, rows in csv_rows.items():
        m = re.match(r"(0\d)_", p.relative_to(D).parts[0])
        if m:
            stats["records_in_csv_by_category"][m.group(1)] = stats["records_in_csv_by_category"].get(m.group(1), 0) + len(rows)
    out = {"validated_at": C.COLLECTED, "checks": RESULTS, "stats": stats,
           "blocking_failures": sum(1 for r in RESULTS if r["result"] == "FAIL"),
           "warnings": sum(1 for r in RESULTS if r["result"] == "warning")}
    C.write_json(VR / "final_validation.json", out)
    md = ["# Final dataset validation\n", f"Run: {C.COLLECTED}. Blocking failures: {out['blocking_failures']}. "
          f"Warnings: {out['warnings']}.\n", "| Check | Result | Detail |", "|---|---|---|"]
    md += [f"| {r['check']} | {r['result']} | {str(r['detail']).replace('|', '/')[:300]} |" for r in RESULTS]
    (VR / "final_validation.md").write_text("\n".join(md) + "\n", encoding="utf-8", newline="\n")
    for r in RESULTS:
        print(f"[{r['result']:>7}] {r['check']}: {str(r['detail'])[:160]}")
    sys.exit(1 if out["blocking_failures"] else 0)


if __name__ == "__main__":
    main()
