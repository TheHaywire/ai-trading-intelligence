"""
CONFIGURATION TEMPLATE
Copy this file to config.py and fill in your own API keys and settings.
"""

# =============================================================================
# API KEYS - GET YOUR FREE KEYS HERE:
# =============================================================================

# Google Gemini AI
# Get your free API key at: https://ai.google.dev/
# Free tier: 50 requests per day
GEMINI_API_KEY = "your_gemini_api_key_here"

# Finnhub Market Data
# Get your free API key at: https://finnhub.io/register
# Free tier: 60 calls/minute
FINNHUB_API_KEY = "your_finnhub_api_key_here"

# =============================================================================
# EMAIL CONFIGURATION (for receiving reports)
# =============================================================================

# EmailJS Configuration (used for sending email reports)
# Sign up for free at: https://www.emailjs.com/
# Follow their setup guide to get these values
EMAILJS_SERVICE_ID = "your_emailjs_service_id"
EMAILJS_TEMPLATE_ID = "your_emailjs_template_id"
EMAILJS_PUBLIC_KEY = "your_emailjs_public_key"
EMAILJS_PRIVATE_KEY = "your_emailjs_private_key"

# Your email address (where reports will be sent)
EMAIL_TO = "your_email@example.com"

# =============================================================================
# METATRADER 5 CONFIGURATION (optional - if not set, MT5 should be running)
# =============================================================================

# MT5 Login Credentials (optional - leave as None to use MT5 terminal session)
MT5_LOGIN = None  # Your MT5 account number
MT5_PASSWORD = None  # Your MT5 password
MT5_SERVER = None  # Your broker server name (e.g., "ICMarkets-Demo")

# =============================================================================
# TRADING PARAMETERS
# =============================================================================

# Risk Management
RISK_PER_TRADE = 0.005  # 0.5% of account per trade
MAX_POSITIONS = 5  # Maximum number of open positions
MIN_CONFIDENCE = 75  # Minimum AI confidence score to trade (0-100)
MAX_DAILY_LOSS_PCT = 0.05  # Maximum daily loss: 5% of account

# ATR-based Stop Loss and Take Profit
ATR_STOP_MULTIPLIER = 2.0  # Stop loss = 2 × ATR
ATR_TARGET_MULTIPLIER = 3.0  # Take profit = 3 × ATR (1.5:1 R:R ratio)

# =============================================================================
# SYMBOLS TO TRADE
# =============================================================================

# Metals
METALS = ['GOLD', 'SILVER', 'XPDUSD', 'XPTUSD']

# Forex - Major Pairs
FOREX_MAJORS = ['EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'NZDUSD', 'USDCAD', 'USDCHF']

# Forex - Cross Pairs
FOREX_CROSSES = ['EURGBP', 'EURJPY', 'GBPJPY', 'AUDJPY', 'EURAUD']

# Cryptocurrencies
CRYPTO = ['BTCUSD', 'ETHUSD', 'XRPUSD']

# Indices
INDICES = ['US100Cash', 'US500Cash', 'US30Cash', 'GER40Cash', 'UK100Cash']

# Commodities
COMMODITIES = ['USOUSD', 'UKOUSD']  # WTI Crude Oil, Brent Crude Oil

# All symbols combined
ALL_SYMBOLS = METALS + FOREX_MAJORS + FOREX_CROSSES + CRYPTO + INDICES + COMMODITIES

# =============================================================================
# TIMEFRAMES
# =============================================================================

TIMEFRAME_M15 = 'M15'  # 15 minutes
TIMEFRAME_H1 = 'H1'  # 1 hour
TIMEFRAME_H4 = 'H4'  # 4 hours
TIMEFRAME_D1 = 'D1'  # Daily

# =============================================================================
# TECHNICAL INDICATORS SETTINGS
# =============================================================================

# RSI Settings
RSI_PERIOD = 14
RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30

# MACD Settings
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9

# Moving Average Settings
MA_FAST = 10
MA_SLOW = 50
MA_TREND = 200

# ATR Settings (for volatility)
ATR_PERIOD = 14

# =============================================================================
# NOTES
# =============================================================================

# 1. To use this system, copy this file to 'config.py' in the same directory
# 2. Fill in your API keys (required for AI analysis and news data)
# 3. Configure your email settings (for receiving reports)
# 4. Adjust trading parameters to match your risk tolerance
# 5. Customize symbol list based on what your broker offers
# 6. Make sure MetaTrader 5 is running before using the system

# Security Note:
# Never commit config.py with real API keys to version control!
# The .gitignore file should already exclude it.
