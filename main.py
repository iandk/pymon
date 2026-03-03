# main.py
import argparse
import asyncio
import logging
import signal
import sys
import monitor
from monitor import monitor_servers, executor
from utils import ConfigError

# Configure logging — write to BOTH file and stderr.
# stderr is captured by systemd journal, so errors are always visible
# in both `journalctl -u pymon` and `monitor.log`.
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/pymon.log'),
        logging.StreamHandler(sys.stderr),
    ]
)
logger = logging.getLogger(__name__)

# Track if we're in silent mode for output decisions
_silent_mode = False


def handle_shutdown(sig_name):
    """Handle shutdown signals gracefully"""
    logger.info(f"Received {sig_name}, initiating shutdown...")
    # shutdown_event is created inside monitor_servers(). Access it via
    # the module to get the live reference, not the stale import-time binding.
    if monitor.shutdown_event is not None:
        monitor.shutdown_event.set()
    else:
        logger.warning(f"Received {sig_name} before monitor was ready, exiting immediately")
        sys.exit(0)


async def main():
    global _silent_mode

    parser = argparse.ArgumentParser(description="Server monitoring with Telegram notifications")
    parser.add_argument("--silent", action="store_true", help="Run in silent mode (no console output)")
    args = parser.parse_args()

    _silent_mode = args.silent

    # Register signal handlers via the event loop for safe asyncio integration
    loop = asyncio.get_running_loop()
    loop.add_signal_handler(signal.SIGTERM, handle_shutdown, "SIGTERM")
    loop.add_signal_handler(signal.SIGHUP, handle_shutdown, "SIGHUP")

    try:
        await monitor_servers(silent=args.silent)
    except KeyboardInterrupt:
        logger.info("Received KeyboardInterrupt, shutting down...")
    except ConfigError as e:
        # Always print config errors to stderr (visible in journal)
        logger.error(f"Configuration error: {e}")
        print(f"\nConfiguration Error: {e}", file=sys.stderr, flush=True)
        print("\nMake sure you have:", file=sys.stderr)
        print("  1. Copied .env.sample to .env and configured settings", file=sys.stderr)
        print("  2. Set ENABLE_TELEGRAM=false if you don't want Telegram notifications", file=sys.stderr)
        print("  3. If ENABLE_TELEGRAM=true, set BOT_TOKEN and CHAT_ID", file=sys.stderr)
        print("  4. Copied servers-sample.yaml to servers.yaml", file=sys.stderr, flush=True)
        sys.exit(1)
    except Exception as e:
        # Always print fatal errors to stderr (visible in journal)
        logger.critical(f"Fatal error: {e}", exc_info=True)
        print(f"pymon FATAL: {e}", file=sys.stderr, flush=True)
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
