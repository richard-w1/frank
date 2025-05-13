import subprocess
import sys
import os
import time
from threading import Thread
import signal
import psutil
import logging
from bot.frank import bot
from bot.config.settings import DISCORD_BOT_TOKEN

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_fastapi():
    """Run the FastAPI server"""
    try:
        logger.info("Starting FastAPI server...")
        subprocess.run([sys.executable, "-m", "uvicorn", "bot.backend:app", "--reload"], check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"FastAPI server error: {e}")
    except Exception as e:
        logger.error(f"Error running FastAPI server: {e}")

def run_discord_bot():
    """Run the Discord bot"""
    try:
        logger.info("Starting Discord bot...")
        bot.run(DISCORD_BOT_TOKEN)
    except Exception as e:
        logger.error(f"Error running Discord bot: {e}")

def cleanup():
    """Clean up processes on exit"""
    logger.info("Cleaning up processes...")
    current_process = psutil.Process()
    children = current_process.children(recursive=True)
    for child in children:
        try:
            child.terminate()
        except psutil.NoSuchProcess:
            pass

if __name__ == "__main__":
    # Register cleanup handler
    signal.signal(signal.SIGINT, lambda s, f: cleanup())
    signal.signal(signal.SIGTERM, lambda s, f: cleanup())
    
    try:
        # Start FastAPI server in a separate thread
        fastapi_thread = Thread(target=run_fastapi)
        fastapi_thread.daemon = True  # Thread will exit when main program exits
        fastapi_thread.start()

        # Give FastAPI server time to start
        logger.info("Waiting for FastAPI server to start...")
        time.sleep(5)

        # Run Discord bot in main thread
        run_discord_bot()
    except KeyboardInterrupt:
        logger.info("\nShutting down...")
        cleanup()
    except Exception as e:
        logger.error(f"Error: {e}")
        cleanup()
        sys.exit(1) 