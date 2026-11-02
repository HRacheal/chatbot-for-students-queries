"""Partial answers, grouped citations and whole-section context (fixes from the 2026-11-02 investigation)."""

from config.database import db_instance
from services import chat_service as cs
from tests.conftest import add_source


def ask(client, question):
    response = client.post("/api/query", json={"question": question})
    return response.get_json()


def unanswered():
    return list(db_instance.get_collection("queries").find({"answered": False}))


# --- Partial answers ------------------------------------------------------------------------------
def test_partly_answered_question_keeps_the_verified_part_and_offers_follow_up(client, fake_llm):
    fake_llm.answer = ("Applications are submitted online through the applicant portal [1].\n"
                       "Not covered by the sources: the application deadline.")
    body = ask(client, "How are applications submitted and what is the application deadline?")
    assert body["status"] == "answered"
    assert body["verified"] is True
    assert body["partial"] is True
    assert "applicant portal" in body["answer"]
    assert [c["title"] for c in body["citations"]] == ["TEST FIXTURE: How to Apply"]
    # The uncovered part is recorded for the right department, with a follow-up offer.
    assert body["enquiry"]["available"] is True
    assert body["enquiry"]["suggested_department"] == "admissions"
    logged = unanswered()
    assert len(logged) == 1 and str(logged[0]["_id"]) == body["enquiry"]["query_id"]


def test_cited_answer_mentioning_missing_detail_is_not_discarded(client, fake_llm):
    # Before the fix, any "no information" phrase anywhere replaced the whole answer with "could not verify".
    fake_llm.answer = ("Applications are submitted online through the applicant portal, and each programme "
                       "lists its entry requirements [1]. There is no information about the application fee.")
    body = ask(client, "How are applications submitted and how much is the application fee?")
    assert body["status"] == "answered"
    assert body["partial"] is True
    assert body["citations"]


def test_complete_answer_is_not_marked_partial_and_logs_nothing(client, fake_llm):
    fake_llm.answer = "Applications are submitted online through the applicant portal [1]."
    body = ask(client, "How are applications submitted?")
    assert body["status"] == "answered"
    assert "partial" not in body and "enquiry" not in body
    assert unanswered() == []


def test_cited_one_line_refusal_is_still_a_refusal(client, fake_llm):
    fake_llm.answer = "The sources do not contain information about this [1]."
    body = ask(client, "How are applications submitted?")
    assert body["status"] == "unanswered"
    assert body["citations"] == []


def test_is_no_answer_rules():
    assert cs.ChatService.is_no_answer("")
    assert cs.ChatService.is_no_answer("I do not know.")
    assert cs.ChatService.is_no_answer("I don't know [1].")
    assert not cs.ChatService.is_no_answer("Registration opens online before each semester [2].")
    long_partial = ("Registration opens online before each semester, and students request an official transcript "
                    "from the Registrar in writing [2]. Not covered by the sources: the registration deadline.")
    assert not cs.ChatService.is_no_answer(long_partial)
    assert cs.ChatService.is_partial(long_partial)


def test_system_prompt_allows_partial_answers_and_combining_sources():
    assert cs.PARTIAL_MARKER in cs.SYSTEM_PROMPT
    assert "Combine information from several sources" in cs.SYSTEM_PROMPT
    assert "reply exactly: I do not know" in cs.SYSTEM_PROMPT  # nothing relevant -> still a refusal


# --- Grouped citation markers -----------------------------------------------------------------------
def test_grouped_citation_markers_are_split():
    assert cs.normalise_citation_markers("Fees are paid [1, 2] and [3,4].") == "Fees are paid [1][2] and [3][4]."
    assert cs.normalise_citation_markers("See 【1，2】") == "See [1][2]"
    assert cs.normalise_citation_markers("KES 3,500 [1]") == "KES 3,500 [1]"


def test_grouped_citation_cites_every_listed_source(client, fake_llm):
    fake_llm.answer = "Applications are online and registration opens before each semester [1, 2]."
    body = ask(client, "How are applications submitted and when does registration open?")
    assert body["status"] == "answered"
    assert len(body["citations"]) == 2
    assert "[1][2]" in body["answer"]


