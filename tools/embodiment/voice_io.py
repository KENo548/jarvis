#!/usr/bin/env python3
"""SAGE Voice I/O — microphone input, Whisper STT, Edge TTS output.

Handles the full voice loop:
  microphone -> WAV -> Whisper (port 8081) -> text -> SAGE -> text -> Edge TTS -> speaker

Dependencies:
  pip install sounddevice numpy edge-tts

Whisper service must be running at port 8081 (docker: jarvis-voice).
"""

from __future__ import annotations

import asyncio
import io
import json
import queue
import sys
import tempfile
import threading
import time
import wave
from pathlib import Path
from typing import Callable

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from llm_client import llm_call

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

WHISPER_URL = "http://localhost:8081"
SAMPLE_RATE = 16000
CHANNELS = 1
CHUNK_DURATION = 0.5  # seconds per chunk for VAD
SILENCE_THRESHOLD = 300  # amplitude threshold for silence detection
MAX_RECORD_SECONDS = 30
TTS_VOICE = "en-US-GuyNeural"  # Edge TTS voice
MIC_DEVICE = None  # auto-detect


def _find_best_mic():
    """Find the best input device by testing each one briefly."""
    import sounddevice as sd
    import numpy as np

    devices = sd.query_devices()
    best_idx = sd.default.device[0]
    best_amp = 0

    for i, d in enumerate(devices):
        if d["max_input_channels"] < 1:
            continue
        if "Stereo Mix" in d["name"] or "PC Speaker" in d["name"]:
            continue
        try:
            with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="int16",
                                blocksize=4000, device=i) as stream:
                data, _ = stream.read(4000)
                audio = data[:, 0] if data.ndim > 1 else data
                amp = np.abs(audio).mean()
                if amp > best_amp:
                    best_amp = amp
                    best_idx = i
        except Exception:
            continue

    if best_amp > 100:
        print(f"[VoiceIO] Using mic: {devices[best_idx]['name']} (device {best_idx}, amp={best_amp:.0f})")
    else:
        print(f"[VoiceIO] Using default mic: {devices[best_idx]['name']} (device {best_idx})")
    return best_idx


# ---------------------------------------------------------------------------
# Microphone recording
# ---------------------------------------------------------------------------

def record_audio(
    max_seconds: int = MAX_RECORD_SECONDS,
    silence_threshold: int = SILENCE_THRESHOLD,
    silence_duration: float = 2.0,
) -> np.ndarray | None:
    """Record audio from microphone with voice activity detection.

    Returns numpy array of audio samples or None if no speech detected.
    """
    try:
        import sounddevice as sd
    except ImportError:
        print("[VoiceIO] sounddevice not installed. Run: pip install sounddevice")
        return None

    global MIC_DEVICE
    if MIC_DEVICE is None:
        MIC_DEVICE = _find_best_mic()

    audio_chunks: list[np.ndarray] = []
    silence_start: float | None = None
    is_recording = False

    print("[VoiceIO] Listening... speak now")

    try:
        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype="int16",
            blocksize=int(SAMPLE_RATE * CHUNK_DURATION),
            device=MIC_DEVICE,
        ) as stream:
            start_time = time.time()

            while time.time() - start_time < max_seconds:
                data, overflowed = stream.read(stream.blocksize)
                audio_chunk = data[:, 0] if data.ndim > 1 else data
                amplitude = np.abs(audio_chunk).mean()

                if amplitude > silence_threshold:
                    if not is_recording:
                        is_recording = True
                        print("[VoiceIO] Speech detected, recording...")
                    audio_chunks.append(audio_chunk.copy())
                    silence_start = None
                elif is_recording:
                    if silence_start is None:
                        silence_start = time.time()
                    elif time.time() - silence_start > silence_duration:
                        print("[VoiceIO] Silence detected, stopping recording")
                        break

    except Exception as e:
        print(f"[VoiceIO] Recording error: {e}")
        return None

    if not audio_chunks:
        print("[VoiceIO] No speech detected")
        return None

    return np.concatenate(audio_chunks)


def save_wav(audio: np.ndarray, path: str | Path) -> Path:
    """Save numpy audio array as WAV file."""
    path = Path(path)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(audio.tobytes())
    return path


# ---------------------------------------------------------------------------
# Whisper STT
# ---------------------------------------------------------------------------

