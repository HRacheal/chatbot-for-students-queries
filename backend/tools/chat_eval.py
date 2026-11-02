"""End-to-end evaluation of USIUBOT against the configured (persistent) MongoDB database.

    python -m tools.chat_eval                      # every case in tools/chat_eval_set.json
    python -m tools.chat_eval --ids R1,F3 --label after
    python -m tools.chat_eval --retrieval-only     # no language model calls

Runs the real chat pipeline (ChatService.process_query: preprocessing, BM25 retrieval, ranking,
the Groq model, citation checks, routing and fallback) on the database named in backend/.env.

READ-ONLY. The database is wrapped in a proxy that only allows reads: any insert, update,
delete or index call raises immediately, and unanswered-question logging is replaced by a
stub. Nothing is written to MongoDB. Results are written to a local JSON + Markdown report.

The expected answers in chat_eval_set.json were taken from the approved sources in the
database (see each case's "basis"); they are checked as required facts (regular expressions),
expected sources (title patterns), the expected outcome and the routing department.
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_SET = os.path.join(HERE, "chat_eval_set.json")
READ_METHODS = {"find", "find_one", "count_documents", "estimated_document_count", "aggregate", "distinct",
                "list_indexes", "index_information", "name", "full_name", "database", "with_options"}


class ReadOnlyError(RuntimeError):
    pass


class ReadOnlyCollection:
    def __init__(self, collection):
        self._c = collection

    def __getattr__(self, name):
        if name in READ_METHODS:
            return getattr(self._c, name)
        raise ReadOnlyError(f"chat_eval is read-only: '{name}' on '{self._c.name}' is not allowed")


class NoOpQueryLog:
    def __init__(self):
        self.logged = []

    def create_query(self, question, user_id=None, answered=False, scope="usiu", department=None):
        self.logged.append({"question": question, "scope": scope, "department": department})
        return "eval-not-stored"


class NoOpChatHistory:
    def create_chat(self, *args, **kwargs):
        return None


def build_service(db):
    """The production ChatService wiring (see app.py), on a read-only view of ``db``."""
    from config.config import Config
    from services.chat_service import ChatService
    from services.department_routing import DepartmentRouting
    from services.live_retrieval import DEFAULT_CATALOGUE, LiveRetriever
    from services.official_links import ManagedCatalogue
    from services.sources import SourceRegistry
    from services.web_access import WebsiteAccess

    settings = {k: getattr(Config, k) for k in dir(Config) if k.isupper()}

    def getter(name):
        return ReadOnlyCollection(db[name])

    registry = SourceRegistry(getter, settings)
    website = WebsiteAccess(settings)
    catalogue = ManagedCatalogue(getter, settings.get("OFFICIAL_PAGES_FILE") or DEFAULT_CATALOGUE, website.is_trusted)
    live = LiveRetriever(settings, website, catalogue)
    routing = DepartmentRouting(getter, settings)
    service = ChatService.__new__(ChatService)
    # Same attributes as ChatService.__init__, minus the database-backed models.
    service.registry, service.settings, service.live_retriever = registry, settings, live
    service.catalogue, service.routing = catalogue, routing
    service.staff_reply_email_available = lambda: False
    service.allowed_domains = tuple(settings.get("ALLOWED_SOURCE_DOMAINS", ("usiu.ac.ke",)))
    service.query_model, service.chat_history_model = NoOpQueryLog(), NoOpChatHistory()
    import threading
    service._memories, service._last_active, service._lock = {}, {}, threading.Lock()
    return service, settings


def check_case(case, body, retrieved, routed):
    answer = body.get("answer") or ""
    status = body.get("status")
    cited = [c.get("title", "") for c in body.get("citations") or []]
    retrieved_titles = [r["source"]["title"] for r in retrieved]
    expect = case["expect"]
    partial = bool(body.get("partial"))
    outcome = ("out_of_scope" if status == "out_of_scope" else "unanswered" if status == "unanswered"
               else "partial" if status == "answered" and partial else "answer" if status == "answered" else status)
    allowed = {"answer": {"answer"}, "partial": {"partial", "answer"}, "answer_or_partial": {"answer", "partial"},
               "unanswered": {"unanswered", "partial"}, "out_of_scope": {"out_of_scope", "unanswered"},
               "partial_or_unanswered": {"partial", "unanswered"}}[expect]
    facts = case.get("facts") or []
    # Models write non-breaking spaces and hyphens; match the facts on plain ones.
    plain = re.sub(r"[\u00a0\u2007\u2009\u202f]", " ", re.sub(r"[\u2010-\u2013]", "-", answer))
    missing = [f for f in facts if not re.search(f, plain, re.IGNORECASE)]
    sources = case.get("sources") or []
    src_retrieved = (not sources) or any(re.search(p, t, re.IGNORECASE) for p in sources for t in retrieved_titles)
    src_cited = (not sources) or any(re.search(p, t, re.IGNORECASE) for p in sources for t in cited)
    # Citation validity: every [n] in the answer refers to a returned citation number.
    numbers = {c["number"] for c in body.get("citations") or []}
    markers = {int(n) for n in re.findall(r"\[(\d{1,2})\]", answer)}
    citations_valid = status != "answered" or (bool(numbers) and markers <= numbers and bool(markers))
    forbidden = [f for f in case.get("forbidden") or [] if re.search(f, answer, re.IGNORECASE)]
    from services.chat_service import uncited_statements
    uncited = uncited_statements(answer) if status == "answered" else []
    routing_ok = (not case.get("dept")) or routed in case["dept"]
    refused = expect in ("answer", "answer_or_partial", "partial") and outcome in ("unanswered", "out_of_scope")
    warn = case.get("warn")
    warn_types = [w.get("type") for w in body.get("warnings") or []]
    warn_ok = (not warn) or status != "answered" or any(warn in t for t in warn_types)
    outcome_ok = outcome in allowed
    answered = outcome in ("answer", "partial")
    # Two or more substantial statements without a citation suggest content not taken from the sources.
    correct = outcome_ok and not forbidden and (not answered or (not missing and src_cited and len(uncited) < 2))
    return {
        "id": case["id"], "category": case["category"], "type": case["type"], "question": case["question"],
        "expected_basis": case.get("basis", ""), "expected_outcome": expect, "outcome": outcome, "status": status,
        "answer": answer, "expected_sources": sources, "retrieved": retrieved_titles, "cited": cited,
        "places_to_look": [p["title"] for p in body.get("places_to_look") or []],
        "site_search": bool(body.get("site_search_url")), "warnings": warn_types,
        "missing_facts": missing, "forbidden_found": forbidden, "uncited_statements": uncited, "source_retrieved": src_retrieved,
        "source_cited": src_cited, "citations_valid": citations_valid, "routed": routed,
        "expected_dept": case.get("dept"), "routing_ok": routing_ok, "unnecessary_refusal": refused,
        "warning_ok": warn_ok, "outcome_ok": outcome_ok, "correct": correct,
    }


def run_case(service, case, delay, retries=3):
    from services.routing import classify_department

    captured = []
    original = service.registry.retrieve

    def spy(*args, **kwargs):
        result = original(*args, **kwargs)
        captured.append(result)
        return result

    service.registry.retrieve = spy
    try:
        session = None
        for turn in case.get("history") or []:  # earlier turns of a follow-up conversation
            for attempt in range(retries + 1):
                body, _ = service.process_query(turn, session)
                if body.get("status") != "ai_unavailable":
                    break
                time.sleep(delay * 3)
            session = body["session_id"]
            time.sleep(delay)
        captured.clear()
        for attempt in range(retries + 1):
            captured.clear()
            body, _ = service.process_query(case["question"], session)
            if body.get("status") != "ai_unavailable":
                break
            print(f"   {case['id']}: AI unavailable ({body.get('error_type')}), retrying", flush=True)
            time.sleep(delay * 3)
    finally:
        service.registry.retrieve = original
    retrieved = captured[-1] if captured and captured[-1] else []
    from services.sources import tokenize
    question = case["question"]
    if case.get("history") and len(tokenize(question)) < 4:  # as in ChatService.process_query
        question = case["history"][-1] + " " + question
    # The department the application itself chose (newer versions return it); else the keyword routing.
    routed = body.get("department") if "department" in body else classify_department(question)[0]
    return body, retrieved, routed


def retrieval_only(service, case):
    from services.routing import classify_department
    from services.sources import tokenize

    s = service.settings
    text = case["question"]
    if case.get("history") and len(tokenize(text)) < 4:
        text = f"{case['history'][-1]} {text}"
    text = service._correct_spelling(text) if hasattr(service, "_correct_spelling") else text
    results = service.registry.retrieve(text, prefer_department=classify_department(text)[0],
                                        k=s.get("SOURCE_CONTEXT_COUNT", 6), min_score=s.get("RETRIEVAL_MIN_SCORE", 0.5),
                                        min_coverage=s.get("RETRIEVAL_MIN_COVERAGE", 0.5))
    titles = [r["source"]["title"] for r in results]
    routed = classify_department(text, hints=[r["source"].get("department") for r in results])[0]
    sources = case.get("sources") or []
    hit = (not sources) or any(re.search(p, t, re.IGNORECASE) for p in sources for t in titles)
    first = next((i for i, t in enumerate(titles, 1) if any(re.search(p, t, re.IGNORECASE) for p in sources)), None)
    return {"id": case["id"], "category": case["category"], "question": case["question"], "retrieved": titles,
            "expected_sources": sources, "source_retrieved": hit, "rank": first,
            "routed": routed, "expected_dept": case.get("dept"),
            "routing_ok": (not case.get("dept")) or routed in case["dept"]}


def markdown(results, label, meta):
    lines = [f"# USIUBOT evaluation: {label}", "", f"Run: {meta['run_at']} | database: `{meta['db']}` | "
             f"model: `{meta['model']}` | cases: {len(results)}", ""]
    by_cat = {}
    for r in results:
        by_cat.setdefault(r["category"], []).append(r)
    lines += ["| Category | Cases | Correct | Expected source retrieved | Routing OK | Unnecessary refusals |",
              "|---|---|---|---|---|---|"]
    for cat, rs in sorted(by_cat.items()):
        lines.append(f"| {cat} | {len(rs)} | {sum(r['correct'] for r in rs)} | {sum(r['source_retrieved'] for r in rs)} | "
                     f"{sum(r['routing_ok'] for r in rs)} | {sum(r['unnecessary_refusal'] for r in rs)} |")
    t = len(results)
    lines.append(f"| **All** | {t} | {sum(r['correct'] for r in results)} | {sum(r['source_retrieved'] for r in results)} | "
                 f"{sum(r['routing_ok'] for r in results)} | {sum(r['unnecessary_refusal'] for r in results)} |")
    lines += ["", "## Cases", ""]
    for r in results:
        mark = "PASS" if r["correct"] else "FAIL"
        lines += [f"### {r['id']} [{mark}] {r['category']} / {r['type']}", "", f"**Q:** {r['question']}", "",
                  f"**Expected ({r['expected_outcome']}):** {r['expected_basis']}", "",
                  f"**Outcome:** {r['outcome']} | routed: {r['routed']} (expected {r['expected_dept']}) | "
                  f"citations valid: {r['citations_valid']} | warnings: {', '.join(r['warnings']) or 'none'}", "",
                  f"**Expected sources:** {', '.join(r['expected_sources']) or '-'} | retrieved: {r['source_retrieved']} "
                  f"| cited: {r['source_cited']}", "",
                  "**Retrieved:** " + "; ".join(r["retrieved"]) if r["retrieved"] else "**Retrieved:** none", "",
                  "**Cited:** " + ("; ".join(r["cited"]) or "none"), ""]
        if r["missing_facts"]:
            lines += [f"**Missing facts:** {r['missing_facts']}", ""]
        if r.get("uncited_statements"):
            lines += [f"**Statements without a citation:** {r['uncited_statements']}", ""]
        if r["forbidden_found"]:
            lines += [f"**Forbidden content found:** {r['forbidden_found']}", ""]
        if r["places_to_look"]:
            lines += [f"**Official pages suggested:** {'; '.join(r['places_to_look'])}", ""]
        lines += ["**Answer:**", "", "> " + r["answer"].replace("\n", "\n> "), ""]
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--set", default=DEFAULT_SET)
    parser.add_argument("--ids", help="comma-separated case ids")
    parser.add_argument("--label", default="run")
    parser.add_argument("--out", default=os.path.join(HERE, "..", "..", "usiubot_datasets", "validation_reports"))
    parser.add_argument("--delay", type=float, default=float(os.getenv("CHAT_EVAL_DELAY", "20")),
                        help="seconds between model calls (Groq free tier: 8000 tokens/minute)")
    parser.add_argument("--retrieval-only", action="store_true")
    parser.add_argument("--resume", action="store_true", help="skip cases already saved under this --label")
    args = parser.parse_args(argv)

    from dotenv import load_dotenv
    load_dotenv(os.path.join(HERE, "..", ".env"))
    from pymongo import MongoClient

    uri, name = os.environ.get("MONGO_URI"), os.environ.get("MONGO_DB_NAME")
    if not uri or not name:
        sys.exit("MONGO_URI and MONGO_DB_NAME must be set in backend/.env")
    db = MongoClient(uri, serverSelectionTimeoutMS=20000)[name]
    service, settings = build_service(db)
    cases = json.load(open(args.set, encoding="utf-8"))["cases"]
    if args.ids:
        wanted = set(args.ids.split(","))
        cases = [c for c in cases if c["id"] in wanted]
    os.makedirs(args.out, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%MZ")
    meta = {"run_at": stamp, "db": name, "model": settings.get("GROQ_MODEL") or "openai/gpt-oss-120b"}

    if args.retrieval_only:
        results = [retrieval_only(service, c) for c in cases]
        ok = sum(r["source_retrieved"] for r in results)
        for r in results:
            print(f"{r['id']:5} src={'Y' if r['source_retrieved'] else 'N'} rank={r['rank']} route={r['routed']}"
                  f"{'' if r['routing_ok'] else ' (WRONG)'} | {r['question'][:70]}")
        print(f"expected source retrieved: {ok}/{len(results)}; routing ok: {sum(r['routing_ok'] for r in results)}")
        path = os.path.join(args.out, f"chat_eval_retrieval_{args.label}_{stamp}.json")
        json.dump({"meta": meta, "results": results}, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("written", path)
        return 0

    # Results are saved after every case, so a run stopped by the Groq daily token limit can be resumed
    # with --resume (cases already in the file are skipped).
    base = os.path.join(args.out, f"chat_eval_{args.label}")
    results = []
    if args.resume and os.path.exists(base + ".json"):
        results = json.load(open(base + ".json", encoding="utf-8"))["results"]
    done = {r["id"] for r in results}

    def save():
        order = {c["id"]: i for i, c in enumerate(json.load(open(args.set, encoding="utf-8"))["cases"])}
        results.sort(key=lambda r: order.get(r["id"], 999))
        json.dump({"meta": meta, "results": results}, open(base + ".json", "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        open(base + ".md", "w", encoding="utf-8").write(markdown(results, args.label, meta))

    for case in cases:
        if case["id"] in done:
            continue
        body, retrieved, routed = run_case(service, case, args.delay)
        if body.get("status") == "ai_unavailable":
            print(f"{case['id']}: the language model is unavailable ({body.get('error_type')}); stopping. "
                  f"Run again with --resume --label {args.label} later.", flush=True)
            break
        r = check_case(case, body, retrieved, routed)
        results.append(r)
        save()
        print(f"{r['id']:5} {'PASS' if r['correct'] else 'FAIL'} {r['outcome']:12} src={'Y' if r['source_retrieved'] else 'N'}"
              f"/{'Y' if r['source_cited'] else 'N'} facts_missing={len(r['missing_facts'])} route={r['routed']}"
              f"{'' if r['routing_ok'] else '(WRONG)'} | {case['question'][:60]}", flush=True)
        time.sleep(args.delay)
    save()
    print(f"correct {sum(r['correct'] for r in results)}/{len(results)}; written {base}.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
