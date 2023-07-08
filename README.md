# pymon

The Monitoring Script is a Python-based script that allows you to monitor the status of servers and services. It supports various monitoring types such as ping, port check, HTTP(s) check, and keyword check. You can easily configure the script to monitor your desired servers and receive notifications via Telegram.

## Supported Monitoring Types

1. Ping: Checks the reachability and latency of a target IP address.
2. Port Check: Verifies if a specific port on a target IP address is open.
3. HTTP(s) Check: Sends an HTTP(s) request to a target URL and checks the response status code. It validates that the status code is 200 and the SSL certificate is present in case it's a https target.
4. Keyword Check: Verifies if a specific keyword is present or absent in the response content of an HTTP(s) request.

## Installation

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


## Configuration options
To monitor your desired servers and services, configure the servers.json file with the following options:


Server Configuration Options:

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

