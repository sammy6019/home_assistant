from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, List
import aiohttp
import asyncio
import os
import csv
import io
from datetime import datetime
import json
import httpx
from functools import lru_cache
import logging

# Import stock screening modules
from stock_analyzer import StockAnalyzer
from ai_analyzer import AIAnalyzer
import technical_analyzer
import analyst_report

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Finance Dashboard API")

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
ALPHA_VANTAGE_KEY = os.getenv("ALPHA_VANTAGE_KEY", "demo")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

# Initialize stock analyzer
stock_analyzer = None
ai_analyzer = None

# Models
class AnalysisRequest(BaseModel):
    symbol: str
    type: str
    timeframe: str = "daily"

class AIInsight(BaseModel):
    symbol: str
    insight: str
    confidence: float
    timestamp: str

class FinancialData(BaseModel):
    symbol: str
    price: float
    change_percent: float
    volume: Optional[int] = None
    timestamp: str
    data_type: str

# Cache for API responses
data_cache = {}
CACHE_DURATION = 3600
analysis_cache = {}
ANALYSIS_CACHE_DURATION = 86400

# Startup event
@app.on_event("startup")
async def startup_event():
    global stock_analyzer, ai_analyzer
    logger.info("Initializing Stock Analyzer...")
    stock_analyzer = StockAnalyzer()
    ai_analyzer = AIAnalyzer()
    logger.info("Stock Analyzer initialized successfully")

# ============ Helper Functions ============

async def fetch_stock_data(symbol: str) -> Dict:
    """Fetch stock data from Alpha Vantage"""
    if is_cache_valid(f"stock_{symbol}"):
        return data_cache[f"stock_{symbol}"]["data"]
    
    try:
        url = f"https://www.alphavantage.co/query"
        params = {
            "function": "GLOBAL_QUOTE",
            "symbol": symbol,
            "apikey": ALPHA_VANTAGE_KEY
        }
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params)
            data = response.json()
            
            if "Global Quote" in data and data["Global Quote"]:
                quote = data["Global Quote"]
                result = {
                    "symbol": symbol,
                    "price": float(quote.get("05. price", 0)),
                    "change_percent": float(quote.get("10. change percent", "0").rstrip("%")),
                    "volume": int(quote.get("06. volume", 0)),
                    "timestamp": datetime.now().isoformat(),
                    "data_type": "stock"
                }
                
                data_cache[f"stock_{symbol}"] = {
                    "data": result,
                    "timestamp": datetime.now()
                }
                
                return result
            else:
                raise ValueError(f"No data found for symbol {symbol}")
    except Exception as e:
        logger.error(f"Error fetching stock data: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to fetch stock data: {str(e)}")

async def fetch_crypto_data(crypto: str) -> Dict:
    """Fetch crypto data from CoinGecko"""
    if is_cache_valid(f"crypto_{crypto}"):
        return data_cache[f"crypto_{crypto}"]["data"]
    
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price"
        params = {
            "ids": crypto.lower(),
            "vs_currencies": "usd",
            "include_24hr_change": "true"
        }
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params)
            data = response.json()
            
            if crypto.lower() in data:
                price_data = data[crypto.lower()]
                result = {
                    "symbol": crypto.upper(),
                    "price": price_data.get("usd", 0),
                    "change_percent": price_data.get("usd_24h_change", 0),
                    "timestamp": datetime.now().isoformat(),
                    "data_type": "crypto"
                }
                
                data_cache[f"crypto_{crypto}"] = {
                    "data": result,
                    "timestamp": datetime.now()
                }
                
                return result
            else:
                raise ValueError(f"No data found for crypto {crypto}")
    except Exception as e:
        logger.error(f"Error fetching crypto data: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to fetch crypto data: {str(e)}")

