"""Build the website, external and register parts of the USIUBOT dataset.

Inputs (all inside usiubot_datasets/):
  web_sources/collection_manifest.json and web_sources/snapshots/*.md   (from import_collection_reports.py)
  web_sources/downloads/USIU-Africa-Free-Structure-2026-2027.pdf         (official fee schedule)
  extraction_scripts/web_config.py, web_curated.py, web_registers.py      (curated, evidence-checked lists)
  the Stage 2 outputs (category CSVs, validation_reports/validation_issues.csv)

Every curated value must be found in its snapshot (evidence check); the build stops otherwise.
Nothing is approved: every record is draft / pending_verification / not_approved.

Run:  backend/.venv/Scripts/python.exe usiubot_datasets/extraction_scripts/build_web_dataset.py
"""
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import web_common as C  # noqa: E402
import web_config as W  # noqa: E402
import web_curated as K  # noqa: E402
import web_registers as R  # noqa: E402
import extraction_config as E  # noqa: E402

D = C.DATASETS
VR = D / "validation_reports"
CHUNK_LIMIT = 1000  # same as the app's CHUNK_SIZE
MANIFEST = json.loads((C.WEB / "collection_manifest.json").read_text(encoding="utf-8"))
PAGES = MANIFEST["pages"]
OK_PAGES = {pid: m for pid, m in PAGES.items() if m.get("http_status") == 200}
FAIL = []

ACADEMIC_YEAR = {  # only where the page itself states it (evidence checked below)
    "tuition-fees": ("2026-2027", "USIU-Africa 2026-2027 Fee Information."),
    "documents__on-campus-programs-fee-structure": ("2026/27", "On Campus Programs Fee Structure 2026/27"),
    "documents__academic-calendar-2026-2027": ("2026-2027", "Academic Calendar 2026 – 2027 (Current)"),
    "documents__academic-calendar-2025-2026": ("2025-2026", "Academic Calendar 2025-2026"),
    "2026-48th-commencement": ("2026 (48th Commencement)", "2026 48th Commencement"),
    "pre-registration-check": ("Fall 2026", "FALL /SEPTEMBER SEMESTER 2026"),
}
for _pid, (_ay, _q) in ACADEMIC_YEAR.items():
    C.check_evidence(_pid, _q, FAIL, f"academic_year:{_pid}")

# --------------------------------------------------------------------------------------
# Issue index (Stage 2 V-issues + website W-issues)
# --------------------------------------------------------------------------------------
V_ISSUES = C.read_csv(VR / "validation_issues.csv")
ISSUE = {r["issue_id"]: {"type": r["type"], "summary": r.get("summary", "")} for r in V_ISSUES}
for i in K.WEB_ISSUES:
    ISSUE[i["id"]] = {"type": i["type"], "summary": i["summary"]}
ISSUE.setdefault("M09", {"type": "missing_source", "summary": "CUE equation procedure not collected (CUE site inaccessible)."})


def warning_for(ids):
    out = []
    for i in ids:
        t = ISSUE.get(i, {}).get("type")
        if not t:
            FAIL.append(f"unknown issue id {i}")
            continue
        out.append(f"{i} ({t})")
    return "; ".join(out)


def page_ay(pid):
    return ACADEMIC_YEAR.get(pid, ("Not stated", ""))[0]


def trace(rid, cat, topic, info, pid, evidence, issues, section=""):
    m = PAGES[pid]
    return {
        "record_id": rid, "category_id": cat, "category_name": C.CATEGORY_NAMES[cat], "topic": topic,
        "information": info, "source_title": m.get("title", ""), "source_url": m["url"],
        "source_file": m.get("snapshot_file", ""), "page": "", "section": section,
        "date_collected": m.get("collected_at", ""), "publication_date": m.get("publication_date", ""),
        "academic_year": page_ay(pid), "source_type": m.get("source_type", "official"),
        "publisher": m.get("publisher", ""), "verification_status": "pending_verification", "review_status": "draft",
        "approval_status": "not_approved", "conflict_or_warning": warning_for(issues), "issue_ids": list(issues),
        "evidence_text": evidence, "last_checked": m.get("last_checked", ""),
    }


# --------------------------------------------------------------------------------------
# 1. Curated records with evidence checks
# --------------------------------------------------------------------------------------
records = defaultdict(list)  # relative output path -> rows


def add(path, row):
    records[path].append(row)


