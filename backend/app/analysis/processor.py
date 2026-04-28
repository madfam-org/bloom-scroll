"""NLP processing for embeddings and bias detection."""

import logging

import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class NLPProcessor:
    """
    Handles NLP tasks for Bloom Scroll:
    - Embedding generation (semantic search)
    - Bias detection (optional/mock for MVP)
    """

    def __init__(self):
        """Initialize the processor with models."""
        self._embedding_model = None
        self._bias_model = None

    def _load_embedding_model(self) -> SentenceTransformer:
        """Lazy load the embedding model."""
        if self._embedding_model is None:
            logger.info("Loading sentence-transformers model...")
            self._embedding_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
            logger.info("Embedding model loaded successfully")
        return self._embedding_model

    def generate_embedding(self, text: str) -> list[float]:
        """
        Generate 384-dimensional embedding for text.

        Args:
            text: Input text (typically title + summary)

        Returns:
            List of 384 floats representing the semantic embedding
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for embedding generation")
            return [0.0] * 384  # Return zero vector

        try:
            model = self._load_embedding_model()
            embedding = model.encode(text, convert_to_numpy=True)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return [0.0] * 384

    def generate_embeddings_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for multiple texts efficiently.

        Args:
            texts: List of input texts

        Returns:
            List of embeddings (each 384 floats)
        """
        if not texts:
            return []

        try:
            model = self._load_embedding_model()
            embeddings = model.encode(texts, convert_to_numpy=True, show_progress_bar=True)
            return embeddings.tolist()
        except Exception as e:
            logger.error(f"Error generating batch embeddings: {e}")
            return [[0.0] * 384] * len(texts)

    def detect_bias(self, text: str) -> float | None:
        """
        Detect political bias in text.

        Returns:
            Bias score from -1.0 (Left) to +1.0 (Right), or None

        Note: This is a placeholder for MVP. Full implementation would use
        a fine-tuned BERT model like 'bucketresearch/politicalBiasBERT'.
        """
        # Mock implementation for MVP
        # In production, this would use a transformer model
        return None

    def calculate_cosine_similarity(
        self,
        embedding1: list[float],
        embedding2: list[float],
    ) -> float:
        """
        Calculate cosine similarity between two embeddings.

        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector

        Returns:
            Similarity score from -1.0 to 1.0 (higher = more similar)
        """
        try:
            vec1 = np.array(embedding1)
            vec2 = np.array(embedding2)

            # Cosine similarity = dot product / (norm1 * norm2)
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)

            if norm1 == 0 or norm2 == 0:
                return 0.0

            similarity = dot_product / (norm1 * norm2)
            return float(similarity)
        except Exception as e:
            logger.error(f"Error calculating cosine similarity: {e}")
            return 0.0

    def calculate_cosine_distance(
        self,
        embedding1: list[float],
        embedding2: list[float],
    ) -> float:
        """
        Calculate cosine distance between two embeddings.

        Cosine distance = 1 - cosine similarity

        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector

        Returns:
            Distance score from 0.0 to 2.0 (lower = more similar)
        """
        similarity = self.calculate_cosine_similarity(embedding1, embedding2)
        return 1.0 - similarity

    def calculate_context_vector(self, embeddings: list[list[float]]) -> list[float]:
        """
        Calculate average embedding from a list of embeddings.

        This represents the "user context" from their recent reads.

        Args:
            embeddings: List of embedding vectors

        Returns:
            Average embedding vector
        """
        if not embeddings:
            return [0.0] * 384

        try:
            embeddings_array = np.array(embeddings)
            avg_embedding = np.mean(embeddings_array, axis=0)
            return avg_embedding.tolist()
        except Exception as e:
            logger.error(f"Error calculating context vector: {e}")
            return [0.0] * 384

    def is_in_serendipity_zone(
        self,
        candidate_embedding: list[float],
        context_embedding: list[float],
        min_distance: float = 0.3,
        max_distance: float = 0.8,
    ) -> bool:
        """
        Check if candidate is in the "Serendipity Zone".

        The Goldilocks zone: different enough to be novel,
        close enough to be understood.

        Args:
            candidate_embedding: Embedding of candidate content
            context_embedding: User's context vector (avg of recent reads)
            min_distance: Minimum distance to avoid echo chamber (default: 0.3)
            max_distance: Maximum distance to avoid irrelevance (default: 0.8)

        Returns:
            True if candidate is in the serendipity zone
        """
        distance = self.calculate_cosine_distance(candidate_embedding, context_embedding)
        return min_distance <= distance <= max_distance


# Global singleton instance
_nlp_processor: NLPProcessor | None = None


def get_nlp_processor() -> NLPProcessor:
    """Get or create the global NLP processor instance."""
    global _nlp_processor
    if _nlp_processor is None:
        _nlp_processor = NLPProcessor()
    return _nlp_processor
