# from fastapi import FastAPI, HTTPException
# import pandas as pd
# import numpy as np

# app = FastAPI(title="Crabel Volatility Compression Engine")

# def calculate_crabel_metrics(df: pd.DataFrame) -> pd.DataFrame:
#     df['Date'] = pd.to_datetime(df['Date'])
#     df = df.sort_values('Date').reset_index(drop=True)
    
#     df['Range'] = df['High'] - df['Low']
#     df['Min_Range_4'] = df['Range'].rolling(window=4, min_periods=4).min()
#     df['Min_Range_7'] = df['Range'].rolling(window=7, min_periods=7).min()
    
#     df['Is_NR4'] = (df['Range'] == df['Min_Range_4'])
#     df['Is_NR7'] = (df['Range'] == df['Min_Range_7'])
    
#     df['Dist_High'] = abs(df['High'] - df['Open'])
#     df['Dist_Low'] = abs(df['Open'] - df['Low'])
#     df['Nearest_Extreme_Dist'] = np.minimum(df['Dist_High'], df['Dist_Low'])
#     df['Stretch'] = df['Nearest_Extreme_Dist'].rolling(window=10, min_periods=10).mean()
    
#     return df

# # @app.get("/api/market-context")
# # def get_market_context(pair: str):
# #     try:
# #         # Simulation setup: NR7 7-day compression triggered
# #         return {
# #             "pair": pair.upper(),
# #             "date": "2026-10-03",
# #             "is_nr4": False,
# #             "is_nr7": True,
# #             "stretch_value": 0.00450,
# #             "prev_close": 1.33500,
# #             "status": "SUCCESS_MOCK"
# #         }
# #     except Exception as e:
# #         raise HTTPException(status_code=500, detail=str(e))

# @app.get("/api/market-context")
# def get_market_context(pair: str):
#     try:
#         # 1. Load the real CSV data
#         df = pd.read_csv("gbpusd_daily.csv")
        
#         # 2. Run the Crabel Volatility Math over the entire dataset
#         processed_df = calculate_crabel_metrics(df)
        
#         # 3. Get the most recent day's data (the final row)
#         latest_data = processed_df.iloc[-1]
        
#         return {
#             "pair": pair.upper(),
#             "date": latest_data['Date'].strftime("%Y-%m-%d"),
#             "is_nr4": bool(latest_data['Is_NR4']),
#             "is_nr7": bool(latest_data['Is_NR7']),
#             "stretch_value": float(latest_data['Stretch']),
#             "prev_close": float(latest_data['Close']),
#             "status": "SUCCESS_LIVE_DATA"
#         }
#     except FileNotFoundError:
#         raise HTTPException(status_code=500, detail="Historical CSV data file not found.")
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))


# from fastapi import FastAPI, HTTPException
# import MetaTrader5 as mt5
# import pandas as pd
# import numpy as np
# from datetime import datetime, timezone
# import uvicorn

# app = FastAPI(title="MT5 Quantitative Bridge", version="1.0")

# def ensure_mt5_connection():
#     """Ensures connection to the local MT5 terminal is active."""
#     if not mt5.initialize():
#         return False
#     return True

# @app.get("/api/v1/market-context")
# def get_market_context(pair: str = "GBPUSD"):
#     """Fetches hourly bars from MT5, calculates ATR, and returns London ORB levels to C#."""
#     if not ensure_mt5_connection():
#         raise HTTPException(status_code=500, detail=f"MT5 initialization failed: {mt5.last_error()}")

#     # Copy the last 50 hourly bars for the symbol
#     rates = mt5.copy_rates_from_pos(pair, mt5.TIMEFRAME_H1, 0, 50)
#     if rates is None or len(rates) == 0:
#         raise HTTPException(status_code=404, detail=f"Failed to retrieve rates for {pair}")

#     df = pd.DataFrame(rates)
#     df['time'] = pd.to_datetime(df['time'], unit='s', utc=True)
#     df['Hour'] = df['time'].dt.hour
#     df['Date'] = df['time'].dt.date

#     # Calculate 14-period ATR on hourly candles
#     high_low = df['high'] - df['low']
#     high_cp = abs(df['high'] - df['close'].shift(1))
#     low_cp = abs(df['low'] - df['close'].shift(1))
#     tr = pd.concat([high_low, high_cp, low_cp], axis=1).max(axis=1)
#     df['ATR'] = tr.rolling(14).mean()

