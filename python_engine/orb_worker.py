import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from datetime import datetime, timezone
import time

def fetch_and_calculate_orbs(symbol="GBPUSD"):
    """Fetches hourly data from MT5, calculates ATR, and determines London ORB triggers."""
    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 50)
    if rates is None or len(rates) == 0:
        print(f"[MT5 ERROR] Failed to retrieve historical rates for {symbol}.")
        return None

    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s', utc=True)
    df['Hour'] = df['time'].dt.hour
    df['Date'] = df['time'].dt.date

    # Calculate 14-period ATR on hourly candles
    high_low = df['high'] - df['low']
    high_cp = abs(df['high'] - df['close'].shift(1))
    low_cp = abs(df['low'] - df['close'].shift(1))
    tr = pd.concat([high_low, high_cp, low_cp], axis=1).max(axis=1)
    df['ATR'] = tr.rolling(14).mean()

    # Isolate today's 08:00 UTC London Open candle
    today = datetime.now(timezone.utc).date()
    today_bars = df[df['Date'] == today]
    open_bar = today_bars[today_bars['Hour'] == 8]

    if open_bar.empty:
        return None

    london_open = float(open_bar['open'].values[0])
    atr = float(open_bar['ATR'].values[0])
    
    stretch = 0.5 * atr
    buy_trigger = london_open + stretch
    stop_loss = buy_trigger - (1.5 * stretch)

    return {
        "LondonOpen": london_open,
        "BuyTrigger": round(buy_trigger, 5),
        "StopLoss": round(stop_loss, 5)
    }

def place_pending_stop_order(symbol="GBPUSD", volume=0.1, price=0.0, sl=0.0):
    """Sends a pending BUY_STOP order into the MT5 terminal."""
    request = {
        "action": mt5.TRADE_ACTION_PENDING,
        "symbol": symbol,
        "volume": float(volume),
        "type": mt5.ORDER_TYPE_BUY_STOP,
        "price": float(price),
        "sl": float(sl),
        "type_time": mt5.ORDER_TIME_DAY,
        "type_filling": mt5.ORDER_FILLING_RETURN,
        "comment": "London ORB Engine"
    }

    result = mt5.order_send(request)
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"[MT5 ORDER FAILED] Retcode: {result.retcode}, error: {mt5.last_error()}")
        return False

    print(f"[MT5 ORDER SUCCESS] Ticket #{result.order} placed at Price: {price} | Stop-Loss: {sl}")
    return True

if __name__ == "__main__":
    if mt5.initialize():
        symbol = "GBPUSD"
        lot_size = 0.1 # Scaled for your risk parameters
        
        print(f"\n[ENGINE ONLINE] Monitoring {symbol} for London Open execution...")
        
        # Test run: Fetch metrics right now to verify calculation flow
        metrics = fetch_and_calculate_orbs(symbol)
        if metrics:
            print(f"[METRICS VERIFIED] London Open: {metrics['LondonOpen']} | Buy Trigger: {metrics['BuyTrigger']} | SL: {metrics['StopLoss']}")
        else:
            print("[STATUS] Waiting for active 08:00 UTC hourly data structure...")

        mt5.shutdown()