#!/usr/bin/env python3
"""Extract text, chunk, and generate embeddings for papers pending processing.
STUB — depends on PDFExtractor, TextChunker, and EmbeddingPipeline being implemented.

Usage: python scripts/build_index.py --limit 20
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import DB_CONFIG
from src.embeddings import EmbeddingGenerator, EmbeddingPipeline

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()

    pipeline = EmbeddingPipeline(DB_CONFIG, EmbeddingGenerator())
    stats = pipeline.process_pending_papers(limit=args.limit)
    print(stats)
