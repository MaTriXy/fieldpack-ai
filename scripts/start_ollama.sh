#!/usr/bin/env bash
# FieldPack AI — Optimized Ollama Startup
#
# Launches Ollama with memory-optimized settings for edge deployment:
#   - OLLAMA_NUM_GPU=0         -> CPU-only (prevents Intel iGPU garbage output)
#   - OLLAMA_FLASH_ATTENTION=1 -> Flash attention for faster KV cache ops
#   - OLLAMA_KV_CACHE_TYPE=q8_0 -> Int8 KV cache (~50% less memory than fp16)
#
# These settings reduce VRAM from ~7.5GB to ~4-5GB, making Gemma 4 E2B
# run comfortably on any laptop with 8GB RAM.
#
# Usage:
#   chmod +x scripts/start_ollama.sh
#   ./scripts/start_ollama.sh
#
# The script will:
#   1. Start Ollama with optimized settings
#   2. Wait for it to be ready
#   3. Create the fieldpack-assistant-lite custom model if it doesn't exist
#   4. Pre-load the model into memory

set -euo pipefail

echo "FieldPack AI - Starting Ollama (memory-optimized)"
echo "   GPU: CPU-only (OLLAMA_NUM_GPU=0)"
echo "   KV Cache: q8_0 (int8, ~50% less memory)"
echo "   Flash Attention: enabled"
echo ""

# Export optimized settings
export OLLAMA_NUM_GPU=0
export OLLAMA_FLASH_ATTENTION=1
export OLLAMA_KV_CACHE_TYPE=q8_0

# Start Ollama in the background
ollama serve &
OLLAMA_PID=$!

# Wait for Ollama to be ready
echo "Waiting for Ollama to start..."
for i in $(seq 1 30); do
    if curl -s http://localhost:11434/api/version > /dev/null 2>&1; then
        echo "Ollama is ready (version: $(curl -s http://localhost:11434/api/version | grep -o '"version":"[^"]*"'))"
        break
    fi
    sleep 1
done

# Pull base model if needed
if ! ollama list | grep -q "gemma4:e2b-it-q4_K_M"; then
    echo "Pulling Gemma 4 E2B (Q4_K_M)..."
    ollama pull gemma4:e2b-it-q4_K_M
fi

# Create custom model if needed
if ! ollama list | grep -q "fieldpack-assistant-lite"; then
    echo "Creating fieldpack-assistant-lite custom model..."
    SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
    ollama create fieldpack-assistant-lite -f "$SCRIPT_DIR/../backend/modelfiles/fieldpack-assistant-lite.Modelfile"
    echo "Custom model created"
fi

# Pre-load model
echo "Pre-loading model into memory..."
ollama run fieldpack-assistant-lite "" --keepalive -1 2>/dev/null || true

echo ""
echo "FieldPack AI Ollama is ready!"
echo "   Model: fieldpack-assistant-lite"
echo "   URL: http://localhost:11434"
echo "   PID: $OLLAMA_PID"
echo ""
echo "   Press Ctrl+C to stop"

# Wait for Ollama process
wait $OLLAMA_PID
