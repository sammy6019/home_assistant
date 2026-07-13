"""Search engine over paper_chunks embeddings."""

import time
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional

import numpy as np
import psycopg2
from psycopg2.extras import RealDictCursor
from pgvector.psycopg2 import register_vector

from src.embeddings import EmbeddingGenerator


class SearchMode(Enum):
    VECTOR = "vector"
    HYBRID = "hybrid"
    KEYWORD = "keyword"


@dataclass
class SearchResult:
    paper_id: int
    arxiv_id: str
    title: str
    abstract: str
    authors: List[str]
    score: float
    matched_chunks: List[Dict]
    published_date: str
    categories: List[str]
    vector_score: Optional[float] = None
    keyword_score: Optional[float] = None


def _filter_clause(filters: Optional[Dict], params: Dict) -> str:
    """Build a SQL WHERE fragment (starting with AND) from a filters dict.
    Supported keys: categories (list), published_after, published_before.
    """
    clauses = []
    if not filters:
        return ""
    if filters.get('categories'):
        clauses.append("p.categories && %(categories)s")
        params['categories'] = filters['categories']
    if filters.get('published_after'):
        clauses.append("p.published_date >= %(published_after)s")
        params['published_after'] = filters['published_after']
    if filters.get('published_before'):
        clauses.append("p.published_date <= %(published_before)s")
        params['published_before'] = filters['published_before']
    return (" AND " + " AND ".join(clauses)) if clauses else ""


def _rows_to_results(rows: List[Dict], limit: int, chunks_per_paper: int = 3) -> List[SearchResult]:
    """Group chunk-level rows by paper, keeping the top-scoring chunks per
    paper as `matched_chunks`, and rank papers by their best chunk score."""
    by_paper: Dict[int, Dict] = {}
    for row in rows:
        pid = row['paper_id']
        entry = by_paper.setdefault(pid, {
            'paper_id': pid,
            'arxiv_id': row['arxiv_id'],
            'title': row['title'],
            'abstract': row['abstract'],
            'authors': row['authors'] or [],
            'categories': row['categories'] or [],
            'published_date': str(row['published_date']) if row['published_date'] else None,
            'best_score': row['score'],
            'chunks': [],
        })
        entry['best_score'] = max(entry['best_score'], row['score'])
        if len(entry['chunks']) < chunks_per_paper:
            entry['chunks'].append({
                'chunk_id': row['chunk_id'],
                'chunk_index': row['chunk_index'],
                'chunk_text': row['chunk_text'],
                'score': row['score'],
            })

    ranked = sorted(by_paper.values(), key=lambda e: e['best_score'], reverse=True)[:limit]
    return [
        SearchResult(
            paper_id=e['paper_id'], arxiv_id=e['arxiv_id'], title=e['title'],
            abstract=e['abstract'], authors=e['authors'], score=e['best_score'],
            matched_chunks=e['chunks'], published_date=e['published_date'],
            categories=e['categories'],
        )
        for e in ranked
    ]


