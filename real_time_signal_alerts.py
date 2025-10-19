"""
REAL-TIME SIGNAL ALERTS
Monitors markets continuously and sends instant email alerts for:
- High-confidence trade setups (>75%)
- Major price movements (>2% moves)
- Breakouts happening NOW
- Critical support/resistance breaks
- Flash opportunities that can't wait for scheduled reports

Runs 24/7 checking markets every 5 minutes
"""

import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import requests
import time
import json
from typing import Dict, List, Optional

# =============================================================================
# CONFIGURATION
# =============================================================================

# Email Configuration
EMAILJS_SERVICE_ID = "service_izx75k5"
EMAILJS_TEMPLATE_ID = "template_als8uks"
EMAILJS_PUBLIC_KEY = "XQfRe_jpXZ4rbWjYO"
EMAILJS_PRIVATE_KEY = "p_3Qq6lPnsgp5WqZFLac1"
EMAIL_TO = "manankharbanda99@gmail.com"

# Alert Thresholds
ALERT_THRESHOLDS = {
    'min_confidence': 75,          # Only alert on setups >75% confidence
    'min_price_move': 2.0,         # Alert on >2% moves in 1 hour
    'min_signal_score': 8,         # Alert on signal scores >=8
    'breakout_lookback': 50,       # Breakout from 50-period high/low
    'volume_spike': 2.0,           # Alert on 2x average volume
}

# Check Interval
CHECK_INTERVAL_MINUTES = 5  # Check every 5 minutes

# Priority Symbols (check these most frequently)
PRIORITY_SYMBOLS = [
    'EURUSD', 'GBPUSD', 'USDJPY', 'GOLD', 'SILVER',
    'BTCUSD', 'ETHUSD', 'US30', 'US100', 'US500'
]

