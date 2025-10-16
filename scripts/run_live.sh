#!/bin/bash
# Run trading system in LIVE mode

if [ -z "$MT5_LOGIN" ] || [ -z "$MT5_PASSWORD" ] || [ -z "$MT5_SERVER" ]; then
    echo "Error: MT5 credentials not set!"
    echo "Please set environment variables:"
    echo "  export MT5_LOGIN=your_login"
    echo "  export MT5_PASSWORD=your_password"
    echo "  export MT5_SERVER=your_server"
    exit 1
fi

echo "Starting Instant Bot in LIVE MODE..."
echo "WARNING: Real money trading!"
read -p "Press Enter to continue or Ctrl+C to cancel..."

python -m src.ui.cli trade --config configs/example_if_100k.yaml