def transcribe_whisper(audio: np.ndarray) -> str:
    """Transcribe audio via Whisper service at port 8081."""
    import urllib.request
    import urllib.error

    # Save audio to temp WAV
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        save_wav(audio, tmp_path)

        # Build multipart request
        boundary = "----SAGEVoiceBoundary"
        with open(tmp_path, "rb") as f:
            audio_data = f.read()

        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="audio.wav"\r\n'
            f"Content-Type: audio/wav\r\n\r\n"
        ).encode() + audio_data + f"\r\n--{boundary}--\r\n".encode()

        req = urllib.request.Request(
            f"{WHISPER_URL}/transcribe",
            data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode())
            return result.get("text", "").strip()

    except urllib.error.URLError as e:
        print(f"[VoiceIO] Whisper service unavailable: {e}")
        return ""
    except Exception as e:
        print(f"[VoiceIO] Transcription error: {e}")
        return ""
    finally:
        try:
            Path(tmp_path).unlink()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Edge TTS
# ---------------------------------------------------------------------------

def speak(text: str, voice: str = TTS_VOICE) -> bool:
    """Convert text to speech using Edge TTS and play it.

    Returns True if successful.
    """
    if not text.strip():
        return False

    try:
        import edge_tts
    except ImportError:
        print("[VoiceIO] edge-tts not installed. Run: pip install edge-tts")
        return False

    try:
        import numpy as np
        import sounddevice as sd
        import io, wave

        communicate = edge_tts.Communicate(text, voice)

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            tmp_path = tmp.name

        # Run async edge_tts in a new event loop (safe from threads)
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    pool.submit(asyncio.run, communicate.save(tmp_path)).result()
            else:
                loop.run_until_complete(communicate.save(tmp_path))
        except RuntimeError:
            asyncio.run(communicate.save(tmp_path))

        # Convert MP3 to raw PCM via edge_tts audio stream, fallback to file
        try:
            import subprocess
            pcm_path = tmp_path.replace(".mp3", ".raw")
            subprocess.run(
                ["ffmpeg", "-y", "-i", tmp_path, "-f", "s16le", "-ar", str(SAMPLE_RATE),
                 "-ac", str(CHANNELS), pcm_path],
                capture_output=True, timeout=10,
            )
            pcm_data = Path(pcm_path).read_bytes()
            audio = np.frombuffer(pcm_data, dtype=np.int16)
            sd.play(audio, samplerate=SAMPLE_RATE, blocking=True)
            try:
                Path(pcm_path).unlink()
            except Exception:
                pass
        except (FileNotFoundError, subprocess.TimeoutExpired):
            # ffmpeg not available — open in default media player
            if sys.platform == "win32":
                subprocess.Popen(["cmd", "/c", "start", tmp_path], shell=False)
            time.sleep(min(len(text) * 0.05, 10))

        try:
            Path(tmp_path).unlink()
        except Exception:
            pass

        return True

    except Exception as e:
        print(f"[VoiceIO] TTS error: {e}")
        return False


# ---------------------------------------------------------------------------
# Full voice loop
# ---------------------------------------------------------------------------

def voice_loop(
    agent_fn: Callable[[str], str],
    max_seconds: int = MAX_RECORD_SECONDS,
    continuous: bool = False,
) -> None:
    """Run the full voice loop: listen -> transcribe -> agent -> speak.

    Args:
        agent_fn: Function that takes user text and returns response text.
        max_seconds: Max recording duration per turn.
        continuous: If True, keep listening after each response.
    """
    print("[VoiceIO] Voice loop started. Say something or press Ctrl+C to stop.")

    try:
        while True:
            # Record
            audio = record_audio(max_seconds=max_seconds)
            if audio is None:
                if not continuous:
                    break
                continue

            # Transcribe
            user_text = transcribe_whisper(audio)
            if not user_text:
                print("[VoiceIO] Could not understand audio")
                if not continuous:
                    break
                continue

            print(f"[VoiceIO] You said: {user_text}")

            # Get agent response
            try:
                response = agent_fn(user_text)
            except Exception as e:
                response = f"Sorry, I encountered an error: {e}"

            print(f"[VoiceIO] Sage says: {response}")

            # Speak response
            try:
                speak(response)
            except Exception as e:
                print(f"[VoiceIO] Speak failed: {e}")

            if not continuous:
                break

    except KeyboardInterrupt:
        print("\n[VoiceIO] Voice loop stopped.")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="SAGE Voice I/O")
    parser.add_argument("--listen", action="store_true", help="Record and transcribe")
    parser.add_argument("--speak", type=str, help="Text to speak")
    parser.add_argument("--loop", action="store_true", help="Run continuous voice loop")
    parser.add_argument("--max-seconds", type=int, default=MAX_RECORD_SECONDS)
    args = parser.parse_args()

    if args.speak:
        speak(args.speak)
    elif args.listen:
        audio = record_audio(max_seconds=args.max_seconds)
        if audio is not None:
            text = transcribe_whisper(audio)
            print(f"Transcribed: {text}")
    elif args.loop:
        def echo_agent(text: str) -> str:
            return f"You said: {text}"
        voice_loop(echo_agent, continuous=True)
    else:
        parser.print_help()