def build_curated():
    for rid, pid, office, dept, ctype, value, ev, iss in K.WEB_CONTACTS:
        C.check_evidence(pid, ev, FAIL, rid)
        C.check_evidence(pid, value if ctype != "extension" else value.replace("Ext. ", ""), FAIL, rid + ":value")
        r = trace(rid, "06", f"Contact: {office}", f"{office} — {ctype}: {value}", pid, ev, iss)
        r.update({"office_as_printed": office, "routing_department": dept,
                  "app_department": R.ROUTING[dept]["app_department"], "contact_type": ctype, "value_as_printed": value,
                  "verification_note": "Printed on an official USIU-Africa web page; not independently verified. "
                                       "Do not send test enquiries to this contact."})
        add("06_department_contacts_and_query_routing/official/web_department_contacts.csv", r)

    for rid, bank, name, cur, number, bcode, brcode, branch, swift, inter in K.WEB_BANKS:
        num = number.replace("Business number ", "")
        for q in (bank, num) + ((swift,) if swift else ()):
            C.check_evidence(W_P("feepay"), q, FAIL, rid)
        iss = ["V01", "V03"] + (["V02"] if "STANBIC" in bank else []) + (["W26"] if "ABSA" in bank else [])
        r = trace(rid, "04", f"Payment channel: {bank} ({cur})",
                  f"{bank}; account name '{name}'; {cur} {number}; bank code {bcode or 'not stated'}; branch code "
                  f"{brcode or 'not stated'}; branch {branch or 'not stated'}; SWIFT {swift or 'not stated'}"
                  + (f"; intermediary {inter}" if inter else ""), W_P("feepay"), num, iss)
        r.update({"channel_as_printed": bank, "account_name_as_printed": name, "currency": cur,
                  "account_or_paybill_as_printed": number, "bank_code": bcode, "branch_code": brcode,
                  "branch_as_printed": branch, "swift_code": swift, "intermediary_bank": inter,
                  "risk_level": "HIGH — payment details; never present as confirmed. Refer users to the Finance "
                                "Office (finance@usiu.ac.ke) to confirm before paying."})
        add("04_fees_and_payments/official/web_bank_and_mobile_payment_details.csv", r)

    simple = [
        (K.WEB_FEE_RULES, "04_fees_and_payments/official/web_fee_policy_rules.csv", "04"),
        (K.WEB_ADMISSION_RULES, "03_admissions_and_applications/official/web_admission_rules.csv", "03"),
        (K.WEB_TRANSFER, "07_academic_documents_results_and_verified_eligibility/official/web_transfer_credit_rules.csv", "07"),
    ]
    for rows, path, cat in simple:
        for rid, pid, topic, rule, iss in rows:
            C.check_evidence(pid, rule, FAIL, rid)
            r = trace(rid, cat, topic, rule, pid, rule, iss)
            if "W10" in iss:
                r["validity_note"] = "Time-limited content; the stated period has passed or differs from the current intake."
            add(path, r)

    for rid, pid, test, minimum, ev, iss in K.WEB_ENGLISH:
        C.check_evidence(pid, ev, FAIL, rid)
        r = trace(rid, "07", f"English proficiency: {test}", f"{test}: {minimum}", pid, ev, iss)
        r.update({"test_as_printed": test, "minimum_as_printed": minimum})
        add("07_academic_documents_results_and_verified_eligibility/official/web_english_proficiency_requirements.csv", r)

    for rid, pid, prog, kind, ev, iss in K.WEB_FINAID:
        C.check_evidence(pid, ev, FAIL, rid)
        r = trace(rid, "04", f"Financial aid: {prog}", f"{prog} ({kind}): {ev}", pid, ev, iss)
        r.update({"programme_as_printed": prog, "aid_type": kind,
                  "validity_note": ("Deadline passed before 2026-11-01: do not present as open."
                                    if "W10" in iss else "")})
        add("04_fees_and_payments/official/web_financial_aid_programmes.csv", r)

    for i in K.WEB_ISSUES:
        for pid, q in i["evidence"]:
            C.check_evidence(pid, q, FAIL, i["id"])
    for vid, (_st, ev, _n) in K.ISSUE_UPDATES.items():
        for pid, q in ev:
            C.check_evidence(pid, q, FAIL, vid)


def W_P(name):
    return {"feepay": K.P_FEEPAY}[name]


EXTERNAL = [
    ("EXT-KUCCPS-01", "kuccps.net__home", "03", "KUCCPS placement to private institutions (homepage)",
     "Currently, KUCCPS does not place students to the private colleges.", ["W24"]),
    ("EXT-KUCCPS-02", "kuccps.net__frequently-asked-questions", "03", "KUCCPS placement to private universities (FAQ)",
     "KUCCPS also places students to private universities.", ["W24"]),
    ("EXT-KUCCPS-03", "kuccps.net__Placem", "07", "KUCCPS minimum requirement for degree placement",
     "Degree: C+ and above", []),
    ("EXT-KUCCPS-04", "kuccps.net__frequently-asked-questions", "07", "KUCCPS placement basis",
     "The placement of students is based on KCSE examination grades only.", []),
]


def build_external():
    for rid, pid, cat, topic, ev, iss in EXTERNAL:
        C.check_evidence(pid, ev, FAIL, rid)
        r = trace(rid, cat, topic, ev, pid, ev, iss)
        r["external_label"] = ("EXTERNAL SOURCE (KUCCPS, a Kenyan government agency). This is not USIU-Africa policy "
                               "and must never be presented as such.")
        add(f"{C.CATEGORY_DIRS[cat]}/external/external_records.csv", r)


# --------------------------------------------------------------------------------------
# 2. Snapshot cleaning, sections and chunks
# --------------------------------------------------------------------------------------
HEAD = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
CUT = re.compile(r"^\s*(?:#+\s*)?(?:\*\*)?\s*(Links in main content|Other links in main content|Links:|Data issues and "
                 r"caveats|Naming inconsistency for your dataset|\(Footer|Image-only content|No visible-text|Items I did "
                 r"not fetch|Note: this page's main content|Notes:|Unsure or flagged|Bank names, account numbers and "
                 r"paybill numbers: NONE|Model-extracted summary|- Downloadable|Downloadable file)", re.I)
DROP_LINE = re.compile(r"^\s*(\+ Section 0 template|\(Table rebuilt|\(Heading present|\(Indentation of|!\[|\[image link|"
                       r"- [^\n]*->\s*(https?:|mailto:|tel:))|\[MISMATCH|\bI did not\b|content I received|"
                       r"The PDF itself was not fetched|^\s*Form fields", re.I)
META_LINE = re.compile(r"^\s*-\s*\**\s*(HTTP|Page title|Published|Final URL|H1|Date:|Opening hours|Read in full)", re.I)
MAIN = re.compile(r"^\s*(?:[-#]+\s*)?(?:\*\*)?Main content\b", re.I)


def clean_page(pid, text):
    text = re.sub(r"^<!--.*?-->\s*", "", text, flags=re.S)
    trunc = W.SNAPSHOT_TRUNCATE.get(pid)
    if trunc and trunc in text:
        text = text.split(trunc, 1)[0]
    lines = text.split("\n")
    start = 0
    for i, ln in enumerate(lines[:15]):
        if MAIN.search(ln):
            start = i + 1
            break
    else:
        while start < len(lines) and (META_LINE.match(lines[start]) or not lines[start].strip()):
            start += 1
    out = []
    for ln in lines[start:]:
        if CUT.match(ln):
            break
        if DROP_LINE.search(ln) or META_LINE.match(ln):
            continue
        out.append(re.sub(r"^\((?:Identical paragraph repeated[^)]*)\)\s*", "", ln))
    body = "\n".join(out)
    body = re.sub(r"^ {2}", "", body, flags=re.M)               # main-content indentation in some reports
    body = re.sub(r"^(.+)\n-{3,}\s*$", r"# \1", body, flags=re.M)  # setext headings
    body = C._LINK.sub(r"\1", body)
    body = re.sub(r"\n{3,}", "\n\n", body).strip()
    return body


