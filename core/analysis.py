"""
TECHNICAL ANALYSIS - All indicator calculations
"""

import pandas as pd
import numpy as np

def calculate_indicators(df):
    """Calculate all technical indicators on a dataframe"""
    # Moving Averages
    df['SMA_20'] = df['close'].rolling(20).mean()
    df['SMA_50'] = df['close'].rolling(50).mean()
    df['SMA_200'] = df['close'].rolling(200).mean()
    df['EMA_12'] = df['close'].ewm(span=12).mean()
    df['EMA_26'] = df['close'].ewm(span=26).mean()

    # RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))

    # MACD
    df['MACD'] = df['EMA_12'] - df['EMA_26']
    df['MACD_Signal'] = df['MACD'].ewm(span=9).mean()
    df['MACD_Hist'] = df['MACD'] - df['MACD_Signal']

    # Bollinger Bands
    df['BB_Middle'] = df['close'].rolling(20).mean()
    bb_std = df['close'].rolling(20).std()
    df['BB_Upper'] = df['BB_Middle'] + (bb_std * 2)
    df['BB_Lower'] = df['BB_Middle'] - (bb_std * 2)

    # ATR
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = np.max(ranges, axis=1)
    df['ATR'] = true_range.rolling(14).mean()

    # Stochastic
    low_14 = df['low'].rolling(14).min()
    high_14 = df['high'].rolling(14).max()
    df['Stoch_K'] = 100 * (df['close'] - low_14) / (high_14 - low_14)
    df['Stoch_D'] = df['Stoch_K'].rolling(3).mean()

    # Volatility
    df['Volatility'] = df['close'].pct_change().rolling(20).std() * np.sqrt(252) * 100

    return df

def detect_trend(df):
    """Detect market trend"""
    latest = df.iloc[-1]

    if latest['close'] > latest['SMA_50'] > latest['SMA_200']:
        return "STRONG UPTREND", 10
    elif latest['close'] > latest['SMA_50']:
        return "UPTREND", 7
    elif latest['close'] < latest['SMA_50'] < latest['SMA_200']:
        return "STRONG DOWNTREND", -10
    elif latest['close'] < latest['SMA_50']:
        return "DOWNTREND", -7
    else:
        return "RANGING", 0

def get_rsi_status(rsi):
    """Get RSI status"""
    if rsi > 70:
        return "OVERBOUGHT"
    elif rsi < 30:
        return "OVERSOLD"
    else:
        return "NEUTRAL"

def detect_macd_signal(df):
    """Detect MACD crossover signals"""
    latest = df.iloc[-1]
    prev = df.iloc[-2]

    if latest['MACD'] > latest['MACD_Signal'] and prev['MACD'] <= prev['MACD_Signal']:
        return "BULLISH CROSS"
    elif latest['MACD'] < latest['MACD_Signal'] and prev['MACD'] >= prev['MACD_Signal']:
        return "BEARISH CROSS"
    elif latest['MACD'] > latest['MACD_Signal']:
        return "BULLISH"
    else:
        return "BEARISH"
