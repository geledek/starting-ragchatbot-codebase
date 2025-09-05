#!/bin/bash
# Comprehensive code quality check script

set -e

echo "🚀 Running comprehensive code quality checks..."
echo

# Format check (dry run)
echo "1️⃣ Checking code formatting..."
if ! uv run black backend/ --check --quiet; then
    echo "❌ Code formatting issues found. Run './scripts/format.sh' to fix."
    exit 1
fi
echo "✅ Code formatting is consistent"
echo

# Import sorting check
echo "2️⃣ Checking import sorting..."
if ! uv run isort backend/ --check-only --quiet; then
    echo "❌ Import sorting issues found. Run './scripts/format.sh' to fix."
    exit 1
fi
echo "✅ Imports are properly sorted"
echo

# Linting
echo "3️⃣ Running linter..."
if ! uv run flake8 backend/; then
    echo "❌ Linting issues found. Please fix the issues above."
    exit 1
fi
echo "✅ No linting issues found"
echo

# Type checking
echo "4️⃣ Running type checker..."
if ! uv run mypy backend/ --ignore-missing-imports --quiet; then
    echo "❌ Type checking issues found. Please fix the issues above."
    exit 1
fi
echo "✅ No type checking issues found"
echo

# Run tests
echo "5️⃣ Running tests..."
if ! uv run pytest backend/tests/ -v; then
    echo "❌ Some tests failed. Please fix the failing tests."
    exit 1
fi
echo "✅ All tests passed"
echo

echo "🎉 All quality checks passed! Your code is ready for commit."