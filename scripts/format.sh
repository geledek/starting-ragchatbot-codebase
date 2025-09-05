#!/bin/bash
# Code formatting script using Black and isort

set -e

echo "🔧 Formatting Python code with Black..."
uv run black backend/ --quiet

echo "📦 Sorting imports with isort..."
uv run isort backend/ --quiet

echo "✅ Code formatting complete!"