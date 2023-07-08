# pymon

The Monitoring Script is a Python-based script that allows you to monitor the status of servers and services. It supports various monitoring types such as ping, port check, HTTP(s) check, and keyword check. You can easily configure the script to monitor your desired servers and receive notifications via Telegram.

## Supported Monitoring Types

1. Ping: Checks the reachability and latency of a target IP address.
2. Port Check: Verifies if a specific port on a target IP address is open.
3. HTTP(s) Check: Sends an HTTP(s) request to a target URL and checks the response status code. It validates that the status code is 200 and the SSL certificate is present in case it's a https target.
4. Keyword Check: Verifies if a specific keyword is present or absent in the response content of an HTTP(s) request.

## Installation
You have two options for running the script: running it in the background, which will automatically monitor for status changes, or running it in the terminal with a graphical output.

###  Background Service 
To run the script as a background service, follow the steps below:


1. Clone the repository to your local machine:

```shell
mkdir -p /opt && cd /opt/
git clone https://github.com/iandk/pymon.git
cd pymon && bash install.sh
```
2. Edit configuration
```shell
# settings
mv /opt/pymon/settings-sample.json /opt/pymon/settings.json
nano /opt/pymon/settings.json

# monitoring targets
mv /opt/pymon/servers-sample.json /opt/pymon/servers.json
nano /opt/pymon/servers.json

```
3. Start pymon
```shell
systemctl start pymon
systemctl status pymon
```

### Terminal View
To run the script in the terminal with a graphical output, use the following command:
> **Note:** The terminal view should only be used if the system service is stopped. Running both the service and terminal view simultaneously may cause conflicts.
```shell
cd /opt/pymon/ && myvenv/bin/python3 main.py
```


## Configuration options
The monitoring script utilizes two configuration files: servers.json to specify monitoring targets such as descriptions, types, and targets, and settings.json to configure application behavior including bot token, chat ID, intervals, and notification preferences

### Monitoring targets:
`servers.json`

- `description`: A brief description of the server or service being monitored.

- `type`: The type of monitoring to perform. Supported types are:
  - `ping`: Checks the reachability and latency of a target IP address.
  - `port`: Verifies if a specific port on a target IP address is open.
  - `http`: Sends an HTTP(s) request to a target URL and checks the response status code.
  - `keyword`: Verifies if a specific keyword is present or absent in the response content of an HTTP(s) request.

- `target`: The IP address or URL of the server or service to monitor.

- `port` (only for `port` type): The port number to check for the `port` monitoring type.

- `keyword` (only for `keyword` type): The keyword to search for in the response content.

- `expect_keyword` (only for `keyword` type): Set to `true` if the keyword should be present, or `false` if it should be absent.

### Application settings:
`settings.json` 

- `bot_token`: The token of your Telegram bot. You can obtain this token by creating a bot using the BotFather bot on Telegram.

- `chat_id`: The chat ID where you want to receive the monitoring notifications. You can find the chat ID by sending a message to your bot and then accessing the following URL: `https://api.telegram.org/bot<bot_token>/getUpdates`.

- `failure_threshold`: The number of consecutive failures before considering a server as "Down".

- `check_interval_seconds`: The interval, in seconds, between each server check.

- `status_report_interval_minutes`: The interval, in minutes, between each status report. The script will send a status report message at this interval, indicating the overall status of all monitored servers.

- `report_only_on_down`: Set this value to `true` if you want to receive status report messages only when a server is "Down". Set it to `false` if you want to receive status report messages regardless of the server status.



Example configuration
```json
{
  "servers": [
    {
      "description": "1.1.1.1",
      "type": "ping",
      "target": "1.1.1.1"
    },
    {
      "description": "v6Node.com",
      "type": "http",
      "target": "https://v6node.com"
    },
    {
      "description": "Google",
      "type": "port",
      "target": "google.com",
      "port": 80
    },
    {
      "description": "v6Node Keyword check",
      "type": "keyword",
      "target": "https://v6node.com",
      "keyword": "v6node",
      "expect_keyword": true
    }
  ]
}
```

