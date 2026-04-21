# FieldPack AI - Quick Start (PowerShell)

> **Preferred method:** See the main [README.md](../README.md) for the Docker one-command setup (`docker-compose up`). This quickstart is maintained for developers who prefer a native Python/Node/Ollama environment.

---

All commands below are for **PowerShell on Windows**.
Run each section in its own terminal window.

---

## 1. Activate Virtual Environment

Run this first in every new terminal:

```powershell
cd C:\fieldpack-ai
.\venv\Scripts\Activate
```

---

## 2. Start Ollama

Ollama usually auto-starts with Windows. Check if it's already running:

```powershell
ollama ps
```

If it's NOT running:

```powershell
ollama serve
```

If you get a "port already in use" error, it's already running -- skip this step.

---

## 3. Start Backend

```powershell
cd C:\fieldpack-ai\backend
$env:PYTHONPATH = "."
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend runs at `http://localhost:8000`

---

## 4. Start Frontend

```powershell
cd C:\fieldpack-ai\frontend
npm run dev
```

Frontend runs at `http://localhost:5173` (proxies API calls to backend on port 8000).

---

## 5. Build APK

```powershell
cd C:\fieldpack-ai\frontend
npm run build
npx cap sync android

$env:JAVA_HOME = "C:\fieldpack-ai\jdk-21.0.10+7"
$env:ANDROID_SDK_ROOT = "C:\fieldpack-ai\.android-sdk"
$env:PATH = "$env:JAVA_HOME\bin;$env:PATH"

.\android\gradlew.bat -p android assembleDebug
```

The APK will be at:
`frontend/android/app/build/outputs/apk/debug/app-debug.apk`

---

## Notes

- Backend must be started from `C:\fieldpack-ai\backend` (not the repo root)
- You need 3 separate terminals: Ollama, backend, frontend
- The phone APK connects to the backend over WiFi -- backend must bind `0.0.0.0`
- If the LLM returns garbage, check `ollama ps` for CPU/GPU split (see `docs/TROUBLESHOOTING_LLM.md`)
