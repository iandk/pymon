import os
import subprocess
import requests
import json
import certifi
from requests.exceptions import SSLError
from telegram import Bot

# Function to read bot_token, chat_id, and threshold from settings file
def read_settings():
    if os.path.exists("settings.json"):
        try:
            with open("settings.json") as json_file:
                settings = json.load(json_file)
                return (
                    settings.get("bot_token"),
                    settings.get("chat_id"),
                    settings.get("failure_threshold"),
                    settings.get("check_interval_seconds"),
                    settings.get("status_report_interval_minutes"),
                    settings.get("report_only_on_down"),
                )
        except json.JSONDecodeError:
            print("Error in settings.json: Invalid JSON syntax. Please check your configuration.")
            return None
    else:
        print("Configuration file not found: settings.json")
        return None


# Function to send a message via Telegram
async def send_telegram_message(message, chat_id, bot_token):
    try:
        bot = Bot(token=bot_token)
        await bot.send_message(chat_id=chat_id, text=message)
    except Exception as e:
        print(f"Failed to send Telegram message: {e}")


def format_timedelta(delta):
    days = delta.days
    hours, remainder = divmod(delta.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    if days > 0:
        return f"{days}d {hours}h"
    elif hours > 0:
        return f"{hours}h {minutes}m"
    elif minutes > 0:
        return f"{minutes}m {seconds}s"
    else:
        return f"{seconds}s"


# Function to perform a ping check
def ping_check(target):
    try:
        latency = subprocess.check_output(['ping', '-c', '1', target]).decode().split('/')[-3].split('=')[-1]
        return ("Up", latency, None)
    except Exception as e:
        return ("Down", None, None)


# Function to perform a port check
def port_check(target, port):
    try:
        subprocess.check_call(['nc', '-z', '-w', '5', target, str(port)], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        status, latency, _ = ping_check(target)  # Ignore the error from ping_check
        return ("Up", latency, None)
    except Exception:
        return ("Down", None, None)



# Function to perform an HTTP(s) check
def http_check(target):
    try:
        response = requests.get(target, verify=certifi.where())  # Use certifi to validate the certificate
        if response.status_code == 200:
            latency = response.elapsed.total_seconds() * 1000  # Convert to milliseconds
            return ("Up", f"{latency:.3f} ms", None)
        else:
            return ("Down", None, f"Returned status code: {response.status_code}")
    except SSLError:
        return ("Down", None, "SSL certificate validation failed")
    except Exception as e:
        return ("Down", None, None)



def keyword_check(target, keyword, expect_keyword):
    try:
        response = requests.get(target, verify=True)
        status_code = response.status_code
        if status_code != 200:
            return ("Down", None, f"Non-200 status code: {status_code}")
        else:
            text = response.text
            keyword_found = keyword in text
            status = "Up" if keyword_found == expect_keyword else "Down"
            latency = response.elapsed.total_seconds() * 1000  # Convert to milliseconds
            return (status, f"{latency:.3f} ms", None if status == "Up" else f"Keyword {'found' if keyword_found else 'not found'}")
    except requests.exceptions.SSLError:
        return ("Down", None, "Invalid or self-signed SSL certificate")
    except Exception as e:
        return ("Down", None, str(e))