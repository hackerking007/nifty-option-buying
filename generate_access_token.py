from kiteconnect import KiteConnect
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("API_KEY")
api_secret = os.getenv("API_SECRET")
request_token = "RFrp6WTpVfUUs1zBJbzR2E6CpFMwI0Zx"  # Replace with the token you just got

kite = KiteConnect(api_key=api_key)

try:
    data = kite.generate_session(request_token, api_secret=api_secret)
    access_token = data["access_token"]
    print(f"✅ Access Token: {access_token}")

    # Save it to your .env
    with open(".env", "a") as f:
        f.write(f"\nACCESS_TOKEN={access_token}\n")
    print("✅ Access token added to .env file")

except Exception as e:
    print(f"❌ Error: {e}")
