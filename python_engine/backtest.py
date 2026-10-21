import MetaTrader5 as mt5
import pandas as pd
import numpy as np

def run_backtest(pair="GBPUSD", days_back=60):
    if not mt5.initialize():
        print(f"MT5 initialization failed: {mt5.last_error()}")
        return

    # Pull hourly candles
    rates = mt5.copy_rates_from_pos(pair, mt5.TIMEFRAME_H1, 0, days_back * 24)
    mt5.shutdown()

    if rates is None or len(rates) == 0:
        print("Failed to fetch historical rates.")
        return

    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s', utc=True)
    df['Hour'] = df['time'].dt.hour
    df['Date'] = df['time'].dt.date

    # --- UPGRADE 1: Daily Volatility Compression (NR4) ---
    daily_df = df.groupby('Date').agg({'high': 'max', 'low': 'min'}).reset_index()
    daily_df['DailyRange'] = daily_df['high'] - daily_df['low']
    
    daily_df['Rolling4MinRange'] = daily_df['DailyRange'].rolling(4).min()
    daily_df['IsNR4_Yesterday'] = (daily_df['DailyRange'].shift(1) == daily_df['Rolling4MinRange'].shift(1))
    
    nr4_map = dict(zip(daily_df['Date'], daily_df['IsNR4_Yesterday']))
    df['NR4_Valid'] = df['Date'].map(nr4_map)
    # -----------------------------------------------------

    dates = df['Date'].unique()
    
    starting_balance = 25000.0
    balance = starting_balance
    risk_per_trade = 0.0035  # 0.35% risk cap
    
    trades_executed = 0
    wins = 0
    losses = 0

    print(f"--- STARTING FINAL BACKTEST (1.5R Target / No Breakeven Choke): {pair} ---")

    for d in dates:
        day_df = df[df['Date'] == d]
        
        # Filter for NR4 compression
        if not day_df['NR4_Valid'].values[0]:
            continue  
            
        # --- UPGRADE 2: Pre-London Session Range Anchor ---
        pre_open_bar = day_df[day_df['Hour'] == 7]
        open_bar = day_df[day_df['Hour'] == 8]
        
        if pre_open_bar.empty or open_bar.empty:
            continue
            
        anchor_high = float(pre_open_bar['high'].values[0])
        anchor_low = float(pre_open_bar['low'].values[0])
        
        # 2-pip breakout confirmation buffer
        buffer = 0.00020
        
        # --- UPGRADE 3: Lower Take Profit (1.5R) & No Breakeven ---
        buy_trigger = anchor_high + buffer
        buy_sl = anchor_low - buffer  
        buy_tp = buy_trigger + (1.5 * (buy_trigger - buy_sl)) 
        
        sell_trigger = anchor_low - buffer
        sell_sl = anchor_high + buffer
        sell_tp = sell_trigger - (1.5 * (sell_sl - sell_trigger)) 
        # ----------------------------------------------------------

        subsequent_bars = day_df[day_df['Hour'] >= 8]
        
        position_filled = None
        fill_time = None
        entry_price = 0.0
        sl_price = 0.0
        tp_price = 0.0
        
        # 1. Check for Pending Order Fill
        for _, bar in subsequent_bars.iterrows():
            h = float(bar['high'])
            l = float(bar['low'])
            
            if h >= buy_trigger:
                position_filled = "BUY"
                entry_price = buy_trigger
                sl_price = buy_sl
                tp_price = buy_tp
                fill_time = bar['time']
                trades_executed += 1
                break
                
            if l <= sell_trigger:
                position_filled = "SELL"
                entry_price = sell_trigger
                sl_price = sell_sl
                tp_price = sell_tp
                fill_time = bar['time']
                trades_executed += 1
                break

        if position_filled is None:
            continue

        # 2. Track outcome strictly forward from the fill bar
        post_fill_bars = subsequent_bars[subsequent_bars['time'] >= fill_time]
        outcome_decided = False
        risk_amount = balance * risk_per_trade
        
        for _, bar in post_fill_bars.iterrows():
            h = float(bar['high'])
            l = float(bar['low'])
            
            if position_filled == "BUY":
                if l <= sl_price:
                    balance -= risk_amount
                    losses += 1
                    outcome_decided = True
                    break
                elif h >= tp_price:
                    balance += risk_amount * 1.5  # Bank 1.5R profit
                    wins += 1
                    outcome_decided = True
                    break
                    
            elif position_filled == "SELL":
                if h >= sl_price:
                    balance -= risk_amount
                    losses += 1
                    outcome_decided = True
                    break
                elif l <= tp_price:
                    balance += risk_amount * 1.5  # Bank 1.5R profit
                    wins += 1
                    outcome_decided = True
                    break
                    
        # If neither TP nor SL hit by end of day, close at session end
        if not outcome_decided:
            losses += 1
            balance -= (risk_amount * 0.25)

    win_rate = (wins / trades_executed * 100) if trades_executed > 0 else 0
    net_profit = balance - 25000.0

    print("\n=== FINAL BACKTEST RESULTS ===")
    print(f"Total Trades: {trades_executed}")
    print(f"Wins: {wins} | Losses: {losses}")
    print(f"Win Rate: {win_rate:.2f}%")
    print(f"Starting Balance: $25,000.00")
    print(f"Final Balance: ${balance:,.2f}")
    print(f"Net Profit/Loss: ${net_profit:,.2f}")

if __name__ == "__main__":
    run_backtest()