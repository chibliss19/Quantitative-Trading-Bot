import yfinance as yf
import pandas as pd

print("Downloading 730 days of hourly GBP/USD data (Yahoo Finance max limit)...")

# Download 1h data for GBPUSD=X (Max allowed is 730d)
df = yf.download("GBPUSD=X", period="730d", interval="1h")

df = df.reset_index()

# Extract only the needed columns, handling multi-level columns if present
if isinstance(df.columns, pd.MultiIndex):
    df.columns = [col[0] for col in df.columns]

# Rename columns to ensure consistency
df = df[['Datetime', 'Open', 'High', 'Low', 'Close']]

# Save to a new hourly CSV
df.to_csv("gbpusd_hourly.csv", index=False)

print("Success! Hourly market data saved to gbpusd_hourly.csv.")