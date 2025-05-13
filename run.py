import subprocess
import sys
import os
import time
from threading import Thread
import signal
import psutil
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_fastapi():
    """Run the FastAPI server"""
    logger.info("Starting FastAPI server...")
    try:
        subprocess.run(
            [sys.executable, "-m", "uvicorn", "bot.backend:app", "--host", "0.0.0.0", "--port", "8000", "--reload"],
            check=True
        )
    except subprocess.CalledProcessError as e:
        logger.error(f"Error starting FastAPI server: {e}")
        sys.exit(1)

def run_discord_bot():
    """Run the Discord bot"""
    logger.info("Starting Discord bot...")
    try:
        subprocess.run([sys.executable, "bot/frank.py"], check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"Error starting Discord bot: {e}")
        sys.exit(1)

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
        api_thread = Thread(target=run_fastapi)
        api_thread.daemon = True  # Thread will exit when main program exits
        api_thread.start()

        # Give the server a moment to start
        logger.info("Waiting for server to start...")
        time.sleep(5)  # Increased wait time to ensure server is ready

        # Start the Discord bot
        run_discord_bot()
    except KeyboardInterrupt:
        logger.info("\nShutting down...")
        cleanup()
    except Exception as e:
        logger.error(f"Error: {e}")
        cleanup()
        sys.exit(1) 