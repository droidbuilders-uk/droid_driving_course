#!/bin/bash
echo "Setting up Droid Course Virtual Environment..."
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
echo "Setup complete. Use 'source venv/bin/activate' before running main.py"
