 📈 Nifty Weekly Options Breakout Bot

This is an automated trading bot that trades Nifty Weekly Options based on the first 5-minute candle breakout strategy using the Zerodha Kite Connect API.

The bot:

* Enters trades based on **9:15–9:20 AM candle breakout**
* Buys ATM/ATM+50 CE/PE options based on direction
* Applies aggressive trailing stop-loss rules
* Monitors P\&L in real-time (every 5 seconds)**
* Takes a second trade** if the first ends in a loss
* Supports dynamic SL, delta selection**, and ATR-based trailing logic

---
⚙️ Strategy Logic

✅ Entry Conditions

* Fetches the first 5-min candle (9:15–9:20).
* If spot price > high, buys ATM/ATM+50 CE
* If spot price < low, buys ATM/ATM+50 PE
* Option selected using closest to 0.50 delta (within 300 points of spot)

🔐 Stop-Loss & Exit Logic

* **Initial SL**: 20% of premium
* **Trailing SL**:

* If profit ≥ 15% → SL moved to lock 5% profit
* If profit ≥ 20% → ATR-based dynamic trailing SL
* Recovery Exit: If unrealized loss exceeds –5%, waits for price to recover +5% to exit
* Hard Stop Exit: If price hits SL at any point

 🔁 Re-Entry Logic

* If the first trade is in loss, bot waits for **reverse breakout
  (e.g. if first trade was CALL, then waits for price to break candle low)
* Second trade is allowed only once

---

📦 Features

* Zerodha Kite API integration
* Option selection by delta (closest to 0.5)
* Real-time P\&L monitoring (5-second interval)
* ATR calculation for dynamic SL
* Auto-exit and re-entry logic
* Logging with timestamps
* Handles rate limit exceptions and retries

---

🛠 Configuration

You can tweak the following in `op_buy.py`:

* `LOTS` — Number of lots to trade
* `ATR_MULTIPLIER` — SL trailing aggressiveness
* `CHECK_INTERVAL` — Time interval for P\&L monitoring
* Re-entry and risk logic as per your preference

---

📌 Disclaimer

> This bot is intended for educational and personal use only. Trading in the stock market involves risk. The author is not responsible for any financial losses. Use at your own risk and make sure you understand Zerodha’s rate limits and trading guidelines.
