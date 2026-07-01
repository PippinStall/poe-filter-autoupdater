#!/usr/bin/env bash
# Builds a native Linux binary for local testing.
# For a Windows .exe, push a tag (v*) to trigger the GitHub Actions workflow.
set -e

echo "Installing dependencies..."
pip install pyinstaller customtkinter

echo ""
echo "Building..."
pyinstaller \
  --onefile \
  --name "PoE2FilterUpdater" \
  --collect-data customtkinter \
  app/main.py

echo ""
echo "Done! Binary is in dist/"
