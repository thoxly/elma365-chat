#!/bin/bash
# Script to set up database: create DB and tables

set -e

echo "=== Database Setup Script ==="
echo ""

# Check if virtual environment exists
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
else
    echo "Warning: Virtual environment not found."
    echo "Make sure dependencies are installed: pip install -r requirements.txt"
    echo ""
fi

# Get directory of script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"
cd "$PROJECT_DIR"

# Set PYTHONPATH
export PYTHONPATH="$PROJECT_DIR"

echo "Step 1: Creating database (if it doesn't exist)..."
python3 scripts/create_db.py

echo ""
echo "Step 2: Creating database tables..."
python3 scripts/init_tables.py

echo ""
echo "=== Database setup complete! ==="
echo ""
echo "You can now start the application:"
echo "  uvicorn app.main:app --reload"










