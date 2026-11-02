"""Approved-source registry and local retrieval index.

Every piece of information USIUBOT answers from is a *source*: one official
USIU-Africa webpage or document, stored in MongoDB with its metadata.

``sources`` collection
    url, url_normalized (unique), title, department, content_type, status,
    source_date (date printed on the source, if any), retrieved_at (when the
    content was obtained), text, text_sha256, notes, status_history, timestamps.

``source_chunks`` collection
    Search chunks of *approved* sources only. They are written when a source is
    approved and deleted when it leaves the approved state, so draft or archived
    content can never be retrieved.

Live crawling is deliberately not implemented here. Source text is entered by
an administrator (pasted text or an uploaded PDF) until permitted automated
access to the university website exists.
"""

import datetime
import difflib
import hashlib
import logging
import math
import re
import threading
import time
from collections import Counter
from urllib.parse import urlsplit, urlunsplit

from bson import ObjectId

logger = logging.getLogger(__name__)

DEPARTMENTS = ("admissions", "registrar", "finance", "academic_programmes", "marketing", "student_affairs", "ict",
               "library", "general_university")
DEPARTMENT_LABELS = {
    "admissions": "Admissions",
    "registrar": "Registrar",
    "finance": "Finance",
    "academic_programmes": "Academic Programmes",
    "marketing": "Marketing",
    "student_affairs": "Student Affairs",
    "ict": "ICT",
    "library": "Library",
    "general_university": "General University Information",
}
CONTENT_TYPES = ("html", "pdf")

# The eight knowledge categories of the USIUBOT dataset (usiubot_datasets/).
CATEGORIES = {
    "01": "General University Information",
    "02": "Academic Programmes",
    "03": "Admissions and Applications",
    "04": "Fees and Payments",
    "05": "Registrar and Academic Administration",
    "06": "Department Contacts and Query Routing",
    "07": "Academic Documents, Results and Verified Eligibility",
    "08": "Questions, Answers and Unresolved Enquiries",
}
# official = published by USIU-Africa; external = another body (e.g. KUCCPS), never USIU-Africa policy.
DATA_ORIGINS = ("official", "external")
# Sources imported from the dataset are keyed by their dataset section id.
DATASET_KEY_PREFIX = "dataset:"
BULK_STATUS_LIMIT = 500
# Answers written by USIU staff for logged questions. They have no URL, are created as
# drafts and only influence answers after an administrator approves them.
STAFF_ANSWER = "staff_answer"
# draft -> approved (searchable) | rejected (reviewed and not used) | archived (withdrawn or outdated)
STATUSES = ("draft", "approved", "rejected", "archived")
FLAG_DUPLICATE_TEXT = "duplicate_content"

MAX_URL_LENGTH = 2048
MAX_TITLE_LENGTH = 300
MAX_NOTES_LENGTH = 2000
SOURCE_DATE_RE = re.compile(r"^\d{4}(-\d{2}(-\d{2})?)?$")


class SourceError(ValueError):
    """Invalid source data or a disallowed operation. Messages are safe to show to admins."""


class SourceNotFound(SourceError):
    pass


def utcnow():
    return datetime.datetime.now(datetime.timezone.utc)


def as_utc(value):
    """MongoDB returns naive datetimes; treat them as UTC."""
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=datetime.timezone.utc)


# --- Validation -------------------------------------------------------------------
def host_is_allowed(host, allowed_domains):
    host = (host or "").lower().rstrip(".")
    return any(host == d or host.endswith("." + d) for d in allowed_domains)


def normalize_source_url(url, allowed_domains):
    """Validate an official source URL and return its canonical form.

    Only ``https`` URLs on an allowed domain (or its subdomains) are accepted;
    credentials, non-standard ports, whitespace and control characters are rejected.
    """
    if not isinstance(url, str) or not url.strip():
        raise SourceError("URL is required")
    url = url.strip()
    if len(url) > MAX_URL_LENGTH or any(ch.isspace() or ord(ch) < 32 for ch in url):
        raise SourceError("URL is too long or contains invalid characters")
    try:
        parts = urlsplit(url)
        port = parts.port
    except ValueError:
        raise SourceError("URL is not valid") from None
    if parts.scheme.lower() != "https":
        raise SourceError("Only https URLs are accepted")
    if parts.username or parts.password or "@" in parts.netloc:
        raise SourceError("URLs must not contain credentials")
    if port not in (None, 443):
        raise SourceError("URLs must use the standard https port")
    host = (parts.hostname or "").lower()
    if not host_is_allowed(host, allowed_domains):
        raise SourceError("URL must be on an approved USIU-Africa domain: " + ", ".join(allowed_domains))
    return urlunsplit(("https", host, parts.path or "/", parts.query, ""))


def is_safe_citation_url(url, allowed_domains):
    try:
        normalize_source_url(url, allowed_domains)
        return True
    except SourceError:
        return False


def parse_source_date(value, label="Source date"):
    """Accept YYYY, YYYY-MM or YYYY-MM-DD (not in the future). Returns the string or None."""
    if value in (None, ""):
        return None
    if not isinstance(value, str) or not SOURCE_DATE_RE.match(value.strip()):
        raise SourceError(f"{label} must be YYYY, YYYY-MM or YYYY-MM-DD")
    value = value.strip()
    if source_date_start(value) is None:
        raise SourceError(f"{label} is not a valid date")
    if source_date_start(value) > utcnow().date():
        raise SourceError(f"{label} cannot be in the future")
    return value


def source_date_start(value):
    """First calendar day covered by a YYYY / YYYY-MM / YYYY-MM-DD string."""
    parts = [int(p) for p in value.split("-")] + [1, 1]
    try:
        return datetime.date(parts[0], parts[1], parts[2])
    except ValueError:
        return None


