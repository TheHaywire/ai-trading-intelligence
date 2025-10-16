"""
EMAIL ALERT SYSTEM
Monitors multiple strategies and symbols, sends email alerts when opportunities arise

Uses EmailJS to send alerts to: manankharbanda99@gmail.com
"""

import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import requests
import json

# EmailJS Configuration
EMAILJS_SERVICE_ID = "service_izx75k5"
EMAILJS_TEMPLATE_ID = "template_als8uks"
EMAILJS_PUBLIC_KEY = "XQfRe_jpXZ4rbWjYO"
EMAILJS_PRIVATE_KEY = "p_3Qq6lPnsgp5WqZFLac1"
EMAIL_TO = "manankharbanda99@gmail.com"

# Symbols to monitor
SYMBOLS = ['GOLD', 'SILVER', 'EURUSD', 'GBPUSD', 'USDJPY']
TIMEFRAME = mt5.TIMEFRAME_H1

# Alert settings
CHECK_INTERVAL = 3600  # Check every hour (3600 seconds)
SEND_SUMMARY_INTERVAL = 21600  # Send summary every 6 hours

class MarketScanner:
    def __init__(self):
        if not mt5.initialize():
            raise Exception("MT5 initialization failed")
        self.last_summary_time = datetime.now()
        self.alerts_sent_today = 0

    def send_email(self, subject, message):
        """Send email via EmailJS"""
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
                    "message": message,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
            }

            headers = {
                "Content-Type": "application/json"
            }

            response = requests.post(url, json=payload, headers=headers)

            if response.status_code == 200:
                print(f"[OK] Email sent: {subject}")
                self.alerts_sent_today += 1
                return True
            else:
                print(f"[FAIL] Email failed: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            print(f"[ERROR] Email error: {str(e)}")
            return False

    def calculate_ema(self, data, period):
        """Calculate EMA"""
        return data.ewm(span=period, adjust=False).mean()

    def calculate_rsi(self, data, period=14):
        """Calculate RSI"""
        delta = data.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def check_ema_crossover(self, symbol):
        """Check for EMA 25/100 crossover"""
        rates = mt5.copy_rates_range(symbol, TIMEFRAME,
                                     datetime.now() - timedelta(days=30),
                                     datetime.now())

        if rates is None or len(rates) < 100:
            return None

        df = pd.DataFrame(rates)
        close = df['close']

        ema25 = self.calculate_ema(close, 25)
        ema100 = self.calculate_ema(close, 100)

        # Check for recent crossover (last 3 bars)
        for i in range(-3, 0):
            if ema25.iloc[i-1] <= ema100.iloc[i-1] and ema25.iloc[i] > ema100.iloc[i]:
                return {
                    'type': 'EMA_CROSSOVER',
                    'direction': 'LONG',
                    'symbol': symbol,
                    'price': close.iloc[-1],
                    'ema25': ema25.iloc[-1],
                    'ema100': ema100.iloc[-1],
                    'strength': 'BULLISH'
                }
            elif ema25.iloc[i-1] >= ema100.iloc[i-1] and ema25.iloc[i] < ema100.iloc[i]:
                return {
                    'type': 'EMA_CROSSOVER',
                    'direction': 'SHORT',
                    'symbol': symbol,
                    'price': close.iloc[-1],
                    'ema25': ema25.iloc[-1],
                    'ema100': ema100.iloc[-1],
                    'strength': 'BEARISH'
                }

        return None

    def check_rsi_extreme(self, symbol):
        """Check for RSI oversold/overbought"""
        rates = mt5.copy_rates_range(symbol, TIMEFRAME,
                                     datetime.now() - timedelta(days=10),
                                     datetime.now())

        if rates is None or len(rates) < 50:
            return None

        df = pd.DataFrame(rates)
        close = df['close']

        rsi = self.calculate_rsi(close, 28)
        current_rsi = rsi.iloc[-1]

        if current_rsi < 35:
            return {
                'type': 'RSI_OVERSOLD',
                'direction': 'LONG',
                'symbol': symbol,
                'price': close.iloc[-1],
                'rsi': current_rsi,
                'strength': 'STRONG' if current_rsi < 30 else 'MODERATE'
            }
        elif current_rsi > 80:
            return {
                'type': 'RSI_OVERBOUGHT',
                'direction': 'SHORT',
                'symbol': symbol,
                'price': close.iloc[-1],
                'rsi': current_rsi,
                'strength': 'STRONG' if current_rsi > 85 else 'MODERATE'
            }

        return None

    def check_donchian_breakout(self, symbol):
        """Check for Donchian channel breakout"""
        rates = mt5.copy_rates_range(symbol, TIMEFRAME,
                                     datetime.now() - timedelta(days=20),
                                     datetime.now())

        if rates is None or len(rates) < 50:
            return None

        df = pd.DataFrame(rates)
        high = df['high']
        low = df['low']
        close = df['close']

        upper_channel = high.rolling(50).max()
        lower_channel = low.rolling(50).min()

        # Check if current price broke above upper channel
        if close.iloc[-1] > upper_channel.iloc[-2] and close.iloc[-2] <= upper_channel.iloc[-3]:
            return {
                'type': 'DONCHIAN_BREAKOUT',
                'direction': 'LONG',
                'symbol': symbol,
                'price': close.iloc[-1],
                'upper_channel': upper_channel.iloc[-2],
                'strength': 'BREAKOUT'
            }
        # Check if broke below lower channel
        elif close.iloc[-1] < lower_channel.iloc[-2] and close.iloc[-2] >= lower_channel.iloc[-3]:
            return {
                'type': 'DONCHIAN_BREAKOUT',
                'direction': 'SHORT',
                'symbol': symbol,
                'price': close.iloc[-1],
                'lower_channel': lower_channel.iloc[-2],
                'strength': 'BREAKDOWN'
            }

        return None

    def get_market_summary(self):
        """Get summary of all symbols"""
        summary = []

        for symbol in SYMBOLS:
            rates = mt5.copy_rates_range(symbol, TIMEFRAME,
                                        datetime.now() - timedelta(days=7),
                                        datetime.now())

            if rates is None or len(rates) < 50:
                continue

            df = pd.DataFrame(rates)
            close = df['close']

            current_price = close.iloc[-1]
            price_7d_ago = close.iloc[0]
            change_pct = ((current_price / price_7d_ago) - 1) * 100

            # Calculate volatility
            returns = close.pct_change()
            volatility = returns.std() * np.sqrt(24) * 100  # Annualized hourly vol

            summary.append({
                'symbol': symbol,
                'price': current_price,
                'change_7d': change_pct,
                'volatility': volatility,
                'high_24h': df['high'].iloc[-24:].max() if len(df) >= 24 else df['high'].max(),
                'low_24h': df['low'].iloc[-24:].min() if len(df) >= 24 else df['low'].min()
            })

        return summary

    def format_signal_email(self, signals):
        """Format signals into email message"""
        if not signals:
            return None

        message = f"TRADING SIGNALS DETECTED - {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"

        for signal in signals:
            symbol = signal['symbol']
            direction = signal['direction']
            signal_type = signal['type']

            message += f"========================================\n"
            message += f"{symbol} - {direction}\n"
            message += f"Signal: {signal_type.replace('_', ' ')}\n"
            message += f"Price: ${signal['price']:.2f}\n"

            if signal_type == 'EMA_CROSSOVER':
                message += f"EMA25: ${signal['ema25']:.2f}\n"
                message += f"EMA100: ${signal['ema100']:.2f}\n"
            elif 'RSI' in signal_type:
                message += f"RSI: {signal['rsi']:.1f}\n"
            elif signal_type == 'DONCHIAN_BREAKOUT':
                if 'upper_channel' in signal:
                    message += f"Broke above: ${signal['upper_channel']:.2f}\n"
                else:
                    message += f"Broke below: ${signal['lower_channel']:.2f}\n"

            message += f"Strength: {signal['strength']}\n\n"

        message += f"\n⏰ Sent at: {datetime.now().strftime('%H:%M:%S')}\n"
        message += f"📧 Alerts today: {self.alerts_sent_today}\n"

        return message

    def format_summary_email(self, summary):
        """Format market summary email"""
        message = f"MARKET SUMMARY - {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"

        for item in summary:
            emoji = "+" if item['change_7d'] > 0 else "-"
            message += f"{emoji} {item['symbol']}\n"
            message += f"  Price: ${item['price']:.2f}\n"
            message += f"  7-Day Change: {item['change_7d']:+.2f}%\n"
            message += f"  24H Range: ${item['low_24h']:.2f} - ${item['high_24h']:.2f}\n"
            message += f"  Volatility: {item['volatility']:.1f}%\n\n"

        message += f"\nMonitoring: {', '.join(SYMBOLS)}\n"
        message += f"Next update in 6 hours\n"

        return message

    def scan_markets(self):
        """Scan all markets for signals"""
        print(f"\n{'='*60}")
        print(f"Scanning markets at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")

        all_signals = []

        for symbol in SYMBOLS:
            print(f"Checking {symbol}...")

            # Check EMA crossover
            signal = self.check_ema_crossover(symbol)
            if signal:
                all_signals.append(signal)
                print(f"  > EMA crossover detected!")

            # Check RSI extreme
            signal = self.check_rsi_extreme(symbol)
            if signal:
                all_signals.append(signal)
                print(f"  > RSI extreme detected!")

            # Check Donchian breakout
            signal = self.check_donchian_breakout(symbol)
            if signal:
                all_signals.append(signal)
                print(f"  > Donchian breakout detected!")

        # Send signals email if any found
        if all_signals:
            subject = f"ALERT: {len(all_signals)} Trading Signal(s) Detected"
            message = self.format_signal_email(all_signals)
            self.send_email(subject, message)
        else:
            print("No signals found this scan.")

        # Send summary email every 6 hours
        if (datetime.now() - self.last_summary_time).seconds >= SEND_SUMMARY_INTERVAL:
            print("Sending market summary...")
            summary = self.get_market_summary()
            subject = f"Market Summary - {datetime.now().strftime('%H:%M')}"
            message = self.format_summary_email(summary)
            self.send_email(subject, message)
            self.last_summary_time = datetime.now()

    def run(self):
        """Main loop - run continuously"""
        print("="*60)
        print("EMAIL ALERT SYSTEM STARTED")
        print("="*60)
        print(f"Monitoring: {', '.join(SYMBOLS)}")
        print(f"Sending alerts to: {EMAIL_TO}")
        print(f"Check interval: {CHECK_INTERVAL/60:.0f} minutes")
        print(f"Summary interval: {SEND_SUMMARY_INTERVAL/3600:.0f} hours")
        print("="*60)

        # Send startup email
        startup_msg = f"System started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        startup_msg += f"Monitoring symbols: {', '.join(SYMBOLS)}\n"
        startup_msg += f"Strategies: EMA Crossover, RSI Extremes, Donchian Breakouts\n\n"
        startup_msg += "You will receive:\n"
        startup_msg += f"- Signal alerts immediately when detected\n"
        startup_msg += f"- Market summary every {SEND_SUMMARY_INTERVAL/3600:.0f} hours\n"

        self.send_email("Trading Alert System Started", startup_msg)

        try:
            while True:
                self.scan_markets()

                print(f"\nSleeping for {CHECK_INTERVAL/60:.0f} minutes...")
                time.sleep(CHECK_INTERVAL)

        except KeyboardInterrupt:
            print("\n\nStopping alert system...")
            shutdown_msg = f"System stopped at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            shutdown_msg += f"Total alerts sent today: {self.alerts_sent_today}"
            self.send_email("Trading Alert System Stopped", shutdown_msg)
            mt5.shutdown()

if __name__ == "__main__":
    scanner = MarketScanner()
    scanner.run()
