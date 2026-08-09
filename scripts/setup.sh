#!/bin/bash

# Setup script for multi-tenant SaaS platform
# This script helps set up the development environment

echo "🚀 Setting up Multi-Tenant SaaS Platform Development Environment"

# Check if we're on the root directory
if [ ! -f "README.md" ]; then
    echo "❌ Please run this script from the project root directory"
    exit 1
fi

echo "📁 Creating the canonical local environment file..."

# Create .env.local if it doesn't exist. Staging and production files are
# intentionally opt-in so a fresh setup cannot accidentally target cloud data.
if [ ! -f ".env.local" ]; then
    echo "📝 Creating .env.local from .env.local.example..."
    cp .env.local.example .env.local
    echo "✅ .env.local created. Please update it with your local Supabase and provider values."
else
    echo "✅ .env.local already exists"
fi

echo ""
echo "🔧 Installing dependencies..."

# Install frontend dependencies
if [ -d "frontend" ]; then
    echo "📦 Installing frontend dependencies..."
    cd frontend
    npm install
    cd ..
    echo "✅ Frontend dependencies installed"
fi

# Install backend dependencies
if [ -d "backend" ]; then
    echo "🐍 Setting up backend environment..."
    cd backend
    
    # Create virtual environment if it doesn't exist
    if [ ! -d ".venv" ]; then
        echo "🔧 Creating Python virtual environment..."
        python3 -m venv .venv
    fi
    
    # Activate virtual environment
    echo "🔧 Activating virtual environment..."
    source .venv/bin/activate
    
    # Install dependencies
    echo "📦 Installing backend dependencies..."
    pip install -r requirements.txt
    
    cd ..
    echo "✅ Backend environment set up"
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "📝 Next steps:"
echo "1. Update .env.local with your local configuration."
echo "   For cloud staging validation, create .env.staging from its example and run:"
echo "      ./start.sh start dev --env staging"
echo ""
echo "2. For local development with Docker:"
echo "   - Start: ./start.sh start dev"
echo "   - Check selected config: ./start.sh config"
echo ""
echo "3. For production deployment, create .env.prod from .env.prod.example"
echo "   and run ./scripts/deploy.sh (production is the default deploy file)."
echo ""
echo "📖 For more information, see docs/ENV_VARS.md"
