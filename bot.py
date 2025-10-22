# bot.py - Kakaroto Albatross v3.0 (MAINNET - 24/7)
import streamlit as st
import time
import json
import pandas as pd
from hyperliquid.info import Info
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants
import pytz
from datetime import datetime, timedelta

# === CHAVES VIA SECRETS ===
ACCOUNT_ADDRESS = st.secrets["ACCOUNT_ADDRESS"]
SECRET_KEY = st.secrets["SECRET_KEY"]

info = Info(constants.MAINNET_API_URL, skip_ws=True)
exchange = Exchange(ACCOUNT_ADDRESS, SECRET_KEY, base_url=constants.MAINNET_API_URL)

NY_TZ = pytz.timezone('America/New_York')
position = None
fib_levels_today = {}
consecutive_losses = 0

def send_telegram(msg):
    # Telegram opcional
    pass

def get_fib_levels():
    now = datetime.now(NY_TZ)
    start = now.replace(hour=3, minute=33, second=0, microsecond=0) - timedelta(days=1)
    end = start + timedelta(days=1)
    start_ts = int(start.timestamp() * 1000)
    end_ts = int(end.timestamp() * 1000)
    try:
        candles = info.candles_snapshot("BTC", "5m", start_ts, end_ts)
        if not candles:
            return None
        df = pd.DataFrame(candles, columns=["ts", "o", "h", "l", "c", "v"])
        high = df['h'].max()
        low = df['l'].min()
        range_val = high - low
        if range_val < high * 0.01:
            return None
        return {
            "2.0": high - 2.0 * range_val,
            "-0.382": high + 0.382 * range_val,
            "-0.618": high + 0.618 * range_val
        }
    except:
        return None

def is_power_hour(ts):
    t = datetime.fromtimestamp(ts/1000, NY_TZ)
    return t.hour == 9 and t.minute in [36, 45]

def check_signal(candle):
    global fib_levels_today
    if not fib_levels_today:
        fib_levels_today = get_fib_levels()
        if not fib_levels_today:
            return None
    low, high = candle['l'], candle['h']
    vol_avg = candle['vol_avg_50']
    if candle['volume'] < 1.7 * vol_avg:
        return None
    if not (9 <= datetime.fromtimestamp(candle['ts']/1000, NY_TZ).hour < 16):
        return None
    for level_name, level_price in fib_levels_today.items():
        if low <= level_price <= high:
            return level_name
    return None

def open_position(side):
    global position, consecutive_losses
    if consecutive_losses >= 3:
        return
    price = info.all_mids().get("BTC", 0)
    if price == 0:
        return
    size = 18 / (price * 0.01)
    result = exchange.order("BTC", side == "long", size, price, {"limit": {"tif": "Gtc"}}, reduce_only=False)
    if result.get("status") == "Ok":
        position = {"side": side, "entry": price, "size": size, "stop": price * (0.99 if side == "long" else 1.01)}
        send_telegram(f"ABERTO {side.upper()} @ ${price:,.0f}")

def update_trailing():
    global position
    if not position:
        return
    mid = info.all_mids().get("BTC", 0)
    if mid == 0:
        return
    pnl_pct = (mid - position['entry']) / position['entry'] * (1 if position['side'] == "long" else -1)
    if pnl_pct >= 0.01:
        new_stop = position['entry'] + (0.01 * position['entry']) * (1 if position['side'] == "long" else -1)
        position['stop'] = new_stop
        send_telegram(f"TRAILING: Stop ${new_stop:,.0f}")

    if (position['side'] == "long" and mid <= position['stop']) or \
       (position['side'] == "short" and mid >= position['stop']):
        close_position(mid)

def close_position(exit_price):
    global position, consecutive_losses
    pnl = (exit_price - position['entry']) * position['size'] * (1 if position['side'] == "long" else -1)
    if pnl < 0:
        consecutive_losses += 1
    else:
        consecutive_losses = 0
    send_telegram(f"FECHADO: PnL ${pnl:+.2f}")
    position = None

# === LOOP 24/7 ===
st.write("Bot rodando em background...")
while True:
    try:
        now = datetime.now(NY_TZ)
        if now.hour == 3 and now.minute == 33:
            fib_levels_today = {}
        candles = info.candles_snapshot("BTC", "5m", int((time.time() - 300)*1000), int(time.time()*1000))
        if candles and len(candles) > 50:
            df = pd.DataFrame(candles, columns=["ts", "o", "h", "l", "c", "v"])
            df['vol_avg_50'] = df['v'].rolling(50).mean()
            latest = df.iloc[-2].to_dict()
            latest['vol_avg_50'] = df['vol_avg_50'].iloc[-2]
            if not position:
                signal = check_signal(latest)
                if signal:
                    side = "short" if signal == "2.0" else "long"
                    open_position(side)
            else:
                update_trailing()
        time.sleep(30)
    except Exception as e:
        st.error(f"Erro no bot: {e}")
        time.sleep(60)
