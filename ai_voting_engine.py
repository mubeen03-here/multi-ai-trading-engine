import os
import asyncio
import aiohttp
import re
from supabase import create_client

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

def get_prompt(market_context):
    return f"Analyze 15M Market Data: {market_context}\nREPLY STRICTLY IN THIS FORMAT: BUY|85|Reason\nNO markdown, NO extra words."

def sanitize_vote(raw_text):
    """AI ke kachre ko saaf kar ke strict DB format banata hai."""
    try:
        clean_text = raw_text.replace('`', '').replace('\n', '').strip()
        parts = clean_text.split('|')
        if len(parts) >= 3:
            raw_vote = parts[0].upper()
            if "BUY" in raw_vote: final_vote = "BUY"
            elif "SELL" in raw_vote: final_vote = "SELL"
            else: final_vote = "HOLD"
            
            conf_str = re.sub(r'\D', '', parts[1])
            conf = int(conf_str) if conf_str else 0
            
            reason = parts[2].strip()[:200]
            return final_vote, conf, reason
    except:
        pass
    return "HOLD", 0, f"Format Error: {raw_text[:50]}"

# --- API Execution Blocks ---
async def call_gemini(session, model, prompt):
    url = f"[https://generativelanguage.googleapis.com/v1beta/models/](https://generativelanguage.googleapis.com/v1beta/models/){model}:generateContent?key={os.getenv('GEMINI_API_KEY')}"
    try:
        async with session.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=10) as r:
            res = await r.json()
            return model, res['candidates'][0]['content']['parts'][0]['text']
    except: return model, "HOLD|0|API Fail"

async def call_groq(session, model, prompt):
    url = "[https://api.groq.com/openai/v1/chat/completions](https://api.groq.com/openai/v1/chat/completions)"
    headers = {"Authorization": f"Bearer {os.getenv('GROQ_API_KEY')}"}
    try:
        async with session.post(url, json={"model": model, "messages": [{"role": "user", "content": prompt}]}, headers=headers, timeout=10) as r:
            res = await r.json()
            return model, res['choices'][0]['message']['content']
    except: return model, "HOLD|0|API Fail"

async def call_mistral(session, prompt):
    key = os.getenv("MISTRAL_API_KEY")
    if not key: return "Mistral", "HOLD|0|No Key"
    url = "[https://api.mistral.ai/v1/chat/completions](https://api.mistral.ai/v1/chat/completions)"
    headers = {"Authorization": f"Bearer {key}"}
    try:
        async with session.post(url, json={"model": "mistral-large-latest", "messages": [{"role": "user", "content": prompt}]}, headers=headers, timeout=10) as r:
            res = await r.json()
            return "Mistral", res['choices'][0]['message']['content']
    except: return "Mistral", "HOLD|0|API Fail"

async def process_consensus(market_payload):
    async with aiohttp.ClientSession() as session:
        for pair, data in market_payload.items():
            if "error" in data: continue
            
            prompt = get_prompt(str(data))
            
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
            results = await asyncio.gather(*tasks)
            
            parsed_votes = []
            decision_map = {"BUY": 0, "SELL": 0, "HOLD": 0}
            
            # Robust Parsing Execution
            for name, raw_text in results:
                v, c, r = sanitize_vote(raw_text)
                decision_map[v] += 1
                parsed_votes.append((name, v, c, r))
            
            # Final Matrix Execution
            final_decision = max(decision_map, key=decision_map.get)
            if decision_map[final_decision] < 4: 
                final_decision = "HOLD"
            
            # Safe Database Injection
            sig_res = supabase.table("signals").insert({"pair": pair, "timeframe": "15M", "final_decision": final_decision}).execute()
            sig_id = sig_res.data[0]['id']
            
            for name, v, c, r in parsed_votes:
                supabase.table("ai_votes").insert({
                    "signal_id": sig_id, "ai_name": name, "vote": v, "confidence": c, "reasoning": r
                }).execute()

if __name__ == "__main__":
    from mt5_engine import run_all_pairs
    data = asyncio.run(run_all_pairs())
    asyncio.run(process_consensus(data))
    
