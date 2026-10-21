import MetaTrader5 as mt5
import pandas as pd
import numpy as np

def scan_market_structure(pair="GBPUSD", days_back=5):
    """Scans for Fair Value Gaps and Swing Pivots on the 15M chart."""
    if not mt5.initialize():
        print("MT5 init failed.")
        return

    # Pull 15-minute data (better for structural day trading)
    rates = mt5.copy_rates_from_pos(pair, mt5.TIMEFRAME_M15, 0, days_back * 96) 
    mt5.shutdown()

    if rates is None or len(rates) == 0:
        print("Failed to fetch M15 rates.")
        return

    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s', utc=True)
    
    # --- 1. DETECT FAIR VALUE GAPS (FVG) ---
    # Shift(2) looks 2 candles back (Candle 1). The current row is Candle 3.
    
    # Bullish FVG: Current Low > Candle 1 High
    df['is_Bullish_FVG'] = df['low'] > df['high'].shift(2)
    df['Bullish_FVG_Top'] = np.where(df['is_Bullish_FVG'], df['low'], np.nan)
    df['Bullish_FVG_Bottom'] = np.where(df['is_Bullish_FVG'], df['high'].shift(2), np.nan)

    # Bearish FVG: Current High < Candle 1 Low
    df['is_Bearish_FVG'] = df['high'] < df['low'].shift(2)
    df['Bearish_FVG_Top'] = np.where(df['is_Bearish_FVG'], df['low'].shift(2), np.nan)
    df['Bearish_FVG_Bottom'] = np.where(df['is_Bearish_FVG'], df['high'], np.nan)

    # --- 2. DETECT SWING HIGHS & LOWS (For Market Structure Shifts) ---
    # A swing high is higher than the 2 candles before and 2 candles after it
    df['Swing_High'] = (df['high'] > df['high'].shift(1)) & \
                       (df['high'] > df['high'].shift(2)) & \
                       (df['high'] > df['high'].shift(-1)) & \
                       (df['high'] > df['high'].shift(-2))

    df['Swing_Low'] = (df['low'] < df['low'].shift(1)) & \
                      (df['low'] < df['low'].shift(2)) & \
                      (df['low'] < df['low'].shift(-1)) & \
                      (df['low'] < df['low'].shift(-2))

    # --- DISPLAY THE LATEST STRUCTURE ---
    # Filter for the last 50 candles to see recent action
    recent_df = df.tail(50).copy()
    
    print(f"\n=== LATEST M15 MARKET STRUCTURE: {pair} ===")
    
    # Print recent FVGs
    fvgs = recent_df[(recent_df['is_Bullish_FVG']) | (recent_df['is_Bearish_FVG'])]
    for _, row in fvgs.iterrows():
        time_str = row['time'].strftime('%Y-%m-%d %H:%M')
        if row['is_Bullish_FVG']:
            print(f"[{time_str}] 🟢 BULLISH FVG Detected | Gap: {row['Bullish_FVG_Bottom']:.5f} - {row['Bullish_FVG_Top']:.5f}")
        else:
            print(f"[{time_str}] 🔴 BEARISH FVG Detected | Gap: {row['Bearish_FVG_Bottom']:.5f} - {row['Bearish_FVG_Top']:.5f}")

if __name__ == "__main__":
    scan_market_structure()