#!/bin/bash

# MoviesFinder - Automated Codespace Setup Script
# This script runs automatically after the Codespace environment is created

echo "🚀 Starting MoviesFinder Setup..."
echo "=================================="

# Update pip to the latest version
echo "📦 Upgrading pip..."
python -m pip install --upgrade pip

# Install required Python packages
echo "📦 Installing required packages..."
python -m pip install streamlit requests python-dotenv

# Create data directory for cache (optional)
mkdir -p /workspaces/MoviesFinder/data

echo "✅ Setup complete!"
echo "=================================="
echo "🎬 Launching MoviesFinder Streamlit App..."
echo "The app will be available at: http://localhost:8501"
echo ""

# Launch the Streamlit app
cd /workspaces/MoviesFinder
streamlit run app.py --server.port=8501 --server.address=0.0.0.0