PROG_LABEL = re.compile(r"^(?:-\s+)?\*{0,2}(H1|Overview[^:]*|Duration[^:]*|Intakes?(?:\(s\))?[^:]*|Mode of study[^:]*|"
                        r"School[^:]*|Entry[^:]*|Admission Requirements[^:]*|Accreditation[^:]*|Career[^:]*|"
                        r"Contact[^:]*|HTTP[^:]*|Note[^:]*|Program Delivery[^:]*|Pre-Requisite[^:]*|Link[^:]*|"
                        r"Form fields[^:]*)\*{0,2}:\*{0,2}\s*(.*)$")
AGENT_ONLY = re.compile(r"^(http|contact|note|link|form)", re.I)


def programme_fields(text):
    """Programme pages are field lists written by the fetching agent: [(label, [value lines])]."""
    out, cur = [], None
    for ln in re.sub(r"^<!--.*?-->\s*", "", text, flags=re.S).split("\n"):
        m = PROG_LABEL.match(ln)
        if m:
            cur = [m.group(1), [m.group(2)] if m.group(2).strip() else []]
            out.append(cur)
            continue
        if cur and ln.strip() and (ln[:1] in " \t" or re.match(r"^(\d+\.|-|\*)\s", ln)):
            cur[1].append(ln.strip())
        elif ln.strip():
            cur = None  # agent text outside a field
    return out


def programme_text(text):
    return "\n".join(re.sub(r"\s*\((?:verbatim|as stated|table flattened|complete)[^)]*\)", "", lab) + ": "
                     + "\n".join(v) for lab, v in programme_fields(text)
                     if not AGENT_ONLY.match(lab) and not lab.startswith("H1") and v)


def split_sections(body):
    sections, stack, buf = [], [], []

    def flush():
        txt = "\n".join(buf).strip()
        if txt:
            sections.append({"headings": [h for _, h in stack], "text": txt})
        buf.clear()

    for ln in body.split("\n"):
        m = HEAD.match(ln)
        if m:
            flush()
            lvl = len(m.group(1))
            stack[:] = [(l, h) for l, h in stack if l < lvl] + [(lvl, m.group(2).strip("* "))]
            continue
        buf.append(ln)
    flush()
    return sections


SENT = re.compile(r"(?<=[.!?;])\s+(?=[A-Z0-9(\"“‘*•●])")


def units_of(block, room):
    lines = block.split("\n")
    if len(block) <= room:
        return [block]
    if all(l.startswith("|") for l in lines) and len(lines) > 2:
        head, rows, out, cur = lines[:2], lines[2:], [], []
        for r in rows:
            if cur and len("\n".join(head + cur + [r])) > room:
                out.append("\n".join(head + cur))
                cur = []
            cur.append(r)
        out.append("\n".join(head + cur))
        return out
    if len(lines) > 1:
        out = []
        for l in lines:
            out.extend(units_of(l, room))
        return out
    return [s for s in SENT.split(block) if s]


def chunk_section(heading_line, text):
    prefix = heading_line + "\n\n" if heading_line else ""
    room = CHUNK_LIMIT - len(prefix)
    units = []
    for block in re.split(r"\n\s*\n", text):
        block = block.strip()
        if block:
            units.extend(units_of(block, room))
    chunks, cur = [], ""
    for u in units:
        cand = (cur + ("\n\n" if cur else "") + u)
        if cur and len(prefix + cand) > CHUNK_LIMIT:
            chunks.append(prefix + cur)
            cur = u
        else:
            cur = cand
    if cur:
        chunks.append(prefix + cur)
    return chunks


def build_chunks():
    sections_by_cat = defaultdict(list)
    chunks_by_cat = defaultdict(list)
    seen, dups, oversize = {}, [], []
    page_numbers = {pid: n for n, pid in enumerate(sorted(OK_PAGES), 1)}
    issue_quotes = [(i["id"], pid, q) for i in K.WEB_ISSUES for pid, q in i["evidence"]]
    for pid, m in sorted(OK_PAGES.items()):
        if pid == "wp-sitemap.xml":
            continue
        raw = C.snapshot(pid)
        is_prog = pid.startswith("programs__")
        body = programme_text(raw) if is_prog else clean_page(pid, raw)
        secs = [{"headings": [m["title"]], "text": body}] if is_prog else split_sections(body)
        cat = m["category_id"]
        origin = m["source_type"]
        for sn, s in enumerate(secs, 1):
            heads = s["headings"] or [m["title"]]
            sid = f"WEB-P{page_numbers[pid]:03d}-S{sn:02d}"
            heading_line = " > ".join(h for h in heads if h)
            if len(C.norm(s["text"])) < 25 and not re.search(r"\d", s["text"]):
                continue
            pieces = chunk_section(heading_line, s["text"])
            sec_issues = sorted({i for i, p, q in issue_quotes if p == pid and C.norm(q) in C.norm(s["text"])})
            sec = {"record_id": sid, "record_type": "web_document_section", "section_id": sid, "category_id": cat,
                   "category_name": C.CATEGORY_NAMES[cat], "data_origin": origin, "publisher": m.get("publisher", ""),
                   "document_id": pid, "document_title": m["title"], "source_url": m["url"],
                   "source_file": m["snapshot_file"], "publication_date": m["publication_date"],
                   "academic_year": page_ay(pid), "sitemap_lastmod": m.get("sitemap_lastmod", ""),
                   "collection_date": m["collected_at"], "last_checked": m["last_checked"], "page": None,
                   "section_heading": heads[-1], "heading_path": heads, "content": s["text"],
                   "content_chars": len(s["text"]), "chunk_count": 0, "content_fidelity": m["content_fidelity"],
                   "review_status": "draft", "verification_status": "pending_verification",
                   "approval_status": "not_approved", "issue_ids": sec_issues}
            kept = 0
            for ci, piece in enumerate(pieces, 1):
                h = C.sha256_text(C.norm(piece.split("\n\n", 1)[-1] if heading_line else piece))
                cid = f"{sid}-c{ci:02d}"
                if h in seen:
                    dups.append({"chunk_id": cid, "duplicate_of": seen[h], "source_url": m["url"],
                                 "content_start": piece[:120]})
                    continue
                seen[h] = cid
                if len(piece) > CHUNK_LIMIT:
                    oversize.append({"chunk_id": cid, "chars": len(piece), "reason": "single sentence or table row longer than the limit"})
                ch = {k: sec[k] for k in sec if k not in ("record_type", "content", "content_chars", "chunk_count")}
                ch.update({"record_id": cid, "record_type": "knowledge_chunk", "chunk_id": cid, "chunk_index": ci,
                           "chunk_count": len(pieces), "content": piece, "content_chars": len(piece),
                           "content_sha256": C.sha256_text(piece),
                           "issue_ids": sorted({i for i, p, q in issue_quotes if p == pid and C.norm(q) in C.norm(piece)}),
                           "flags": (["external_source_not_usiu_policy"] if origin == "external" else [])})
                chunks_by_cat[(cat, origin)].append(ch)
                kept += 1
            sec["chunk_count"] = kept
            sections_by_cat[(cat, origin)].append(sec)
    for (cat, origin), secs in sections_by_cat.items():
        folder = "official" if origin == "official" else "external"
        base = D / C.CATEGORY_DIRS[cat] / folder
        C.write_json(base / "web_document_sections.json", secs)
        C.write_json(base / "web_knowledge_chunks.json", chunks_by_cat[(cat, origin)])
        C.write_csv(base / "web_sections_index.csv", [
            {"record_id": s["record_id"], "document_id": s["document_id"], "data_origin": s["data_origin"],
             "source_url": s["source_url"],
             "section_heading": s["section_heading"], "heading_path": " > ".join(s["heading_path"]),
             "content_chars": s["content_chars"], "chunk_count": s["chunk_count"], "issue_ids": s["issue_ids"],
             "review_status": "draft", "verification_status": "pending_verification"} for s in secs])
    C.write_csv(VR / "web_duplicate_chunks.csv", dups, ["chunk_id", "duplicate_of", "source_url", "content_start"])
    return sections_by_cat, chunks_by_cat, dups, oversize


