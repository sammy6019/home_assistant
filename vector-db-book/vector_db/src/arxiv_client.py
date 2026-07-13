"""ArXiv API client. search_papers is implemented; fetch_by_ids and
search_recent_papers are still STUBS."""

import logging
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Generator, List, Optional

import arxiv

from config.settings import ARXIV_MAX_RESULTS, ARXIV_RATE_LIMIT

logger = logging.getLogger(__name__)


@dataclass
class ArxivPaper:
    """Structured representation of an ArXiv paper."""
    arxiv_id: str
    title: str
    abstract: str
    authors: List[str]
    categories: List[str]
    primary_category: str
    published_date: datetime
    updated_date: datetime
    pdf_url: str
    comment: Optional[str] = None
    journal_ref: Optional[str] = None
    doi: Optional[str] = None


class ArxivClient:
    """Robust ArXiv API client with rate limiting and error handling."""

    def __init__(self, rate_limit_seconds: float = ARXIV_RATE_LIMIT,
                 max_results_per_query: int = ARXIV_MAX_RESULTS):
        self.rate_limit_seconds = rate_limit_seconds
        self.max_results_per_query = max_results_per_query
        self.last_request_time = 0.0

    def _rate_limit(self):
        """Enforce rate limiting between API calls."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.rate_limit_seconds:
            time.sleep(self.rate_limit_seconds - elapsed)
        self.last_request_time = time.time()

    def search_papers(self, query: str, max_results: int = 100,
                      sort_by=arxiv.SortCriterion.SubmittedDate,
                      sort_order=arxiv.SortOrder.Descending
                      ) -> Generator[ArxivPaper, None, None]:
        """Search ArXiv, yielding ArxivPaper records one at a time.

        The arxiv package paginates internally (page_size results per HTTP
        call); rate limiting between those calls is handled by the Client's
        delay_seconds rather than our own _rate_limit(), which we still use
        to space out separate search_papers() calls.
        """
        self._rate_limit()

        client = arxiv.Client(
            page_size=min(max_results, 100),
            delay_seconds=self.rate_limit_seconds,
            num_retries=3,
        )
        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        try:
            for result in client.results(search):
                yield self._to_arxiv_paper(result)
        except arxiv.UnexpectedEmptyPageError as exc:
            logger.warning("ArXiv returned an empty page for query %r: %s", query, exc)
        except arxiv.HTTPError as exc:
            logger.error("ArXiv HTTP error for query %r: %s", query, exc)

    def _to_arxiv_paper(self, result: "arxiv.Result") -> ArxivPaper:
        """Convert an arxiv.Result into our ArxivPaper dataclass."""
        return ArxivPaper(
            arxiv_id=result.get_short_id(),
            title=result.title.strip(),
            abstract=result.summary.strip(),
            authors=[author.name for author in result.authors],
            categories=list(result.categories),
            primary_category=result.primary_category,
            published_date=result.published,
            updated_date=result.updated,
            pdf_url=result.pdf_url,
            comment=result.comment,
            journal_ref=result.journal_ref,
            doi=result.doi,
        )

    def fetch_by_ids(self, arxiv_ids: List[str]) -> List[ArxivPaper]:
        """Fetch specific papers by ArXiv ID. STUB."""
        pass

    def search_recent_papers(self, categories: List[str],
                             days_back: int = 7) -> Generator[ArxivPaper, None, None]:
        """Fetch recent papers by category. STUB."""
        pass
