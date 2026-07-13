"""LangGraph agent: search locally first, and if there's too little to show,
fetch fresh papers from ArXiv, ingest them, and search again.

Graph:
    search_local --(thin results?)--> fetch_and_ingest --> search_local_again --> END
                  \\--(enough results)---------------------------------------------> END
"""

import logging
import time
from typing import Dict, List, Optional, TypedDict

from langgraph.graph import END, StateGraph

from config.settings import DB_CONFIG
from src.arxiv_client import ArxivClient
from src.database import PaperProcessor
from src.embeddings import EmbeddingGenerator, EmbeddingPipeline
from src.pdf_processor import PDFDownloader
from src.search import PaperSearchEngine, SearchMode, SearchResult

logger = logging.getLogger(__name__)

MIN_RESULTS_BEFORE_FETCH = 3
MIN_RELEVANCE_SCORE = 0.35
FETCH_MAX_PAPERS = 15


class AgentState(TypedDict):
    query: str
    limit: int
    results: List[SearchResult]
    fetched: bool
    ingest_stats: Optional[Dict]
    steps: List[Dict]


class SearchAgent:
    """Wraps PaperSearchEngine + the ingestion pipeline in a small LangGraph
    graph so a vague query that has too little local coverage triggers a
    live ArXiv fetch before answering."""

    def __init__(self):
        self.embedding_generator = EmbeddingGenerator()
        self.engine = PaperSearchEngine(DB_CONFIG, self.embedding_generator)
        self.processor = PaperProcessor(DB_CONFIG, ArxivClient(), PDFDownloader())
        self.embedding_pipeline = EmbeddingPipeline(DB_CONFIG, self.embedding_generator)
        self.graph = self._build_graph()

    def _build_graph(self):
        graph = StateGraph(AgentState)
        graph.add_node("search_local", self._search_local)
        graph.add_node("fetch_and_ingest", self._fetch_and_ingest)
        graph.add_node("search_local_again", self._search_local_again)

        graph.set_entry_point("search_local")
        graph.add_conditional_edges(
            "search_local",
            self._needs_more_papers,
            {"fetch": "fetch_and_ingest", "enough": END},
        )
        graph.add_edge("fetch_and_ingest", "search_local_again")
        graph.add_edge("search_local_again", END)
        return graph.compile()

    # -- nodes ---------------------------------------------------------

    def _search_local(self, state: AgentState) -> AgentState:
        t0 = time.perf_counter()
        results = self.engine.search(state["query"], mode=SearchMode.HYBRID,
                                      limit=state["limit"])
        state["results"] = results
        state["steps"].extend(self.engine.last_debug.get("steps", []))
        state["steps"].append({
            "name": "Search local index",
            "detail": f"{len(results)} papers already in Postgres matched \"{state['query']}\"",
            "ms": round((time.perf_counter() - t0) * 1000, 1),
        })
        return state

    def _needs_more_papers(self, state: AgentState) -> str:
        """pgvector cosine search is nearest-neighbor, not thresholded — it
        always returns *something*, even for topics nowhere in the corpus.
        So "enough results" has to mean enough *relevant* results, not just
        enough rows."""
        results = state["results"]
        if len(results) < MIN_RESULTS_BEFORE_FETCH:
            return "fetch"
        if max(r.score for r in results) < MIN_RELEVANCE_SCORE:
            return "fetch"
        return "enough"

    def _fetch_and_ingest(self, state: AgentState) -> AgentState:
        query = state["query"]
        results = state["results"]
        best = max((r.score for r in results), default=0.0)
        reason = (f"only {len(results)} local matches" if len(results) < MIN_RESULTS_BEFORE_FETCH
                  else f"best local match scored {best:.2f}, below relevance threshold {MIN_RELEVANCE_SCORE}")

        t0 = time.perf_counter()
        fetch_stats = self.processor.process_papers_batch(query, max_papers=FETCH_MAX_PAPERS)
        state["steps"].append({
            "name": "Fetch from ArXiv (local index too weak)",
            "detail": f"{reason} → searched arxiv.org for \"{query}\" → "
                      f"{fetch_stats['inserted']} new papers, {fetch_stats['skipped']} already known",
            "ms": round((time.perf_counter() - t0) * 1000, 1),
        })

        t0 = time.perf_counter()
        queue_stats = self.processor.process_queue(limit=FETCH_MAX_PAPERS)
        state["steps"].append({
            "name": "Download + extract PDFs",
            "detail": f"{queue_stats['processed']} PDFs downloaded and text-extracted",
            "ms": round((time.perf_counter() - t0) * 1000, 1),
        })

        t0 = time.perf_counter()
        embed_stats = self.embedding_pipeline.process_pending_papers(limit=FETCH_MAX_PAPERS)
        state["steps"].append({
            "name": "Chunk + embed + store in pgvector",
            "detail": f"{embed_stats['processed']} papers embedded, {embed_stats['chunks_stored']} chunks stored",
            "ms": round((time.perf_counter() - t0) * 1000, 1),
        })

        state["fetched"] = True
        state["ingest_stats"] = {
            "fetched": fetch_stats, "queued": queue_stats, "embedded": embed_stats,
        }
        return state

    def _search_local_again(self, state: AgentState) -> AgentState:
        t0 = time.perf_counter()
        results = self.engine.search(state["query"], mode=SearchMode.HYBRID,
                                      limit=state["limit"])
        state["results"] = results
        state["steps"].extend(self.engine.last_debug.get("steps", []))
        state["steps"].append({
            "name": "Re-search local index",
            "detail": f"{len(results)} papers now match \"{state['query']}\" after ingest",
            "ms": round((time.perf_counter() - t0) * 1000, 1),
        })
        return state

    # -- public API ------------------------------------------------------

    def run(self, query: str, limit: int = 10) -> AgentState:
        initial: AgentState = {
            "query": query, "limit": limit, "results": [], "fetched": False,
            "ingest_stats": None, "steps": [],
        }
        return self.graph.invoke(initial)
