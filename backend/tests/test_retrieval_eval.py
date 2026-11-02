"""Retrieval evaluation on a small SYNTHETIC corpus (not USIU-Africa information).

Each question has an expected outcome:
* a source slug: that source must be the *first* citation;
* "unanswered": no source should match and the question must be logged for staff;
* "out_of_scope": refused (with no model configured it is still logged as "unclear").

Some questions also list sources that must be cited after the first one (e.g. the
outdated version of a source, so the stale/conflict warnings can still apply, or the
second part of a two-part question).

No language model is configured, so answered questions come back as "sources_only"
(real retrieval and citations, no generated text).
"""

import pytest

from config.database import db_instance
from tests.conftest import add_source

LABEL = "SYNTHETIC TEST TEXT, NOT USIU-AFRICA INFORMATION. "
CORPUS = {
    "fees": ("admissions", "2026-03", "Synthetic fee schedule",
             "Tuition fees are charged per credit unit each semester. Fees must be paid before "
             "registration. Late payment attracts an interest charge."),
    "registration": ("registrar", "2026-08", "Synthetic registration procedures",
                     "Course registration is done online on the student portal during the registration week of "
                     "each semester. Students who missed a semester must obtain clearance from the Registrar "
                     "before registering."),
    "transcripts": ("registrar", "2026-05", "Synthetic transcript requests",
                    "Official transcripts are requested from the Registrar in writing and signed by the student. "
                    "Transcripts are processed within two working days after payment is confirmed."),
    "housing": ("general_university", "2026-01", "Synthetic campus housing",
                "On-campus accommodation is available in student hostels. Rooms are shared by two students. "
                "Apply for a room using the housing application form."),
    "deferment": ("admissions", "2026-02", "Synthetic admission deferment",
                  "Admitted applicants may request to defer their admission for up to one academic year by "
                  "writing to the Admissions Office."),
    "scholarship-old": ("admissions", "2022", "Synthetic scholarship guide 2022",
                        "The merit scholarship covers fifty percent of tuition for students with excellent grades."),
    "scholarship-new": ("admissions", "2026-06", "Synthetic scholarship guide 2026",
                        "The merit scholarship covers thirty percent of tuition for students with excellent grades."),
    "clubs": ("marketing", "2026-04", "Synthetic student life",
              "Students can join clubs, sports teams and cultural societies. Club fairs are held at the start "
              "of each semester."),
}

CASES = [
    # (question, expected first, also cited, kind)
    ("How are tuition fees charged?", "fees", (), "same wording"),
    ("When must fees be paid?", "fees", (), "same wording"),
    ("How much does it cost to study per semester?", "fees", (), "synonym: cost"),
    ("What is the price of tuition?", "fees", (), "synonym: price"),
    ("How do I register for courses?", "registration", (), "word form"),
    ("How do I sign up for classes?", "registration", (), "synonym: sign up"),
    ("How do I enrol for next semester?", "registration", (), "synonym: enrol"),
    ("I missed a semester, what do I do before registering?", "registration", (), "partial wording"),
    ("How do I request an official transcript?", "transcripts", (), "same wording"),
    ("How can I get a copy of my academic record?", "transcripts", (), "synonym: academic record"),
    ("How long does transcript processing take?", "transcripts", (), "word form"),
    ("Can I get a transcript showing my results?", "transcripts", (), "'transcript' named explicitly"),
    ("Is there on-campus accommodation?", "housing", (), "same wording"),
    ("Where can I live while studying? Are there dorms?", "housing", (), "synonym: dorm / where can I live"),
    ("How many students share a hostel room?", "housing", (), "partial wording"),
    ("Can I defer my admission?", "deferment", (), "same wording"),
    ("Can I postpone starting my studies by a year?", "deferment", (), "synonym: postpone"),
    ("Can I start next year instead of this year?", "deferment", (), "phrase: start next year"),
    # Two versions of the same guide with comparable relevance: the current one ranks
    # first, the outdated one is still cited (so the stale warning applies).
    ("What does the merit scholarship cover?", "scholarship-new", ("scholarship-old",), "current vs stale"),
    ("Does the university offer financial help for good students?", "scholarship-new", ("scholarship-old",),
     "synonym: financial help; current vs stale"),
    ("How much of my tuition does the scholarship pay?", "scholarship-new", ("scholarship-old",),
     "two concepts; current vs stale"),
    ("Which clubs can I join?", "clubs", (), "same wording"),
    # Accommodation is the subject of the question; both concepts must be cited.
    ("What does a dorm cost?", "housing", ("fees",), "ambiguous: two concepts"),
    ("When must fees be paid and can I defer my admission?", "fees", ("deferment",), "two-part question"),
    ("What are the requirements?", "unanswered", (), "ambiguous, no matching source"),
    ("Is there a gym on campus?", "unanswered", (), "university topic, no source"),
    ("What time does the swimming pool close?", "unanswered", (), "facility, no source"),
    # "results" alone is not a transcript enquiry.
    ("When are exam results released?", "unanswered", (), "'results' is not 'transcript'"),
    ("Where can I see my KCSE results?", "unanswered", (), "'results' is not 'transcript'"),
    ("Who won the football world cup?", "out_of_scope", (), "unrelated"),
    ("Write a python script to sort a list", "out_of_scope", (), "unrelated"),
    ("Can you recommend a good restaurant?", "out_of_scope", (), "unrelated"),
    # A place name alone does not make a question about the university.
    ("What is the weather in Nairobi today?", "out_of_scope", (), "unrelated but contains a place name"),
    ("Can you recommend a hotel in Nairobi?", "out_of_scope", (), "unrelated but contains a place name"),
    ("How far is Thika from Kasarani?", "out_of_scope", (), "unrelated, only place names"),
    ("Is there a shuttle from Nairobi to the campus?", "unanswered", (), "place name plus university words"),
    ("How do I get to USIU from Nairobi CBD?", "unanswered", (), "place name plus the university's name"),
]