# --------------------------------------------------------------------------------------
# 3. Programme pages
# --------------------------------------------------------------------------------------
def unq(v):
    v = v.strip()
    if len(v) > 1 and v[0] in "\"“" and v.rstrip(".")[-1] in "\"”" and v.count('"') <= 2:
        v = v.strip("\"“”")
    return v


def build_programmes():
    n = 0
    for pid, m in sorted(OK_PAGES.items()):
        if not pid.startswith("programs__"):
            continue
        n += 1
        fields = {}
        for label, vals in programme_fields(C.snapshot(pid)):
            lab = label.lower()
            key = ("title" if lab.startswith("h1") else "school" if lab.startswith("school") else
                   "duration" if lab.startswith("duration") else "intake" if lab.startswith("intake") else
                   "mode" if lab.startswith("mode") else
                   "requirements" if (lab.startswith(("entry", "admission requirements"))) else
                   "accreditation" if lab.startswith("accreditation") else
                   "careers" if lab.startswith("career") else "overview" if lab.startswith("overview") else None)
            if key and (key not in fields or not fields[key]):
                fields[key] = vals
        f = {k: unq(" ".join(v)) if k != "requirements" else "\n".join(x.strip() for x in v if x.strip())
             for k, v in fields.items()}
        title = unq(f.get("title", m["title"]))
        level = ("doctoral" if re.match(r"Doctor", title, re.I) else
                 "masters" if re.match(r"(Master|MBA|MSc)", title, re.I) else
                 "undergraduate" if re.match(r"Bachelor", title, re.I) else "not stated")
        req = f.get("requirements", "")
        stated = bool(req) and not re.match(r"^\W*Not stated", req, re.I)
        iss = [i["id"] for i in K.WEB_ISSUES if any(p == pid for p, _ in i["evidence"])]
        if not stated and "W23" not in iss:
            iss.append("W23")
        if pid == "programs__master-of-business-administration-online" and "W22" not in iss:
            iss.append("W22")
        rid = f"PROG-WEB-{n:02d}"
        C.check_evidence(pid, title, FAIL, rid)
        r = trace(rid, "02", f"Programme: {title}",
                  f"{title} — {f.get('school', 'school not stated')}; duration {f.get('duration', 'not stated')}; "
                  f"{f.get('intake', 'intake not stated')}; mode {f.get('mode', 'not stated')}", pid, title, iss)
        r.update({"programme_title_as_printed": title, "level": level, "school_as_printed": f.get("school", ""),
                  "duration_as_printed": f.get("duration", ""), "intake_as_printed": f.get("intake", ""),
                  "mode_as_printed": f.get("mode", ""), "accreditation_as_printed": f.get("accreditation", ""),
                  "career_opportunities": f.get("careers", ""), "overview_first_paragraph": f.get("overview", ""),
                  "field_fidelity": "Field values were written by the fetching agent: quoted text is verbatim from the "
                                    "page; unquoted text (e.g. 'Not stated on page') is the agent's description."})
        add("02_academic_programmes/official/web_programmes.csv", r)
        r2 = trace(f"PREQ-WEB-{n:02d}", "07", f"Entry requirements: {title}",
                   req if stated else "Not stated on the programme page.", pid, title, iss)
        r2.update({"programme_title_as_printed": title, "level": level, "requirements_stated_on_page": "yes" if stated else "no",
                   "requirements_as_printed": req})
        add("07_academic_documents_results_and_verified_eligibility/official/programme_entry_requirements.csv", r2)
    return n


# --------------------------------------------------------------------------------------
# 4. Fee tables (tuition page) with arithmetic and PDF cross-checks
# --------------------------------------------------------------------------------------
AMT = re.compile(r"^(USD\s*)?[\d,]+\.\d{2}$")


def amount(s):
    s = s.strip().strip("*")
    if s in ("–", "-", "", "TBA"):
        return None
    if AMT.match(s):
        return float(s.replace("USD", "").replace(",", "").strip())
    return None


