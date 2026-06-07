from typing import Dict, List
import logging

logger = logging.getLogger(__name__)

class MetricsCalculator:
    """Calculate composite scores for stocks and cryptos"""
    
    def __init__(self, weights=None):
        # Accept optional weights parameter
        if weights:
            self.weights = weights
        else:
            self.weights = {
                'growth': 0.4,
                'dividend': 0.2,
                'momentum': 0.4
            }
    
    def safe_round(self, value, decimals=2):
        """Safely round a value, handling None"""
        try:
            val = float(value or 0)
            return round(val, decimals)
        except (TypeError, ValueError):
            return 0.0
    
    def score_growth(self, stock_data: Dict) -> float:
        """Score growth potential (0-100)"""
        try:
            if 'error' in stock_data:
                return 0.0
            
            score = 0
            weight_count = 0
            
            earnings_growth = stock_data.get('earnings_growth')
            if earnings_growth is not None and earnings_growth > 0:
                eg_score = min(40, (float(earnings_growth) * 100) / 0.75)
                score += eg_score
                weight_count += 1
            
            revenue_growth = stock_data.get('revenue_growth')
            if revenue_growth is not None and revenue_growth > 0:
                rg_score = min(30, (float(revenue_growth) * 100) / 1.0)
                score += rg_score
                weight_count += 1
            
            return_30d = stock_data.get('return_30d')
            if return_30d is not None:
                ret_30 = float(return_30d)
                momentum_score = 15 + (ret_30 / 2)
                momentum_score = max(0, min(30, momentum_score))
                score += momentum_score
                weight_count += 1
            
            if weight_count == 0:
                return 0.0
            
            return min(100, score / weight_count * 2)
        except Exception as e:
            logger.warning(f"Error in score_growth: {e}")
            return 0.0
    
    def score_dividend(self, stock_data: Dict) -> float:
        """Score dividend attractiveness (0-100)"""
        try:
            if 'error' in stock_data:
                return 0.0
            
            score = 0
            weight_count = 0
            
            div_yield = stock_data.get('dividend_yield')
            if div_yield is not None and div_yield > 0:
                div_yield_float = float(div_yield)
                div_score = min(60, (div_yield_float * 100) * 20)
                score += div_score
                weight_count += 1
            else:
                score += 0
                weight_count += 1
            
            if div_yield is not None and div_yield > 0:
                score += 40
                weight_count += 1
            
            if weight_count == 0:
                return 0.0
            
            return min(100, score / weight_count)
        except Exception as e:
            logger.warning(f"Error in score_dividend: {e}")
            return 0.0
    
    def score_momentum(self, stock_data: Dict) -> float:
        """Score technical momentum (0-100)"""
        try:
            if 'error' in stock_data:
                return 0.0
            
            score = 0
            weight_count = 0
            
            return_30d = stock_data.get('return_30d')
            if return_30d is not None:
                ret_30 = float(return_30d)
                momentum_30d = 25 + (ret_30 / 2)
                momentum_30d = max(0, min(50, momentum_30d))
                score += momentum_30d
                weight_count += 1
            
            return_90d = stock_data.get('return_90d')
            if return_90d is not None:
                ret_90 = float(return_90d)
                momentum_90d = 25 + (ret_90 / 2.4)
                momentum_90d = max(0, min(50, momentum_90d))
                score += momentum_90d
                weight_count += 1
            
            if weight_count == 0:
                return 0.0
            
            return min(100, score / weight_count)
        except Exception as e:
            logger.warning(f"Error in score_momentum: {e}")
            return 0.0
    
    def calculate_stock_score(self, stock_data: Dict) -> Dict:
        """Calculate composite score for a stock"""
        try:
            if 'error' in stock_data:
                return {
                    'symbol': stock_data.get('symbol', 'UNKNOWN'),
                    'error': stock_data.get('error', 'Unknown error'),
                    'score': 0
                }
            
            growth_score = self.score_growth(stock_data) or 0.0
            dividend_score = self.score_dividend(stock_data) or 0.0
            momentum_score = self.score_momentum(stock_data) or 0.0
            
            growth_score = float(growth_score) if growth_score is not None else 0.0
            dividend_score = float(dividend_score) if dividend_score is not None else 0.0
            momentum_score = float(momentum_score) if momentum_score is not None else 0.0
            
            composite = (
                (growth_score * self.weights.get('growth', 0.4)) +
                (dividend_score * self.weights.get('dividend', 0.2)) +
                (momentum_score * self.weights.get('momentum', 0.4))
            )
            
            return {
                'symbol': stock_data.get('symbol', 'UNKNOWN'),
                'price': self.safe_round(stock_data.get('price'), 2),
                'sector': stock_data.get('sector', 'N/A'),
                'score': self.safe_round(composite, 2),
                'scores': {
                    'growth': self.safe_round(growth_score, 2),
                    'dividend': self.safe_round(dividend_score, 2),
                    'momentum': self.safe_round(momentum_score, 2)
                },
                'metrics': {
                    'return_30d': self.safe_round(stock_data.get('return_30d'), 2),
                    'return_90d': self.safe_round(stock_data.get('return_90d'), 2),
                    'pe_ratio': self.safe_round(stock_data.get('pe_ratio'), 2),
                    'dividend_yield': self.safe_round(stock_data.get('dividend_yield'), 4),
                    'earnings_growth': self.safe_round(stock_data.get('earnings_growth'), 4)
                }
            }
        except Exception as e:
            logger.error(f"Error calculating stock score: {e}")
            return {
                'symbol': stock_data.get('symbol', 'UNKNOWN'),
                'error': f'Scoring error: {str(e)}',
                'score': 0
            }
    
    def score_market_health(self, crypto_data: Dict) -> float:
        """Score market health for crypto"""
        try:
            if 'error' in crypto_data:
                return 0.0
            return 50.0
        except:
            return 0.0
    
    def score_crypto_momentum(self, crypto_data: Dict) -> float:
        """Score technical momentum for crypto"""
        try:
            if 'error' in crypto_data:
                return 0.0
            
            score = 0
            weight_count = 0
            
            return_24h = crypto_data.get('return_24h')
            if return_24h is not None:
                ret_24 = float(return_24h)
                momentum_24h = 16.5 + (ret_24)
                momentum_24h = max(0, min(33, momentum_24h))
                score += momentum_24h
                weight_count += 1
            
            return_7d = crypto_data.get('return_7d')
            if return_7d is not None:
                ret_7 = float(return_7d)
                momentum_7d = 16.5 + (ret_7 / 2)
                momentum_7d = max(0, min(33, momentum_7d))
                score += momentum_7d
                weight_count += 1
            
            return_30d = crypto_data.get('return_30d')
            if return_30d is not None:
                ret_30 = float(return_30d)
                momentum_30d = 17 + (ret_30 / 3)
                momentum_30d = max(0, min(34, momentum_30d))
                score += momentum_30d
                weight_count += 1
            
            if weight_count == 0:
                return 0.0
            
            return min(100, score / weight_count)
        except Exception as e:
            logger.warning(f"Error in score_crypto_momentum: {e}")
            return 0.0
    
    def calculate_crypto_score(self, crypto_data: Dict) -> Dict:
        """Calculate composite score for a crypto"""
        try:
            if 'error' in crypto_data:
                return {
                    'symbol': crypto_data.get('symbol', 'UNKNOWN'),
                    'error': crypto_data.get('error', 'Unknown error'),
                    'score': 0
                }
            
            growth_score = self.score_crypto_momentum(crypto_data) or 0.0
            market_health_score = self.score_market_health(crypto_data) or 0.0
            momentum_score = self.score_crypto_momentum(crypto_data) or 0.0
            
            growth_score = float(growth_score) if growth_score is not None else 0.0
            market_health_score = float(market_health_score) if market_health_score is not None else 0.0
            momentum_score = float(momentum_score) if momentum_score is not None else 0.0
            
            composite = (
                (growth_score * self.weights.get('growth', 0.4)) +
                (market_health_score * self.weights.get('dividend', 0.2)) +
                (momentum_score * self.weights.get('momentum', 0.4))
            )
            
            return {
                'symbol': crypto_data.get('symbol', 'UNKNOWN'),
                'price': self.safe_round(crypto_data.get('price'), 2),
                'market_cap': crypto_data.get('market_cap'),
                'score': self.safe_round(composite, 2),
                'scores': {
                    'momentum': self.safe_round(momentum_score, 2),
                    'market_health': self.safe_round(market_health_score, 2)
                },
                'metrics': {
                    'return_24h': self.safe_round(crypto_data.get('return_24h'), 2),
                    'return_7d': self.safe_round(crypto_data.get('return_7d'), 2),
                    'return_30d': self.safe_round(crypto_data.get('return_30d'), 2)
                }
            }
        except Exception as e:
            logger.error(f"Error calculating crypto score: {e}")
            return {
                'symbol': crypto_data.get('symbol', 'UNKNOWN'),
                'error': f'Scoring error: {str(e)}',
                'score': 0
            }
    
    def rank_assets(self, assets: List[Dict], top_n: int = 10) -> List[Dict]:
        """Rank assets by composite score"""
        try:
            valid_assets = [a for a in assets if 'error' not in a]
            sorted_assets = sorted(valid_assets, key=lambda x: x.get('score', 0), reverse=True)
            return sorted_assets[:top_n]
        except Exception as e:
            logger.error(f"Error ranking assets: {e}")
            return []
