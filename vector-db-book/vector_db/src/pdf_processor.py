"""PDF download, extraction, and chunking. STUB — most methods unimplemented."""

import logging
import re
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import fitz  # PyMuPDF
import requests

from config.settings import PDF_STORAGE_PATH

logger = logging.getLogger(__name__)

MATH_PATTERN = re.compile(
    r'\$[^$\n]+\$|\\(?:frac|sum|int|alpha|beta|gamma|delta|theta|lambda|sigma|'
    r'mu|pi|infty|partial|nabla|cdot|leq|geq|neq)\b|'
    r'[∑∫√±≤≥≠∞∂∇αβγδθλμπσφψω]'
)
TABLE_LINE_PATTERN = re.compile(r'(?:\S+[ \t]{2,}){2,}\S+')


class PDFDownloader:
    """Manages PDF downloads with retry logic and organization."""

    def __init__(self, storage_path: str = str(PDF_STORAGE_PATH),
                 max_retries: int = 3, timeout: int = 30):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.max_retries = max_retries
        self.timeout = timeout

    def _get_pdf_path(self, arxiv_id: str, published_date: datetime) -> Path:
        """Generate organized storage path: <storage_path>/<year>/<arxiv_id>.pdf."""
        year = str(published_date.year) if published_date else "unknown"
        safe_id = arxiv_id.replace("/", "_")
        year_dir = self.storage_path / year
        year_dir.mkdir(parents=True, exist_ok=True)
        return year_dir / f"{safe_id}.pdf"

    def download_pdf(self, pdf_url: str, arxiv_id: str,
                     published_date: datetime,
                     force: bool = False) -> Tuple[bool, Optional[Path], Optional[str]]:
        """Download a PDF with retry logic. Returns (success, path, error)."""
        pdf_path = self._get_pdf_path(arxiv_id, published_date)

        if pdf_path.exists() and not force:
            if self._validate_pdf(pdf_path):
                return True, pdf_path, None
            pdf_path.unlink()

        tmp_path = pdf_path.with_suffix(".pdf.tmp")
        last_error = None

        for attempt in range(1, self.max_retries + 1):
            try:
                response = requests.get(pdf_url, timeout=self.timeout, stream=True)
                response.raise_for_status()

                with open(tmp_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)

                if not self._validate_pdf(tmp_path):
                    raise ValueError("downloaded file failed PDF validation")

                tmp_path.rename(pdf_path)
                return True, pdf_path, None

            except Exception as exc:
                last_error = str(exc)
                logger.warning("Download attempt %d/%d failed for %s: %s",
                               attempt, self.max_retries, arxiv_id, last_error)
                tmp_path.unlink(missing_ok=True)
                if attempt < self.max_retries:
                    time.sleep(2 ** (attempt - 1))

        return False, None, last_error

    def _validate_pdf(self, pdf_path: Path) -> bool:
        """Check if file is a non-trivial, well-formed PDF."""
        try:
            if not pdf_path.exists() or pdf_path.stat().st_size < 1024:
                return False
            with open(pdf_path, "rb") as f:
                return f.read(5) == b"%PDF-"
        except OSError:
            return False


@dataclass
class ExtractedPage:
    page_num: int
    text: str
    blocks: List[Dict]
    has_columns: bool
    has_math: bool
    has_tables: bool
    confidence: float


class PDFExtractor:
    """Advanced PDF text extraction for academic papers."""

    def __init__(self):
        pass

    def extract_paper_text(self, pdf_path: str) -> Dict[str, any]:
        """Extract complete text from a PDF, page by page."""
        doc = fitz.open(pdf_path)
        try:
            pages = [self._extract_page(page, i + 1) for i, page in enumerate(doc)]
        finally:
            doc.close()

        full_text = self._clean_extracted_text(
            "\n\n".join(p.text for p in pages if p.text)
        )
        avg_confidence = sum(p.confidence for p in pages) / len(pages) if pages else 0.0

        return {
            'text': full_text,
            'pages': pages,
            'num_pages': len(pages),
            'has_math': any(p.has_math for p in pages),
            'has_tables': any(p.has_tables for p in pages),
            'has_columns': any(p.has_columns for p in pages),
            'confidence': avg_confidence,
        }

    def _extract_page(self, page, page_num: int) -> ExtractedPage:
        """Extract text and structural signals for a single page."""
        text_dict = page.get_text("dict")
        blocks = text_dict.get("blocks", [])
        text = page.get_text()

        has_columns = self._detect_columns(text_dict)
        has_math = bool(MATH_PATTERN.search(text))
        has_tables = bool(TABLE_LINE_PATTERN.search(text))
        confidence = 1.0 if text.strip() else 0.0

        return ExtractedPage(
            page_num=page_num,
            text=text,
            blocks=blocks,
            has_columns=has_columns,
            has_math=has_math,
            has_tables=has_tables,
            confidence=confidence,
        )

    def _detect_columns(self, blocks: Dict) -> bool:
        """Detect a two-column layout: pairs of text blocks that occupy
        disjoint horizontal halves of the page but overlap vertically."""
        page_width = blocks.get("width")
        text_blocks = [b for b in blocks.get("blocks", []) if b.get("type") == 0]
        if not page_width or len(text_blocks) < 4:
            return False

        mid = page_width / 2
        left = [b for b in text_blocks if b["bbox"][2] <= mid]
        right = [b for b in text_blocks if b["bbox"][0] >= mid]
        if not left or not right:
            return False

        for lb in left:
            ly0, ly1 = lb["bbox"][1], lb["bbox"][3]
            for rb in right:
                ry0, ry1 = rb["bbox"][1], rb["bbox"][3]
                if ly0 < ry1 and ry0 < ly1:  # vertical overlap
                    return True
        return False

    def _clean_extracted_text(self, text: str) -> str:
        """Normalize whitespace and rejoin hyphenated line-break words."""
        text = text.replace('\x00', '')
        text = re.sub(r'(\w)-\n(\w)', r'\1\2', text)
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()