def fee_pdf_text():
    dl = W.DOWNLOADS[0]
    p = D / dl["file"]
    sha = C.sha256_file(p)
    if sha != dl["sha256"]:
        FAIL.append(f"fee schedule PDF hash changed: {sha}")
    from pypdf import PdfReader
    reader = PdfReader(str(p))
    pages = [(pg.extract_text() or "") for pg in reader.pages]
    out = D / "source_documents" / dl["document_id"]
    md = [f"# {dl['title']}\n", f"Source: {dl['url']}  \nLanding page: {dl['landing_page']}  \nSHA-256: {sha}  \n"
          f"Downloaded: {C.COLLECTED} (official USIU-Africa website). Text extracted with pypdf; table layout is "
          f"flattened. Review status: draft.\n"]
    for i, t in enumerate(pages, 1):
        md.append(f"\n## Page {i}\n\n{t.strip()}\n")
    out.mkdir(parents=True, exist_ok=True)
    (out / "extracted_text_by_page.md").write_text("".join(md), encoding="utf-8", newline="\n")
    C.write_json(out / "document_metadata.json", {
        "document_id": dl["document_id"], "title": dl["title"], "source_url": dl["url"],
        "landing_page": dl["landing_page"], "file": dl["file"], "sha256": sha, "bytes": p.stat().st_size,
        "pages": len(pages), "academic_year": dl["academic_year"],
        "publication_date": "Not stated in the document (states 'Effective September 1, 2026')",
        "pdf_metadata_note": dl["note"], "source_type": "official", "publisher": "USIU-Africa",
        "collected_at": C.COLLECTED, "review_status": "draft", "verification_status": "pending_verification",
        "approval_status": "not_approved"})
    return pages


def build_fees(pdf_pages):
    pdf_norm = C.norm(" ".join(pdf_pages))
    text = C.snapshot("tuition-fees")
    lines = text.split("\n")
    mode = level = school = ""
    progs, tables, i = [], [], 0
    while i < len(lines):
        ln = lines[i]
        m = HEAD.match(ln)
        if m:
            h, lvl = m.group(2).strip(), len(m.group(1))
            if re.match(r"0\d\.", h):
                mode = h
            elif re.search(r"\bcost\b", h, re.I):
                level, school = h, ""
            elif lvl in (3, 4) and " - " in h:
                school = h
            elif lvl == 6:
                if progs and progs[-1] == "__table__":
                    progs = []
                progs.append(h)
            i += 1
            continue
        if ln.startswith("|") and i + 1 < len(lines) and lines[i + 1].startswith("|---"):
            header = [c.strip() for c in ln.strip("|").split("|")]
            rows = []
            i += 2
            while i < len(lines) and lines[i].startswith("|"):
                rows.append([c.strip() for c in lines[i].strip("|").split("|")])
                i += 1
            tables.append({"mode": mode, "level": level, "school": school, "programmes": [p for p in progs if p != "__table__"],
                           "header": header, "rows": rows})
            progs.append("__table__")
            continue
        i += 1
    fee_rows, checks, other = [], [], []
    tno = 0
    for t in tables:
        name = " / ".join(t["programmes"])
        if t["header"][0].lower().startswith("kshs"):
            tno += 1
            tid = f"FEETAB-{tno:02d}"
            sums = [0.0] * (len(t["header"]) - 1)
            total = None
            for rn, row in enumerate(t["rows"], 1):
                vals = [amount(c) for c in row[1:]]
                if row[0].strip("* ").upper() == "TOTAL":
                    total = vals
                else:
                    sums = [s + (v or 0) for s, v in zip(sums, vals)]
                rid = f"{tid}-R{rn:02d}"
                ev = "| " + " | ".join(row) + " |"
                C.check_evidence("tuition-fees", ev, FAIL, rid)
                r = trace(rid, "04", f"Fee table: {name}", f"{name} — {row[0]}: " + "; ".join(
                    f"{h} {c}" for h, c in zip(t["header"][1:], row[1:])), "tuition-fees", ev, [])
                r.update({"table_id": tid, "mode_heading": t["mode"], "level_heading": t["level"],
                          "school_heading": t["school"], "programmes_as_printed": t["programmes"],
                          "fee_item_as_printed": row[0], "column_1_label": t["header"][1], "column_1_amount": row[1],
                          "column_2_label": t["header"][2] if len(t["header"]) > 2 else "",
                          "column_2_amount": row[2] if len(row) > 2 else "",
                          "column_3_label": t["header"][3] if len(t["header"]) > 3 else "",
                          "column_3_amount": row[3] if len(row) > 3 else "", "currency": "KES",
                          "period": "per semester (table header 'Kshs (PER SEMESTER)')"})
                fee_rows.append(r)
            arith = total is not None and all(abs(s - (tv or 0)) < 0.005 for s, tv in zip(sums, total))
            total_row = next((r for r in t["rows"] if r[0].strip("* ").upper() == "TOTAL"), None)
            in_pdf = bool(total_row) and C.norm("TOTAL " + " ".join(total_row[1:])) in pdf_norm
            checks.append({"table_id": tid, "programmes": name, "mode_heading": t["mode"], "level_heading": t["level"],
                           "item_rows": len(t["rows"]) - (1 if total_row else 0),
                           "computed_sums": "; ".join(f"{s:,.2f}" for s in sums),
                           "printed_total": "; ".join(total_row[1:]) if total_row else "",
                           "arithmetic_check": "pass" if arith else "FAIL",
                           "total_row_found_in_fee_schedule_pdf": "yes" if in_pdf else "no",
                           "note": ("" if in_pdf else "The 2026-2027 fee schedule PDF covers on-campus programmes; online "
                                    "programme tables are in a separate 'Online Programs Fee Schedule' that was not "
                                    "collected." if "Online" in t["mode"] else "TOTAL line not found in PDF text")})
        else:
            for rn, row in enumerate(t["rows"], 1):
                if all(not c.strip() for c in row[1:]):
                    continue
                rid = f"FEEOTH-{len(other) + 1:02d}"
                ev = "| " + " | ".join(row) + " |"
                C.check_evidence("tuition-fees", ev, FAIL, rid)
                r = trace(rid, "04", f"{name}: {row[0].strip('* ')}", f"{row[0].strip('* ')}: " + "; ".join(
                    f"{h} {c}" for h, c in zip(t["header"][1:], row[1:])), "tuition-fees", ev,
                    ["W13"] if "Room Only" in row[0] else ["W21"] if "Technology Fee" in row[0] else [])
                r.update({"table_as_printed": name, "fee_item_as_printed": row[0].strip("* "),
                          "amounts_as_printed": "; ".join(f"{h}: {c}" for h, c in zip(t["header"][1:], row[1:]))})
                other.append(r)
    for r in fee_rows:
        add("04_fees_and_payments/official/web_tuition_fee_tables.csv", r)
    for r in other:
        add("04_fees_and_payments/official/web_other_and_general_charges.csv", r)
    C.write_csv(VR / "fee_table_checks.csv", checks)
    return tno, len(fee_rows), len(other), checks


