from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel
from app.trade import place_market_order, execute_dca_strategy
from typing import Optional, Dict, Any
import time
from functools import lru_cache

app = FastAPI()

# middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

RATE_LIMIT = 10
RATE_LIMIT_WINDOW = 60

@lru_cache(maxsize=100)
def get_rate_limit():
    return {}

class TradeRequest(BaseModel):
    intent: str
    side: str
    amount: float
    symbol: str
    strategy_params: Optional[Dict[str, Any]] = None

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.requests = {}

    async def dispatch(self, request, call_next):
        client_ip = request.client.host
        current_time = time.time()
        self.requests = {
            ip: timestamps
            for ip, timestamps in self.requests.items()
            if current_time - timestamps[-1] < RATE_LIMIT_WINDOW
        }

        if client_ip in self.requests:
            if len(self.requests[client_ip]) >= RATE_LIMIT:
                return HTTPException(
                    status_code=429,
                    detail="Rate limit exceeded. Please try again later."
                )
            self.requests[client_ip].append(current_time)
        else:
            self.requests[client_ip] = [current_time]
        return await call_next(request)

app.add_middleware(RateLimitMiddleware)

@app.post("/trade")
async def trade(req: TradeRequest):
    if req.intent != "trade":
        raise HTTPException(
            status_code=400,
            detail="Invalid trade intent"
        )
    
    if not req.side or not req.amount or not req.symbol:
        raise HTTPException(
            status_code=400,
            detail="Missing required trade parameters"
        )

    product_id = f"{req.symbol.upper()}-USD"
    
    # DCA strategy
    if req.strategy_params and req.strategy_params.get("intervals"):
        result = await execute_dca_strategy(
            product_id,
            req.side.upper(),
            req.amount,
            req.strategy_params
        )
    else:
        # market order
        result = place_market_order(
            product_id,
            req.side.upper(),
            req.amount,
            req.strategy_params
        )

    if result.get("success"):
        return {"success": True, "order": result.get("order")}
    else:
        return {"success": False, "error": result.get("error", "Unknown error")}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# NOTE: For any direct Coinbase API calls, use JWT authentication as shown in frank.py

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