async def get_ollama_insight(symbol: str, financial_data: Dict, data_type: str) -> AIInsight:
    """Get AI-powered insights from Ollama"""
    try:
        prompt = f"""
        Analyze this {data_type} data and provide a brief investment insight:
        
        Symbol: {symbol}
        Current Price: ${financial_data.get('price', 0)}
        24h Change: {financial_data.get('change_percent', 0)}%
        
        Provide a concise, actionable insight (2-3 sentences).
        """
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{OLLAMA_HOST}/api/generate",
                json={
                    "model": "neural-chat",
                    "prompt": prompt,
                    "stream": False,
                },
                timeout=30.0
            )
            
            if response.status_code == 200:
                result = response.json()
                insight_text = result.get("response", "").strip()
                
                return AIInsight(
                    symbol=symbol,
                    insight=insight_text,
                    confidence=0.75,
                    timestamp=datetime.now().isoformat()
                )
            else:
                return AIInsight(
                    symbol=symbol,
                    insight="AI service unavailable",
                    confidence=0.0,
                    timestamp=datetime.now().isoformat()
                )
    except Exception as e:
        logger.error(f"Error getting Ollama insight: {e}")
        return AIInsight(
            symbol=symbol,
            insight="Error generating insight",
            confidence=0.0,
            timestamp=datetime.now().isoformat()
        )

def is_cache_valid(key: str) -> bool:
    """Check if cache entry is still valid"""
    if key not in data_cache:
        return False
    return (datetime.now() - data_cache[key]["timestamp"]).seconds < CACHE_DURATION

async def check_ollama_health():
    """Check if Ollama is available"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{OLLAMA_HOST}/api/tags")
            return response.status_code == 200
    except:
        return False

# ============ Health Check ============

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "ollama_available": await check_ollama_health()
    }

# ============ SPECIFIC Stock Routes (BEFORE GENERIC) ============

@app.get("/api/stocks/top-rated")
async def get_top_rated_stocks(include_ai: bool = False):
    """Get top-rated stocks based on composite scoring"""
    try:
        logger.info("Fetching top-rated stocks...")
        result = stock_analyzer.analyze_all(include_ai=include_ai)
        return result
    except Exception as e:
        logger.error(f"Error analyzing stocks: {e}")
        return {
            "timestamp": datetime.now().isoformat(),
            "ai_available": False,
            "top_stocks": [],
            "top_cryptos": [],
            "daily_summary": "",
            "stats": {
                "total_stocks_analyzed": 0,
                "total_cryptos_analyzed": 0,
                "stocks_with_errors": 0,
                "cryptos_with_errors": 0
            }
        }

@app.get("/api/stocks/{symbol}/analysis")
async def get_stock_analysis(symbol: str, include_ai: bool = False):
    """Get detailed analysis for a specific stock"""
    try:
        result = stock_analyzer.analyze_stock(symbol, include_ai=include_ai)
        return result
    except Exception as e:
        logger.error(f"Error analyzing stock {symbol}: {e}")
        raise HTTPException(status_code=400, detail=f"Error analyzing stock: {str(e)}")

# ============ SPECIFIC Crypto Routes (BEFORE GENERIC) ============

@app.get("/api/crypto/top-rated")
@app.get("/api/stocks/top-rated")
async def get_top_rated_stocks(include_ai: bool = False):
    """Get top-rated stocks based on composite scoring"""
    try:
        logger.info("Fetching top-rated stocks...")
        result = stock_analyzer.analyze_all(include_ai=include_ai)
        return {
            "timestamp": result.get("timestamp"),
            "ai_available": result.get("ai_available"),
            "top_stocks": result.get("top_stocks", []),
            "stats": result.get("stats")
        }
    except Exception as e:
        logger.error(f"Error analyzing stocks: {e}")
        raise HTTPException(status_code=400, detail=f"Error analyzing stocks: {str(e)}")
async def get_top_rated_cryptos(include_ai: bool = False):
    """Get top-rated cryptos based on composite scoring"""
    try:
        logger.info("Fetching top-rated cryptos...")
        result = stock_analyzer.analyze_all(include_ai=include_ai)
        return {
            "timestamp": result.get("timestamp"),
            "ai_available": result.get("ai_available"),
            "top_cryptos": result.get("top_cryptos", []),
            "stats": result.get("stats")
        }
    except Exception as e:
        logger.error(f"Error analyzing cryptos: {e}")
        raise HTTPException(status_code=400, detail=f"Error analyzing cryptos: {str(e)}")

@app.get("/api/crypto/{symbol}/analysis")
async def get_crypto_analysis(symbol: str, include_ai: bool = False):
    """Get detailed analysis for a specific crypto"""
    try:
        result = stock_analyzer.analyze_crypto(symbol, include_ai=include_ai)
        return result
    except Exception as e:
        logger.error(f"Error analyzing crypto {symbol}: {e}")
        raise HTTPException(status_code=400, detail=f"Error analyzing crypto: {str(e)}")

# ============ GENERIC Routes (AFTER SPECIFIC) ============

@app.get("/api/stock/{symbol}")
async def get_stock(symbol: str):
    """Get stock data (legacy endpoint)"""
    stock_data = await fetch_stock_data(symbol)
    insight = await get_ollama_insight(symbol, stock_data, "stock")
    return {"data": stock_data, "insight": insight}

@app.get("/api/crypto/{crypto}")
async def get_crypto(crypto: str):
    """Get crypto data (legacy endpoint)"""
    crypto_data = await fetch_crypto_data(crypto)
    insight = await get_ollama_insight(crypto, crypto_data, "crypto")
    return {"data": crypto_data, "insight": insight}

# ============ Dashboard & Summary Routes ============

@app.get("/api/portfolio/summary")
async def get_portfolio_summary():
    """Get portfolio summary"""
    return {
        "total_value": 0,
        "24h_change": 0,
        "top_holdings": [],
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/ollama/models")
async def get_ollama_models():
    """Get available Ollama models"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{OLLAMA_HOST}/api/tags")
            if response.status_code == 200:
                return response.json()
            else:
                return {"models": [], "error": "Ollama unavailable"}
    except Exception as e:
        logger.error(f"Error fetching Ollama models: {e}")
        return {"models": [], "error": str(e)}

