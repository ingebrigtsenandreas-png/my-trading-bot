import os
import json
import requests
import yfinance as yf

# ==========================================
# SECURE CONFIGURATION (Reads from GitHub Secrets)
# ==========================================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
T212_KEY = os.environ.get("T212_KEY")
T212_SECRET = os.environ.get("T212_SECRET")

# Pointing directly to the dedicated cloud endpoint to bypass web filters
T212_URL = "https://trading212.com" 
TARGET_TICKER = "AAPL"
T212_TICKER = "AAPL_US_EQ"
MAX_RISK_PERCENT = 0.05

# Trading 212 API Header Structure
t212_headers = {
    "X-API-KEY": T212_SECRET if T212_SECRET else T212_KEY,
    "Content-Type": "application/json"
}

def run_automated_trade():
    print("Initiating free AI trading bot workflow...")
    
    # 1. Fetch market data via Yahoo Finance
    try:
        ticker_data = yf.Ticker(TARGET_TICKER)
        history = ticker_data.history(period="2d")
        current_price = history['Close'].iloc[-1]
        print(f"Current Market Price for {TARGET_TICKER}: \${current_price:.2f}")
    except Exception as e:
        print(f"Market Data Fetch Interrupted: {e}")
        return
    
    # 2. Extract portfolio values from Trading 212
    try:
        summary_res = requests.get(f"{T212_URL}/equity/account/summary", headers=t212_headers)
        print(f"Trading 212 Status Code: {summary_res.status_code}")
        
        if summary_res.status_code != 200:
            print(f"Trading 212 returned error text: {summary_res.text}")
            return
            
        summary_data = summary_res.json()
        free_cash = float(summary_data.get("free", 0))
        print(f"Verified available liquidity balance: \${free_cash:.2f}")
    except Exception as e:
        print(f"Trading 212 Connection Dropped: {e}")
        return
    
    # 3. Compile highly constrained structured prompt layout
    prompt_text = (
        f"You are a robotic trading bot evaluating {TARGET_TICKER}.\n"
        f"Current Price: \${current_price:.2f}\n"
        f"Available Balance: \${free_cash:.2f}\n\n"
        "Respond STRICTLY with a raw, valid JSON object matching this structure exactly, "
        "with absolutely no markdown formatting, no code blocks, and no conversational text:\n"
        '{"action": "BUY" | "SELL" | "HOLD", "quantity": 1.0}'
    )
    
    # 4. Corrected complete Google Gemini Flash endpoint path
    gemini_url = f"https://googleapis.com{GEMINI_API_KEY}"
    payload = {"contents": [{"parts": [{"text": prompt_text}]}]}
    
    try:
        gemini_res = requests.post(gemini_url, json=payload).json()
        ai_raw_text = gemini_res['candidates']['content']['parts']['text'].strip()
        
        if "```json" in ai_raw_text:
            ai_raw_text = ai_raw_text.replace("```json", "").replace("```", "").strip()
            
        decision = json.loads(ai_raw_text)
        print(f"AI Decision Data Object parsed successfully: {decision}")
    except Exception as e:
        print(f"AI decision-making logic error: {e}. Forcing safety sequence: HOLD.")
        decision = {"action": "HOLD", "quantity": 0}

    action = decision.get("action")
    qty = float(decision.get("quantity", 0))
    
    # 5. Core Operational Safety Check
    if action == "HOLD" or qty <= 0:
        print("Decision resolution settled on HOLD. Aborting trade execution.")
        return
        
    if action == "SELL":
        qty = -abs(qty)
        
    order_payload = {"ticker": T212_TICKER, "quantity": qty, "timeInForce": "DAY"}
    
    print(f"Submitting market execution order: {action} {qty} shares of {T212_TICKER}...")
    order_res = requests.post(f"{T212_URL}/equity/orders/market", headers=t212_headers, json=order_payload)
    print("Trading 212 Server Logs:", order_res.json())

if __name__ == "__main__":
    run_automated_trade()
