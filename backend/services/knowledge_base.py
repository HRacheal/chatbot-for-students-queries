"""Knowledge-base indexing and retrieval (Pinecone + sentence-transformer embeddings).

Integrity rules implemented here:

* Each document is chunked on its own (documents are never concatenated), and
  every chunk records which document it came from (``source_id`` / ``title``).
* Vector IDs are deterministic: ``<document public_id>#chunk-<n>``. Re-indexing
  the same document overwrites its vectors instead of creating duplicates.
* After a rebuild, vectors that no longer belong to any current document
  (deleted documents, shrunk documents, and legacy random-ID duplicates) are
  removed. Vectors of documents that failed to download are kept, so a
  temporary error never wipes content.
* If no document produces any text, the rebuild aborts and the existing index
  is left untouched.
* Deleting a document removes its vectors immediately.

Heavy libraries (sentence-transformers, Pinecone, LangChain) are imported
lazily so the web app and the test-suite can start without them.
"""

import logging
import threading
from dataclasses import dataclass

from utils.pdf_utils import extract_pdf_text

logger = logging.getLogger(__name__)

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150
DELETE_BATCH_SIZE = 1000


class KnowledgeBaseError(RuntimeError):
    """Raised for knowledge-base problems. Messages are safe to show to admins."""


class KnowledgeBaseUnavailable(KnowledgeBaseError):
    pass


class RebuildInProgress(KnowledgeBaseError):
    pass


@dataclass
class SourceDocument:
    source_id: str
    title: str
    text: str


def vector_id_prefix(source_id):
    return f"{source_id}#chunk-"


def vector_id(source_id, chunk_number):
    return f"{vector_id_prefix(source_id)}{chunk_number:05d}"


def split_text(text):
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
    return [chunk.strip() for chunk in splitter.split_text(text or "") if chunk.strip()]


