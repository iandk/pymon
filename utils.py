import os
import subprocess
import requests
import json
import certifi
import asyncio
from requests.exceptions import SSLError
from telegram import Bot
from typing import Optional, Tuple, Dict, Any
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='monitor.log'
)
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

def validate_json_structure(data: Dict[str, Any], file_name: str) -> None:
    """Validate JSON structure and raise ConfigError if invalid"""
    if file_name == "settings.json":
        required_fields = {
            "bot_token": str,
            "chat_id": str,
            "failure_threshold": int,
            "check_interval_seconds": int,
            "status_report_interval_minutes": int
        }
        
        for field, expected_type in required_fields.items():
            if field not in data:
                raise ConfigError(f"Missing required field: {field}")
            if not isinstance(data[field], expected_type):
                raise ConfigError(f"Invalid type for {field}: expected {expected_type.__name__}")
                
    elif file_name == "servers.json":
        if not isinstance(data.get("servers"), list):
            raise ConfigError("Missing or invalid 'servers' array")
            
        for idx, server in enumerate(data["servers"]):
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
    """Read and validate settings with enhanced error handling"""
    if not os.path.exists("settings.json"):
        raise ConfigError("Configuration file not found: settings.json")
        
    try:
        with open("settings.json") as json_file:
            settings = json.load(json_file)
            validate_json_structure(settings, "settings.json")
            
            return (
                settings.get("bot_token"),
                settings.get("chat_id"),
                settings.get("failure_threshold"),
                settings.get("check_interval_seconds"),
                settings.get("status_report_interval_minutes"),
                settings.get("report_only_on_down", False)
            )
    except json.JSONDecodeError as e:
        line_col = f" at line {e.lineno}, column {e.colno}"
        raise ConfigError(f"Invalid JSON syntax in settings.json{line_col}: {e.msg}")
    except Exception as e:
        raise ConfigError(f"Error reading settings.json: {str(e)}")

def read_servers():
    """Read and validate servers configuration with enhanced error handling"""
    if not os.path.exists("servers.json"):
        raise ConfigError("Configuration file not found: servers.json")
        
    try:
        with open("servers.json") as json_file:
            config = json.load(json_file)
            validate_json_structure(config, "servers.json")
            return config["servers"]
    except json.JSONDecodeError as e:
        line_col = f" at line {e.lineno}, column {e.colno}"
        raise ConfigError(f"Invalid JSON syntax in servers.json{line_col}: {e.msg}")
    except Exception as e:
        raise ConfigError(f"Error reading servers.json: {str(e)}")

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