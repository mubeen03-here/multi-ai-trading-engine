import os
import asyncio
import aiohttp

TWELVEDATA_API_KEY = os.getenv("TWELVEDATA_API_KEY")

async def get_pair_data(session, symbol):
    """
    Direct TwelveData API call without heavy pandas library.
    """
    if not TWELVEDATA_API_KEY:
        return symbol, {"error": "Missing TWELVEDATA_API_KEY"}
    
    url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval=15min&outputsize=10&apikey={TWELVEDATA_API_KEY}"
    
    try:
        async with session.get(url, timeout=10) as resp:
            res = await resp.json()
            if "values" not in res or not res["values"]:
                return symbol, {"error": res.get("message", "No data returned")}
            
            latest = res["values"][0]
            data_summary = {
                "close": float(latest["close"]),
                "high": float(latest["high"]),
                "low": float(latest["low"]),
                "open": float(latest["open"]),
                "volume": float(latest.get("volume", 0))
            }
            return symbol, data_summary
    except Exception as e:
        return symbol, {"error": str(e)}

async def run_all_pairs():
    """
    Parallel market data fetching engine.
    """
    pairs = ["XAU/USD", "EUR/USD", "GBP/USD", "BTC/USD"]
    async with aiohttp.ClientSession() as session:
        tasks = [get_pair_data(session, pair) for pair in pairs]
        results = await asyncio.gather(*tasks)
        return {symbol: data for symbol, data in results}

if __name__ == "__main__":
    data = asyncio.run(run_all_pairs())
    print("Market Data Payload:", data)
    
