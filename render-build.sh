#!/usr/bin/env bash
# Exit immediately if a command exits with a non-zero status
set -o errexit

echo "==> Upgrading pip..."
pip install --upgrade pip

echo "==> Installing lightweight CPU-only PyTorch..."
pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

echo "==> Installing remaining dependencies..."
pip install --no-cache-dir -r requirements.txt

echo "==> Pre-caching sentence transformer model weights (all-MiniLM-L6-v2)..."
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

echo "==> Build completed successfully!"
