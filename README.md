# pymon

A Python-based script that allows you to monitor the status of servers and services. It supports various monitoring types such as ping, port check, HTTP(s) check, and keyword check. You can easily configure the script to monitor your desired servers and receive notifications via Telegram.

## Supported Monitoring Types

1. Ping: Checks the reachability and latency of a target IP address.
2. Port Check: Verifies if a specific port on a target IP address is open.
3. HTTP(s) Check: Sends an HTTP(s) request to a target URL and checks the response status code. It validates that the status code is 200 and the SSL certificate is present in case it's a https target.
4. Keyword Check: Verifies if a specific keyword is present or absent in the response content of an HTTP(s) request.

## Docker
Install Docker
```shell
curl -sSL https://get.docker.com | sh
```
Download pymon
```shell
mkdir -p /opt && cd /opt/ && git clone https://github.com/iandk/pymon.git
```

Edit configuration
```shell
# settings
cp /opt/pymon/.env.sample /opt/pymon/.env
nano /opt/pymon/.env

# monitoring targets
cp /opt/pymon/servers-sample.yaml /opt/pymon/servers.yaml
nano /opt/pymon/servers.yaml
```

Build container
```shell
cd pymon && docker build -t pymon:latest .
```

Run container
```shell
docker run -d --name pymon -v /opt/pymon:/opt/pymon --network host pymon
```

## Manual Installation
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
cp /opt/pymon/.env.sample /opt/pymon/.env
nano /opt/pymon/.env

# monitoring targets
cp /opt/pymon/servers-sample.yaml /opt/pymon/servers.yaml
nano /opt/pymon/servers.yaml
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


## Configuration

### Environment Variables (`.env`)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `BOT_TOKEN` | Yes | - | Telegram bot token from BotFather |
| `CHAT_ID` | Yes | - | Telegram chat ID for notifications |
| `FAILURE_THRESHOLD` | No | 3 | Consecutive failures before marking server as Down |
| `CHECK_INTERVAL_SECONDS` | No | 60 | Interval between server checks |
| `STATUS_REPORT_INTERVAL_MINUTES` | No | 60 | Interval between status report messages |
| `REPORT_ONLY_ON_DOWN` | No | false | Only send reports when servers are down |

To find your chat ID, send a message to your bot and access: `https://api.telegram.org/bot<bot_token>/getUpdates`

### Monitoring Targets (`servers.yaml`)

Each server entry requires:
- `description`: A brief description of the server or service
- `type`: Monitoring type (`ping`, `port`, `http`, or `keyword`)
- `target`: IP address or URL to monitor

Additional fields by type:
- `port` type: `port` - Port number to check
- `keyword` type: `keyword` - Keyword to search for, `expect_keyword` - true/false

Example configuration:
```yaml
- description: "1.1.1.1"
  type: ping
  target: "1.1.1.1"

- description: "v6Node.com"
  type: http
  target: "https://v6node.com"

- description: "Google"
  type: port
  target: "google.com"
  port: 80

- description: "v6Node Keyword check"
  type: keyword
  target: "https://v6node.com"
  keyword: "v6node"
  expect_keyword: true
```
