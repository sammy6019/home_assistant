"""
Technical + Fundamental analyzer for individual holdings.

Technical Score  (60% of composite):
  - RSI 14-period       (33%): neutral=50, overbought>70, oversold<30
  - 50-day MA cross     (33%): price above = short-term uptrend
  - 200-day MA cross    (33%): price above = long-term uptrend

Fundamental Score (40% of composite):
  - P/E ratio           (40%): lower vs ~20 market avg = better
  - Earnings growth     (35%): higher % = better
  - Dividend yield      (25%): 0–5% sweet spot

Composite 0–100 → Strong Buy / Buy / Hold / Sell / Strong Sell
"""

import logging
import time
from typing import Optional
import yfinance as yf

logger = logging.getLogger(__name__)

# Simple in-process cache to avoid hammering Yahoo Finance
_cache: dict = {}
CACHE_TTL = 3600  # 1 hour


def _rsi(closes, period=14) -> Optional[float]:
    """Compute RSI from a list/series of closing prices."""
    if len(closes) < period + 1:
        return None
    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains  = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 2)


def _rating(score: float) -> str:
    if score >= 85: return "Strong Buy"
    if score >= 70: return "Buy"
    if score >= 50: return "Hold"
    if score >= 30: return "Sell"
    return "Strong Sell"


def _rating_color(rating: str) -> str:
    return {
        "Strong Buy": "strong-buy",
        "Buy":        "buy",
        "Hold":       "hold",
        "Sell":       "sell",
        "Strong Sell":"strong-sell",
    }.get(rating, "hold")


def analyze(symbol: str, asset_class: str = "stock") -> dict:
    """
    Return full technical + fundamental analysis for a symbol.
    Crypto (asset_class='crypto') skips fundamentals and uses crypto-adjusted RSI logic.
    """
    now = time.time()
    cached = _cache.get(symbol)
    if cached and now - cached["ts"] < CACHE_TTL:
        return cached["data"]

    result = _analyze(symbol, asset_class)
    _cache[symbol] = {"ts": now, "data": result}
    return result


