"""Question understanding, ranking, routing and fallback honesty (2026-11-02 chatbot improvement).

All source texts here are SYNTHETIC TEST TEXT, not USIU-Africa information.
"""

import pytest

from services import chat_service as cs
from services.routing import classify_department
from services.sources import question_intents, tokenize
from tests.conftest import add_source

LABEL = "SYNTHETIC TEST TEXT, NOT USIU-AFRICA INFORMATION. "
SITE = "https://www.usiu.ac.ke/synthetic-understanding/"


def add(registry, slug, title, text, department="registrar"):
    return add_source(registry, url=SITE + slug + "/", title=title, department=department, text=LABEL + text)


def titles(results):
    return [r["source"]["title"] for r in results]


def retrieve(registry, question, department=None, k=4):
    return registry.retrieve(question, k=k, min_score=0.5, min_coverage=0.5, prefer_department=department)


# --- Preprocessing --------------------------------------------------------------------------------
def test_filler_words_are_not_key_terms():
    tokens = tokenize("Hello! I am a current student. Please guide me through the process for the upcoming semester")
    for filler in ("am", "current", "guide", "through", "process", "upcom"):
        assert filler not in tokens
    assert "semest" in tokens


@pytest.mark.parametrize("phrasing, concept", [
    ("I stopped studying for a while. How do I come back to USIU?", "conceptreadmission"),
    ("Can I resume my studies?", "conceptreadmission"),
    ("Which days is the dentist in?", "conceptdental"),
    ("is there wifi?", "conceptwifi"),
    ("Is wireless internet available?", "conceptwifi"),
    ("What is the process for selecting my units?", "conceptregistration"),
    ("How do I drop a course?", "conceptadddrop"),
    ("I lost my student ID", "conceptidcard"),
    ("What happens if I have a financial hold?", "concepthold"),
    ("The library doesn't have a book I need", "conceptinterlibrary"),
    ("When is the graduation ceremony?", "conceptgraduation"),
])
def test_different_wordings_share_one_concept(phrasing, concept):
    assert concept in tokenize(phrasing)


def test_british_and_american_spellings_match():
    assert tokenize("counselling counsellor instalment") == tokenize("counseling counselor installment")


@pytest.mark.parametrize("question, kind", [
    ("How do I register for my courses?", "procedure"),
    ("What are the steps to apply?", "procedure"),
    ("When does online registration close?", "deadline"),
    ("What is the last day to drop a course?", "deadline"),
    ("How much is the late registration fee?", "fees"),
    ("What are the entry requirements for the MBA?", "requirements"),
    ("What is the Registrar's email address?", "contact"),
    ("What time does the library open on Saturday?", "schedule"),
])
def test_question_intents(question, kind):
    assert kind in question_intents(question)


# --- Retrieval ------------------------------------------------------------------------------------
def test_section_heading_is_searchable_even_if_the_text_does_not_repeat_it(registry):
    add(registry, "services", "Handbook - 4.3 Services offered by the Registrar",
        "1. Processing of official transcripts. 2. Enrollment verification. 3. Graduation clearance.")
    add(registry, "other", "Handbook - Library rules", "Books must be returned on time to the library desk.",
        department="library")
    assert titles(retrieve(registry, "What services does the Registrar provide?"))[0].endswith("by the Registrar")


def test_misspelt_words_are_corrected_against_the_approved_sources(registry):
    add(registry, "calendar", "Synthetic calendar",
        "Online registration continues through 22 January. Accommodation opens on 5 January.")
    add(registry, "other", "Synthetic library rules", "Books are borrowed at the library desk.", department="library")
    index = registry.index
    assert index.correct_spelling("wen does onlin registrashun close") == "wen does onlin registration close"
    assert index.correct_spelling("accomodation") == "accommodation"
    # Short words are never "corrected" into a different word.
    assert index.correct_spelling("hotel") == "hotel"
    assert titles(retrieve(registry, "when does registrashun close"))[0] == "Synthetic calendar"


def test_an_unknown_word_does_not_hide_the_matching_source(registry):
    add(registry, "fees", "Synthetic fee schedule", "The late registration fee is charged per semester.",
        department="finance")
    assert titles(retrieve(registry, "How much is the late registration fee quidditch?")) == ["Synthetic fee schedule"]
    # But a question made only of unknown words matches nothing.
    assert retrieve(registry, "quidditch broomstick tournament") == []


def test_the_passage_with_the_kind_of_answer_asked_for_ranks_first(registry):
    add(registry, "steps", "Synthetic registration procedure",
        "Course registration:\n1. Log in to the student portal.\n2. Select your courses.\n3. Submit the form.")
    add(registry, "dates", "Synthetic registration dates",
        "Course registration opens on January 5 and the last day of course registration is January 22.")
    assert titles(retrieve(registry, "How do I register for my courses?"))[0] == "Synthetic registration procedure"
    assert titles(retrieve(registry, "When is the last day of course registration?"))[0] == "Synthetic registration dates"


