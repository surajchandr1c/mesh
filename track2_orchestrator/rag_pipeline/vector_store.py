"""ChromaDB vector store helpers for Track 2."""

from __future__ import annotations

import os
from typing import List, Optional

import chromadb
from langchain_core.documents import Document

DEFAULT_DB_PATH = os.getenv("CHROMA_DB_PATH", "./chroma_db")
COLLECTION_NAME = "mesh_knowledge"


class VectorStoreManager:
    def __init__(self, db_path: str = DEFAULT_DB_PATH) -> None:
        self.db_path = db_path
        os.makedirs(self.db_path, exist_ok=True)
        self.client = chromadb.PersistentClient(path=self.db_path)
        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )

    def add_documents(self, documents: List[Document]) -> int:
        if not documents:
            return 0

        ids = [f"doc_{idx}_{hash(doc.page_content[:50])}" for idx, doc in enumerate(documents)]
        texts = [doc.page_content for doc in documents]
        metadatas = [doc.metadata for doc in documents]
        self.collection.add(ids=ids, documents=texts, metadatas=metadatas)
        return len(texts)

    def query(self, query_text: str, top_k: int = 3) -> List[str]:
        if self.collection.count() == 0:
            return []

        results = self.collection.query(query_texts=[query_text], n_results=min(top_k, self.collection.count()))
        documents = results.get("documents", [[]])
        return documents[0] if documents else []

    def get_count(self) -> int:
        return self.collection.count()


_vector_store_instance: Optional[VectorStoreManager] = None


def get_vector_store() -> VectorStoreManager:
    global _vector_store_instance
    if _vector_store_instance is None:
        _vector_store_instance = VectorStoreManager()
    return _vector_store_instance