#     # Isolate today's 08:00 UTC London Open candle
#     today = datetime.now(timezone.utc).date()
#     today_bars = df[df['Date'] == today]
#     open_bar = today_bars[today_bars['Hour'] == 8]

#     if open_bar.empty:
#         return {
#             "Status": "WAITING_FOR_LONDON_OPEN",
#             "Pair": pair,
#             "TimestampIso": datetime.now(timezone.utc).isoformat()
#         }

#     london_open = float(open_bar['open'].values[0])
#     atr = float(open_bar['ATR'].values[0])
    
#     stretch = 0.5 * atr
#     buy_trigger = london_open + stretch
#     stop_loss = buy_trigger - (1.5 * stretch)

#     return {
#         "Status": "SUCCESS_LIVE_DATA",
#         "Pair": pair,
#         "LondonOpenPrice": round(london_open, 5),
#         "StretchValue": round(stretch, 5),
#         "BuyTrigger": round(buy_trigger, 5),
#         "StopLoss": round(stop_loss, 5),
#         "TimestampIso": datetime.now(timezone.utc).isoformat()
#     }

# @app.post("/api/v1/execute-order")
# def execute_order(payload: dict):
#     """Receives order parameters from C# and executes a pending stop order on MT5."""
#     if not ensure_mt5_connection():
#         raise HTTPException(status_code=500, detail="MT5 connection lost.")

#     symbol = payload.get("symbol", "GBPUSD")
#     volume = float(payload.get("volume", 0.1))
#     price = float(payload.get("price", 0.0))
#     sl = float(payload.get("sl", 0.0))

#     request = {
#         "action": mt5.TRADE_ACTION_PENDING,
#         "symbol": symbol,
#         "volume": volume,
#         "type": mt5.ORDER_TYPE_BUY_STOP,
#         "price": price,
#         "sl": sl,
#         "type_time": mt5.ORDER_TIME_DAY,
#         "type_filling": mt5.ORDER_FILLING_RETURN,
#         "comment": "C# Orchestrator Bridge"
#     }

#     result = mt5.order_send(request)
#     if result.retcode != mt5.TRADE_RETCODE_DONE:
#         return {
#             "Success": False,
#             "Retcode": result.retcode,
#             "Error": str(mt5.last_error())
#         }

#     return {
#         "Success": True,
#         "OrderTicket": result.order,
#         "ExecutedPrice": price,
#         "StopLoss": sl
#     }

# if __name__ == "__main__":
#     uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)


# from datetime import datetime, timezone
# import MetaTrader5 as mt5
# import pandas as pd
# import requests
# import uvicorn
# from fastapi import FastAPI, HTTPException

# app = FastAPI(title="MT5 Quantitative Bridge", version="1.1")

# # Telegram Configuration
# TELEGRAM_BOT_TOKEN = "8868777057:AAEgVwD9bVez0f96hkLVv00rZLcYM8EqP-Q"
# TELEGRAM_CHAT_ID = "6832468419"

# # In-memory execution state lock to prevent rapid retry loops on error
# EXECUTION_LOCK = {
#     "last_attempt_time": None,
#     "last_error": None,
#     "has_executed_today": False
# }


# def send_telegram_alert(message: str):
#     """Sends a real-time push notification to Telegram."""
#     if not TELEGRAM_CHAT_ID or TELEGRAM_CHAT_ID == "YOUR_CHAT_ID_HERE":
#         return

#     url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
#     payload = {
#         "chat_id": TELEGRAM_CHAT_ID,
#         "text": message,
#         "parse_mode": "Markdown",
#     }
#     try:
#         requests.post(url, json=payload, timeout=5)
#     except Exception as e:
#         print(f"[TELEGRAM ERROR] Failed to send alert: {e}")


# def ensure_mt5_connection() -> bool:
#     """Ensures MT5 terminal is initialized and connected to broker."""
#     if not mt5.initialize():
#         return False
#     terminal_info = mt5.terminal_info()
#     if terminal_info is None or not terminal_info.connected:
#         return False
#     return True


# def get_broker_filling_mode(symbol_info) -> int:
#     """Detects broker-supported order filling mode (FOK, IOC, or RETURN)."""
#     modes = symbol_info.filling_mode
    
#     # In the Python MT5 library, symbol filling modes are bit flags: 1 = FOK, 2 = IOC
#     if modes & 1:
#         return mt5.ORDER_FILLING_FOK
#     elif modes & 2:
#         return mt5.ORDER_FILLING_IOC
    
