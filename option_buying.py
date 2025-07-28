import os
import time
import datetime
import random
from dotenv import load_dotenv
from kite_session import get_kite_instance

# Load environment variables
load_dotenv()

# ---- Config ----
LOT_SIZE = 75
LOTS = 1
QUANTITY = LOT_SIZE * LOTS
ENTRY_PRICE = None
OPTION_SYMBOL = None
ORDER_ID = None
TRADE_PLACED = False
FIRST_TRADE_DONE = False
FIRST_TRADE_WAS_PROFIT = False
DIRECTION = None
ATR = None
ATR_MULTIPLIER = 2.5
NEXT_CHECK_TIME = None
CHECK_INTERVAL = 5  # seconds

# ---- Logger ----
def log(msg):
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {msg}")

# ---- Kite Init ----
kite = get_kite_instance()

# ---- Refresh Instruments with Retry ----
def refresh_instruments(retries=5, delay=5):
    for i in range(retries):
        try:
            raw_instruments = kite.instruments("NFO")
            instruments = [
                inst for inst in raw_instruments
                if inst.get("exchange") == "NFO" and
                   inst.get("name") == "NIFTY" and
                   inst.get("segment") == "NFO-OPT" and
                   inst.get("instrument_type") in ["CE", "PE"]
            ]
            if instruments:
                log(f"📦 Total NIFTY OPTIDX instruments fetched: {len(instruments)}")
                return instruments
            else:
                log(f"⚠️ No NIFTY OPTIDX instruments yet. Retrying... ({i+1}/{retries})")
                time.sleep(delay)
        except Exception as e:
            log(f"❌ Error fetching instruments: {e}")
            time.sleep(delay)
    log("🚫 Failed to fetch instruments after multiple retries.")
    return []

# ---- Get Nearest Expiry Date ----
def get_nearest_expiry():
    global instruments
    instruments = refresh_instruments()
    today = datetime.date.today()
    expiries = sorted(set(
        inst["expiry"].date() if isinstance(inst["expiry"], datetime.datetime) else inst["expiry"]
        for inst in instruments if inst.get("expiry")
    ))
    log(f"📅 All detected expiries: {expiries}")
    for exp in expiries:
        if exp >= today:
            return exp
    return None

instruments = refresh_instruments()
CURRENT_EXPIRY = get_nearest_expiry()
if not CURRENT_EXPIRY:
    log("❌ Could not determine nearest expiry. Aborting trade.")
    exit()
log(f"📅 Nearest expiry: {CURRENT_EXPIRY}")

# ---- Option Instrument Fetch Closest to 0.50 Delta ----
def get_option_by_delta(option_type):
    global instruments
    instruments = refresh_instruments()

    closest_option = None
    closest_delta_diff = float('inf')
    available_strikes = []
    today = datetime.date.today()
    spot = get_nifty_spot()

    for inst in instruments:
        expiry = inst.get("expiry")
        if isinstance(expiry, datetime.datetime):
            expiry = expiry.date()

        if expiry != CURRENT_EXPIRY:
            continue

        tradingsymbol = inst.get("tradingsymbol", "")
        is_correct_type = tradingsymbol.endswith(option_type.upper())

        if is_correct_type:
            strike = inst.get("strike")
            available_strikes.append(strike)

            if abs(strike - spot) > 300:
                continue

            try:
                time.sleep(0.4 + random.uniform(0, 0.2))
                oi = kite.quote([f"NFO:{tradingsymbol}"])
                greeks = oi[f"NFO:{tradingsymbol}"].get("greeks", {})
                delta = abs(greeks.get("delta", 0))

                if expiry == today and delta <= 0.50:
                    continue

                delta_diff = abs(delta - 0.5)
                if delta_diff < closest_delta_diff:
                    closest_delta_diff = delta_diff
                    closest_option = inst
            except:
                continue

    log(f"📊 Available {option_type.upper()} strikes for {CURRENT_EXPIRY}: {sorted(set(available_strikes))}")
    if closest_option:
        log(f"🎯 Selected strike near 0.50 delta: {closest_option['tradingsymbol']} with strike {closest_option['strike']}")
        return closest_option.get("tradingsymbol"), closest_option.get("instrument_token")

    log(f"❌ No suitable {option_type} option found for expiry {CURRENT_EXPIRY}")
    return None, None

# ---- Utility Functions ----
def get_nifty_spot():
    retries = 3
    for i in range(retries):
        try:
            time.sleep(0.4 + random.uniform(0, 0.2))
            return kite.ltp("NSE:NIFTY 50")["NSE:NIFTY 50"]["last_price"]
        except Exception as e:
            log(f"⚠️ [get_nifty_spot] Attempt {i+1}/{retries} failed: {e}")
            time.sleep(1)
    raise Exception("❌ Failed to get Nifty spot after retries")

def get_ltp(symbol):
    retries = 3
    for i in range(retries):
        try:
            time.sleep(0.4 + random.uniform(0, 0.2))
            return kite.ltp(f"NFO:{symbol}")[f"NFO:{symbol}"]["last_price"]
        except Exception as e:
            log(f"⚠️ [get_ltp] Attempt {i+1}/{retries} failed: {e}")
            time.sleep(1)
    raise Exception(f"❌ Failed to get LTP for {symbol} after retries")