def source_date_end(value):
    """Last calendar day covered (so '2025' is treated as late as 2025-12-31)."""
    parts = [int(p) for p in value.split("-")]
    if len(parts) == 1:
        return datetime.date(parts[0], 12, 31)
    if len(parts) == 2:
        next_month = datetime.date(parts[0] + parts[1] // 12, parts[1] % 12 + 1, 1)
        return next_month - datetime.timedelta(days=1)
    return datetime.date(*parts)


def parse_retrieved_at(value):
    if value in (None, ""):
        return utcnow()
    if not isinstance(value, str):
        raise SourceError("Retrieval date must be an ISO date")
    try:
        parsed = datetime.datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        raise SourceError("Retrieval date must be an ISO date (YYYY-MM-DD)") from None
    parsed = as_utc(parsed)
    # A plain date ("2026-10-26") is the local date of whoever obtained the source; in time zones
    # ahead of UTC (Nairobi is UTC+3) it can already be tomorrow in UTC terms, so allow up to 14 hours.
    tolerance = datetime.timedelta(hours=14) if len(value.strip()) == 10 else datetime.timedelta(minutes=5)
    if parsed > utcnow() + tolerance:
        raise SourceError("Retrieval date cannot be in the future")
    return parsed


def reference_date(source):
    """The date a source is judged by: its own date, else its retrieval date, else None."""
    if source.get("source_date"):
        return source_date_end(source["source_date"])
    if source.get("retrieved_at"):
        return as_utc(source["retrieved_at"]).date()
    return None


def _date_rank(source):
    reference = reference_date(source)
    return reference.toordinal() if reference else 0


def is_stale(source, max_age_days, now=None):
    """A source is stale when its own date (or, if absent, its retrieval date) is too old."""
    now = now or utcnow()
    reference = reference_date(source)
    if reference is None:
        return True
    return (now.date() - reference).days > max_age_days


def _clean_text(value, label, max_length, required=True):
    if value is None and not required:
        return ""
    if not isinstance(value, str) or (required and not value.strip()):
        raise SourceError(f"{label} is required")
    value = value.strip()
    if len(value) > max_length:
        raise SourceError(f"{label} must be at most {max_length} characters")
    return value


def _choice(value, label, choices):
    if value not in choices:
        raise SourceError(f"{label} must be one of: {', '.join(choices)}")
    return value


# --- Text processing for the local index -------------------------------------------
STOPWORDS = frozenset("""
a an and are as at be been but by can could did do does for from had has have how i if in into is it
its me my of on or our please so that the their them then there these they this to us was we were
what when where which who why will with would you your about any also tell know want need get
hello hi hey kindly like available still
am go going goes went bring come comes coming else somewhere someone something anything everything
doesn don didn isn aren wasn won cant cannot just really very much many some every each there here
okay ok thanks thank dear sir madam guide through upcoming current currently next while way ways able
possible should must happen happens happened mean means provide provides offer offers find help day days
time times process procedure procedures step steps exactly
""".split())
# Question words such as "process", "steps", "deadline" or "how much" say what *kind* of answer is
# wanted, not what it is about; they are stopwords for matching and are used by question_intents().
TOKEN_RE = re.compile(r"[a-z0-9]+")

# Synonyms and phrasings for common university enquiries. Every listed word or phrase,
# in questions *and* in source text, is replaced by one shared concept token, so a
# question about the "cost" of studying matches a source about "fees". Keep the lists
# short and specific: a variant here changes how every source is matched.
SYNONYM_GROUPS = {
    "fees": ["fee", "fees", "tuition", "cost", "costs", "price", "prices", "how much", "charges"],
    # Not "results": exam results, KCSE results and transcripts are different enquiries.
    "transcript": ["transcript", "transcripts", "academic record", "academic records"],
    "accommodation": ["accommodation", "accommodations", "hostel", "hostels", "dorm", "dorms",
                      "dormitory", "dormitories", "housing", "residence hall", "residence halls",
                      "where can i live", "where will i live", "where to live", "live on campus",
                      "place to stay", "stay on campus"],
    "registration": ["register", "registers", "registered", "registering", "registration",
                     "sign up", "signing up", "enrol", "enroll", "enrols", "enrolls", "enrolment",
                     "enrollment", "enrolling",
                     # Kenyan usage: "units" are courses ("register my units", "unit registration").
                     "unit registration", "select my units", "selecting my units", "select units",
                     "selecting units", "choose my units", "choosing my units", "pick my units",
                     "select my courses", "selecting my courses", "select courses", "choose my courses",
                     "course selection", "unit selection"],
    "readmission": ["readmission", "re-admission", "readmit", "re-admit", "readmitted", "re-admitted",
                    "come back to usiu", "come back to the university", "come back to school",
                    "return to usiu", "return to the university", "return to my studies", "resume my studies",
                    "resume studies", "rejoin the university", "rejoin usiu", "stopped studying",
                    "not in continuous enrolment", "not in continuous enrollment"],
    "adddrop": ["add/drop", "add and drop", "add drop", "drop a course", "drop course", "drop courses",
                "drop my course", "drop a class", "dropping a course", "dropped course", "dropped courses",
                "drop a unit", "drop my unit"],
    "hold": ["hold", "holds", "financial hold", "blocked from registering", "blocked from registration"],
    "idcard": ["id card", "id cards", "student id", "identification card", "rfid card", "student card",
               "id"],
    "wifi": ["wifi", "wi-fi", "wireless", "wireless internet", "internet access", "internet connection"],
    "dental": ["dental", "dentist", "dentists", "teeth", "tooth"],
    "medical": ["clinic", "clinics", "health center", "health centre", "medical", "medical services",
                "medical treatment", "medical care", "see a doctor", "hospital"],
    "interlibrary": ["inter-library loan", "interlibrary loan", "inter library loan", "inter-library",
                     "interlibrary", "other libraries", "another library", "other local libraries",
                     "library doesn't have", "library does not have", "not available in the library"],
    "contact": ["contact", "contacts", "contact details", "phone", "telephone", "tel", "email", "e-mail",
                "mail", "phone number", "telephone number", "email address", "reach"],
    "graduation": ["graduation", "graduation ceremony", "commencement", "graduation day"],
    "deferment": ["defer", "defers", "deferred", "deferring", "deferral", "deferment", "postpone",
                  "postponing", "postponement", "start later", "start next year", "start my studies later",
                  "begin later", "delay my admission", "delay admission"],
    "scholarship": ["scholarship", "scholarships", "financial aid", "financial help", "financial support",
                    "funding", "bursary", "bursaries", "sponsorship"],
    # Applying is a main intent of visitor questions ("... and how can I apply?").
    "apply": ["apply", "applies", "applying", "application", "applications", "applicant", "applicants"],
    "location": ["located", "location", "locations", "situated", "address", "directions", "where to find us",
                 "p o box", "po box", "postal address", "physical address"],
}
CONCEPT_PREFIX = "concept"
# British and American spellings of the same word ("programmes" in a question, "Programs" on the
# university website) are indexed as one token.
SPELLING_VARIANTS = {"programme": "program", "programmes": "programs", "centre": "center", "centres": "centers",
                     "counselling": "counseling", "counsellor": "counselor", "counsellors": "counselors",
                     "instalment": "installment", "instalments": "installments", "cheque": "check",
                     "cheques": "checks", "licence": "license", "behaviour": "behavior"}
# Words that share a stem with a synonym concept but mean something else ("Applied Computer Technology"
# is a programme name, not a question about applying). They are stemmed but never mapped to a concept.
NOT_A_CONCEPT = frozenset({"applied"})
# Light suffix stripping so "apply", "applied", "application" and "applicant" match.
SUFFIXES = ("ication", "icant", "ration", "ation", "ment", "ing", "ied", "ed", "er", "y")


def stem(token, _second_pass=False):
    if len(token) > 4 and token.endswith("ies"):
        token = token[:-3] + "y"
    elif len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
        token = token[:-1]
    for suffix in SUFFIXES:
        if token.endswith(suffix) and len(token) - len(suffix) >= 4:
            token = token[: -len(suffix)]
            # One more pass so "studying" -> "study" -> "stud" agrees with "study" -> "stud".
            return token if _second_pass else stem(token, _second_pass=True)
    return token


def _build_synonym_tables():
    phrases, words = [], {}
    for concept, variants in SYNONYM_GROUPS.items():
        token = CONCEPT_PREFIX + concept
        for variant in variants:
            parts = TOKEN_RE.findall(variant.lower())
            if len(parts) > 1:
                phrases.append((re.compile(r"\b" + r"\W+".join(parts) + r"\b"), f" {token} "))
            else:
                words[parts[0]] = token
                words[stem(parts[0])] = token
    phrases.sort(key=lambda item: len(item[0].pattern), reverse=True)  # longest phrase first
    return phrases, words


_PHRASES, _SYNONYM_WORDS = _build_synonym_tables()
# All phrases in one pattern (longest alternative first), so tokenising costs one scan of the text
# instead of one per phrase.
_PHRASE_TOKENS = {" ".join(TOKEN_RE.findall(variant.lower())): f" {CONCEPT_PREFIX}{concept} "
                  for concept, variants in SYNONYM_GROUPS.items() for variant in variants
                  if len(TOKEN_RE.findall(variant.lower())) > 1}
_PHRASE_RE = re.compile(r"\b(?:" + "|".join(
    r"\W+".join(key.split()) for key in sorted(_PHRASE_TOKENS, key=len, reverse=True)) + r")\b")


def _phrase_token(match):
    return _PHRASE_TOKENS[" ".join(TOKEN_RE.findall(match.group(0)))]

# Letter grades ("C+", "C plus", "C+ (Plus)", "B- (minus)", "C plain") become one token each, so that
# "C plain" no longer matches "B plain" and "C+" is searchable at all (one-letter words are dropped).
GRADE_RE = re.compile(r"(?<![A-Za-z0-9])([A-Ea-e])(\+|-(?![A-Za-z0-9])|\s+(?:plus|minus|plain)\b)(?:\s*\((?:plus|minus|plain)\))?", re.IGNORECASE)
GRADE_MODIFIERS = {"+": "plus", "plus": "plus", "-": "minus", "minus": "minus", "plain": "plain"}


def _grade_token(match):
    letter, modifier = match.group(1), match.group(2).strip().lower()
    if letter == "a" and modifier.isalpha():  # "a plain answer": the article, not grade A
        return match.group(0)
    # Any stated grade (a "grade" concept) plus the exact grade, so "C plain" still finds the pages that
    # state the KCSE grade requirement while the exact grade ranks the closest match first.
    return f" {CONCEPT_PREFIX}grade grade{letter.lower()}{GRADE_MODIFIERS[modifier]} "


def tokenize(text):
    text = GRADE_RE.sub(_grade_token, text or "").lower()
    text = _PHRASE_RE.sub(_phrase_token, text)
    tokens = []
    for raw in TOKEN_RE.findall(text):
        raw = SPELLING_VARIANTS.get(raw, raw)
        if raw.startswith(CONCEPT_PREFIX):
            tokens.append(raw)
        elif raw in NOT_A_CONCEPT:
            tokens.append(stem(raw))
        elif raw not in STOPWORDS and len(raw) >= 2:
            tokens.append(_SYNONYM_WORDS.get(raw) or _SYNONYM_WORDS.get(stem(raw)) or stem(raw))
    return tokens


# Splits multi-part questions into parts ("... and ...", "...? ...", "...; ...", sentences, and
# comma-separated lists such as "the programmes you offer, the admission requirements"). A comma or
# full stop only splits when followed by a space, so "KES 3,500" and "e.g." stay whole.
PART_SPLIT_RE = re.compile(r"\?|;|!|[.,](?=\s)|\band\b|\balso\b", re.IGNORECASE)

# Words that appear in almost every university source; they don't help choose between sources.
LOW_SIGNAL_TERMS = frozenset(tokenize("usiu africa usiu-africa university universities student students campus"))

# What *kind* of answer a question asks for, and what a passage that gives that kind of answer looks
# like. "How do I register?" (procedure) and "When does registration close?" (deadline) share their
# topic words; among passages that match the topic, those with the right kind of content (numbered
# steps, forms and portals for a procedure; dates for a deadline; amounts for a fee) rank higher.
_MONTH = r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?"
QUESTION_INTENTS = {
    "procedure": (
        re.compile(r"\bhow (?:do|can|should|would|to|does)\b|\bprocess\b|\bprocedure|\bsteps?\b|\bguide me\b"
                   r"|\bwhat (?:should|do|must) i do\b|\bwhat do i need to do\b|\bapply for\b|\bget (?:a|an|my)\b", re.I),
        re.compile(r"(?:^|\n)\s*(?:\d{1,2}[.)]|step\s*\d)\s+\S|\bsteps?\b|\bprocedure\b|\bsubmit|\bfill\b|\bform\b"
                   r"|\bportal\b|\blog ?in\b|\bapply (?:through|via|online|at)\b|\bapproval\b|\bapproved by\b", re.I)),
    "deadline": (
        re.compile(r"\bwhen\b|\bdeadline|\blast day\b|\bdue\b|\bclos(?:e|es|ing)\b|\bdates?\b|\bbegins?\b|\bstarts?\b", re.I),
        re.compile(rf"\b{_MONTH}\s+\d{{1,2}}\b|\b\d{{1,2}}(?:st|nd|rd|th)?\s+{_MONTH}\b|\bdeadline|\blast day\b"
                   r"|\bdue\b|\bbefore (?:the )?(?:registration|semester|start|first day|end|deadline|date)\b"
                   r"|\bwithin \w+ (?:calendar |working )?(?:days|weeks)\b", re.I)),
    "fees": (
        re.compile(r"\bhow much\b|\bcosts?\b|\bfees?\b|\bprices?\b|\bcharges?\b|\btuition\b|\binterest\b|\brefund", re.I),
        re.compile(r"\bK(?:E)?SH?S?\.?\s?\d|\b\d{1,3}(?:,\d{3})+(?:\.\d{2})?\b|\d\s?%|\bper (?:semester|month|course)\b",
                   re.I)),
    "requirements": (
        re.compile(r"\brequire|\bwhat do i need\b|\bqualif|\beligib|\bentry\b|\bminimum\b|\bwho can\b|\bcriteria\b"
                   r"|\bget into\b|\ballowed\b|\brules?\b", re.I),
        re.compile(r"\brequire|\bminimum\b|\bmust\b|\beligib|\bqualif|\bholders? of\b|\bvalid\b|\bnot (?:allowed|permitted)\b"
                   r"|\bonly\b", re.I)),
    "contact": (
        re.compile(r"\bcontact|\be-?mail|\bphone|\bcall\b|\breach\b|\bnumber\b|\bwho (?:do|should|can) i (?:talk|speak|ask)",
                   re.I),
        re.compile(r"@[a-z0-9.-]+\.[a-z]{2,}|\+?\d{3}[\s-]?\d{3}[\s-]?\d{3}|\btel\b|\bext\b", re.I)),
    "schedule": (
        re.compile(r"\bwhat time\b|\bhours\b|\bopen(?:ing)?\b|\bwhich days?\b|\bwhat days?\b", re.I),
        re.compile(r"\d{1,2}[:.]\d{2}|\b(?:mon|tue|wed|thu|fri|sat|sun)[a-z]*\b|\b\d{1,2}\s?(?:am|pm)\b", re.I)),
}
INTENT_BOOST = 1.3


def _edit_distance(a, b):
    """Levenshtein distance (insertions, deletions and substitutions)."""
    previous = list(range(len(b) + 1))
    for i, char_a in enumerate(a, 1):
        current = [i]
        for j, char_b in enumerate(b, 1):
            current.append(min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (char_a != char_b)))
        previous = current
    return previous[-1]


