"""Offline integration checks for the real LangChain wiring.

These run the actual ConversationalRetrievalChain with a fake chat model and
an in-memory vector store, so no API keys or network access are needed. They
are skipped automatically when the AI libraries are not installed (e.g. with
requirements-dev.txt only).
"""

from unittest.mock import MagicMock

import pytest

pytest.importorskip("langchain_classic")
pytest.importorskip("langchain_groq")
pytest.importorskip("langchain_pinecone")

from langchain_core.embeddings import DeterministicFakeEmbedding  # noqa: E402
from langchain_core.language_models.fake_chat_models import FakeListChatModel  # noqa: E402
from langchain_core.vectorstores import InMemoryVectorStore  # noqa: E402

from services.chat_service import ChatService  # noqa: E402

SETTINGS = {
    "GROQ_API_KEY": "test-key",
    "GROQ_MODEL": "llama-3.3-70b-versatile",
    "GROQ_TIMEOUT": 5,
    "RETRIEVAL_K": 2,
    "SESSION_TIMEOUT": 60,
    "MAX_SESSIONS": 10,
}


@pytest.fixture
def service(app):  # ``app`` connects the in-memory database used by the models
    return ChatService(knowledge_base=None, settings=SETTINGS)


def test_real_retrieval_chain_runs_with_custom_prompt(service, monkeypatch):
    store = InMemoryVectorStore(DeterministicFakeEmbedding(size=16))
    store.add_texts(["Applications are submitted through the online portal."])
    llm = FakeListChatModel(responses=["Apply through the online portal."])
    monkeypatch.setattr(service, "_get_llm", lambda: llm)

    chain = service.get_conversation_chain(service.resolve_session_id(None), store)
    result = chain.invoke({"question": "How do I apply?"})
    assert result["answer"] == "Apply through the online portal."


def test_conversation_memory_is_kept_per_session(service, monkeypatch):
    store = InMemoryVectorStore(DeterministicFakeEmbedding(size=16))
    store.add_texts(["Registration opens in January."])
    llm = FakeListChatModel(responses=["January.", "rephrased question", "Still January."])
    monkeypatch.setattr(service, "_get_llm", lambda: llm)
    session = service.resolve_session_id(None)

    service.get_conversation_chain(session, store).invoke({"question": "When is registration?"})
    service.get_conversation_chain(session, store).invoke({"question": "Are you sure?"})
    assert len(service._memories[session].chat_memory.messages) == 4


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