@app.get("/api/dashboard/summary")
async def get_dashboard_summary():
    """Get daily AI market summary"""
    try:
        logger.info("Generating daily summary...")
        summary = stock_analyzer.get_daily_summary()
        return {
            "timestamp": datetime.now().isoformat(),
            "summary": summary,
            "ai_available": True
        }
    except Exception as e:
        logger.error(f"Error generating summary: {e}")
        return {
            "timestamp": datetime.now().isoformat(),
            "summary": "Summary unavailable",
            "ai_available": False
        }

@app.get("/api/analysis/refresh")
async def refresh_analysis():
    """Manually refresh all cached analysis"""
    try:
        global analysis_cache
        analysis_cache.clear()
        return {
            "status": "success",
            "message": "Analysis cache cleared",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error refreshing analysis: {e}")
        raise HTTPException(status_code=400, detail=f"Error refreshing: {str(e)}")

@app.get("/api/analysis/watchlist")
async def get_watchlist():
    """Get current watchlist configuration"""
    try:
        watchlist = stock_analyzer.data_fetcher.watchlist
        return {
            "stocks": watchlist.get("stocks", []),
            "cryptos": watchlist.get("cryptos", []),
            "total": len(watchlist.get("stocks", [])) + len(watchlist.get("cryptos", [])),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting watchlist: {e}")
        raise HTTPException(status_code=400, detail=f"Error getting watchlist: {str(e)}")

@app.post("/api/analyze")
async def analyze_asset(request: AnalysisRequest):
    """Analyze a specific asset"""
    try:
        if request.type == "stock":
            result = stock_analyzer.analyze_stock(request.symbol)
        elif request.type == "crypto":
            result = stock_analyzer.analyze_crypto(request.symbol)
        else:
            raise ValueError(f"Unknown asset type: {request.type}")
        
        return result
    except Exception as e:
        logger.error(f"Error analyzing {request.symbol}: {e}")
        raise HTTPException(status_code=400, detail=f"Error analyzing asset: {str(e)}")

# ============ Multi-Account Portfolio ============

CACHE_DIR   = "/tmp/finance_cache"
SCHWAB_CACHE   = f"{CACHE_DIR}/schwab_positions.json"
COINBASE_CACHE = f"{CACHE_DIR}/coinbase_positions.json"
ROBINHOOD_CACHE= f"{CACHE_DIR}/robinhood_positions.json"

# kept for backwards-compat
PORTFOLIO_CACHE = SCHWAB_CACHE


def _flt(val, default=0.0):
    try:
        v = str(val).strip().strip('"').replace("$","").replace(",","").replace("%","")
        return float(v) if v not in ("","--","N/A","nan") else default
    except (ValueError, TypeError):
        return default


def _summarise(positions: list, cash: float, account: str) -> dict:
    total_cost        = sum(p.get("cost_basis", 0) for p in positions)
    total_gain        = sum(p.get("gain_loss_dollar", 0) for p in positions)
    total_mkt         = sum(p.get("market_value", 0) for p in positions) + cash
    total_day_change  = sum(p.get("day_change_dollar", 0) for p in positions)
    prev_value        = total_mkt - total_day_change
    total_day_pct     = (total_day_change / prev_value * 100) if prev_value else 0
    alerts            = [p for p in positions if abs(p.get("day_change_pct", 0)) >= 5]
    return {
        "account":           account,
        "positions":         positions,
        "cash":              round(cash, 2),
        "total_value":       round(total_mkt, 2),
        "total_cost":        round(total_cost, 2),
        "total_gain_dollar": round(total_gain, 2),
        "total_gain_pct":    round((total_gain / total_cost * 100) if total_cost else 0, 2),
        "total_day_change":  round(total_day_change, 2),
        "total_day_pct":     round(total_day_pct, 2),
        "alerts":            alerts,
        "position_count":    len(positions),
        "uploaded_at":       datetime.now().isoformat(),
    }


def parse_schwab_csv(content: str) -> dict:
    """
    Parse a Schwab positions CSV export.
    Schwab prepends account header rows before the actual column headers,
    and appends Cash/Total rows at the bottom — we skip both.
    """
    reader = csv.reader(io.StringIO(content))
    rows   = list(reader)

    header_idx = next((i for i, r in enumerate(rows) if r and r[0].strip('"') == "Symbol"), None)
    if header_idx is None:
        raise ValueError("Could not find 'Symbol' header — is this a Schwab positions CSV?")

    headers   = [h.strip().strip('"') for h in rows[header_idx]]
    positions = []
    cash      = 0.0

    for row in rows[header_idx + 1:]:
        if not row or not row[0].strip().strip('"'):
            continue
        symbol = row[0].strip().strip('"')
        if symbol == "Account Total":
            continue

        def col(name, default=""):
            try:
                return row[headers.index(name)].strip().strip('"').replace("$","").replace(",","").replace("%","")
            except (ValueError, IndexError):
                return default

        if symbol in ("Cash & Cash Investments", "Cash"):
            cash = _flt(col("Market Value"))
            continue

        asset_type = col("Asset Type") or col("Security Type", "Stock")
        positions.append({
            "symbol":            symbol,
            "description":       col("Description"),
            "quantity":          _flt(col("Qty (Quantity)") or col("Quantity")),
            "price":             _flt(col("Price")),
            "market_value":      _flt(col("Mkt Val (Market Value)") or col("Market Value")),
            "day_change_pct":    _flt(col("Day Chng % (Day Change %)") or col("Day Change %")),
            "day_change_dollar": _flt(col("Day Chng $ (Day Change $)") or col("Day Change $")),
            "cost_basis":        _flt(col("Cost Basis")),
            "gain_loss_pct":     _flt(col("Gain % (Gain/Loss %)") or col("Gain/Loss %")),
            "gain_loss_dollar":  _flt(col("Gain $ (Gain/Loss $)") or col("Gain/Loss $")),
            "security_type":     asset_type,
            "pct_of_account":    _flt(col("% Of Account")),
            "asset_class":       "crypto" if asset_type.upper() == "CRYPTO" else "stock",
        })

    return _summarise(positions, cash, "schwab")


def parse_coinbase_csv(content: str) -> dict:
    """
    Parse Coinbase transaction history CSV.
    Aggregates buys/receives as additions, sells/sends as subtractions
    to derive current holdings. Cost basis is estimated from buy transactions.

    Expected headers (Coinbase standard export):
      Timestamp, Transaction Type, Asset, Quantity Transacted,
      Spot Price Currency, Spot Price at Transaction,
      Subtotal, Total (inclusive of fees and/or spread), Fees and/or Spread, Notes
    """
    reader  = csv.DictReader(io.StringIO(content))
    # Normalise header names (strip whitespace/BOM)
    raw     = list(reader)
    if not raw:
        raise ValueError("Coinbase CSV appears empty")

    # Remap headers to lowercase-no-space keys for resilience
    def h(row, *candidates):
        for k in row:
            norm = k.strip().lower().replace(" ","_").replace("(","").replace(")","")
            for c in candidates:
                if c in norm:
                    return row[k]
        return ""

    holdings: dict[str, dict] = {}

    for row in raw:
        txn_type = h(row, "transaction_type").strip().lower()
        asset    = h(row, "asset").strip().upper()
        qty      = _flt(h(row, "quantity_transacted"))
        price    = _flt(h(row, "spot_price_at"))
        subtotal = _flt(h(row, "subtotal"))
        fees     = _flt(h(row, "fees"))

        if not asset or qty == 0:
            continue

        if asset not in holdings:
            holdings[asset] = {"qty": 0.0, "cost": 0.0, "proceeds": 0.0}

        if txn_type in ("buy", "receive", "reward", "coinbase_earn", "learning_reward",
                        "staking_income", "interest"):
            holdings[asset]["qty"]  += qty
            holdings[asset]["cost"] += subtotal + fees if subtotal else qty * price + fees
        elif txn_type in ("sell", "send", "convert"):
            holdings[asset]["qty"]  -= qty
            holdings[asset]["proceeds"] += subtotal

    positions = []
    for asset, h_data in holdings.items():
        qty = round(h_data["qty"], 8)
        if qty <= 1e-8:
            continue
        cost     = h_data["cost"]
        avg_cost = cost / qty if qty else 0
        # Use avg cost as current price estimate (no live feed without API key)
        mkt_val  = qty * avg_cost
        positions.append({
            "symbol":            asset,
            "description":       asset,
            "quantity":          round(qty, 8),
            "price":             round(avg_cost, 6),
            "market_value":      round(mkt_val, 2),
            "day_change_pct":    0.0,
            "day_change_dollar": 0.0,
            "cost_basis":        round(cost, 2),
            "gain_loss_pct":     0.0,
            "gain_loss_dollar":  round(h_data["proceeds"] - cost, 2),
            "security_type":     "Crypto",
            "pct_of_account":    0.0,
            "asset_class":       "crypto",
        })

    # Recalculate pct_of_account
    total = sum(p["market_value"] for p in positions)
    for p in positions:
        p["pct_of_account"] = round(p["market_value"] / total * 100, 2) if total else 0

    return _summarise(positions, 0.0, "coinbase")


def parse_robinhood_csv(content: str) -> dict:
    """
    Parse a Robinhood positions CSV export.

    Robinhood web export headers (robinhood.com/account/portfolio/export):
      Symbol, Date, Type, Side, Quantity, Price, Amount
    OR the older positions format:
      Instrument, Symbol, Quantity, Average Buy Price, Equity,
      Percent Change, Equity Change, Type, Name, ID, Currency
    """
    reader = csv.DictReader(io.StringIO(content))
    rows   = list(reader)
    if not rows:
        raise ValueError("Robinhood CSV appears empty")

    headers_lower = {k.strip().lower() for k in rows[0].keys()}

    # Detect which format
    is_activity = "side" in headers_lower  # activity/order history format
    positions_map: dict[str, dict] = {}

    if is_activity:
        # Aggregate order history into positions
        for row in rows:
            def rv(k): return row.get(k, row.get(k.title(), "")).strip()
            side   = rv("Side").lower()
            sym    = rv("Symbol").upper()
            qty    = _flt(rv("Quantity"))
            price  = _flt(rv("Price"))
            if not sym or qty == 0:
                continue
            if sym not in positions_map:
                positions_map[sym] = {"qty": 0.0, "cost": 0.0}
            if side == "buy":
                positions_map[sym]["qty"]  += qty
                positions_map[sym]["cost"] += qty * price
            elif side == "sell":
                avg = positions_map[sym]["cost"] / positions_map[sym]["qty"] if positions_map[sym]["qty"] else price
                positions_map[sym]["qty"]  -= qty
                positions_map[sym]["cost"] -= qty * avg

        positions = []
        for sym, d in positions_map.items():
            qty = round(d["qty"], 4)
            if qty <= 0:
                continue
            avg_price = d["cost"] / qty if qty else 0
            positions.append({
                "symbol":            sym,
                "description":       sym,
                "quantity":          qty,
                "price":             round(avg_price, 4),
                "market_value":      round(qty * avg_price, 2),
                "day_change_pct":    0.0,
                "day_change_dollar": 0.0,
                "cost_basis":        round(d["cost"], 2),
                "gain_loss_pct":     0.0,
                "gain_loss_dollar":  0.0,
                "security_type":     "Stock",
                "pct_of_account":    0.0,
                "asset_class":       "stock",
            })
    else:
        # Direct positions export
        def rh(row, *keys):
            for k in row:
                if k.strip().lower() in [x.lower() for x in keys]:
                    return row[k].strip()
            return ""

        for row in rows:
            sym     = rh(row, "symbol", "Symbol").upper()
            qty     = _flt(rh(row, "quantity", "Quantity"))
            avg_buy = _flt(rh(row, "average buy price", "Average Buy Price"))
            equity  = _flt(rh(row, "equity", "Equity"))
            pct_chg = _flt(rh(row, "percent change", "Percent Change"))
            eq_chg  = _flt(rh(row, "equity change", "Equity Change"))
            rh_type = rh(row, "type", "Type").lower()
            name    = rh(row, "name", "Name")

            if not sym or qty <= 0:
                continue

            cost     = avg_buy * qty
            gl_dol   = equity - cost
            gl_pct   = (gl_dol / cost * 100) if cost else 0
            cur_price= equity / qty if qty else avg_buy

            positions.append({
                "symbol":            sym,
                "description":       name or sym,
                "quantity":          qty,
                "price":             round(cur_price, 4),
                "market_value":      round(equity, 2),
                "day_change_pct":    round(pct_chg, 2),
                "day_change_dollar": round(eq_chg, 2),
                "cost_basis":        round(cost, 2),
                "gain_loss_pct":     round(gl_pct, 2),
                "gain_loss_dollar":  round(gl_dol, 2),
                "security_type":     "ETF" if "etf" in rh_type else "Stock",
                "pct_of_account":    0.0,
                "asset_class":       "stock",
            })

    total = sum(p["market_value"] for p in positions)
    for p in positions:
        p["pct_of_account"] = round(p["market_value"] / total * 100, 2) if total else 0

    return _summarise(positions, 0.0, "robinhood")


def _load_cache(path: str) -> dict | None:
    if os.path.exists(path):
        try:
            with open(path) as f:
                return json.load(f)
        except Exception:
            pass
    return None


def _save_cache(path: str, data: dict):
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f)


# ── Upload endpoints ──────────────────────────────────────────────────────────

async def _do_upload(file: UploadFile, parser, cache_path: str, label: str) -> dict:
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a .csv")
    try:
        content = (await file.read()).decode("utf-8-sig")
        data    = parser(content)
        _save_cache(cache_path, data)
        logger.info(f"{label} uploaded: {data['position_count']} positions, ${data['total_value']:,.2f}")
        return {"status": "ok", "positions": data["position_count"], "total_value": data["total_value"]}
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"{label} upload error: {e}")
        raise HTTPException(status_code=500, detail=f"Parse error: {str(e)}")


