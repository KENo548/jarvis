import asyncio
import threading
import json
import sys
import traceback
from pathlib import Path

from config.llm_client import chat_completion, format_model_label, get_llm_settings, list_models, search_models
sys.path.append(str(Path(__file__).resolve().parent.parent))
from tools.embodiment.voice_io import voice_loop
from ui import JarvisUI

# Import the Soul-Body protocol
from protocols.jarvis_soul import JarvisSoul
from protocols.types import Intent, SoulState


def get_base_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent


BASE_DIR        = get_base_dir()
API_CONFIG_PATH = BASE_DIR / "config" / "api_keys.json"


def _read_runtime_config() -> dict:
    if not API_CONFIG_PATH.exists():
        return {}
    try:
        with open(API_CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _write_runtime_config(cfg: dict) -> None:
    API_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(API_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=4)


class JarvisLive:

    def __init__(self, ui: JarvisUI):
        self.ui             = ui
        self._is_speaking   = False
        self._speaking_lock = threading.Lock()
        self.ui.on_text_command = self._on_text_command
        self._conv_history: list[tuple[str, str]] = []

        llm = get_llm_settings()
        self._provider = llm.get("provider", "nvidia")
        self._live_model = llm.get("model") or "meta/llama-3.1-70b-instruct"

        # Initialize the Soul
        self._soul = JarvisSoul()
        self._soul.set_state_callback(self._on_soul_state)
        self._soul.set_feedback_callback(self._on_soul_feedback)
        print("[JARVIS] Initializing soul...")
        self._soul.initialize()
        print("[JARVIS] Soul ready.")

    def _on_soul_state(self, state: SoulState) -> None:
        """Handle soul state changes → update HUD."""
        state_map = {
            SoulState.IDLE: "LISTENING",
            SoulState.LISTENING: "LISTENING",
            SoulState.THINKING: "THINKING",
            SoulState.ROUTING: "PROCESSING",
            SoulState.EXECUTING: "PROCESSING",
            SoulState.SPEAKING: "SPEAKING",
            SoulState.ERROR: "ERROR",
        }
        ui_state = state_map.get(state, "LISTENING")
        self.ui.set_state(ui_state)

    def _on_soul_feedback(self, message: str, level: str) -> None:
        """Handle soul feedback messages → show in HUD log."""
        prefix = {"info": "SYS", "warning": "WARN", "error": "ERR", "success": "OK"}
        tag = prefix.get(level, "SYS")
        self.ui.write_log(f"{tag}: {message}")

    def _append_history(self, role: str, text: str):
        t = (text or "").strip()
        if not t:
            return
        self._conv_history.append((role, text))
        if len(self._conv_history) > 40:
            self._conv_history = self._conv_history[-40:]

    def _handle_slash_command(self, text: str) -> bool:
        raw = (text or "").strip()
        if not raw.startswith("/"):
            return False

        parts = raw.split()
        cmd = parts[0].lower()

        if cmd not in {"/model", "/provider", "/soul", "/caps"}:
            self.ui.write_log("SYS: Unknown slash command. Use /model, /provider, /soul, or /caps.")
            return True

        cfg = _read_runtime_config()

        if cmd == "/provider":
            if len(parts) == 1:
                self.ui.write_log(
                    f"SYS: provider={self._provider} model={self._live_model} | openai | nvidia | opencode_zen"
                )
                return True

            provider_query = " ".join(parts[1:]).strip().lower()
            provider_map = {
                "openai": "openai", "nvidia": "nvidia", "nv": "nvidia",
                "opencode": "opencode_zen", "zen": "opencode_zen", "opencode_zen": "opencode_zen",
            }
            new_provider = provider_map.get(provider_query)
            if not new_provider:
                self.ui.write_log("SYS: Invalid provider. Use openai, nvidia, or opencode_zen.")
                return True

            key_map = {"openai": "openai_api_key", "nvidia": "nvidia_api_key", "opencode_zen": "opencode_zen_api_key"}
            if not cfg.get(key_map.get(new_provider, "")):
                self.ui.write_log(f"SYS: Missing API key for {new_provider}.")
                return True

            cfg["llm_provider"] = new_provider
            _write_runtime_config(cfg)
            self._provider = new_provider
            self.ui.write_log(f"SYS: Switched to {new_provider}")
            return True

        if cmd == "/model":
            if len(parts) == 1:
                self.ui.write_log(f"SYS: model={self._live_model}")
                return True
            new_model = " ".join(parts[1:]).strip()
            cfg["llm_model"] = new_model
            _write_runtime_config(cfg)
            self._live_model = new_model
            self.ui.write_log(f"SYS: Model set to {new_model}")
            return True

        if cmd == "/soul":
            status = self._soul.get_status()
            self.ui.write_log(f"SOUL: state={status['state']} caps={status['capabilities_count']} v{status['version']}")
            return True

        if cmd == "/caps":
            caps = self._soul.list_capabilities()
            lines = [f"  {c['name']} ({c['risk']})" for c in caps[:10]]
            self.ui.write_log(f"SOUL: {len(caps)} tools\n" + "\n".join(lines))
            return True

        return False

    def _on_text_command(self, text: str):
        if self._handle_slash_command(text):
            return

        self._append_history("user", text)
        print(f"[JARVIS] Text: {text[:80]}")

        # Route through the Soul protocol
        intent = Intent(text=text, intent_type="chat", source="text_input")
        try:
            result = self._soul.process(intent)
            response = result.response
        except Exception as exc:
            response = f"Error: {exc}"
            print(f"[JARVIS] Soul error: {exc}")
            traceback.print_exc()

        self._append_history("assistant", response)
        self.ui.write_log(f"Jarvis: {response}")
        print(f"[JARVIS] Response: {response[:80]}")

    def set_speaking(self, value: bool):
        with self._speaking_lock:
            self._is_speaking = value
        if value:
            self.ui.set_state("SPEAKING")
        elif not self.ui.muted:
            self.ui.set_state("LISTENING")

    def speak(self, text: str):
        self.ui.write_log(f"Jarvis: {text}")

    def speak_error(self, tool_name: str, error: str):
        short = str(error)[:120]
        self.ui.write_log(f"ERR: {tool_name} — {short}")

    async def run(self):
        def agent_fn(text: str) -> str:
            self._append_history("user", text)
            print(f"[JARVIS] Voice: {text[:80]}")

            # Route through the Soul protocol
            intent = Intent(text=text, intent_type="voice", source="voice")
            try:
                result = self._soul.process(intent)
                response = result.response
            except Exception as exc:
                response = f"Error: {exc}"
                print(f"[JARVIS] Voice soul error: {exc}")
                traceback.print_exc()

            self._append_history("assistant", response)
            self.ui.write_log(f"Jarvis: {response}")
            print(f"[JARVIS] Voice response: {response[:80]}")
            return response

        self.ui.set_state("LISTENING")
        self.ui.write_log("SYS: JARVIS online. Soul connected. Listening...")
        print("[JARVIS] Starting voice loop...")
        try:
            await asyncio.to_thread(voice_loop, agent_fn, continuous=True)
        except Exception as exc:
            print(f"[JARVIS] Voice loop failed: {exc}")
            traceback.print_exc()
            self.ui.write_log(f"SYS: Voice error: {exc}")

def main():
    ui = JarvisUI("face.png")

    def runner():
        ui.wait_for_api_key()
        jarvis = JarvisLive(ui)
        try:
            asyncio.run(jarvis.run())
        except KeyboardInterrupt:
            print("\nShutting down...")
            jarvis._soul.shutdown()

    threading.Thread(target=runner, daemon=True).start()
    ui.root.mainloop()

if __name__ == "__main__":
    main()
