import os
import requests
import pytz
from datetime import datetime
from telegram import Bot
import pandas as pd
import ta

# Read sensitive information from environment variables
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHANNEL_ID = os.getenv('TELEGRAM_CHANNEL_ID')

# API addresses
COIN_API = 'https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=10&page=1&sparkline=false'
NEWS_API = 'https://min-api.cryptocompare.com/data/v2/news/?lang=EN'
TRENDING_API = 'https://api.coingecko.com/api/v3/search/trending'
BITCOIN_HISTORICAL = 'https://api.coingecko.com/api/v3/coins/bitcoin/market_chart?vs_currency=usd&days=120&interval=daily'



def add_emojis(text):
    crypto_emojis = {"بیت‌کوین": "💰", "اتریوم": "🔷", "اخبار": "📰", "هشدار": "🚨", "آموزش": "📚", "معامله": "📈", "سرگرمی": "😄"}
    for key, emoji in crypto_emojis.items():
        text = text.replace(key, f"{emoji} {key}")
    return text

def get_price_change_emoji(change):
    if change < -2:
        return "🔴"  # Red emoji for negative change less than -2%
    elif -2 <= change <= 2:
        return "⚪️"  # Gray emoji for change between -2% and 2%
    else:
        return "🟢"  # Green emoji for positive change greater than 2%

def get_crypto_data():
    try:
        response = requests.get(COIN_API)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error fetching crypto data: {e}")
        return []

def get_crypto_news():
    try:
        response = requests.get(NEWS_API)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error fetching crypto news: {e}")
        return {"Data": []}

def get_trending_coins():
    try:
        response = requests.get(TRENDING_API)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error fetching trending coins: {e}")
        return {"coins": []}

def get_bitcoin_historical():
    try:
        response = requests.get(BITCOIN_HISTORICAL)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error fetching Bitcoin historical data: {e}")
        return {"prices": []}

async def send_message(bot, message):
    try:
        rtl_message = "\u200F" + add_emojis(message)  # Add RTL mark
        await bot.send_message(chat_id=CHANNEL_ID, text=rtl_message, parse_mode='HTML')
    except Exception as e:
        print(f"Error sending message: {e}")
        if "Message is too long" in str(e):
            parts = [rtl_message[i:i+4096] for i in range(0, len(rtl_message), 4096)]
            for part in parts:
                await bot.send_message(chat_id=CHANNEL_ID, text=part, parse_mode='HTML')

async def post_market_update(bot):
    data = get_crypto_data()
    if not data:
        return

    message = "📊 گزارش بازار ارزهای دیجیتال:\n\n"
    for coin in data[:10]:
        price_change = coin['price_change_percentage_24h']
        change_emoji = get_price_change_emoji(price_change)
        message += f"🪙 {coin['name']} (${coin['symbol'].upper()}):\n"
        message += f"💵 قیمت: ${coin['current_price']:,.2f}\n"
        message += f"📈 تغییر 24 ساعته: {change_emoji} {price_change:.2f}%\n\n"
    
    message += "#گزارش_بازار #ارز_دیجیتال"
    await send_message(bot, message)

async def post_bitcoin_analysis(bot):
    data = get_bitcoin_historical()
    if not data or not data['prices']:
        return

    df = pd.DataFrame(data['prices'], columns=['timestamp', 'price'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)

    # Calculate RSI
    df['rsi'] = ta.momentum.RSIIndicator(df['price'], window=14).rsi()

    # Calculate 120-day Moving Average
    df['ma_120'] = df['price'].rolling(window=120).mean()

    last_price = df['price'].iloc[-1]
    last_rsi = df['rsi'].iloc[-1]
    last_ma = df['ma_120'].iloc[-1]

    message = f"📊 تحلیل بیت‌کوین:\n\n"
    message += f"💰 قیمت فعلی: ${last_price:,.2f}\n"
    message += f"📈 RSI: {last_rsi:.2f}\n"
    message += f"➖ میانگین متحرک 120 روزه: ${last_ma:,.2f}\n\n"

    if last_price > last_ma:
        message += "🔼 قیمت بالای میانگین متحرک 120 روزه است.\n"
    else:
        message += "🔽 قیمت زیر میانگین متحرک 120 روزه است.\n"

    if last_rsi > 70:
        message += "⚠️ RSI در منطقه اشباع خرید است.\n"
    elif last_rsi < 30:
        message += "⚠️ RSI در منطقه اشباع فروش است.\n"
    else:
        message += "✅ RSI در محدوده نرمال است.\n"

    message += "\n#بیت_کوین #تحلیل_تکنیکال"
    await send_message(bot, message)

async def post_crypto_news(bot):
    news = get_crypto_news()
    if news['Data']:
        for article in news['Data'][:3]:
            message = f"📰 اخبار ارزهای دیجیتال:\n\n"
            message += f"<b>{article['title']}</b>\n\n"
            message += f"{article['body'][:200]}...\n\n"
            message += f"<a href='{article['url']}'>ادامه مطلب</a>\n\n"
            message += "#اخبار_کریپتو"
            await send_message(bot, message)

async def post_trending_coins(bot):
    data = get_trending_coins()
    if not data or not data['coins']:
        return

    message = "🔥 ارزهای دیجیتال پرطرفدار:\n\n"
    for coin in data['coins'][:5]:
        coin_data = coin['item']
        message += f"🪙 {coin_data['name']} (${coin_data['symbol']}):\n"
        message += f"🏅 رتبه در بازار: {coin_data['market_cap_rank']}\n"
        message += f"💹 امتیاز CoinGecko: {coin_data['score']}\n\n"

    message += "#ترند_کریپتو #ارزهای_محبوب"
    await send_message(bot, message)

async def main():
    bot = Bot(token=TOKEN)
    now = datetime.now(pytz.timezone('Asia/Tehran'))
    hour = now.hour
    if 9 <= hour <= 12:
        await post_market_update(bot)
    elif 12 <= hour <= 15:
        await post_bitcoin_analysis(bot)
    elif 15 <= hour <= 18:
        await post_crypto_news(bot)
    elif 17 <= hour <= 20:
        await post_trending_coins(bot)

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