# --------------------------------------------------------------------------------------
# 5. Bank comparison across the three official sources
# --------------------------------------------------------------------------------------
def bank_key(name):
    n = name.upper()
    for k, pat in (("NCBA / Commercial Bank of Africa", "NCBA|COMMERCIAL BANK OF AFRICA"), ("Co-operative Bank", "CO-?OP"),
                   ("Standard Chartered", "STANDARD CHARTERED"), ("KCB", "KENYA COMMERCIAL|KCB"),
                   ("Absa", "ABSA"), ("Stanbic", "STANBIC"), ("M-PESA paybill", "M-PESA|MPESA")):
        if re.search(pat, n):
            return k
    return name


def build_bank_comparison():
    stage2 = C.read_csv(D / "04_fees_and_payments/official/bank_and_mobile_payment_details.csv")
    web = records["04_fees_and_payments/official/web_bank_and_mobile_payment_details.csv"]
    table = defaultdict(lambda: {"website": [], "calendar_2026_2027": [], "student_handbook": []})

    def cur(c):
        return "USD" if "USD" in c else "KES" if "KES" in c else "Not stated"
    for r in stage2:
        src = "calendar_2026_2027" if "-CAL-" in r["record_id"] else "student_handbook"
        num = re.sub(r"\D", "", r["account_or_paybill_as_printed"])
        table[(bank_key(r["channel_as_printed"]), num)][src].append(
            f"{r['record_id']}: {r['channel_as_printed']}; {r['branch_as_printed']}; {r['currency']}; "
            f"{r['account_name_as_printed']}; {r['codes_as_printed'] or 'no codes printed'}")
    for r in web:
        num = re.sub(r"\D", "", r["account_or_paybill_as_printed"])
        table[(bank_key(r["channel_as_printed"]), num)]["website"].append(
            f"{r['record_id']}: {r['channel_as_printed']}; {r['branch_as_printed']}; {r['currency']}; "
            f"{r['account_name_as_printed']}; bank code {r['bank_code'] or '-'}, branch code {r['branch_code'] or '-'}, "
            f"SWIFT {r['swift_code'] or '-'}")
    rows = []
    for n, ((bank, num), v) in enumerate(sorted(table.items()), 1):
        present = [k for k in v if v[k]]
        rows.append({"comparison_id": f"BANKCMP-{n:02d}", "bank": bank, "account_or_paybill_number": num,
                     "on_website_fee_payment_page": " | ".join(v["website"]) or "NOT LISTED",
                     "in_academic_calendar_2026_2027": " | ".join(v["calendar_2026_2027"]) or "NOT LISTED",
                     "in_student_handbook_undated": " | ".join(v["student_handbook"]) or "NOT LISTED",
                     "listed_in": f"{len(present)} of 3 sources",
                     "status": "UNCONFIRMED — refer users to the Finance Office (finance@usiu.ac.ke) before paying",
                     "issue_ids": "V01; V02; V03; W26"})
    C.write_csv(D / "04_fees_and_payments/official/bank_details_comparison.csv", rows)
    return rows


# --------------------------------------------------------------------------------------
# 6. Official FAQ pairs and category 08 registers
# --------------------------------------------------------------------------------------
def build_faq():
    n = 0
    for pid, m in sorted(OK_PAGES.items()):
        if m["source_type"] != "official" or pid == "wp-sitemap.xml":
            continue
        body = programme_text(C.snapshot(pid)) if pid.startswith("programs__") else clean_page(pid, C.snapshot(pid))
        for s in split_sections(body):
            q = s["headings"][-1] if s["headings"] else ""
            if not re.match(r"^\d+\.\s+.*\?$", q):
                continue
            n += 1
            question = re.sub(r"^\d+\.\s+", "", q)
            ans = s["text"].strip()
            C.check_evidence(pid, question, FAIL, f"FAQ-WEB-{n:03d}")
            iss = [i["id"] for i in K.WEB_ISSUES if any(p == pid and C.norm(qq) in C.norm(ans) for p, qq in i["evidence"])]
            r = trace(f"FAQ-WEB-{n:03d}", "08", f"Official FAQ: {question}", ans, pid, question, iss,
                      section=" > ".join(s["headings"][:-1]))
            r.update({"question_as_published": question, "answer_as_published": ans,
                      "record_origin": "Official FAQ published by USIU-Africa (not a student enquiry)"})
            add("08_questions_answers_and_unresolved_enquiries/official/official_faq_pairs.csv", r)
    return n


