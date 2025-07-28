from kiteconnect import KiteConnect
import os

api_key = "m953x25lm4pobrh2"  # from your .env
kite = KiteConnect(api_key=api_key)

print("🔗 Visit this URL to login and get request_token:")
print(kite.login_url())