#!/bin/bash
# Code linting script using flake8

set -e

echo "🔍 Running flake8 linter..."
uv run flake8 backend/

echo "✅ Linting complete - no issues found!"