def _analyze(symbol: str, asset_class: str) -> dict:
    is_crypto = asset_class == "crypto"
    yf_symbol = symbol + "-USD" if is_crypto else symbol

    # ── Fetch price history ───────────────────────────────────────────────────
    try:
        ticker  = yf.Ticker(yf_symbol)
        history = ticker.history(period="1y")
        if history.empty:
            return _error(symbol, "No price history available")
        closes = list(history["Close"])
    except Exception as e:
        logger.error(f"[{symbol}] history fetch failed: {e}")
        return _error(symbol, f"Data fetch failed: {e}")

    current_price = closes[-1]
    ma50  = sum(closes[-50:])  / min(50,  len(closes)) if len(closes) >= 10 else None
    ma200 = sum(closes[-200:]) / min(200, len(closes)) if len(closes) >= 50 else None
    rsi   = _rsi(closes)

    # ── Technical score ───────────────────────────────────────────────────────
    # RSI component (33 pts): sweet-spot 40-60 = full score, penalise extremes
    rsi_score = 0.0
    rsi_label = "N/A"
    rsi_explanation = "RSI data unavailable"
    if rsi is not None:
        if rsi > 70:
            rsi_score = max(0, 33 - (rsi - 70) * 1.1)
            rsi_label = "Overbought"
            rsi_explanation = f"RSI at {rsi:.0f} — overbought, may pull back soon"
        elif rsi < 30:
            rsi_score = max(0, 33 - (30 - rsi) * 0.5)
            rsi_label = "Oversold"
            rsi_explanation = f"RSI at {rsi:.0f} — oversold, potential bounce opportunity"
        else:
            rsi_score = 33 - abs(rsi - 55) * 0.4
            rsi_score = max(15, min(33, rsi_score))
            rsi_label = "Neutral"
            rsi_explanation = f"RSI at {rsi:.0f} — neutral momentum, not stretched either way"

    # 50-day MA component (33 pts)
    ma50_score = 0.0
    ma50_label = "N/A"
    ma50_explanation = "50-day MA unavailable"
    if ma50 is not None:
        pct_diff = (current_price - ma50) / ma50 * 100
        if current_price >= ma50:
            ma50_score = min(33, 20 + pct_diff * 0.65)
            ma50_label = "Above"
            ma50_explanation = f"Price ${current_price:.2f} is {pct_diff:+.1f}% above 50-day MA (${ma50:.2f}) — short-term uptrend"
        else:
            ma50_score = max(0, 20 + pct_diff * 0.65)
            ma50_label = "Below"
            ma50_explanation = f"Price ${current_price:.2f} is {abs(pct_diff):.1f}% below 50-day MA (${ma50:.2f}) — short-term downtrend"

    # 200-day MA component (33 pts)
    ma200_score = 0.0
    ma200_label = "N/A"
    ma200_explanation = "200-day MA unavailable"
    if ma200 is not None:
        pct_diff = (current_price - ma200) / ma200 * 100
        if current_price >= ma200:
            ma200_score = min(34, 20 + pct_diff * 0.5)
            ma200_label = "Above"
            ma200_explanation = f"Price ${current_price:.2f} is {pct_diff:+.1f}% above 200-day MA (${ma200:.2f}) — long-term uptrend"
        else:
            ma200_score = max(0, 20 + pct_diff * 0.5)
            ma200_label = "Below"
            ma200_explanation = f"Price ${current_price:.2f} is {abs(pct_diff):.1f}% below 200-day MA (${ma200:.2f}) — long-term downtrend"

    technical_score = round(rsi_score + ma50_score + ma200_score, 1)

    # ── Fundamentals (stocks only) ────────────────────────────────────────────
    pe_ratio       = None
    earnings_growth= None
    div_yield      = None
    sector         = "N/A"
    pe_score       = 0.0
    eg_score       = 0.0
    dy_score       = 0.0
    pe_explanation = "P/E data unavailable"
    eg_explanation = "Earnings growth data unavailable"
    dy_explanation = "Dividend data unavailable"
    fundamental_score = 50.0  # neutral default for crypto

    if not is_crypto:
        try:
            info           = ticker.info
            fast           = ticker.fast_info
            pe_ratio       = info.get("trailingPE") or info.get("forwardPE")
            earnings_growth= info.get("earningsGrowth") or info.get("revenueGrowth")
            div_yield      = info.get("dividendYield")
            sector         = info.get("sector", "N/A")

            # P/E score (40 pts): ~20 = market avg; lower = better up to a point
            MARKET_AVG_PE = 22.0
            if pe_ratio and pe_ratio > 0:
                if pe_ratio < 10:
                    pe_score = 32.0
                    pe_explanation = f"P/E of {pe_ratio:.1f} — very cheap vs market average of {MARKET_AVG_PE:.0f}"
                elif pe_ratio <= MARKET_AVG_PE:
                    pe_score = 40 - (pe_ratio / MARKET_AVG_PE) * 8
                    pe_explanation = f"P/E of {pe_ratio:.1f} vs market average {MARKET_AVG_PE:.0f} — trading below average, potentially undervalued"
                elif pe_ratio <= 35:
                    pe_score = max(15, 40 - (pe_ratio - MARKET_AVG_PE) * 1.5)
                    pe_explanation = f"P/E of {pe_ratio:.1f} vs market average {MARKET_AVG_PE:.0f} — premium valuation, priced for growth"
                else:
                    pe_score = max(5, 40 - (pe_ratio - 20) * 0.9)
                    pe_explanation = f"P/E of {pe_ratio:.1f} — high valuation, requires strong growth to justify"
            else:
                pe_score = 20.0
                pe_explanation = "P/E not available (may be unprofitable or data missing)"

            # Earnings growth score (35 pts)
            if earnings_growth is not None:
                eg_pct = earnings_growth * 100
                if eg_pct >= 20:
                    eg_score = 35.0
                    eg_explanation = f"Earnings growing {eg_pct:.1f}% per year — strong growth"
                elif eg_pct >= 10:
                    eg_score = 20 + (eg_pct - 10) * 1.5
                    eg_explanation = f"Earnings growing {eg_pct:.1f}% per year — healthy growth"
                elif eg_pct >= 0:
                    eg_score = eg_pct * 2
                    eg_explanation = f"Earnings growing {eg_pct:.1f}% per year — modest growth"
                else:
                    eg_score = max(0, 10 + eg_pct * 0.5)
                    eg_explanation = f"Earnings declining {abs(eg_pct):.1f}% per year — watch closely"
            else:
                eg_score = 15.0
                eg_explanation = "Earnings growth data not available"

            # Dividend yield score (25 pts): sweet spot 1.5–4%
            if div_yield and div_yield > 0:
                # yfinance returns dividendYield already as a percentage (e.g. 0.36 = 0.36%)
                dy_pct = div_yield
                if 1.5 <= dy_pct <= 4.0:
                    dy_score = 25.0
                    dy_explanation = f"Dividend yield of {dy_pct:.2f}% — attractive income, pays you to hold"
                elif dy_pct < 1.5:
                    dy_score = dy_pct / 1.5 * 20
                    dy_explanation = f"Dividend yield of {dy_pct:.2f}% — low yield, more of a growth play"
                else:
                    dy_score = max(10, 25 - (dy_pct - 4) * 3)
                    dy_explanation = f"Dividend yield of {dy_pct:.2f}% — high yield, verify sustainability"
            else:
                dy_score = 8.0
                dy_explanation = "No dividend — growth-oriented or reinvests earnings"

            fundamental_score = round(pe_score + eg_score + dy_score, 1)

        except Exception as e:
            logger.warning(f"[{symbol}] fundamentals fetch failed: {e}")
            fundamental_score = 40.0

    # ── Composite ─────────────────────────────────────────────────────────────
    if is_crypto:
        composite = round(technical_score, 1)   # tech only for crypto
    else:
        composite = round(technical_score * 0.6 + fundamental_score * 0.4, 1)

    rating = _rating(composite)

    return {
        "symbol":          symbol,
        "asset_class":     asset_class,
        "current_price":   round(current_price, 4),
        "composite_score": composite,
        "rating":          rating,
        "rating_class":    _rating_color(rating),
        "technical": {
            "score": technical_score,
            "max":   100,
            "rsi": {
                "value":       rsi,
                "label":       rsi_label,
                "score":       round(rsi_score, 1),
                "max":         33,
                "explanation": rsi_explanation,
            },
            "ma50": {
                "value":       round(ma50, 2) if ma50 else None,
                "label":       ma50_label,
                "score":       round(ma50_score, 1),
                "max":         33,
                "explanation": ma50_explanation,
            },
            "ma200": {
                "value":       round(ma200, 2) if ma200 else None,
                "label":       ma200_label,
                "score":       round(ma200_score, 1),
                "max":         34,
                "explanation": ma200_explanation,
            },
        },
        "fundamental": None if is_crypto else {
            "score":     fundamental_score,
            "max":       100,
            "sector":    sector,
            "pe": {
                "value":       round(pe_ratio, 2) if pe_ratio else None,
                "score":       round(pe_score, 1),
                "max":         40,
                "explanation": pe_explanation,
            },
            "earnings_growth": {
                "value":       round(earnings_growth * 100, 1) if earnings_growth else None,
                "score":       round(eg_score, 1),
                "max":         35,
                "explanation": eg_explanation,
            },
            "dividend_yield": {
                "value":       round(div_yield, 2) if div_yield else None,
                "score":       round(dy_score, 1),
                "max":         25,
                "explanation": dy_explanation,
            },
        },
        "price_history": {
            "ma50":  round(ma50, 2)  if ma50  else None,
            "ma200": round(ma200, 2) if ma200 else None,
        },
    }


def _error(symbol: str, msg: str) -> dict:
    return {
        "symbol":          symbol,
        "error":           msg,
        "composite_score": None,
        "rating":          "N/A",
        "rating_class":    "hold",
        "technical":       None,
        "fundamental":     None,
    }
