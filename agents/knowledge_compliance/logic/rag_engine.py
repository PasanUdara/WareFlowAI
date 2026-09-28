"""
RAG Engine & Qdrant Client [Member 3]

Semantic search over warehouse Standard Operating Procedures (SOPs)
using FastEmbed for local embeddings and Qdrant for vector storage.
"""

from typing import List, Dict, Any
import os

from fastembed import TextEmbedding
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct


class RAGEngine:
    """
    Handles SOP embeddings, Qdrant indexing, and semantic retrieval.
    """

    EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
    VECTOR_SIZE = 384

    def __init__(
        self,
        host: str = None,
        port: int = None,
        collection_name: str = None,
    ):
        self.host = host or os.getenv("QDRANT_HOST", "localhost")
        self.port = port or int(os.getenv("QDRANT_PORT", "6333"))

        self.collection_name = (
            collection_name
            or os.getenv("QDRANT_COLLECTION_NAME", "warehouse_sops")
        )

        self._qdrant_client = QdrantClient(
            host=self.host,
            port=self.port,
        )

        self._embedding_model = TextEmbedding(
            model_name=self.EMBEDDING_MODEL
        )

        self._ensure_collection()

    def _ensure_collection(self) -> None:
        """Create the Qdrant collection if it does not exist."""

        collections = self._qdrant_client.get_collections()

        existing_names = [
            collection.name
            for collection in collections.collections
        ]

        if self.collection_name not in existing_names:
            self._qdrant_client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.VECTOR_SIZE,
                    distance=Distance.COSINE,
                ),
            )

    def index_chunks(
        self,
        chunks: List[Dict[str, Any]],
    ) -> int:
        """
        Generate embeddings for SOP chunks and store them in Qdrant.
        """

        if not chunks:
            return 0

        texts = [
            chunk["content"]
            for chunk in chunks
        ]

        vectors = list(
            self._embedding_model.embed(texts)
        )

        points = []

        for index, (chunk, vector) in enumerate(
            zip(chunks, vectors)
        ):
            points.append(
                PointStruct(
                    id=index,
                    vector=vector.tolist(),
                    payload={
                        "filename": chunk["filename"],
                        "section_title": chunk["section_title"],
                        "sop_id": chunk.get("sop_id", ""),
                        "content": chunk["content"],
                    },
                )
            )

        self._qdrant_client.upsert(
            collection_name=self.collection_name,
            points=points,
        )

        return len(points)

    def search_sops(
        self,
        query: str,
        top_k: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        Search SOP chunks using semantic similarity.
        """

        if not query.strip():
            return []

        query_vector = list(
            self._embedding_model.embed([query])
        )[0]

        results = self._qdrant_client.search(
            collection_name=self.collection_name,
            query_vector=query_vector.tolist(),
            limit=top_k,
        )

        output = []

        for result in results:
            payload = result.payload or {}

            output.append(
                {
                    "section_title": payload.get(
                        "section_title",
                        "Unknown Section",
                    ),
                    "content": payload.get(
                        "content",
                        "",
                    ),
                    "score": result.score,
                    "sop_id": payload.get(
                        "sop_id",
                        "",
                    ),
                    "filename": payload.get(
                        "filename",
                        "",
                    ),
                }
            )

        return output