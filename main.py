# main.py
import argparse
import asyncio
import logging
from monitor import monitor_servers, executor

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='monitor.log'
)
logger = logging.getLogger(__name__)

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--silent", action="store_true", help="Run in silent mode")
    args = parser.parse_args()

    try:
        await monitor_servers(silent=args.silent)
    except KeyboardInterrupt:
        logger.info("Shutting down monitor...")
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
    finally:
        executor.shutdown(wait=True)

if __name__ == "__main__":
    asyncio.run(main())