# --- Whole sections reach the model ---------------------------------------------------------------------
LONG_LIST = "TEST FIXTURE. Undergraduate programme list. " + " ".join(
    f"Programme number {i}: Bachelor of Science in Subject{i} offered by School{i % 5} with intake in all "
    f"semesters and study on campus." for i in range(1, 31))


def test_whole_short_section_is_given_to_the_model(client, fake_llm, registry):
    add_source(registry, url="https://www.usiu.ac.ke/test-fixture/programme-list/", title="TEST FIXTURE: Programmes",
               department="academic_programmes", text=LONG_LIST)
    assert db_instance.get_collection("source_chunks").count_documents({"text": {"$regex": "Subject30"}}) == 1
    fake_llm.answer = "Programmes include Bachelor of Science in Subject1 and Subject30 [1]."
    ask(client, "Which undergraduate programmes are offered?")
    prompt = fake_llm.prompts[-1]
    assert "Subject1 " in prompt and "Subject15 " in prompt and "Subject30 " in prompt  # every passage, not two


def test_whole_section_limit_can_be_disabled(make_app):
    app = make_app(SOURCE_FULL_SECTION_CHARS=0)
    registry = app.extensions["source_registry"]
    add_source(registry, url="https://www.usiu.ac.ke/test-fixture/programme-list/", title="TEST FIXTURE: Programmes",
               department="academic_programmes", text=LONG_LIST)
    with app.app_context():
        results = registry.retrieve("Which undergraduate programmes are offered?", min_coverage=0.5)
    assert results and len(results[0]["chunks"]) <= 2 and len("".join(results[0]["chunks"])) < len(LONG_LIST)


def test_draft_section_text_is_never_used_as_context(client, fake_llm, registry):
    source = add_source(registry, url="https://www.usiu.ac.ke/test-fixture/programme-list/",
                        title="TEST FIXTURE: Programmes", department="academic_programmes", text=LONG_LIST)
    registry.set_status(str(source["_id"]), "draft")
    fake_llm.prompts.clear()
    body = ask(client, "Which undergraduate programmes are offered by School3?")
    assert all("Subject30" not in p for p in fake_llm.prompts)
    assert all(c["title"] != "TEST FIXTURE: Programmes" for c in body.get("citations") or [])


# --- Sections of the same page travel together ------------------------------------------------------
def _entry(registry_id, url, text, score=1.0):
    from bson import ObjectId

    return {"source": {"_id": ObjectId(), "url": url, "title": registry_id}, "chunks": [text], "chunk_meta": [],
            "score": score, "relevance": score, "stale": False}


def test_matching_sections_of_a_chosen_page_are_added_within_the_budget(app):
    registry = app.extensions["source_registry"]
    registry.settings = {**registry.settings, "SOURCE_CONTEXT_MAX_CHARS": 1000}
    page, other = "https://www.usiu.ac.ke/test-fixture/page/", "https://www.usiu.ac.ke/test-fixture/other/"
    a, b = _entry("A", page, "x" * 300), _entry("B", other, "y" * 300)
    c, d, e = _entry("C", page, "z" * 300), _entry("D", page, "w" * 600), _entry("E", other + "x/", "v" * 10)
    with app.app_context():
        extra = registry._page_siblings([a, b], [a, b, c, d, e])
    assert [x["source"]["title"] for x in extra] == ["C"]  # D would exceed the budget; E is another page


def test_page_siblings_can_be_disabled(app):
    registry = app.extensions["source_registry"]
    registry.settings = {**registry.settings, "SOURCE_CONTEXT_MAX_CHARS": 0}
    page = "https://www.usiu.ac.ke/test-fixture/page/"
    a, c = _entry("A", page, "x"), _entry("C", page, "z")
    assert registry._page_siblings([a], [a, c]) == []


# --- Department detection ----------------------------------------------------------------------------
def test_department_detection_for_visitor_questions():
    from services.routing import classify_department

    assert classify_department("Can you guarantee that I will be admitted?")[0] == "admissions"
    assert classify_department("What facilities and services are available to students?")[0] == "general_university"
    assert classify_department("I have a problem with my examination results. Which department should I contact?")[0] \
        == "registrar"
    assert classify_department("I have a question about my university fees. Who should assist me?")[0] == "finance"
    assert classify_department("How can I apply to USIU-Africa?")[0] == "admissions"


