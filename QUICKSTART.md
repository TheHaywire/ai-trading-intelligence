# Quick Start Guide - AI Trading Intelligence

Get started in 5 minutes!

---

## Step 1: Install (2 minutes)

```bash
git clone https://github.com/TheHaywire/ai-trading-intelligence.git
cd ai-trading-intelligence
pip install -r requirements.txt
```

---

## Step 2: Configure API Keys (2 minutes)

### Get Your Free API Keys

**Google Gemini AI** (Free: 50 requests/day)
- Visit: https://ai.google.dev/
- Click "Get API Key"
- Copy your key

**Finnhub** (Free tier available)
- Visit: https://finnhub.io/register
- Sign up for free account
- Copy your API key from dashboard

### Create Configuration File

Copy `core/config.example.py` to `core/config.py` and add your keys:

```python
# core/config.py

# API Keys
GEMINI_API_KEY = "paste_your_gemini_key_here"
FINNHUB_API_KEY = "paste_your_finnhub_key_here"

# Your email for receiving reports
YOUR_EMAIL = "your_email@example.com"

# MetaTrader 5 settings
MT5_LOGIN = "your_mt5_login"  # Optional
MT5_PASSWORD = "your_mt5_password"  # Optional
MT5_SERVER = "your_broker_server"  # Optional
```

---

## Step 3: Connect MetaTrader 5 (1 minute)

1. **Open MetaTrader 5** on your computer
2. **Enable Algo Trading**:
   - Go to `Tools` > `Options` > `Expert Advisors`
   - Check "Allow algorithmic trading"
   - Click OK
3. **Make sure you're logged in** to your broker account

---

## Step 4: Run Your First Analysis (30 seconds)

```bash
python trade.py cards
```

**What happens:**
- System connects to MT5
- Analyzes all your symbols
- Gets AI intelligence from Gemini
- Fetches latest market news
- Generates beautiful HTML report
- Opens report in your browser automatically

**You'll see:**
- Individual cards for each symbol
- Clear BUY/SELL/HOLD decisions
- AI confidence scores
- Entry/stop/target prices
- Multi-timeframe analysis
- Historical performance context

---

## Your First Trade Decision

Look at any symbol card in the report:

✅ **TRADE THIS** if:
- Decision says "BUY" or "SELL" (not "DON'T TRADE")
- AI confidence > 60%
- Quality score > 50
- Timeframes are aligned

❌ **DON'T TRADE** if:
- Decision says "DON'T TRADE"
- AI confidence < 40%
- Quality score < 30
- Conflicting timeframes

---

## Daily Workflow

### Every Morning (5 minutes)

```bash
# 1. Get AI-powered symbol cards
python trade.py cards

# 2. Get executive summary via email
python trade.py summary

# 3. Check real-time signals
python trade.py signals
```

### Before Each Trade

1. Open symbol cards report
2. Find your symbol
3. Check AI verdict + confidence
4. Use provided entry/stop/target prices
5. Confirm quality score is good

### End of Day

```bash
# Review performance
python trade.py perf
```

---

## All Commands Cheat Sheet

| Command | What You Get |
|---------|-------------|
| `python trade.py cards` | AI-powered symbol decision cards (YOUR #1 TOOL) |
| `python trade.py summary` | Executive summary (email) |
| `python trade.py ai` | ML intelligence & predictions |
| `python trade.py signals` | Real-time entry/exit signals |
| `python trade.py risk` | Risk management dashboard |
| `python trade.py perf` | Performance attribution |
| `python trade.py ta` | Technical analysis report |
| `python trade.py digest` | Complete daily digest |
| `python trade.py status` | Current positions status |

---

## Troubleshooting

### "Failed to connect to MT5"
- Make sure MT5 is open and running
- Enable Algo Trading in MT5 Options
- Verify you're logged into your account

### "API rate limit reached"
- You've used 50+ Gemini requests today
- Wait until tomorrow (resets at midnight UTC)
- Or upgrade to paid Gemini tier

### "No email received"
- Check spam/junk folder
- Verify email in `core/config.py`
- Note: Symbol cards are too large for email (opens in browser instead)

### "Import error" or "Module not found"
```bash
pip install -r requirements.txt
```

---

## What Each Command Actually Does

### `python trade.py cards` (MOST IMPORTANT)
- Analyzes every symbol individually
- Multi-timeframe analysis (M15, H1, H4, D1)
- Historical context (7d, 30d)
- AI verdict from Gemini
- Latest market news
- Clear TRADE/DON'T TRADE decision
- **When**: Every morning before trading

### `python trade.py summary`
- Account health overview
- Top 3 opportunities
- Critical alerts
- Daily market briefing
- **When**: Morning routine

### `python trade.py signals`
- Entry/exit signals
- Position monitoring
- Stop-loss alerts
- Take-profit reminders
- **When**: Throughout the day

### `python trade.py ai`
- ML predictions (Random Forest, Gradient Boosting)
- Win probability scores
- Trade quality assessment
- Feature importance analysis
- **When**: When you want deeper ML insights

### `python trade.py risk`
- Value at Risk (VaR)
- Stress testing
- Correlation analysis
- Position heat maps
- **When**: Before taking high-risk trades

### `python trade.py perf`
- Which strategies work
- Best performing symbols
- Win rate analysis
- Profit/loss attribution
- **When**: End of day/week review

---

## Pro Tips

1. **Run `cards` every morning** - It's your trading roadmap for the day

2. **Only trade symbols with:**
   - BUY or SELL decision (not DON'T TRADE)
   - AI confidence > 60%
   - Quality score > 50
   - Aligned timeframes

3. **Use the exact entry/stop/target prices** provided by the system

4. **Check AI reasoning** - Understand WHY before trading

5. **Review performance daily** - Learn what works for you

6. **Start small** - Test with small position sizes first

7. **Don't override the system** - If it says DON'T TRADE, don't trade!

---

## Next Steps

- **Read full documentation**: [README.md](README.md)
- **Understand the system**: [MILLION_DOLLAR_SYSTEM_GUIDE.md](MILLION_DOLLAR_SYSTEM_GUIDE.md)
- **Run your first analysis**: `python trade.py cards`
- **Paper trade first**: Test the system before going live
- **Start small**: Use small position sizes initially
- **Journal your trades**: Keep track of what works

---

## Support

- **Issues**: Open on GitHub
- **Questions**: Check existing issues first
- **Documentation**: See full README.md

---

**You're ready to trade smarter with AI-powered intelligence!**

```bash
python trade.py cards
```

Good luck and trade responsibly!
