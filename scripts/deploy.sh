#!/bin/bash
# scripts/deploy.sh
# Complete deployment script for the Autopoietic System

set -e

echo "========================================"
echo "  CAIS Autopoietic System Deployment"
echo "========================================"
echo ""

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version | cut -d' ' -f2)
required_version="3.10.0"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "❌ Python version $python_version is less than $required_version"
    exit 1
fi
echo "✅ Python version: $python_version"

# Create directory structure
echo ""
echo "Creating directory structure..."
mkdir -p ~/PROMETHEUS
cd ~/PROMETHEUS

# Create all directories
for dir in src/agents src/core src/integrations src/parsers src/generators src/validators src/dashboard src/acquisitor src/worm \
            data/constitution data/laws data/instructions data/categories \
            input/constitution input/laws input/google_drive \
            downloads compressed processed \
            output/generated_code output/generated_rules output/reports output/parsed \
            logs/success logs/errors logs/review_needed \
            config config/security config/worm \
            tests/unit tests/integration tests/fixtures \
            docs docs/generated; do
    mkdir -p "$dir"
done

# Setup virtual environment
echo ""
echo "Setting up virtual environment..."
python3 -m venv venv_prometheus
source venv_prometheus/bin/activate

# Install dependencies
echo ""
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt 2>/dev/null || echo "⚠️ requirements.txt not found, continuing..."

# Create credential directory
mkdir -p config/security
chmod 700 config/security

echo ""
echo "========================================"
echo "  Deployment complete!"
echo "========================================"
echo ""
echo "Next steps:"
echo "1. Place your Google Drive service account key in:"
echo "   ~/PROMETHEUS/config/security/gdrive-credentials.json"
echo ""
echo "2. Place constitution PDFs in:"
echo "   ~/PROMETHEUS/input/constitution/"
echo ""
echo "3. Place building code PDFs in:"
echo "   ~/PROMETHEUS/input/laws/"
echo ""
echo "4. Run the Sovereign Dashboard:"
echo "   cd ~/PROMETHEUS && source venv_prometheus/bin/activate && python -m src.dashboard.sovereign_dashboard"
echo ""
echo "5. The system will guide you through the rest."
