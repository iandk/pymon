import time
import asyncio
from utils import (
    read_settings, read_servers, ping_check, port_check, http_check, 
    keyword_check, format_timedelta, send_telegram_message, notify_error,
    ConfigError
)
import datetime
import logging
from concurrent.futures import ThreadPoolExecutor

# Get logger
logger = logging.getLogger(__name__)

# Create executor as module-level variable
executor = ThreadPoolExecutor(max_workers=10)

# Declare dictionaries to store previous status, downtime start time and fail_count for each server
previous_status = {}
downtime_start = {}
fail_count = {}

def generate_status_report():
    """Generate a status report of all servers"""
    down_servers = [server for server, status in previous_status.items() if status == "Down"]
    up_servers = [server for server, status in previous_status.items() if status == "Up"]

    if down_servers:
        report = "🔴 Status Report - Servers Down:\n"
        for server in down_servers:
            report += f"- {server}\n"
    else:
        report = "✅ Status Report - All Servers Up\n"

    if up_servers:
        report += "\nServers Up:\n"
        for server in up_servers:
            report += f"- {server}\n"

    return report

async def check_server(description, type_, target, port=None, keyword=None, expect_keyword=None, failure_threshold=None, silent=False):
    """Check a single server with better error handling and retry logic"""
    try:
        settings = read_settings()
        if settings is None:
            return

        bot_token, chat_id, _, _, _, _ = settings
        if bot_token is None or chat_id is None:
            return

        if failure_threshold is None:
            await notify_error(f"Failure threshold not specified: {description}", chat_id, bot_token)
            return

        # Use ThreadPoolExecutor for CPU-bound checks
        try:
            if type_ == 'ping':
                status, latency, error = await asyncio.get_event_loop().run_in_executor(
                    executor, ping_check, target
                )
                latency_suffix = " ms"
            elif type_ == 'port':
                status, latency, error = await asyncio.get_event_loop().run_in_executor(
                    executor, port_check, target, port
                )
                latency_suffix = " ms"
            elif type_ == 'http':
                status, latency, error = await asyncio.get_event_loop().run_in_executor(
                    executor, http_check, target
                )
                latency_suffix = ""
            elif type_ == 'keyword':
                if keyword is None or expect_keyword is None:
                    await notify_error(f"Invalid configuration for keyword check: {description}", chat_id, bot_token)
                    return
                status, latency, error = await asyncio.get_event_loop().run_in_executor(
                    executor, keyword_check, target, keyword, expect_keyword
                )
                latency_suffix = ""
            else:
                await notify_error(f"Invalid type or type not specified: {description}", chat_id, bot_token)
                return

            if status == "Down":
                fail_count[description] = fail_count.get(description, 0) + 1
                if previous_status.get(description) != "Down" and fail_count[description] >= failure_threshold:
                    message = f"❌ {description} is down"
                    if error is not None:
                        message += f". {error}"
                    await send_telegram_message(message, chat_id, bot_token)
                    previous_status[description] = "Down"
                    downtime_start[description] = datetime.datetime.now()
            else:
                fail_count[description] = 0  # Reset failure count on success
                was_down = previous_status.get(description) == "Down"
                previous_status[description] = "Up"  # Store the status of the server
                if was_down:
                    downtime = datetime.datetime.now() - downtime_start[description]
                    downtime_formatted = format_timedelta(downtime)
                    await send_telegram_message(
                        f"✅ {description} is back up. Downtime: {downtime_formatted}",
                        chat_id,
                        bot_token
                    )

            if not silent:
                if status == "Up":
                    print(f"{description: <30} \033[0;32m{status}\033[0m ({latency}{latency_suffix})")
                else:
                    reason = f" {error}" if error is not None else ""
                    print(f"{description: <30} \033[0;31m{status}\033[0m{reason}")

        except Exception as e:
            error_msg = f"Error checking server {description}: {str(e)}"
            await notify_error(error_msg, chat_id, bot_token)
            logger.error(error_msg)

    except ConfigError as e:
        logger.error(f"Configuration error while checking {description}: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error while checking {description}: {str(e)}")

async def monitor_servers(silent=False):
    """Monitor servers with enhanced error handling and configuration validation"""
    settings = None
    
    try:
        # Try to read settings first
        settings = read_settings()
        if settings is None:
            return

        bot_token, chat_id, failure_threshold, check_interval_seconds, status_report_interval_minutes, report_only_if_down = settings
        if None in (bot_token, chat_id, failure_threshold, check_interval_seconds):
            await notify_error("Invalid settings configuration", chat_id, bot_token)
            return

        check_interval_seconds = int(check_interval_seconds)
        status_report_interval_seconds = int(status_report_interval_minutes) * 60
        last_status_report_time = time.time()

        first_run = True
        while True:
            try:
                if not silent:
                    print("\033c", end="")
                    print("\033[0;36mMonitoring servers...\033[0m")

                # Read and validate servers configuration
                try:
                    servers = read_servers()
                    
                    # Check servers in parallel
                    tasks = []
                    for server in servers:
                        task = check_server(
                            server['description'],
                            server['type'],
                            server['target'],
                            server.get('port'),
                            server.get('keyword'),
                            server.get('expect_keyword'),
                            failure_threshold,
                            silent
                        )
                        tasks.append(task)
                    
                    await asyncio.gather(*tasks)

                    if first_run:
                        first_run = False
                        report = generate_status_report()
                        await send_telegram_message(report, chat_id, bot_token)

                    # Send status report at specified interval
                    current_time = time.time()
                    if current_time - last_status_report_time >= status_report_interval_seconds:
                        report = generate_status_report()
                        if not report_only_if_down or "Down" in report:
                            await send_telegram_message(report, chat_id, bot_token)
                        last_status_report_time = current_time

                except ConfigError as e:
                    error_msg = f"Configuration error: {str(e)}"
                    await notify_error(error_msg, chat_id, bot_token)
                    logger.error(error_msg)
                    # Don't break here, allow retrying on next iteration
                    await asyncio.sleep(check_interval_seconds)
                    continue

            except Exception as e:
                error_msg = f"Monitoring error: {str(e)}"
                await notify_error(error_msg, chat_id, bot_token)
                logger.error(error_msg)
            
            await asyncio.sleep(check_interval_seconds)

    except ConfigError as e:
        # Handle configuration errors with both logging and notification
        error_msg = f"Fatal configuration error: {str(e)}"
        if settings and all(settings[:2]):  # If we have valid bot_token and chat_id
            await notify_error(error_msg, settings[1], settings[0])
        else:
            logger.error(error_msg)
        raise  # Re-raise to stop the monitor

    except Exception as e:
        # Handle unexpected errors
        error_msg = f"Fatal error in monitor: {str(e)}"
        if settings and all(settings[:2]):
            await notify_error(error_msg, settings[1], settings[0])
        else:
            logger.error(error_msg)
        raise