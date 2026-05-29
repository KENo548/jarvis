"""SAGE Embodiment E2E Verification — Tier 1 tool tests.

Run: python -m tests.embodiment_e2e
Gate: 6/7 must pass before adding dangerous tools.
"""

from __future__ import annotations

import json
import sys
import tempfile
import time
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent.parent / "tools"
sys.path.insert(0, str(TOOLS_DIR))
sys.path.insert(0, str(TOOLS_DIR / "embodiment"))

RESULTS: list[dict] = []


def _test(name: str, fn):
    t0 = time.time()
    try:
        passed, detail = fn()
        ms = int((time.time() - t0) * 1000)
        RESULTS.append({"name": name, "passed": passed, "ms": ms, "detail": detail})
        icon = "PASS" if passed else "FAIL"
        print(f"  [{icon}] {name} ({ms}ms) — {detail}")
    except Exception as e:
        ms = int((time.time() - t0) * 1000)
        RESULTS.append({"name": name, "passed": False, "ms": ms, "detail": str(e)})
        print(f"  [FAIL] {name} ({ms}ms) — {e}")


# ---------------------------------------------------------------------------
# Test 1: Capability Registry
# ---------------------------------------------------------------------------

def test_capability_registry():
    from capability_registry import CAPABILITIES, get_capability, requires_approval

    def run():
        if len(CAPABILITIES) < 7:
            return False, f"Only {len(CAPABILITIES)} capabilities registered (need 7+)"
        for name in ["voice_io", "app_launcher", "screen_vision", "browser_navigation",
                      "file_operations", "os_control", "system_settings"]:
            cap = get_capability(name)
            if cap is None:
                return False, f"Missing capability: {name}"
        high_risk = [c for c in CAPABILITIES if c.approval_required]
        if len(high_risk) < 2:
            return False, f"Only {len(high_risk)} capabilities require approval (need 2+)"
        return True, f"{len(CAPABILITIES)} capabilities, {len(high_risk)} with approval gate"
    _test("capability_registry", run)


# ---------------------------------------------------------------------------
# Test 2: Voice I/O — mic detection
# ---------------------------------------------------------------------------

def test_voice_mic():
    from voice_io import _find_best_mic

    def run():
        idx = _find_best_mic()
        if idx is None or idx < 0:
            return False, "No input device found"
        import sounddevice as sd
        devices = sd.query_devices()
        name = devices[idx]["name"] if idx < len(devices) else "unknown"
        return True, f"device {idx}: {name}"
    _test("voice_mic_detection", run)


# ---------------------------------------------------------------------------
# Test 3: Whisper transcription
# ---------------------------------------------------------------------------

def test_whisper():
    from voice_io import transcribe_whisper, save_wav
    import numpy as np

    def run():
        import urllib.request
        try:
            urllib.request.urlopen("http://localhost:8081/health", timeout=3)
        except Exception:
            return False, "Whisper service not running on port 8081"

        audio = np.zeros(16000, dtype=np.int16)
        text = transcribe_whisper(audio)
        return True, f"Whisper responded (empty text for silence: '{text}')"
    _test("whisper_transcription", run)


# ---------------------------------------------------------------------------
# Test 4: TTS playback
# ---------------------------------------------------------------------------

def test_tts():
    from voice_io import speak

    def run():
        result = speak("Test")
        if result:
            return True, "TTS played successfully"
        return False, "TTS returned False"
    _test("tts_playback", run)


# ---------------------------------------------------------------------------
# Test 5: Open App
# ---------------------------------------------------------------------------

def test_open_app():
    from open_app import launch

    def run():
        result = launch({"app_name": "notepad"})
        if result and ("opened" in str(result).lower() or "launched" in str(result).lower() or "notepad" in str(result).lower()):
            return True, str(result)[:80]
        return False, f"Unexpected result: {str(result)[:80]}"
    _test("open_app", run)


# ---------------------------------------------------------------------------
# Test 6: File Controller
# ---------------------------------------------------------------------------

def test_file_controller():
    from file_controller import file_controller

    def run():
        result = file_controller({"action": "list", "path": "home"})
        if result and "files" in str(result).lower() or "entries" in str(result).lower() or isinstance(result, dict):
            return True, "File listing returned data"
        return False, f"Unexpected result: {str(result)[:80]}"
    _test("file_controller_list", run)


# ---------------------------------------------------------------------------
# Test 7: Browser Control
# ---------------------------------------------------------------------------

def test_browser_control():
    from browser_control import browser_control

    def run():
        result = browser_control({"action": "list_browsers"})
        return True, f"Browser control responded: {str(result)[:60]}"
    _test("browser_control", run)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_all():
    print("\n  SAGE Embodiment E2E Verification")
    print("  " + "=" * 50)

    test_capability_registry()
    test_voice_mic()
    test_whisper()
    test_tts()
    test_open_app()
    test_file_controller()
    test_browser_control()

    passed = sum(1 for r in RESULTS if r["passed"])
    total = len(RESULTS)
    gate = "PASS" if passed >= 6 else "FAIL"

    print(f"\n  Result: {passed}/{total} passed — Gate: {gate}")
    print(f"  Requirement: 6/7 must pass\n")

    return passed >= 6


if __name__ == "__main__":
    success = run_all()
    sys.exit(0 if success else 1)
