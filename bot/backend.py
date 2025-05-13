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
import re
import uuid
from .services.coinbase import CoinbaseService
from .services.llm import LLMService
from .models.trade import TradeResponse, MarketStatus

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY")
COINBASE_API_KEY = os.getenv("COINBASE_API_KEY")
COINBASE_API_SECRET = os.getenv("COINBASE_API_SECRET")

app = FastAPI()
client = Together(api_key=TOGETHER_API_KEY)
llm_service = LLMService()

def get_coinbase_jwt(method: str, path: str) -> str:
    """Generate JWT for Coinbase API"""
    jwt_uri = jwt_generator.format_jwt_uri(method, path)
    return jwt_generator.build_rest_jwt(jwt_uri, COINBASE_API_KEY, COINBASE_API_SECRET)

def execute_trade(symbol: str, side: str, amount: float) -> Dict:
    """Execute a trade on Coinbase"""
    try:
        product_id = f"{symbol.upper()}-USD"
        request_method = "POST"
        request_path = "/api/v3/brokerage/orders"
        jwt_token = get_coinbase_jwt(request_method, request_path)
        
        headers = {
            "Authorization": f"Bearer {jwt_token}",
            "Content-Type": "application/json"
        }

        # Get current price to calculate USD amount
        current_price = get_crypto_price(symbol)
        if not current_price:
            return {
                "success": False,
                "message": f"❌ Could not get current price for {symbol}"
            }

        # Calculate USD amount and format to 2 decimal places (standard for USD)
        usd_amount = amount * current_price
        formatted_usd_amount = f"{usd_amount:.2f}"

        logger.info(f"Current price: ${current_price}, USD amount: ${formatted_usd_amount}")
        
        # Configure order based on side
        if side.upper() == "BUY":
            order_config = {"market_market_ioc": {"quote_size": formatted_usd_amount}}
        else:  # SELL
            # For sell orders, use the crypto amount with 8 decimal places
            formatted_crypto_amount = f"{amount:.8f}".rstrip('0').rstrip('.')
            order_config = {"market_market_ioc": {"base_size": formatted_crypto_amount}}

        body = {
            "client_order_id": str(uuid.uuid4()),
            "product_id": product_id,
            "side": side.upper(),
            "order_configuration": order_config
        }

        logger.info(f"Executing trade with body: {json.dumps(body, indent=2)}")
        response = requests.post(
            "https://api.coinbase.com/api/v3/brokerage/orders",
            headers=headers,
            json=body
        )
        
        logger.info(f"Response status: {response.status_code}")
        logger.info(f"Response headers: {dict(response.headers)}")
        
        try:
            response_data = response.json()
            logger.info(f"Response data: {json.dumps(response_data, indent=2)}")
        except json.JSONDecodeError:
            logger.error(f"Failed to parse response as JSON: {response.text}")
            response_data = {}
        
        if response.status_code == 200:
            if response_data.get("success"):
                order = response_data.get("order", {})
                success_response = order.get("success_response", {})
                order_config = order.get("order_configuration", {})
                market_ioc = order_config.get("market_market_ioc", {})
                
                return {
                    "success": True,
                    "message": f"✅ Trade executed successfully!\n"
                              f"Side: {success_response.get('side')}\n"
                              f"Product: {success_response.get('product_id')}\n"
                              f"Amount: {market_ioc.get('base_size') or market_ioc.get('quote_size')}\n"
                              f"Order ID: {success_response.get('order_id')}"
                }
            else:
                error_msg = response_data.get('error', 'Unknown error')
                error_details = response_data.get('error_details', '')
                message = response_data.get('message', '')
                preview_failure = response_data.get('preview_failure_reason', '')
                return {
                    "success": False,
                    "message": f"❌ Trade failed: {error_msg}\nDetails: {error_details}\nMessage: {message}\nPreview: {preview_failure}"
                }
        else:
            error_msg = response_data.get('message', response.text)
            error_details = response_data.get('error_details', '')
            return {
                "success": False,
                "message": f"❌ API Error ({response.status_code}):\nError: {error_msg}\nDetails: {error_details}"
            }
    except Exception as e:
        logger.error(f"Error executing trade: {str(e)}", exc_info=True)
        return {
            "success": False,
            "message": f"❌ Error: {str(e)}"
        }

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

