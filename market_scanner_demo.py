

import MetaTrader5 as mt5
import pandas as pd
import pandas_ta as ta
import yaml
import os

# Get the absolute path to the directory of the current script
script_dir = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(script_dir, 'configs', 'example_if_100k.yaml')

# Define a list of major symbols to scan
SYMBOLS_TO_SCAN = [
    "EURUSD", "GBPUSD", "USDJPY", "USDCAD", "AUDUSD", "NZDUSD",
    "USDCHF", "GOLD", "XAUUSD", "UK100", "US30", "DE30"
]

def main():
    """Connects to MT5, scans multiple symbols for key features, and prints a summary."""
    results = []
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        platform_config = config.get('platform', {})
        login = platform_config.get('login')
        password = platform_config.get('password')
        server = platform_config.get('server')

        if not all([login, password, server]):
            print("Error: MT5 login, password, or server not found in the config file.")
            return

        if not mt5.initialize(login=int(login), password=password, server=server):
            print(f"initialize() failed, error code = {mt5.last_error()}")
            return

        print(f"Connected to MT5. Scanning {len(SYMBOLS_TO_SCAN)} symbols...\n")

        # Ensure all symbols are available on the broker's side
        available_symbols = {s.name for s in mt5.symbols_get()}
        symbols = [s for s in SYMBOLS_TO_SCAN if s in available_symbols]

        for symbol in symbols:
            # Get the last 50 H1 bars to have enough data for a 50-period EMA
            rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 50)
            if rates is None or len(rates) < 50:
                print(f"Could not get enough data for {symbol}. Skipping.")
                continue

            df = pd.DataFrame(rates)
            df['time'] = pd.to_datetime(df['time'], unit='s')

            # Calculate EMA(50) and RSI(14)
            df.ta.ema(length=50, append=True)
            df.ta.rsi(length=14, append=True)

            # Get the latest values
            latest_bar = df.iloc[-1]
            close_price = latest_bar['close']
            ema_50 = latest_bar['EMA_50']
            rsi_14 = latest_bar['RSI_14']

            # Calculate distance from EMA as a percentage
            dist_from_ema_pct = ((close_price - ema_50) / ema_50) * 100 if ema_50 else 0

            results.append({
                "Symbol": symbol,
                "Close Price": close_price,
                "RSI_14": rsi_14,
                "Dist_from_EMA50_%": dist_from_ema_pct
            })

        if results:
            summary_df = pd.DataFrame(results)
            print("--- Real-Time Market Scanner (H1 Timeframe) ---")
            print(summary_df.to_string(index=False))

    except FileNotFoundError:
        print(f"Error: Config file not found at {config_path}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        if 'mt5' in locals() and mt5.is_connected():
            mt5.shutdown()
            print("\nDisconnected from MT5.")

if __name__ == "__main__":
    main()

