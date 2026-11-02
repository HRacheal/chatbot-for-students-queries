"""Enquiry classification and department routing (routing agent).

Deterministic keyword scoring, so routing works without a language model and is easy
to explain to staff. The user can always correct the suggested department.
"""

import re

from services.sources import tokenize

from services.sources import DEPARTMENT_LABELS, DEPARTMENTS, LOW_SIGNAL_TERMS

# Enquiry departments are the source departments (Finance is separate from Admissions).
# Staff delivery addresses and published contacts are configured by administrators
# (admin Routing tab, services/department_routing.py); none are hard-coded.
ENQUIRY_DEPARTMENTS = DEPARTMENTS
ENQUIRY_DEPARTMENT_LABELS = dict(DEPARTMENT_LABELS)

# Each department: single words (matched after tokenising, so synonyms and word forms count) and
# phrases (matched as whole phrases). Words that belong to several offices on their own ("day",
# "open", "school", "office") are only listed inside a phrase ("open day"), so "What time does the
# library open?" is not routed to Marketing.
_KEYWORDS = {
    "admissions": (
        """admission admissions admit admitted apply applying application applicant applicants intake intakes
        entry requirement requirements qualify qualification kcse igcse ib diploma prospective join joining
        scholarship scholarships bursary undergraduate postgraduate masters doctoral phd readmission
        international visa orientation cutoff kuccps""",
        ["financial aid", "offer letter", "cut off", "cut-off points", "transfer student", "transfer admission",
         "pupil's pass", "student pass"]),
    "finance": (
        """fee fees tuition cost costs payment payments pay paying paid invoice balance statement deposit
        refund refunds paybill mpesa swift receipt receipts installment installments arrears penalty billing
        finance bursar caution interest waiver hold""",
        ["bank account", "m-pesa", "caution money", "payment plan", "deferred payment", "financial clearance",
         "financial hold", "charge waiver", "3pay"]),
    "registrar": (
        """registrar registration register transcript transcripts exam exams examination examinations result
        results grade grades gpa marks graduation commencement certificate certificates calendar semester
        timetable schedule deferment withdraw withdrawal clearance verification probation dismissal appeal
        id card add/drop""",
        ["academic record", "academic records", "leave of absence", "add/drop", "credit transfer",
         "degree certificate", "late registration", "enrollment verification", "student records"]),
    "marketing": (
        """marketing brochure brochures prospectus press advert advertising advertisement brand logo
        publication publications partnership partnerships collaboration outreach exhibition sponsor sponsorship""",
        ["open day", "campus tour", "school visit", "social media", "education fair", "media enquiry"]),
    "academic_programmes": (
        """programme programmes program programs degree degrees major majors minor minors curriculum syllabus
        bachelor bachelors bsc msc mba catalog concentration specialisation specialization accreditation
        accredited elective electives prerequisite prerequisites doctorate online""",
        ["academic catalog", "course duration", "short course", "short courses"]),
    "student_affairs": (
        """hostel hostels accommodation housing counseling counselor clinic health medical dental wellness
        club clubs society societies discipline conduct disability chaplain chaplaincy sport sports gym
        emergency stress""",
        ["student affairs", "dean of students", "student council", "student life", "residence hall"]),
    "ict": (
        """ict wifi password portal login helpdesk computer computers lab labs blackboard moodle network
        printing""",
        ["e-learning", "it helpdesk", "student email", "office365", "office 365", "computer lab"]),
    "library": (
        """library libraries librarian book books borrow borrowing journal journals e-resources database
        databases loan loans overdue interlibrary""",
        ["e-resources"]),
    "general_university": (
        """contact location cafeteria dining parking transport shuttle security history mission vision chancellor
        leadership founded facility facilities career careers internship internships cv job jobs
        employment""",
        ["about usiu", "where is usiu", "placement and careers", "career services"]),
}
_TERMS = {dept: set(tokenize(words)) - LOW_SIGNAL_TERMS for dept, (words, _) in _KEYWORDS.items()}
_PHRASES = {dept: [re.compile(r"(?<![a-z0-9])" + r"\W+".join(map(re.escape, re.findall(r"[a-z0-9]+", p.lower())))
                              + r"(?![a-z0-9])") for p in phrases]
            for dept, (_, phrases) in _KEYWORDS.items()}

GUIDANCE_RE = re.compile(
    r"\b(which|what|recommend|suggest|suitable|best|qualify|eligible|should)\b.{0,60}"
    r"\b(course|courses|degree|degrees|programme|programmes|program|programs|major)\b"
    r"|\bresults?\s+slip\b|\bwith\s+(a|an|my)\s+(mean\s+grade|[a-e][+-]?)(?![a-z])",
    re.IGNORECASE,
)
PERSONAL_RE = re.compile(r"\b(i|me|my|mine|i'm|im)\b", re.IGNORECASE)


_OFFICE_NAMES = frozenset(tokenize("registrar admissions finance bursar library librarian ict helpdesk"))
_WEAK_CONCEPTS = frozenset(tokenize("contact location"))


def _term_weight(term):
    if term in _OFFICE_NAMES:
        return 3
    if term.startswith("concept") and term not in _WEAK_CONCEPTS:
        return 2
    return 1


def classify_department(text, hints=()):
    """Return ``(department or None, scores)``. ``None`` means the user should choose.

    ``hints`` are the departments of the sources retrieved for the question, best first. They decide
    a tie between departments, or the department when no keyword matched (e.g. "What is the caution
    money for day students?" finds the Finance fee schedule).
    """
    # Words found in almost every university question ("student", "campus") do not indicate a department.
    tokens = [t for t in tokenize(text) if t not in LOW_SIGNAL_TERMS]
    lowered = (text or "").lower()
    # Concept tokens (e.g. every way of saying "registration") and phrases are stronger signals than words;
    # the name of an office ("Registrar", "ICT helpdesk") is the strongest. "Contact" says what kind of
    # answer is wanted, not which office, so it counts as an ordinary word.
    scores = {dept: sum(_term_weight(t) for t in tokens if t in terms)
              + sum(2 for pattern in _PHRASES[dept] if pattern.search(lowered))
              for dept, terms in _TERMS.items()}
    best = max(scores.values()) if scores else 0
    hints = [h for h in hints if h in scores]
    if best == 0:
        return (hints[0] if hints else None), scores
    leaders = [d for d, s in scores.items() if s == best]
    if len(leaders) == 1:
        return leaders[0], scores
    return next((h for h in hints if h in leaders), None), scores


def is_guidance_request(text):
    """Personal questions about which programme suits the user ("which course can I do with a C+?").

    Used only to *offer* the degree-guidance tool next to the normal answer.
    """
    text = text or ""
    return bool(GUIDANCE_RE.search(text) and PERSONAL_RE.search(text))
