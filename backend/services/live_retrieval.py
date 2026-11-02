"""Answering from official pages fetched live (University-information agent's retriever).

The *official page catalogue* (``config/official_pages.json``) lists candidate URLs with
titles, departments and keywords. It holds no page text and is never evidence:

* entries marked ``reviewed: true`` may be fetched live (only if live retrieval is
  enabled, the host is trusted and robots.txt allows it);
* any entry may be shown as an unverified "place to look" when no answer was verified.

Fetched page text is chunked and ranked in memory with the same BM25 scoring as the
approved-source index, and returned in the same result shape, so the answer, citation
and link-scrubbing code in ``ChatService`` is shared.
"""

import datetime
import json
import logging
import os
import re
import threading
from concurrent.futures import ThreadPoolExecutor, wait
from urllib.parse import quote_plus, urlsplit

from services.sources import (CONCEPT_PREFIX, DEPARTMENT_LABELS, DEPARTMENTS, LOW_SIGNAL_TERMS, SYNONYM_GROUPS,
                              TOKEN_RE, LocalIndex, tokenize)

logger = logging.getLogger(__name__)

DEFAULT_CATALOGUE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                 "config", "official_pages.json")
LIVE_ORIGIN = "live"
CHUNK_CHARS = 1200
CHUNK_OVERLAP = 150


class MemoryIndex(LocalIndex):
    """BM25 index over chunks held in memory (no database)."""

    def __init__(self, chunks):
        super().__init__(db_getter=None)
        prepared, df, avgdl, _ = self.prepare(chunks)
        self._prepared = (prepared, df, avgdl)
        # A small in-memory index (the page catalogue, or a few fetched pages) is matched literally: its
        # vocabulary is too small for spelling correction ("hotel" would become "hostel") or for leaving
        # out unknown words, and catalogue titles are not passages, so answer-kind boosts do not apply.
        # Questions reach it already corrected against the full approved-source index.
        self._vocabulary = {}
        self.adaptive = False

    def _ensure_loaded(self):
        return self._prepared


def chunk_text(text, size=CHUNK_CHARS, overlap=CHUNK_OVERLAP):
    """Split on paragraph boundaries into chunks of about ``size`` characters."""
    chunks, current = [], ""
    for paragraph in (p.strip() for p in (text or "").split("\n")):
        if not paragraph:
            continue
        if current and len(current) + len(paragraph) + 1 > size:
            chunks.append(current)
            current = current[-overlap:] + "\n" + paragraph if overlap else paragraph
        else:
            current = f"{current}\n{paragraph}" if current else paragraph
        while len(current) > size * 1.5:
            chunks.append(current[:size])
            current = current[size - overlap:]
    if current.strip():
        chunks.append(current)
    return chunks


# Words that say *how* someone is looking, not *what* for ("where can I find ..."). They are
# ignored when choosing a page, so "find the handbook" does not match "Where to find us".
LINK_QUERY_NOISE = frozenset(tokenize("find finding look looking see page pages info information details "
                                      "website site link links official")) | LOW_SIGNAL_TERMS
YEAR_RE = re.compile(r"\b(?:19|20)\d{2}\b")


def link_weight(entry, today=None):
    """How much a matching page is preferred (1.0 = normal). Specific, current content pages win
    over the home page, news listings, pages for past years and one-word section pages."""
    path = urlsplit(entry["url"]).path.strip("/")
    if not path:
        return 0.0  # the home page is never a useful "specific page"
    weight = 1.0
    if path.startswith("category/") or "news" in entry["title"].lower():
        weight *= 0.6
    years = [int(y) for y in YEAR_RE.findall(entry["title"])]
    if years and max(years) < (today or datetime.date.today()).year - 1:
        weight *= 0.6
    if len(TOKEN_RE.findall(entry["title"].lower())) <= 1 and "/" not in path:
        weight *= 0.85
    return weight


def matched_words(question, words, entry_terms):
    """The words (or synonym phrases, e.g. "financial aid") of the question that a page matches."""
    found = [w for w in words if set(tokenize(w)) & entry_terms]
    lowered = (question or "").lower()
    for concept, variants in SYNONYM_GROUPS.items():
        if CONCEPT_PREFIX + concept in entry_terms:
            phrase = next((v for v in variants if " " in v
                           and re.search("(?<![a-z0-9])" + re.escape(v) + "(?![a-z0-9])", lowered)), None)
            if phrase:
                found.append(phrase)
    return list(dict.fromkeys(found))


