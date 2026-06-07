"""
AI Analyzer
Uses Ollama to generate investment insights and recommendations
"""

import requests
import json
import logging
from typing import Dict, List
import os

logger = logging.getLogger(__name__)


class AIAnalyzer:
    """Generate AI-powered investment insights using Ollama"""
    
    def __init__(self, ollama_host: str = "http://host.docker.internal:11434"):
        self.ollama_host = ollama_host
        self.model = "neural-chat"  # Default model
        self.timeout = 30
    
    def is_ollama_available(self) -> bool:
        """Check if Ollama is running and accessible"""
        try:
            response = requests.get(
                f"{self.ollama_host}/api/tags",
                timeout=5
            )
            return response.status_code == 200
        except:
            return False
    
    def generate_insight(self, asset_data: Dict, asset_type: str = "stock") -> Dict:
        """
        Generate AI insight for an asset
        
        Args:
            asset_data: Dict with score data and metrics
            asset_type: "stock" or "crypto"
        
        Returns:
            Dict with AI-generated insight
        """
        if not self.is_ollama_available():
            return {
                'symbol': asset_data.get('symbol'),
                'insight': 'AI analysis unavailable',
                'error': 'Ollama not responding'
            }
        
        # Build prompt based on asset type
        if asset_type == "stock":
            prompt = self._build_stock_prompt(asset_data)
        else:
            prompt = self._build_crypto_prompt(asset_data)
        
        try:
            response = requests.post(
                f"{self.ollama_host}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "temperature": 0.7,
                    "top_p": 0.9
                },
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                insight_text = result.get('response', '').strip()
                
                return {
                    'symbol': asset_data.get('symbol'),
                    'insight': insight_text,
                    'model': self.model,
                    'timestamp': asset_data.get('timestamp')
                }
            else:
                return {
                    'symbol': asset_data.get('symbol'),
                    'insight': 'Unable to generate insight',
                    'error': f"API error {response.status_code}"
                }
        
        except requests.Timeout:
            return {
                'symbol': asset_data.get('symbol'),
                'insight': 'AI analysis timed out',
                'error': 'Request timeout'
            }
        except Exception as e:
            logger.error(f"Error generating insight for {asset_data.get('symbol')}: {e}")
            return {
                'symbol': asset_data.get('symbol'),
                'insight': 'Error generating insight',
                'error': str(e)
            }
    
    def _build_stock_prompt(self, data: Dict) -> str:
        """Build prompt for stock analysis"""
        symbol = data.get('symbol', 'UNKNOWN')
        score = data.get('score', 0)
        scores = data.get('scores', {})
        metrics = data.get('metrics', {})
        sector = data.get('sector', 'Unknown sector')
        price = data.get('price', 0)
        
        prompt = f"""Analyze this stock investment opportunity briefly (2-3 sentences max):

Stock: {symbol}
Current Price: ${price:.2f}
Sector: {sector}

Investment Score: {score}/100
- Growth Score: {scores.get('growth', 0)}/100
- Dividend Score: {scores.get('dividend', 0)}/100  
- Momentum Score: {scores.get('momentum', 0)}/100

Key Metrics:
- 30-Day Return: {metrics.get('return_30d', 0)}%
- 90-Day Return: {metrics.get('return_90d', 0)}%
- P/E Ratio: {metrics.get('pe_ratio', 'N/A')}
- Dividend Yield: {metrics.get('dividend_yield', 0):.2%}
- Earnings Growth: {metrics.get('earnings_growth', 0):.2%}

Provide:
1. Why this score (key drivers)
2. Risk level (low/medium/high)
3. Best suited for (conservative/balanced/aggressive investors)
4. One caution to watch

Keep response under 150 words, professional tone."""
        
        return prompt
    
    def _build_crypto_prompt(self, data: Dict) -> str:
        """Build prompt for crypto analysis"""
        symbol = data.get('symbol', 'UNKNOWN')
        score = data.get('score', 0)
        scores = data.get('scores', {})
        metrics = data.get('metrics', {})
        price = data.get('price', 0)
        
        prompt = f"""Analyze this cryptocurrency briefly (2-3 sentences max):

Crypto: {symbol}
Current Price: ${price:.2f}

Investment Score: {score}/100
- Momentum Score: {scores.get('momentum', 0)}/100
- Market Health: {scores.get('market_health', 0)}/100

Recent Performance:
- 24h Change: {metrics.get('return_24h', 0):.2f}%
- 7d Change: {metrics.get('return_7d', 0):.2f}%
- 30d Change: {metrics.get('return_30d', 0):.2f}%

Provide:
1. Current market sentiment (bullish/neutral/bearish)
2. What's driving the momentum
3. Risk level (low/medium/high/very high)
4. Who should consider this (traders/investors/risk-averse)

Keep response under 120 words, professional tone."""
        
        return prompt
    
    def generate_daily_summary(self, top_stocks: List[Dict], top_cryptos: List[Dict]) -> str:
        """Generate a daily market summary"""
        
        if not self.is_ollama_available():
            return "Daily summary unavailable - AI not responding"
        
        # Build data summary
        stock_symbols = [s.get('symbol') for s in top_stocks[:5]]
        crypto_symbols = [c.get('symbol') for c in top_cryptos[:3]]
        avg_stock_score = sum(s.get('score', 0) for s in top_stocks[:5]) / min(5, len(top_stocks)) if top_stocks else 0
        avg_crypto_score = sum(c.get('score', 0) for c in top_cryptos[:3]) / min(3, len(top_cryptos)) if top_cryptos else 0
        
        prompt = f"""Generate a brief daily market summary for an investment dashboard (100-150 words):

Top 5 Stocks Today: {', '.join(stock_symbols)}
Average Stock Score: {avg_stock_score:.1f}/100

Top 3 Cryptos Today: {', '.join(crypto_symbols)}
Average Crypto Score: {avg_crypto_score:.1f}/100

Create a summary that:
1. Highlights the overall market mood
2. Notes if stocks or cryptos are performing better
3. Mentions one opportunity and one caution
4. Recommends action (buy/hold/wait)

Professional tone, actionable insights."""
        
        try:
            response = requests.post(
                f"{self.ollama_host}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "temperature": 0.7,
                    "top_p": 0.9
                },
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get('response', '').strip()
            else:
                return "Unable to generate summary"
        
        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            return "Summary generation error"
    
    def get_risk_assessment(self, asset_data: Dict) -> Dict:
        """Quick risk assessment without AI (fallback when AI unavailable)"""
        score = asset_data.get('score', 50)
        volatility = abs(asset_data.get('metrics', {}).get('return_30d', 0))
        
        if score < 30:
            risk_level = "Very High"
            risk_color = "red"
        elif score < 50:
            risk_level = "High"
            risk_color = "orange"
        elif score < 70:
            risk_level = "Medium"
            risk_color = "yellow"
        else:
            risk_level = "Low"
            risk_color = "green"
        
        return {
            'symbol': asset_data.get('symbol'),
            'risk_level': risk_level,
            'risk_color': risk_color,
            'score': score,
            'volatility': round(volatility, 2)
        }
