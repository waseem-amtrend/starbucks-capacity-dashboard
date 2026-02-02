#!/bin/bash
# Quick start script for Starbucks Capacity Dashboard

echo "🚀 Starting Starbucks Capacity Dashboard..."
echo ""

# Check for API key
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "⚠️  ANTHROPIC_API_KEY not set!"
    echo "   Set it with: export ANTHROPIC_API_KEY='your-key-here'"
    echo "   Or create a .env file (see .env.template)"
    exit 1
fi

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3.8+"
    exit 1
fi

# Check/Install dependencies
if ! python3 -c "import flask" 2>/dev/null; then
    echo "📦 Installing dependencies..."
    pip3 install -r requirements.txt
fi

# Start server
echo "✅ Starting server on http://localhost:5000"
echo "📊 Dashboard: http://localhost:5000"
echo "💚 Health: http://localhost:5000/health"
echo ""
python3 backend_server.py
