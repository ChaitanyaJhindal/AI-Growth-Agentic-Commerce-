#!/usr/bin/env bash
# Exit immediately if a command exits with a non-zero status
set -o errexit

echo "==> Upgrading pip..."
pip install --upgrade pip

echo "==> Installing dependencies (Lightweight - Zero PyTorch/CUDA)..."
pip install --no-cache-dir -r requirements.txt

echo "==> Build completed successfully!"
