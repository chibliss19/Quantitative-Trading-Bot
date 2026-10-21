import MetaTrader5 as mt5
import pandas as pd
import numpy as np

def run_structure_backtest(pair="GBPUSD", days_back=60):
    if not mt5.initialize():
        print(f"MT5 initialization failed: {mt5.last_error()}")
        return

    # 1. Pull M15 data for granular structural analysis
    rates = mt5.copy_rates_from_pos(pair, mt5.TIMEFRAME_M15, 0, days_back * 96)
    mt5.shutdown()

    if rates is None or len(rates) == 0:
        print("Failed to fetch historical rates.")
        return

    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s', utc=True)
    df['Hour'] = df['time'].dt.hour
    
    # 2. Vectorized FVG Detection
    # Bullish FVG: Low of candle 3 is higher than High of candle 1
    df['is_Bullish_FVG'] = df['low'] > df['high'].shift(2)
    df['Bullish_FVG_Top'] = np.where(df['is_Bullish_FVG'], df['low'], np.nan)
    df['Bullish_FVG_Bottom'] = np.where(df['is_Bullish_FVG'], df['high'].shift(2), np.nan)

    # Bearish FVG: High of candle 3 is lower than Low of candle 1
    df['is_Bearish_FVG'] = df['high'] < df['low'].shift(2)
    df['Bearish_FVG_Top'] = np.where(df['is_Bearish_FVG'], df['low'].shift(2), np.nan)
    df['Bearish_FVG_Bottom'] = np.where(df['is_Bearish_FVG'], df['high'], np.nan)

    starting_balance = 25000.0
    balance = starting_balance
    risk_per_trade = 0.0035  # 0.35% risk cap
    
    trades_executed = 0
    wins = 0
    losses = 0
    
    # State tracking to simulate live execution logic
    active_position = None
    pending_order = None
    order_expiry_bars = 0

    print(f"--- STARTING STRUCTURAL FVG BACKTEST: {pair} (M15) ---")

    # 3. Bar-by-bar chronological execution (Prevents look-ahead bias)
    for i in range(2, len(df)):
        bar = df.iloc[i]
        h = float(bar['high'])
        l = float(bar['low'])
        
        # Manage active positions first
        if active_position is not None:
            risk_amount = balance * risk_per_trade
            
            if active_position['type'] == "BUY":
                if l <= active_position['sl']:
                    balance -= risk_amount
                    losses += 1
                    active_position = None
                elif h >= active_position['tp']:
                    balance += risk_amount * 1.5
                    wins += 1
                    active_position = None
                    
            elif active_position['type'] == "SELL":
                if h >= active_position['sl']:
                    balance -= risk_amount
                    losses += 1
                    active_position = None
                elif l <= active_position['tp']:
                    balance += risk_amount * 1.5
                    wins += 1
                    active_position = None
            continue 

        # Check pending Limit Orders for fills or expiration
        if pending_order is not None:
            if pending_order['type'] == "BUY" and l <= pending_order['entry']:
                active_position = pending_order
                pending_order = None
                trades_executed += 1
                
            elif pending_order['type'] == "SELL" and h >= pending_order['entry']:
                active_position = pending_order
                pending_order = None
                trades_executed += 1
                
            else:
                order_expiry_bars -= 1
                if order_expiry_bars <= 0:
                    pending_order = None  # Cancel order if price runs away without filling the gap
            continue

        # Look for new structural setups during peak London/NY overlap (07:00 - 15:00 UTC)
        if 7 <= bar['Hour'] <= 15:
            buffer = 0.00020  # 2-pip structural safety buffer
            
            if bar['is_Bullish_FVG']:
                entry = bar['Bullish_FVG_Top']  # Buy Limit at the top of the gap
                sl = bar['Bullish_FVG_Bottom'] - buffer  # Stop below the gap
                tp = entry + (1.5 * (entry - sl))
                
                pending_order = {'type': "BUY", 'entry': entry, 'sl': sl, 'tp': tp}
                order_expiry_bars = 8  # Give price 2 hours (8 candles) to pull back into the gap
                
            elif bar['is_Bearish_FVG']:
                entry = bar['Bearish_FVG_Bottom']  # Sell Limit at the bottom of the gap
                sl = bar['Bearish_FVG_Top'] + buffer  # Stop above the gap
                tp = entry - (1.5 * (sl - entry))
                
                pending_order = {'type': "SELL", 'entry': entry, 'sl': sl, 'tp': tp}
                order_expiry_bars = 8

    win_rate = (wins / trades_executed * 100) if trades_executed > 0 else 0
    net_profit = balance - starting_balance

    print("\n=== STRUCTURAL LIMIT ORDER BACKTEST RESULTS ===")
    print(f"Total Trades: {trades_executed}")
    print(f"Wins: {wins} | Losses: {losses}")
    print(f"Win Rate: {win_rate:.2f}%")
    print(f"Starting Balance: ${starting_balance:,.2f}")
    print(f"Final Balance: ${balance:,.2f}")
    print(f"Net Profit/Loss: ${net_profit:,.2f}")

if __name__ == "__main__":
    run_structure_backtest()