CODE_PATTERN = re.compile(
    r'```|^\s{4,}\S|\b(?:def|class|import|return|function)\b\s|[{};]\s*$',
    re.MULTILINE,
)
REFERENCE_PATTERN = re.compile(r'\[\d+\]|\([A-Z][a-z]+(?:\s+et al\.)?,?\s+\d{4}\)')
SENTENCE_SPLIT = re.compile(r'(?<=[.!?])\s+(?=[A-Z0-9])')


class TextChunker:
    """Intelligent text chunking for academic papers.

    Chunk sizes are approximated in whitespace-delimited words, which is a
    close enough stand-in for tokens without pulling in a tokenizer.
    """

    def __init__(self, target_chunk_size: int = 768, min_chunk_size: int = 256,
                 max_chunk_size: int = 1024, overlap_size: int = 128):
        self.target_chunk_size = target_chunk_size
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
        self.overlap_size = overlap_size

    def chunk_paper(self, text: str, sections: List[Dict],
                    preserve_sections: bool = True) -> List[Dict]:
        """Chunk paper text intelligently, optionally respecting section
        boundaries. `sections` is a list of {'name': str, 'text': str};
        pass an empty list to chunk the full text as one unnamed section.
        """
        chunks: List[Dict] = []

        if preserve_sections and sections:
            for section in sections:
                chunks.extend(self._chunk_text(section['text'], section.get('name')))
        else:
            chunks.extend(self._chunk_text(text, None))

        for i, chunk in enumerate(chunks):
            chunk['chunk_index'] = i

        return chunks

    def _chunk_text(self, text: str,
                    section_name: Optional[str] = None) -> List[Dict]:
        """Greedily pack sentences into ~target_chunk_size-word chunks with
        word-level overlap between consecutive chunks."""
        text = text.strip()
        if not text:
            return []

        sentences = [s.strip() for s in SENTENCE_SPLIT.split(text) if s.strip()]
        if not sentences:
            sentences = [text]

        chunks = []
        current_words: List[str] = []
        char_cursor = 0
        chunk_start_char = 0

        def flush():
            nonlocal current_words, chunk_start_char
            if not current_words:
                return
            chunk_text = " ".join(current_words)
            chunks.append({
                'chunk_text': chunk_text,
                'chunk_tokens': len(current_words),
                'section_name': section_name,
                'char_start': chunk_start_char,
                'char_end': chunk_start_char + len(chunk_text),
                'has_math': bool(MATH_PATTERN.search(chunk_text)),
                'has_code': bool(CODE_PATTERN.search(chunk_text)),
                'has_references': bool(REFERENCE_PATTERN.search(chunk_text)),
            })

        for sentence in sentences:
            sentence_words = sentence.split()

            if (len(current_words) + len(sentence_words) > self.max_chunk_size
                    and len(current_words) >= self.min_chunk_size):
                flush()
                overlap_words = current_words[-self.overlap_size:] if self.overlap_size else []
                current_words = list(overlap_words)
                chunk_start_char = char_cursor - len(" ".join(overlap_words))

            current_words.extend(sentence_words)
            char_cursor += len(sentence) + 1

            if len(current_words) >= self.target_chunk_size:
                flush()
                overlap_words = current_words[-self.overlap_size:] if self.overlap_size else []
                current_words = list(overlap_words)
                chunk_start_char = char_cursor - len(" ".join(overlap_words))

        if current_words and (not chunks or len(current_words) >= self.min_chunk_size):
            flush()
        elif current_words and chunks:
            # trailing fragment too small on its own — merge into the last chunk
            last = chunks[-1]
            last['chunk_text'] = last['chunk_text'] + " " + " ".join(current_words)
            last['chunk_tokens'] = len(last['chunk_text'].split())
            last['char_end'] = last['char_start'] + len(last['chunk_text'])

        return chunks
