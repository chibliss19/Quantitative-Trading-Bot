import MetaTrader5 as mt5

# Initialize connection to the open MT5 desktop app
if not mt5.initialize():
    print(f"[ERROR] MT5 Initialization failed, error code = {mt5.last_error()}")
    quit()

# Fetch account info to confirm the handshake
account_info = mt5.account_info()
if account_info is not None:
    print("[SUCCESS] Python is successfully talking to your MT5 terminal!")
    print(f"Login ID : {account_info.login}")
    print(f"Balance  : {account_info.balance} {account_info.currency}")
    print(f"Server   : {account_info.server}")
else:
    print("[WARNING] Connected to MT5, but could not read account info. Make sure you are logged into an account.")

# Clean up and close connection
mt5.shutdown()