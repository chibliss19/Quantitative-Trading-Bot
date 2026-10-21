import MetaTrader5 as mt5
import pandas as pd
import numpy as np

def run_pro_structure_backtest(pair="GBPUSD", days_back=60):
    if not mt5.initialize():
        print(f"MT5 initialization failed: {mt5.last_error()}")
        return

    # 1. Pull M15 data and H4 data
    rates_m15 = mt5.copy_rates_from_pos(pair, mt5.TIMEFRAME_M15, 0, days_back * 96)
    rates_h4 = mt5.copy_rates_from_pos(pair, mt5.TIMEFRAME_H4, 0, days_back * 6)
    mt5.shutdown()

    if rates_m15 is None or len(rates_m15) == 0 or rates_h4 is None or len(rates_h4) == 0:
        print("Failed to fetch historical rates.")
        return

    df = pd.DataFrame(rates_m15)
    df['time'] = pd.to_datetime(df['time'], unit='s', utc=True)
    df['Hour'] = df['time'].dt.hour
    df['Date'] = df['time'].dt.date

    # --- H4 Trend Filter ---
    df_h4 = pd.DataFrame(rates_h4)
    df_h4['time'] = pd.to_datetime(df_h4['time'], unit='s', utc=True)
    df_h4['H4_EMA'] = df_h4['close'].ewm(span=20, adjust=False).mean()
    
    df_h4_subset = df_h4[['time', 'H4_EMA']].sort_values('time')
    df = pd.merge_asof(df.sort_values('time'), df_h4_subset, on='time', direction='backward')
    df['HTF_Bullish'] = df['close'] > df['H4_EMA']
    # -----------------------

    # --- 2. Vectorized FVG Detection ---
    df['is_Bullish_FVG'] = df['low'] > df['high'].shift(2)
    df['Bullish_FVG_Top'] = np.where(df['is_Bullish_FVG'], df['low'], np.nan)
    df['Bullish_FVG_Bottom'] = np.where(df['is_Bullish_FVG'], df['high'].shift(2), np.nan)

    df['is_Bearish_FVG'] = df['high'] < df['low'].shift(2)
    df['Bearish_FVG_Top'] = np.where(df['is_Bearish_FVG'], df['low'], np.nan)
    df['Bearish_FVG_Bottom'] = np.where(df['is_Bearish_FVG'], df['high'], np.nan)
    # -----------------------------------

    starting_balance = 25000.0
    balance = starting_balance
    risk_per_trade = 0.0035  # 0.35% total risk per trade
    
    trades_executed = 0
    wins = 0
    losses = 0
    partial_wins = 0
    
    active_position = None
    pending_order = None
    order_expiry_bars = 0

    print(f"--- STARTING SPLIT-TARGET (1.5R + 3.0R RUNNER) BACKTEST: {pair} ---")

    for i in range(20, len(df)):
        bar = df.iloc[i]
        h = float(bar['high'])
        l = float(bar['low'])
        htf_bull = bool(bar['HTF_Bullish'])
        
        # Manage active positions (Split into Half 1 and Half 2)
        if active_position is not None:
            total_risk_amount = balance * risk_per_trade
            half_risk = total_risk_amount / 2.0
            
            if active_position['type'] == "BUY":
                # Check Stop Loss (Hits full position if TP1 hasn't been secured)
                if l <= active_position['sl']:
                    if active_position['tp1_hit']:
                        # TP1 was hit, so only half the risk was active
                        balance -= half_risk
                    else:
                        balance -= total_risk_amount
                    losses += 1
                    active_position = None
                    
                else:
                    # Check TP1 (1.5R) for the first half
                    if not active_position['tp1_hit'] and h >= active_position['tp1']:
                        balance += half_risk * 1.5  # Bank 1.5R on first half
                        active_position['tp1_hit'] = True
                        active_position['sl'] = active_position['entry']  # Move remaining stop to breakeven
                        partial_wins += 1
                        
                    # Check TP2 (3.0R Runner) for the second half
                    if active_position['tp1_hit'] and h >= active_position['tp2']:
                        balance += half_risk * 3.0  # Bank 3.0R on runner
                        wins += 1
                        active_position = None
                        
            elif active_position['type'] == "SELL":
                if h >= active_position['sl']:
                    if active_position['tp1_hit']:
                        balance -= half_risk
                    else:
                        balance -= total_risk_amount
                    losses += 1
                    active_position = None
                    
                else:
                    if not active_position['tp1_hit'] and l <= active_position['tp1']:
                        balance += half_risk * 1.5
                        active_position['tp1_hit'] = True
                        active_position['sl'] = active_position['entry']
                        partial_wins += 1
                        
                    if active_position['tp1_hit'] and l <= active_position['tp2']:
                        balance += half_risk * 3.0
                        wins += 1
                        active_position = None
            continue 

        # Check pending Limit Orders
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
                    pending_order = None
            continue

        # Peak London/NY session window (07:00 - 16:00 UTC)
        if 7 <= bar['Hour'] <= 16:
            buffer = 0.00020  # 2-pip safety buffer
            
            if bar['is_Bullish_FVG'] and htf_bull:
                entry = bar['Bullish_FVG_Top']
                sl = bar['Bullish_FVG_Bottom'] - buffer
                risk_dist = entry - sl
                
                tp1 = entry + (1.5 * risk_dist)
                tp2 = entry + (3.0 * risk_dist)  # Extended runner target
                
                pending_order = {
                    'type': "BUY", 'entry': entry, 'sl': sl, 
                    'tp1': tp1, 'tp2': tp2, 'tp1_hit': False
                }
                order_expiry_bars = 8
                
            elif bar['is_Bearish_FVG'] and not htf_bull:
                entry = bar['Bearish_FVG_Bottom']
                sl = bar['Bearish_FVG_Top'] + buffer
                risk_dist = sl - entry
                
                tp1 = entry - (1.5 * risk_dist)
                tp2 = entry - (3.0 * risk_dist)  # Extended runner target
                
                pending_order = {
                    'type': "SELL", 'entry': entry, 'sl': sl, 
                    'tp1': tp1, 'tp2': tp2, 'tp1_hit': False
                }
                order_expiry_bars = 8

    net_profit = balance - starting_balance

    print("\n=== SPLIT-TARGET BACKTEST RESULTS ===")
    print(f"Total Trades: {trades_executed}")
    print(f"Full Wins (Hit 3R): {wins} | Partial Wins (Hit 1.5R): {partial_wins} | Losses: {losses}")
    print(f"Starting Balance: ${starting_balance:,.2f}")
    print(f"Final Balance: ${balance:,.2f}")
    print(f"Net Profit/Loss: ${net_profit:,.2f}")

if __name__ == "__main__":
    run_pro_structure_backtest()