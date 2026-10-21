import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from datetime import datetime, timezone
import time

def initialize_mt5():
    """Initializes connection to the local MetaTrader 5 terminal."""
    if not mt5.initialize():
        print(f"[MT5 ERROR] Initialization failed, error code = {mt5.last_error()}")
        return False
    print("[MT5 SUCCESS] Connected to MetaTrader 5 terminal.")
    return True

def fetch_and_calculate_orbs(symbol="GBPUSD"):
    """Fetches hourly data from MT5, calculates ATR, and determines London ORB triggers."""
    # Copy the last 100 hourly bars for the symbol
    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 100)
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
    # Ensure account trade permissions and connection are active
    account_info = mt5.account_info()
    if account_info is None:
        print("[MT5 ERROR] Failed to fetch account info. Check terminal login.")
        return False

    request = {
        "action": mt5.TRADE_ACTION_PENDING,
        "symbol": symbol,
        "volume": float(volume),
        "type": mt5.ORDER_TYPE_BUY_STOP,
        "price": float(price),
        "sl": float(sl),
        "type_time": mt5.ORDER_TIME_DAY,
        "type_filling": mt5.ORDER_FILLING_RETURN,
        "comment": "London ORB Python Engine"
    }

    result = mt5.order_send(request)
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"[MT5 ORDER FAILED] Retcode: {result.retcode}, error: {mt5.last_error()}")
        return False

    print(f"[MT5 ORDER SUCCESS] Ticket #{result.order} placed at Price: {price} | Stop-Loss: {sl}")
    return True

if __name__ == "__main__":
    if initialize_mt5():
        symbol = "GBPUSD"
        lot_size = 0.1 # Adjust depending on your $25k account risk allocation
        traded_today = False

        print(f"\n[ENGINE ONLINE] Monitoring {symbol} for 08:00 UTC London Open setup...")

        while True:
            current_hour = datetime.now(timezone.utc).hour
            current_date = datetime.now(timezone.utc).date()

            # Reset flag for a new day
            if current_hour < 8:
                traded_today = false

            # Execute during the 08:00 UTC window if not already traded today
            if current_hour == 8 and not traded_today:
                print("[SETUP WINDOW] 08:00 UTC reached. Evaluating market context...")
                metrics = fetch_and_calculate_orbs(symbol)

                if metrics:
                    print(f"[TRIGGERS CALCULATED] Open: {metrics['LondonOpen']} | Buy Trigger: {metrics['BuyTrigger']} | SL: {metrics['StopLoss']}")
                    
                    success = place_pending_stop_order(
                        symbol=symbol, 
                        volume=lot_size, 
                        price=metrics['BuyTrigger'], 
                        sl=metrics['StopLoss']
                    )

                    if success:
                        traded_today = True
                        print("[SESSION LOCKED] Order placed successfully. Sleeping until tomorrow.")
                else:
                    print("[WAITING] 08:00 candle still forming or data unavailable...")

            # Check every 20 seconds
            time.sleep(20)
    
    mt5.shutdown()