#     return mt5.ORDER_FILLING_RETURN


# @app.get("/api/v1/market-context")
# def get_market_context(pair: str = "GBPUSD"):
#     """Fetches hourly bars from MT5, calculates ATR, and returns London ORB levels."""
#     if not ensure_mt5_connection():
#         raise HTTPException(
#             status_code=500, detail=f"MT5 offline: {mt5.last_error()}"
#         )

#     rates = mt5.copy_rates_from_pos(pair, mt5.TIMEFRAME_H1, 0, 50)
#     if rates is None or len(rates) == 0:
#         raise HTTPException(
#             status_code=404, detail=f"Failed to retrieve rates for {pair}"
#         )

#     df = pd.DataFrame(rates)
#     df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
#     df["Hour"] = df["time"].dt.hour
#     df["Date"] = df["time"].dt.date

#     # 14-period True Range & ATR
#     high_low = df["high"] - df["low"]
#     high_cp = abs(df["high"] - df["close"].shift(1))
#     low_cp = abs(df["low"] - df["close"].shift(1))
#     tr = pd.concat([high_low, high_cp, low_cp], axis=1).max(axis=1)
#     df["ATR"] = tr.rolling(14).mean()

#     # Isolate today's 08:00 UTC London Open candle
#     today = datetime.now(timezone.utc).date()
#     today_bars = df[df["Date"] == today]
#     open_bar = today_bars[today_bars["Hour"] == 8]

#     # Testing Fallback: Use latest bar if before/outside 08:00 UTC
#     # Strict Production Mode: Only trade the actual London Open
#     if open_bar.empty:
#         return {
#             "Status": "WAITING_FOR_LONDON_OPEN",
#             "Pair": pair,
#             "TimestampIso": datetime.now(timezone.utc).isoformat()
#         }

#     london_open = float(open_bar["open"].values[0])
#     atr = float(open_bar["ATR"].values[0])

#     stretch = 0.5 * atr
#     buy_trigger = london_open + stretch
#     stop_loss = buy_trigger - (1.5 * stretch)

#     return {
#         "Status": "SUCCESS_LIVE_DATA",
#         "Pair": pair,
#         "LondonOpenPrice": round(london_open, 5),
#         "StretchValue": round(stretch, 5),
#         "BuyTrigger": round(buy_trigger, 5),
#         "StopLoss": round(stop_loss, 5),
#         "TimestampIso": datetime.now(timezone.utc).isoformat(),
#     }


# @app.post("/api/v1/execute-order")
# def execute_order(payload: dict):
#     """Executes order on MT5 with strict price validation, broker filling detection, and spam prevention."""
#     if not ensure_mt5_connection():
#         raise HTTPException(status_code=500, detail="MT5 connection lost.")

#     symbol = payload.get("symbol", "GBPUSD")

#     # 1. State-Lock: Terminal-level check for active trades or pending orders
#     existing_orders = mt5.orders_get(symbol=symbol)
#     existing_positions = mt5.positions_get(symbol=symbol)

#     if (existing_orders and len(existing_orders) > 0) or (
#         existing_positions and len(existing_positions) > 0
#     ):
#         return {
#             "Success": False,
#             "Error": f"State Lock Active: Active trade or order already exists for {symbol}.",
#         }

#     # 2. State-Lock: Cooldown guard (prevents hammering MT5 every second on rejected prices)
#     now = datetime.now(timezone.utc)
#     if (
#         EXECUTION_LOCK["last_attempt_time"]
#         and (now - EXECUTION_LOCK["last_attempt_time"]).total_seconds() < 30
#     ):
#         return {
#             "Success": False,
#             "Error": "Cooldown Active: Waiting 30s before retrying execution.",
#         }

#     EXECUTION_LOCK["last_attempt_time"] = now

#     # 3. Pull live tick and symbol specifications
#     symbol_info = mt5.symbol_info(symbol)
#     if symbol_info is None:
#         raise HTTPException(
#             status_code=404, detail=f"Symbol {symbol} not found."
#         )

#     if not symbol_info.visible and not mt5.symbol_select(symbol, True):
#         raise HTTPException(
#             status_code=400, detail=f"Failed to enable symbol {symbol}."
#         )

#     tick = mt5.symbol_info_tick(symbol)
#     if tick is None:
#         raise HTTPException(
#             status_code=500, detail="Failed to fetch live market tick."
#         )

