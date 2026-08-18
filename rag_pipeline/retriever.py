import logging
from typing import List
from rag_pipeline.vector_store import get_vector_store

logger = logging.getLogger("rag_retriever")


def retrieve_context(query: str, top_k: int = 3) -> List[str]:
    """
    Retrieves top-k relevant text chunks for a query from the ChromaDB vector store.
    """
    try:
        vector_store = get_vector_store()
        chunks = vector_store.query(query_text=query, top_k=top_k)
        return chunks
    except Exception as e:
        logger.error(f"Error during context retrieval: {e}")
        return []


def build_enriched_prompt(prompt: str, rag_enabled: bool = True, top_k: int = 3) -> str:
    """
    Enriches the input prompt with retrieved RAG context if enabled.
    Returns formatted enriched prompt string.
    """
    if not rag_enabled:
        return prompt

    context_chunks = retrieve_context(query=prompt, top_k=top_k)
    if not context_chunks:
        logger.info("No RAG context found for prompt.")
        return prompt

    context_str = "\n---\n".join(context_chunks)
    enriched_prompt = (
        f"[Retrieved Context Information]:\n{context_str}\n\n"
        f"[User Prompt]:\n{prompt}"
    )
    logger.info(f"Successfully enriched prompt with {len(context_chunks)} RAG chunks.")
    return enriched_prompt
