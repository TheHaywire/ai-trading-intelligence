#!/bin/bash
# Run trading system in paper mode

echo "Starting Instant Bot in PAPER MODE..."
python -m src.ui.cli trade --config configs/example_if_100k.yaml --paper