class KnowledgeBase:
    """Owns the connection to the vector index and the embedding model."""

    def __init__(self, settings, vectorstore=None, index=None):
        self.settings = settings
        self.namespace = settings.get("PINECONE_NAMESPACE", "course_materials")
        self._vectorstore = vectorstore
        self._index = index
        self._lock = threading.Lock()
        self._rebuild_lock = threading.Lock()

    # --- connections ---------------------------------------------------------
    def is_configured(self):
        return self._vectorstore is not None or bool(self.settings.get("PINECONE_API_KEY"))

    def _get_index(self):
        if self._index is not None:
            return self._index
        if not self.settings.get("PINECONE_API_KEY"):
            raise KnowledgeBaseUnavailable("Vector database is not configured")
        from pinecone import Pinecone, ServerlessSpec

        pc = Pinecone(api_key=self.settings["PINECONE_API_KEY"])
        name = self.settings["PINECONE_INDEX_NAME"]
        if name not in [idx.name for idx in pc.list_indexes()]:
            logger.info("Creating Pinecone index %s", name)
            pc.create_index(
                name=name,
                dimension=self.settings["EMBEDDING_DIMENSION"],
                metric="cosine",
                spec=ServerlessSpec(
                    cloud=self.settings["PINECONE_CLOUD"],
                    region=self.settings["PINECONE_REGION"],
                ),
            )
        self._index = pc.Index(name)
        return self._index

    def get_vectorstore(self):
        """Return the LangChain vector store, or ``None`` if it is unavailable."""
        if self._vectorstore is not None:
            return self._vectorstore
        if not self.is_configured():
            logger.warning("Knowledge base unavailable: vector database not configured")
            return None
        with self._lock:
            if self._vectorstore is not None:
                return self._vectorstore
            try:
                from langchain_huggingface import HuggingFaceEmbeddings
                from langchain_pinecone import PineconeVectorStore

                embeddings = HuggingFaceEmbeddings(
                    model_name=self.settings["EMBEDDING_MODEL"],
                    model_kwargs={"device": "cpu"},
                    encode_kwargs={"normalize_embeddings": True},
                )
                self._vectorstore = PineconeVectorStore(
                    index=self._get_index(), embedding=embeddings, namespace=self.namespace
                )
                logger.info("Knowledge base connected (namespace=%s)", self.namespace)
            except KnowledgeBaseUnavailable:
                logger.warning("Knowledge base unavailable: vector database not configured")
                return None
            except Exception as e:
                logger.error("Knowledge base unavailable (%s)", type(e).__name__)
                return None
        return self._vectorstore

    def _require_vectorstore(self):
        store = self.get_vectorstore()
        if store is None:
            raise KnowledgeBaseUnavailable("The knowledge base is not available")
        return store

    # --- index maintenance ----------------------------------------------------
    def list_vector_ids(self, prefix=None):
        index = self._get_index()
        ids = []
        kwargs = {"namespace": self.namespace}
        if prefix:
            kwargs["prefix"] = prefix
        for page in index.list(**kwargs):
            ids.extend(page)
        return ids

    def _delete_ids(self, ids):
        index = self._get_index()
        ids = list(ids)
        for start in range(0, len(ids), DELETE_BATCH_SIZE):
            index.delete(ids=ids[start:start + DELETE_BATCH_SIZE], namespace=self.namespace)
        return len(ids)

    def index_document(self, document):
        """(Re)index one document. Returns the list of vector IDs written."""
        chunks = split_text(document.text)
        if not chunks:
            return []
        ids = [vector_id(document.source_id, i) for i in range(len(chunks))]
        metadatas = [
            {"source_id": document.source_id, "title": document.title, "chunk": i}
            for i in range(len(chunks))
        ]
        self._require_vectorstore().add_texts(
            chunks, metadatas=metadatas, ids=ids, namespace=self.namespace
        )
        return ids

    def delete_document(self, source_id):
        """Remove every vector belonging to a document. Returns the number removed."""
        return self._delete_ids(self.list_vector_ids(prefix=vector_id_prefix(source_id)))

    def rebuild(self, documents, failed_source_ids=()):
        """Re-index ``documents`` and remove vectors that are no longer valid."""
        if not self._rebuild_lock.acquire(blocking=False):
            raise RebuildInProgress("A knowledge-base rebuild is already running")
        try:
            self._require_vectorstore()
            written, indexed, skipped = set(), [], []
            for document in documents:
                ids = self.index_document(document)
                if ids:
                    written.update(ids)
                    indexed.append(document.source_id)
                else:
                    skipped.append(document.source_id)

            if not written:
                raise KnowledgeBaseError(
                    "No text could be extracted from any document; the existing index was left unchanged"
                )

            keep_prefixes = tuple(vector_id_prefix(s) for s in failed_source_ids)
            stale = [
                vid for vid in self.list_vector_ids()
                if vid not in written and not (keep_prefixes and vid.startswith(keep_prefixes))
            ]
            removed = self._delete_ids(stale)
            summary = {
                "documents_indexed": len(indexed),
                "chunks_indexed": len(written),
                "documents_without_text": skipped,
                "documents_failed": list(failed_source_ids),
                "stale_vectors_removed": removed,
            }
            logger.info(
                "Knowledge base rebuilt: %d documents, %d chunks, %d stale vectors removed",
                len(indexed), len(written), removed,
            )
            return summary
        finally:
            self._rebuild_lock.release()


def rebuild_from_storage(knowledge_base, storage, max_pages=500):
    """Download every stored PDF, extract its text and rebuild the index."""
    documents, failed = [], []
    for resource in storage.list_pdfs():
        public_id = resource.get("public_id")
        try:
            text = extract_pdf_text(storage.download_pdf_bytes(resource), max_pages=max_pages)
        except Exception as e:
            logger.warning("Could not read stored document %s (%s)", public_id, type(e).__name__)
            failed.append(public_id)
            continue
        title = resource.get("original_filename") or public_id.split("/")[-1]
        documents.append(SourceDocument(source_id=public_id, title=title, text=text))

    if not documents and not failed:
        raise KnowledgeBaseError("No documents found in storage; the existing index was left unchanged")
    return knowledge_base.rebuild(documents, failed_source_ids=failed)
