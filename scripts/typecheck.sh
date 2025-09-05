#!/bin/bash
# Type checking script using mypy

set -e

echo "🔍 Running mypy type checker..."
uv run mypy backend/ --ignore-missing-imports

echo "✅ Type checking complete - no issues found!"