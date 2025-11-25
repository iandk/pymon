#!/bin/bash

# Update system packages
apt update

# Set working directory
mkdir -p /opt/pymon && cd /opt/pymon

# Install Python 3 and pip
apt install -y python3 python3-pip netcat-openbsd

# Upgrade pip to latest version
python3 -m pip install --upgrade pip

# Install required Python packages system-wide
python3 -m pip install -r requirements.txt

# Setup systemd service file
cp pymon.service /etc/systemd/system/pymon.service
systemctl daemon-reload
systemctl enable pymon
