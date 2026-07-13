"""DB connection helpers, schema setup, and the paper ingestion pipeline."""

import logging
from pathlib import Path

import psycopg2
from psycopg2.extras import RealDictCursor

from config.settings import CACHE_PATH, DB_CONFIG
from src.arxiv_client import ArxivClient, ArxivPaper
from src.pdf_processor import PDFDownloader, PDFExtractor

logger = logging.getLogger(__name__)

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schema.sql"


def get_connection():
    return psycopg2.connect(cursor_factory=RealDictCursor, **DB_CONFIG)


def setup_database():
    """Create database schema from schema.sql."""
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = True
    cursor = conn.cursor()
    cursor.execute(SCHEMA_PATH.read_text())
    cursor.close()
    conn.close()
    print("Database schema created.")


class PaperProcessor:
    """Orchestrates the complete paper processing pipeline."""

    def __init__(self, db_config: dict, arxiv_client: ArxivClient,
                 pdf_downloader: PDFDownloader, max_workers: int = 4):
        self.db_config = db_config
        self.arxiv_client = arxiv_client
        self.pdf_downloader = pdf_downloader
        self.pdf_extractor = PDFExtractor()
        self.max_workers = max_workers

    def process_papers_batch(self, query: str, max_papers: int = 100,
                             skip_existing: bool = True) -> dict:
        """Search ArXiv for `query`, upsert each result's metadata, and
        enqueue it for PDF download/embedding. Returns run stats.
        """
        stats = {'fetched': 0, 'inserted': 0, 'updated': 0, 'skipped': 0, 'errors': 0}

        conn = psycopg2.connect(cursor_factory=RealDictCursor, **self.db_config)
        try:
            cursor = conn.cursor()
            for paper in self.arxiv_client.search_papers(query, max_results=max_papers):
                stats['fetched'] += 1
                try:
                    cursor.execute("SELECT id FROM papers WHERE arxiv_id = %s",
                                   (paper.arxiv_id,))
                    already_exists = cursor.fetchone() is not None

                    if already_exists and skip_existing:
                        stats['skipped'] += 1
                        continue

                    paper_id = self._upsert_paper(cursor, paper)
                    cursor.execute("""
                        INSERT INTO processing_queue (paper_id, operation)
                        VALUES (%s, 'download_pdf')
                    """, (paper_id,))
                    conn.commit()

                    if already_exists:
                        stats['updated'] += 1
                    else:
                        stats['inserted'] += 1
                except Exception:
                    conn.rollback()
                    stats['errors'] += 1
                    logger.exception("Failed to process paper %s", paper.arxiv_id)
        finally:
            conn.close()

        return stats

    def _upsert_paper(self, cursor, paper: ArxivPaper) -> int:
        """Insert or update paper metadata, return paper ID. IMPLEMENTED."""
        cursor.execute("""
            INSERT INTO papers (arxiv_id, title, abstract, authors, categories,
                                primary_category, published_date, updated_date,
                                pdf_url, comment, journal_ref, doi)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (arxiv_id) DO UPDATE SET title = EXCLUDED.title
            RETURNING id
        """, (paper.arxiv_id, paper.title, paper.abstract,
              paper.authors, paper.categories, paper.primary_category,
              paper.published_date, paper.updated_date,
              paper.pdf_url, paper.comment, paper.journal_ref, paper.doi))

        paper_db_id = cursor.fetchone()['id']

        # Sync relational author tables
        for author_name in paper.authors:
            cursor.execute("""
                INSERT INTO authors (name, normalized_name)
                VALUES (%s, %s)
                ON CONFLICT (normalized_name) DO NOTHING
                RETURNING id
            """, (author_name, author_name))

            res = cursor.fetchone()
            if res:
                author_id = res['id']
            else:
                cursor.execute("SELECT id FROM authors WHERE normalized_name = %s",
                               (author_name,))
                author_id = cursor.fetchone()['id']

            cursor.execute("""
                INSERT INTO paper_authors (paper_id, author_id)
                VALUES (%s, %s) ON CONFLICT DO NOTHING
            """, (paper_db_id, author_id))

        return paper_db_id

    def process_queue(self, limit: int = 50) -> dict:
        """Public entry point: open a connection and work through up to
        `limit` pending processing_queue items."""
        stats = {'processed': 0, 'failed': 0, 'requeued': 0}
        conn = psycopg2.connect(cursor_factory=RealDictCursor, **self.db_config)
        try:
            self._process_queue(conn, stats, limit=limit)
        finally:
            conn.close()
        return stats

    def _process_queue(self, conn, stats: dict, limit: int = 50):
        """Work through pending queue items: download the PDF, extract its
        text, cache it, and enqueue the next stage (embedding generation).
        """
        cursor = conn.cursor()
        cursor.execute("""
            SELECT q.id AS queue_id, q.paper_id, q.operation, q.retry_count,
                   p.arxiv_id, p.pdf_url, p.published_date
            FROM processing_queue q
            JOIN papers p ON p.id = q.paper_id
            WHERE q.status = 'pending' AND q.operation = 'download_pdf'
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

                ok, pdf_path, error = self.pdf_downloader.download_pdf(
                    item['pdf_url'], item['arxiv_id'], item['published_date'])

                if not ok:
                    raise RuntimeError(error or "download failed")

                extracted = self.pdf_extractor.extract_paper_text(str(pdf_path))

                cache_path = CACHE_PATH / f"{item['arxiv_id'].replace('/', '_')}.txt"
                cache_path.write_text(extracted['text'], encoding="utf-8")

                cursor.execute("""
                    UPDATE papers
                    SET pdf_downloaded = TRUE, pdf_processed = TRUE, processing_error = NULL
                    WHERE id = %s
                """, (item['paper_id'],))
                cursor.execute("""
                    UPDATE processing_queue
                    SET status = 'completed', completed_at = now()
                    WHERE id = %s
                """, (item['queue_id'],))
                cursor.execute("""
                    INSERT INTO processing_queue (paper_id, operation)
                    VALUES (%s, 'generate_embeddings')
                """, (item['paper_id'],))
                conn.commit()
                stats['processed'] += 1

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
                stats['failed' if next_status == 'failed' else 'requeued'] += 1
                logger.exception("Queue item %s failed for paper %s",
                                  item['queue_id'], item['arxiv_id'])
