# AI Trading Intelligence

> **Professional-grade trading intelligence system powered by Google Gemini AI, Finnhub, and MetaTrader 5**

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![MT5](https://img.shields.io/badge/MT5-Integrated-orange.svg)](https://www.metatrader5.com/)
[![AI](https://img.shields.io/badge/AI-Gemini%202.0-purple.svg)](https://ai.google.dev/)

A comprehensive trading intelligence platform that combines technical analysis, machine learning, and real-time AI insights to provide actionable trading decisions.

![Symbol Cards Demo](assets/symbol_cards_demo.png)

---

## What This System Does

**Stop guessing. Start trading with confidence.**

This system analyzes every symbol in your watchlist and tells you:
- **WHAT to trade** - Clear BUY/SELL/HOLD decisions
- **WHEN to trade** - Precise entry, stop-loss, and take-profit levels
- **WHY to trade** - AI-powered reasoning with confidence scores
- **HOW GOOD** - 100-point quality score for each setup

### The Million-Dollar Feature: Symbol Decision Cards

Every symbol gets its own professional analysis card with:

**Multi-Timeframe Analysis**
- M15, H1, H4, D1 trends simultaneously
- Identifies fully aligned bull/bear markets
- Shows you the big picture context

**Historical Performance Context**
- 7-day and 30-day price changes
- Distance from period highs/lows
- Helps avoid buying tops or selling bottoms

**AI Intelligence (Google Gemini 2.0)**
- Real-time AI verdict: BUY/SELL/HOLD
- Confidence score: 0-100%
- Clear reasoning: WHY this decision
- Risk factor: What could go wrong
- Latest market news integrated

**Trade Setup**
- Exact entry price
- Precise stop-loss level
- Target take-profit level
- Quality score out of 100 points

**Clear Decision**
- STRONG BUY / BUY / MAYBE / SELL / STRONG SELL / DON'T TRADE
- Detailed reasoning (5+ factors)
- Red flag warnings
- No more guessing!

---

## Quick Start (5 Minutes)

### 1. Install Dependencies

```bash
git clone https://github.com/TheHaywire/ai-trading-intelligence.git
cd ai-trading-intelligence
pip install -r requirements.txt
```

### 2. Configure API Keys

Create `core/config.py` from the template:

```python
# Copy from core/config.example.py and add your keys

# Google Gemini AI (Free tier: 50 requests/day)
# Get key at: https://ai.google.dev/
GEMINI_API_KEY = "your_gemini_api_key_here"

# Finnhub (Free tier available)
# Get key at: https://finnhub.io/
FINNHUB_API_KEY = "your_finnhub_api_key_here"

# Email (for receiving reports)
YOUR_EMAIL = "your_email@example.com"
```

### 3. Connect MetaTrader 5

1. Open MetaTrader 5
2. Enable Algo Trading in Tools > Options > Expert Advisors
3. Make sure you're logged into your account

### 4. Run Your First Analysis

```bash
python trade.py cards
```

This will:
- Analyze all your symbols
- Generate AI-powered decision cards
- Open beautiful HTML report in your browser
- Show clear TRADE/DON'T TRADE decisions

---

## What To Run When

### Morning Routine (5 minutes)

Start your day with complete market intelligence:

```bash
# 1. Get AI-powered symbol cards (MOST IMPORTANT!)
python trade.py cards
```

Check your browser for the HTML report. Each symbol has a card showing:
- Should I trade this? (Clear YES/NO)
- What's the AI's opinion?
- What are the entry/stop/target levels?
- What's the quality score?

```bash
# 2. Get executive summary
python trade.py summary
```

Receive email with:
- Account health overview
- Top opportunities today
- Critical alerts
- Key metrics

```bash
# 3. Check real-time signals
python trade.py signals
```

Get immediate actionable signals:
- Entry/exit alerts
- Position monitoring
- Risk warnings

### Throughout the Day

- **Check email** for automated reports
- **Review symbol cards** before entering trades
- **Confirm AI confidence** is >60% before trading
- **Follow entry/stop/target** prices from cards

### Before Any Trade

1. Open your symbol cards report
2. Find the symbol you want to trade
3. Check:
   - ✅ Is decision "BUY" or "SELL" (not "DON'T TRADE")?
   - ✅ Is AI confidence >60%?
   - ✅ Is quality score >50?
   - ✅ Are timeframes aligned?
4. Use the provided entry/stop/target prices
5. Read AI reasoning to understand WHY

### Evening Review

```bash
# Get performance summary
python trade.py perf
```

Analyze:
- What worked today?
- Which symbols were profitable?
- Where did you deviate from the system?

---

## All Available Commands

### Core Intelligence Commands

| Command | What It Does | When To Use |
|---------|-------------|-------------|
| `python trade.py cards` | **AI-Powered Symbol Decision Cards** - Individual deep analysis per symbol | **Every morning** - Your #1 tool |
| `python trade.py summary` | Executive Summary - Account health + opportunities | Morning briefing |
| `python trade.py ai` | AI/ML Intelligence - Predictions + win probability | When you want ML insights |
| `python trade.py signals` | Real-Time Signals - Entry/exit alerts | Throughout the day |

### Analysis & Risk Commands

| Command | What It Does | When To Use |
|---------|-------------|-------------|
| `python trade.py risk` | Risk Management Dashboard - VaR, stress tests | Before high-risk trades |
| `python trade.py perf` | Performance Attribution - What makes money | End of day/week review |
| `python trade.py ta` | Technical Analysis Report - Charts + patterns | When you need TA deep dive |
| `python trade.py digest` | Complete Daily Digest - All metrics | Daily comprehensive overview |

### Position Management Commands

| Command | What It Does | When To Use |
|---------|-------------|-------------|
| `python trade.py status` | Current Positions Status | Quick position check |
| `python trade.py close-losers` | Close All Losing Positions | Risk management |
| `python trade.py close-all` | Close All Positions | Emergency exit |

---

## System Architecture

```
Commands Layer (trade.py)
    │
    ├─→ Symbol Cards (commands/symbol_cards.py)
    │   └─→ Real-Time Intelligence (core/realtime_intelligence.py)
    │       ├─→ Gemini AI (Google)
    │       └─→ Finnhub API (Market Data + News)
    │
    ├─→ Analysis Engine (core/analysis.py)
    │   └─→ Multi-Timeframe + Historical Context
    │
    ├─→ MT5 Data (core/mt5_service.py)
    │   └─→ Live positions + market data
    │
    └─→ Email Reports (core/email_service.py)
        └─→ Beautiful HTML reports delivered
```

---

## Key Features

### 1. AI-Powered Analysis
- **Google Gemini 2.0** - Latest AI model for market analysis
- **Finnhub News** - Real-time market news + sentiment
- **Conservative rate limiting** - Stays within free tier limits
- **Human-readable verdicts** - Clear BUY/SELL/HOLD decisions

### 2. Multi-Timeframe Context
- **M15** - 15-minute trend (short-term)
- **H1** - 1-hour trend (intraday)
- **H4** - 4-hour trend (swing)
- **D1** - Daily trend (position)
- **Alignment Detection** - Identifies when all timeframes agree

### 3. Historical Performance
- **7-day context** - Weekly price movement
- **30-day context** - Monthly trend direction
- **Distance from highs/lows** - Avoid chasing or panic selling
- **Current positioning** - Where you are in the range

### 4. Trade Quality Scoring (100 Points)
- **Trend Quality** (40 pts) - Is trend strong and clear?
- **Momentum** (25 pts) - Is momentum building?
- **Entry Timing** (20 pts) - Is this a good entry point?
- **Risk/Reward** (10 pts) - Is R:R favorable?
- **Market Structure** (5 pts) - Clean chart structure?

### 5. Clear Decisions
- **STRONG BUY** - Everything aligned, high confidence
- **BUY** - Good setup, favorable conditions
- **MAYBE** - Marginal setup, consider carefully
- **SELL** - Good short setup, favorable conditions
- **STRONG SELL** - Everything aligned for shorts
- **DON'T TRADE** - Poor setup, stay out

---

## Example Daily Workflow

**7:00 AM - Market Open Prep**
```bash
python trade.py cards
```
Review all symbol cards in browser. Note top 3 opportunities.

**7:05 AM - Check Email**
```bash
python trade.py summary
```
Read executive summary in email. Confirm no critical alerts.

**9:00 AM - Trading Session**
- Monitor only symbols with BUY/SELL decisions (not DON'T TRADE)
- Enter trades only when AI confidence >60%
- Use entry/stop/target from cards
- Follow position sizing rules

**12:00 PM - Mid-Day Check**
```bash
python trade.py signals
```
Check for new signals or position alerts.

**5:00 PM - End of Day**
```bash
python trade.py perf
```
Review performance. What worked? What didn't? Journal insights.

---

## Screenshots & Demos

### Symbol Decision Card Example
![Symbol Card](assets/symbol_cards_demo.png)

Each card shows:
- Current positions (if any)
- Multi-timeframe analysis with alignment
- Historical 7d/30d performance
- AI verdict with confidence + reasoning
- Trade setup with entry/stop/target
- Clear TRADE or DON'T TRADE decision
- Detailed reasoning (5+ factors)
- Risk warnings

### Multi-Timeframe Alignment
![Timeframe Alignment](assets/mtf_alignment_demo.png)

See at a glance:
- M15: Short-term trend
- H1: Intraday trend
- H4: Swing trend
- D1: Position trend
- Overall alignment status

### AI Intelligence Section
![AI Intelligence](assets/ai_intelligence_demo.png)

Google Gemini AI provides:
- Clear verdict (BUY/SELL/HOLD)
- Confidence percentage
- Key reasoning (one sentence)
- Risk factor (biggest danger)
- Latest market news headline

---

## API Rate Limits & Costs

### Google Gemini AI
- **Free Tier**: 50 requests/day
- **System Usage**: Conservative (only for tradeable symbols)
- **Cost if exceeded**: $0 (system stops making requests)

### Finnhub
- **Free Tier**: 60 calls/minute
- **System Usage**: Minimal (news + quotes only)
- **Cost if exceeded**: $0 (system handles gracefully)

### MetaTrader 5
- **Cost**: Free platform
- **Requirements**: Broker account (your own)

**Total Monthly Cost**: $0 (using free tiers wisely)

---

## Troubleshooting

### "Failed to connect to MT5"
1. Make sure MetaTrader 5 is open
2. Enable Algo Trading: Tools > Options > Expert Advisors
3. Verify you're logged into your broker account

### "API rate limit reached"
- Gemini: System automatically stops after 50 requests/day
- Finnhub: System handles rate limits gracefully
- **Solution**: Wait until next day or upgrade to paid tier

### "No email received"
1. Check spam folder
2. Verify email in `core/config.py`
3. Note: Symbol cards are saved as HTML (too large for email)
4. Other reports should arrive via email

### "AttributeError: module 'core.config' has no attribute..."
- Make sure you created `core/config.py` from `core/config.example.py`
- Add all required keys (see Installation section)

---

## Comparison with Professional Systems

### vs. TradingView Pro ($60/month)
✅ **AI analysis** (TradingView doesn't have this)
✅ **Multi-timeframe cards** (TradingView requires manual checking)
✅ **Clear trade decisions** (TradingView only shows indicators)
✅ **News integration** (TradingView news is separate)

### vs. Bloomberg Terminal ($2,000/month)
✅ **MT5 integration** (Bloomberg doesn't integrate)
✅ **AI-powered analysis** (Bloomberg is data-only)
✅ **Automated reports** (Bloomberg requires manual work)
✅ **Affordable** (Bloomberg is extremely expensive)

### vs. AlgoTrader ($1,000+/month)
✅ **Symbol decision cards** (AlgoTrader is execution-focused)
✅ **Gemini AI intelligence** (AlgoTrader doesn't use Gemini)
✅ **Real-time news sentiment** (AlgoTrader doesn't analyze news)
✅ **Beautiful reports** (AlgoTrader is technical/ugly)

---

## Disclaimer

**FOR EDUCATIONAL PURPOSES ONLY. NOT FINANCIAL ADVICE.**

Trading involves substantial risk of loss and is not suitable for all investors. Past performance is not indicative of future results. This system is a tool to assist in analysis but does not guarantee profitable trades.

**You are responsible for:**
- Your own trading decisions
- Risk management
- Position sizing
- Compliance with your broker's rules
- Understanding your local regulations

**The system provides:**
- Analysis and insights
- AI-powered recommendations
- Technical indicators
- Historical context

**The system does NOT:**
- Make trades for you (unless you build auto-trading)
- Guarantee profits
- Replace your judgment
- Constitute financial advice

Use this system as a professional tool to enhance your analysis, but always apply your own judgment and risk management principles.

---

## Contributing

Found a bug? Have a feature request? Want to contribute?

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## License

MIT License - see LICENSE file for details.

---

## Support

- **Documentation**: See [MILLION_DOLLAR_SYSTEM_GUIDE.md](MILLION_DOLLAR_SYSTEM_GUIDE.md) for comprehensive guide
- **Quick Start**: See [QUICKSTART.md](QUICKSTART.md) for 5-minute setup
- **Issues**: Open an issue on GitHub
- **Questions**: Check existing issues first

---

## Credits

**Built with:**
- [MetaTrader 5](https://www.metatrader5.com/) - Trading platform
- [Google Gemini AI](https://ai.google.dev/) - AI analysis
- [Finnhub](https://finnhub.io/) - Market data + news
- [Python](https://www.python.org/) - Core language
- [pandas](https://pandas.pydata.org/) - Data analysis
- [scikit-learn](https://scikit-learn.org/) - Machine learning

---

**Built with love for traders who want an edge in the markets**

**Start trading smarter. Get AI-powered intelligence. Make better decisions.**

```bash
python trade.py cards
```
