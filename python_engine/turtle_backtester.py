import pandas as pd
import numpy as np

def run_turtle_backtest(csv_file: str):
    print("Loading daily data and running 20-day Donchian Channel simulation...")
    df = pd.read_csv(csv_file)
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values('Date').reset_index(drop=True)

    df['Upper_20'] = df['High'].rolling(20).max().shift(1)
    df['Lower_20'] = df['Low'].rolling(20).min().shift(1)
    df['Upper_10'] = df['High'].rolling(10).max().shift(1)
    df['Lower_10'] = df['Low'].rolling(10).min().shift(1)

    high_low = df['High'] - df['Low']
    high_cp = abs(df['High'] - df['Close'].shift(1))
    low_cp = abs(df['Low'] - df['Close'].shift(1))
    tr = pd.concat([high_low, high_cp, low_cp], axis=1).max(axis=1)
    df['N'] = tr.rolling(20).mean().shift(1)

    trades = []
    position = None
    entry_price = 0.0
    stop_price = 0.0

    for _, row in df.dropna().iterrows():
        if position == 'LONG':
            if row['Low'] <= stop_price:
                trades.append({'Date': row['Date'], 'PnL': (stop_price - entry_price) / 0.0001})
                position = None
            elif row['Low'] <= row['Lower_10']:
                trades.append({'Date': row['Date'], 'PnL': (row['Lower_10'] - entry_price) / 0.0001})
                position = None
            else:
                stop_price = max(stop_price, row['Close'] - (2 * row['N']))

        elif position == 'SHORT':
            if row['High'] >= stop_price:
                trades.append({'Date': row['Date'], 'PnL': (entry_price - stop_price) / 0.0001})
                position = None
            elif row['High'] >= row['Upper_10']:
                trades.append({'Date': row['Date'], 'PnL': (entry_price - row['Upper_10']) / 0.0001})
                position = None
            else:
                stop_price = min(stop_price, row['Close'] + (2 * row['N']))

        if position is None:
            if row['High'] >= row['Upper_20']:
                position = 'LONG'
                entry_price = row['Upper_20']
                stop_price = entry_price - (2 * row['N'])
            elif row['Low'] <= row['Lower_20']:
                position = 'SHORT'
                entry_price = row['Lower_20']
                stop_price = entry_price + (2 * row['N'])

    results_df = pd.DataFrame(trades)
    if results_df.empty:
        print("No trades triggered.")
        return

    # Convert dates to Monthly periods based on trade exit date
    results_df['Date'] = pd.to_datetime(results_df['Date'])
    results_df['Month'] = results_df['Date'].dt.to_period('M')
    
    monthly_stats = results_df.groupby('Month').agg(
        Trades=('PnL', 'count'),
        Wins=('PnL', lambda x: (x > 0).sum()),
        Total_PnL=('PnL', 'sum')
    ).reset_index()
    monthly_stats['Win_Rate'] = (monthly_stats['Wins'] / monthly_stats['Trades']) * 100

    print("\n=== MONTHLY BREAKDOWN: TURTLE DONCHIAN (LAST 24 MONTHS) ===")
    # Slice the last 24 months to compare with the ORB data
    recent_months = monthly_stats.tail(24)
    for _, row in recent_months.iterrows():
        print(f"{row['Month']} | Trades: {row['Trades']:<3} | Win Rate: {row['Win_Rate']:>5.2f}% | PnL: {row['Total_PnL']:>8.1f} pips")
    
    print(f"\nTOTAL PNL (All 10 Years): {results_df['PnL'].sum():.1f} pips")

if __name__ == "__main__":
    run_turtle_backtest("gbpusd_daily.csv")