@app.post("/api/portfolio/upload")          # backwards-compat alias
@app.post("/api/portfolio/upload/schwab")
async def upload_schwab(file: UploadFile = File(...)):
    return await _do_upload(file, parse_schwab_csv, SCHWAB_CACHE, "Schwab")


@app.post("/api/portfolio/upload/coinbase")
async def upload_coinbase(file: UploadFile = File(...)):
    return await _do_upload(file, parse_coinbase_csv, COINBASE_CACHE, "Coinbase")


@app.post("/api/portfolio/upload/robinhood")
async def upload_robinhood(file: UploadFile = File(...)):
    return await _do_upload(file, parse_robinhood_csv, ROBINHOOD_CACHE, "Robinhood")


# ── Read endpoints ────────────────────────────────────────────────────────────

@app.get("/api/portfolio/positions")        # backwards-compat alias
@app.get("/api/portfolio/schwab")
async def get_schwab():
    return _load_cache(SCHWAB_CACHE) or {"positions": [], "total_value": 0, "account": "schwab"}


@app.get("/api/portfolio/coinbase")
async def get_coinbase():
    return _load_cache(COINBASE_CACHE) or {"positions": [], "total_value": 0, "account": "coinbase"}


@app.get("/api/portfolio/robinhood")
async def get_robinhood():
    return _load_cache(ROBINHOOD_CACHE) or {"positions": [], "total_value": 0, "account": "robinhood"}


