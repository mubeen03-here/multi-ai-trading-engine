import os
import requests
import time

TWELVEDATA_API_KEY = os.getenv("TWELVEDATA_API_KEY")

def fetch_with_retry(symbol):
    # Free Tier ke liye 65 seconds ka delay lazmi hai taake 429 error na aaye
    time.sleep(65)
    url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval=15min&outputsize=1&apikey={TWELVEDATA_API_KEY}"
    try:
        response = requests.get(url, timeout=20)
        if response.status_code == 429:
            return None # Rate limit hit - data skip karein, crash na karein
        
        data = response.json()
        if "values" not in data:
            return None
            
        latest = data["values"][0]
        return {
            "close": float(latest["close"]),
            "high": float(latest["high"]),
            "low": float(latest["low"])
        }
    except Exception:
        return None

def run_all_pairs():
    # Sirf 2 pairs rakhein agar account limit hit ho rahi hai
    pairs = ["XAU/USD", "EUR/USD"] 
    results = {}
    
    for pair in pairs:
        data = fetch_with_retry(pair)
        if data:
            results[pair] = data
        else:
            # Agar data na aaye toh empty dict bhej dein taake engine chale
            results[pair] = {"close": 0, "high": 0, "low": 0}
            
    return results

if __name__ == "__main__":
    print(run_all_pairs())
    
