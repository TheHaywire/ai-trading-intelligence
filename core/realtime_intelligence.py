"""
REAL-TIME MARKET INTELLIGENCE
Powered by Gemini AI + Finnhub real-time data

This module provides:
- Real-time news sentiment analysis (Finnhub)
- AI-powered market analysis (Gemini)
- Live market data streaming
- Smart trade recommendations
"""

import os
import requests
import json
from datetime import datetime, timedelta
import google.generativeai as genai

# API Keys
GEMINI_API_KEY = "AIzaSyDfTNLfwi2il65osKyHBi1mUcaOkQ3tUN8"
FINNHUB_API_KEY = "d1cp2vpr01qic6lf39lgd1cp2vpr01qic6lf39m0"

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)


class FinnhubClient:
    """Finnhub API client for real-time market data"""

    def __init__(self):
        self.base_url = "https://finnhub.io/api/v1"
        self.api_key = FINNHUB_API_KEY
        self.headers = {"X-Finnhub-Token": self.api_key}

    def get_quote(self, symbol):
        """Get real-time quote for a symbol"""
        # Convert MT5 symbols to Finnhub format
        symbol_map = {
            "EURUSD": "OANDA:EUR_USD",
            "GBPUSD": "OANDA:GBP_USD",
            "USDJPY": "OANDA:USD_JPY",
            "AUDUSD": "OANDA:AUD_USD",
            "USDCAD": "OANDA:USD_CAD",
            "USDCHF": "OANDA:USD_CHF",
            "GOLD": "OANDA:XAU_USD",
            "SILVER": "OANDA:XAG_USD",
            "BTCUSD": "BINANCE:BTCUSDT"
        }

        finnhub_symbol = symbol_map.get(symbol, symbol)

        try:
            response = requests.get(
                f"{self.base_url}/quote",
                params={"symbol": finnhub_symbol},
                headers=self.headers,
                timeout=5
            )

            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            print(f"[Finnhub Quote Error] {symbol}: {e}")
            return None

    def get_news(self, category="forex", count=10):
        """Get latest market news"""
        try:
            response = requests.get(
                f"{self.base_url}/news",
                params={"category": category, "minId": 0},
                headers=self.headers,
                timeout=10
            )

            if response.status_code == 200:
                news = response.json()
                return news[:count]  # Limit to count items
            return []
        except Exception as e:
            print(f"[Finnhub News Error]: {e}")
            return []

    def get_market_sentiment(self, symbol):
        """Get market sentiment for a symbol"""
        try:
            response = requests.get(
                f"{self.base_url}/news-sentiment",
                params={"symbol": symbol},
                headers=self.headers,
                timeout=10
            )

            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            print(f"[Finnhub Sentiment Error] {symbol}: {e}")
            return None

    def get_recommendations(self, symbol):
        """Get analyst recommendations"""
        try:
            response = requests.get(
                f"{self.base_url}/stock/recommendation",
                params={"symbol": symbol},
                headers=self.headers,
                timeout=10
            )

            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            print(f"[Finnhub Recommendations Error] {symbol}: {e}")
            return None