def build_registers(v_rows):
    rows = []
    for qid, q, ids, dept, say in R.OPEN_QUESTIONS:
        rows.append({"record_id": qid, "category_id": "08", "category_name": C.CATEGORY_NAMES["08"],
                     "topic": "Open question derived from the dataset", "information": q, "question": q,
                     "linked_issue_or_gap": ids, "route_to": dept, "app_department": R.ROUTING[dept]["app_department"],
                     "interim_safe_response_guidance": say,
                     "record_origin": "Derived from conflicts and gaps in this dataset — NOT a real student enquiry; "
                                      "no enquiry was sent to any department",
                     "source_type": "derived", "source_url": "", "source_file": "validation_reports/"
                     "conflict_and_verification_register.csv", "date_collected": C.COLLECTED,
                     "publication_date": "Not applicable", "verification_status": "unresolved",
                     "review_status": "draft", "approval_status": "not_approved", "last_checked": C.COLLECTED})
    C.write_csv(D / "08_questions_answers_and_unresolved_enquiries/official/open_questions_register.csv", rows)

    miss = [{"gap_id": f"GAP-{n:02d}", "category_id": c, "information_required": info, "status": st,
             "where_found_or_why_missing": where, "action_type": at, "action_needed": act}
            for n, (c, info, st, where, at, act) in enumerate(R.MISSING, 1)]
    miss.append({"gap_id": f"GAP-{len(miss) + 1:02d}", "category_id": "04",
                 "information_required": "Online programmes fee schedule document", "status": "Not collected",
                 "where_found_or_why_missing": "Linked from the Tuition & Fees page "
                 "(https://www.usiu.ac.ke/documents/online-programs-fee-structure/); not fetched in this run.",
                 "action_type": R.TW, "action_needed": "Fetch the document page and its PDF; cross-check online fee tables."})
    C.write_csv(VR / "missing_information_register.csv", miss)

    reg = []
    for v in v_rows:
        st, ev, note = K.ISSUE_UPDATES.get(v["issue_id"], ("open", [], "No new evidence found in the website pages collected."))
        reg.append({"issue_id": v["issue_id"], "origin": "Stage 2 PDF extraction", "type": v["type"],
                    "severity": v["severity"], "requires_admin_decision": v.get("requires_admin_decision", ""),
                    "summary": v.get("summary", ""), "evidence_versions": v.get("evidence", ""),
                    "website_evidence": " | ".join(f"{PAGES[p]['url']}: \"{q}\"" for p, q in ev),
                    "status": st, "status_note": note, "action": v.get("recommended_action", v.get("action", "")),
                    "last_checked": C.COLLECTED})
    for i in K.WEB_ISSUES:
        reg.append({"issue_id": i["id"], "origin": "Website collection 2026-11-01", "type": i["type"],
                    "severity": i["severity"], "requires_admin_decision": "yes" if i["admin_decision"] else "no",
                    "summary": i["summary"], "evidence_versions": "",
                    "website_evidence": " | ".join(f"{PAGES[p]['url']}: \"{q}\"" for p, q in i["evidence"]),
                    "status": "open", "status_note": "", "action": i["action"], "last_checked": C.COLLECTED})
    C.write_csv(VR / "conflict_and_verification_register.csv", reg)
    return rows, miss, reg


# --------------------------------------------------------------------------------------
# 7. Routing, source register, layout verification
# --------------------------------------------------------------------------------------
def build_routing():
    stage2 = C.read_csv(D / "06_department_contacts_and_query_routing/official/department_contacts.csv")
    web = records["06_department_contacts_and_query_routing/official/web_department_contacts.csv"]
    out = {}
    for dept, d in R.ROUTING.items():
        ref = E.ROUTING_REFERENCE.get(dept, {})
        out[dept] = {
            "label": d["label"], "usiubot_app_department": d["app_department"], "app_gap_note": d.get("app_gap", ""),
            "responsibilities_from_handbook": [{"document_id": doc, "page": pg, "section": sec, "quote": q}
                                               for doc, pg, sec, q in ref.get("responsibilities", [])],
            "contacts_web": [f"{r['record_id']}: {r['office_as_printed']} — {r['contact_type']} {r['value_as_printed']}"
                             + (f" [{r['conflict_or_warning']}]" if r["conflict_or_warning"] else "")
                             for r in web if r["routing_department"] == dept],
            "contacts_pdf": [f"{r['record_id']}: {r['office_as_printed']} — {r['contact_type']} {r['value_as_printed']}"
                             for r in stage2 if r["maps_to_usiubot_enquiry_department"] == dept],
            "keywords_processing_aid": d["keywords"],
            "keywords_note": "Keywords are a processing aid written for USIUBOT, not university text.",
            "contact_status": "As printed on official sources; unverified. Do not send test enquiries.",
        }
    C.write_json(D / "06_department_contacts_and_query_routing/official/routing_departments.json", out)
    return out


def build_source_register(rec_counts):
    rows = []
    for doc_id, d in E.DOCUMENTS.items():
        rows.append({"source_id": doc_id, "title": d["title"], "source_type": "official", "publisher": "USIU-Africa",
                     "format": "PDF (local copy)", "url": d["source_url"] or "", "file": d["file"],
                     "access_outcome": d["source_url_status"], "http_status": "", "collected_at": "2026-11-01",
                     "last_checked": C.COLLECTED, "publication_date": d["publication_date"],
                     "academic_year": d["academic_year"], "sitemap_lastmod": "",
                     "sha256": _pdf_hash(d["file"]), "content_fidelity": "PDF text layer (pypdf)",
                     "records_derived": rec_counts.get(doc_id, 0)})
    for dl in W.DOWNLOADS:
        if dl["file"]:
            rows.append({"source_id": dl["document_id"], "title": dl["title"], "source_type": "official",
                         "publisher": "USIU-Africa", "format": "PDF (downloaded)", "url": dl["url"], "file": dl["file"],
                         "access_outcome": "downloaded HTTP 200", "http_status": 200, "collected_at": C.COLLECTED,
                         "last_checked": C.COLLECTED, "publication_date": "Not stated in the document",
                         "academic_year": dl["academic_year"], "sitemap_lastmod": "", "sha256": dl["sha256"],
                         "content_fidelity": "PDF text layer (pypdf); used for cross-checks",
                         "records_derived": rec_counts.get(dl["document_id"], 0)})
    for pid, m in sorted(PAGES.items()):
        rows.append({"source_id": pid, "title": m.get("title", ""), "source_type": m.get("source_type", ""),
                     "publisher": m.get("publisher", ""), "format": "web page",
                     "url": m["url"], "file": m.get("snapshot_file", ""),
                     "access_outcome": m.get("access_outcome", "collected HTTP 200"),
                     "http_status": m.get("http_status") or "", "collected_at": m.get("collected_at", ""),
                     "last_checked": m.get("last_checked", ""), "publication_date": m.get("publication_date", "Publication date not stated"),
                     "academic_year": page_ay(pid), "sitemap_lastmod": m.get("sitemap_lastmod", ""),
                     "sha256": m.get("snapshot_sha256", ""), "content_fidelity": m.get("content_fidelity", ""),
                     "records_derived": rec_counts.get(pid, 0)})
    C.write_csv(VR / "source_register.csv", rows)
    return rows