class PaperSearchEngine:
    """Advanced search engine for academic papers."""

    def __init__(self, db_config: dict, embedding_generator: EmbeddingGenerator):
        self.db_config = db_config
        self.embedding_generator = embedding_generator
        # Populated on every search() call — a trace of what just happened,
        # for the "behind the scenes" demo panel. Not thread-safe; fine for
        # a single-worker Flask dev server.
        self.last_debug: Dict = {}

    def _connect(self):
        conn = psycopg2.connect(cursor_factory=RealDictCursor, **self.db_config)
        register_vector(conn)
        return conn

    def search(self, query: str, mode: SearchMode = SearchMode.HYBRID,
               limit: int = 10, filters: Optional[Dict] = None) -> List[SearchResult]:
        """Main search interface, dispatching to the requested mode."""
        self.last_debug = {'query': query, 'mode': mode.value, 'steps': []}
        if not query or not query.strip():
            return []

        t0 = time.perf_counter()
        if mode == SearchMode.VECTOR:
            results = self._vector_search(query, limit, filters)
        elif mode == SearchMode.KEYWORD:
            results = self._keyword_search(query, limit, filters)
        else:
            results = self._hybrid_search(query, limit, filters)
        self.last_debug['total_ms'] = round((time.perf_counter() - t0) * 1000, 1)
        return results

    def _vector_search(self, query: str, limit: int,
                       filters: Optional[Dict]) -> List[SearchResult]:
        """Cosine-similarity search over chunk embeddings."""
        t_embed = time.perf_counter()
        query_embedding = self.embedding_generator.generate_query_embedding(query)
        embed_ms = round((time.perf_counter() - t_embed) * 1000, 1)
        self.last_debug['embed_ms'] = embed_ms
        self.last_debug['embedding_dim'] = len(query_embedding)
        self.last_debug['embedding_preview'] = [round(float(x), 3) for x in query_embedding[:8]]
        self.last_debug['embedding_model'] = self.embedding_generator.model_name
        self.last_debug.setdefault('steps', []).append({
            'name': 'Embed query', 'detail': f"{self.embedding_generator.model_name} → {len(query_embedding)}-dim vector",
            'ms': embed_ms,
        })

        params = {'qvec': query_embedding, 'fetch_limit': limit * 5}
        where_extra = _filter_clause(filters, params)

        conn = self._connect()
        try:
            t_sql = time.perf_counter()
            cursor = conn.cursor()
            cursor.execute(f"""
                SELECT p.id AS paper_id, p.arxiv_id, p.title, p.abstract, p.authors,
                       p.categories, p.published_date,
                       c.id AS chunk_id, c.chunk_index, c.chunk_text,
                       1 - (c.embedding <=> %(qvec)s) AS score
                FROM paper_chunks c
                JOIN papers p ON p.id = c.paper_id
                WHERE c.embedding IS NOT NULL{where_extra}
                ORDER BY c.embedding <=> %(qvec)s
                LIMIT %(fetch_limit)s
            """, params)
            rows = cursor.fetchall()
            sql_ms = round((time.perf_counter() - t_sql) * 1000, 1)
        finally:
            conn.close()

        self.last_debug['vector_search_ms'] = sql_ms
        self.last_debug['vector_candidates'] = len(rows)
        self.last_debug['steps'].append({
            'name': 'Vector search (pgvector cosine)',
            'detail': f"{len(rows)} matching chunks, ORDER BY embedding <=> query",
            'ms': sql_ms,
        })

        return _rows_to_results(rows, limit)

    def _keyword_search(self, query: str, limit: int,
                        filters: Optional[Dict]) -> List[SearchResult]:
        """Trigram-similarity keyword search over chunk text."""
        params = {'q': query, 'fetch_limit': limit * 5}
        where_extra = _filter_clause(filters, params)

        conn = self._connect()
        try:
            t_sql = time.perf_counter()
            cursor = conn.cursor()
            cursor.execute(f"""
                SELECT p.id AS paper_id, p.arxiv_id, p.title, p.abstract, p.authors,
                       p.categories, p.published_date,
                       c.id AS chunk_id, c.chunk_index, c.chunk_text,
                       word_similarity(%(q)s, c.chunk_text) AS score
                FROM paper_chunks c
                JOIN papers p ON p.id = c.paper_id
                WHERE %(q)s <%% c.chunk_text{where_extra}
                ORDER BY score DESC
                LIMIT %(fetch_limit)s
            """, params)
            rows = cursor.fetchall()
            sql_ms = round((time.perf_counter() - t_sql) * 1000, 1)
        finally:
            conn.close()

        self.last_debug['keyword_search_ms'] = sql_ms
        self.last_debug['keyword_candidates'] = len(rows)
        self.last_debug.setdefault('steps', []).append({
            'name': 'Keyword search (pg_trgm word_similarity)',
            'detail': f"{len(rows)} matching chunks, trigram similarity vs. query",
            'ms': sql_ms,
        })

        return _rows_to_results(rows, limit)

    def _hybrid_search(self, query: str, limit: int,
                       filters: Optional[Dict]) -> List[SearchResult]:
        """Blend vector and keyword search: 0.6 * vector_score + 0.4 * keyword_score."""
        t_merge = time.perf_counter()
        vector_results = self._vector_search(query, limit * 2, filters)
        keyword_results = self._keyword_search(query, limit * 2, filters)

        merged: Dict[int, SearchResult] = {}
        for r in vector_results:
            merged[r.paper_id] = r
            r.vector_score = r.score
            r.score = 0.6 * r.score

        for r in keyword_results:
            if r.paper_id in merged:
                existing = merged[r.paper_id]
                existing.keyword_score = r.score
                existing.score += 0.4 * r.score
                seen = {c['chunk_id'] for c in existing.matched_chunks}
                for c in r.matched_chunks:
                    if c['chunk_id'] not in seen and len(existing.matched_chunks) < 3:
                        existing.matched_chunks.append(c)
            else:
                r.keyword_score = r.score
                r.score = 0.4 * r.score
                merged[r.paper_id] = r

        ranked = sorted(merged.values(), key=lambda r: r.score, reverse=True)[:limit]
        self.last_debug['steps'].append({
            'name': 'Merge (60% vector + 40% keyword)',
            'detail': f"{len(vector_results)} vector hits + {len(keyword_results)} keyword hits → "
                      f"{len(merged)} unique papers, top {len(ranked)} kept",
            'ms': round((time.perf_counter() - t_merge) * 1000, 1),
        })
        return ranked

    def find_similar_papers(self, paper_id: int,
                            limit: int = 10) -> List[SearchResult]:
        """Find papers similar to `paper_id` using its chunk-embedding centroid."""
        conn = self._connect()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT embedding FROM paper_chunks WHERE paper_id = %s",
                           (paper_id,))
            rows = cursor.fetchall()
            if not rows:
                return []

            embeddings = np.array([r['embedding'].to_numpy() for r in rows])
            centroid = embeddings.mean(axis=0)
            centroid = centroid / np.linalg.norm(centroid)

            cursor.execute("""
                SELECT p.id AS paper_id, p.arxiv_id, p.title, p.abstract, p.authors,
                       p.categories, p.published_date,
                       c.id AS chunk_id, c.chunk_index, c.chunk_text,
                       1 - (c.embedding <=> %(qvec)s) AS score
                FROM paper_chunks c
                JOIN papers p ON p.id = c.paper_id
                WHERE p.id != %(paper_id)s
                ORDER BY c.embedding <=> %(qvec)s
                LIMIT %(fetch_limit)s
            """, {'qvec': centroid, 'paper_id': paper_id, 'fetch_limit': limit * 5})
            rows = cursor.fetchall()
        finally:
            conn.close()

        return _rows_to_results(rows, limit)