class GeminiAIAnalyzer:
    """Gemini AI for intelligent market analysis"""

    def __init__(self):
        self.model = genai.GenerativeModel('gemini-2.0-flash')  # Use latest available Gemini model
        self.requests_today = 0
        self.max_requests_per_day = 50  # Conservative limit for free tier

    def can_make_request(self):
        """Check if we can make more API requests (rate limiting)"""
        return self.requests_today < self.max_requests_per_day

    def analyze_market_setup(self, symbol, technical_data, news_data):
        """
        Get AI-powered analysis of a trading setup

        Args:
            symbol: Trading symbol
            technical_data: Dict with RSI, MACD, trend, etc.
            news_data: Recent news headlines and sentiment
        """
        if not self.can_make_request():
            return {
                'ai_verdict': 'NEUTRAL',
                'ai_reasoning': 'Rate limit reached for today. Using technical analysis only.',
                'ai_confidence': 0
            }

        # Prepare prompt
        prompt = f"""You are an expert quantitative trading analyst. Analyze this trading setup and provide a CLEAR verdict.

SYMBOL: {symbol}

TECHNICAL ANALYSIS:
- Current Price: {technical_data.get('price', 'N/A')}
- Trend: {technical_data.get('trend', 'N/A')} (Score: {technical_data.get('trend_score', 'N/A')})
- RSI: {technical_data.get('rsi', 'N/A')}
- MACD: {technical_data.get('macd', 'N/A')}
- MACD Signal: {technical_data.get('macd_signal', 'N/A')}
- Setup Quality Score: {technical_data.get('score', 0)}/100

RECENT MARKET NEWS:
{self._format_news(news_data)}

TASK:
Based on the technical setup and news sentiment, provide your analysis in this EXACT format:

VERDICT: [BUY/SELL/HOLD - one word only]
CONFIDENCE: [0-100 integer only]
KEY_REASON: [One sentence explaining the most important factor]
RISK_FACTOR: [One sentence about the biggest risk]

Keep it concise and actionable. Focus on what matters most."""

        try:
            self.requests_today += 1
            response = self.model.generate_content(prompt)
            result = self._parse_ai_response(response.text)

            return result

        except Exception as e:
            print(f"[Gemini AI Error] {symbol}: {e}")
            return {
                'ai_verdict': 'NEUTRAL',
                'ai_reasoning': f'AI analysis unavailable: {str(e)}',
                'ai_confidence': 0,
                'ai_risk': 'Unable to assess'
            }

    def _format_news(self, news_data):
        """Format news data for AI prompt"""
        if not news_data or len(news_data) == 0:
            return "No recent news available"

        formatted = []
        for item in news_data[:5]:  # Top 5 news items
            headline = item.get('headline', 'N/A')
            summary = item.get('summary', '')[:100]  # First 100 chars
            formatted.append(f"- {headline}")
            if summary:
                formatted.append(f"  {summary}...")

        return "\n".join(formatted)

    def _parse_ai_response(self, response_text):
        """Parse structured response from Gemini"""
        lines = response_text.strip().split('\n')

        result = {
            'ai_verdict': 'NEUTRAL',
            'ai_reasoning': '',
            'ai_confidence': 50,
            'ai_risk': 'Unknown'
        }

        for line in lines:
            line = line.strip()

            if line.startswith('VERDICT:'):
                verdict = line.replace('VERDICT:', '').strip().upper()
                if verdict in ['BUY', 'SELL', 'HOLD']:
                    result['ai_verdict'] = verdict

            elif line.startswith('CONFIDENCE:'):
                try:
                    conf = line.replace('CONFIDENCE:', '').strip()
                    conf = ''.join(c for c in conf if c.isdigit())
                    if conf:
                        result['ai_confidence'] = min(100, max(0, int(conf)))
                except:
                    pass

            elif line.startswith('KEY_REASON:'):
                result['ai_reasoning'] = line.replace('KEY_REASON:', '').strip()

            elif line.startswith('RISK_FACTOR:'):
                result['ai_risk'] = line.replace('RISK_FACTOR:', '').strip()

        return result

    def get_daily_market_briefing(self, symbols, news_data):
        """Get AI-powered daily market briefing"""
        if not self.can_make_request():
            return "Rate limit reached. Daily briefing unavailable."

        prompt = f"""You are a professional trading analyst providing a morning briefing to traders.

SYMBOLS WE TRADE: {', '.join(symbols)}

TODAY'S TOP NEWS:
{self._format_news(news_data)}

Provide a concise 3-4 sentence daily briefing covering:
1. Overall market sentiment
2. Key opportunities or risks
3. Sectors/assets to watch today

Be specific, actionable, and professional."""

        try:
            self.requests_today += 1
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            print(f"[Gemini Briefing Error]: {e}")
            return f"Daily briefing unavailable: {str(e)}"


# Global instances
finnhub = FinnhubClient()
gemini_ai = GeminiAIAnalyzer()


def get_realtime_intelligence(symbol, technical_data):
    """
    Get complete real-time intelligence for a symbol

    Args:
        symbol: Trading symbol
        technical_data: Dict with technical indicators

    Returns:
        Dict with real-time quote, news, and AI analysis
    """
    print(f"[Real-time Intelligence] Analyzing {symbol}...")

    # Get Finnhub data
    quote = finnhub.get_quote(symbol)
    news = finnhub.get_news(category="forex" if "USD" in symbol else "general", count=5)

    # Get AI analysis (uses Gemini conservatively)
    ai_analysis = gemini_ai.analyze_market_setup(symbol, technical_data, news)

    return {
        'quote': quote,
        'news': news,
        'ai_analysis': ai_analysis,
        'timestamp': datetime.now().isoformat()
    }


def get_market_overview():
    """Get overall market overview"""
    print("[Real-time Intelligence] Getting market overview...")

    # Get general market news
    forex_news = finnhub.get_news("forex", count=5)
    crypto_news = finnhub.get_news("crypto", count=3)
    general_news = finnhub.get_news("general", count=5)

    all_news = forex_news + crypto_news + general_news

    return {
        'news': all_news,
        'forex_news': forex_news,
        'crypto_news': crypto_news,
        'general_news': general_news,
        'timestamp': datetime.now().isoformat()
    }


def get_ai_daily_briefing(symbols):
    """Get AI-powered daily briefing"""
    print("[Real-time Intelligence] Generating AI daily briefing...")

    news = finnhub.get_news("forex", count=10)
    briefing = gemini_ai.get_daily_market_briefing(symbols, news)

    return {
        'briefing': briefing,
        'news_analyzed': len(news),
        'timestamp': datetime.now().isoformat()
    }


if __name__ == "__main__":
    # Test the module
    print("=" * 80)
    print("REAL-TIME INTELLIGENCE TEST")
    print("=" * 80)
    print()

    # Test Finnhub
    print("[1] Testing Finnhub API...")
    quote = finnhub.get_quote("EURUSD")
    if quote:
        print(f"✓ EURUSD Quote: {quote}")
    else:
        print("✗ Quote fetch failed")

    news = finnhub.get_news("forex", count=3)
    print(f"✓ Fetched {len(news)} news items")

    # Test Gemini AI
    print("\n[2] Testing Gemini AI...")
    test_data = {
        'price': 1.0850,
        'trend': 'UPTREND',
        'trend_score': 7,
        'rsi': 55,
        'macd': 0.0005,
        'macd_signal': 0.0003,
        'score': 72
    }

    ai_result = gemini_ai.analyze_market_setup("EURUSD", test_data, news)
    print(f"✓ AI Verdict: {ai_result['ai_verdict']}")
    print(f"✓ AI Confidence: {ai_result['ai_confidence']}%")
    print(f"✓ AI Reasoning: {ai_result['ai_reasoning']}")

    print("\n[DONE]")