def _pdf_hash(name):
    return C.sha256_file(C.PROJECT / name)


def build_layout_verification():
    from pypdf import PdfReader
    page = PdfReader(str(C.PROJECT / "Student-Handbook.pdf")).pages[6]
    pieces = []
    page.extract_text(visitor_text=lambda t, cm, tm, fd, fs: pieces.append((t.strip(), round(tm[4]), round(tm[5])))
                      if t.strip() else None)
    want = ["OUR VISION", "To be a premier", "OUR MISSION", "Promote", "CORE VALUES", "OUR SCHOOLS", "Chandaria"]
    found = {}
    for w in want:
        for t, x, y in pieces:
            if t.startswith(w) and w not in found:
                found[w] = {"text_start": t[:60], "x": x, "y": y}
    pairs = [("OUR VISION", "To be a premier"), ("OUR MISSION", "Promote"), ("OUR SCHOOLS", "Chandaria")]
    checks = []
    for h, b in pairs:
        if h in found and b in found:
            ok = found[h]["y"] > found[b]["y"] and abs(found[h]["x"] - found[b]["x"]) < 60
            checks.append({"heading": h, "block": b, "heading_xy": [found[h]["x"], found[h]["y"]],
                           "block_xy": [found[b]["x"], found[b]["y"]],
                           "result": "heading directly above block" if ok else "CHECK"})
        else:
            checks.append({"heading": h, "block": b, "result": "text not found"})
    C.write_json(VR / "layout_verification.json", {
        "document": "Student-Handbook.pdf", "page": 7, "method": "pypdf text-matrix positions (PDF points, origin "
        "bottom-left; larger y = higher on the page). No rendering tool is installed, so positions are used instead "
        "of an image.", "positions": found, "checks": checks, "issue": "V24", "checked_at": C.COLLECTED})
    return checks


# --------------------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------------------
def main():
    build_curated()
    build_external()
    n_prog = build_programmes()
    pdf_pages = fee_pdf_text()
    n_tables, n_fee_rows, n_other, checks = build_fees(pdf_pages)
    n_faq = build_faq()
    if FAIL:
        print("EVIDENCE / INPUT CHECKS FAILED:")
        for f in FAIL:
            print("  " + f)
        sys.exit(1)
    for path, rows in records.items():
        C.write_csv(D / path, rows)
    banks = build_bank_comparison()
    secs, chunks, dups, oversize = build_chunks()
    open_q, miss, reg = build_registers(V_ISSUES)
    routing = build_routing()
    layout = build_layout_verification()
    by_page = Counter()
    for f in D.glob("0*/official/*.csv"):
        for r in C.read_csv(f):
            if r.get("document_id"):
                by_page[r["document_id"]] += 1
    for rows in records.values():
        for r in rows:
            for pid, m in PAGES.items():
                if m["url"] == r["source_url"]:
                    by_page[pid] += 1
                    break
    src = build_source_register(by_page)
    stats = {
        "web_pages_collected": len(OK_PAGES),
        "web_pages_official": sum(1 for m in OK_PAGES.values() if m["source_type"] == "official"),
        "web_pages_external": sum(1 for m in OK_PAGES.values() if m["source_type"] == "external"),
        "sources_not_collected": len(PAGES) - len(OK_PAGES),
        "fetch_attempts": len(MANIFEST["fetch_attempts"]),
        "fetch_attempts_failed": sum(1 for a in MANIFEST["fetch_attempts"] if a["outcome"] == "failed"),
        "web_record_files": {p: len(r) for p, r in sorted(records.items())},
        "web_records_total": sum(len(r) for r in records.values()),
        "web_sections": {f"{c}/{o}": len(v) for (c, o), v in sorted(secs.items())},
        "web_sections_total": sum(len(v) for v in secs.values()),
        "web_chunks": {f"{c}/{o}": len(v) for (c, o), v in sorted(chunks.items())},
        "web_chunks_total": sum(len(v) for v in chunks.values()),
        "web_duplicate_chunks_removed": len(dups),
        "web_oversize_chunks": oversize,
        "programme_pages": n_prog, "fee_tables": n_tables, "fee_table_rows": n_fee_rows,
        "fee_tables_arithmetic_pass": sum(1 for c in checks if c["arithmetic_check"] == "pass"),
        "fee_tables_total_found_in_pdf": sum(1 for c in checks if c["total_row_found_in_fee_schedule_pdf"] == "yes"),
        "other_and_general_charge_rows": n_other, "official_faq_pairs": n_faq,
        "open_questions": len(open_q), "missing_information_items": len(miss),
        "register_issues_total": len(reg),
        "register_issue_status": dict(Counter(r["status"] for r in reg)),
        "bank_comparison_rows": len(banks), "routing_departments": len(routing),
        "layout_checks": [c["result"] for c in layout], "source_register_rows": len(src),
    }
    import web_reports as REP
    index_rows = REP.all_records_index()
    cc = REP.chunk_counts()
    stats["all_records_index_rows"] = len(index_rows)
    stats["all_records_by_category"] = dict(sorted(Counter(r["category_id"] for r in index_rows).items()))
    stats["all_records_by_source_type"] = dict(Counter(r["source_type"] for r in index_rows))
    stats["sections_and_chunks_by_category"] = {k: cc[k] for k in sorted(cc)}
    REP.write_collection_report(stats, MANIFEST)
    REP.update_category_readmes(cc)
    REP.write_top_readme(stats, index_rows, cc)
    C.write_json(VR / "web_build_statistics.json", stats)
    print(json.dumps({k: v for k, v in stats.items() if not isinstance(v, (dict, list))}, indent=1))


if __name__ == "__main__":
    main()
