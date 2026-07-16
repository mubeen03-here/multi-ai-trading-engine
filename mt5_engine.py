async def get_pair_data(session, symbol):
    # API rate limit avoidance (Added delay)
    await asyncio.sleep(1) 
    
    url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval=15min&outputsize=1&apikey={TWELVEDATA_API_KEY}"
    
    try:
        async with session.get(url, timeout=15) as resp:
            if resp.status == 429: # Rate limit error
                return symbol, {"error": "Rate limited - Wait 1 min"}
            
            res = await resp.json()
            if "values" not in res:
                return symbol, {"error": "No Data"}
            
            latest = res["values"][0]
            return symbol, {
                "close": float(latest["close"]),
                "high": float(latest["high"]),
                "low": float(latest["low"])
            }
    except Exception as e:
        return symbol, {"error": "Connection Timeout"}
