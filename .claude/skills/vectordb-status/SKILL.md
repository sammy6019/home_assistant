---
name: vectordb-status
description: Checks the vector-db-book Postgres+pgvector instance health - container status, database/table sizes, disk usage, queue backlog, and Docker volume growth. Use when the ArXiv search demo feels slow, before ingesting a large batch of papers, or to check how much space the vector DB is using.
---

## Container status
- docker ps --filter name=vectordb --format '{{.Names}}\t{{.Status}}'
- docker inspect -f '{{.State.Health.Status}}' vectordb_postgres

## Database & table sizes
- docker exec vectordb_postgres psql -U postgres -d arxiv_papers -c "\l+"
- docker exec vectordb_postgres psql -U postgres -d arxiv_papers -c "\dt+"
- docker exec vectordb_postgres psql -U postgres -d arxiv_papers -c "
  SELECT relname AS table, pg_size_pretty(pg_total_relation_size(relid)) AS total_size
  FROM pg_catalog.pg_statio_user_tables ORDER BY pg_total_relation_size(relid) DESC;"

## Row counts / content volume
- docker exec vectordb_postgres psql -U postgres -d arxiv_papers -c "
  SELECT
    (SELECT count(*) FROM papers) AS papers,
    (SELECT count(*) FROM paper_chunks) AS chunks,
    (SELECT count(*) FROM papers WHERE embedding_generated) AS embedded_papers,
    (SELECT count(*) FROM papers WHERE pdf_downloaded AND NOT embedding_generated) AS pdf_only;"

## Processing queue backlog (stuck/failed items worth knowing about)
- docker exec vectordb_postgres psql -U postgres -d arxiv_papers -c "
  SELECT status, operation, count(*) FROM processing_queue GROUP BY status, operation ORDER BY 1,2;"
- docker exec vectordb_postgres psql -U postgres -d arxiv_papers -c "
  SELECT id, paper_id, operation, retry_count, error_message
  FROM processing_queue WHERE status = 'failed' ORDER BY id DESC LIMIT 10;"

## Docker volume + host disk usage
- docker system df -v | grep -A2 pgdata
- df -h /mnt/ssd

## PDF/cache/log storage on disk (outside the DB)
- du -sh /mnt/ssd/vector-db-book/vector_db/data/pdfs 2>/dev/null
- du -sh /mnt/ssd/vector-db-book/vector_db/data/cache 2>/dev/null
- du -sh /mnt/ssd/vector-db-book/vector_db/data/logs 2>/dev/null

## Interpreting results
- `arxiv_papers` DB size climbs mainly from `paper_chunks` (embeddings are 384 floats/chunk) — expect steady growth as more papers are ingested via the auto-fetch agent.
- Non-zero `failed` rows in processing_queue after 3 retries usually mean a broken PDF URL or a paper whose extracted text kept failing (check `error_message`).
- If `pdfs/` on disk is much larger than the DB, that's expected — raw PDFs are cached to disk separately from the extracted text stored in Postgres.
