import time
import asyncio
from utils import (
    read_settings, read_servers, ping_check, port_check, http_check,
    keyword_check, format_timedelta, send_telegram_message, notify_error,
    ConfigError, Settings
)
from display import get_display
import datetime
import logging
from concurrent.futures import ThreadPoolExecutor

# Get logger
logger = logging.getLogger(__name__)

# Create executor as module-level variable
executor = ThreadPoolExecutor(max_workers=10)

# Shutdown event for graceful termination (will be created in event loop)
shutdown_event = None

# Declare dictionaries to store previous status, downtime start time and fail/recovery counts for each server
previous_status = {}
downtime_start = {}
fail_count = {}
recovery_count = {}

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

async def check_server(settings: Settings, description, type_, target, port=None, keyword=None, expect_keyword=None, failure_threshold=None, recovery_threshold=None, display=None):
    """Check a single server. Settings are passed in — never re-read per check."""
    try:
        if failure_threshold is None:
            msg = f"BUG: failure_threshold is None for {description}"
            logger.error(msg)
            if settings.telegram_enabled:
                await notify_error(msg, settings.chat_id, settings.bot_token)
            return

        # Use ThreadPoolExecutor for blocking I/O checks
        if type_ == 'ping':
            status, latency, error = await asyncio.get_event_loop().run_in_executor(
                executor, ping_check, target
            )
        elif type_ == 'port':
            status, latency, error = await asyncio.get_event_loop().run_in_executor(
                executor, port_check, target, port
            )
        elif type_ == 'http':
            status, latency, error = await asyncio.get_event_loop().run_in_executor(
                executor, http_check, target
            )
        elif type_ == 'keyword':
            if keyword is None or expect_keyword is None:
                msg = f"BUG: keyword check misconfigured for {description}"
                logger.error(msg)
                if settings.telegram_enabled:
                    await notify_error(msg, settings.chat_id, settings.bot_token)
                return
            status, latency, error = await asyncio.get_event_loop().run_in_executor(
                executor, keyword_check, target, keyword, expect_keyword
            )
        else:
            msg = f"BUG: unknown check type '{type_}' for {description}"
            logger.error(msg)
            if settings.telegram_enabled:
                await notify_error(msg, settings.chat_id, settings.bot_token)
            return

        if status == "Down":
            fail_count[description] = fail_count.get(description, 0) + 1
            recovery_count[description] = 0  # Reset recovery count on failure
            if previous_status.get(description) != "Down" and fail_count[description] >= failure_threshold:
                message = f"❌ {description} is down"
                if error is not None:
                    message += f". {error}"
                if settings.telegram_enabled:
                    await send_telegram_message(message, settings.chat_id, settings.bot_token)
                previous_status[description] = "Down"
                downtime_start[description] = datetime.datetime.now()
        else:
            fail_count[description] = 0  # Reset failure count on success
            was_down = previous_status.get(description) == "Down"
            if was_down:
                recovery_count[description] = recovery_count.get(description, 0) + 1
                if recovery_count[description] >= recovery_threshold:
                    previous_status[description] = "Up"
                    recovery_count[description] = 0
                    downtime = datetime.datetime.now() - downtime_start[description]
                    downtime_formatted = format_timedelta(downtime)
                    if settings.telegram_enabled:
                        await send_telegram_message(
                            f"✅ {description} is back up. Downtime: {downtime_formatted}",
                            settings.chat_id,
                            settings.bot_token
                        )
            else:
                previous_status[description] = "Up"

        # Update display
        if display:
            display.update_server(description, status, latency, error)

    except Exception as e:
        # LOUD failure — log AND print to stderr so systemd journal captures it
        error_msg = f"MONITOR ERROR checking {description}: {e}"
        logger.error(error_msg, exc_info=True)
        print(error_msg, flush=True)
        if display:
            display.update_server(description, "Error", None, str(e))

async def monitor_servers(silent=False):
    """Monitor servers with enhanced error handling and configuration validation"""
    global shutdown_event

    # Create shutdown event in the current event loop
    shutdown_event = asyncio.Event()

    # Validate all configuration at startup before entering the loop
    settings = read_settings()

    # Validate servers.yaml exists at startup
    servers = read_servers()

    # Log startup summary to journal (stdout) so operators can verify
    server_count = len(servers)
    logger.info(f"pymon started: monitoring {server_count} targets, check every {settings.check_interval}s, telegram={'on' if settings.telegram_enabled else 'off'}")
    print(f"pymon: monitoring {server_count} targets, interval={settings.check_interval}s, telegram={'on' if settings.telegram_enabled else 'off'}", flush=True)

    status_report_interval_seconds = settings.status_report_interval * 60
    last_status_report_time = time.time()

    # Initialize display
    display = get_display() if not silent else None

    first_run = True
    consecutive_cycle_errors = 0

    while not shutdown_event.is_set():
        try:
            # Re-read servers config to pick up changes
            try:
                servers = read_servers()
            except ConfigError as e:
                logger.error(f"Failed to reload servers.yaml: {e}")
                print(f"pymon: failed to reload servers.yaml: {e}", flush=True)
                # Use wait with timeout instead of sleep to respond to shutdown
                try:
                    await asyncio.wait_for(shutdown_event.wait(), timeout=settings.check_interval)
                    break  # Shutdown requested
                except asyncio.TimeoutError:
                    pass
                continue

            # Clear old results before new check cycle
            if display:
                display.clear_results()

            # Check servers in parallel
            tasks = []
            for server in servers:
                task = check_server(
                    settings,
                    server['description'],
                    server['type'],
                    server['target'],
                    server.get('port'),
                    server.get('keyword'),
                    server.get('expect_keyword'),
                    settings.failure_threshold,
                    settings.recovery_threshold,
                    display
                )
                tasks.append(task)

            await asyncio.gather(*tasks)
            consecutive_cycle_errors = 0  # Reset on successful cycle

            # Print results after all checks complete
            if display:
                display.clear()
                display.print_header()
                display.print_results()

            if first_run:
                first_run = False
                if settings.telegram_enabled:
                    report = generate_status_report()
                    await send_telegram_message(report, settings.chat_id, settings.bot_token)

            # Send status report at specified interval
            current_time = time.time()
            if current_time - last_status_report_time >= status_report_interval_seconds:
                if settings.telegram_enabled:
                    report = generate_status_report()
                    if not settings.report_only_on_down or "Down" in report:
                        await send_telegram_message(report, settings.chat_id, settings.bot_token)
                last_status_report_time = current_time

        except Exception as e:
            consecutive_cycle_errors += 1
            error_msg = f"pymon: monitoring cycle error #{consecutive_cycle_errors}: {e}"
            logger.error(error_msg, exc_info=True)
            print(error_msg, flush=True)

            # If we fail 10 cycles in a row, something is fundamentally broken
            if consecutive_cycle_errors >= 10:
                fatal_msg = f"pymon: FATAL — {consecutive_cycle_errors} consecutive cycle failures, last error: {e}"
                logger.critical(fatal_msg)
                print(fatal_msg, flush=True)
                if settings.telegram_enabled:
                    await send_telegram_message(f"🔥 {fatal_msg}", settings.chat_id, settings.bot_token)
                raise RuntimeError(fatal_msg)

        # Use wait with timeout instead of sleep to respond to shutdown quickly
        try:
            await asyncio.wait_for(shutdown_event.wait(), timeout=settings.check_interval)
            break  # Shutdown requested
        except asyncio.TimeoutError:
            pass  # Continue monitoring

    logger.info("Monitor loop exited gracefully")
    print("pymon: shutdown complete", flush=True)