def question_intents(text):
    """The kinds of answer the question asks for, e.g. ``{"procedure"}`` or ``{"deadline", "fees"}``."""
    return {name for name, (pattern, _) in QUESTION_INTENTS.items() if pattern.search(text or "")}


def passage_intents(text):
    """The kinds of answer a passage can give (see ``QUESTION_INTENTS``)."""
    return {name for name, (_, pattern) in QUESTION_INTENTS.items() if pattern.search(text or "")}


# Spelling correction: a question word that appears in no approved source (and is not a known
# synonym) is replaced by the closest word of the same first letter that does, if it is similar
# enough ("registrashun" -> "registration", "accomodation" -> "accommodation", "semster" ->
# "semester"). Words under six letters are left alone: "hotel" must not become "hostel".
SPELLING_MIN_LENGTH = 6
SPELLING_CUTOFF = 0.8
SPELLING_CUTOFF_LONG = 0.75  # words of 9+ letters may differ a little more ("registrashun")
_KNOWN_WORDS = frozenset(w for variants in SYNONYM_GROUPS.values() for v in variants for w in TOKEN_RE.findall(v))
# A term found in no approved source cannot tell sources apart. If more than this share of a question
# (by weight) is found in the index, the unknown words are left out of the coverage test, so one odd
# or misspelt word does not hide every source; otherwise they stay and the question matches nothing
# ("What is the capital of France?" must not match a source on "capital" alone).
KNOWN_TERMS_MIN_SHARE = 0.6
TITLE_TERM_COUNT = 2


