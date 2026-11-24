"""
Embedding Provider Module for Open Semantic Engine.
Supports:
1. Voyage AI API (voyage-multilingual-2 / voyage-3) - Recommended for Production & Korean Nuance
2. Local HuggingFace/BGE-M3 (FlagEmbedding) - Offline Fallback
3. Mock Provider - For Unit Testing
"""

import os
import math
from typing import List, Optional

class BaseEmbeddingProvider:
    """Abstract interface for embedding generation."""
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        raise NotImplementedError

    def similarity(self, vec_a: List[float], vec_b: List[float]) -> float:
        """Compute cosine similarity between two normalized or raw vectors."""
        dot = sum(a * b for a, b in zip(vec_a, vec_b))
        norm_a = math.sqrt(sum(a * a for a in vec_a))
        norm_b = math.sqrt(sum(b * b for b in vec_b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)


class VoyageEmbeddingProvider(BaseEmbeddingProvider):
    """
    Voyage AI embedding provider.
    Uses voyageai SDK or direct HTTPS API.
    Recommended model: 'voyage-multilingual-2' (1024-dim, SOTA for Korean retrieval & sentiment).
    """
    def __init__(self, api_key: Optional[str] = None, model: str = "voyage-multilingual-2"):
        self.api_key = api_key or os.getenv("VOYAGE_API_KEY")
        self.model = model
        self._client = None

        if self.api_key:
            try:
                import voyageai
                self._client = voyageai.Client(api_key=self.api_key)
            except ImportError:
                # Can fallback to urllib requests if voyageai is not installed
                self._client = None

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        
        if not self.api_key:
            raise ValueError("VOYAGE_API_KEY is not set. Please export VOYAGE_API_KEY='your-key' or provide api_key.")

        if self._client:
            # voyageai SDK
            result = self._client.embed(texts, model=self.model, input_type="document")
            return result.embeddings
        else:
            # Direct REST API fallback via requests/urllib
            import json
            import urllib.request

            req_data = json.dumps({
                "input": texts,
                "model": self.model,
                "input_type": "document"
            }).encode("utf-8")

            req = urllib.request.Request(
                "https://api.voyageai.com/v1/embeddings",
                data=req_data,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}"
                }
            )

            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return [item["embedding"] for item in data["data"]]


class LocalBGEEmbeddingProvider(BaseEmbeddingProvider):
    """Local offline embedding using sentence_transformers (BAAI/bge-m3)."""
    def __init__(self, model_name: str = "BAAI/bge-m3"):
        self.model_name = model_name
        self._model = None

    def _load(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name)

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        self._load()
        embeddings = self._model.encode(texts, normalize_embeddings=True)
        return embeddings.tolist()


class MockEmbeddingProvider(BaseEmbeddingProvider):
    """Deterministic lightweight mock embeddings for unit testing without network or GPU."""
    def __init__(self, dim: int = 128):
        self.dim = dim

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        results = []
        for text in texts:
            # Generate deterministic pseudo-vector based on character codes
            h = hash(text)
            vec = [(float((h >> (i % 32)) & 0xFF) / 255.0) - 0.5 for i in range(self.dim)]
            norm = math.sqrt(sum(x * x for x in vec)) or 1.0
            results.append([x / norm for x in vec])
        return results


def get_embedding_provider(
    provider_type: str = "auto",
    voyage_api_key: Optional[str] = None
) -> BaseEmbeddingProvider:
    """
    Factory to return the appropriate embedding provider:
    - 'voyage': Voyage AI API (requires VOYAGE_API_KEY)
    - 'local': Local BGE-M3
    - 'mock': Deterministic mock for test environments
    - 'auto': Voyage if key is present, otherwise fallback to local/mock
    """
    if provider_type == "voyage" or (provider_type == "auto" and (voyage_api_key or os.getenv("VOYAGE_API_KEY"))):
        return VoyageEmbeddingProvider(api_key=voyage_api_key)
    elif provider_type == "local":
        return LocalBGEEmbeddingProvider()
    elif provider_type == "mock":
        return MockEmbeddingProvider()
    else:
        # Default auto when no key: mock or local
        try:
            return LocalBGEEmbeddingProvider()
        except Exception:
            return MockEmbeddingProvider()
