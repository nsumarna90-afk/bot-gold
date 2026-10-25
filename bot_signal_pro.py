import telebot
from telebot import types
import yfinance as yf
import pandas as pd
import requests
import threading
import time
from datetime import datetime

# ========== GANTI TOKEN LU ==========
TOKEN = "8812650205:AAFcT1TuBAA31Gp5L48b0AXi8nw7IlUn034"
# ====================================
bot = telebot.TeleBot(TOKEN)

# ====== PAIR LENGKAP - BUKAN CUMA XAUUSD ======
PAIRS = {
    "XAUUSD": "GC=F",
    "EURUSD": "EURUSD=X",
    "GBPUSD": "GBPUSD=X",
    "USDJPY": "USDJPY=X",
    "AUDUSD": "AUDUSD=X",
    "NZDUSD": "NZDUSD=X",
    "USDCAD": "USDCAD=X",
    "USDCHF": "USDCHF=X",
    "EURJPY": "EURJPY=X",
    "GBPJPY": "GBPJPY=X",
    "BTCUSD": "BTC-USD",
    "ETHUSD": "ETH-USD"
}
TIMEFRAMES = {
    "M1": "1m", "M5": "5m", "M15": "15m", "H1": "60m", "H4": "60m", "D1": "1d"
}
user_data = {}

def get_signal(pair_code, tf_code):
    try:
        ticker = PAIRS[pair_code]
        yf_tf = TIMEFRAMES[tf_code]
        interval = "7d" if tf_code != "D1" else "1mo"
        df = yf.download(ticker, period=interval, interval=yf_tf, progress=False)
        if len(df) < 50: return None
        close = df['Close'].squeeze()
        ema20 = close.ewm(span=20).mean().iloc[-1]
        ema50 = close.ewm(span=50).mean().iloc[-1]
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        rsi_val = rsi.iloc[-1]
        price = close.iloc[-1]
        buy_score = 50
        if ema20 > ema50: buy_score += 15
        else: buy_score -= 15
        if rsi_val > 50: buy_score += 10
        else: buy_score -= 10
        if rsi_val < 30: buy_score += 15
        if rsi_val > 70: buy_score -= 15
        buy_score = max(10, min(90, buy_score))
        sell_score = 100 - buy_score
        return price, buy_score, sell_score
    except Exception as e:
        print(e)
        return None

def get_calendar():
    try:
        url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
        r = requests.get(url, timeout=10).json()
        result = [x for x in r if x.get('country')=='USD' and x.get('impact')=='High']
        return result[:15]
    except:
        return []

def analisa_news(n):
    actual = n.get('actual','')
    forecast = n.get('forecast','')
    if not actual: return None
    try:
        act = float(str(actual).replace('%','').replace('K',''))
        fore = float(str(forecast).replace('%','').replace('K','')) if forecast else act
    except: act=0; fore=0
    if act > fore:
        return f"USD KUAT -> XAUUSD JUNAM 🔴"
    else:
        return f"USD LEMAH -> XAUUSD FLY 🟢"

@bot.message_handler(commands=['start'])
def start(m):
    markup = types.InlineKeyboardMarkup(row_width=3)
    markup.add(
        types.InlineKeyboardButton("XAUUSD", callback_data="pair_XAUUSD"),
        types.InlineKeyboardButton("EURUSD", callback_data="pair_EURUSD"),
        types.InlineKeyboardButton("GBPUSD", callback_data="pair_GBPUSD"),
        types.InlineKeyboardButton("USDJPY", callback_data="pair_USDJPY"),
        types.InlineKeyboardButton("AUDUSD", callback_data="pair_AUDUSD"),
        types.InlineKeyboardButton("NZDUSD", callback_data="pair_NZDUSD"),
        types.InlineKeyboardButton("USDCAD", callback_data="pair_USDCAD"),
        types.InlineKeyboardButton("USDCHF", callback_data="pair_USDCHF"),
        types.InlineKeyboardButton("EURJPY", callback_data="pair_EURJPY"),
        types.InlineKeyboardButton("GBPJPY", callback_data="pair_GBPJPY"),
        types.InlineKeyboardButton("BTCUSD", callback_data="pair_BTCUSD"),
        types.InlineKeyboardButton("ETHUSD", callback_data="pair_ETHUSD"),
        types.InlineKeyboardButton("📰 NEWS GOLD JUNAM/FLY", callback_data="menu_news")
    )
    bot.send_message(m.chat.id, "🤖 BOT PRO 12 PAIR + NEWS\n\nPILIH PAIR (bukan cuma XAUUSD):", reply_markup=markup)

@bot.callback_query_handler(func=lambda c: True)
def callback(call):
    if call.data.startswith("pair_"):
        pair = call.data.split("_")[1]
        user_data[call.message.chat.id] = {"pair": pair}
        markup = types.InlineKeyboardMarkup(row_width=3)
        markup.add(
            types.InlineKeyboardButton("M1", callback_data="tf_M1"),
            types.InlineKeyboardButton("M5", callback_data="tf_M5"),
            types.InlineKeyboardButton("M15", callback_data="tf_M15"),
            types.InlineKeyboardButton("H1", callback_data="tf_H1"),
            types.InlineKeyboardButton("H4", callback_data="tf_H4"),
            types.InlineKeyboardButton("D1", callback_data="tf_D1"),
        )
        bot.edit_message_text(f"Pair: {pair}\nPILIH TIMEFRAME:", call.message.chat.id, call.message.message_id, reply_markup=markup)
    
    elif call.data.startswith("tf_"):
        tf = call.data.split("_")[1]
        pair = user_data.get(call.message.chat.id, {}).get("pair", "XAUUSD")
        bot.send_message(call.message.chat.id, f"⏳ Analisa {pair} {tf}...")
        hasil = get_signal(pair, tf)
        if hasil:
            price, buy, sell = hasil
            bot.send_message(call.message.chat.id, f"📊 {pair} - {tf}\nHarga: {price:.2f}\nBUY: {buy}% 🟢\nSELL: {sell}% 🔴\nEntry: {price*0.999:.2f} - {price:.2f}")
        else:
            bot.send_message(call.message.chat.id, "Data gagal, coba TF lain.")

    elif call.data == "menu_news":
        bot.send_message(call.message.chat.id, "⏳ Narik news USD...")
        news = get_calendar()
        if not news:
            bot.send_message(call.message.chat.id, "Kalender kosong.")
            return
        txt = "📅 NEWS USD HIGH IMPACT (NGARUH KE SEMUA PAIR + GOLD)\n\n"
        for n in news:
            extra = ""
            if n.get('actual'):
                extra = f" -> {analisa_news(n)}"
            txt += f"{n.get('time','')} - {n.get('title')}\nAct: {n.get('actual','-')} | Fore: {n.get('forecast','-')}{extra}\n\n"
        bot.send_message(call.message.chat.id, txt)

print("Bot 12 PAIR + NEWS jalan... jangan close CMD")
bot.infinity_polling()