def is_citable(source, allowed_domains, external_domains=()):
    """Whether a source can be shown as a citation.

    * Approved staff answers have no URL.
    * External dataset sources need an https URL on an allowed external domain (they are always
      labelled as external, never as USIU-Africa policy).
    * A dataset PDF section without a public URL (e.g. the undated Student Handbook) is cited by
      its file name and page numbers instead of a link.
    * Every other source needs a valid official URL.
    """
    if source.get("content_type") == STAFF_ANSWER:
        return not source.get("url")
    dataset = source.get("dataset") or {}
    if source.get("data_origin") == "external":
        return bool(external_domains) and is_safe_citation_url(source.get("url"), external_domains)
    if not source.get("url") and dataset:
        return bool(source.get("content_type") == "pdf" and dataset.get("document_file") and dataset.get("page_start"))
    return is_safe_citation_url(source.get("url"), allowed_domains)


def is_test_record(source):
    """Records made for automated tests. They are never retrieved unless the app runs in test mode."""
    return bool(source.get("is_test"))


class LocalIndex:
    """BM25 keyword search over chunks of approved sources, kept in memory.

    The in-memory copy is rebuilt from MongoDB when the registry changes in
    this process, and at least every ``ttl`` seconds so that other worker
    processes pick up approvals too.
    """

    K1 = 1.5
    B = 0.75
    # Spelling correction, leaving out unknown words and answer-kind boosts (see search()).
    adaptive = True

    def __init__(self, db_getter, ttl=60):
        self._db_getter = db_getter
        self.ttl = ttl
        self._lock = threading.Lock()
        self._loaded_at = 0.0
        self._chunks = []

    def invalidate(self):
        with self._lock:
            self._loaded_at = 0.0

    def _ensure_loaded(self):
        with self._lock:
            if self._loaded_at and time.monotonic() - self._loaded_at < self.ttl:
                return self._chunks, self._df, self._avgdl
            chunks_col = self._db_getter("source_chunks")
            docs = list(chunks_col.find({}, {"source_id": 1, "chunk": 1, "text": 1, "category": 1, "meta": 1}))
            # Source titles (page and section headings) are searchable too: PDF sections such as
            # "4.3 Services offered by the Registrar" do not repeat their heading in the text.
            titles = {}
            try:
                ids = list({d["source_id"] for d in docs})
                titles = {s["_id"]: s.get("title") or "" for s in self._db_getter("sources").find(
                    {"_id": {"$in": ids}}, {"title": 1})}
            except Exception as e:  # titles only improve ranking; never fail the search over them
                logger.warning("Source titles not indexed (%s)", type(e).__name__)
            for doc in docs:
                doc["title"] = titles.get(doc["source_id"], "")
            chunks, df, avgdl, vocabulary = self.prepare(docs)
            self._chunks, self._df, self._avgdl, self._vocabulary = chunks, df, avgdl, vocabulary
            self._loaded_at = time.monotonic()
            return chunks, df, avgdl

    @staticmethod
    def prepare(docs):
        """Term counts, document frequencies, average length and word vocabulary for chunk ``docs``.

        Title words count as ``TITLE_TERM_COUNT`` occurrences (one extra if the text already has them):
        a heading says what the section is about, and PDF sections such as "4.3 Services offered by
        the Registrar" do not repeat it in their text. Each chunk also records which kinds of
        answer it can give (``passage_intents``).
        """
        chunks, vocabulary = [], {}
        for doc in docs:
            text, title = doc.get("text") or "", doc.get("title") or ""
            terms = Counter(tokenize(text))
            for term in set(tokenize(title)):
                terms[term] += TITLE_TERM_COUNT if term not in terms else 1
            chunks.append({**doc, "terms": terms, "length": sum(terms.values()), "intents": passage_intents(text)})
            for word in TOKEN_RE.findall(f"{title} {text}".lower()):
                if len(word) >= SPELLING_MIN_LENGTH and not word.isdigit():
                    vocabulary.setdefault(word[0], set()).add(word)
        for word in _KNOWN_WORDS:
            if len(word) >= SPELLING_MIN_LENGTH:
                vocabulary.setdefault(word[0], set()).add(word)
        df = Counter()
        for chunk in chunks:
            df.update(chunk["terms"].keys())
        avgdl = (sum(c["length"] for c in chunks) / len(chunks)) if chunks else 0.0
        return chunks, df, avgdl, {letter: sorted(words) for letter, words in vocabulary.items()}

    def correct_spelling(self, text):
        """``text`` with misspelt words replaced by the closest word found in the approved sources."""
        self._ensure_loaded()
        vocabulary = getattr(self, "_vocabulary", None) or {}
        if not text or not vocabulary:
            return text or ""

        def fix(match):
            word = match.group(0)
            lower = word.lower()
            if (len(lower) < SPELLING_MIN_LENGTH or lower.isdigit() or lower in STOPWORDS
                    or lower in vocabulary.get(lower[0], ())):
                return word
            cutoff = SPELLING_CUTOFF_LONG if len(lower) >= 9 else SPELLING_CUTOFF
            close = difflib.get_close_matches(lower, vocabulary.get(lower[0], ()), n=5, cutoff=cutoff)
            # Of the similar words, the one fewest edits away ("registrashun" -> "registration", not
            # "registers"); ties keep difflib's order (most similar first).
            return min(close, key=lambda candidate: _edit_distance(lower, candidate)) if close else word

        return re.sub(r"[A-Za-z]+", fix, text)

    @staticmethod
    def _weights(text):
        # Words found in almost any source ("USIU-Africa", "students") get weight 0: they never count
        # towards coverage, but still add their (small) BM25 score, so "Where is USIU-Africa located?"
        # prefers text about USIU-Africa itself over "the PACS office is located at ...".
        return {t: (0 if t in LOW_SIGNAL_TERMS else 2 if t.startswith(CONCEPT_PREFIX) else 1)
                for t in tokenize(text)}

    @classmethod
    def query_parts(cls, query):
        """Term weights for the whole question and for each part of a multi-part question.

        "When does registration open and how are applications submitted?" is also
        searched as its two parts, so each part can find its own source while every
        part still has to meet the coverage threshold. Parts with less than two
        weighted terms (e.g. the single words of "terms and conditions") are ignored.
        """
        parts = [cls._weights(query)]
        pieces = PART_SPLIT_RE.split(query or "")
        if len(pieces) > 1:
            for piece in pieces:
                weights = cls._weights(piece)
                if sum(weights.values()) >= 2 and weights not in parts:
                    parts.append(weights)
        return [w for w in parts if sum(w.values()) > 0]

    @staticmethod
    def _known_terms(weights, df):
        """Leave out words no approved source contains, if most of the question is still known
        (see ``KNOWN_TERMS_MIN_SHARE``)."""
        total = sum(weights.values())
        known = {term: weight for term, weight in weights.items() if df.get(term)}
        if known and total and sum(known.values()) > total * KNOWN_TERMS_MIN_SHARE:
            return known
        return weights

    def search(self, query, k=5, min_score=0.0, min_coverage=0.0, categories=None, per_part=0):
        """Return ``[(chunk_doc, score)]`` sorted by score, best first.

        Each returned chunk is a copy carrying ``part_scores`` ({part index: score} for every part of
        the question it is relevant to; 0 = the whole question). With ``per_part`` > 0, the best
        ``per_part`` chunks of every part of a multi-part question are also returned even if they are
        outside the top ``k``, so one part of the question cannot crowd out the others.

        ``min_coverage`` is the weighted share of the question's key terms a chunk
        must contain, so one shared word is not treated as relevant. Words found in
        almost any university text (LOW_SIGNAL_TERMS) are ignored, and a synonym
        concept ("fees", "accommodation", ...) counts twice because it carries the
        main intent of the question. A chunk is relevant if it meets the threshold
        for the whole question or for one of its parts (see ``query_parts``).
        """
        # ``categories`` (dataset category ids such as "04") restricts the search to chunks of those
        # categories; statistics (IDF) are still computed over the whole index.
        chunks, df, avgdl = self._ensure_loaded()
        if self.adaptive:
            query = self.correct_spelling(query)
            parts = [self._known_terms(weights, df) for weights in self.query_parts(query)]
        else:
            parts = self.query_parts(query)
        if not chunks or not parts:
            return []
        intents = question_intents(query) if self.adaptive else set()
        n = len(chunks)
        wanted = set(categories) if categories else None
        scored = []
        for chunk in chunks:
            if wanted is not None and chunk.get("category") not in wanted:
                continue
            # A passage that gives the kind of answer asked for (steps, a date, an amount...) ranks higher.
            boost = INTENT_BOOST if intents & chunk.get("intents", set()) else 1.0
            part_scores = {}
            for index, weights in enumerate(parts):
                score, matched = 0.0, 0
                for term, weight in weights.items():
                    tf = chunk["terms"].get(term, 0)
                    if not tf:
                        continue
                    matched += weight
                    idf = math.log(1 + (n - df[term] + 0.5) / (df[term] + 0.5))
                    norm = tf + self.K1 * (1 - self.B + self.B * chunk["length"] / (avgdl or 1))
                    score += idf * tf * (self.K1 + 1) / norm
                if matched and score > min_score and matched / sum(weights.values()) >= min_coverage:
                    part_scores[index] = score * boost
            if part_scores:
                scored.append(({**chunk, "part_scores": part_scores}, max(part_scores.values())))
        scored.sort(key=lambda item: item[1], reverse=True)
        top = scored[:k]
        if per_part and len(parts) > 1:
            included = {id(item[0]) for item in top}
            for index in range(1, len(parts)):
                ranked = sorted((item for item in scored if index in item[0]["part_scores"]),
                                key=lambda item: item[0]["part_scores"][index], reverse=True)
                for item in ranked[:per_part]:
                    if id(item[0]) not in included:
                        included.add(id(item[0]))
                        top.append(item)
            top.sort(key=lambda item: item[1], reverse=True)
        return top


