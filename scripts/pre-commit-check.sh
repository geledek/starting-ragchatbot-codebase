#!/bin/bash
# Essential pre-commit quality checks

set -e

echo "🚀 Running essential pre-commit checks..."
echo

# Format check (dry run)
echo "1️⃣ Checking code formatting..."
if ! uv run black backend/ --check --quiet; then
    echo "❌ Code formatting issues found. Running formatter..."
    uv run black backend/
    echo "✅ Code formatted successfully"
else
    echo "✅ Code formatting is consistent"
fi
echo

# Import sorting check
echo "2️⃣ Checking import sorting..."
if ! uv run isort backend/ --check-only --quiet; then
    echo "❌ Import sorting issues found. Running import sorter..."
    uv run isort backend/
    echo "✅ Imports sorted successfully"
else
    echo "✅ Imports are properly sorted"
fi
echo

# Run tests
echo "3️⃣ Running tests..."
if ! uv run pytest backend/tests/ --quiet; then
    echo "❌ Some tests failed. Please fix the failing tests."
    exit 1
fi
echo "✅ All tests passed"
echo

echo "🎉 Essential pre-commit checks completed! Code is ready for commit."