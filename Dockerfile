# Use an official Python runtime as a parent image
FROM python:3.9-slim-buster

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install system dependencies
RUN apt-get update \
  && apt-get install -y netcat-openbsd iputils-ping \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

# Set working directory in Docker
WORKDIR /opt/pymon

# Copy Python dependencies files to Docker
COPY requirements.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the code
COPY . .

# Command to run the app
CMD [ "python", "main.py" ]