def place_order(symbol):
    return kite.place_order(
        variety="regular",
        exchange="NFO",
        tradingsymbol=symbol,
        transaction_type="BUY",
        quantity=QUANTITY,
        order_type="MARKET",
        product="MIS"
    )

def exit_trade(symbol):
    kite.place_order(
        variety="regular",
        exchange="NFO",
        tradingsymbol=symbol,
        transaction_type="SELL",
        quantity=QUANTITY,
        order_type="MARKET",
        product="MIS"
    )
    log(f"✅ Exited trade: {symbol}")

# ---- Fetch First 5-min Candle ----
def get_first_candle():
    log("⏳ Waiting for 9:20 AM to fetch first 5-min candle...")
    while datetime.datetime.now().time() < datetime.time(9, 20):
        time.sleep(1)
    try:
        candles = kite.historical_data(
            instrument_token=256265,
            from_date=datetime.datetime.combine(datetime.date.today(), datetime.time(9, 15)),
            to_date=datetime.datetime.combine(datetime.date.today(), datetime.time(9, 20)),
            interval="5minute"
        )
        if candles:
            return candles[0]["high"], candles[0]["low"]
        else:
            log("❌ Failed to fetch the 9:15 candle. Exiting.")
            exit()
    except Exception as e:
        log(f"❌ Error fetching historical data: {e}")
        exit()

# ---- ATR Calculation ----
def get_atr(instrument_token=256265, interval='5minute', period=14):
    end = datetime.datetime.now()
    start = end - datetime.timedelta(days=5)
    candles = kite.historical_data(instrument_token, start, end, interval)
    trs = []
    for i in range(1, len(candles)):
        high = candles[i]['high']
        low = candles[i]['low']
        prev_close = candles[i - 1]['close']
        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        trs.append(tr)
    return sum(trs[-period:]) / period if len(trs) >= period else None

# ---- Main Trading Logic ----
first_high, first_low = get_first_candle()
ATR = get_atr()
log(f"📊 9:15 Candle — High: {first_high}, Low: {first_low}, ATR: {ATR:.2f}")

breakout_deadline = datetime.datetime.combine(datetime.date.today(), datetime.time(15, 30))
reentry_done = False

while datetime.datetime.now() < breakout_deadline:
    try:
        spot_price = get_nifty_spot()
        direction = None

        if not TRADE_PLACED and not FIRST_TRADE_DONE:
            if spot_price > first_high:
                direction = "CALL"
            elif spot_price < first_low:
                direction = "PUT"

            if direction:
                symbol, token = get_option_by_delta("CE" if direction == "CALL" else "PE")
                if not symbol:
                    log("❌ No valid option instrument found. Skipping trade.")
                    time.sleep(10)
                    continue

                ORDER_ID = place_order(symbol)
                ENTRY_PRICE = get_ltp(symbol)
                OPTION_SYMBOL = symbol
                max_loss_price = ENTRY_PRICE * 0.8
                TRADE_PLACED = True
                NEXT_CHECK_TIME = datetime.datetime.now() + datetime.timedelta(seconds=CHECK_INTERVAL)
                trail_sl_triggered = False
                negative_triggered = False
                negative_started = False
                log(f"🎯 Trade entered: {symbol} at ₹{ENTRY_PRICE:.2f}")

        elif TRADE_PLACED:
            now = datetime.datetime.now()
            if NEXT_CHECK_TIME and now >= NEXT_CHECK_TIME:
                ltp = get_ltp(OPTION_SYMBOL)
                pnl_pct = ((ltp - ENTRY_PRICE) / ENTRY_PRICE) * 100

                if not negative_started and pnl_pct < 0:
                    negative_started = True

                if negative_started and pnl_pct <= -5:
                    negative_triggered = True
                    log("⚠️ Triggered -5% loss condition. Watching for recovery...")

                if negative_triggered and pnl_pct >= 5:
                    exit_trade(OPTION_SYMBOL)
                    TRADE_PLACED = False
                    FIRST_TRADE_DONE = True
                    FIRST_TRADE_WAS_PROFIT = True
                    continue

                if ltp <= max_loss_price:
                    exit_trade(OPTION_SYMBOL)
                    TRADE_PLACED = False
                    FIRST_TRADE_DONE = True
                    FIRST_TRADE_WAS_PROFIT = False
                    continue

                if pnl_pct >= 15 and not trail_sl_triggered:
                    max_loss_price = ENTRY_PRICE * 1.05
                    trail_sl_triggered = True
                    log(f"🔐 Profit >15%, SL moved to lock 5% profit: ₹{max_loss_price:.2f}")

                if pnl_pct >= 20:
                    new_sl = ltp - (ATR_MULTIPLIER * ATR)
                    if new_sl > max_loss_price:
                        max_loss_price = new_sl
                        log(f"🔁 Trailing SL updated to ₹{max_loss_price:.2f}")
                    if ltp <= max_loss_price:
                        exit_trade(OPTION_SYMBOL)
                        TRADE_PLACED = False
                        FIRST_TRADE_DONE = True
                        FIRST_TRADE_WAS_PROFIT = True
                        continue

                NEXT_CHECK_TIME += datetime.timedelta(seconds=CHECK_INTERVAL)

    except Exception as e:
        import traceback
        log(f"⚠️ Error: {e}")
        traceback.print_exc()
        time.sleep(5)
