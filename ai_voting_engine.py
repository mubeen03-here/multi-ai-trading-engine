import os
import asyncio
import aiohttp
from supabase import create_client

# Database Client Setup
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

def get_prompt(market_context):
    return f"""
    Analyze 15M Market Data: {market_context}
    Provide action: BUY, SELL, or HOLD.
    Confidence: 0 to 100.
    Format response EXACTLY like this: BUY|85|Wick rejection at support
    No extra text.
    """

# --- GOOGLE GEMINI MODELS ---
async def call_gemini(session, model_name, prompt):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={os.getenv('GEMINI_API_KEY')}"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    try:
        async with session.post(url, json=payload, timeout=10) as r:
            res = await r.json()
            return model_name, res['candidates'][0]['content']['parts'][0]['text'].strip()
    except Exception:
        return model_name, "HOLD|0|Skipped (API Error)"

# --- GROQ CLOUD MODELS ---
async def call_groq(session, model_name, prompt):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {os.getenv('GROQ_API_KEY')}"}
    payload = {"model": model_name, "messages": [{"role": "user", "content": prompt}]}
    try:
        async with session.post(url, json=payload, headers=headers, timeout=10) as r:
            res = await r.json()
            return model_name, res['choices'][0]['message']['content'].strip()
    except Exception:
        return model_name, "HOLD|0|Skipped (API Error)"

# --- MISTRAL AI MODEL (AUTO-SKIP ON FAILURE) ---
async def call_mistral(session, prompt):
    api_key = os.getenv("MISTRAL_API_KEY")
    if not api_key:
        return "Mistral-Large", "HOLD|0|Skipped (No Key)"
        
    url = "https://api.mistral.ai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}"}
    payload = {"model": "mistral-large-latest", "messages": [{"role": "user", "content": prompt}]}
    try:
        async with session.post(url, json=payload, headers=headers, timeout=10) as r:
            if r.status != 200:
                return "Mistral-Large", "HOLD|0|Skipped (Status Code Error)"
            res = await r.json()
            return "Mistral-Large", res['choices'][0]['message']['content'].strip()
    except Exception:
        return "Mistral-Large", "HOLD|0|Skipped (Execution Error)"

async def process_consensus(market_payload):
    async with aiohttp.ClientSession() as session:
        for pair, data in market_payload.items():
            if "error" in data: continue
            
            prompt = get_prompt(str(data))
            
            # Parallel Calls (Gemini + Groq + Mistral)
            tasks = [
                call_gemini(session, "gemini-1.5-pro", prompt),
                call_gemini(session, "gemini-1.5-flash", prompt),
                call_gemini(session, "gemini-2.0-flash-exp", prompt),
                call_groq(session, "llama-3.3-70b-versatile", prompt),
                call_groq(session, "llama-3.1-8b-instant", prompt),
                call_groq(session, "mixtral-8x7b-32768", prompt),
                call_groq(session, "gemma2-9b-it", prompt),
                call_mistral(session, prompt)
            ]
            raw_results = await asyncio.gather(*tasks)
            
            parsed_votes = []
            decision_map = {"BUY": 0, "SELL": 0, "HOLD": 0}
            
            for ai_name, raw_text in raw_results:
                try:
                    vote, conf, reason = raw_text.split('|')
                    conf = int(conf)
                except:
                    vote, conf, reason = "HOLD", 0, "Parsing Error"
                
                if vote in decision_map:
                    decision_map[vote] += 1
                parsed_votes.append((ai_name, vote, conf, reason))
            
            # Dynamic Consensus Rule: Majority decision based on active votes
            final_decision = max(decision_map, key=decision_map.get)
            if decision_map[final_decision] < 4: 
                final_decision = "HOLD"
            
            # Save Signals to Database
            signal_res = supabase.table("signals").insert({"pair": pair, "timeframe": "15M", "final_decision": final_decision}).execute()
            signal_id = signal_res.data[0]['id']
            
            # Save Individual Votes
            for name, vote, conf, reason in parsed_votes:
                supabase.table("ai_votes").insert({
                    "signal_id": signal_id,
                    "ai_name": name,
                    "vote": vote,
                    "confidence": conf,
                    "reasoning": reason
                }).execute()

if __name__ == "__main__":
    from mt5_engine import run_all_pairs
    market_data = asyncio.run(run_all_pairs())
    asyncio.run(process_consensus(market_data))
          
