import os
import asyncio
import aiohttp

TWELVEDATA_API_KEY = os.getenv("TWELVEDATA_API_KEY")

async def get_pair_data(session, symbol):
    # API rate limit check
    if not TWELVEDATA_API_KEY:
        return symbol, {"error": "Missing Key"}
    
    url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval=15min&outputsize=1&apikey={TWELVEDATA_API_KEY}"
    
    try:
        async with session.get(url, timeout=10) as resp:
            if resp.status == 429: # Rate limit hit
                return symbol, {"close": 0, "status": "RATE_LIMITED"}
            
            res = await resp.json()
            if "values" not in res:
                return symbol, {"close": 0, "status": "NO_DATA"}
            
            latest = res["values"][0]
            return symbol, {
                "close": float(latest["close"]),
                "high": float(latest["high"]),
                "low": float(latest["low"])
            }
    except Exception:
        return symbol, {"close": 0, "status": "API_ERROR"}

async def run_all_pairs():
    pairs = ["XAU/USD", "EUR/USD", "GBP/USD", "BTC/USD"]
    async with aiohttp.ClientSession() as session:
        # 1.5s delay between calls to avoid API ban
        tasks = []
        for pair in pairs:
            tasks.append(get_pair_data(session, pair))
            await asyncio.sleep(2) 
        
        results = await asyncio.gather(*tasks)
        return {symbol: data for symbol, data in results}
        
