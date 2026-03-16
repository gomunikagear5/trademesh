#!/usr/bin/env bash
# TradeMesh Dashboard — start script
# Usage: bash dashboard/start.sh

set -e

cd "$(dirname "$0")/.."

echo ""
echo "🔌 TradeMesh Dashboard"
echo "   Installing dependencies..."

pip install fastapi uvicorn jinja2 --quiet

echo "   Starting server on http://localhost:8765"
echo "   Ctrl+C to stop"
echo ""

uvicorn dashboard.app:app --host 0.0.0.0 --port 8765 --reload
