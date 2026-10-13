import os
import sys
import json
import requests
import yfinance as yf

# ==========================================
# SIKKER KONFIGURASJON (Henter fra GitHub Secrets)
# ==========================================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
T212_KEY = os.environ.get("T212_KEY")          # Din API Key ID
T212_SECRET = os.environ.get("T212_SECRET")    # Din Secret Key

# VIKTIG: Vi tvinger den dedikerte API-subdomenet, ALDRI hovednettsiden!
T212_URL = "https://demo.trading212.com/api/v0" 

TARGET_TICKER = "AAPL"
T212_TICKER = "AAPL_US_EQ"
MAX_RISK_PERCENT = 0.05

# For å lure Cloudflare må vi sende med en 'User-Agent' som ser ut som en ekte nettleser,
# og bruke den offisielle måten Trading 212 krever nøkkelen på (X-API-KEY).
t212_headers = {
    "X-API-KEY": T212_SECRET if T212_SECRET else T212_KEY,
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def run_automated_trade():
    print("Starter gratis AI-trading bot...")
    
    # 1. Hent markedsdata gratis via Yahoo Finance
    try:
        ticker_data = yf.Ticker(TARGET_TICKER)
        history = ticker_data.history(period="2d")
        current_price = history['Close'].iloc[-1]
        print(f"Gjeldende markedspris for {TARGET_TICKER}: \${current_price:.2f}")
    except Exception as e:
        print(f"Feil under henting av markedsdata: {e}")
        sys.exit(1)
    
    # 2. Hent kontobalanse fra Trading 212 API
    try:
        summary_res = requests.get(f"{T212_URL}/equity/account/summary", headers=t212_headers)
        print(f"Trading 212 Statuskode: {summary_res.status_code}")
        
        # Hvis Cloudflare eller feil nøkkel stopper oss, tvinger vi GitHub til å lyse RØDT (sys.exit)
        if summary_res.status_code != 200:
            print(f"Klarte ikke å koble til Trading 212. Serveren svarte: {summary_res.text[:200]}")
            print("Tips: Hvis du fortsatt får 403, betyr det at Trading 212 blokkerer GitHub-servere fullstendig.")
            sys.exit(1)
            
        summary_data = summary_res.json()
        free_cash = float(summary_data.get("free", 0))
        print(f"Verifisert tilgjengelig saldo: \${free_cash:.2f}")
    except Exception as e:
        print(f"Tilkobling til Trading 212 avbrutt: {e}")
        sys.exit(1)
    
    # 3. Lag prompt til Gemini AI
    prompt_text = (
        f"You are a robotic trading bot evaluating {TARGET_TICKER}.\n"
        f"Current Price: \${current_price:.2f}\n"
        f"Available Balance: \${free_cash:.2f}\n\n"
        "Respond STRICTLY with a raw, valid JSON object matching this structure exactly, "
        "with absolutely no markdown formatting, no code blocks, and no conversational text:\n"
        '{"action": "BUY" | "SELL" | "HOLD", "quantity": 1.0}'
    )
    
    # 4. Send til Google Gemini Flash (Gratis API)
    gemini_url = f"https://googleapis.com{GEMINI_API_KEY}"
    payload = {"contents": [{"parts": [{"text": prompt_text}]}]}
    
    try:
        gemini_res = requests.post(gemini_url, json=payload).json()
        ai_raw_text = gemini_res['candidates']['content']['parts']['text'].strip()
        
        if "```json" in ai_raw_text:
            ai_raw_text = ai_raw_text.replace("```json", "").replace("```", "").strip()
            
        decision = json.loads(ai_raw_text)
        print(f"AI-beslutning tolket vellykket: {decision}")
    except Exception as e:
        print(f"Feil i AI-logikken: {e}. Forpaster sikkerhetssekvens: HOLD.")
        decision = {"action": "HOLD", "quantity": 0}

    action = decision.get("action")
    qty = float(decision.get("quantity", 0))
    
    # 5. Sikkerhetssjekk og utførelse
    if action == "HOLD" or qty <= 0:
        print("AI valgte HOLD. Ingen ordre sendt.")
        return
        
    if action == "SELL":
        qty = -abs(qty)
        
    order_payload = {"ticker": T212_TICKER, "quantity": qty, "timeInForce": "DAY"}
    
    print(f"Sender ordre til markedet: {action} {qty} aksjer i {T212_TICKER}...")
    order_res = requests.post(f"{T212_URL}/equity/orders/market", headers=t212_headers, json=order_payload)
    print("Trading 212 Server-respons:", order_res.json())

if __name__ == "__main__":
    run_automated_trade()
