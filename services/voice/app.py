#!/usr/bin/env python3
"""
JARVIS Voice Service
FastAPI service for speech-to-text using Whisper.
"""

from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
import tempfile
import os
import sys
import subprocess
import whisper

SUPPORTED_MODELS = ("tiny", "base", "small", "medium", "large")

app = FastAPI(title="JARVIS Voice Service")

model = None

@app.on_event("startup")
async def load_model():
    global model
    model_size = os.getenv("WHISPER_MODEL", "base")
    if model_size not in SUPPORTED_MODELS:
        print(f"[!] Unknown model '{model_size}', falling back to 'base'")
        model_size = "base"
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        print("[!] ffmpeg not found — install ffmpeg for audio support")
    print(f"[*] Loading Whisper model: {model_size}")
    model = whisper.load_model(model_size)
    print(f"[OK] Whisper model '{model_size}' loaded")

@app.post("/transcribe")
async def transcribe(file: UploadFile = File(...)):
    """Transcribe uploaded audio file."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name
    
    try:
        result = model.transcribe(tmp_path)
        return {"text": result["text"], "language": result.get("language", "unknown")}
    finally:
        os.unlink(tmp_path)

@app.get("/health")
async def health():
    return {"status": "healthy", "model": os.getenv("WHISPER_MODEL", "base")}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8081)