@pytest.fixture
def corpus(registry):
    for slug, (department, date, title, text) in CORPUS.items():
        add_source(registry, url=f"https://www.usiu.ac.ke/synthetic-test/{slug}/", title=title,
                   department=department, source_date=date, text=LABEL + text)


def slug(citation):
    return citation["url"].rstrip("/").rsplit("/", 1)[-1]


def outcome(body):
    if body["status"] == "sources_only" and body["citations"]:
        return slug(body["citations"][0])
    return body["status"]


@pytest.mark.parametrize("question,expected,also,kind", CASES, ids=[q for q, _, _, _ in CASES])
def test_retrieval_case(client, corpus, question, expected, also, kind):
    body = client.post("/api/query", json={"question": question}).get_json()
    got = outcome(body)
    ranked = [slug(c) for c in body["citations"]]
    if kind == "two-part question":
        # Each part must find its own source; which part's source is listed first does not matter.
        assert set(ranked[:1 + len(also)]) == {expected, *also}, f"{kind}: got {ranked}"
        return
    assert got == expected, f"{kind}: expected {expected} first, got {got} (ranking {ranked})"
    for other in also:
        assert other in ranked[1:], f"{kind}: expected {other} to be cited too, got {ranked}"
    logged = db_instance.get_collection("queries").find_one({"question": question})
    if got == "unanswered":
        assert logged and logged["scope"] == "usiu"
    if got == "out_of_scope":
        # No model is configured, so the scope can't be confirmed; the question is kept for review.
        assert logged and logged["scope"] == "unclear"


def test_draft_and_archived_sources_never_appear(client, registry, corpus):
    draft = add_source(registry, approve=False, url="https://www.usiu.ac.ke/synthetic-test/parking/",
                       title="Synthetic parking", text=LABEL + "Visitor parking permits are issued at the gate.")
    body = client.post("/api/query", json={"question": "How do I get a visitor parking permit?"}).get_json()
    assert body["citations"] == []
    registry.set_status(str(draft["_id"]), "approved")
    body = client.post("/api/query", json={"question": "How do I get a visitor parking permit?"}).get_json()
    assert outcome(body) == "parking"
    registry.set_status(str(draft["_id"]), "archived")
    body = client.post("/api/query", json={"question": "How do I get a visitor parking permit?"}).get_json()
    assert body["citations"] == []


def test_stale_version_is_flagged_when_both_versions_are_retrieved(client, corpus):
    body = client.post("/api/query", json={"question": "What does the merit scholarship cover?"}).get_json()
    assert [(c["title"], c["stale"]) for c in body["citations"]] == [
        ("Synthetic scholarship guide 2026", False), ("Synthetic scholarship guide 2022", True)]
    assert any(w["type"] == "stale" for w in body["warnings"])


def test_exam_results_source_outranks_transcripts_for_an_exam_results_question(client, registry, corpus):
    add_source(registry, url="https://www.usiu.ac.ke/synthetic-test/exam-results/", title="Synthetic exam results",
               department="registrar", source_date="2026-07",
               text=LABEL + "End of semester exam results are released on the student portal two weeks "
                            "after the last examination.")
    body = client.post("/api/query", json={"question": "When are exam results released?"}).get_json()
    assert [slug(c) for c in body["citations"]] == ["exam-results"]
