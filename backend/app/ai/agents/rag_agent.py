"""
RAG Agent — Retrieval-Augmented Generation using ChromaDB + LangChain.
Retrieves relevant textbook content to ground LLM answers.
"""

from __future__ import annotations

from typing import Any

from loguru import logger

from app.config import settings


class RAGAgent:
    """ChromaDB-powered knowledge retrieval for educational content."""

    def __init__(self):
        self._client = None
        self._embedding_fn = None

    def _get_client(self):
        if self._client is None:
            try:
                import chromadb

                self._client = chromadb.HttpClient(
                    host=settings.CHROMADB_HOST,
                    port=settings.CHROMADB_PORT,
                )
                logger.info("[RAGAgent] ChromaDB client connected")
            except Exception as e:
                logger.warning(f"[RAGAgent] ChromaDB connection failed: {e}")
        return self._client

    def _get_embedding_fn(self):
        if self._embedding_fn is None:
            try:
                from chromadb.utils import embedding_functions

                self._embedding_fn = (
                    embedding_functions.SentenceTransformerEmbeddingFunction(
                        model_name="all-MiniLM-L6-v2"
                    )
                )
            except Exception as e:
                logger.warning(f"[RAGAgent] Embedding function failed: {e}")
        return self._embedding_fn

    def _get_collection(self, collection_name: str):
        client = self._get_client()
        if client is None:
            return None
        try:
            return client.get_or_create_collection(
                name=collection_name,
                embedding_function=self._get_embedding_fn(),
            )
        except Exception as e:
            logger.error(f"[RAGAgent] Cannot get collection {collection_name}: {e}")
            return None

    def retrieve(
        self,
        query: str,
        collection_name: str | None = None,
        n_results: int = 5,
        subject_filter: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Retrieve relevant document chunks from ChromaDB.
        Returns list of {content, title, score, metadata}.
        """
        collection_name = collection_name or settings.CHROMA_COLLECTION_TEXTBOOKS
        collection = self._get_collection(collection_name)

        if collection is None:
            logger.warning("[RAGAgent] No ChromaDB collection available")
            return []

        try:
            where = {"subject": subject_filter} if subject_filter else None
            results = collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where,
                include=["documents", "metadatas", "distances"],
            )

            sources = []
            docs = results.get("documents", [[]])[0]
            metas = results.get("metadatas", [[]])[0]
            distances = results.get("distances", [[]])[0]

            for doc, meta, dist in zip(docs, metas, distances):
                sources.append(
                    {
                        "content": doc,
                        "title": meta.get("title", "Textbook"),
                        "page": meta.get("page"),
                        "subject": meta.get("subject"),
                        "score": 1 - dist,  # Convert distance to similarity
                    }
                )

            logger.info(
                f"[RAGAgent] Retrieved {len(sources)} chunks for query: {query[:60]}..."
            )
            return sources

        except Exception as e:
            logger.error(f"[RAGAgent] Retrieval failed: {e}")
            return []

    def ingest_document(
        self,
        chunks: list[str],
        metadata: list[dict],
        collection_name: str | None = None,
        ids: list[str] | None = None,
    ) -> bool:
        """Ingest document chunks into ChromaDB."""
        collection_name = collection_name or settings.CHROMA_COLLECTION_TEXTBOOKS
        collection = self._get_collection(collection_name)

        if collection is None:
            return False

        try:
            if ids is None:
                import uuid

                ids = [str(uuid.uuid4()) for _ in chunks]

            collection.add(documents=chunks, metadatas=metadata, ids=ids)
            logger.info(
                f"[RAGAgent] Ingested {len(chunks)} chunks into {collection_name}"
            )
            return True
        except Exception as e:
            logger.error(f"[RAGAgent] Ingestion failed: {e}")
            return False

    def search_similar(self, query: str, top_k: int = 3) -> list[dict[str, Any]]:
        """Search across all collections and return top results."""
        all_results = []
        for collection_name in [
            settings.CHROMA_COLLECTION_TEXTBOOKS,
            settings.CHROMA_COLLECTION_NOTES,
            settings.CHROMA_COLLECTION_SOLUTIONS,
        ]:
            results = self.retrieve(
                query, collection_name=collection_name, n_results=top_k
            )
            all_results.extend(results)

        # Sort by score descending
        all_results.sort(key=lambda x: x.get("score", 0), reverse=True)
        return all_results[:top_k]
