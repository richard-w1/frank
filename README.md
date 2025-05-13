# Frank

Frank is a Discord cryptocurrency trading assistant that combines natural language processing with real-time trading capabilities. It can understand user intents and execute trades through Coinbase.

### Natural Language Processing
- Conversational interface using Meta Llama-3.3-70B.
- Understands natural language queries about crypto trading
- Processes complex trading intents and commands

### Trading Capabilities
- Real-time cryptocurrency price tracking
- Portfolio balance monitoring
- Market status analysis
- Automated trade execution (buy/sell)
- Support for major cryptocurrencies (BTC, ETH, etc.)

## Stack

FastAPI, discord.py, Together AI API, Coinbase API, langchain LLM integration

## You'll need

- Python 3.8 or higher
- Discord API
- Together AI API Key
- Coinbase API Key and Secret

## Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd frank
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the root directory with the following variables:
```env
DISCORD_BOT_TOKEN=your_discord_bot_token
TOGETHER_API_KEY=your_together_api_key
COINBASE_API_KEY=your_coinbase_api_key
COINBASE_API_SECRET=your_coinbase_api_secret
```

4. Start the FastAPI backend and Discord bot:
```bash
python run.py
```


## 💬 Available Commands

### Discord Commands
- `!price <symbol>` - Get current price of a cryptocurrency
- `!portfolio` - View your portfolio balance
- `!market` - Check current market status
- `!trade <amount> <symbol>` - Execute a trade
- `!commands` - Show all available commands

### Natural Language Examples
- "What's the price of Bitcoin?"
- "Show me my portfolio"
- "How's the market doing?"
- "Buy 0.1 ETH"
- "What's the current BTC price?"

## Security

- API keys are stored securely using environment variables
- JWT authentication for Coinbase API calls

## ⚠️ Disclaimer

AI can make mistakes. Cryptocurrency trading involves significant risk. Use at your own discretion.
Also don't give your CoinBase API key transfer permissions.