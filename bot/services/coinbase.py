import requests
import logging
import json
import uuid
from typing import Dict, Optional
from coinbase import jwt_generator
from bot.config.settings import (
    COINBASE_API_KEY,
    COINBASE_API_SECRET,
    COINBASE_API_V2_URL,
    COINBASE_API_V3_URL
)

logger = logging.getLogger(__name__)

class CoinbaseService:
    @staticmethod
    def get_jwt(method: str, path: str) -> str:
        """Generate JWT for Coinbase API"""
        jwt_uri = jwt_generator.format_jwt_uri(method, path)
        return jwt_generator.build_rest_jwt(jwt_uri, COINBASE_API_KEY, COINBASE_API_SECRET)

    @staticmethod
    def get_crypto_price(symbol: str) -> Optional[float]:
        """Get current price of a cryptocurrency"""
        try:
            response = requests.get(f"{COINBASE_API_V2_URL}/prices/{symbol}-USD/spot")
            if response.status_code == 200:
                return float(response.json()["data"]["amount"])
            return None
        except Exception as e:
            logger.error(f"Error getting price: {e}")
            return None

    @staticmethod
    def get_portfolio_balance() -> Optional[Dict]:
        """Get user's portfolio balance"""
        try:
            jwt_token = CoinbaseService.get_jwt("GET", "/v2/accounts")
            headers = {"Authorization": f"Bearer {jwt_token}"}
            response = requests.get(f"{COINBASE_API_V2_URL}/accounts", headers=headers)
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            logger.error(f"Error getting portfolio: {e}")
            return None

    @staticmethod
    def execute_trade(symbol: str, side: str, amount: float) -> Dict:
        """Execute a trade on Coinbase"""
        try:
            product_id = f"{symbol.upper()}-USD"
            request_method = "POST"
            request_path = "/api/v3/brokerage/orders"
            jwt_token = CoinbaseService.get_jwt(request_method, request_path)
            
            headers = {
                "Authorization": f"Bearer {jwt_token}",
                "Content-Type": "application/json"
            }

            # Get current price to calculate USD amount
            current_price = CoinbaseService.get_crypto_price(symbol)
            if not current_price:
                return {
                    "success": False,
                    "message": f"❌ Could not get current price for {symbol}"
                }

            # Calculate USD amount and format to 2 decimal places
            usd_amount = amount * current_price
            formatted_usd_amount = f"{usd_amount:.2f}"
            
            logger.info(f"Current price: ${current_price}, USD amount: ${formatted_usd_amount}")
            
            # Configure order based on side
            if side.upper() == "BUY":
                order_config = {"market_market_ioc": {"quote_size": formatted_usd_amount}}
            else:  # SELL
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
                f"{COINBASE_API_V3_URL}/brokerage/orders",
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