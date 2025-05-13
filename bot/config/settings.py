import os
from dotenv import load_dotenv

load_dotenv()

# Discord
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
FASTAPI_URL = "http://localhost:8000/query"

# API Keys
TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY")
COINBASE_API_KEY = os.getenv("COINBASE_API_KEY")
COINBASE_API_SECRET = os.getenv("COINBASE_API_SECRET")

# API URLs
COINBASE_API_BASE_URL = "https://api.coinbase.com"
COINBASE_API_V2_URL = f"{COINBASE_API_BASE_URL}/v2"
COINBASE_API_V3_URL = f"{COINBASE_API_BASE_URL}/api/v3"

# LLM Settings
LLM_MODEL = "meta-llama/Llama-3.3-70B-Instruct-Turbo-Free"
LLM_MAX_TOKENS = 200
LLM_TEMPERATURE = 0.7
LLM_TOP_P = 0.9 