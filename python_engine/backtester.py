import pandas as pd
import numpy as np

def run_realistic_backtest(csv_file: str):
    print("Loading hourly data for realistic sequential simulation...")
    df = pd.read_csv(csv_file)
    df['Datetime'] = pd.to_datetime(df['Datetime'], utc=True)
    df = df.sort_values('Datetime').reset_index(drop=True)
    df['Date'] = df['Datetime'].dt.date
    df['Hour'] = df['Datetime'].dt.hour

    # Calculate 14-period ATR
    high_low = df['High'] - df['Low']
    high_cp = abs(df['High'] - df['Close'].shift(1))
    low_cp = abs(df['Low'] - df['Close'].shift(1))
    tr = pd.concat([high_low, high_cp, low_cp], axis=1).max(axis=1)
    df['ATR'] = tr.rolling(14).mean()

    dates = df['Date'].unique()
    trades = []
    
    # Realistic Broker Costs (Spread + Commission + Slippage)
    frictional_cost_pips = 1.5 

    for d in dates:
        day_bars = df[df['Date'] == d]
        open_bar = day_bars[day_bars['Hour'] == 8]
        
        if open_bar.empty or pd.isna(open_bar['ATR'].values[0]):
            continue
            
        london_open = open_bar['Open'].values[0]
        atr = open_bar['ATR'].values[0]
        
        stretch = 0.5 * atr
        buy_trigger = london_open + stretch
        sell_trigger = london_open - stretch
        stop_buffer = 1.5 * stretch

        position = None
        entry_price = 0.0
        stop_price = 0.0

        session_bars = day_bars[(day_bars['Hour'] >= 8) & (day_bars['Hour'] <= 16)]
        
        for _, bar in session_bars.iterrows():
            if position is None:
                if bar['High'] >= buy_trigger:
                    position = 'LONG'
                    entry_price = buy_trigger
                    stop_price = entry_price - stop_buffer
                elif bar['Low'] <= sell_trigger:
                    position = 'SHORT'
                    entry_price = sell_trigger
                    stop_price = entry_price + stop_buffer

            elif position == 'LONG':
                if bar['Low'] <= stop_price:
                    raw_pnl = (stop_price - entry_price) / 0.0001
                    trades.append({'Date': d, 'PnL': raw_pnl - frictional_cost_pips})
                    position = 'CLOSED'
                    break
            elif position == 'SHORT':
                if bar['High'] >= stop_price:
                    raw_pnl = (entry_price - stop_price) / 0.0001
                    trades.append({'Date': d, 'PnL': raw_pnl - frictional_cost_pips})
                    position = 'CLOSED'
                    break

        # Market-on-Close
        if position == 'LONG':
            raw_pnl = (session_bars.iloc[-1]['Close'] - entry_price) / 0.0001
            trades.append({'Date': d, 'PnL': raw_pnl - frictional_cost_pips})
        elif position == 'SHORT':
            raw_pnl = (entry_price - session_bars.iloc[-1]['Close']) / 0.0001
            trades.append({'Date': d, 'PnL': raw_pnl - frictional_cost_pips})

    results_df = pd.DataFrame(trades)
    if results_df.empty:
        print("No trades triggered.")
        return

    wins = results_df[results_df['PnL'] > 0]
    win_rate = (len(wins) / len(results_df)) * 100
    total_pnl = results_df['PnL'].sum()
    
    cumulative = results_df['PnL'].cumsum()
    peak = cumulative.cummax()
    max_drawdown = (peak - cumulative).max()

    print("\n=== REALISTIC LONDON ORB (WITH 1.5 PIP SPREAD/COMMISSION) ===")
    print(f"Total Trades:     {len(results_df)}")
    print(f"Winning Trades:   {len(wins)}")
    print(f"Win Rate:         {win_rate:.2f}%")
    print(f"Total PnL:        {total_pnl:.1f} pips")
    print(f"Average Trade:    {results_df['PnL'].mean():.1f} pips")
    print(f"Max Drawdown:     {max_drawdown:.1f} pips")

if __name__ == "__main__":
    run_realistic_backtest("gbpusd_hourly.csv")