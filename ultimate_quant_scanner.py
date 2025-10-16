

"""
ULTIMATE QUANT SCANNER

DISCLAIMER: This script is for educational purposes only. It is not financial advice.
Trading involves substantial risk of loss. No profitability is guaranteed.
"""

import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import requests
import os

# --- USER CONFIGURATION ---

# 1. Email Settings (using EmailJS - create a free account at emailjs.com)
EMAILJS_SERVICE_ID = "service_izx75k5"  # Your EmailJS Service ID
EMAILJS_TEMPLATE_ID = "template_als8uks" # Your EmailJS Template ID
EMAILJS_PUBLIC_KEY = "XQfRe_jpXZ4rbWjYO"   # Your EmailJS Public Key
EMAILJS_PRIVATE_KEY = "p_3Qq6lPnsgp5WqZFLac1" # Your EmailJS Private Key (store securely)
EMAIL_TO = "manankharbanda99@gmail.com" # The email address to receive alerts

# 2. MT5 Credentials (loaded from YAML)
script_dir = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(script_dir, 'configs', 'example_if_100k.yaml')

# 3. Scanner Settings
SYMBOLS_TO_SCAN = ['GOLD', 'EURUSD', 'GBPUSD', 'USDJPY', 'US30', 'UK100']
SCAN_INTERVAL_SECONDS = 3600  # Check every 1 hour
ALERT_COOLDOWN_HOURS = 4 # Don't re-alert for the same signal for 4 hours

# --- ADVANCED QUANT PARAMETERS ---
TREND_TIMEFRAME = mt5.TIMEFRAME_D1
ENTRY_TIMEFRAME = mt5.TIMEFRAME_H1
TREND_EMA_PERIOD = 50
ENTRY_EMA_PERIOD = 20
VOLATILITY_ATR_PERIOD = 14
MIN_VOLATILITY_PCT = 0.1  # Min ATR as % of price
MAX_VOLATILITY_PCT = 1.5  # Max ATR as % of price
RSI_PERIOD = 14

# --- Global State ---
# Used to prevent re-alerting for the same signal
# Format: {"SYMBOL_DIRECTION": datetime_of_last_alert}
ALERT_HISTORY = {}


# --- CORE FUNCTIONS ---

def send_email(subject, html_message):
    """Sends an HTML email using the EmailJS API."""
    try:
        url = "https://api.emailjs.com/api/v1.0/email/send"
        payload = {
            "service_id": EMAILJS_SERVICE_ID,
            "template_id": EMAILJS_TEMPLATE_ID,
            "user_id": EMAILJS_PUBLIC_KEY,
            "accessToken": EMAILJS_PRIVATE_KEY,
            "template_params": {
                "to_email": EMAIL_TO,
                "subject": subject,
                "message": html_message,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        }
        headers = {"Content-Type": "application/json"}
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 200:
            print(f"[EMAIL SUCCESS] Sent '{subject}' to {EMAIL_TO}")
            return True
        else:
            print(f"[EMAIL FAIL] Failed to send: {response.text}")
            return False
    except Exception as e:
        print(f"[EMAIL ERROR] An exception occurred: {str(e)}")
        return False

def get_mt5_data(symbol, timeframe, num_bars):
    """Fetches data from MT5 and returns a pandas DataFrame."""
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, num_bars)
    if rates is None or len(rates) == 0:
        return None
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.set_index('time', inplace=True)
    return df

