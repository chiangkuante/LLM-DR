#!/bin/bash

# Configuration
# Point to where you cloned llama.cpp (User requested ~/llama.cpp)
LLAMA_CPP_DIR="$HOME/llama.cpp"
MODEL_PATH="/home/wa1ter/LLM-DR/models/Ministral-3-14B-Instruct-2512-Q6_K.gguf"

# Check if model exists
if [ ! -f "$MODEL_PATH" ]; then
    echo "❌ Model not found at: $MODEL_PATH"
    echo "Please download it first."
    exit 1
fi

# Check if llama-server exists
SERVER_BIN="$LLAMA_CPP_DIR/build/bin/llama-server"

if [ ! -f "$SERVER_BIN" ]; then
    echo "❌ llama-server binary not found at: $SERVER_BIN"
    echo "Please compile llama.cpp first:"
    echo "  cd ~/llama.cpp"
    echo "  cmake -B build -DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=\"89\""
    echo "  cmake --build build --config Release -j 8"
    exit 1
fi

echo "🚀 Starting llama-server..."
echo "Model: $MODEL_PATH"

# Launch parameters
# -c 32768: Context size (adjust as needed, older config said 128k but 32k is safer for 24GB VRAM with this model size)
# -ngl 99: Offload all layers to GPU
# --host 0.0.0.0 --port 8080: Bind to all interfaces
# --parallel 4: Handle multiple requests (optional)
# -fa: Flash Attention (if supported)

"$SERVER_BIN" \
    -m "$MODEL_PATH" \
    -c 67000 \
    -ngl 99 \
    --host 0.0.0.0 \
    --port 8080 \
    --parallel 1 \
    --alias ministral-3-14b