#     current_ask = tick.ask
#     digits = symbol_info.digits
#     point = symbol_info.point
#     min_stop_distance = (
#         symbol_info.trade_stops_level * point
#         if symbol_info.trade_stops_level > 0
#         else 10 * point
#     )

#     requested_price = float(payload.get("price", 0.0))
#     requested_sl = float(payload.get("sl", 0.0))
#     volume = round(float(payload.get("volume", 0.1)), 2)

#     # 4. Determine execution path (Pending Stop vs Immediate Fill)
#     # If market has already crossed the trigger, place a Buy Stop slightly above Ask or execute at market
#     if requested_price <= (current_ask + min_stop_distance):
#         # Breakout already breached: adjust stop order safe distance above Ask
#         order_price = current_ask + (20 * point)
#         order_sl = order_price - (25 * point)
#     else:
#         order_price = requested_price
#         order_sl = requested_sl

#     request = {
#         "action": mt5.TRADE_ACTION_PENDING,
#         "symbol": symbol,
#         "volume": volume,
#         "type": mt5.ORDER_TYPE_BUY_STOP,
#         "price": round(order_price, digits),
#         "sl": round(order_sl, digits),
#         "type_time": mt5.ORDER_TIME_DAY,
#         "type_filling": get_broker_filling_mode(symbol_info),
#         "comment": "Orchestrator Bridge",
#     }

#     result = mt5.order_send(request)

#     if result.retcode != mt5.TRADE_RETCODE_DONE:
#         error_msg = f"[MT5 ORDER FAILED] Retcode: {result.retcode}, Error: {mt5.last_error()}"
#         print(error_msg)

#         # Notify Telegram once per distinct error type (avoids chat flooding)
#         if EXECUTION_LOCK["last_error"] != result.retcode:
#             send_telegram_alert(f"⚠️ *Execution Rejected*\n{error_msg}")
#             EXECUTION_LOCK["last_error"] = result.retcode

#         return {
#             "Success": False,
#             "Retcode": result.retcode,
#             "Error": str(mt5.last_error()),
#         }

#     # Reset errors on success
#     EXECUTION_LOCK["last_error"] = None
#     EXECUTION_LOCK["has_executed_today"] = True

#     # 5. Success Telemetry Alert
#     send_telegram_alert(
#         f"🚀 *ORDER PLACED SUCCESSFULLY*\n"
#         f"• *Ticket:* #{result.order}\n"
#         f"• *Symbol:* {symbol}\n"
#         f"• *Lots:* {volume}\n"
#         f"• *Entry Price:* {request['price']}\n"
#         f"• *Stop Loss:* {request['sl']}"
#     )

#     return {
#         "Success": True,
#         "OrderTicket": result.order,
#         "ExecutedPrice": request["price"],
#         "StopLoss": request["sl"],
#     }


# if __name__ == "__main__":
#     uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)


from datetime import datetime, timezone
import MetaTrader5 as mt5
import pandas as pd
import requests
import uvicorn
from fastapi import FastAPI, HTTPException

app = FastAPI(title="MT5 Quantitative Bridge", version="1.2")

# Telegram Configuration
TELEGRAM_BOT_TOKEN = "8868777057:AAEgVwD9bVez0f96hkLVv00rZLcYM8EqP-Q"
TELEGRAM_CHAT_ID = "6832468419"

# In-memory execution state lock to prevent rapid retry loops on error
EXECUTION_LOCK = {
    "last_attempt_time": None,
    "last_error": None,
    "has_executed_today": False
}

# Track the date of the last executed setup to prevent multiple trades per day
SESSION_STATE = {
    "last_traded_date": None  # Format: "YYYY-MM-DD"
}

# Cache the last notified deal ticket to avoid duplicate closure alerts
LAST_NOTIFIED_DEAL = None


def send_telegram_alert(message: str):
    """Sends a real-time push notification to Telegram."""
    if not TELEGRAM_CHAT_ID or TELEGRAM_CHAT_ID == "YOUR_CHAT_ID_HERE":
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
    }
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"[TELEGRAM ERROR] Failed to send alert: {e}")


def ensure_mt5_connection() -> bool:
    """Ensures MT5 terminal is initialized and connected to broker."""
    if not mt5.initialize():
        return False
    terminal_info = mt5.terminal_info()
    if terminal_info is None or not terminal_info.connected:
        return False
    return True


