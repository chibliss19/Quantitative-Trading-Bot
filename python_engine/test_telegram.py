import requests

TOKEN = "place holder for your bot token"
CHAT_ID = "place holder for your chat ID"

url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
payload = {
    "chat_id": CHAT_ID,
    "text": "🚨 *TEST ALERT*\nYour Telegram telemetry bridge is live and connected!",
    "parse_mode": "Markdown"
}

response = requests.post(url, json=payload)
print(f"Status Code: {response.status_code}")
print(f"Response: {response.text}")