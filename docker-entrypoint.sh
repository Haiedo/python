#!/bin/bash
set -e

echo "Starting Expense Splitter..."

if [ ! -f "instance/expense_splitter.db" ]; then
    echo "Database not found. Initializing..."
    python -c "from app import create_app, db; app = create_app(); app.app_context().push(); db.create_all()"
    echo "Running seed data..."
    python seed_data.py
fi

echo "Starting Flask application..."
exec python run.py