@app.get("/api/portfolio/overview")
async def get_overview():
    """Combine all three accounts into a single overview response."""
    schwab    = _load_cache(SCHWAB_CACHE)    or {"positions": [], "total_value": 0, "total_cost": 0, "total_gain_dollar": 0, "total_day_change": 0, "cash": 0}
    coinbase  = _load_cache(COINBASE_CACHE)  or {"positions": [], "total_value": 0, "total_cost": 0, "total_gain_dollar": 0, "total_day_change": 0, "cash": 0}
    robinhood = _load_cache(ROBINHOOD_CACHE) or {"positions": [], "total_value": 0, "total_cost": 0, "total_gain_dollar": 0, "total_day_change": 0, "cash": 0}

    all_positions = (
        [dict(p, account="Schwab")    for p in schwab["positions"]]   +
        [dict(p, account="Coinbase")  for p in coinbase["positions"]] +
        [dict(p, account="Robinhood") for p in robinhood["positions"]]
    )

    total_value      = schwab["total_value"]    + coinbase["total_value"]    + robinhood["total_value"]
    total_cost       = schwab["total_cost"]     + coinbase["total_cost"]     + robinhood["total_cost"]
    total_gain       = schwab["total_gain_dollar"] + coinbase["total_gain_dollar"] + robinhood["total_gain_dollar"]
    total_day_change = schwab["total_day_change"]  + coinbase["total_day_change"]  + robinhood["total_day_change"]
    total_cash       = schwab.get("cash", 0)    + coinbase.get("cash", 0)    + robinhood.get("cash", 0)
    prev_value       = total_value - total_day_change
    total_day_pct    = (total_day_change / prev_value * 100) if prev_value else 0

    # Top 10 holdings by market value
    top10 = sorted(all_positions, key=lambda p: p.get("market_value", 0), reverse=True)[:10]

    # Asset class allocation
    allocation = {"Stocks": 0.0, "ETFs": 0.0, "Crypto": 0.0, "Cash": round(total_cash, 2)}
    for p in all_positions:
        mv  = p.get("market_value", 0)
        cls = p.get("asset_class", "stock")
        st  = p.get("security_type", "").lower()
        if cls == "crypto" or "crypto" in st:
            allocation["Crypto"] += mv
        elif "etf" in st:
            allocation["ETFs"] += mv
        else:
            allocation["Stocks"] += mv

    # Account breakdown
    breakdown = {
        "Schwab":    round(schwab["total_value"], 2),
        "Coinbase":  round(coinbase["total_value"], 2),
        "Robinhood": round(robinhood["total_value"], 2),
    }

    return {
        "total_value":      round(total_value, 2),
        "total_cost":       round(total_cost, 2),
        "total_gain_dollar":round(total_gain, 2),
        "total_gain_pct":   round((total_gain / total_cost * 100) if total_cost else 0, 2),
        "total_day_change": round(total_day_change, 2),
        "total_day_pct":    round(total_day_pct, 2),
        "total_cash":       round(total_cash, 2),
        "top10":            top10,
        "allocation":       {k: round(v, 2) for k, v in allocation.items()},
        "account_breakdown": breakdown,
        "accounts_loaded":  [a for a, v in breakdown.items() if v > 0],
        "updated_at":       datetime.now().isoformat(),
    }


# ============ Analyst Report ============

@app.get("/api/report")
async def get_analyst_report(force: bool = False):
    """Return cached daily AI analyst report, or generate a new one."""
    try:
        result = await asyncio.get_event_loop().run_in_executor(
            None, analyst_report.generate, force
        )
        return result
    except Exception as e:
        logger.error(f"Report endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============ Technical Analysis ============

@app.get("/api/ta/{symbol}")
async def get_technical_analysis(symbol: str, asset_class: str = "stock"):
    """
    Return RSI, 50/200-day MA, P/E, earnings growth, dividend yield,
    and composite score (0-100) with plain-English explanations.
    """
    try:
        result = await asyncio.get_event_loop().run_in_executor(
            None, technical_analyzer.analyze, symbol.upper(), asset_class
        )
        return result
    except Exception as e:
        logger.error(f"TA error for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Error handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}")
    return {
        "detail": str(exc),
        "timestamp": datetime.now().isoformat()
    }
