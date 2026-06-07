"""
Stock Analyzer
Orchestrates data fetching, metric calculation, and AI analysis
"""

import json
import logging
from typing import Dict, List
from datetime import datetime
from stock_data_fetcher import DataFetcherManager
from metrics_calculator import MetricsCalculator
from ai_analyzer import AIAnalyzer

logger = logging.getLogger(__name__)


class StockAnalyzer:
    """Main coordinator for stock and crypto analysis"""
    
    def __init__(self, watchlist_path: str = 'config/watchlist.json', cache_dir: str = '/tmp/finance_cache'):
        self.data_fetcher = DataFetcherManager(watchlist_path)
        self.watchlist = self.data_fetcher.watchlist
        self.cache_dir = cache_dir
        
        # Load stock and crypto weights
        stock_weights = self.watchlist.get('score_weights', {}).get('stocks', {
            'growth': 0.4,
            'dividend': 0.2,
            'momentum': 0.4
        })
        crypto_weights = self.watchlist.get('score_weights', {}).get('crypto', {
            'growth': 0.4,
            'market_health': 0.2,
            'momentum': 0.4
        })
        
        self.stock_calculator = MetricsCalculator(stock_weights)
        self.crypto_calculator = MetricsCalculator(crypto_weights)
        self.ai_analyzer = AIAnalyzer()
        
        logger.info(f"StockAnalyzer initialized with {len(self._get_all_stocks())} stocks and {len(self._get_all_cryptos())} cryptos")
    
    def _get_all_stocks(self) -> List[str]:
        """Get all stock symbols from watchlist"""
        stocks = self.watchlist.get('stocks', [])
        if isinstance(stocks, list):
            return stocks
        # If still nested
        all_stocks = []
        for category, symbols in stocks.items():
            all_stocks.extend(symbols)
        return all_stocks
    
    def _get_all_cryptos(self) -> List[str]:
        """Get all crypto symbols from watchlist"""
        cryptos = self.watchlist.get('cryptos', [])
        if isinstance(cryptos, list):
            return cryptos
        # If still nested
        return cryptos.get('major', [])
    
    def analyze_all(self, include_ai: bool = True) -> Dict:
        """
        Analyze all stocks and cryptos, return ranked results
        
        Args:
            include_ai: Whether to include AI insights (slower but richer)
        
        Returns:
            Dict with top stocks and cryptos with scores and insights
        """
        logger.info("Starting analysis of all assets...")
        
        # Fetch data for all assets
        all_data = self.data_fetcher.fetch_all_assets()
        
        # Calculate scores
        stock_scores = []
        for stock_data in all_data.get('stocks', []):
            score_data = self.stock_calculator.calculate_stock_score(stock_data)
            stock_scores.append(score_data)
        
        crypto_scores = []
        for crypto_data in all_data.get('cryptos', []):
            score_data = self.crypto_calculator.calculate_crypto_score(crypto_data)
            crypto_scores.append(score_data)
        
        # Rank
        top_stocks = self.stock_calculator.rank_assets(stock_scores, top_n=10)
        top_cryptos = self.crypto_calculator.rank_assets(crypto_scores, top_n=5)
        
        # Add AI insights if requested
        if include_ai:
            for stock in top_stocks:
                ai_insight = self.ai_analyzer.generate_insight(stock, asset_type="stock")
                stock['ai_insight'] = ai_insight.get('insight')
                stock['risk_assessment'] = self.ai_analyzer.get_risk_assessment(stock)
            
            for crypto in top_cryptos:
                ai_insight = self.ai_analyzer.generate_insight(crypto, asset_type="crypto")
                crypto['ai_insight'] = ai_insight.get('insight')
                crypto['risk_assessment'] = self.ai_analyzer.get_risk_assessment(crypto)
        
        # Generate daily summary
        daily_summary = self.ai_analyzer.generate_daily_summary(top_stocks, top_cryptos) if include_ai else ""
        
        result = {
            'timestamp': datetime.now().isoformat(),
            'ai_available': self.ai_analyzer.is_ollama_available(),
            'top_stocks': top_stocks,
            'top_cryptos': top_cryptos,
            'daily_summary': daily_summary,
            'stats': {
                'total_stocks_analyzed': len(stock_scores),
                'total_cryptos_analyzed': len(crypto_scores),
                'stocks_with_errors': len([s for s in stock_scores if 'error' in s]),
                'cryptos_with_errors': len([c for c in crypto_scores if 'error' in c])
            }
        }
        
        logger.info(f"Analysis complete. Top stock: {top_stocks[0]['symbol'] if top_stocks else 'N/A'}")
        
        return result
    
    def analyze_stock(self, symbol: str, include_ai: bool = True) -> Dict:
        """Analyze a single stock"""
        logger.info(f"Analyzing stock: {symbol}")
        
        # Fetch data
        stock_data = self.data_fetcher.fetch_stock(symbol)
        
        # Calculate score
        score_data = self.stock_calculator.calculate_stock_score(stock_data)
        
        # Add AI insight
        if include_ai:
            ai_insight = self.ai_analyzer.generate_insight(score_data, asset_type="stock")
            score_data['ai_insight'] = ai_insight.get('insight')
            score_data['risk_assessment'] = self.ai_analyzer.get_risk_assessment(score_data)
        
        score_data['raw_data'] = stock_data
        
        return score_data
    
    def analyze_crypto(self, symbol: str, include_ai: bool = True) -> Dict:
        """Analyze a single crypto"""
        logger.info(f"Analyzing crypto: {symbol}")
        
        # Fetch data
        crypto_data = self.data_fetcher.fetch_crypto(symbol)
        
        # Calculate score
        score_data = self.crypto_calculator.calculate_crypto_score(crypto_data)
        
        # Add AI insight
        if include_ai:
            ai_insight = self.ai_analyzer.generate_insight(score_data, asset_type="crypto")
            score_data['ai_insight'] = ai_insight.get('insight')
            score_data['risk_assessment'] = self.ai_analyzer.get_risk_assessment(score_data)
        
        score_data['raw_data'] = crypto_data
        
        return score_data
    
    def get_watchlist(self) -> Dict:
        """Return the current watchlist configuration"""
        return self.watchlist
    
    def search_stocks_by_sector(self, sector: str, top_scores: List[Dict]) -> List[Dict]:
        """Filter top stocks by sector"""
        return [s for s in top_scores if s.get('sector') == sector]


# Simple test
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    analyzer = StockAnalyzer()
    
    # Test single stock analysis
    print("\n=== Testing Single Stock Analysis ===")
    nvidia = analyzer.analyze_stock("NVDA", include_ai=False)  # Set False to skip AI for testing
    print(f"NVDA Score: {nvidia.get('score')}")
    print(f"Growth: {nvidia.get('scores', {}).get('growth')}")
    print(f"Momentum: {nvidia.get('scores', {}).get('momentum')}")
    
    # Test single crypto analysis
    print("\n=== Testing Single Crypto Analysis ===")
    bitcoin = analyzer.analyze_crypto("BTC", include_ai=False)
    print(f"BTC Score: {bitcoin.get('score')}")
    print(f"Price: ${bitcoin.get('price')}")
