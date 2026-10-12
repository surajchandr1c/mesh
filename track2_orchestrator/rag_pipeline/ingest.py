"""Knowledge ingestion script for QThorium Mesh RAG vector database."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from langchain_core.documents import Document
from track2_orchestrator.rag_pipeline.vector_store import get_vector_store

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger("RAGIngest")

SAMPLE_DOCS = [
    Document(
        page_content="QThorium Mesh is a distributed P2P AI inference and orchestration platform. "
                     "It splits computational tasks across distributed contributor worker nodes "
                     "using gRPC and Redis message brokers.",
        metadata={"source": "architecture_overview", "topic": "mesh_basics"}
    ),
    Document(
        page_content="The failover engine in Track 4 actively tracks heartbeat pings and worker liveness. "
                     "If a worker node drops offline for more than 10 seconds, its active tasks are "
                     "automatically re-routed to healthy workers with lowest CPU and RAM load.",
        metadata={"source": "failover_guide", "topic": "reliability"}
    ),
    Document(
        page_content="Track 1 worker nodes use local quantized GGUF models or Ollama for fast, low-latency "
                     "token streaming. Hardware stats including CPU and RAM usage are transmitted "
                     "as heartbeats every 5 seconds to ensure cluster stability.",
        metadata={"source": "worker_nodes", "topic": "execution_engine"}
    ),
]


def ingest_seed_documents():
    """Populate the ChromaDB vector collection with baseline documents."""
    store = get_vector_store()
    current_count = store.get_count()
    LOGGER.info("Current vector store document count: %d", current_count)
    added = store.add_documents(SAMPLE_DOCS)
    LOGGER.info("Successfully added %d documents. Total now: %d", added, store.get_count())


if __name__ == "__main__":
    ingest_seed_documents()
