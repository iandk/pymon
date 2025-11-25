#!/bin/bash

# Update system packages
apt update

# Set working directory
mkdir -p /opt/pymon && cd /opt/pymon

# Install Python 3 and pip
apt install -y python3 python3-pip netcat-openbsd

# Install required Python packages system-wide
pip3 install -r requirements.txt --break-system-packages

# Setup systemd service file
cp pymon.service /etc/systemd/system/pymon.service
systemctl daemon-reload
systemctl enable pymon
