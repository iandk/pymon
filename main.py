# main.py
import argparse
import asyncio
import logging
import signal
import sys
from monitor import monitor_servers, executor, shutdown_event
from utils import ConfigError

# Configure logging - only log to file, not console (Rich handles display)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('monitor.log'),
    ]
)
logger = logging.getLogger(__name__)

# Track if we're in silent mode for output decisions
_silent_mode = False


def handle_shutdown(signum, frame):
    """Handle shutdown signals gracefully"""
    sig_name = signal.Signals(signum).name
    logger.info(f"Received {sig_name}, initiating shutdown...")
    if not _silent_mode:
        print(f"\nReceived {sig_name}, shutting down...")
    shutdown_event.set()


async def main():
    global _silent_mode

    parser = argparse.ArgumentParser(description="Server monitoring with Telegram notifications")
    parser.add_argument("--silent", action="store_true", help="Run in silent mode (no console output)")
    args = parser.parse_args()

    _silent_mode = args.silent

    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGTERM, handle_shutdown)
    signal.signal(signal.SIGHUP, handle_shutdown)

    try:
        await monitor_servers(silent=args.silent)
    except KeyboardInterrupt:
        logger.info("Received KeyboardInterrupt, shutting down...")
        if not _silent_mode:
            print("\nShutting down...")
    except ConfigError as e:
        logger.error(f"Configuration error: {e}")
        if not _silent_mode:
            print(f"\nConfiguration Error: {e}")
            print("\nMake sure you have:")
            print("  1. Copied .env.sample to .env and configured settings")
            print("  2. Set ENABLE_TELEGRAM=false if you don't want Telegram notifications")
            print("  3. If ENABLE_TELEGRAM=true, set BOT_TOKEN and CHAT_ID")
            print("  4. Copied servers-sample.yaml to servers.yaml")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        if not _silent_mode:
            print(f"Error: {str(e)}")
        sys.exit(1)
    finally:
        logger.info("Shutting down executor...")
        executor.shutdown(wait=True)
        logger.info("Shutdown complete")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        if not _silent_mode:
            print("\nBye!")