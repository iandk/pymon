import time
import os
import json
import asyncio
from utils import read_settings, ping_check, port_check, http_check, keyword_check, format_timedelta, send_telegram_message
import datetime

# Declare dictionaries to store previous status, downtime start time and fail_count for each server
previous_status = {}
downtime_start = {}
fail_count = {}

def generate_status_report():
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

# Function to check a single server
def check_server(description, type_, target, port=None, keyword=None, expect_keyword=None, failure_threshold=None, silent=False):
    settings = read_settings()
    if settings is None:
        return

    bot_token, chat_id, _, _, _, _ = settings
    if bot_token is None or chat_id is None:
        return

    if failure_threshold is None:
        print(f"Failure threshold not specified: {description}")
        return

    if type_ == 'ping':
        status, latency, error = ping_check(target)
        latency_suffix = " ms"
    elif type_ == 'port':
        status, latency, error = port_check(target, port)
        latency_suffix = " ms"
    elif type_ == 'http':
        status, latency, error = http_check(target)
        latency_suffix = ""
    elif type_ == 'keyword':
        if keyword is None or expect_keyword is None:
            print(f"Invalid configuration for keyword check: {description}")
            return
        status, latency, error = keyword_check(target, keyword, expect_keyword)
        latency_suffix = ""
    else:
        print(f"Invalid type or type not specified: {description}")
        return

    if status == "Down":
        fail_count[description] = fail_count.get(description, 0) + 1
        if previous_status.get(description) != "Down" and fail_count[description] >= failure_threshold:
            message = f"❌ {description} is down"
            if error is not None:
                message += f". {error}"
            asyncio.run(send_telegram_message(message, chat_id, bot_token))
            previous_status[description] = "Down"
            downtime_start[description] = datetime.datetime.now()
    else:
        fail_count[description] = 0  # Reset failure count on success
        was_down = previous_status.get(description) == "Down"
        previous_status[description] = "Up"  # Store the status of the server
        if was_down:
            downtime = datetime.datetime.now() - downtime_start[description]
            downtime_formatted = format_timedelta(downtime)
            asyncio.run(send_telegram_message(f"✅ {description} is back up. Downtime: {downtime_formatted}", chat_id, bot_token))

    if not silent:
        if status == "Up":
            print(f"{description: <30} \033[0;32m{status}\033[0m ({latency}{latency_suffix})")  # Print in green if Up
        else:
            reason = f" {error}" if error is not None else ""
            print(f"{description: <30} \033[0;31m{status}\033[0m{reason}")  # Print in red if Down

# Function to monitor servers continuously
def monitor_servers(silent=False):
    settings = read_settings()
    if settings is None:
        return

    bot_token, chat_id, failure_threshold, check_interval_seconds, status_report_interval_minutes, report_only_if_down = settings
    if bot_token is None or chat_id is None or failure_threshold is None or check_interval_seconds is None:
        return

    check_interval_seconds = int(check_interval_seconds)
    status_report_interval_seconds = int(status_report_interval_minutes) * 60
    last_status_report_time = time.time()

    first_run = True
    while True:
        if not silent:
            print("\033c", end="")  # Clear terminal output
        if not silent:
            print("\033[0;36mMonitoring servers...\033[0m")
        try:
            if os.path.exists("servers.json"):
                with open("servers.json") as json_file:
                    servers = json.load(json_file).get('servers', [])
                for server in servers:
                    check_server(server['description'], server['type'], server['target'], server.get('port'), server.get('keyword'), server.get('expect_keyword'), failure_threshold, silent)

                if first_run:
                    first_run = False
                    report = generate_status_report()
                    asyncio.run(send_telegram_message(report, chat_id, bot_token))
            else:
                print("Configuration file not found: servers.json")
        except json.JSONDecodeError:
            error_message = "Error in servers.json: Invalid JSON syntax"
            print(error_message)
            asyncio.run(send_telegram_message(error_message, chat_id, bot_token))
            break

        # Send status report at specified interval
        current_time = time.time()
        if current_time - last_status_report_time >= status_report_interval_seconds:
            report = generate_status_report()
            if not report_only_if_down or "Down" in report:
                asyncio.run(send_telegram_message(report, chat_id, bot_token))
            last_status_report_time = current_time

        time.sleep(check_interval_seconds)  # Wait for the specified sleep time before rechecking
    settings = read_settings()
    if settings is None:
        return

    bot_token, chat_id, failure_threshold, check_interval_seconds, status_report_interval_minutes, report_only_if_down = settings
    if bot_token is None or chat_id is None or failure_threshold is None or check_interval_seconds is None:
        return

    check_interval_seconds = int(check_interval_seconds)
    status_report_interval_seconds = int(status_report_interval_minutes) * 60
    last_status_report_time = time.time()

    first_run = True
    while True:
        if not silent:
            print("\033c", end="")  # Clear terminal output
        if not silent:
            print("\033[0;36mMonitoring servers...\033[0m")
        if os.path.exists("servers.json"):
            with open("servers.json") as json_file:
                servers = json.load(json_file).get('servers', [])
            for server in servers:
                check_server(server['description'], server['type'], server['target'], server.get('port'), server.get('keyword'), server.get('expect_keyword'), failure_threshold, silent)
                
            if first_run:
                first_run = False
                report = generate_status_report()
                asyncio.run(send_telegram_message(report, chat_id, bot_token))
        else:
            print("Configuration file not found: servers.json")

        # Send status report at specified interval
        current_time = time.time()
        if current_time - last_status_report_time >= status_report_interval_seconds:
            report = generate_status_report()
            if not report_only_if_down or "Down" in report:
                asyncio.run(send_telegram_message(report, chat_id, bot_token))
            last_status_report_time = current_time

        time.sleep(check_interval_seconds)  # Wait for the specified sleep time before rechecking

if __name__ == "__main__":
    monitor_servers()