# All Symbols to Monitor
ALL_SYMBOLS = {
    'Forex Majors': ['EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'AUDUSD', 'NZDUSD', 'USDCAD'],
    'Forex Minors': ['EURJPY', 'GBPJPY', 'EURGBP', 'EURAUD', 'EURCHF', 'GBPAUD', 'AUDJPY'],
    'Exotic Forex': ['USDMXN', 'USDZAR', 'USDTRY', 'USDSEK', 'USDNOK'],
    'Precious Metals': ['GOLD', 'SILVER', 'XPTUSD', 'XPDUSD'],
    'Crypto': ['BTCUSD', 'ETHUSD', 'LTCUSD', 'XRPUSD'],
    'Indices': ['US30', 'US100', 'US500', 'DE40', 'UK100']
}

# Alert History (prevent duplicate alerts)
ALERT_HISTORY_FILE = "alert_history.json"
ALERT_COOLDOWN_MINUTES = 60  # Don't re-alert same symbol for 60 min

# =============================================================================
# ALERT HISTORY MANAGEMENT
# =============================================================================

def load_alert_history() -> Dict:
    """Load alert history from file"""
    try:
        with open(ALERT_HISTORY_FILE, 'r') as f:
            return json.load(f)
    except:
        return {}

def save_alert_history(history: Dict):
    """Save alert history to file"""
    try:
        with open(ALERT_HISTORY_FILE, 'w') as f:
            json.dump(history, f, indent=2)
    except Exception as e:
        print(f"[ERROR] Saving alert history: {e}")

def can_send_alert(symbol: str, alert_type: str, history: Dict) -> bool:
    """Check if we can send alert (not sent recently)"""
    key = f"{symbol}_{alert_type}"

    if key not in history:
        return True

    last_alert_time = datetime.fromisoformat(history[key])
    cooldown = timedelta(minutes=ALERT_COOLDOWN_MINUTES)

    return datetime.now() - last_alert_time > cooldown

def mark_alert_sent(symbol: str, alert_type: str, history: Dict):
    """Mark alert as sent"""
    key = f"{symbol}_{alert_type}"
    history[key] = datetime.now().isoformat()

# =============================================================================
# EMAIL ALERTS
# =============================================================================

def send_instant_alert(alert_data: Dict) -> bool:
    """Send instant email alert"""
    try:
        subject = f"🚨 ALERT: {alert_data['symbol']} - {alert_data['alert_type']}"

        # Create compact HTML alert
        html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
body{{font-family:Arial,sans-serif;margin:0;padding:15px;background:#f5f5f5}}
.alert{{max-width:600px;margin:0 auto;background:#fff;border-radius:8px;overflow:hidden;border:3px solid #f5576c}}
.header{{background:linear-gradient(135deg,#f5576c,#f093fb);color:#fff;padding:20px;text-align:center}}
.header h1{{margin:0;font-size:24px}}
.urgency{{background:#ffc107;color:#000;padding:5px 15px;text-align:center;font-weight:bold;font-size:14px}}
.content{{padding:20px}}
.metric{{background:#f8f9fa;padding:12px;margin:8px 0;border-radius:6px;border-left:4px solid #667eea}}
.label{{font-size:11px;color:#666;text-transform:uppercase}}
.value{{font-size:18px;font-weight:bold;color:#1e3c72;margin-top:4px}}
.positive{{color:#10b981}}
.negative{{color:#ef4444}}
.action{{background:#667eea;color:#fff;padding:15px;margin:15px 0;border-radius:6px}}
.footer{{background:#f8f9fa;padding:10px;text-align:center;font-size:11px;color:#666}}
</style></head><body>
<div class="alert">
<div class="header">
<h1>⚡ INSTANT TRADE ALERT</h1>
<p style="margin:5px 0 0 0;font-size:14px">{datetime.now().strftime('%Y-%m-%d %I:%M %p')}</p>
</div>
<div class="urgency">🔔 {alert_data['alert_type'].upper()} DETECTED - ACTION RECOMMENDED</div>
<div class="content">
<h2 style="color:#1e3c72;margin:0 0 15px 0">{alert_data['symbol']}</h2>
"""

        # High Confidence Setup Alert
        if alert_data['alert_type'] == 'HIGH_CONFIDENCE_SETUP':
            setup = alert_data['setup']
            dir_color = '#10b981' if setup['direction'] == 'BULLISH' else '#ef4444'

            html += f"""
<div class="metric">
<div class="label">Signal Direction</div>
<div class="value" style="color:{dir_color}">{setup['direction']}</div>
</div>
<div class="metric">
<div class="label">Confidence Score</div>
<div class="value">{setup['confidence']:.1f}% (EXCELLENT!)</div>
</div>
<div class="metric">
<div class="label">Entry Price</div>
<div class="value">{setup['entry']:.5f}</div>
</div>
<div class="metric">
<div class="label">Stop Loss</div>
<div class="value negative">{setup['stop_loss']:.5f}</div>
</div>
<div class="metric">
<div class="label">Target 1</div>
<div class="value positive">{setup['target_1']:.5f}</div>
</div>
<div class="metric">
<div class="label">Target 2</div>
<div class="value positive">{setup['target_2']:.5f}</div>
</div>
<div class="metric">
<div class="label">Risk:Reward Ratio</div>
<div class="value">1:{setup['risk_reward']:.1f}</div>
</div>
<div class="metric">
<div class="label">Position Size</div>
<div class="value">{setup['lot_size']:.2f} lots</div>
</div>
<div class="action">
<strong>⚡ IMMEDIATE ACTION:</strong><br>
Enter {setup['direction']} at {setup['entry']:.5f}<br>
Stop: {setup['stop_loss']:.5f} | Target: {setup['target_1']:.5f}<br>
Size: {setup['lot_size']:.2f} lots
</div>
"""

        # Major Price Movement Alert
        elif alert_data['alert_type'] == 'MAJOR_PRICE_MOVE':
            change = alert_data['price_change']
            change_color = '#10b981' if change > 0 else '#ef4444'

            html += f"""
<div class="metric">
<div class="label">Price Movement (Last Hour)</div>
<div class="value" style="color:{change_color}">{change:+.2f}%</div>
</div>
<div class="metric">
<div class="label">Current Price</div>
<div class="value">{alert_data['current_price']:.5f}</div>
</div>
<div class="metric">
<div class="label">Previous Price</div>
<div class="value">{alert_data['previous_price']:.5f}</div>
</div>
<div class="action">
<strong>🔥 MOMENTUM ALERT:</strong><br>
Strong {('bullish' if change > 0 else 'bearish')} movement detected!<br>
Consider {('buying' if change > 0 else 'selling')} on pullback
</div>
"""

        # Breakout Alert
        elif alert_data['alert_type'] == 'BREAKOUT':
            html += f"""
<div class="metric">
<div class="label">Breakout Type</div>
<div class="value">{alert_data['breakout_type']}</div>
</div>
<div class="metric">
<div class="label">Current Price</div>
<div class="value">{alert_data['current_price']:.5f}</div>
</div>
<div class="metric">
<div class="label">Breakout Level</div>
<div class="value">{alert_data['breakout_level']:.5f}</div>
</div>
<div class="metric">
<div class="label">Volume</div>
<div class="value">{alert_data.get('volume_ratio', 1):.1f}x Average</div>
</div>
<div class="action">
<strong>📈 BREAKOUT CONFIRMED:</strong><br>
Price breaking {alert_data['breakout_type']}<br>
Watch for continuation or reversal
</div>
"""

        # Volume Spike Alert
        elif alert_data['alert_type'] == 'VOLUME_SPIKE':
            html += f"""
<div class="metric">
<div class="label">Volume Spike</div>
<div class="value">{alert_data['volume_ratio']:.1f}x Normal</div>
</div>
<div class="metric">
<div class="label">Current Price</div>
<div class="value">{alert_data['current_price']:.5f}</div>
</div>
<div class="action">
<strong>📊 HIGH VOLUME DETECTED:</strong><br>
Institutional activity or major news?<br>
Monitor for significant price movement
</div>
"""

        html += f"""
<p style="margin-top:15px;font-size:12px;color:#666">
<strong>Signals Triggered:</strong><br>
{', '.join(alert_data.get('signals', ['N/A'])[:5])}
</p>
</div>
<div class="footer">
<p><strong>Real-Time Alert System</strong> | PropShop Trading Intelligence</p>
<p>Alert generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
<p style="margin-top:8px">Next scheduled report in your inbox soon</p>
</div>
</div>
</body></html>"""

        # Send email
        url = "https://api.emailjs.com/api/v1.0/email/send"
        payload = {
            "service_id": EMAILJS_SERVICE_ID,
            "template_id": EMAILJS_TEMPLATE_ID,
            "user_id": EMAILJS_PUBLIC_KEY,
            "accessToken": EMAILJS_PRIVATE_KEY,
            "template_params": {
                "to_email": EMAIL_TO,
                "subject": subject,
                "message": html,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        }
        headers = {"Content-Type": "application/json"}
        response = requests.post(url, json=payload, headers=headers, timeout=30)

        if response.status_code == 200:
            print(f"[ALERT SENT] {alert_data['symbol']} - {alert_data['alert_type']}")
            return True
        else:
            print(f"[ALERT FAILED] HTTP {response.status_code}: {response.text}")
            return False

    except Exception as e:
        print(f"[ERROR] Sending alert: {e}")
        return False

# =============================================================================
# MARKET MONITORING
# =============================================================================

def check_symbol_for_alerts(symbol: str, category: str) -> List[Dict]:
    """Check single symbol for alert conditions"""
    alerts = []

    try:
        # Get recent data
        rates = mt5.copy_rates_range(
            symbol, mt5.TIMEFRAME_M5,
            datetime.now() - timedelta(hours=4),
            datetime.now()
        )

        if rates is None or len(rates) < 100:
            return alerts

        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')

        # Import analyzer from main script
        import sys
        sys.path.insert(0, '.')
        from exhaustive_daily_quant_report import TechnicalAnalyzer, QuantitativeSignalEngine, TradeSetupGenerator

        # Calculate indicators
        analyzer = TechnicalAnalyzer()
        df = analyzer.calculate_all_indicators(df)

        latest = df.iloc[-1]
        prev = df.iloc[-2]
        hour_ago = df.iloc[-12] if len(df) >= 12 else df.iloc[0]  # 12 bars = 1 hour on M5

        # === CHECK 1: High Confidence Setup ===
        signal_engine = QuantitativeSignalEngine()
        signal_data = signal_engine.generate_signals(df, symbol)

        if signal_data['confidence'] >= ALERT_THRESHOLDS['min_confidence']:
            setup_gen = TradeSetupGenerator()
            setup = setup_gen.generate_setup(df, symbol, signal_data)

            if setup and signal_data['score'] >= ALERT_THRESHOLDS['min_signal_score']:
                alerts.append({
                    'symbol': symbol,
                    'category': category,
                    'alert_type': 'HIGH_CONFIDENCE_SETUP',
                    'setup': setup,
                    'signals': [s['signal'] for s in signal_data['signals'][:5]],
                    'timestamp': datetime.now()
                })

        # === CHECK 2: Major Price Movement ===
        price_change_1h = ((latest['close'] / hour_ago['close']) - 1) * 100

        if abs(price_change_1h) >= ALERT_THRESHOLDS['min_price_move']:
            alerts.append({
                'symbol': symbol,
                'category': category,
                'alert_type': 'MAJOR_PRICE_MOVE',
                'price_change': price_change_1h,
                'current_price': latest['close'],
                'previous_price': hour_ago['close'],
                'signals': [f"{price_change_1h:+.2f}% move in 1 hour"],
                'timestamp': datetime.now()
            })

        # === CHECK 3: Breakouts ===
        donchian_high = df['high'].rolling(ALERT_THRESHOLDS['breakout_lookback']).max().iloc[-2]
        donchian_low = df['low'].rolling(ALERT_THRESHOLDS['breakout_lookback']).min().iloc[-2]

        if latest['close'] > donchian_high:
            alerts.append({
                'symbol': symbol,
                'category': category,
                'alert_type': 'BREAKOUT',
                'breakout_type': f'{ALERT_THRESHOLDS["breakout_lookback"]}-Period High',
                'current_price': latest['close'],
                'breakout_level': donchian_high,
                'volume_ratio': latest.get('tick_volume', 1) / df['tick_volume'].rolling(20).mean().iloc[-1] if 'tick_volume' in df.columns else 1,
                'signals': [f'Breakout above {donchian_high:.5f}'],
                'timestamp': datetime.now()
            })

        elif latest['close'] < donchian_low:
            alerts.append({
                'symbol': symbol,
                'category': category,
                'alert_type': 'BREAKOUT',
                'breakout_type': f'{ALERT_THRESHOLDS["breakout_lookback"]}-Period Low',
                'current_price': latest['close'],
                'breakout_level': donchian_low,
                'volume_ratio': latest.get('tick_volume', 1) / df['tick_volume'].rolling(20).mean().iloc[-1] if 'tick_volume' in df.columns else 1,
                'signals': [f'Breakdown below {donchian_low:.5f}'],
                'timestamp': datetime.now()
            })

        # === CHECK 4: Volume Spike ===
        if 'tick_volume' in df.columns:
            avg_volume = df['tick_volume'].rolling(20).mean().iloc[-1]
            current_volume = latest['tick_volume']
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1

            if volume_ratio >= ALERT_THRESHOLDS['volume_spike']:
                alerts.append({
                    'symbol': symbol,
                    'category': category,
                    'alert_type': 'VOLUME_SPIKE',
                    'volume_ratio': volume_ratio,
                    'current_price': latest['close'],
                    'signals': [f'Volume {volume_ratio:.1f}x normal'],
                    'timestamp': datetime.now()
                })

        return alerts

    except Exception as e:
        print(f"[ERROR] Checking {symbol}: {e}")
        return alerts

def scan_markets_for_alerts() -> List[Dict]:
    """Scan all markets for alert conditions"""
    all_alerts = []

    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Scanning markets for alerts...")

    # Check priority symbols first
    for symbol in PRIORITY_SYMBOLS:
        category = 'Priority'
        for cat, symbols in ALL_SYMBOLS.items():
            if symbol in symbols:
                category = cat
                break

        alerts = check_symbol_for_alerts(symbol, category)
        all_alerts.extend(alerts)

    # Periodically check all other symbols (every 3rd scan)
    import random
    if random.randint(1, 3) == 1:
        other_symbols = []
        for symbols in ALL_SYMBOLS.values():
            other_symbols.extend([s for s in symbols if s not in PRIORITY_SYMBOLS])

        # Check random subset
        sample_size = min(10, len(other_symbols))
        sample = random.sample(other_symbols, sample_size)

        for symbol in sample:
            category = 'Other'
            for cat, symbols in ALL_SYMBOLS.items():
                if symbol in symbols:
                    category = cat
                    break

            alerts = check_symbol_for_alerts(symbol, category)
            all_alerts.extend(alerts)

    return all_alerts

# =============================================================================
# MAIN LOOP
# =============================================================================

def main():
    """Main monitoring loop"""
    print("="*80)
    print(" REAL-TIME SIGNAL ALERTS - CONTINUOUS MONITORING")
    print("="*80)
    print(f"\nStarting at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"\nAlert Thresholds:")
    print(f"  - Min Confidence: {ALERT_THRESHOLDS['min_confidence']}%")
    print(f"  - Min Price Move: {ALERT_THRESHOLDS['min_price_move']}%")
    print(f"  - Min Signal Score: {ALERT_THRESHOLDS['min_signal_score']}")
    print(f"\nCheck Interval: Every {CHECK_INTERVAL_MINUTES} minutes")
    print(f"Priority Symbols: {len(PRIORITY_SYMBOLS)}")
    print(f"Alert Cooldown: {ALERT_COOLDOWN_MINUTES} minutes")
    print(f"\nEmail: {EMAIL_TO}")
    print("="*80)

    # Initialize MT5
    if not mt5.initialize():
        print("\n[ERROR] Failed to initialize MetaTrader 5")
        return

    print("\n[OK] MT5 initialized - monitoring started\n")

    alert_history = load_alert_history()
    scan_count = 0

    try:
        while True:
            scan_count += 1
            print(f"\n{'='*80}")
            print(f"SCAN #{scan_count} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{'='*80}")

            # Scan for alerts
            alerts = scan_markets_for_alerts()

            if alerts:
                print(f"\n[FOUND] {len(alerts)} potential alert(s)")

                for alert in alerts:
                    alert_key = f"{alert['symbol']}_{alert['alert_type']}"

                    # Check cooldown
                    if can_send_alert(alert['symbol'], alert['alert_type'], alert_history):
                        print(f"\n[ALERT] {alert['symbol']} - {alert['alert_type']}")

                        # Send alert
                        if send_instant_alert(alert):
                            mark_alert_sent(alert['symbol'], alert['alert_type'], alert_history)
                            save_alert_history(alert_history)
                    else:
                        print(f"[COOLDOWN] {alert_key} - skipping (too recent)")
            else:
                print("[OK] No alerts - markets stable")

            # Wait for next check
            print(f"\nNext scan in {CHECK_INTERVAL_MINUTES} minutes...")
            time.sleep(CHECK_INTERVAL_MINUTES * 60)

    except KeyboardInterrupt:
        print("\n\n[STOPPED] Monitoring stopped by user")
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
    finally:
        mt5.shutdown()
        print("\n[OK] MT5 shutdown complete")

if __name__ == "__main__":
    main()
