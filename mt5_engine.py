import MetaTrader5 as mt5
import pandas as pd

# 5 Locked Pairs List
TARGET_PAIRS = ["XAUUSD", "EURUSD", "NAS100", "USDJPY", "BTCUSD"]

def fetch_market_data(symbol, timeframe=mt5.TIMEFRAME_M15, count=50):
    """
    MT5 se numeric price, key levels, aur wick rejection tracking data extract karta hai.
    """
    if not mt5.initialize():
        return {"error": "MT5 initialize nahi ho saka"}

    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, count)
    mt5.shutdown()

    if rates is None or len(rates) == 0:
        return {"error": f"{symbol} ka data nahi mila"}

    df = pd.DataFrame(rates)
    
    # Body aur Wicks calculation
    df['body'] = (df['close'] - df['open']).abs()
    df['upper_wick'] = df['high'] - df[['open', 'close']].max(axis=1)
    df['lower_wick'] = df[['open', 'close']].min(axis=1) - df['low']

    # Support aur Resistance Zones
    resistance = float(df['high'].max())
    support = float(df['low'].min())

    # Rejection Logic: Upper/Lower Wick if > 1.8x Body Size
    last_candle = df.iloc[-1]
    top_rejection = last_candle['upper_wick'] > (1.8 * last_candle['body'])
    bottom_rejection = last_candle['lower_wick'] > (1.8 * last_candle['body'])

    return {
        "pair": symbol,
        "timeframe": "15M",
        "price": float(last_candle['close']),
        "levels": {"resistance": resistance, "support": support},
        "rejection": {
            "top_rejection": bool(top_rejection),
            "bottom_rejection": bool(bottom_rejection)
        }
    }

def run_all_pairs():
    """
    5 pairs par loop chala kar JSON dictionary ready karta hai.
    """
    results = {}
    for pair in TARGET_PAIRS:
        data = fetch_market_data(pair)
        results[pair] = data
    return results

if __name__ == "__main__":
    market_payload = run_all_pairs()
    print(market_payload)
    
