import argparse
from monitor import monitor_servers

# Parse command-line arguments
parser = argparse.ArgumentParser()
parser.add_argument("--silent", action="store_true", help="Run in silent mode")
args = parser.parse_args()

# Start monitoring servers
monitor_servers(silent=args.silent)
