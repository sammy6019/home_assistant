"""
Daily AI Analyst Report — powered by Ollama (qwen3:4b-instruct).

Reads the cached portfolio data, runs technical analysis on each holding,
then asks Ollama to write a plain-English report covering:
  - Top 3 buys this week
  - Overbought / oversold holdings
  - Rebalancing suggestions
  - Dividend opportunities
  - Tax-loss harvesting alerts

The report is cached for 6 hours so it doesn't re-run on every page load.
"""

import json
import logging
import os
import time
from datetime import datetime
from typing import Optional
import requests
import technical_analyzer

logger = logging.getLogger(__name__)

CACHE_DIR        = "/tmp/finance_cache"
REPORT_CACHE     = f"{CACHE_DIR}/analyst_report.json"
REPORT_CACHE_TTL = 6 * 3600   # regenerate every 6 hours

SCHWAB_CACHE    = f"{CACHE_DIR}/schwab_positions.json"
COINBASE_CACHE  = f"{CACHE_DIR}/coinbase_positions.json"
ROBINHOOD_CACHE = f"{CACHE_DIR}/robinhood_positions.json"

OLLAMA_HOST  = os.getenv("OLLAMA_HOST", "http://192.168.1.227:11434")
OLLAMA_MODEL = "qwen3:4b-instruct"

ANALOGIES = {
    "rsi_high":  "RSI above 70 is like a runner who's sprinted too fast — they often need to slow down before going further.",
    "rsi_low":   "RSI below 30 is like a stock that's been beaten up — sometimes a bounce back is overdue.",
    "rsi_mid":   "RSI near 50 means the stock has balanced buying and selling pressure — no strong signal either way.",
    "pe":        "The P/E ratio is simply the price you're paying for each $1 of earnings. A P/E of 20 means you pay $20 for every $1 the company earns per year.",
    "ma_above":  "Price above the moving average is like the stock staying above its own trend line — a sign the uptrend is intact.",
    "ma_below":  "Price below the moving average means the stock has broken below its trend — momentum is pointing down.",
    "div_yield": "Dividend yield is the annual income you earn just for holding the stock. A 3% yield means a $10,000 investment pays you $300/year.",
    "tax_loss":  "Tax-loss harvesting means selling a losing position to capture a tax deduction, then replacing it with a similar investment.",
}


def _load_json(path: str) -> Optional[dict]:
    if os.path.exists(path):
        try:
            with open(path) as f:
                return json.load(f)
        except Exception:
            pass
    return None


def _all_positions() -> list:
    positions = []
    for path, label in [(SCHWAB_CACHE, "Schwab"), (COINBASE_CACHE, "Coinbase"), (ROBINHOOD_CACHE, "Robinhood")]:
        data = _load_json(path)
        if data:
            for p in data.get("positions", []):
                positions.append({**p, "account": label})
    return positions


def _run_ta_batch(positions: list) -> dict:
    """Run TA on up to 15 stock positions (skip crypto for speed)."""
    results = {}
    stocks = [p for p in positions if p.get("asset_class") != "crypto"][:15]
    for p in stocks:
        sym = p["symbol"]
        try:
            ta = technical_analyzer.analyze(sym, p.get("asset_class", "stock"))
            results[sym] = ta
        except Exception as e:
            logger.warning(f"TA skipped for {sym}: {e}")
    return results


def _portfolio_summary(positions: list, ta_map: dict) -> dict:
    total_value      = sum(p.get("market_value", 0) for p in positions)
    total_gl         = sum(p.get("gain_loss_dollar", 0) for p in positions)
    total_gl_pct     = (total_gl / (total_value - total_gl) * 100) if total_value else 0
    total_day_change = sum(p.get("day_change_dollar", 0) for p in positions)

    overbought, oversold, losers, top_scores = [], [], [], []

    for p in positions:
        sym = p["symbol"]
        ta  = ta_map.get(sym)
        gl  = p.get("gain_loss_dollar", 0)
        mv  = p.get("market_value", 0)

        if ta and not ta.get("error"):
            rsi   = ta.get("technical", {}).get("rsi", {}).get("value")
            score = ta.get("composite_score")
            if rsi and rsi > 70:
                overbought.append({"symbol": sym, "rsi": rsi, "score": score, "market_value": mv})
            elif rsi and rsi < 30:
                oversold.append({"symbol": sym, "rsi": rsi, "score": score, "market_value": mv})
            if score:
                top_scores.append({"symbol": sym, "score": score, "rating": ta.get("rating"), "market_value": mv})

        if gl < -500 and p.get("asset_class") != "crypto":
            losers.append({"symbol": sym, "gain_loss_dollar": gl, "gain_loss_pct": p.get("gain_loss_pct", 0), "market_value": mv})

    top_scores.sort(key=lambda x: x["score"], reverse=True)
    losers.sort(key=lambda x: x["gain_loss_dollar"])

    # Dividend holdings (yield > 1%)
    div_holdings = []
    for p in positions:
        ta = ta_map.get(p["symbol"])
        if ta and not ta.get("error"):
            f = ta.get("fundamental")
            if f:
                dy = f.get("dividend_yield", {}).get("value")
                if dy and dy > 1.0:
                    div_holdings.append({"symbol": p["symbol"], "yield": dy, "market_value": p.get("market_value", 0)})

    # Asset allocation
    allocation = {"Stocks": 0.0, "ETFs": 0.0, "Crypto": 0.0}
    for p in positions:
        mv  = p.get("market_value", 0)
        cls = p.get("asset_class", "stock")
        st  = p.get("security_type", "").lower()
        if cls == "crypto":
            allocation["Crypto"] += mv
        elif "etf" in st:
            allocation["ETFs"] += mv
        else:
            allocation["Stocks"] += mv

    return {
        "total_value":      round(total_value, 2),
        "total_gl":         round(total_gl, 2),
        "total_gl_pct":     round(total_gl_pct, 2),
        "total_day_change": round(total_day_change, 2),
        "position_count":   len(positions),
        "overbought":       overbought[:5],
        "oversold":         oversold[:5],
        "top_scores":       top_scores[:5],
        "losers":           losers[:5],
        "div_holdings":     sorted(div_holdings, key=lambda x: -x["yield"])[:5],
        "allocation":       {k: round(v, 2) for k, v in allocation.items()},
    }


