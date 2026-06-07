import requests
import logging
import time
import json
from typing import Dict, List
from pathlib import Path

logger = logging.getLogger(__name__)

ALPHA_VANTAGE_KEY = "demo"  # Replace with your free key from alphavantage.co
ALPHA_VANTAGE_URL = "https://www.alphavantage.co/query"

class StockDataFetcher:
    """Fetch stock data from Alpha Vantage"""
    
    def __init__(self):
        self.delay = 12.5  # 5 requests/min = 1 request per 12 seconds
    
    def fetch_stock(self, symbol: str) -> Dict:
        """Fetch a single stock's data"""
        try:
            time.sleep(self.delay)
            logger.info(f"Fetching stock data for {symbol}...")
            
            params = {
                "function": "GLOBAL_QUOTE",
                "symbol": symbol,
                "apikey": ALPHA_VANTAGE_KEY
            }
            
            response = requests.get(ALPHA_VANTAGE_URL, params=params, timeout=10)
            data = response.json()
            
            if "Global Quote" not in data or not data["Global Quote"]:
                return {'symbol': symbol, 'error': 'No data found'}
            
            quote = data["Global Quote"]
            
            # Also fetch daily data for returns
            params2 = {
                "function": "TIME_SERIES_DAILY",
                "symbol": symbol,
                "apikey": ALPHA_VANTAGE_KEY
            }
            
            time.sleep(self.delay)
            response2 = requests.get(ALPHA_VANTAGE_URL, params=params2, timeout=10)
            daily_data = response2.json()
            
            # Calculate returns
            return_30d = 0
            return_90d = 0
            
            if "Time Series (Daily)" in daily_data:
                ts = daily_data["Time Series (Daily)"]
                dates = sorted(ts.keys())
                if len(dates) > 0:
                    current = float(quote.get("05. price", 0))
                    if len(dates) > 22:
                        price_30d_ago = float(ts[dates[-22]].get("4. close", current))
                        return_30d = ((current - price_30d_ago) / price_30d_ago * 100) if price_30d_ago else 0
                    if len(dates) > 64:
                        price_90d_ago = float(ts[dates[-64]].get("4. close", current))
                        return_90d = ((current - price_90d_ago) / price_90d_ago * 100) if price_90d_ago else 0
            
            return {
                'symbol': symbol,
                'price': float(quote.get("05. price", 0)),
                'sector': 'N/A',
                'pe_ratio': None,
                'dividend_yield': None,
                'earnings_growth': None,
                'revenue_growth': None,
                'return_30d': return_30d,
                'return_90d': return_90d,
                'volume': int(quote.get("06. volume", 0))
            }
        
        except Exception as e:
            logger.error(f"Error fetching {symbol}: {e}")
            return {'symbol': symbol, 'error': str(e)[:100]}

class CryptoDataFetcher:
    """Fetch crypto data from CoinGecko"""
    
    def __init__(self):
        self.gecko_ids = {
            'BTC': 'bitcoin', 'ETH': 'ethereum', 'XRP': 'ripple', 'ADA': 'cardano',
            'SOL': 'solana', 'DOGE': 'dogecoin', 'LINK': 'chainlink', 'USDT': 'tether',
            'DOT': 'polkadot', 'MATIC': 'matic-network', 'AVAX': 'avalanche-2',
            'ARB': 'arbitrum', 'OP': 'optimism', 'PEPE': 'pepe', 'SHIB': 'shiba-inu',
            'NEAR': 'near', 'FTM': 'fantom', 'AAVE': 'aave', 'UNI': 'uniswap'
        }
    
    def fetch_crypto(self, symbol: str) -> Dict:
        try:
            time.sleep(1.0)
            gecko_id = self.gecko_ids.get(symbol)
            if not gecko_id:
                return {'symbol': symbol, 'error': 'Unknown crypto symbol'}
            
            url = f"https://api.coingecko.com/api/v3/coins/{gecko_id}"
            resp = requests.get(url, params={
                'localization': 'false', 'tickers': 'false', 'market_data': 'true',
                'community_data': 'false', 'developer_data': 'false'
            }, timeout=5)
            resp.raise_for_status()
            data = resp.json()
            
            market_data = data.get('market_data', {})
            
            return {
                'symbol': symbol,
                'price': market_data.get('current_price', {}).get('usd'),
                'market_cap': market_data.get('market_cap', {}).get('usd'),
                'return_24h': market_data.get('price_change_percentage_24h', 0),
                'return_7d': market_data.get('price_change_percentage_7d', 0),
                'return_30d': market_data.get('price_change_percentage_30d', 0)
            }
        except Exception as e:
            logger.error(f"Error fetching crypto {symbol}: {e}")
            return {'symbol': symbol, 'error': str(e)[:100]}

class DataFetcherManager:
    def __init__(self, watchlist_path=None):
        self.stock_fetcher = StockDataFetcher()
        self.crypto_fetcher = CryptoDataFetcher()
        self.watchlist = self._load_watchlist(watchlist_path)
    
    def _load_watchlist(self, watchlist_path=None):
        try:
            if watchlist_path is None:
                watchlist_path = Path(__file__).parent / 'config' / 'watchlist.json'
            
            with open(watchlist_path, 'r') as f:
                data = json.load(f)
            
            stocks = []
            if 'stocks' in data and isinstance(data['stocks'], dict):
                for category, symbols in data['stocks'].items():
                    stocks.extend(symbols)
            
            cryptos = []
            if 'crypto' in data and isinstance(data['crypto'], dict):
                for category, symbols in data['crypto'].items():
                    cryptos.extend(symbols)
            
            return {'stocks': stocks, 'cryptos': cryptos}
        except Exception as e:
            logger.error(f"Error loading watchlist: {e}")
            return {'stocks': [], 'cryptos': []}
    
    def fetch_stocks(self, symbols: List[str]) -> List[Dict]:
        return [self.stock_fetcher.fetch_stock(symbol) for symbol in symbols]
    
    def fetch_cryptos(self, symbols: List[str]) -> List[Dict]:
        return [self.crypto_fetcher.fetch_crypto(symbol) for symbol in symbols]
    
    def fetch_all_assets(self):
        stocks = self.fetch_stocks(self.watchlist.get('stocks', []))
        cryptos = self.fetch_cryptos(self.watchlist.get('cryptos', []))
        return {"stocks": stocks, "cryptos": cryptos}
