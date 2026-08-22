"""RAG prompt enrichment helpers."""

from __future__ import annotations

import logging
from typing import List

from track2_orchestrator.rag_pipeline.vector_store import get_vector_store

logger = logging.getLogger(__name__)


def retrieve_context(query: str, top_k: int = 3) -> List[str]:
    try:
        vector_store = get_vector_store()
        return vector_store.query(query_text=query, top_k=top_k)
    except Exception as exc:
        logger.error("Error during context retrieval: %s", exc)
        return []


def build_enriched_prompt(prompt: str, rag_enabled: bool = True, top_k: int = 3) -> str:
    if not rag_enabled:
        return prompt

    context_chunks = retrieve_context(query=prompt, top_k=top_k)
    if not context_chunks:
        logger.info("No RAG context found for prompt.")
        return prompt

    context_str = "\n---\n".join(context_chunks)
    logger.info("Successfully enriched prompt with %d RAG chunks.", len(context_chunks))
    return f"[Retrieved Context Information]:\n{context_str}\n\n[User Prompt]:\n{prompt}"
