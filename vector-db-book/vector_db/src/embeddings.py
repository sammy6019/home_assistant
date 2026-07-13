"""Embedding generation and storage pipeline."""

import logging
import re
from typing import Dict, List

import numpy as np
import psycopg2
from psycopg2.extras import RealDictCursor, execute_batch
from pgvector.psycopg2 import register_vector
from sentence_transformers import SentenceTransformer

from config.settings import CACHE_PATH, EMBEDDING_BATCH_SIZE, EMBEDDING_DEVICE, EMBEDDING_MODEL
from src.pdf_processor import TextChunker

logger = logging.getLogger(__name__)

_WHITESPACE = re.compile(r'\s+')


class EmbeddingGenerator:
    """Efficient embedding generation with singleton pattern. IMPLEMENTED."""

    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(EmbeddingGenerator, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, model_name: str = EMBEDDING_MODEL):
        if self._initialized:
            return
        self.model_name = model_name
        self.model = SentenceTransformer(model_name, device=EMBEDDING_DEVICE)
        self.dimension = self.model.get_sentence_embedding_dimension()
        self._initialized = True
        print(f"Loaded {model_name} (dim={self.dimension}, device={EMBEDDING_DEVICE})")

    def generate_embeddings(self, texts: List[str],
                            show_progress: bool = True,
                            batch_size: int = EMBEDDING_BATCH_SIZE) -> np.ndarray:
        """Generate L2-normalized embeddings for a list of texts."""
        if not texts:
            return np.empty((0, self.dimension), dtype=np.float32)

        processed = [self._preprocess_text(t) for t in texts]
        return self.model.encode(
            processed,
            batch_size=batch_size,
            show_progress_bar=show_progress,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )

    def _preprocess_text(self, text: str) -> str:
        """Collapse whitespace before embedding. The model's own tokenizer
        handles truncation to its max sequence length."""
        return _WHITESPACE.sub(' ', text).strip()

    def generate_query_embedding(self, query: str) -> np.ndarray:
        """Generate an embedding for a single search query."""
        return self.generate_embeddings([query], show_progress=False)[0]


class EmbeddingPipeline:
    """Complete pipeline for generating and storing embeddings."""

    def __init__(self, db_config: dict, embedding_generator: EmbeddingGenerator,
                 batch_size: int = 100):
        self.db_config = db_config
        self.embedding_generator = embedding_generator
        self.batch_size = batch_size
        self.text_chunker = TextChunker()

    def process_paper(self, paper_id: int, chunks: List[Dict]) -> Dict[str, any]:
        """Embed and store all chunks for a single paper."""
        if not chunks:
            return {'paper_id': paper_id, 'chunks_stored': 0}

        texts = [c['chunk_text'] for c in chunks]
        embeddings = self.embedding_generator.generate_embeddings(
            texts, show_progress=False, batch_size=self.batch_size)

        self._store_chunks_with_embeddings(paper_id, chunks, embeddings)

        return {'paper_id': paper_id, 'chunks_stored': len(chunks)}

    def _store_chunks_with_embeddings(self, paper_id: int, chunks: List[Dict],
                                      embeddings: np.ndarray):
        """Upsert chunks and their embeddings into paper_chunks."""
        conn = psycopg2.connect(cursor_factory=RealDictCursor, **self.db_config)
        register_vector(conn)
        try:
            cursor = conn.cursor()
            rows = [
                (paper_id, chunk['chunk_index'], chunk['chunk_text'],
                 chunk['chunk_tokens'], embedding, chunk.get('section_name'),
                 chunk.get('page_number'), chunk.get('char_start'), chunk.get('char_end'),
                 chunk.get('has_math', False), chunk.get('has_code', False),
                 chunk.get('has_references', False))
                for chunk, embedding in zip(chunks, embeddings)
            ]
            execute_batch(cursor, """
                INSERT INTO paper_chunks (
                    paper_id, chunk_index, chunk_text, chunk_tokens, embedding,
                    section_name, page_number, char_start, char_end,
                    has_math, has_code, has_references
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (paper_id, chunk_index) DO UPDATE SET
                    chunk_text = EXCLUDED.chunk_text,
                    embedding = EXCLUDED.embedding
            """, rows)
            conn.commit()
        finally:
            conn.close()

    def process_pending_papers(self, limit: int = 10) -> Dict[str, any]:
        """Process papers with a pending 'generate_embeddings' queue item:
        load their cached extracted text, chunk it, embed, and store."""
        stats = {'processed': 0, 'failed': 0, 'chunks_stored': 0}

        conn = psycopg2.connect(cursor_factory=RealDictCursor, **self.db_config)
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT q.id AS queue_id, q.paper_id, q.retry_count, p.arxiv_id
                FROM processing_queue q
                JOIN papers p ON p.id = q.paper_id
                WHERE q.status = 'pending' AND q.operation = 'generate_embeddings'
                ORDER BY q.priority DESC, q.created_at ASC
                LIMIT %s
            """, (limit,))
            items = cursor.fetchall()

            for item in items:
                try:
                    cursor.execute("""
                        UPDATE processing_queue SET status = 'processing', started_at = now()
                        WHERE id = %s
                    """, (item['queue_id'],))
                    conn.commit()

                    cache_path = CACHE_PATH / f"{item['arxiv_id'].replace('/', '_')}.txt"
                    if not cache_path.exists():
                        raise FileNotFoundError(f"no cached text at {cache_path}")
                    text = cache_path.read_text(encoding="utf-8").replace('\x00', '')

                    chunks = self.text_chunker.chunk_paper(text, sections=[], preserve_sections=False)
                    result = self.process_paper(item['paper_id'], chunks)

                    cursor.execute("""
                        UPDATE papers SET embedding_generated = TRUE, processing_error = NULL
                        WHERE id = %s
                    """, (item['paper_id'],))
                    cursor.execute("""
                        UPDATE processing_queue SET status = 'completed', completed_at = now()
                        WHERE id = %s
                    """, (item['queue_id'],))
                    conn.commit()

                    stats['processed'] += 1
                    stats['chunks_stored'] += result['chunks_stored']

                except Exception as exc:
                    conn.rollback()
                    retry_count = item['retry_count'] + 1
                    next_status = 'pending' if retry_count < 3 else 'failed'
                    cursor.execute("""
                        UPDATE processing_queue
                        SET status = %s, retry_count = %s, error_message = %s
                        WHERE id = %s
                    """, (next_status, retry_count, str(exc), item['queue_id']))
                    cursor.execute("""
                        UPDATE papers SET processing_error = %s WHERE id = %s
                    """, (str(exc), item['paper_id']))
                    conn.commit()
                    stats['failed'] += 1
                    logger.exception("Embedding generation failed for paper %s",
                                      item['arxiv_id'])
        finally:
            conn.close()

        return stats