def get_broker_filling_mode(symbol_info) -> int:
    """Detects broker-supported order filling mode (FOK, IOC, or RETURN)."""
    modes = symbol_info.filling_mode
    if modes & 1:
        return mt5.ORDER_FILLING_FOK
    elif modes & 2:
        return mt5.ORDER_FILLING_IOC
    return mt5.ORDER_FILLING_RETURN


@app.get("/api/v1/market-context")
def get_market_context(pair: str = "GBPUSD"):
    """Fetches hourly bars from MT5, calculates ATR, and returns London ORB levels."""
    if not ensure_mt5_connection():
        raise HTTPException(status_code=500, detail=f"MT5 offline: {mt5.last_error()}")

    rates = mt5.copy_rates_from_pos(pair, mt5.TIMEFRAME_H1, 0, 50)
    if rates is None or len(rates) == 0:
        raise HTTPException(status_code=404, detail=f"Failed to retrieve rates for {pair}")

    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
    df["Hour"] = df["time"].dt.hour
    df["Date"] = df["time"].dt.date

    # 14-period True Range & ATR
    high_low = df["high"] - df["low"]
    high_cp = abs(df["high"] - df["close"].shift(1))
    low_cp = abs(df["low"] - df["close"].shift(1))
    tr = pd.concat([high_low, high_cp, low_cp], axis=1).max(axis=1)
    df["ATR"] = tr.rolling(14).mean()

    # Isolate today's 08:00 UTC London Open candle
    today = datetime.now(timezone.utc).date()
    today_bars = df[df["Date"] == today]
    open_bar = today_bars[today_bars["Hour"] == 8]

    # Strict Production Mode: Only trade the actual London Open
    if open_bar.empty:
        return {
            "Status": "WAITING_FOR_LONDON_OPEN",
            "Pair": pair,
            "TimestampIso": datetime.now(timezone.utc).isoformat()
        }

    london_open = float(open_bar["open"].values[0])
    atr = float(open_bar["ATR"].values[0])

    stretch = 0.5 * atr
    buy_trigger = london_open + stretch
    stop_loss = buy_trigger - (1.5 * stretch)

    return {
        "Status": "SUCCESS_LIVE_DATA",
        "Pair": pair,
        "LondonOpenPrice": round(london_open, 5),
        "StretchValue": round(stretch, 5),
        "BuyTrigger": round(buy_trigger, 5),
        "StopLoss": round(stop_loss, 5),
        "TimestampIso": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/api/v1/execute-order")
def execute_order(payload: dict):
    """Executes order on MT5 with strict price validation, daily limits, and spam prevention."""
    if not ensure_mt5_connection():
        raise HTTPException(status_code=500, detail="MT5 connection lost.")

    symbol = payload.get("symbol", "GBPUSD")
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # 0. HARD DAILY LOCK: Disallow more than one trade per trading day
    if SESSION_STATE["last_traded_date"] == today_str:
        return {
            "Success": False,
            "Error": f"Daily limit reached: A trade was already executed for {today_str}. Standby until tomorrow."
        }

    # 1. State-Lock: Terminal-level check for active trades or pending orders
    existing_orders = mt5.orders_get(symbol=symbol)
    existing_positions = mt5.positions_get(symbol=symbol)

    if (existing_orders and len(existing_orders) > 0) or (
        existing_positions and len(existing_positions) > 0
    ):
        return {
            "Success": False,
            "Error": f"State Lock Active: Active trade or order already exists for {symbol}.",
        }

    # 2. State-Lock: Cooldown guard
    now = datetime.now(timezone.utc)
    if (
        EXECUTION_LOCK["last_attempt_time"]
        and (now - EXECUTION_LOCK["last_attempt_time"]).total_seconds() < 30
    ):
        return {
            "Success": False,
            "Error": "Cooldown Active: Waiting 30s before retrying execution.",
        }

    EXECUTION_LOCK["last_attempt_time"] = now

    # 3. Pull live tick and symbol specifications
    symbol_info = mt5.symbol_info(symbol)
    if symbol_info is None:
        raise HTTPException(status_code=404, detail=f"Symbol {symbol} not found.")

    if not symbol_info.visible and not mt5.symbol_select(symbol, True):
        raise HTTPException(status_code=400, detail=f"Failed to enable symbol {symbol}.")

    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        raise HTTPException(status_code=500, detail="Failed to fetch live market tick.")

    current_ask = tick.ask
    digits = symbol_info.digits
    point = symbol_info.point
    min_stop_distance = (
        symbol_info.trade_stops_level * point
        if symbol_info.trade_stops_level > 0
        else 10 * point
    )

    requested_price = float(payload.get("price", 0.0))
    requested_sl = float(payload.get("sl", 0.0))
    volume = round(float(payload.get("volume", 0.1)), 2)

    # 4. Determine execution path
    if requested_price <= (current_ask + min_stop_distance):
        order_price = current_ask + (20 * point)
        order_sl = order_price - (25 * point)
    else:
        order_price = requested_price
        order_sl = requested_sl

    request = {
        "action": mt5.TRADE_ACTION_PENDING,
        "symbol": symbol,
        "volume": volume,
        "type": mt5.ORDER_TYPE_BUY_STOP,
        "price": round(order_price, digits),
        "sl": round(order_sl, digits),
        "type_time": mt5.ORDER_TIME_DAY,
        "type_filling": get_broker_filling_mode(symbol_info),
        "comment": "Orchestrator Bridge",
    }

    result = mt5.order_send(request)

    if result.retcode != mt5.TRADE_RETCODE_DONE:
        error_msg = f"[MT5 ORDER FAILED] Retcode: {result.retcode}, Error: {mt5.last_error()}"
        print(error_msg)

        if EXECUTION_LOCK["last_error"] != result.retcode:
            send_telegram_alert(f"⚠️ *Execution Rejected*\n{error_msg}")
            EXECUTION_LOCK["last_error"] = result.retcode

        return {
            "Success": False,
            "Retcode": result.retcode,
            "Error": str(mt5.last_error()),
        }

    # Reset errors and engage daily lock
    EXECUTION_LOCK["last_error"] = None
    EXECUTION_LOCK["has_executed_today"] = True
    SESSION_STATE["last_traded_date"] = today_str

    # 5. Success Telemetry Alert
    send_telegram_alert(
        f"🚀 *ORDER PLACED SUCCESSFULLY*\n"
        f"• *Ticket:* #{result.order}\n"
        f"• *Symbol:* {symbol}\n"
        f"• *Lots:* {volume}\n"
        f"• *Entry Price:* {request['price']}\n"
        f"• *Stop Loss:* {request['sl']}\n"
        f"🔒 *Session Lock:* Engaged for {today_str}"
    )

    return {
        "Success": True,
        "OrderTicket": result.order,
        "ExecutedPrice": request["price"],
        "StopLoss": request["sl"],
    }


@app.get("/api/v1/monitor-account")
def monitor_account():
    """Checks for closed trades and daily drawdown status."""
    global LAST_NOTIFIED_DEAL
    if not ensure_mt5_connection():
        return {"Status": "DISCONNECTED"}

    # 1. Detect Trade Closures (SL, TP, or Manual Exit)
    from_time = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    deals = mt5.history_deals_get(from_time, datetime.now(timezone.utc))
    
    if deals and len(deals) > 0:
        latest_deal = deals[-1]
        # entry == 1 corresponds to an exit/close deal in MT5 (Deal out)
        if latest_deal.entry == 1 and latest_deal.ticket != LAST_NOTIFIED_DEAL:
            LAST_NOTIFIED_DEAL = latest_deal.ticket
            pnl = round(latest_deal.profit + latest_deal.commission + latest_deal.swap, 2)
            outcome = "🟢 PROFIT" if pnl >= 0 else "🔴 LOSS"
            
            send_telegram_alert(
                f"🏁 *TRADE CLOSED ({outcome})*\n"
                f"• *Deal Ticket:* #{latest_deal.ticket}\n"
                f"• *Symbol:* {latest_deal.symbol}\n"
                f"• *Exit Price:* {latest_deal.price}\n"
                f"• *Realized PnL:* ${pnl}\n"
                f"• *Comment:* {latest_deal.comment}"
            )

    # 2. Account Health & Circuit Breakers
    account = mt5.account_info()
    if account:
        equity = account.equity
        balance = account.balance
        floating_drawdown = round(((balance - equity) / balance) * 100, 2) if balance > 0 else 0.0

        return {
            "Balance": balance,
            "Equity": equity,
            "FloatingDrawdownPct": floating_drawdown,
            "LastTradedDate": SESSION_STATE["last_traded_date"]
        }

    return {"Status": "OK"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)