# --- Routing --------------------------------------------------------------------------------------
@pytest.mark.parametrize("question, department", [
    ("What time does the library open on Saturday?", "library"),       # not Marketing ("open day")
    ("What is the caution money for day students?", "finance"),
    ("What happens if I have a financial hold?", "finance"),
    ("Which days is the dentist available at the clinic?", "student_affairs"),
    ("What career support does the university offer?", "general_university"),
    ("What is the Registrar's email address?", "registrar"),            # office name beats "email"
    ("How do I contact the ICT helpdesk?", "ict"),
    ("I stopped studying for a while. How do I come back to USIU?", "admissions"),
])
def test_department_routing(question, department):
    assert classify_department(question)[0] == department


def test_retrieved_sources_decide_a_tie():
    question = "What are the hostel fees?"  # Student Affairs (hostel) and Finance (fees) score the same
    assert classify_department(question)[0] is None
    assert classify_department(question, hints=["finance", "student_affairs"])[0] == "finance"
    assert classify_department(question, hints=["library", "student_affairs"])[0] == "student_affairs"
    assert classify_department("How do I drop a course, and will I get a refund?")[0] == "registrar"
    assert classify_department("Is it far?", hints=["general_university"])[0] == "general_university"


# --- Fallback honesty -----------------------------------------------------------------------------
def test_no_staff_follow_up_is_promised_when_no_staff_can_see_the_question(client, app, monkeypatch, fake_llm):
    monkeypatch.setitem(app.config, "ADMIN_EMAIL", None)
    fake_llm.answer = "I do not know."
    body = client.post("/api/query", json={"question": "How do I request an official transcript?"}).get_json()
    assert body["status"] == "unanswered"
    assert body["enquiry"]["staff_review"] is False and body["enquiry"]["available"] is False
    assert "no USIU staff member reviews USIUBOT questions yet" in body["answer"]
    assert "follow up with you" not in body["answer"]


def test_staff_follow_up_is_offered_when_an_administrator_exists(client, fake_llm):
    fake_llm.answer = "I do not know."
    body = client.post("/api/query", json={"question": "How do I request an official transcript?"}).get_json()
    assert body["enquiry"]["staff_review"] is True and body["enquiry"]["available"] is True
    assert body["answer"].endswith(cs.FOLLOW_UP_STAFF)


def test_uncited_statements_are_detected():
    answer = ("**Registering**\n1. Log in to the student portal with your username [1].\n"
              "2. Add the courses you wish to take using the portal interface.\n"
              "3. Review your selected courses, then submit the registration.\n"
              "| Semester | Date |\n" + cs.PARTIAL_MARKER + " the full registration procedure is not in the sources.")
    assert cs.uncited_statements(answer) == [
        "Add the courses you wish to take using the portal interface",
        "Review your selected courses, then submit the registration"]
    assert cs.uncited_statements("Fees are paid per semester before registration [1][2].") == []
    # One source, cited once after the whole list: every statement comes from it.
    assert cs.uncited_statements("1. Provide a police abstract for the lost certificate.\n"
                                 "2. Complete the degree replacement form and pay the replacement fee.\n\n[1]") == []
    # A citation line after each block covers that block; the uncovered part is not a claim.
    assert cs.uncited_statements("* Report the loss of the card to the campus security office.\n [1]\n"
                                 "* The fixed replacement fee is two thousand shillings, paid at Finance.\n [3]\n"
                                 + cs.PARTIAL_MARKER + "\nThe sources do not give a detailed step-by-step procedure.") == []


def test_an_answer_without_markers_cites_only_the_sources_it_uses():
    results = [{"source": {"title": "hold"}, "chunks": ["Students with outstanding fees are placed on financial hold, "
                                                        "which blocks access to grades and registration."]},
               {"source": {"title": "parking"}, "chunks": ["Parking stickers are issued at the main gate."]},
               {"source": {"title": "accreditation"}, "chunks": ["The university is accredited in Kenya and the USA."]}]
    answer = "A financial hold blocks access to your grades and registration while fees are outstanding."
    assert cs.ChatService._sources_used(answer, results) == [1]
    # An answer that shares no key word with any source still lists them all.
    assert cs.ChatService._sources_used("Okay.", results) == [1, 2, 3]


def test_long_question_still_suggests_the_matching_official_page(app):
    catalogue = app.extensions["chat_service"].catalogue
    question = ("Hello! I am a current student at USIU-Africa. How do I register for my courses for the "
                "upcoming semester? Please guide me through the process.")
    assert [m["title"] for m in catalogue.match(question, min_coverage=0.5)][:1] == ["Registration Policies and Procedures"]