def analyze_symbol(symbol):
    """Performs the multi-timeframe quant analysis for a single symbol."""
    # 1. Get Data for both timeframes
    df_trend = get_mt5_data(symbol, TREND_TIMEFRAME, 100)
    df_entry = get_mt5_data(symbol, ENTRY_TIMEFRAME, 100)

    if df_trend is None or df_entry is None:
        return None, "Data fetch failed"

    # 2. Analyze Long-Term Trend (D1)
    df_trend['ema_trend'] = df_trend['close'].ewm(span=TREND_EMA_PERIOD).mean()
    latest_trend_price = df_trend['close'].iloc[-1]
    latest_trend_ema = df_trend['ema_trend'].iloc[-1]
    long_term_trend = "BULLISH" if latest_trend_price > latest_trend_ema else "BEARISH"
    score = 1

    # 3. Analyze Entry Timeframe (H1)
    df_entry['ema_entry'] = df_entry['close'].ewm(span=ENTRY_EMA_PERIOD).mean()
    df_entry['rsi'] = calculate_rsi(df_entry['close'], RSI_PERIOD)
    df_entry['atr'] = calculate_atr(df_entry['high'], df_entry['low'], df_entry['close'], VOLATILITY_ATR_PERIOD)

    latest_entry_price = df_entry['close'].iloc[-1]
    latest_entry_ema = df_entry['ema_entry'].iloc[-1]
    latest_rsi = df_entry['rsi'].iloc[-1]
    latest_atr_pct = (df_entry['atr'].iloc[-1] / latest_entry_price) * 100

    # 4. Check for Pullback Signal
    pullback_signal = False
    # Bullish pullback: D1 is BULLISH, H1 price is near its EMA
    if long_term_trend == "BULLISH" and latest_entry_price >= latest_entry_ema and abs(latest_entry_price - latest_entry_ema) / latest_entry_price < 0.01:
        pullback_signal = True
        score += 1
    # Bearish pullback: D1 is BEARISH, H1 price is near its EMA
    elif long_term_trend == "BEARISH" and latest_entry_price <= latest_entry_ema and abs(latest_entry_price - latest_entry_ema) / latest_entry_price < 0.01:
        pullback_signal = True
        score += 1

    # 5. Check Volatility Regime
    is_optimal_volatility = MIN_VOLATILITY_PCT < latest_atr_pct < MAX_VOLATILITY_PCT
    if is_optimal_volatility:
        score += 1

    # 6. Check RSI Filter
    rsi_ok = (long_term_trend == "BULLISH" and latest_rsi < 75) or (long_term_trend == "BEARISH" and latest_rsi > 25)
    if rsi_ok:
        score += 1

    # 7. Final Signal Generation
    signal = None
    if pullback_signal and is_optimal_volatility and rsi_ok:
        signal = long_term_trend # "BULLISH" or "BEARISH"

    analysis = {
        'symbol': symbol,
        'signal': signal,
        'score': f"{score}/4",
        'long_term_trend': long_term_trend,
        'entry_price': latest_entry_price,
        'h1_volatility_pct': f"{latest_atr_pct:.2f}%",
        'h1_rsi': f"{latest_rsi:.1f}",
        'details': f"D1 Trend: {long_term_trend}. H1 Pullback: {'Yes' if pullback_signal else 'No'}. H1 Volatility: {'Optimal' if is_optimal_volatility else 'Suboptimal'}. H1 RSI: {'OK' if rsi_ok else 'Extreme'}."
    }
    return analysis, "Analysis complete"

# --- Helper Functions ---
def calculate_rsi(data, period):
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_atr(high, low, close, period):
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(period).mean()

