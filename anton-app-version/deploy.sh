#!/bin/bash
# Simple deployment script for AWS EC2 (Amazon Linux 2 or Ubuntu)

# Ensure docker is installed (for Ubuntu/Debian)
if ! command -v docker &> /dev/null
then
    echo "Docker not found. Installing docker..."
    sudo apt-get update
    sudo apt-get install -y docker.io docker-compose-v2
    sudo usermod -aG docker $USER
    echo "Please log out and log back in, then run this script again."
    exit 1
fi

if [ ! -f .env ]; then
    echo "No .env file found! Copying .env.example to .env"
    echo "Please edit .env with your bot token and API keys before running this script again."
    cp .env.example .env
    exit 1
fi

echo "Building and starting the bot..."
# Use docker compose plugin
docker compose up --build -d

echo "Bot is running!"
docker compose logs -f
