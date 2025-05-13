# frank_bot.py
import discord
import requests
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_BOT_TOKEN")
FASTAPI_URL = "http://localhost:8000/query"

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f"Frank is online as {client.user}")

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith("!ask"):
        prompt = message.content[5:].strip()
        await message.channel.send("Hmm...")

        try:
            response = requests.post(FASTAPI_URL, json={"prompt": prompt})
            data = response.json()
            await message.channel.send(data["response"][:2000])
        except Exception as e:
            await message.channel.send("Something went wrong.")

client.run(TOKEN)
