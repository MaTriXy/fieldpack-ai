# Handoff: Intel Arc iGPU Acceleration for Ollama

## Goal
Get Ollama to offload Gemma 4 E2B (Q4_K_M, 7GB) layers to the Intel Arc iGPU on this Windows 11 laptop. Currently running pure CPU at ~12 tok/s. Target: 30-50+ tok/s with iGPU offload.

## Hardware
- Intel Core Ultra 7 (Meteor Lake / Arrow Lake)
- Intel Arc iGPU (integrated, shared VRAM from 32GB RAM)
- Device ID: 0x7d45, Vulkan 1.4.328 conformant
- Driver: 32.0.101.8332 (Intel proprietary, current)
- No discrete GPU

## What We Already Know

### Ollama DOES ship a Vulkan backend
- `C:\Users\or.k\AppData\Local\Programs\Ollama\lib\ollama\vulkan\ggml-vulkan.dll` (52MB, dated 2026-04-04)
- Ollama version: 0.20.2
- The startup log says: `experimental Vulkan support disabled. To enable, set OLLAMA_VULKAN=1`

### The env var never reached the process
- We tried `set OLLAMA_VULKAN=1` in PowerShell and `OLLAMA_VULKAN=1` in bash
- Ollama runs as a tray app (`ollama app.exe`) that spawns `ollama.exe` — it ignores terminal env vars
- Server config dump always showed `OLLAMA_VULKAN:false`
- `OLLAMA_INTEL_GPU=1` is NOT a real Ollama variable — it does nothing

### NPU is not usable
- Intel NPU is for fixed-function AI (Studio Effects, ONNX via OpenVINO)
- No support for Gemma 4 architecture on NPU
- Off the table

## Step-by-Step Fix

### Step 1: Set env var permanently (5 min)
```powershell
# In PowerShell (admin or user):
setx OLLAMA_VULKAN 1

# Also set these for shared-memory iGPU:
setx OLLAMA_GPU_OVERHEAD 0
setx GGML_VK_VISIBLE_DEVICES 0
```

### Step 2: Fully restart Ollama
- Right-click Ollama tray icon -> Quit (don't just close window)
- Verify no ollama processes: `tasklist | findstr ollama`
- Verify port free: `netstat -ano | findstr 11434`
- Start Ollama from Start Menu or tray icon (it reads system env on startup)

### Step 3: Verify Vulkan is active
Check the server log:
```powershell
Get-Content "$env:LOCALAPPDATA\Ollama\server.log" -Tail 50
```
Must show: `OLLAMA_VULKAN:true` in the config dump.

If GPU is detected, you'll see lines like:
```
msg="inference compute" id=0 library=vulkan name="Intel(R) Arc(TM)..."
```

### Step 4: Test with model
```bash
curl http://localhost:11434/api/generate -d '{"model":"gemma4:e2b-it-q4_K_M","prompt":"Hello","stream":false}'
```
Then check: `curl http://localhost:11434/api/ps`
- `size_vram > 0` = layers offloaded to iGPU

### Step 5: If 0 layers offload (shared memory issue)
Force partial offload via API:
```bash
# Start with 8 layers, increase until performance degrades
curl http://localhost:11434/api/generate -d '{
  "model": "gemma4:e2b-it-q4_K_M",
  "prompt": "Hello",
  "options": {"num_gpu": 18}
}'
```

Each E2B Q4_K_M layer is ~200MB. With 8GB shared VRAM budget, can offload ~30-35 layers (out of 36 total).

To make `num_gpu` permanent, add it to `offline_llm.py`:
```python
return ChatOllama(
    model=settings.ollama_model,
    base_url=settings.ollama_base_url,
    temperature=temperature,
    num_gpu=settings.ollama_num_gpu,  # Add to config.py: default 36
)
```

## Fallback: llama.cpp with Intel SYCL

If Ollama Vulkan doesn't work with shared memory, the nuclear option is building llama.cpp with Intel SYCL (oneAPI):

1. Install Intel oneAPI Base Toolkit (free): `intel.com/oneapi`
2. Build llama.cpp with `-DGGML_SYCL=ON`
3. Run `llama-server` as HTTP endpoint
4. Point app at it (different API contract than Ollama — needs adapter)

This is 30-60 min setup and breaks the Ollama abstraction. Only do this if Vulkan fails.

## Relevant Files
- `C:\Users\or.k\AppData\Local\Ollama\server.log` — ground truth for GPU detection
- `C:\Users\or.k\AppData\Local\Programs\Ollama\lib\ollama\vulkan\` — Vulkan backend DLLs
- `C:\fieldpack-ai\backend\app\models\offline_llm.py` — ChatOllama instantiation
- `C:\fieldpack-ai\backend\app\config.py` — settings (add ollama_num_gpu if needed)

## Known Ollama Issues
- GitHub issues #4896, #5886, #6214 — iGPU Vulkan offload inconsistencies on Windows
- Shared-memory devices may report available_vram=0, causing 0-layer offload
- `num_gpu` API option can force offload past this detection bug
