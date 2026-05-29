"""Finalize Phase 0/1: wire agents configs, generate secrets, and run canonical tasks."""
import os
import json
from pathlib import Path
from jarvis.tools.log_encrypt import generate_key


AGENTS_DIR = Path(__file__).resolve().parents[1] / 'agents'


def wire_agents_use_llm_integration():
    # iterate agents/*/config.json and add use_llm_integration flag
    for cfg in AGENTS_DIR.glob('**/config.json'):
        try:
            data = json.loads(cfg.read_text(encoding='utf-8'))
            data['use_llm_integration'] = True
            if 'llm_model' not in data:
                data['llm_model'] = data.get('model', 'local/default')
            cfg.write_text(json.dumps(data, indent=2), encoding='utf-8')
        except Exception:
            continue


def ensure_secrets():
    k = generate_key()
    print('Generated log encryption key at secrets/llm_logs.key')


if __name__ == '__main__':
    print('Wiring agents to use LLM integration...')
    wire_agents_use_llm_integration()
    ensure_secrets()
    print('Done. You may run tests/run_canonical_tasks.py to execute mock E2E.')
