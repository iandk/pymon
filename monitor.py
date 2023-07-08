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


# Function to check a single server
def check_server(description, type_, target, port=None, keyword=None, expect_keyword=None, failure_threshold=None, silent=False):
    settings = read_settings()
    if settings is None:
        return

    bot_token, chat_id, _, _ = settings
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
        if previous_status.get(description) == "Down":
            downtime = datetime.datetime.now() - downtime_start[description]
            downtime_formatted = format_timedelta(downtime)
            asyncio.run(send_telegram_message(f"✅ {description} is back up. Downtime: {downtime_formatted}", chat_id, bot_token))
            previous_status[description] = "Up"

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

    bot_token, chat_id, failure_threshold, check_interval = settings
    if bot_token is None or chat_id is None or failure_threshold is None or check_interval is None:
        return

    check_interval = int(check_interval)
    first_run = True
    all_servers_up = True
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
                if first_run and previous_status.get(server['description']) == "Down":
                    all_servers_up = False
            if first_run:
                first_run = False
                if all_servers_up:
                    asyncio.run(send_telegram_message("✅ All servers are reachable", chat_id, bot_token))
        else:
            print("Configuration file not found: servers.json")

        time.sleep(check_interval)  # Wait for the specified sleep time before rechecking
