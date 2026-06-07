from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, List
import aiohttp
import asyncio
import os
from datetime import datetime
import json
import httpx
from functools import lru_cache
import logging

# Import stock screening modules
from stock_analyzer import StockAnalyzer
from ai_analyzer import AIAnalyzer

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

# Error handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}")
    return {
        "detail": str(exc),
        "timestamp": datetime.now().isoformat()
    }
