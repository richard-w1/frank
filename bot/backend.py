from fastapi import FastAPI, Request
from together import Together
import os
from dotenv import load_dotenv
from fastapi.concurrency import run_in_threadpool
import requests
from coinbase import jwt_generator
import json
from typing import Dict, Any, Optional
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY")
COINBASE_API_KEY = os.getenv("COINBASE_API_KEY")
COINBASE_API_SECRET = os.getenv("COINBASE_API_SECRET")

app = FastAPI()
client = Together(api_key=TOGETHER_API_KEY)

def get_coinbase_jwt(method: str, path: str) -> str:
    """Generate JWT for Coinbase API"""
    jwt_uri = jwt_generator.format_jwt_uri(method, path)
    return jwt_generator.build_rest_jwt(jwt_uri, COINBASE_API_KEY, COINBASE_API_SECRET)

def get_crypto_price(symbol: str) -> Optional[float]:
    """Get current price of a cryptocurrency"""
    try:
        response = requests.get(f"https://api.coinbase.com/v2/prices/{symbol}-USD/spot")
        if response.status_code == 200:
            return float(response.json()["data"]["amount"])
        return None
    except Exception as e:
        logger.error(f"Error getting price: {e}")
        return None

def get_portfolio_balance() -> Optional[Dict]:
    """Get user's portfolio balance"""
    try:
        jwt_token = get_coinbase_jwt("GET", "/v2/accounts")
        headers = {"Authorization": f"Bearer {jwt_token}"}
        response = requests.get("https://api.coinbase.com/v2/accounts", headers=headers)
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        logger.error(f"Error getting portfolio: {e}")
        return None

def get_market_status() -> Dict:
    """Get current market status for major cryptocurrencies"""
    try:
        btc_price = get_crypto_price("BTC")
        eth_price = get_crypto_price("ETH")
        
        # Get 24h price changes
        btc_change = None
        eth_change = None
        
        if btc_price:
            response = requests.get("https://api.coinbase.com/v2/prices/BTC-USD/historic?period=day")
            if response.status_code == 200:
                data = response.json()
                prices = [float(p["price"]) for p in data["data"]["prices"]]
                btc_change = ((prices[-1] - prices[0]) / prices[0]) * 100
        
        if eth_price:
            response = requests.get("https://api.coinbase.com/v2/prices/ETH-USD/historic?period=day")
            if response.status_code == 200:
                data = response.json()
                prices = [float(p["price"]) for p in data["data"]["prices"]]
                eth_change = ((prices[-1] - prices[0]) / prices[0]) * 100
        
        return {
            "btc": {"price": btc_price, "change_24h": btc_change},
            "eth": {"price": eth_price, "change_24h": eth_change}
        }
    except Exception as e:
        logger.error(f"Error getting market status: {e}")
        return {}

@app.post("/query")
async def query(request: Request):
    data = await request.json()
    user_prompt = data.get("prompt", "")

    try:
        # First, get intent from LLM
        response = await run_in_threadpool(
            lambda: client.chat.completions.create(
                model="meta-llama/Llama-3.3-70B-Instruct-Turbo-Free",
                messages=[{
                    "role": "user", 
                    "content": f"""Analyze this crypto trading request and determine the intent. 
                    Return a JSON with the following structure:
                    {{
                        "intent": "trade|price|portfolio|market",
                        "symbol": "BTC|ETH|etc",
                        "amount": number or null,
                        "side": "buy|sell" or null
                    }}
                    
                    Request: {user_prompt}"""
                }],
                max_tokens=200,
                temperature=0.7,
                top_p=0.9
            )
        )
        
        # Parse the intent
        intent_data = json.loads(response.choices[0].message.content)
        
        # Handle different intents
        if intent_data["intent"] == "price":
            price = get_crypto_price(intent_data["symbol"])
            if price:
                return {"response": f"Current price of {intent_data['symbol']}: ${price:,.2f}"}
            return {"response": f"Sorry, couldn't get the price for {intent_data['symbol']}"}
            
        elif intent_data["intent"] == "portfolio":
            portfolio = get_portfolio_balance()
            if portfolio:
                portfolio_info = "**Your Portfolio:**\n"
                total_value = 0.0
                for account in portfolio.get("data", []):
                    balance = float(account.get("balance", {}).get("amount", 0))
                    currency = account.get("currency")
                    if balance > 0:
                        if currency != "USD":
                            price = get_crypto_price(currency)
                            if price:
                                value = balance * price
                                total_value += value
                                portfolio_info += f"{currency}: {balance} (${value:,.2f})\n"
                        else:
                            total_value += balance
                            portfolio_info += f"{currency}: ${balance:,.2f}\n"
                portfolio_info += f"\n**Total Portfolio Value: ${total_value:,.2f}**"
                return {"response": portfolio_info}
            return {"response": "Sorry, couldn't fetch your portfolio information"}
            
        elif intent_data["intent"] == "market":
            market_status = get_market_status()
            market_info = "**Current Market Status:**\n"
            
            if market_status.get("btc"):
                btc = market_status["btc"]
                market_info += f"BTC: ${btc['price']:,.2f}"
                if btc['change_24h']:
                    market_info += f" ({btc['change_24h']:+.2f}%)\n"
                else:
                    market_info += "\n"
                    
            if market_status.get("eth"):
                eth = market_status["eth"]
                market_info += f"ETH: ${eth['price']:,.2f}"
                if eth['change_24h']:
                    market_info += f" ({eth['change_24h']:+.2f}%)\n"
                else:
                    market_info += "\n"
                    
            return {"response": market_info}
            
        elif intent_data["intent"] == "trade":
            # For trading, we'll need to implement the actual trade execution
            # This would go through the Coinbase API
            return {"response": f"Trade intent detected: {intent_data['side']} {intent_data['amount']} {intent_data['symbol']}"}
            
        else:
            return {"response": "I'm not sure what you want to do. Try asking about prices, portfolio, market status, or trading."}
            
    except Exception as e:
        logger.error(f"Error processing request: {e}")
        return {"error": str(e)}
