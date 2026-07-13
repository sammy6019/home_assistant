#!/usr/bin/env python3
"""Fetch papers from ArXiv and store metadata. STUB — depends on ArxivClient
and PaperProcessor.process_papers_batch being implemented.

Usage: python scripts/fetch_papers.py "cat:cs.LG" --max-papers 50
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import DB_CONFIG
from src.arxiv_client import ArxivClient
from src.database import PaperProcessor
from src.pdf_processor import PDFDownloader

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("query")
    parser.add_argument("--max-papers", type=int, default=50)
    args = parser.parse_args()

    processor = PaperProcessor(DB_CONFIG, ArxivClient(), PDFDownloader())
    stats = processor.process_papers_batch(args.query, max_papers=args.max_papers)
    print(stats)
