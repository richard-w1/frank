# frank_bot.py
import discord
import requests
import logging
from discord.ext import commands
from bot.config.settings import DISCORD_BOT_TOKEN, FASTAPI_URL

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    logger.info(f"Frank is online as {bot.user}")
    logger.info("------")
    logger.info("Available commands:")
    logger.info("!price <symbol> - Get current price of a cryptocurrency")
    logger.info("!portfolio - View your portfolio balance")
    logger.info("!market - Check current market status")
    logger.info("!trade <buy|sell> <amount> <symbol> - Execute a trade")
    logger.info("Or just chat naturally with me!")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    # Check if message is a command
    if message.content.startswith('!'):
        await bot.process_commands(message)
        return

    # Handle natural language if mentioned or in DM
    if bot.user.mentioned_in(message) or isinstance(message.channel, discord.DMChannel):
        # Check if it's a help request
        if message.content.lower() in ['help', 'commands', '?', 'what can you do', '!help', '!commands']:
            help_message = """
            
            **Frank's Available Commands:**
            
            **Trading Commands:**
            `!price <symbol>` - Get current price of a cryptocurrency (e.g., `!price BTC`)
            `!portfolio` - View your portfolio balance
            `!market` - Check current market status
            `!trade <amount> <symbol>` - Execute a trade (e.g., `!trade 0.1 BTC`)

            **Natural Language:**
            You can also chat with me naturally! Try:
            - "What's the price of Bitcoin?"
            - "Show me my portfolio"
            - "How's the market doing?"
            - "Buy 0.1 ETH"

            Need help? Just type `!commands` or mention me with your question!
            
            """
            await message.channel.send(help_message)
            return

        await message.channel.send("Thinking...")

        try:
            response = requests.post(FASTAPI_URL, json={"prompt": message.content})
            data = response.json()
            
            if "error" in data:
                await message.channel.send(f"❌ Error: {data['error']}")
            else:
                await message.channel.send(data["response"][:2000])
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            await message.channel.send("Something went wrong. 😞")

@bot.command(name="price")
async def price(ctx, symbol: str):
    """Get current price of a cryptocurrency"""
    try:
        response = requests.post(FASTAPI_URL, json={"prompt": f"what is the price of {symbol}"})
        data = response.json()
        await ctx.send(data["response"])
    except Exception as e:
        logger.error(f"Error in price command: {e}")
        await ctx.send(f"❌ Error: {str(e)}")

@bot.command(name="portfolio")
async def portfolio(ctx):
    """View your portfolio balance"""
    try:
        response = requests.post(FASTAPI_URL, json={"prompt": "show my portfolio"})
        data = response.json()
        await ctx.send(data["response"])
    except Exception as e:
        logger.error(f"Error in portfolio command: {e}")
        await ctx.send(f"❌ Error: {str(e)}")

@bot.command(name="market")
async def market(ctx):
    """Check current market status"""
    try:
        response = requests.post(FASTAPI_URL, json={"prompt": "what's the market status"})
        data = response.json()
        await ctx.send(data["response"])
    except Exception as e:
        logger.error(f"Error in market command: {e}")
        await ctx.send(f"❌ Error: {str(e)}")

@bot.command(name="trade")
async def trade(ctx, amount: float, symbol: str):
    """Execute a trade"""
    try:
        response = requests.post(FASTAPI_URL, json={"prompt": f"buy {amount} {symbol}"})
        data = response.json()
        await ctx.send(data["response"])
    except Exception as e:
        logger.error(f"Error in trade command: {e}")
        await ctx.send(f"❌ Error: {str(e)}")

@bot.command(name="commands")
async def show_commands(ctx):
    """Show available commands"""
    help_message = """
    
    **Frank's Available Commands:**
    
    **Trading Commands:**
    `!price <symbol>` - Get current price of a cryptocurrency (e.g., `!price BTC`)
    `!portfolio` - View your portfolio balance
    `!market` - Check current market status
    `!trade <amount> <symbol>` - Execute a trade (e.g., `!trade 0.1 BTC`)

    **Natural Language:**
    You can also chat with me naturally! Try:
    - "What's the price of Bitcoin?"
    - "Show me my portfolio"
    - "How's the market doing?"
    - "Buy 0.1 ETH"

    Need help? Just type `!commands` or mention me with your question!
    
    """
    await ctx.send(help_message)

if __name__ == "__main__":
    try:
        bot.run(DISCORD_BOT_TOKEN)
    except Exception as e:
        logger.error(f"Error starting Discord bot: {e}")