def extract_json_from_text(text: str) -> Optional[Dict]:
    """Extract JSON from text, handling various formats"""
    try:
        # First try direct JSON parsing
        return json.loads(text)
    except json.JSONDecodeError:
        try:
            # Try to find JSON-like structure in the text
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass
        
        # If that fails, try to extract key information using regex
        intent_match = re.search(r'"intent"\s*:\s*"([^"]+)"', text)
        symbol_match = re.search(r'"symbol"\s*:\s*"([^"]+)"', text)
        amount_match = re.search(r'"amount"\s*:\s*(\d+\.?\d*)', text)
        side_match = re.search(r'"side"\s*:\s*"([^"]+)"', text)
        
        if intent_match:
            result = {
                "intent": intent_match.group(1),
                "symbol": symbol_match.group(1) if symbol_match else None,
                "amount": float(amount_match.group(1)) if amount_match else None,
                "side": side_match.group(1) if side_match else None
            }
            return result
    return None

@app.post("/query")
async def query(request: Request):
    data = await request.json()
    user_prompt = data.get("prompt", "")

    try:
        # Get intent from LLM
        trade_intent = llm_service.get_trade_intent(user_prompt)
        
        if not trade_intent.intent:
            return {"response": "I'm not sure what you want to do. Try asking about prices, portfolio, market status, or trading."}
        
        # Handle different intents
        if trade_intent.intent == "chat":
            # Return the chat response directly
            return {"response": trade_intent.response or "I'm here to help with crypto trading. What would you like to know?"}
            
        elif trade_intent.intent == "price":
            if not trade_intent.symbol:
                return {"response": "Please specify which cryptocurrency you want to check (e.g., BTC, ETH)"}
            price = CoinbaseService.get_crypto_price(trade_intent.symbol)
            if price:
                return {"response": f"Current price of {trade_intent.symbol}: ${price:,.2f}"}
            return {"response": f"Sorry, couldn't get the price for {trade_intent.symbol}"}
            
        elif trade_intent.intent == "portfolio":
            portfolio = CoinbaseService.get_portfolio_balance()
            if portfolio:
                portfolio_info = "**Your Portfolio:**\n"
                total_value = 0.0
                for account in portfolio.get("data", []):
                    balance = float(account.get("balance", {}).get("amount", 0))
                    currency = account.get("currency")
                    if balance > 0:
                        if currency != "USD":
                            price = CoinbaseService.get_crypto_price(currency)
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
            
        elif trade_intent.intent == "market":
            btc_price = CoinbaseService.get_crypto_price("BTC")
            eth_price = CoinbaseService.get_crypto_price("ETH")
            
            market_info = "**Current Market Status:**\n"
            
            if btc_price:
                market_info += f"BTC: ${btc_price:,.2f}\n"
            if eth_price:
                market_info += f"ETH: ${eth_price:,.2f}\n"
                
            return {"response": market_info}
            
        elif trade_intent.intent == "trade":
            if not all([trade_intent.symbol, trade_intent.amount, trade_intent.side]):
                return {"response": "Please specify the cryptocurrency, amount, and whether you want to buy or sell"}
            
            # Execute the trade
            trade_result = CoinbaseService.execute_trade(
                symbol=trade_intent.symbol,
                side=trade_intent.side,
                amount=float(trade_intent.amount)
            )
            
            return {"response": trade_result["message"]}
            
        else:
            return {"response": "I'm not sure what you want to do. Try asking about prices, portfolio, market status, or trading."}
            
    except Exception as e:
        logger.error(f"Error processing request: {e}")
        return {"error": str(e)}
