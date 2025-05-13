from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel
import httpx
import os
import time
import hmac
import hashlib
from dotenv import load_dotenv
from coinbase import jwt_generator
import logging
import json

# logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

load_dotenv()

COINBASE_REDIRECT_URI = os.getenv("COINBASE_REDIRECT_URI", "http://localhost:8000/auth/callback")
COINBASE_API_KEY = os.getenv("COINBASE_API_KEY")
COINBASE_API_SECRET = os.getenv("COINBASE_API_SECRET")

class CoinbaseAuth:
    def __init__(self):
        # CDP API configuration
        self.api_key = os.getenv("COINBASE_API_KEY")
        self.api_secret = os.getenv("COINBASE_API_SECRET")
        
        # Debug logging
        logger.debug(f"API Key format: {self.api_key}")
        logger.debug(f"API Secret starts with: {self.api_secret[:50] if self.api_secret else 'None'}")
        
        if not self.api_key or not self.api_secret:
            logger.error("Missing API credentials")
            return
            
        if not self.api_key.startswith("organizations/"):
            logger.error(f"Invalid API key format: {self.api_key}")
            
        if not self.api_secret.startswith("-----BEGIN EC PRIVATE KEY-----"):
            logger.error("Invalid API secret format")
            
        self.user_tokens = {}
        
    def get_jwt_headers(self, method: str, path: str) -> dict:
        try:
            logger.debug(f"Generating JWT for {method} {path}")
            
            # JWT URI
            jwt_uri = jwt_generator.format_jwt_uri(method, path)
            logger.debug(f"JWT URI: {jwt_uri}")
            
            # clean API 
            clean_secret = self.api_secret.strip()
            if not clean_secret.endswith("\n"):
                clean_secret += "\n"
            
            # generate
            try:
                jwt_token = jwt_generator.build_rest_jwt(jwt_uri, self.api_key, clean_secret)
                logger.debug("JWT generated successfully")
            except Exception as jwt_error:
                logger.error(f"JWT generation failed: {str(jwt_error)}")
                raise HTTPException(
                    status_code=401,
                    detail=f"JWT generation failed: {str(jwt_error)}"
                )
            
            return {
                'Authorization': f'Bearer {jwt_token}',
                'Content-Type': 'application/json'
            }
        except Exception as e:
            logger.error(f"Failed to generate JWT: {str(e)}")
            raise HTTPException(status_code=401, detail=f"Failed to generate JWT: {str(e)}")
        
    async def verify_api_key(self) -> bool:
        try:
            logger.debug("Verifying API key")
            headers = self.get_jwt_headers('GET', '/api/v3/brokerage/accounts')
            
            async with httpx.AsyncClient() as client:
                try:
                    response = await client.get(
                        "https://api.coinbase.com/api/v3/brokerage/accounts",
                        headers=headers,
                        timeout=10.0
                    )
                    logger.debug(f"API response status: {response.status_code}")
                    logger.debug(f"API response headers: {dict(response.headers)}")
                    
                    if response.status_code != 200:
                        try:
                            error_data = response.json()
                            logger.error(f"API error response: {json.dumps(error_data, indent=2)}")
                        except:
                            logger.error(f"API error text: {response.text}")
                        return False
                        
                    return True
                except httpx.TimeoutException:
                    logger.error("API request timed out")
                    return False
                except Exception as e:
                    logger.error(f"API request failed: {str(e)}")
                    return False
        except Exception as e:
            logger.error(f"API verification failed: {str(e)}")
            return False

    async def get_authorization_url(self, state: str) -> str:
        params = {
            "response_type": "code",
            "client_id": COINBASE_CLIENT_ID,
            "redirect_uri": COINBASE_REDIRECT_URI,
            "scope": "wallet:accounts:read,wallet:transactions:read,wallet:transactions:send",
            "state": state
        }
        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        return f"https://www.coinbase.com/oauth/authorize?{query_string}"

    async def get_access_token(self, code: str) -> dict:
        """Exchange authorization code for access token"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.coinbase.com/oauth/token",
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "client_id": COINBASE_CLIENT_ID,
                    "client_secret": COINBASE_CLIENT_SECRET,
                    "redirect_uri": COINBASE_REDIRECT_URI
                }
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=400,
                    detail="Failed to get access token"
                )
            
            return response.json()

    async def refresh_token(self, refresh_token: str) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.coinbase.com/oauth/token",
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                    "client_id": COINBASE_CLIENT_ID,
                    "client_secret": COINBASE_CLIENT_SECRET
                }
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=400,
                    detail="Failed to refresh token"
                )
            
            return response.json()

    def store_user_tokens(self, user_id: str, tokens: dict):
        self.user_tokens[user_id] = tokens

    def get_user_tokens(self, user_id: str) -> dict:
        return self.user_tokens.get(user_id)

auth_handler = CoinbaseAuth()

app = FastAPI()

class AuthResponse(BaseModel):
    authorization_url: str

@app.get("/auth/start")
async def start_auth():
    """Start OAuth2 flow"""
    state = "random_state_string"  # In production, generate and validate state
    auth_url = await auth_handler.get_authorization_url(state)
    return AuthResponse(authorization_url=auth_url)

@app.get("/auth/callback")
async def auth_callback(code: str, state: str):
    """Handle OAuth2 callback"""
    try:
        tokens = await auth_handler.get_access_token(code)
        # In production, associate tokens with user ID from your database
        user_id = "user123"  # Replace with actual user ID
        auth_handler.store_user_tokens(user_id, tokens)
        return {"status": "success", "message": "Successfully authenticated with Coinbase"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "version": "cdp-jwt"}

@app.get("/auth/verify")
async def verify_auth():
    logger.debug("Verifying authentication (CDP API key)")
    if not COINBASE_API_KEY or not COINBASE_API_SECRET:
        logger.error("Missing COINBASE_API_KEY or COINBASE_API_SECRET")
        return {
            "method": "none",
            "status": "not_configured",
            "error": "Missing COINBASE_API_KEY or COINBASE_API_SECRET"
        }
    try:
        # Generate JWT for /v2/accounts
        jwt_uri = jwt_generator.format_jwt_uri("GET", "/v2/accounts")
        jwt_token = jwt_generator.build_rest_jwt(jwt_uri, COINBASE_API_KEY, COINBASE_API_SECRET)
        headers = {"Authorization": f"Bearer {jwt_token}"}
        async with httpx.AsyncClient() as client:
            response = await client.get("https://api.coinbase.com/v2/accounts", headers=headers, timeout=10.0)
            logger.debug(f"API response status: {response.status_code}")
            if response.status_code == 200:
                return {
                    "method": "cdp_api",
                    "status": "valid"
                }
            else:
                return {
                    "method": "cdp_api",
                    "status": "invalid",
                    "error": response.text
                }
    except Exception as e:
        logger.error(f"API verification failed: {str(e)}")
        return {
            "method": "cdp_api",
            "status": "invalid",
            "error": str(e)
        }

# Dependency for protected routes
async def get_current_user(authorization: str = Header(None)):
    """Validate and return current user"""
    if not authorization:
        raise HTTPException(status_code=401, detail="No authorization header")
    
    try:
        # In production, validate the JWT token
        return {"user_id": "user123"}
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e)) 