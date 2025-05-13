import requests
from coinbase import jwt_generator
import os
import uuid
from dotenv import load_dotenv
from typing import Dict, Any
import asyncio
from datetime import datetime, timedelta
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

api_key = os.getenv("COINBASE_API_KEY")
api_secret = os.getenv("COINBASE_API_SECRET")

def place_market_order(product_id: str, side: str, size: float, strategy_params: Dict[str, Any] = None) -> Dict:
    try:
        request_method = "POST"
        request_path = "/api/v3/brokerage/orders"
        jwt_uri = jwt_generator.format_jwt_uri(request_method, request_path)
        jwt_token = jwt_generator.build_rest_jwt(jwt_uri, api_key, api_secret)
        headers = {
            "Authorization": f"Bearer {jwt_token}",
            "Content-Type": "application/json"
        }

        # Apply strategy parameters
        if strategy_params:
            if "position_size" in strategy_params:
                size = strategy_params["position_size"]
            elif "max_position_size" in strategy_params:
                size = min(size, strategy_params["max_position_size"])

        if side == "BUY":
            order_config = {"market_market_ioc": {"quote_size": size}}
        else:  # SELL
            order_config = {"market_market_ioc": {"base_size": size}}

        body = {
            "client_order_id": str(uuid.uuid4()),
            "product_id": product_id,
            "side": side,
            "order_configuration": order_config
        }

        logger.info(f"Placing market order: {body}")
        response = requests.post(
            "https://api.coinbase.com/api/v3/brokerage/orders",
            headers=headers,
            json=body
        )
        data = response.json()
        
        if response.status_code == 200 and data.get("success"):
            logger.info(f"Order placed successfully: {data}")
            return {"success": True, "order": data.get("order", data)}
        else:
            logger.error(f"Order failed: {data}")
            return {"success": False, "error": data.get("error", data)}
    except Exception as e:
        logger.error(f"Error placing order: {str(e)}")
        return {"success": False, "error": str(e)}

async def execute_dca_strategy(product_id: str, side: str, total_amount: float, strategy_params: Dict[str, Any]) -> Dict:
    """Execute Dollar-Cost Averaging strategy"""
    try:
        # Extract DCA parameters
        intervals = strategy_params.get("intervals", 5)
        interval_hours = strategy_params.get("interval_hours", 24)
        position_size = total_amount / intervals
        
        logger.info(f"Starting DCA strategy for {product_id}: {intervals} intervals, {interval_hours} hours each")
        
        results = []
        for i in range(intervals):
            logger.info(f"Executing DCA interval {i+1}/{intervals}")
            result = place_market_order(
                product_id,
                side,
                position_size,
                {"position_size": position_size}
            )
            results.append(result)
            
            if not result.get("success"):
                logger.error(f"DCA interval {i+1} failed: {result.get('error')}")
                return {
                    "success": False,
                    "error": f"DCA interval {i+1} failed: {result.get('error')}",
                    "completed_intervals": i,
                    "results": results
                }
            
            if i < intervals - 1:  # Don't wait after the last trade
                wait_time = interval_hours * 3600 / intervals
                logger.info(f"Waiting {wait_time} seconds before next interval")
                await asyncio.sleep(wait_time)
        
        logger.info("DCA strategy completed successfully")
        return {
            "success": True,
            "orders": results,
            "total_intervals": intervals,
            "completed_intervals": intervals
        }
    except Exception as e:
        logger.error(f"Error executing DCA strategy: {str(e)}")
        return {"success": False, "error": str(e)}

def process_trade(message: str, strategy: str = "conservative", strategy_params: Dict[str, Any] = None) -> Dict:
    """Process trade with strategy parameters"""
    try:
        # Extract trade parameters from message
        # This is handled by the LLM in frank.py now
        
        # Execute trade based on strategy
        if strategy == "dca" and strategy_params:
            # DCA strategy is handled asynchronously
            return {"status": "pending", "message": "DCA strategy initiated"}
        else:
            # Regular market order
            return {"status": "success", "message": "Trade executed"}
    except Exception as e:
        logger.error(f"Error processing trade: {str(e)}")
        return {"status": "error", "message": str(e)}