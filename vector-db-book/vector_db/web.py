"""Minimal web UI for the Chapter 5 ArXiv paper search demo.

Wraps src.search.PaperSearchEngine. Search results stay empty until search()
and the embedding pipeline are implemented and papers have been ingested.
"""

from flask import Flask, render_template, request

from config.settings import DB_CONFIG
from src.agent import SearchAgent
from src.embeddings import EmbeddingGenerator
from src.search import PaperSearchEngine, SearchMode

app = Flask(__name__)

_engine = None
_agent = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = PaperSearchEngine(DB_CONFIG, EmbeddingGenerator())
    return _engine


def get_agent():
    global _agent
    if _agent is None:
        _agent = SearchAgent()
    return _agent


@app.route("/", methods=["GET"])
def index():
    query = request.args.get("q", "").strip()
    auto_fetch = request.args.get("auto_fetch") == "on"
    results = []
    error = None
    debug = {}
    if query:
        try:
            if auto_fetch:
                state = get_agent().run(query, limit=10)
                results = state["results"] or []
                debug = {"query": query, "mode": "agent (auto-fetch)",
                         "steps": state["steps"],
                         "total_ms": round(sum(s["ms"] for s in state["steps"]), 1),
                         "fetched": state["fetched"]}
            else:
                engine = get_engine()
                results = engine.search(query, mode=SearchMode.HYBRID, limit=10) or []
                debug = engine.last_debug
        except Exception as exc:
            error = str(exc)
    return render_template("index.html", query=query, results=results, error=error,
                           debug=debug, auto_fetch=auto_fetch)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