def _build_prompt(summary: dict, ta_map: dict) -> str:
    alloc  = summary["allocation"]
    total  = summary["total_value"]
    top3   = summary["top_scores"][:3]
    ob     = summary["overbought"]
    os_    = summary["oversold"]
    losers = summary["losers"]
    divs   = summary["div_holdings"]

    top3_text = "\n".join(
        f"  - {p['symbol']}: composite score {p['score']}, rated {p['rating']}"
        for p in top3
    ) or "  - No scored positions available"

    ob_text = "\n".join(
        f"  - {p['symbol']}: RSI {p['rsi']:.0f} (overbought — {ANALOGIES['rsi_high']})"
        for p in ob
    ) or "  - None"

    os_text = "\n".join(
        f"  - {p['symbol']}: RSI {p['rsi']:.0f} (oversold — {ANALOGIES['rsi_low']})"
        for p in os_
    ) or "  - None"

    loser_text = "\n".join(
        f"  - {p['symbol']}: ${p['gain_loss_dollar']:,.0f} ({p['gain_loss_pct']:.1f}%) unrealised loss"
        for p in losers
    ) or "  - No significant losers"

    div_text = "\n".join(
        f"  - {p['symbol']}: {p['yield']:.2f}% yield"
        for p in divs
    ) or "  - No dividend-paying holdings found"

    alloc_text = ", ".join(f"{k}: ${v:,.0f}" for k, v in alloc.items() if v > 0)

    return f"""You are a personal financial analyst. Write a brief portfolio report using ONLY the data below. Plain English, 2-3 sentences per section. Use exact section headers shown.

Date: {datetime.now().strftime('%B %d, %Y')}
Portfolio: ${total:,.2f} total, {summary['total_gl_pct']:+.1f}% overall gain/loss, {summary['position_count']} positions
Allocation: {alloc_text}
Top holdings by score: {top3_text}
Overbought (RSI>70): {ob_text}
Oversold (RSI<30): {os_text}
Tax-loss candidates: {loser_text}
Dividends: {div_text}

## 🏆 Top 3 Buys This Week
## ⚠️ Overbought / Oversold Alerts
## ⚖️ Rebalancing Suggestions
## 💰 Dividend Opportunities
## 🌿 Tax-Loss Harvesting Alerts
"""


def _call_ollama(prompt: str) -> str:
    try:
        resp = requests.post(
            f"{OLLAMA_HOST}/api/generate",
            json={
                "model":  OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.4, "num_predict": 500},
            },
            timeout=300,
        )
        resp.raise_for_status()
        text = resp.json().get("response", "").strip()
        # Strip <think>...</think> blocks that qwen3 sometimes emits
        import re
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
        return text
    except Exception as e:
        logger.error(f"Ollama call failed: {e}")
        raise


def generate(force: bool = False) -> dict:
    """
    Return cached report if fresh, otherwise generate a new one.
    Pass force=True to regenerate regardless of cache age.
    """
    if not force:
        cached = _load_json(REPORT_CACHE)
        if cached:
            age = time.time() - cached.get("generated_ts", 0)
            if age < REPORT_CACHE_TTL:
                return cached

    positions = _all_positions()
    if not positions:
        return {
            "error":       "No portfolio data — upload at least one account CSV first.",
            "report":      None,
            "summary":     None,
            "generated_at": datetime.now().isoformat(),
        }

    logger.info(f"Generating analyst report for {len(positions)} positions…")
    ta_map  = _run_ta_batch(positions)
    summary = _portfolio_summary(positions, ta_map)
    prompt  = _build_prompt(summary, ta_map)

    try:
        report_text = _call_ollama(prompt)
    except Exception as e:
        report_text = None
        logger.error(f"Report generation failed: {e}")

    result = {
        "report":       report_text,
        "summary":      summary,
        "generated_at": datetime.now().isoformat(),
        "generated_ts": time.time(),
        "model":        OLLAMA_MODEL,
        "error":        None if report_text else "Ollama unavailable — check that it is running.",
    }

    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(REPORT_CACHE, "w") as f:
        json.dump(result, f)

    return result
