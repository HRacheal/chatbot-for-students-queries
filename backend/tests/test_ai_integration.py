"""Offline integration checks for the real LangChain wiring.

These run the real prompt template and a LangChain fake chat model (no API keys
or network access). They are skipped automatically when the AI libraries are not
installed (e.g. with requirements-dev.txt only).
"""

from unittest.mock import MagicMock

import pytest

pytest.importorskip("langchain_groq")
pytest.importorskip("langchain_pinecone")

from langchain_core.embeddings import DeterministicFakeEmbedding  # noqa: E402
from langchain_core.language_models.fake_chat_models import FakeListChatModel  # noqa: E402

from services.chat_service import ChatService  # noqa: E402
from tests.conftest import TEST_SOURCES  # noqa: E402

SETTINGS = {
    "GROQ_API_KEY": "test-key",
    "GROQ_MODEL": "llama-3.3-70b-versatile",
    "GROQ_TIMEOUT": 5,
    "SESSION_TIMEOUT": 60,
    "MAX_SESSIONS": 10,
    "ALLOWED_SOURCE_DOMAINS": ["usiu.ac.ke"],
}


@pytest.fixture
def service(app, approved_sources):
    return ChatService(app.extensions["source_registry"], {**app.config, **SETTINGS})


def test_real_prompt_and_chat_model_produce_a_cited_answer(service, monkeypatch):
    llm = FakeListChatModel(responses=["Applications are submitted online [1]."])
    monkeypatch.setattr(service, "_get_llm", lambda: llm)
    body, status = service.process_query("How are applications submitted?", None)
    assert status == 200
    assert body["status"] == "answered"
    assert body["citations"][0]["url"] == TEST_SOURCES[0]["url"]


def test_conversation_history_is_kept_per_session(service, monkeypatch):
    llm = FakeListChatModel(responses=["Online [1].", "In writing [1]."])
    monkeypatch.setattr(service, "_get_llm", lambda: llm)
    first, _ = service.process_query("How are applications submitted?", None)
    service.process_query("How do students request an official transcript?", first["session_id"])
    assert len(service._memories[first["session_id"]]) == 2
    other, _ = service.process_query("How are applications submitted?", None)
    assert other["session_id"] != first["session_id"]
    assert len(service._memories[other["session_id"]]) == 1
    assert len(service._memories[first["session_id"]]) == 2


def test_groq_client_configuration(service):
    llm = service._get_llm()
    assert llm.model_name == "llama-3.3-70b-versatile"
    assert llm.max_retries == 2


def test_pinecone_vectorstore_accepts_injected_index():
    from langchain_pinecone import PineconeVectorStore

    store = PineconeVectorStore(
        index=MagicMock(), embedding=DeterministicFakeEmbedding(size=16), namespace="ns"
    )
    assert store._namespace == "ns"


# --- Groq reasoning models (openai/gpt-oss-*) ----------------------------------------------

def test_gpt_oss_citation_markers_are_normalised(service, monkeypatch):
    """gpt-oss writes "【1】"; it must become "[1]" so only the cited source is listed."""
    llm = FakeListChatModel(responses=["Applications are submitted online \u30101\u3011."])
    monkeypatch.setattr(service, "_get_llm", lambda: llm)
    body, _ = service.process_query("How are applications submitted?", None)
    assert body["status"] == "answered"
    assert "[1]" in body["answer"] and "\u3010" not in body["answer"]
    assert [c["url"] for c in body["citations"]] == [TEST_SOURCES[0]["url"]]


def test_citation_marker_variants():
    from services.chat_service import normalise_citation_markers as normalise

    assert normalise("a \u30102\u2020L1-L4\u3011 b \uff3b3\uff3d") == "a [2] b [3]"
    assert normalise("keep [link](https://www.usiu.ac.ke/) and [x]") == "keep [link](https://www.usiu.ac.ke/) and [x]"


def test_empty_model_reply_is_reported_as_ai_failure_not_a_blank_answer(service, monkeypatch):
    llm = FakeListChatModel(responses=[""])
    monkeypatch.setattr(service, "_get_llm", lambda: llm)
    body, _ = service.process_query("How are applications submitted?", None)
    assert body["status"] == "ai_unavailable"
    assert body["answer"].strip()  # the visitor gets an explanation, never an empty bubble


def test_reasoning_effort_is_low_for_gpt_oss_and_absent_for_other_models(app, approved_sources):
    from services.chat_service import reasoning_effort_for

    registry = app.extensions["source_registry"]
    oss = ChatService(registry, {**app.config, **SETTINGS, "GROQ_MODEL": "openai/gpt-oss-120b"})._get_llm()
    assert oss.model_name == "openai/gpt-oss-120b" and oss.reasoning_effort == "low"
    assert ChatService(registry, {**app.config, **SETTINGS})._get_llm().reasoning_effort is None
    assert reasoning_effort_for("openai/gpt-oss-20b", "medium") == "medium"
    assert reasoning_effort_for("openai/gpt-oss-20b", "default") is None
    blank = ChatService(registry, {**app.config, **SETTINGS, "GROQ_MODEL": "  "})._get_llm()
    assert blank.model_name == "openai/gpt-oss-120b"  # an empty GROQ_MODEL falls back to the default


def test_connection_check_fails_on_an_empty_groq_reply(monkeypatch, capsys):
    import langchain_groq
    from langchain_core.messages import AIMessage

    from tools.connection_check import check_groq

    class EmptyGroq:
        def __init__(self, **kwargs):
            assert kwargs["max_tokens"] >= 100  # enough budget for reasoning models
            assert kwargs.get("reasoning_effort") == "low"

        def invoke(self, prompt):
            return AIMessage(content="", response_metadata={"finish_reason": "length"})

    monkeypatch.setattr(langchain_groq, "ChatGroq", EmptyGroq)
    assert check_groq("gsk_secret_value", "openai/gpt-oss-120b", 5) is False
    out = capsys.readouterr().out
    assert "no visible text" in out and "finish_reason=length" in out and "gsk_secret_value" not in out
