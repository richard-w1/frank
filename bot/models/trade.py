from typing import Dict, Optional
from dataclasses import dataclass

@dataclass
class TradeIntent:
    intent: str  # "trade|price|portfolio|market|chat"
    symbol: Optional[str]  # "BTC|ETH|etc"
    amount: Optional[float]
    side: Optional[str]  # "buy|sell"
    response: Optional[str] = None  # chat

@dataclass
class TradeResponse:
    success: bool
    message: str
    data: Optional[Dict] = None

@dataclass
class MarketStatus:
    btc: Dict[str, Optional[float]]
    eth: Dict[str, Optional[float]] 