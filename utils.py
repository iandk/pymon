import os
import subprocess
import requests
import yaml
import certifi
import asyncio
from dotenv import load_dotenv
from requests.exceptions import SSLError
from telegram import Bot
from typing import Optional, Tuple, Dict, Any
import logging

load_dotenv()
logger = logging.getLogger(__name__)

class ConfigError(Exception):
    """Custom exception for configuration errors"""
    pass

async def notify_error(message: str, chat_id: Optional[str] = None, bot_token: Optional[str] = None):
    """Send error notification via both logging and Telegram if credentials available"""
    logger.error(message)
    if chat_id and bot_token:
        try:
            await send_telegram_message(f"⚠️ Configuration Error: {message}", chat_id, bot_token)
        except Exception as e:
            logger.error(f"Failed to send Telegram notification: {e}")

def validate_servers(data: list) -> None:
    """Validate servers YAML structure and raise ConfigError if invalid"""
    if not isinstance(data, list):
        raise ConfigError("servers.yaml must contain a list of servers")

    for idx, server in enumerate(data):
        required_server_fields = {
            "description": str,
            "type": str,
            "target": str
        }

        for field, expected_type in required_server_fields.items():
            if field not in server:
                raise ConfigError(f"Server #{idx + 1}: Missing required field: {field}")
            if not isinstance(server[field], expected_type):
                raise ConfigError(f"Server #{idx + 1}: Invalid type for {field}")

        if server["type"] not in ["ping", "port", "http", "keyword"]:
            raise ConfigError(f"Server #{idx + 1}: Invalid type value: {server['type']}")

def read_settings():
    """Read settings from environment variables"""
    bot_token = os.getenv("BOT_TOKEN")
    chat_id = os.getenv("CHAT_ID")
    failure_threshold = os.getenv("FAILURE_THRESHOLD", "3")
    check_interval = os.getenv("CHECK_INTERVAL_SECONDS", "60")
    status_report_interval = os.getenv("STATUS_REPORT_INTERVAL_MINUTES", "60")
    report_only_on_down = os.getenv("REPORT_ONLY_ON_DOWN", "false").lower() == "true"

    if not bot_token:
        raise ConfigError("Missing required environment variable: BOT_TOKEN")
    if not chat_id:
        raise ConfigError("Missing required environment variable: CHAT_ID")

    try:
        failure_threshold = int(failure_threshold)
        check_interval = int(check_interval)
        status_report_interval = int(status_report_interval)
    except ValueError as e:
        raise ConfigError(f"Invalid integer value in environment: {e}")

    return (
        bot_token,
        chat_id,
        failure_threshold,
        check_interval,
        status_report_interval,
        report_only_on_down
    )

def read_servers():
    """Read and validate servers configuration from YAML file"""
    servers_file = os.getenv("SERVERS_FILE", "servers.yaml")

    if not os.path.exists(servers_file):
        raise ConfigError(f"Configuration file not found: {servers_file}")

    try:
        with open(servers_file) as yaml_file:
            servers = yaml.safe_load(yaml_file)
            validate_servers(servers)
            return servers
    except yaml.YAMLError as e:
        raise ConfigError(f"Invalid YAML syntax in {servers_file}: {e}")
    except ConfigError:
        raise
    except Exception as e:
        raise ConfigError(f"Error reading {servers_file}: {str(e)}")

async def send_telegram_message(message: str, chat_id: str, bot_token: str, retry_count: int = 3):
    """Send Telegram message with retries"""
    for attempt in range(retry_count):
        try:
            bot = Bot(token=bot_token)
            await bot.send_message(chat_id=chat_id, text=message)
            return
        except Exception as e:
            if attempt == retry_count - 1:  # Last attempt
                logger.error(f"Failed to send Telegram message after {retry_count} attempts: {e}")
            else:
                await asyncio.sleep(1)  # Wait before retry

def format_timedelta(delta):
    """Format a timedelta into a human-readable string"""
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

def ping_check(target: str) -> Tuple[str, Optional[str], Optional[str]]:
    """Perform ping check with better error handling"""
    try:
        result = subprocess.run(
            ['ping', '-c', '1', '-W', '5', target],
            capture_output=True,
            text=True,
            timeout=6
        )
        if result.returncode == 0:
            latency = result.stdout.split('/')[-3].split('=')[-1].strip()
            return ("Up", latency, None)
        else:
            return ("Down", None, result.stderr.strip())
    except subprocess.TimeoutExpired:
        return ("Down", None, "Timeout")
    except Exception as e:
        logger.error(f"Ping check error for {target}: {str(e)}")
        return ("Down", None, str(e))

def port_check(target: str, port: int) -> Tuple[str, Optional[str], Optional[str]]:
    """Perform port check with better error handling"""
    try:
        result = subprocess.run(
            ['nc', '-z', '-w', '5', target, str(port)],
            capture_output=True,
            text=True,
            timeout=6
        )
        if result.returncode == 0:
            status, latency, _ = ping_check(target)
            return ("Up", latency, None)
        else:
            return ("Down", None, result.stderr.strip())
    except subprocess.TimeoutExpired:
        return ("Down", None, "Timeout")
    except Exception as e:
        logger.error(f"Port check error for {target}:{port}: {str(e)}")
        return ("Down", None, str(e))

def http_check(target: str) -> Tuple[str, Optional[str], Optional[str]]:
    """Perform HTTP check with better error handling"""
    try:
        session = requests.Session()
        session.verify = certifi.where()
        response = session.get(target, timeout=10)
        
        if response.status_code == 200:
            latency = response.elapsed.total_seconds() * 1000
            return ("Up", f"{latency:.3f} ms", None)
        else:
            return ("Down", None, f"Status code: {response.status_code}")
    except requests.Timeout:
        return ("Down", None, "Timeout")
    except SSLError:
        return ("Down", None, "SSL certificate validation failed")
    except Exception as e:
        logger.error(f"HTTP check error for {target}: {str(e)}")
        return ("Down", None, str(e))
    finally:
        session.close()

def keyword_check(target: str, keyword: str, expect_keyword: bool) -> Tuple[str, Optional[str], Optional[str]]:
    """Perform keyword check with better error handling"""
    try:
        session = requests.Session()
        session.verify = certifi.where()
        response = session.get(target, timeout=10)
        
        if response.status_code != 200:
            return ("Down", None, f"Status code: {response.status_code}")
        
        text = response.text
        keyword_found = keyword.lower() in text.lower()
        status = "Up" if keyword_found == expect_keyword else "Down"
        latency = response.elapsed.total_seconds() * 1000
        
        if status == "Up":
            return (status, f"{latency:.3f} ms", None)
        else:
            return (status, None, f"Keyword {'found' if keyword_found else 'not found'}")
    except requests.Timeout:
        return ("Down", None, "Timeout")
    except SSLError:
        return ("Down", None, "SSL certificate validation failed")
    except Exception as e:
        logger.error(f"Keyword check error for {target}: {str(e)}")
        return ("Down", None, str(e))
    finally:
        session.close()