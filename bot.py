import os
import sys
import json
import time
import requests
import yfinance as yf

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
T212_SECRET = os.environ.get("T212_SECRET")
T212_URL = "https://trading212.com" 
TARGET_TICKER = "AAPL"
T212_TICKER = "AAPL_US_EQ"

t212_headers = {
    "Authorization": f"Bearer {T212_SECRET}" if T212_SECRET else "",
    "Content-Type": "application/json"
}

def run_automated_trade():
    print("Vekker boten for å sjekke markedet...")
    try:
        ticker_data = yf.Ticker(TARGET_TICKER)
        history = ticker_data.history(period="2d")
        current_price = history['Close'].iloc[-1]
        print(f"Kurs for {TARGET_TICKER}: \${current_price:.2f}")
    except Exception as e:
        print(f"Feil ved markedsdata: {e}")
        return
    
    try:
        summary_res = requests.get(f"{T212_URL}/equity/account/summary", headers=t212_headers)
        if summary_res.status_code != 200:
            print(f"Trading 212 avviste tilkobling (Status: {summary_res.status_code})")
            return
        free_cash = float(summary_res.json().get("free", 0))
        print(f"Saldo: \${free_cash:.2f}")
    except Exception as e:
        print(f"Tilkoblingsfeil: {e}")
        return
    
    prompt_text = (
        f"You are an automated stock trading bot evaluating {TARGET_TICKER}.\n"
        f"Current Price: \${current_price:.2f}\n"
        f"Available Account Balance: \${free_cash:.2f}\n\n"
        "Respond STRICTLY with a raw, valid JSON object matching this structure exactly:\n"
        '{"action": "BUY" | "SELL" | "HOLD", "quantity": 1.0}'
    )
    
    gemini_url = f"https://googleapis.com{GEMINI_API_KEY}"
    payload = {"contents": [{"parts": [{"text": prompt_text}]}]}
    
    try:
        gemini_res = requests.post(gemini_url, json=payload).json()
        ai_raw_text = gemini_res['candidates']['content']['parts']['text'].strip()
        if "```json" in ai_raw_text:
            ai_raw_text = ai_raw_text.replace("```json", "").replace("```", "").strip()
        decision = json.loads(ai_raw_text)
        print(f"AI Beslutning: {decision}")
    except Exception as e:
        print(f"AI-feil: {e}")
        decision = {"action": "HOLD", "quantity": 0}

    action = decision.get("action")
    qty = float(decision.get("quantity", 0))
    
    if action == "HOLD" or qty <= 0:
        print("Ingen handel utført.")
        return
        
    if action == "SELL":
        qty = -abs(qty)
        
    order_payload = {"ticker": T212_TICKER, "quantity": qty, "timeInForce": "DAY"}
    order_res = requests.post(f"{T212_URL}/equity/orders/market", headers=t212_headers, json=order_payload)
    print("Serverrespons:", order_res.json())

if __name__ == "__main__":
    print("AI-Trading Bot startet på gratis sky-server!")
    while True:
        run_automated_trade()
        # Boten kjører én gang, og sover deretter i 24 timer (86400 sekunder) før neste sjekk
        print("Sjekk fullført. Sover i 24 timer...")
        time.sleep(86400)
