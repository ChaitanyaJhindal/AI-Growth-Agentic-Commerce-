#!/usr/bin/env bash
# Exit immediately if a command exits with a non-zero status
set -o errexit

echo "==> Upgrading pip..."
pip install --upgrade pip

echo "==> Installing lightweight CPU-only PyTorch (prevents Out-Of-Memory / status 137)..."
pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

echo "==> Installing remaining dependencies..."
pip install --no-cache-dir -r requirements.txt

echo "==> Build completed successfully!"