# --- Main Loop ---
def run_scanner():
    """Main 24/7 loop to scan markets and send alerts."""
    print("--- Ultimate Quant Scanner INITIALIZING ---")
    # Load MT5 credentials from config
    try:
        with open(CONFIG_PATH, 'r') as f:
            config = yaml.safe_load(f)
        platform_config = config.get('platform', {})
        login = int(platform_config.get('login'))
        password = platform_config.get('password')
        server = platform_config.get('server')
    except Exception as e:
        print(f"[FATAL ERROR] Could not read MT5 config from {CONFIG_PATH}. Exiting. Error: {e}")
        return

    if not mt5.initialize(login=login, password=password, server=server):
        print(f"[FATAL ERROR] MT5 initialization failed. Exiting.")
        return
    
    print(f"[SUCCESS] MT5 Connected. Account: {login}")
    send_email("Quant Scanner Started", "The Ultimate Quant Scanner has been started and is now monitoring the markets.")

    while True:
        try:
            print(f"\n--- New Scan Cycle Started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---")
            all_results = []
            signals_found = []

            for symbol in SYMBOLS_TO_SCAN:
                analysis, status = analyze_symbol(symbol)
                if analysis:
                    all_results.append(analysis)
                    print(f"  - {symbol}: {status} (Score: {analysis['score']}) ")
                    # Check if a new, valid signal is found
                    if analysis['signal']:
                        alert_key = f"{symbol}_{analysis['signal']}"
                        now = datetime.now()
                        # Check if we have alerted this signal recently
                        if alert_key not in ALERT_HISTORY or (now - ALERT_HISTORY[alert_key]) > timedelta(hours=ALERT_COOLDOWN_HOURS):
                            print(f"    -> [NEW SIGNAL FOUND] for {symbol}! Preparing alert.")
                            signals_found.append(analysis)
                            ALERT_HISTORY[alert_key] = now # Update history
                        else:
                            print(f"    -> [Stale Signal] for {symbol}. Cooldown active.")
                else:
                    print(f"  - {symbol}: {status}")

            # If there are any new signals, format and send one email
            if signals_found:
                subject = f"QUANT ALERT: {len(signals_found)} New High-Probability Signal(s) Detected"
                html_body = format_html_email(signals_found, all_results)
                send_email(subject, html_body)
            else:
                print("--- No new high-probability signals found this cycle. ---")

            print(f"--- Scan Cycle Complete. Sleeping for {SCAN_INTERVAL_SECONDS / 60:.0f} minutes. ---")
            time.sleep(SCAN_INTERVAL_SECONDS)

        except KeyboardInterrupt:
            print("\n--- Scanner shutting down by user request. ---")
            send_email("Quant Scanner Stopped", "The Ultimate Quant Scanner has been manually stopped.")
            break
        except Exception as e:
            print(f"[ERROR] An unexpected error occurred in the main loop: {e}")
            time.sleep(60) # Wait a minute before retrying on error

    mt5.shutdown()
    print("--- MT5 Disconnected. Scanner has stopped. ---")

def format_html_email(signals, all_results):
    """Formats the beautiful HTML email report."""
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    html = f"""...""" # This would be the full HTML string from professional_market_scan.py
    # For brevity, I will create a simpler HTML body here.
    html = f"""
    <html>
        <head><style>body{{font-family:sans-serif;}} .container{{width:800px;margin:auto;}}</style></head>
        <body>
            <div class="container">
                <h1>Ultimate Quant Scan Report</h1>
                <p>Generated at: {now_str}</p>
                <h2>🔥 {len(signals)} New High-Probability Signals! 🔥</h2>
    """
    for signal in signals:
        html += f"""
        <div style="border:1px solid #ddd;padding:10px;margin-bottom:10px;">
            <h3>{signal['symbol']} - {signal['signal']} SIGNAL (Score: {signal['score']})</h3>
            <p>{signal['details']}</p>
            <ul>
                <li>Entry Price: {signal['entry_price']:.5f}</li>
                <li>H1 Volatility: {signal['h1_volatility_pct']}</li>
                <li>H1 RSI: {signal['h1_rsi']}</li>
            </ul>
        </div>
        """
    html += "<h2>Market Overview</h2><table border='1' cellpadding='5' cellspacing='0'><tr><th>Symbol</th><th>Score</th><th>D1 Trend</th><th>Details</th></tr>"
    for result in all_results:
        html += f"<tr><td>{result['symbol']}</td><td>{result['score']}</td><td>{result['long_term_trend']}</td><td>{result['details']}</td></tr>"
    html += "</table></div></body></html>"
    return html

if __name__ == "__main__":
    run_scanner()

