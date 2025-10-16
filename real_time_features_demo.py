

import MetaTrader5 as mt5
import pandas as pd
import pandas_ta as ta
import yaml
import os

# Get the absolute path to the directory of the current script
script_dir = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(script_dir, 'configs', 'example_if_100k.yaml')

def main():
    """Connects to MT5, fetches data, calculates features, and prints them."""
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

        # Establish connection to the MetaTrader 5 terminal
        if not mt5.initialize(login=int(login), password=password, server=server):
            print(f"initialize() failed, error code = {mt5.last_error()}")
            return

        print(f"Connected to MT5 account #{login} on server {server}")

        # Get the last 100 H1 bars for EURUSD
        rates = mt5.copy_rates_from_pos("EURUSD", mt5.TIMEFRAME_H1, 0, 100)
        if rates is None:
            print(f"No rates found for EURUSD, error code = {mt5.last_error()}")
            mt5.shutdown()
            return

        # Create a pandas DataFrame
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df.set_index('time', inplace=True)

        print("\nCalculating features for EURUSD H1 data...")

        # Use pandas_ta to create a strategy and calculate multiple indicators
        # This will calculate: 4 EMAs, MACD, and RSI
        custom_strategy = ta.Strategy(
            name="Common Features",
            description="RSI, MACD, and EMAs",
            ta=[
                {"kind": "ema", "length": 10},
                {"kind": "ema", "length": 20},
                {"kind": "ema", "length": 50},
                {"kind": "ema", "length": 200},
                {"kind": "macd", "fast": 12, "slow": 26, "signal": 9},
                {"kind": "rsi", "length": 14},
            ]
        )
        
        # Apply the strategy to the DataFrame
        df.ta.strategy(custom_strategy)

        print("\n--- Real-time Features for EURUSD (last 5 hours) ---")
        # Display the last 5 rows with the new features
        print(df.tail(5))

    except FileNotFoundError:
        print(f"Error: Config file not found at {config_path}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        # Shut down connection to the MetaTrader 5 terminal
        if 'mt5' in locals() and mt5.is_connected():
            mt5.shutdown()
            print("\nDisconnected from MT5.")

if __name__ == "__main__":
    main()

