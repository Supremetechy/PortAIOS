# AI-OS Model Repository

This directory contains the AI models used by AI-OS for on-device inference.

## Recommended Model: Gemma 2B Instruction-Tuned (Q4_K_M)

### Download Instructions

```bash
# Using Hugging Face CLI
pip install huggingface-hub
huggingface-cli download google/gemma-2b-it-GGUF gemma-2b-it-q4_k_m.gguf --local-dir .

# Or download directly from:
# https://huggingface.co/google/gemma-2b-it-GGUF/blob/main/gemma-2b-it-q4_k_m.gguf
```

### Alternative Models

**Small & Fast (< 1GB):**
- `phi-3-mini-4k-instruct-q4.gguf` (2.3GB) - Microsoft Phi-3, excellent reasoning
- `llama-3.2-1b-instruct-q4_k_m.gguf` (800MB) - Ultra-fast, basic capabilities
- `tinyllama-1.1b-chat-v1.0.q4_k_m.gguf` (669MB) - Minimal footprint

**Medium Quality (2-4GB):**
- `gemma-2b-it-q4_k_m.gguf` (2.5GB) - **RECOMMENDED** - Best balance
- `mistral-7b-instruct-v0.2.q4_k_m.gguf` (4.4GB) - Higher quality, slower

**High Quality (> 4GB):**
- `llama-3.1-8b-instruct-q4_k_m.gguf` (4.9GB) - Excellent, requires 8GB+ RAM
- `mixtral-8x7b-instruct-v0.1.q4_k_m.gguf` (26GB) - Best quality, GPU required

## Model Specifications

### Gemma 2B IT Q4_K_M (Recommended)

```
Model: gemma-2b-it-q4_k_m.gguf
Size: 2.5 GB
RAM Required: 4-6 GB
Quantization: Q4_K_M (4-bit, mixed precision)
Context: 8192 tokens
Speed (CPU): ~10-20 tokens/sec
Speed (GPU): ~50-100 tokens/sec
License: Gemma Terms of Use
```

**Capabilities:**
- Instruction following
- Question answering
- Code assistance
- System configuration help
- Hardware guidance

**Ideal for:**
- Boot-time onboarding
- System configuration
- Hardware optimization advice
- General AI assistance

## File Structure

After download, your structure should be:

```
models/
├── README.md (this file)
├── gemma-2b-it-q4_k_m.gguf (2.5GB)
└── .gitignore
```

## Testing the Model

```bash
# Test with llama.cpp directly
cd kernel_rs/llama.cpp
./build/bin/main -m ../../models/gemma-2b-it-q4_k_m.gguf \
    -p "You are an AI assistant in AI-OS. Introduce yourself." \
    -n 100
```

## Integration with AI-OS

The model is automatically loaded during boot if present at:
- `/models/gemma-2b-it-q4_k_m.gguf` (in ISO)
- Or configured path in `kernel_rs/src/ai/mod.rs`

## Disk Space Requirements

- Model file: 2.5 GB
- ISO build: 3.0 GB (includes kernel + model + initramfs)
- Runtime RAM: 4-6 GB (model loaded in memory)

## Performance Optimization

**CPU-only:**
- Enable AVX2/AVX512: Compile with `-DLLAMA_AVX2=ON`
- Use all cores: Set `threads: num_cpus` in AIConfig

**With GPU:**
- CUDA: Set `gpu_layers: 32` (offload all layers)
- ROCm/HIP: Similar performance
- Metal (Apple): Automatic acceleration

## Updating Models

To update or change models:

1. Download new model to `models/`
2. Update path in `kernel_rs/src/ai/mod.rs`:
   ```rust
   model_path: "/models/your-model.gguf"
   ```
3. Rebuild ISO: `./build_iso.sh`

## License Compliance

**Gemma:** Google Gemma Terms of Use
- Free for research and commercial use
- See: https://ai.google.dev/gemma/terms

**Other models:** Check respective licenses on Hugging Face

## Troubleshooting

**Model not loading:**
- Check file size matches expected (~2.5GB)
- Verify GGUF format (not GGML or other)
- Ensure sufficient RAM

**Slow inference:**
- Enable GPU offloading
- Reduce context size
- Use smaller quantization (Q4 vs Q8)

**Out of memory:**
- Use smaller model (1B instead of 2B)
- Reduce context window
- Close other applications
