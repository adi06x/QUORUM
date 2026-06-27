from __future__ import annotations

from typing import Any

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.schemas import SourceRecord
from app.utils.embeddings import embed_text, embed_texts


class EvidenceVectorStore:
    def __init__(self, storage_path: str) -> None:
        self.client = chromadb.PersistentClient(
            path=storage_path,
            settings=ChromaSettings(anonymized_telemetry=False, is_persistent=True, persist_directory=storage_path),
        )

    def upsert_sources(self, query_id: str, sources: list[SourceRecord]) -> None:
        if not sources:
            return

        collection = self.client.get_or_create_collection(name=self._collection_name(query_id))
        documents = [self._document_text(source) for source in sources]
        metadatas = [
            {
                "title": source.title,
                "provider": source.provider,
                "year": source.year or 0,
                "url": source.url or "",
                "simulated": source.simulated,
            }
            for source in sources
        ]
        embeddings = embed_texts(documents)
        collection.upsert(
            ids=[source.id for source in sources],
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings,
        )

    def query_related(self, query_id: str, text: str, limit: int = 6) -> list[dict[str, Any]]:
        collection = self.client.get_or_create_collection(name=self._collection_name(query_id))
        results = collection.query(
            query_embeddings=[embed_text(text)],
            n_results=limit,
        )
        ids = results.get("ids", [[]])[0]
        docs = results.get("documents", [[]])[0]
        distances = results.get("distances", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        ranked_items: list[dict[str, Any]] = []
        for index, source_id in enumerate(ids):
            ranked_items.append(
                {
                    "id": source_id,
                    "document": docs[index],
                    "distance": distances[index] if index < len(distances) else None,
                    "metadata": metadatas[index] if index < len(metadatas) else {},
                }
            )
        return ranked_items

    def _collection_name(self, query_id: str) -> str:
        normalized = "".join(character for character in query_id if character.isalnum()).lower()
        return f"quorum_{normalized[:32]}"

    def _document_text(self, source: SourceRecord) -> str:
        author_line = ", ".join(source.authors[:4]) if source.authors else "Unknown authors"
        return "\n".join(
            filter(
                None,
                [
                    source.title,
                    source.abstract,
                    source.venue or "",
                    author_line,
                    str(source.year or ""),
                ],
            )
        )
