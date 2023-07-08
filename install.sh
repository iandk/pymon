#!/bin/bash

# Update system packages
apt update

# Set working directory
mkdir -p /opt/pymon && cd /opt/pymon

# Install Python 3 and pip
apt install -y python3 python3-pip python3.11-venv netcat-openbsd

# Create a virtual environment
python3 -m venv myvenv

# Activate the virtual environment
source myvenv/bin/activate

# Install required packages
pip install -r requirements.txt

# Deactivate the virtual environment
deactivate

# Setup systemd service file
cp pymon.service /etc/systemd/system/pymon.service
systemctl daemon-reload
systemctl enable pymon
