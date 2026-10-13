import os
import sys
import json
import requests
import yfinance as yf

# Henter nøkler fra servermiljøet
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
T212_SECRET = os.environ.get("T212_SECRET")

T212_URL = "https://trading212.com" 
TARGET_TICKER = "AAPL"
T212_TICKER = "AAPL_US_EQ"

# Oppdatert autentisering som slipper gjennom eksterne skyservere
t212_headers = {
    "Authorization": f"Bearer {T212_SECRET}" if T212_SECRET else "",
    "Content-Type": "application/json"
}

def run_automated_trade():
    print("Starter AI-trading bot på godkjent nettverk...")
    
    # 1. Hent aksjekurs fra Yahoo Finance
    try:
        ticker_data = yf.Ticker(TARGET_TICKER)
        history = ticker_data.history(period="2d")
        current_price = history['Close'].iloc[-1]
        print(f"Gjeldende markedspris for {TARGET_TICKER}: \${current_price:.2f}")
    except Exception as e:
        print(f"Feil ved henting av markedsdata: {e}")
        sys.exit(1)
    
    # 2. Hent saldo fra Trading 212
    try:
        summary_res = requests.get(f"{T212_URL}/equity/account/summary", headers=t212_headers)
        if summary_res.status_code != 200:
            print(f"Trading 212 avviste tilkobling (Status: {summary_res.status_code})")
            print(f"Svar fra server: {summary_res.text[:150]}")
            sys.exit(1)
            
        free_cash = float(summary_res.json().get("free", 0))
        print(f"Tilgjengelig saldo på konto: \${free_cash:.2f}")
    except Exception as e:
        print(f"Tilkoblingsfeil: {e}")
        sys.exit(1)
    
    # 3. Spør Gemini AI om råd
    prompt_text = (
        f"You are an automated stock trading bot evaluating {TARGET_TICKER}.\n"
        f"Current Price: \${current_price:.2f}\n"
        f"Available Account Balance: \${free_cash:.2f}\n\n"
        "Respond STRICTLY with a raw, valid JSON object matching this structure exactly, "
        "with absolutely no markdown formatting, no code blocks, and no conversational text:\n"
        '{"action": "BUY" | "SELL" | "HOLD", "quantity": 1.0}'
    )
    
    # Korrigert Gemini API URL
    gemini_url = f"https://googleapis.com{GEMINI_API_KEY}"
    payload = {"contents": [{"parts": [{"text": prompt_text}]}]}
    
    try:
        gemini_res = requests.post(gemini_url, json=payload).json()
        ai_raw_text = gemini_res['candidates'][0]['content']['parts'][0]['text'].strip()
        
        if "```json" in ai_raw_text:
            ai_raw_text = ai_raw_text.replace("```json", "").replace("```", "").strip()
            
        decision = json.loads(ai_raw_text)
        print(f"Gemini AI Beslutning: {decision}")
    except Exception as e:
        print(f"AI-logikk feilet: {e}. Forpaster til HOLD.")
        decision = {"action": "HOLD", "quantity": 0}

    action = decision.get("action")
    qty = float(decision.get("quantity", 0))
    
    # 4. Send ordren automatisk
    if action == "HOLD" or qty <= 0:
        print("AI valgte HOLD. Ingen handel utført.")
        return
        
    if action == "SELL":
        qty = -abs(qty)
        
    order_payload = {"ticker": T212_TICKER, "quantity": qty, "timeInForce": "DAY"}
    print(f"Sender {action}-ordre på {qty} aksjer...")
    order_res = requests.post(f"{T212_URL}/equity/orders/market", headers=t212_headers, json=order_payload)
    print("Handel utført! Serverrespons:", order_res.json())

if __name__ == "__main__":
    run_automated_trade()
