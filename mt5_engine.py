import os
import requests
import time

TWELVEDATA_API_KEY = os.getenv("TWELVEDATA_API_KEY")

def get_pair_data(symbol):
    url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval=15min&outputsize=1&apikey={TWELVEDATA_API_KEY}"
    try:
        response = requests.get(url, timeout=15)
        if response.status_code == 429:
            return symbol, {"status": "LIMIT_HIT"}
        
        data = response.json()
        if "values" not in data:
            return symbol, {"status": "NO_DATA"}
        
        latest = data["values"][0]
        return symbol, {
            "close": float(latest["close"]),
            "high": float(latest["high"]),
            "low": float(latest["low"])
        }
    except Exception:
        return symbol, {"status": "ERROR"}

def run_all_pairs():
    pairs = ["XAU/USD", "EUR/USD", "GBP/USD", "BTC/USD"]
    results = {}
    
    for pair in pairs:
        print(f"Fetching {pair}...")
        results[pair] = get_pair_data(pair)[1]
        # Rate limit bachane ke liye 65 seconds ka wait
        time.sleep(65) 
        
    return results

if __name__ == "__main__":
    print("Starting Sequential Fetch...")
    print(run_all_pairs())
    
