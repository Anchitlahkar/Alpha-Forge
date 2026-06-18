#!/bin/bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
echo "Setup complete. Please edit the .env file with your API keys."