def test_how_can_i_apply_is_kept_as_its_own_question_part():
    from services.sources import LocalIndex

    parts = LocalIndex.query_parts("What programmes are offered, and how can I apply?")
    assert {"conceptapply": 2} in parts


def test_applied_in_a_programme_name_is_not_the_apply_concept():
    from services.routing import classify_department
    from services.sources import tokenize

    assert "conceptapply" not in tokenize("Bachelor of Science in Applied Computer Technology")
    assert set(tokenize("apply")) == set(tokenize("applications")) == {"conceptapply"}
    assert classify_department("What are the prerequisites for the BSc in Applied Computer Technology?")[0] \
        == "academic_programmes"


# --- Unresolved register items are never hidden from visitors ----------------------------------------
def test_unresolved_low_severity_issues_are_shown_but_internal_notes_are_not():
    from services.chat_service import visible_issues

    dataset = {"issues": [
        {"id": "W05", "type": "inconsistency", "status": "open", "user_warning": False},
        {"id": "W21", "type": "ambiguity", "status": "open", "user_warning": False},
        {"id": "V06", "type": "document_quality", "status": "open", "user_warning": False},
        {"id": "W14", "type": "conflict", "status": "unresolved", "user_warning": True},
        {"id": "W02", "type": "conflict", "status": "updated", "user_warning": False},
        {"id": "V07", "type": "missing_source", "status": "unresolved", "user_warning": False},
    ]}
    assert [i["id"] for i in visible_issues(dataset)] == ["W05", "W21", "V06", "W14"]
    assert visible_issues({}) == [] and visible_issues(None) == []


# --- Phrasing: grades, location, the department of the question ------------------------------------
def test_grades_are_searchable_and_distinct():
    from services.sources import tokenize

    c_plus, c_plain, b_plain = tokenize("C+"), tokenize("C plain"), tokenize("B plain")
    assert c_plus[0] == c_plain[0] == "conceptgrade" and len({c_plus[1], c_plain[1], b_plain[1]}) == 3
    assert tokenize("KCSE C+ and above") == tokenize("kcse C plus and above") == ["kcse", *c_plus, "above"]
    assert tokenize("a minimum aggregate of C+ (Plus)")[-2:] == c_plus
    assert tokenize("Mean grade of B- (minus)")[-2:] == tokenize("B minus")
    assert c_plain[1] not in tokenize("at least a B plain in English")
    assert tokenize("a plain answer")[0] == "plain"  # the article, not grade A
    assert tokenize("e-resources") == ["resource"]


def test_location_wording_and_university_name_help_ranking_but_not_coverage():
    from services.sources import LocalIndex, tokenize

    assert set(tokenize("Where is it located?")) == set(tokenize("location")) == set(tokenize("our address"))
    assert LocalIndex.query_parts("Where is USIU-Africa located?") == [{"usiu": 0, "africa": 0, "conceptlocation": 2}]
    assert LocalIndex.query_parts("USIU-Africa students") == []  # nothing to search for


def test_sources_of_the_questions_department_rank_first(app, registry):
    with app.app_context():
        add_source(registry, url="https://www.usiu.ac.ke/test-fixture/fin/", title="TEST FIXTURE: Finance",
                   department="finance", text="Zorblat forms are collected at the zorblat desk.")
        add_source(registry, url="https://www.usiu.ac.ke/test-fixture/reg/", title="TEST FIXTURE: Registrar",
                   department="registrar", text="Zorblat forms: the zorblat office.")
        plain = [r["source"]["title"] for r in registry.retrieve("zorblat forms", k=2)]
        preferred = [r["source"]["title"] for r in registry.retrieve("zorblat forms", k=2, prefer_department="finance")]
        registry.settings = {**registry.settings, "SOURCE_DEPARTMENT_BOOST": 1.0}
        off = [r["source"]["title"] for r in registry.retrieve("zorblat forms", k=2, prefer_department="finance")]
    assert plain[0] == "TEST FIXTURE: Registrar"  # shorter text wins without a preference
    assert preferred[0] == "TEST FIXTURE: Finance" and set(plain) == set(preferred)
    assert off == plain


def test_prompt_forbids_answering_from_off_topic_sources():
    from services.chat_service import SYSTEM_PROMPT

    assert "Use a source only for what it is actually about" in SYSTEM_PROMPT
