import os
import asyncio
import aiohttp
import pandas as pd

# 5 Locked Pairs List
PAIR_MAP = {
    "XAUUSD": "XAU/USD",
    "EURUSD": "EUR/USD",
    "NAS100": "QQQ",
    "USDJPY": "USD/JPY",
    "BTCUSD": "BTC/USD"
}

API_KEY = os.getenv("TWELVEDATA_API_KEY")

async def fetch_pair_data(session, symbol, ticker):
    """
    Direct Cloud REST API se 100% exact 15M candles fetch karta hai.
    """
    url = f"https://api.twelvedata.com/time_series?symbol={ticker}&interval=15min&outputsize=50&apikey={API_KEY}"
    
    try:
        async with session.get(url) as response:
            data = await response.json()
            
            if "values" not in data:
                return symbol, {"error": f"{symbol} data fetch failed"}

            df = pd.DataFrame(data["values"])
            
            # Numeric conversion
            df['open'] = df['open'].astype(float)
            df['high'] = df['high'].astype(float)
            df['low'] = df['low'].astype(float)
            df['close'] = df['close'].astype(float)

            # Body aur Wick Calculations
            df['body'] = (df['close'] - df['open']).abs()
            df['upper_wick'] = df['high'] - df[['open', 'close']].max(axis=1)
            df['lower_wick'] = df[['open', 'close']].min(axis=1) - df['low']

            resistance = float(df['high'].max())
            support = float(df['low'].min())

            last = df.iloc[0] # TwelveData delivers newest first
            top_rejection = bool(last['upper_wick'] > (1.8 * last['body']))
            bottom_rejection = bool(last['lower_wick'] > (1.8 * last['body']))

            return symbol, {
                "pair": symbol,
                "timeframe": "15M",
                "price": float(last['close']),
                "levels": {"resistance": resistance, "support": support},
                "rejection": {
                    "top_rejection": top_rejection,
                    "bottom_rejection": bottom_rejection
                }
            }
    except Exception as e:
        return symbol, {"error": str(e)}

async def run_all_pairs():
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_pair_data(session, pair, ticker) for pair, ticker in PAIR_MAP.items()]
        results = await asyncio.gather(*tasks)
        return dict(results)

if __name__ == "__main__":
    market_data = asyncio.run(run_all_pairs())
    print(market_data)
