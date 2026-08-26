#!/usr/bin/env bash
# Exit immediately if a command exits with a non-zero status
set -o errexit

echo "==> Upgrading pip..."
pip install --upgrade pip

echo "==> Installing Python dependencies (Lightweight - Zero PyTorch/CUDA)..."
pip install --no-cache-dir -r requirements.txt

if command -v npm &> /dev/null; then
    echo "==> Installing Node.js Baileys dependencies..."
    npm install --omit=dev --no-audit --no-fund
fi

echo "==> Build completed successfully!"
