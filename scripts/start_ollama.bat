@echo off
REM FieldPack AI — Optimized Ollama Startup (Windows)
REM
REM Launches Ollama with memory-optimized settings for edge deployment.

echo FieldPack AI - Starting Ollama (memory-optimized)
echo    GPU: CPU-only
echo    KV Cache: q8_0 (int8)
echo    Flash Attention: enabled

set OLLAMA_NUM_GPU=0
set OLLAMA_FLASH_ATTENTION=1
set OLLAMA_KV_CACHE_TYPE=q8_0

echo Starting Ollama...
start /B ollama serve

REM Wait for ready
timeout /t 5 /nobreak > nul

REM Create custom model if needed
ollama list | findstr "fieldpack-assistant-lite" > nul 2>&1
if errorlevel 1 (
    echo Creating fieldpack-assistant-lite custom model...
    ollama create fieldpack-assistant-lite -f backend\modelfiles\fieldpack-assistant-lite.Modelfile
)

echo.
echo FieldPack AI Ollama is ready!
echo    Model: fieldpack-assistant-lite
echo    URL: http://localhost:11434
