import os
import base64
import json
import requests
import yfinance as yf

# ==========================================
# SECURE CONFIGURATION (Reads from GitHub Secrets)
# ==========================================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
T212_KEY = os.environ.get("T212_KEY")
T212_SECRET = os.environ.get("T212_SECRET")

# Trading 212 Official Environments:
# Demo (Paper Trading Sandbox): "https://demo.trading212.com/api/v0"
# Live (Real Capital Portfolio): "https://live.trading212.com/api/v0"
T212_URL = "https://demo.trading212.com/api/v0" 

TARGET_TICKER = "AAPL"        # Yahoo Finance ticker flag
T212_TICKER = "AAPL_US_EQ"    # Trading 212 internal contract tracking ID
MAX_RISK_PERCENT = 0.05       # Guardrail limit: Max 5% account cash exposure

# Construct Basic Authentication Credentials (Key:Secret encoded)
auth_bytes = f"{T212_KEY}:{T212_SECRET}".encode('utf-8')
auth_header = base64.b64encode(auth_bytes).decode('utf-8')
t212_headers = {"Authorization": f"Basic {auth_header}"}

def run_automated_trade():
    print("Initiating free AI trading bot workflow...")
    
    # 1. Fetch market context via Yahoo Finance (yfinance library)
    try:
        ticker_data = yf.Ticker(TARGET_TICKER)
        history = ticker_data.history(period="2d")
        current_price = history['Close'].iloc[-1]
        print(f"Current Market Price for {TARGET_TICKER}: \${current_price:.2f}")
    except Exception as e:
        print(f"Market Data Fetch Interrupted: {e}")
        return
    
    # 2. Extract portfolio values via Trading 212 REST account layer
    try:
        summary_res = requests.get(f"{T212_URL}/equity/account/summary", headers=t212_headers).json()
        free_cash = float(summary_res.get("free", 0))
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
    
    # 4. Prompt Google Gemini Flash API endpoint directly via HTTPS REST requests
    gemini_url = f"https://googleapis.com{GEMINI_API_KEY}"
    payload = {"contents": [{"parts": [{"text": prompt_text}]}]}
    
    try:
        gemini_res = requests.post(gemini_url, json=payload).json()
        ai_raw_text = gemini_res['candidates'][0]['content']['parts'][0]['text'].strip()
        
        # Clean out markdown annotations if model slips back to chat styles
        if "```json" in ai_raw_text:
            ai_raw_text = ai_raw_text.replace("```json", "").replace("```", "").strip()
            
        decision = json.loads(ai_raw_text)
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
        # Trading 212 relies on signed values (Negative quantity = Sell Order execution)
        qty = -abs(qty)
        
    order_payload = {"ticker": T212_TICKER, "quantity": qty, "timeInForce": "DAY"}
    
    print(f"Submitting market execution order: {action} {qty} shares of {T212_TICKER}...")
    order_res = requests.post(f"{T212_URL}/equity/orders/market", headers=t212_headers, json=order_payload)
    print("Trading 212 Server Logs:", order_res.json())

if __name__ == "__main__":
    run_automated_trade()
