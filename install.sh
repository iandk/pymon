#!/bin/bash

# Update system packages
apt-get update

# Set working directory
mkdir -p /opt/pymon && cd /opt/pymon

# Install Python 3 and pip
apt-get install -y python3 python3-pip

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
systemctl start pymon
systemctl enable pymon