# --- Registry -------------------------------------------------------------------------
class SourceRegistry:
    """Create, review and retrieve approved USIU-Africa sources."""

    def __init__(self, db_getter, settings):
        self._db = db_getter
        self.settings = settings
        self.allowed_domains = tuple(d.lower() for d in settings.get("ALLOWED_SOURCE_DOMAINS", ("usiu.ac.ke",)))
        # Domains of external bodies (e.g. KUCCPS) whose dataset records may be cited, always labelled external.
        self.external_domains = tuple(d.lower() for d in settings.get("EXTERNAL_SOURCE_DOMAINS", ()))
        self.max_text = settings.get("SOURCE_MAX_TEXT_CHARS", 200_000)
        self.index = LocalIndex(db_getter, ttl=settings.get("SOURCE_INDEX_TTL", 60))

    def citable(self, source):
        return is_citable(source, self.allowed_domains, self.external_domains)

    def _retrievable(self, source):
        """Approved, citable and not a test record (test records are retrievable only in test mode)."""
        if is_test_record(source) and not self.settings.get("ALLOW_TEST_SOURCES"):
            return False
        return self.citable(source)

    @property
    def sources(self):
        return self._db("sources")

    @property
    def chunks(self):
        return self._db("source_chunks")

    # --- reading ---------------------------------------------------------------------
    def get(self, source_id):
        try:
            oid = ObjectId(source_id)
        except Exception:
            raise SourceNotFound("Source not found") from None
        source = self.sources.find_one({"_id": oid})
        if not source:
            raise SourceNotFound("Source not found")
        return source

    def find_by_url(self, url):
        """The source with this URL (after normalisation), or None."""
        return self.sources.find_one({"url_normalized": normalize_source_url(url, self.allowed_domains)})

    def list(self, status=None, department=None, category=None, data_origin=None, origin_kind=None, search=None,
             flagged=None):
        """Filter sources. ``origin_kind``: "dataset" (imported from usiubot_datasets) or "manual"."""
        query = {}
        if status:
            query["status"] = _choice(status, "Status", STATUSES)
        if department:
            query["department"] = _choice(department, "Department", DEPARTMENTS)
        if category:
            query["category"] = _choice(category, "Category", tuple(CATEGORIES))
        if data_origin:
            query["data_origin"] = _choice(data_origin, "Origin", DATA_ORIGINS)
        if origin_kind == "dataset":
            query["dataset"] = {"$exists": True}
        elif origin_kind == "manual":
            query["dataset"] = {"$exists": False}
        elif origin_kind:
            raise SourceError("Origin kind must be dataset or manual")
        if search:
            if not isinstance(search, str) or len(search) > 200:
                raise SourceError("Search text must be at most 200 characters")
            query["title"] = {"$regex": re.escape(search.strip()), "$options": "i"}
        if flagged == "yes":
            query["review_flags.0"] = {"$exists": True}
        elif flagged == "no":
            query["review_flags.0"] = {"$exists": False}
        return list(self.sources.find(query, {"text": 0, "dataset_chunks": 0}).sort("updated_at", -1))

    # --- writing ---------------------------------------------------------------------
    def _validated(self, data, partial=False, existing=None):
        fields = {}
        if not partial or "url" in data:
            fields["url_normalized"] = normalize_source_url(data.get("url"), self.allowed_domains)
            fields["url"] = fields["url_normalized"]
        if not partial or "title" in data:
            fields["title"] = _clean_text(data.get("title"), "Title", MAX_TITLE_LENGTH)
        if not partial or "department" in data:
            fields["department"] = _choice(data.get("department"), "Department", DEPARTMENTS)
        if not partial or "content_type" in data:
            fields["content_type"] = _choice(data.get("content_type", "html"), "Content type", CONTENT_TYPES)
        if not partial or "source_date" in data:
            fields["source_date"] = parse_source_date(data.get("source_date"))
        if not partial or "notes" in data:
            fields["notes"] = _clean_text(data.get("notes"), "Notes", MAX_NOTES_LENGTH, required=False)
        if not partial or "text" in data:
            text = data.get("text") or ""
            if not isinstance(text, str):
                raise SourceError("Text must be a string")
            text = text.strip()
            if len(text) > self.max_text:
                raise SourceError(f"Text must be at most {self.max_text} characters")
            fields["text"] = text
            fields["text_sha256"] = hashlib.sha256(text.encode("utf-8")).hexdigest() if text else ""
            fields["retrieved_at"] = parse_retrieved_at(data.get("retrieved_at")) if text else None
        elif "retrieved_at" in data:
            fields["retrieved_at"] = parse_retrieved_at(data.get("retrieved_at"))
        return fields

    def _check_unique_url(self, url_normalized, exclude_id=None):
        query = {"url_normalized": url_normalized}
        if exclude_id is not None:
            query["_id"] = {"$ne": exclude_id}
        if self.sources.find_one(query, {"_id": 1}):
            raise SourceError("A source with this URL already exists")

    def create(self, data, actor="admin"):
        fields = self._validated(data)
        self._check_unique_url(fields["url_normalized"])
        now = utcnow()
        doc = {
            **fields,
            "status": "draft",
            "created_at": now,
            "updated_at": now,
            "approved_at": None,
            "approved_by": None,
            "status_history": [{"status": "draft", "at": now, "by": actor}],
        }
        if self._same_text_as(fields.get("text_sha256")):
            doc["review_flags"] = [FLAG_DUPLICATE_TEXT]
        doc["_id"] = self.sources.insert_one(doc).inserted_id
        return doc

    def _same_text_as(self, text_sha256, exclude_id=None):
        """Another source with exactly the same text, or None (shown to reviewers as a flag)."""
        if not text_sha256:
            return None
        query = {"text_sha256": text_sha256}
        if exclude_id is not None:
            query["_id"] = {"$ne": exclude_id}
        return self.sources.find_one(query, {"_id": 1, "url": 1})

    def update(self, source_id, data, actor="admin"):
        """Edit a source. Changing the URL or text of an approved source sends it back to draft."""
        source = self.get(source_id)
        if source.get("content_type") == STAFF_ANSWER and ({"url", "content_type"} & set(data)):
            raise SourceError("A staff answer has no URL and its content type cannot be changed")
        if source.get("dataset") and ({"url", "content_type", "text", "retrieved_at"} & set(data)):
            raise SourceError("Dataset sources are changed in usiubot_datasets and re-imported; only the "
                              "title, department, notes and date can be edited here")
        fields = self._validated(data, partial=True)
        if "url_normalized" in fields:
            self._check_unique_url(fields["url_normalized"], exclude_id=source["_id"])
        content_changed = (
            fields.get("url_normalized", source["url_normalized"]) != source["url_normalized"]
            or fields.get("text_sha256", source.get("text_sha256")) != source.get("text_sha256")
        )
        now = utcnow()
        update = {"$set": {**fields, "updated_at": now}}
        if source["status"] == "approved" and content_changed:
            update["$set"].update({"status": "draft", "approved_at": None, "approved_by": None})
            update["$push"] = {"status_history": {"status": "draft", "at": now, "by": actor,
                                                  "note": "content changed; re-approval required"}}
        self.sources.update_one({"_id": source["_id"]}, update)
        updated = self.get(source_id)
        if updated["status"] == "approved":
            self._index_source(updated)  # metadata-only edit of an approved source
        else:
            self._unindex_source(updated["_id"])
        return updated

    def set_status(self, source_id, status, actor="admin", note=""):
        status = _choice(status, "Status", STATUSES)
        source = self.get(source_id)
        if status == "approved":
            if not source.get("text"):
                raise SourceError("A source needs text content before it can be approved")
            if source.get("dataset"):
                if not self.citable(source):
                    raise SourceError("This dataset source has no citable URL or page reference "
                                      "(external sources need EXTERNAL_SOURCE_DOMAINS)")
            elif source.get("content_type") != STAFF_ANSWER:
                normalize_source_url(source["url"], self.allowed_domains)  # re-check against current allow-list
        now = utcnow()
        changes = {"status": status, "updated_at": now}
        if status == "approved":
            changes.update({"approved_at": now, "approved_by": actor})
        entry = {"status": status, "at": now, "by": actor}
        if note:
            entry["note"] = _clean_text(note, "Note", MAX_NOTES_LENGTH)
        self.sources.update_one({"_id": source["_id"]}, {"$set": changes, "$push": {"status_history": entry}})
        updated = self.get(source_id)
        if status == "approved":
            self._index_source(updated)
        else:
            self._unindex_source(updated["_id"])
        return updated

    def set_review_flags(self, source_id, flags, import_metadata=None):
        """Record review flags (and import details) found by the import tool.

        Informational only: it changes neither the status nor the index. The flags are
        shown to administrators, who must check them before approving the source.
        """
        source = self.get(source_id)
        changes = {"review_flags": [str(f) for f in flags]}
        if import_metadata is not None:
            changes["import"] = {**import_metadata, "at": utcnow()}
        self.sources.update_one({"_id": source["_id"]}, {"$set": changes})
        return self.get(source_id)

    def create_staff_answer(self, question, answer, query_id, department="general_university", actor="admin"):
        """Store an admin's answer to a logged question as a *draft* source.

        It is not searchable until an administrator approves it. Answering the same
        question again replaces the text and returns the source to draft.
        """
        text = _clean_text(f"Question: {question}\nAnswer: {answer}", "Answer", self.max_text)
        title = _clean_text("Staff answer: " + (question if len(question) <= 120 else question[:117] + "..."),
                            "Title", MAX_TITLE_LENGTH)
        key = f"staff-answer:{query_id}"
        existing = self.sources.find_one({"url_normalized": key})
        if existing:
            return self.update(str(existing["_id"]), {"text": text}, actor=actor) if existing.get("status") != "draft" \
                else self._replace_draft_text(existing, text)
        now = utcnow()
        doc = {
            "url": None,
            "url_normalized": key,
            "title": title,
            "department": _choice(department, "Department", DEPARTMENTS),
            "content_type": STAFF_ANSWER,
            "source_date": None,
            "notes": "Written by USIU staff in response to a logged question. Review before approving.",
            "text": text,
            "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "retrieved_at": now,
            "query_id": str(query_id),
            "status": "draft",
            "created_at": now,
            "updated_at": now,
            "approved_at": None,
            "approved_by": None,
            "status_history": [{"status": "draft", "at": now, "by": actor}],
        }
        doc["_id"] = self.sources.insert_one(doc).inserted_id
        return doc

    def _replace_draft_text(self, source, text):
        now = utcnow()
        self.sources.update_one({"_id": source["_id"]}, {"$set": {
            "text": text, "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "retrieved_at": now, "updated_at": now}})
        return self.get(str(source["_id"]))

    # --- dataset sources -------------------------------------------------------------
    def find_dataset_source(self, section_id):
        return self.sources.find_one({"url_normalized": DATASET_KEY_PREFIX + section_id})

    def upsert_dataset_source(self, record, actor="dataset-import", dry_run=False):
        """Create or refresh one source from a dataset section (see services/dataset_import.py).

        ``record`` holds: section_id, title, url (or None), department, category, data_origin,
        content_type, retrieved_at (datetime), notes, dataset (metadata), chunks (list of
        ``{"chunk_id", "text", ...}``) and review_flags.

        Returns ``(outcome, source_or_None)`` with outcome ``created``, ``unchanged``, ``updated``
        (metadata only), ``returned_to_draft`` (content of an approved source changed) or
        ``content_updated`` (content of a draft/rejected/archived source changed).
        Never approves anything.
        """
        if record.get("data_origin") not in DATA_ORIGINS:
            raise SourceError("Dataset records must be official or external (synthetic data is refused)")
        if record.get("is_test") and not self.settings.get("ALLOW_TEST_SOURCES"):
            raise SourceError("Test records can only be imported when the app runs in test mode")
        url = record.get("url") or None
        if url:
            domains = self.external_domains if record["data_origin"] == "external" else self.allowed_domains
            if not domains:
                raise SourceError("External sources need EXTERNAL_SOURCE_DOMAINS")
            url = normalize_source_url(url, domains)
        _choice(record.get("department"), "Department", DEPARTMENTS)
        _choice(record.get("category"), "Category", tuple(CATEGORIES))
        _choice(record.get("content_type"), "Content type", CONTENT_TYPES)
        chunks = [c for c in record.get("chunks") or [] if (c.get("text") or "").strip()]
        if not chunks:
            raise SourceError("A dataset section needs at least one passage")
        text = "\n\n".join(c["text"] for c in chunks)
        if len(text) > self.max_text:
            raise SourceError(f"Text must be at most {self.max_text} characters")
        sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
        key = DATASET_KEY_PREFIX + record["section_id"]
        fields = {
            "url": url,
            "title": _clean_text(record.get("title"), "Title", MAX_TITLE_LENGTH),
            "department": record["department"],
            "category": record["category"],
            "data_origin": record["data_origin"],
            "content_type": record["content_type"],
            "source_date": None,
            "dataset": record.get("dataset") or {},
            "dataset_chunks": chunks,
            "review_flags": list(record.get("review_flags") or []),
            "is_test": bool(record.get("is_test")),
        }
        existing = self.sources.find_one({"url_normalized": key})
        now = utcnow()
        if existing is None:
            if dry_run:
                return "created", None
            doc = {**fields, "url_normalized": key, "text": text, "text_sha256": sha,
                   "retrieved_at": record.get("retrieved_at") or now,
                   "notes": _clean_text(record.get("notes"), "Notes", MAX_NOTES_LENGTH, required=False),
                   "status": "draft", "created_at": now, "updated_at": now, "approved_at": None,
                   "approved_by": None, "status_history": [{"status": "draft", "at": now, "by": actor,
                                                            "note": "imported from the USIUBOT dataset"}]}
            doc["_id"] = self.sources.insert_one(doc).inserted_id
            return "created", doc
        # Title and department may have been corrected by an administrator: keep their edits.
        for kept in ("title", "department"):
            fields[kept] = existing.get(kept, fields[kept])
        content_changed = existing.get("text_sha256") != sha or existing.get("url") != url
        meta_changed = any(existing.get(k) != v for k, v in fields.items() if k not in ("title", "department"))
        if not content_changed and not meta_changed:
            return "unchanged", existing
        if dry_run:
            if content_changed:
                return ("returned_to_draft" if existing.get("status") == "approved" else "content_updated"), existing
            return "updated", existing
        update = {"$set": {**fields, "updated_at": now}}
        outcome = "updated"
        if content_changed:
            update["$set"].update({"text": text, "text_sha256": sha, "retrieved_at": record.get("retrieved_at") or now})
            outcome = "content_updated"
            if existing.get("status") == "approved":
                outcome = "returned_to_draft"
                update["$set"].update({"status": "draft", "approved_at": None, "approved_by": None})
                update["$push"] = {"status_history": {"status": "draft", "at": now, "by": actor,
                                                      "note": "dataset content changed; re-approval required"}}
        self.sources.update_one({"_id": existing["_id"]}, update)
        updated = self.sources.find_one({"_id": existing["_id"]})
        if updated.get("status") == "approved":
            self._index_source(updated)  # metadata (warnings, page numbers) refreshed in the index
        elif content_changed:
            self._unindex_source(updated["_id"])
        return outcome, updated

    def archive_missing_dataset_sources(self, present_section_ids, actor="dataset-import", dry_run=False):
        """Archive dataset sources whose section no longer exists in the dataset. Returns their ids."""
        keys = {DATASET_KEY_PREFIX + s for s in present_section_ids}
        gone = [s for s in self.sources.find({"dataset": {"$exists": True}, "status": {"$ne": "archived"}},
                                             {"url_normalized": 1, "is_test": 1})
                if s["url_normalized"] not in keys]
        if not dry_run:
            for s in gone:
                self.set_status(str(s["_id"]), "archived", actor=actor, note="no longer in the USIUBOT dataset")
        return [str(s["_id"]) for s in gone]

    def bulk_set_status(self, source_ids, status, actor="admin", note=""):
        """Change the status of several sources (the admin's selection). Returns a per-source report.

        Each source goes through ``set_status``, so the same checks apply (text present, citable).
        """
        if not isinstance(source_ids, list) or not source_ids:
            raise SourceError("Select at least one source")
        if len(source_ids) > BULK_STATUS_LIMIT:
            raise SourceError(f"At most {BULK_STATUS_LIMIT} sources can be changed at once")
        _choice(status, "Status", STATUSES)
        done, failed = [], []
        for source_id in dict.fromkeys(str(s) for s in source_ids):
            try:
                self.set_status(source_id, status, actor=actor, note=note)
                done.append(source_id)
            except SourceError as e:
                failed.append({"id": source_id, "error": str(e)})
        return {"changed": done, "failed": failed}

    def check_citations(self, citations):
        """Re-validate stored citations (e.g. in chat history) against the current sources.

        A citation stays linkable only while its source exists, is approved and is citable.
        Otherwise it is kept as plain text with ``available: False`` and no URL.
        """
        citations = [c for c in (citations or []) if isinstance(c, dict)]
        ids = []
        for c in citations:
            try:
                ids.append(ObjectId(c.get("source_id")))
            except Exception:
                pass
        current = {str(s["_id"]): s for s in self.sources.find({"_id": {"$in": ids}}, {"text": 0})} if ids else {}
        checked = []
        for c in citations:
            if c.get("origin") == "live":
                # Pages fetched live are not stored; the link stays only while its host is trusted.
                checker = getattr(self, "live_url_checker", None)
                ok = bool(checker and checker(c.get("url")))
                checked.append({**c, "available": ok} if ok else {**c, "url": None, "available": False})
                continue
            source = current.get(str(c.get("source_id")))
            ok = (source is not None and source.get("status") == "approved"
                  and self.citable(source) and source.get("url") == c.get("url"))
            checked.append({**c, "available": ok} if ok else {**c, "url": None, "available": False})
        return checked

    # --- index maintenance ----------------------------------------------------------
    def _index_source(self, source):
        from services.knowledge_base import split_text

        self.chunks.delete_many({"source_id": source["_id"]})
        if source.get("dataset_chunks"):
            # Dataset sections arrive already split (at most 1000 characters, heading kept with its text,
            # no sentence cut), each with its own id and page numbers: index them as they are.
            docs = [{"source_id": source["_id"], "chunk": i, "text": c["text"], "category": source.get("category"),
                     "meta": {k: c.get(k) for k in ("chunk_id", "page_start", "page_end", "section_heading")}}
                    for i, c in enumerate(source["dataset_chunks"])]
        else:
            docs = [{"source_id": source["_id"], "chunk": i, "text": text, "category": source.get("category")}
                    for i, text in enumerate(split_text(source["text"]))]
        if docs:
            self.chunks.insert_many(docs)
        self.index.invalidate()
        return len(docs)

    def _unindex_source(self, source_oid):
        self.chunks.delete_many({"source_id": source_oid})
        self.index.invalidate()

    def rebuild_index(self):
        """Re-create the search chunks of every approved source and drop chunks of anything else.

        Only the ``source_chunks`` collection is written: source records, their text and
        their approvals are never changed. A source that fails to index is reported and
        keeps its status.
        """
        approved = list(self.sources.find({"status": "approved"}))
        approved_ids = [s["_id"] for s in approved]
        removed = self.chunks.delete_many({"source_id": {"$nin": approved_ids}}).deleted_count
        chunks, failed = 0, []
        for source in approved:
            try:
                chunks += self._index_source(source)
            except Exception as e:
                logger.error("Source %s could not be indexed (%s)", source["_id"], type(e).__name__)
                failed.append({"id": str(source["_id"]), "title": source.get("title"), "error": type(e).__name__})
        self.index.invalidate()
        return {"approved_sources": len(approved), "chunks": chunks, "removed_chunks": removed, "failed": failed}

    def counts(self):
        counts = {s: 0 for s in STATUSES}
        for row in self.sources.aggregate([{"$group": {"_id": "$status", "n": {"$sum": 1}}}]):
            if row["_id"] in counts:
                counts[row["_id"]] = row["n"]
        return counts

    # --- retrieval ------------------------------------------------------------------
    def retrieve(self, query, k=5, min_score=0.0, min_coverage=0.0, max_chunks_per_source=2, categories=None,
                 prefer_department=None):
        """Return approved sources relevant to ``query``, best first.

        Each result is ``{"source": <source doc without text>, "chunks": [text, ...],
        "relevance": float, "score": float, "stale": bool}``. ``relevance`` is the
        BM25 score of the source's best chunk; ``score`` is the ranking score:
        ``relevance``, multiplied by ``SOURCE_STALE_PENALTY`` (default 0.85) when the
        source is out of date. So a current source outranks a stale one of comparable
        relevance, but a clearly more relevant stale source still comes first, and the
        dates of two current sources play no part. Equal scores are ordered newest
        source first, then by id, so the order is deterministic. Stale sources are
        kept (not dropped), so the stale and conflict warnings still apply.

        Approval is re-checked against the ``sources`` collection, so a source that
        was archived a moment ago is never returned even if the cache is stale.

        ``prefer_department`` (the department the question is about, from the routing
        classifier) multiplies the score of that department's sources by
        ``SOURCE_DEPARTMENT_BOOST`` (default 1.5), so that with many approved sources a
        specific page of the right office outranks pages elsewhere that merely share a
        word. Other sources are still returned; 1.0 turns the preference off.
        """
        boost = float(self.settings.get("SOURCE_DEPARTMENT_BOOST", 1.5)) if prefer_department else 1.0
        pool = k * 5 if boost != 1.0 else k * 3
        hits = self.index.search(query, k=pool, min_score=min_score, min_coverage=min_coverage,
                                 categories=categories, per_part=max_chunks_per_source)
        if not hits:
            return []
        ids = list({chunk["source_id"] for chunk, _ in hits})
        approved = {
            s["_id"]: s for s in self.sources.find({"_id": {"$in": ids}, "status": "approved"},
                                                   {"text": 0, "dataset_chunks": 0})
        }
        stale_days = self.settings.get("SOURCE_STALE_DAYS", 365)
        penalty = self.settings.get("SOURCE_STALE_PENALTY", 0.85)
        results, by_source = [], {}
        for chunk, score in hits:  # best chunk first
            source = approved.get(chunk["source_id"])
            if source is None or not self._retrievable(source):
                continue
            entry = by_source.get(source["_id"])
            if entry is None:
                stale = is_stale(source, stale_days)
                factor = (penalty if stale else 1.0) * (boost if source.get("department") == prefer_department else 1.0)
                entry = {"source": source, "chunks": [], "chunk_meta": [], "relevance": score, "stale": stale,
                         "score": score * factor, "_factor": factor, "_parts": {}}
                by_source[source["_id"]] = entry
                results.append(entry)
            for index, part_score in (chunk.get("part_scores") or {}).items():
                entry["_parts"][index] = max(entry["_parts"].get(index, 0.0), part_score * entry["_factor"])
            if len(entry["chunks"]) < max_chunks_per_source:
                entry["chunks"].append(chunk["text"])
                entry["chunk_meta"].append(chunk.get("meta") or {})
        results.sort(key=lambda e: (-e["score"], -_date_rank(e["source"]), str(e["source"]["_id"])))
        selected = self._cover_question_parts(results, k, float(self.settings.get("SOURCE_RELATIVE_MIN_SCORE", 0.3)))
        for entry in results:
            entry.pop("_parts", None)
            entry.pop("_factor", None)
        self._use_full_sections(selected)
        selected += self._page_siblings(selected, results)
        return selected

    def _page_siblings(self, selected, ranked):
        """Other approved sections of the same official page that also matched the question.

        Dataset sources are page *sections* ("Admission Requirements > Kenyan Applicants"). When a page
        is chosen, its other matching sections usually hold the rest of the answer (the programme list
        next to the programme overview, the KCSE grade next to the general requirements), so they are
        added, best first, while the whole context stays within ``SOURCE_CONTEXT_MAX_CHARS``. Each keeps
        its own citation number.
        """
        budget = self.settings.get("SOURCE_CONTEXT_MAX_CHARS", 16000)
        if not budget:
            return []
        used = sum(len(c) for entry in selected for c in entry["chunks"])
        urls = {entry["source"].get("url") for entry in selected if entry["source"].get("url")}
        # Only sections nearly as relevant as the best source: a page with 60 sections (the library page)
        # must not fill the context with every section that shares one word with the question.
        floor = float(self.settings.get("SOURCE_SIBLING_MIN_RELATIVE", 0.5)) * max(
            (entry["score"] for entry in selected), default=0.0)
        candidates = [entry for entry in ranked if entry["source"].get("url") in urls
                      and entry["score"] >= floor and not any(entry is s for s in selected)]
        self._use_full_sections(candidates)
        extra = []
        for entry in candidates:  # already in ranking order
            size = sum(len(c) for c in entry["chunks"])
            if used + size <= budget:
                extra.append(entry)
                used += size
        return extra

    def _use_full_sections(self, results):
        """Give the model the whole approved section when it is short enough.

        Only the best ``max_chunks_per_source`` passages of a source are kept by the search, which cut
        lists in half (the undergraduate programme list is six passages, so only about 8 of 19
        programmes reached the model). Sections up to ``SOURCE_FULL_SECTION_CHARS`` characters
        (0 = off) are therefore passed whole. Page references then come from the section.
        """
        limit = self.settings.get("SOURCE_FULL_SECTION_CHARS", 6000)
        if not limit or not results:
            return
        ids = [entry["source"]["_id"] for entry in results]
        texts = {s["_id"]: s.get("text") or "" for s in self.sources.find(
            {"_id": {"$in": ids}, "status": "approved"}, {"text": 1})}
        for entry in results:
            text = texts.get(entry["source"]["_id"], "")
            if text and len(text) <= limit and len(text) > sum(len(c) for c in entry["chunks"]):
                entry["chunks"] = [text]
                entry["chunk_meta"] = []

    @staticmethod
    def _cover_question_parts(results, k, min_relative=0.0):
        """Pick up to ``k`` of the ranked ``results`` so that every part of a multi-part question is covered.

        The best source for each part of the question (part 0 is the whole question) is taken first,
        strongest parts first, then the remaining places are filled in ranking order with sources scoring
        at least ``min_relative`` times the best score (weak matches only take context away from the
        model). The returned list keeps the ranking order.
        """
        floor = min_relative * max((entry.get("score", 0.0) for entry in results), default=0.0)
        part_ids = sorted({index for entry in results for index in entry["_parts"] if index > 0})
        if not part_ids:
            return [entry for entry in results[:k] if entry.get("score", 0.0) >= floor]
        best_per_part = []
        for index in part_ids:
            candidates = [entry for entry in results if index in entry["_parts"]]
            best = max(candidates, key=lambda entry: entry["_parts"][index])  # ties: earlier (better) rank wins
            best_per_part.append((best["_parts"][index], best))
        chosen = []
        for _, entry in sorted(best_per_part, key=lambda item: item[0], reverse=True):
            if len(chosen) < k and not any(entry is c for c in chosen):
                chosen.append(entry)
        for entry in results:
            if len(chosen) >= k:
                break
            if entry.get("score", 0.0) >= floor and not any(entry is c for c in chosen):
                chosen.append(entry)
        return [entry for entry in results if any(entry is c for c in chosen)]


def serialize_source(source, include_text=False, stale_days=365):
    data = {
        "id": str(source["_id"]),
        "url": source.get("url"),
        "title": source.get("title"),
        "department": source.get("department"),
        "content_type": source.get("content_type"),
        "status": source.get("status"),
        "source_date": source.get("source_date"),
        "retrieved_at": as_utc(source["retrieved_at"]).isoformat() if source.get("retrieved_at") else None,
        "approved_at": as_utc(source["approved_at"]).isoformat() if source.get("approved_at") else None,
        "approved_by": source.get("approved_by"),
        "updated_at": as_utc(source["updated_at"]).isoformat() if source.get("updated_at") else None,
        "notes": source.get("notes", ""),
        "has_text": bool(source.get("text_sha256")),
        "stale": is_stale(source, stale_days),
        "review_flags": list(source.get("review_flags", [])),
        "category": source.get("category"),
        "data_origin": source.get("data_origin", "official"),
        "from_dataset": bool(source.get("dataset")),
    }
    dataset = source.get("dataset") or {}
    if dataset:
        data["dataset"] = {k: dataset.get(k) for k in (
            "section_id", "document_id", "document_title", "document_file", "page_start", "page_end",
            "section_heading", "publisher", "collected_at", "publication_date", "academic_year", "content_fidelity",
            "issues", "verification_status")}
        data["passage_count"] = len(source.get("dataset_chunks") or [])
    if include_text:
        data["text"] = source.get("text", "")
        data["status_history"] = [
            {**h, "at": as_utc(h["at"]).isoformat()} for h in source.get("status_history", [])
        ]
    return data
