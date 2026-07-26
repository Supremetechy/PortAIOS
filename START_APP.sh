#!/bin/bash
# Quick Start Script for PortAIOS with DeepGram Integration

echo "🚀 Starting PortAIOS with DeepGram Voice Agent..."
echo ""

# Activate virtual environment
if [ -d "venv" ]; then
    echo "✅ Activating virtual environment..."
    source venv/bin/activate
else
    echo "⚠️  No virtual environment found. Using system Python."
fi

# Check for .env file
if [ -f ".env" ]; then
    echo "✅ .env file found"
else
    echo "⚠️  .env file not found. Creating from template..."
    cp .env.example .env
    echo "📝 Please edit .env and add your DEEPGRAM_API_KEY"
fi

# Start the application
echo ""
echo "🎤 Starting application..."
echo ""
python kernel/onboarding_gui.py
