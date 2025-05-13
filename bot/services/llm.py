import logging
import json
import re
from together import Together
from bot.config.settings import (
    TOGETHER_API_KEY,
    LLM_MODEL,
    LLM_MAX_TOKENS,
    LLM_TEMPERATURE,
    LLM_TOP_P
)
from bot.models.trade import TradeIntent

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self):
        self.client = Together(api_key=TOGETHER_API_KEY)

    def get_trade_intent(self, user_prompt: str) -> TradeIntent:
        """Get trading intent from user prompt using LLM"""
        try:
            response = self.client.chat.completions.create(
                model=LLM_MODEL,
                messages=[{
                    "role": "user", 
                    "content": f"""You are a crypto trading assistant named Frank. Analyze this request and respond with a JSON object.
                    The JSON must have these exact fields:
                    {{
                        "intent": "trade|price|portfolio|market|chat",
                        "symbol": "BTC|ETH|etc" or null,
                        "amount": number or null,
                        "side": "buy|sell" or null,
                        "response": "your response to the user" or null
                    }}

                    Examples:
                    - "what's the price of BTC?" -> {{"intent": "price", "symbol": "BTC", "amount": null, "side": null, "response": null}}
                    - "show my portfolio" -> {{"intent": "portfolio", "symbol": null, "amount": null, "side": null, "response": null}}
                    - "buy 0.1 BTC" -> {{"intent": "trade", "symbol": "BTC", "amount": 0.1, "side": "buy", "response": null}}
                    - "hi" -> {{"intent": "chat", "symbol": null, "amount": null, "side": null, "response": "Hello! I'm Frank, your crypto trading assistant. How can I help you today?"}}
                    - "how are you?" -> {{"intent": "chat", "symbol": null, "amount": null, "side": null, "response": "I'm doing great! Ready to help you with any crypto trading questions or tasks."}}

                    For general chat, use the "chat" intent and provide a friendly, helpful response in the "response" field.
                    For trading-related queries, use the appropriate intent and leave "response" as null.

                    Request: {user_prompt}"""
                }],
                max_tokens=LLM_MAX_TOKENS,
                temperature=LLM_TEMPERATURE,
                top_p=LLM_TOP_P
            )
            
            response_text = response.choices[0].message.content
            logger.info(f"LLM Response: {response_text}")
            
            try:
                # First try direct JSON parsing
                data = json.loads(response_text)
            except json.JSONDecodeError:
                try:
                    # Try to find JSON-like structure in the text
                    json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                    if json_match:
                        data = json.loads(json_match.group())
                except:
                    # If that fails, try to extract key information using regex
                    intent_match = re.search(r'"intent"\s*:\s*"([^"]+)"', response_text)
                    symbol_match = re.search(r'"symbol"\s*:\s*"([^"]+)"', response_text)
                    amount_match = re.search(r'"amount"\s*:\s*(\d+\.?\d*)', response_text)
                    side_match = re.search(r'"side"\s*:\s*"([^"]+)"', response_text)
                    response_match = re.search(r'"response"\s*:\s*"([^"]+)"', response_text)
                    
                    data = {
                        "intent": intent_match.group(1) if intent_match else None,
                        "symbol": symbol_match.group(1) if symbol_match else None,
                        "amount": float(amount_match.group(1)) if amount_match else None,
                        "side": side_match.group(1) if side_match else None,
                        "response": response_match.group(1) if response_match else None
                    }
            
            return TradeIntent(
                intent=data.get("intent"),
                symbol=data.get("symbol"),
                amount=data.get("amount"),
                side=data.get("side"),
                response=data.get("response")
            )
            
        except Exception as e:
            logger.error(f"Error getting trade intent: {e}")
            return TradeIntent(intent=None, symbol=None, amount=None, side=None, response=None) 