class OfficialPageCatalogue:
    """Candidate official pages (metadata only)."""

    def __init__(self, entries, is_trusted):
        self.entries = []
        for entry in entries:
            url = entry.get("url")
            if not isinstance(url, str) or not entry.get("title"):
                continue
            if not is_trusted(url):
                logger.info("Catalogue entry skipped (not a trusted page): %s", url)
                continue
            department = entry.get("department")
            self.entries.append({
                "url": url,
                "title": str(entry["title"])[:300],
                "department": department if department in DEPARTMENTS else "general_university",
                "keywords": [str(k) for k in entry.get("keywords", [])][:30],
                "reviewed": entry.get("reviewed") is True,
            })
        self._index = MemoryIndex([
            {"source_id": i, "chunk": 0, "text": self._match_text(e)} for i, e in enumerate(self.entries)
        ])

    @staticmethod
    def _match_text(entry):
        path_words = urlsplit(entry["url"]).path.replace("-", " ").replace("/", " ").replace("_", " ")
        return " ".join([entry["title"], entry["title"], path_words, " ".join(entry["keywords"])])

    @classmethod
    def load(cls, path, is_trusted):
        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
        except FileNotFoundError:
            logger.warning("Official page catalogue not found: %s", path)
            return cls([], is_trusted)
        except (OSError, ValueError) as e:
            logger.error("Official page catalogue could not be read (%s)", type(e).__name__)
            return cls([], is_trusted)
        return cls(data.get("pages", []) if isinstance(data, dict) else [], is_trusted)

    @property
    def reviewed_count(self):
        return sum(e["reviewed"] for e in self.entries)

    def match(self, question, k=3, reviewed_only=False, min_coverage=0.3):
        """Best-matching pages, most specific first. Each result has ``score`` and a short ``reason``
        (the words of the question its title, address or keywords match)."""
        words = [w for w in TOKEN_RE.findall((question or "").lower())
                 if not set(tokenize(w)) <= LINK_QUERY_NOISE]

        def drop_noise(match):
            terms = set(tokenize(match.group(0)))
            return "" if terms and terms <= LINK_QUERY_NOISE else match.group(0)

        # Punctuation is kept, so a long question is also matched part by part ("Hello! I am a student.
        # How do I register for my courses?" matches the registration page through its second sentence).
        query = re.sub(r"[A-Za-z0-9]+", drop_noise, question or "")
        hits = self._index.search(query, k=len(self.entries) or 1, min_score=0.0, min_coverage=min_coverage)
        matched = []
        for chunk, score in hits:
            entry = self.entries[chunk["source_id"]]
            if reviewed_only and not entry["reviewed"]:
                continue
            weight = link_weight(entry)
            if weight <= 0:
                continue
            entry_terms = set(tokenize(self._match_text(entry)))
            hit_words = matched_words(question, words, entry_terms)
            reason = (f"Official {DEPARTMENT_LABELS.get(entry['department'], 'USIU-Africa')} page whose title, "
                      f"address or keywords match: {', '.join(hit_words[:5])}") if hit_words else ""
            matched.append({**entry, "score": score * weight, "reason": reason})
        matched.sort(key=lambda e: -e["score"])
        return matched[:k]


def site_search_url(question, host="www.usiu.ac.ke"):
    """A browser link to a web search restricted to the official site. Never fetched by the server."""
    return "https://www.google.com/search?q=" + quote_plus(f"site:{host} {question.strip()[:200]}")


class LiveRetriever:
    """Find, fetch and rank official pages for a question."""

    def __init__(self, settings, website, catalogue):
        self.settings = settings
        self.website = website
        self.catalogue = catalogue
        self._executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="live-fetch")
        self._lock = threading.Lock()
        self.last_report = []  # (url, status) of the most recent attempt, for diagnostics

    @property
    def enabled(self):
        return bool(self.settings.get("LIVE_RETRIEVAL_ENABLED"))

    def retrieve(self, question, k=4, min_score=0.5, min_coverage=0.5):
        """Return ``(results, report)``. ``results`` use the approved-source result shape."""
        if not self.enabled:
            return [], [("*", "disabled")]
        candidates = self.catalogue.match(question, k=self.settings.get("LIVE_MAX_PAGES_PER_QUESTION", 3),
                                          reviewed_only=True)
        if not candidates:
            return [], [("*", "no_reviewed_page_matched")]
        futures = {self._executor.submit(self.website.fetch_page, c["url"]): c for c in candidates}
        done, not_done = wait(futures, timeout=self.settings.get("LIVE_QUESTION_BUDGET_SECONDS", 15))
        report, pages = [], []
        for future, candidate in futures.items():
            if future in not_done:
                report.append((candidate["url"], "timeout"))
                continue
            result = future.result()
            report.append((candidate["url"], result.status))
            if result.ok:
                pages.append((candidate, result.page))
        self.last_report = report
        if not pages:
            return [], report

        chunks, meta = [], {}
        for i, (candidate, page) in enumerate(pages):
            meta[i] = (candidate, page)
            for n, text in enumerate(chunk_text(page.text)):
                chunks.append({"source_id": i, "chunk": n, "text": text})
        hits = MemoryIndex(chunks).search(question, k=k * 3, min_score=min_score, min_coverage=min_coverage)
        by_page, results = {}, []
        for chunk, score in hits:
            candidate, page = meta[chunk["source_id"]]
            entry = by_page.get(chunk["source_id"])
            if entry is None:
                entry = {
                    "source": {
                        "_id": "live:" + page.final_url,
                        "title": page.title or candidate["title"],
                        "url": page.final_url,
                        "department": candidate["department"],
                        "content_type": "html",
                        "origin": LIVE_ORIGIN,
                        "source_date": page.published or None,
                        "retrieved_at": page.fetched_at,
                    },
                    "chunks": [], "relevance": score, "score": score, "stale": False,
                }
                by_page[chunk["source_id"]] = entry
                results.append(entry)
            if len(entry["chunks"]) < 2:
                entry["chunks"].append(chunk["text"])
        results.sort(key=lambda e: -e["score"])
        return results[:k], report

    def status(self):
        return {
            "enabled": self.enabled,
            "trusted_hosts": sorted(self.website.trusted_hosts),
            "catalogue_pages": len(self.catalogue.entries),
            "reviewed_pages": self.catalogue.reviewed_count,
            "cache": self.website.cache_info(),
            "last_attempt": [{"url": u, "status": s} for u, s in self.last_report],
        }
