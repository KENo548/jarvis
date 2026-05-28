#!/usr/bin/env python3
"""
JARVIS Voice Input Module
Uses OpenAI Whisper for local speech-to-text.
"""

import sys
import os
import tempfile
import numpy as np

def transcribe(audio_path: str = None, model_size: str = "base") -> str:
    """Transcribe audio file to text using Whisper."""
    import whisper
    
    if audio_path is None:
        # Record from microphone
        try:
            import sounddevice as sd
            print("[*] Recording... Speak now (Ctrl+C to stop)")
            duration = 10  # seconds
            sample_rate = 16000
            audio = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1)
            sd.wait()
            audio = audio.flatten()
            
            # Save to temp file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                import scipy.io.wavfile as wavfile
                wavfile.write(f.name, sample_rate, (audio * 32767).astype(np.int16))
                audio_path = f.name
        except ImportError:
            print("[!] Install sounddevice: pip install sounddevice")
            return ""
    
    print(f"[*] Loading Whisper model ({model_size})...")
    model = whisper.load_model(model_size)
    
    print(f"[*] Transcribing {audio_path}...")
    result = model.transcribe(audio_path)
    
    # Clean up temp file
    if audio_path and os.path.exists(audio_path):
        os.unlink(audio_path)
    
    return result["text"].strip()


def list_models():
    """List available Whisper models."""
    models = ["tiny", "base", "small", "medium", "large"]
    print("Available Whisper models:")
    for m in models:
        sizes = {"tiny": "39M", "base": "74M", "small": "244M", "medium": "769M", "large": "1550M"}
        print(f"  {m}: {sizes.get(m, 'unknown')} parameters")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "list":
            list_models()
        else:
            model = sys.argv[2] if len(sys.argv) > 2 else "base"
            text = transcribe(sys.argv[1], model)
            print(f"\n[Transcript]: {text}")
    else:
        print("Usage:")
        print("  python voice_input.py <audio_file> [model_size]")
        print("  python voice_input.py list")
        print("\nModels: tiny, base, small, medium, large")
        print("Example: python voice_input.py recording.wav base")
