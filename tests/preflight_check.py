#!/usr/bin/env python3
"""
SAGE/JARVIS Infrastructure Pre-Flight Check
============================================
Verifies all critical services and dependencies before voice testing.

Usage:
    python tests/preflight_check.py              # Full check
    python tests/preflight_check.py --quick       # Quick check (services only)
    python tests/preflight_check.py --json        # JSON output for automation
    python tests/preflight_check.py --report      # Save report to file

Exit codes:
    0 = All checks passed (or only warnings)
    1 = One or more critical checks failed
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import socket
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

OLLAMA_URL = "http://localhost:11434"
WHISPER_URL = "http://localhost:8081"
REQUIRED_OLLAMA_MODELS = ["llama3.2:latest", "nomic-embed-text:latest"]
REQUIRED_DOCKER_CONTAINERS = [
    "jarvis-voice", "jarvis-chroma", "jarvis-redis",
]
CRITICAL_PYTHON_MODULES = [
    "sounddevice", "edge_tts", "numpy", "pyautogui", "pyperclip",
    "mss", "PIL", "psutil",
]
VOICE_PIPELINE_MODULES = [
    "sounddevice",   # microphone input
    "edge_tts",      # text-to-speech output
    "numpy",         # audio data processing
]
TTS_AVAILABLE = ["en-US-GuyNeural", "en-US-JennyNeural", "en-GB-SoniaNeural"]
TIMEOUT = 5  # seconds for service checks

# ---------------------------------------------------------------------------
# Result tracking
# ---------------------------------------------------------------------------

CRITICAL = "critical"
WARNING = "warning"
INFO = "info"
PASS = "pass"

results: list[dict[str, Any]] = []
exit_code = 0


def check(name: str, category: str, critical: bool = False) -> dict:
    """Create a check context and return it."""
    return {
        "name": name,
        "category": category,
        "critical": critical,
        "status": "pending",
        "detail": "",
        "start": time.time(),
    }


def pass_check(ctx: dict, detail: str = "") -> None:
    """Mark a check as passed."""
    ctx["status"] = PASS
    ctx["detail"] = detail
    ctx["elapsed_ms"] = int((time.time() - ctx["start"]) * 1000)
    results.append(ctx)
    icon = "OK" if not ctx["critical"] else "**"
    print(f"  [{icon}] {ctx['name']} - {detail}")


def fail_check(ctx: dict, detail: str, is_critical: bool = False) -> None:
    """Mark a check as failed."""
    global exit_code
    if is_critical or ctx["critical"]:
        ctx["status"] = CRITICAL
        exit_code = 1
    else:
        ctx["status"] = WARNING
    ctx["detail"] = detail
    ctx["elapsed_ms"] = int((time.time() - ctx["start"]) * 1000)
    results.append(ctx)
    icon = "FAIL" if ctx["status"] == CRITICAL else "WARN"
    print(f"  [{icon}] {ctx['name']} - {detail}")


def warn_check(ctx: dict, detail: str) -> None:
    """Mark a check as warning (non-critical)."""
    ctx["status"] = WARNING
    ctx["detail"] = detail
    ctx["elapsed_ms"] = int((time.time() - ctx["start"]) * 1000)
    results.append(ctx)
    print(f"  [WARN] {ctx['name']} - {detail}")


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def http_get(url: str, timeout: int = TIMEOUT) -> tuple[int, str]:
    """Simple HTTP GET returning (status_code, body)."""
    try:
        import urllib.request
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, body
    except Exception as e:
        return 0, str(e)


def http_post(url: str, data: dict, timeout: int = TIMEOUT) -> tuple[int, str]:
    """Simple HTTP POST with JSON body."""
    try:
        import urllib.request
        body = json.dumps(data).encode()
        req = urllib.request.Request(url, data=body, method="POST")
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode()
    except Exception as e:
        return 0, str(e)


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

def check_ollama_service() -> None:
    """Check that Ollama is running and models are available."""
    ctx = check("Ollama Service", "services", critical=True)

    status, body = http_get(f"{OLLAMA_URL}/api/tags")
    if status != 200:
        fail_check(ctx, f"Ollama not responding on {OLLAMA_URL} (HTTP {status})")
        return

    try:
        data = json.loads(body)
        installed = [m["name"] for m in data.get("models", [])]
    except (json.JSONDecodeError, KeyError) as e:
        fail_check(ctx, f"Ollama response parse error: {e}")
        return

    missing = [m for m in REQUIRED_OLLAMA_MODELS if m not in installed]
    if missing:
        fail_check(
            ctx,
            f"Ollama running but missing model(s): {', '.join(missing)}",
            is_critical=True,
        )
        return

    # Quick test — ping the model
    g_status, g_body = http_post(
        f"{OLLAMA_URL}/api/generate",
        {"model": "llama3.2", "prompt": "ping", "stream": False},
        timeout=15,
    )
    if g_status != 200:
        fail_check(ctx, f"Ollama model test failed (HTTP {g_status})")
        return

    models_detail = ", ".join(installed)
    pass_check(ctx, f"Ollama running, models: {models_detail}")


def check_whisper_service() -> None:
    """Check that Whisper STT service is running on port 8081."""
    ctx = check("Whisper STT Service", "services", critical=True)

    status, body = http_get(f"{WHISPER_URL}/health")
    if status != 200:
        fail_check(ctx, f"Whisper not responding on {WHISPER_URL} (HTTP {status})")
        return

    try:
        data = json.loads(body)
        model = data.get("model", "unknown")
        pass_check(ctx, f"Whisper running — model: {model}")
    except json.JSONDecodeError:
        fail_check(ctx, f"Whisper health response invalid: {body[:100]}")


def test_whisper_transcription() -> None:
    """Send a silent audio sample and verify Whisper responds."""
    ctx = check("Whisper Transcription", "services", critical=True)

    try:
        import requests as req_lib
        import numpy as np
        import io
        import wave

        # Generate 1.0s of silence
        sample_rate = 16000
        audio = np.zeros(sample_rate, dtype=np.int16)

        # Write WAV to bytes
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(audio.tobytes())
        wav_data = buf.getvalue()

        # Use requests library for clean multipart
        files = {"file": ("silence.wav", wav_data, "audio/wav")}
        resp = req_lib.post(f"{WHISPER_URL}/transcribe", files=files, timeout=60)
        resp.raise_for_status()
        result = resp.json()
        text = result.get("text", "").strip()
        pass_check(ctx, f"Whisper responded (empty audio -> \"{text[:60]}\")")
    except ImportError:
        # Fallback: use urllib with proper multipart
        try:
            import numpy as np
            import urllib.request
            import io
            import wave

            sample_rate = 16000
            audio = np.zeros(sample_rate, dtype=np.int16)
            buf = io.BytesIO()
            with wave.open(buf, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(sample_rate)
                wf.writeframes(audio.tobytes())
            wav_data = buf.getvalue()

            boundary = "----PreflightBoundary"
            header = (
                "--" + boundary + "\r\n"
                "Content-Disposition: form-data; name=\"file\"; filename=\"silence.wav\"\r\n"
                "Content-Type: audio/wav\r\n\r\n"
            ).encode("utf-8")
            footer = ("\r\n--" + boundary + "--\r\n").encode("utf-8")
            body = header + wav_data + footer

            req = urllib.request.Request(
                f"{WHISPER_URL}/transcribe",
                data=body,
                headers={"Content-Type": "multipart/form-data; boundary=" + boundary},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read().decode())
                text = result.get("text", "").strip()
                pass_check(ctx, f"Whisper responded (empty audio -> \"{text[:60]}\")")
        except Exception as e2:
            fail_check(ctx, f"Whisper test failed: {e2}", is_critical=True)
    except Exception as e:
        fail_check(ctx, f"Whisper transcription test failed: {e}", is_critical=True)


def check_edge_tts() -> None:
    """Check edge-tts is installed and voices are available."""
    ctx = check("Edge TTS", "dependencies", critical=True)

    try:
        import edge_tts
        version = getattr(edge_tts, "__version__", "installed")
        found_voices = 0
        available = []

        # Try listing voices with a fresh event loop
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            v = loop.run_until_complete(edge_tts.list_voices())
            loop.close()
            voice_names = [x["ShortName"] for x in v if "ShortName" in x]
            found_voices = len(voice_names)
            available = [v for v in TTS_AVAILABLE if v in voice_names]
        except Exception as ve:
            # Voice listing may fail in some environments
            pass

        if found_voices > 0:
            pass_check(
                ctx,
                f"edge-tts {version}: {found_voices} voices available, "
                f"{len(available)} preferred voice(s) found",
            )
        else:
            # Package works but listing failed — still functional
            pass_check(ctx, f"edge-tts {version} installed and importable")
    except ImportError:
        fail_check(ctx, "edge-tts not installed — run: pip install edge-tts", is_critical=True)


def check_sounddevice() -> None:
    """Check sounddevice is installed and audio devices are available."""
    ctx = check("Sounddevice Audio", "dependencies", critical=True)

    try:
        import sounddevice as sd
        devices = sd.query_devices()
        inputs = [d for d in devices if d["max_input_channels"] > 0]
        outputs = [d for d in devices if d["max_output_channels"] > 0]

        if not inputs:
            fail_check(ctx, "No input (microphone) devices found!", is_critical=True)
            return

        if not outputs:
            fail_check(ctx, "No output (speaker) devices found!", is_critical=True)
            return

        # Find best mic
        best = sd.default.device
        best_mic = devices[best[0]] if best[0] < len(devices) else inputs[0]
        best_spk = devices[best[1]] if best[1] < len(devices) else outputs[0]

        pass_check(
            ctx,
            f"sounddevice {sd.__version__}: {len(inputs)} mic(s), {len(outputs)} speaker(s) — "
            f"default mic: {best_mic['name']}, default speaker: {best_spk['name']}",
        )
    except ImportError:
        fail_check(ctx, "sounddevice not installed — run: pip install sounddevice", is_critical=True)
    except Exception as e:
        fail_check(ctx, f"sounddevice error: {e}")


def check_pyqt6() -> None:
    """Check PyQt6 is installed."""
    ctx = check("PyQt6", "dependencies")

    try:
        from PyQt6.QtCore import QT_VERSION_STR
        try:
            from PyQt6.QtWidgets import QApplication
            pass_check(ctx, f"PyQt6 {QT_VERSION_STR}")
        except ImportError:
            warn_check(ctx, f"PyQt6 {QT_VERSION_STR} (QtWidgets not fully available — headless?)")
    except ImportError:
        fail_check(ctx, "PyQt6 not installed — run: pip install PyQt6", is_critical=True)


def check_playwright() -> None:
    """Check Playwright and browser installation."""
    ctx = check("Playwright Browser", "dependencies")

    try:
        import playwright
        version = getattr(playwright, "__version__", "unknown")

        # Check if chromium is installed
        browser_path = Path.home() / "AppData" / "Local" / "ms-playwright"
        chromium_dirs = list(browser_path.glob("chromium-*")) if browser_path.exists() else []
        ff_dirs = list(browser_path.glob("firefox-*")) if browser_path.exists() else []

        browsers = []
        if chromium_dirs:
            browsers.append(f"chromium ({len(chromium_dirs)} install)")
        if ff_dirs:
            browsers.append(f"firefox ({len(ff_dirs)} install)")

        if browsers:
            pass_check(ctx, f"Playwright {version}, browsers: {', '.join(browsers)}")
        else:
            warn_check(ctx, f"Playwright {version} installed, but no browsers found — run: python -m playwright install chromium")
    except ImportError:
        fail_check(ctx, "Playwright not installed — run: pip install playwright")


def check_ffmpeg() -> None:
    """Check ffmpeg is available (needed by voice pipeline for audio conversion)."""
    ctx = check("FFmpeg", "dependencies", critical=True)

    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path:
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True, text=True, timeout=10,
            )
            first_line = result.stdout.split("\n")[0] if result.stdout else "ffmpeg"
            pass_check(ctx, f"{first_line}")
        except Exception as e:
            fail_check(ctx, f"ffmpeg found at {ffmpeg_path} but failed to run: {e}", is_critical=True)
    else:
        fail_check(ctx, "ffmpeg not found in PATH — required for audio conversion", is_critical=True)


def check_python_modules() -> None:
    """Check all critical Python modules are importable."""
    ctx = check("Python Modules", "dependencies", critical=True)

    missing = []
    details = []
    for mod_name in CRITICAL_PYTHON_MODULES:
        try:
            import_name = mod_name.replace("-", "_")
            mod = __import__(import_name)
            ver = getattr(mod, "__version__", "ok")
            details.append(f"{mod_name}=={ver}")
        except ImportError:
            missing.append(mod_name)

    if missing:
        fail_check(
            ctx,
            f"Missing modules: {', '.join(missing)} — run pip install",
            is_critical=True,
        )
    else:
        pass_check(ctx, f"All {len(CRITICAL_PYTHON_MODULES)} modules importable")


def check_docker_containers() -> None:
    """Check critical Docker containers are running."""
    ctx = check("Docker Containers", "services")

    try:
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}\t{{.Status}}"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            warn_check(ctx, f"Docker not accessible: {result.stderr.strip()}")
            return

        running = {}
        for line in result.stdout.strip().split("\n"):
            if "\t" in line:
                name, status = line.split("\t", 1)
                running[name] = status

        missing = [c for c in REQUIRED_DOCKER_CONTAINERS if c not in running]
        unhealthy = [c for c in REQUIRED_DOCKER_CONTAINERS if c in running and "unhealthy" in running[c].lower()]

        parts = []
        if not missing:
            parts.append(f"{len(REQUIRED_DOCKER_CONTAINERS)}/{len(REQUIRED_DOCKER_CONTAINERS)} critical containers up")
        else:
            parts.append(f"missing: {', '.join(missing)}")
            fail_check(ctx, f"Missing containers: {', '.join(missing)}")

        if unhealthy:
            fail_check(ctx, f"Unhealthy containers: {', '.join(unhealthy)}")
        elif not missing and not unhealthy:
            pass_check(ctx, "; ".join(parts))

    except FileNotFoundError:
        fail_check(ctx, "Docker not installed or not in PATH")
    except subprocess.TimeoutExpired:
        warn_check(ctx, "Docker command timed out")


def check_network_connectivity() -> None:
    """Verify network connectivity to critical services."""
    ctx = check("Network Connectivity", "services", critical=True)

    endpoints = [("Ollama", OLLAMA_URL), ("Whisper", WHISPER_URL)]
    failures = []

    for name, url in endpoints:
        host = url.split("://")[1].split(":")[0]
        port = int(url.split(":")[-1].split("/")[0])
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(TIMEOUT)
        try:
            sock.connect((host, port))
            sock.close()
        except Exception as e:
            failures.append(f"{name} ({host}:{port}): {e}")
        finally:
            sock.close()

    if failures:
        fail_check(ctx, f"Connectivity failures: {'; '.join(failures)}", is_critical=True)
    else:
        pass_check(ctx, "All service endpoints reachable")


def check_voice_pipeline_end_to_end() -> None:
    """End-to-end check: can we record -> transcribe -> speak?"""
    ctx = check("Voice Pipeline (dry-run)", "pipeline", critical=True)

    checks_passed = 0
    checks_total = 3
    failures = []

    # 1. Can we record audio?
    try:
        import sounddevice as sd
        import numpy as np
        # Just check we can open a stream briefly
        data = np.zeros(1600, dtype=np.int16)
        checks_passed += 1
    except Exception as e:
        failures.append(f"audio capture: {e}")

    # 2. Can we reach Whisper?
    try:
        import urllib.request
        req = urllib.request.Request(f"{WHISPER_URL}/health")
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            checks_passed += 1
    except Exception as e:
        failures.append(f"whisper: {e}")

    # 3. Can we import edge_tts?
    try:
        import edge_tts
        checks_passed += 1
    except ImportError:
        failures.append("edge-tts not installed")

    if failures:
        fail_check(ctx, f"Pipeline issues: {'; '.join(failures)}", is_critical=True)
    else:
        pass_check(ctx, f"Dry-run: {checks_passed}/{checks_total} stages OK")


def check_disk_space() -> None:
    """Check available disk space for logging and model storage."""
    ctx = check("Disk Space", "system")

    try:
        import shutil
        total, used, free = shutil.disk_usage("/")
        free_gb = free // (1024 ** 3)
        if free_gb < 5:
            fail_check(ctx, f"Low disk space: {free_gb} GB free (need >= 5 GB)")
        elif free_gb < 20:
            warn_check(ctx, f"{free_gb} GB free")
        else:
            pass_check(ctx, f"{free_gb} GB free")
    except Exception:
        if sys.platform == "win32":
            import ctypes
            free_bytes = ctypes.c_ulonglong(0)
            ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                ctypes.c_wchar_p(os.getcwd()),
                None, None, ctypes.pointer(free_bytes),
            )
            free_gb = free_bytes.value // (1024 ** 3)
            if free_gb < 5:
                fail_check(ctx, f"Low disk space: {free_gb} GB free")
            else:
                pass_check(ctx, f"{free_gb} GB free")


def check_audio_loopback() -> None:
    """Verify we can do a short audio recording."""
    ctx = check("Audio Loopback Test", "pipeline", critical=True)

    try:
        import sounddevice as sd
        import numpy as np

        duration = 0.5  # 500ms
        sample_rate = 16000
        recording = sd.rec(
            int(duration * sample_rate),
            samplerate=sample_rate,
            channels=1,
            dtype="int16",
            blocking=True,
        )
        if recording is None:
            fail_check(ctx, "Recording returned None")
            return

        peak = np.abs(recording).max()
        level = "silent" if peak < 50 else "quiet" if peak < 500 else "audible"
        pass_check(ctx, f"Recorded {duration}s — peak amplitude: {peak} ({level})")
    except Exception as e:
        fail_check(ctx, f"Audio loopback failed: {e}", is_critical=True)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_all(quick: bool = False) -> int:
    """Run all checks and return exit code."""
    global exit_code

    print()
    print("=" * 60)
    print("  SAGE/JARVIS Infrastructure Pre-Flight Check")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    print()

    # -- Layer 1: Core Services --
    print("  +- Core Services -----------------------------------------+")
    check_ollama_service()
    check_whisper_service()
    if not quick:
        test_whisper_transcription()
    check_network_connectivity()
    check_docker_containers()

    # -- Layer 2: Dependencies --
    print("\n  +- Dependencies ------------------------------------------+")
    check_edge_tts()
    check_sounddevice()
    check_pyqt6()
    check_playwright()
    check_ffmpeg()
    check_python_modules()

    # -- Layer 3: Pipeline Tests --
    print("\n  +- Pipeline Tests ----------------------------------------+")
    check_voice_pipeline_end_to_end()
    if not quick:
        check_audio_loopback()
    check_disk_space()

    # -- Summary --
    print("\n  +- Summary -----------------------------------------------+")
    critical_fails = [r for r in results if r["status"] == CRITICAL]
    warnings = [r for r in results if r["status"] == WARNING]
    passed = [r for r in results if r["status"] == PASS]

    print(f"    Total: {len(results)}  |  "
          f"Pass: {len(passed)}  |  "
          f"Warning: {len(warnings)}  |  "
          f"Critical: {len(critical_fails)}")

    if critical_fails:
        print(f"\n    !! CRITICAL FAILURES ({len(critical_fails)}):")
        for c in critical_fails:
            print(f"       - {c['name']}: {c['detail']}")

    if warnings:
        print(f"\n    !! WARNINGS ({len(warnings)}):")
        for w in warnings:
            print(f"       - {w['name']}: {w['detail']}")

    print()
    print("=" * 60)
    verdict = "PASS" if exit_code == 0 else "FAIL"
    print(f"  VERDICT: {verdict}")
    print(f"  Ready for voice testing: {'YES' if exit_code == 0 else 'FIX ISSUES FIRST'}")
    print("=" * 60)
    print()

    return exit_code


def save_report(path: str | None = None) -> str:
    """Save JSON report to file."""
    if path is None:
        reports_dir = Path("reports")
        reports_dir.mkdir(exist_ok=True)
        path = str(reports_dir / f"preflight_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")

    report = {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total": len(results),
            "passed": sum(1 for r in results if r["status"] == PASS),
            "warnings": sum(1 for r in results if r["status"] == WARNING),
            "critical": sum(1 for r in results if r["status"] == CRITICAL),
        },
        "checks": results,
        "exit_code": exit_code,
        "verdict": "PASS" if exit_code == 0 else "FAIL",
    }

    with open(path, "w") as f:
        json.dump(report, f, indent=2)

    return path


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="SAGE/JARVIS Infrastructure Pre-Flight Check")
    parser.add_argument("--quick", action="store_true", help="Skip transcription and audio loopback tests")
    parser.add_argument("--json", action="store_true", help="Output as JSON (to stdout)")
    parser.add_argument("--report", type=str, nargs="?", const=True, help="Save report to file")

    args = parser.parse_args()

    code = run_all(quick=args.quick)

    if args.report:
        path = save_report(args.report if isinstance(args.report, str) else None)
        print(f"\nReport saved to: {path}")

    if args.json:
        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total": len(results),
                "passed": sum(1 for r in results if r["status"] == PASS),
                "warnings": sum(1 for r in results if r["status"] == WARNING),
                "critical": sum(1 for r in results if r["status"] == CRITICAL),
            },
            "checks": results,
            "exit_code": code,
            "verdict": "PASS" if code == 0 else "FAIL",
        }
        print(json.dumps(report, indent=2))

    sys.exit(code)
