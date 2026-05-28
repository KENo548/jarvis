import subprocess
import time
import requests
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from workflows.langgraph.orchestrator_graph import build_graph


LLM_URL = os.environ.get('LOCAL_LLM_URL', 'http://127.0.0.1:7860')
MCP_BRIDGE = os.environ.get('MCP_BRIDGE', 'http://127.0.0.1:8099')


def start_llm_process():
    proc = subprocess.Popen([sys.executable, "services/local_llm_server.py"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    # wait for server to become responsive
    for _ in range(20):
        try:
            r = requests.post(f"{LLM_URL}/generate", json={"prompt": "health check"}, timeout=1)
            if r.status_code == 200:
                return proc
        except Exception:
            time.sleep(0.5)
    raise RuntimeError('Local LLM did not start in time')


def stop_process(proc: subprocess.Popen):
    try:
        proc.terminate()
        proc.wait(timeout=3)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


def run_graph():
    graph = build_graph()
    state = graph.invoke({'task': 'Demo: build hello world'})

    artifact = state.get('artifact', {'path': 'github-repos/demo/hello.py', 'content': 'print("Hello, world")'})
    out_path = os.path.join('github-repos', 'demo')
    os.makedirs(out_path, exist_ok=True)
    file_path = os.path.join(out_path, 'hello.py')
    with open(file_path, 'w', encoding='utf-8') as fh:
        fh.write(artifact['content'])

    notes = ''
    try:
        r = requests.get(f"{MCP_BRIDGE}/health", timeout=2)
        notes += f"mcp_bridge={r.status_code}; "
    except Exception as e:
        notes += f"mcp_bridge_error={e}; "

    try:
        exec_proc = subprocess.run([sys.executable, file_path], capture_output=True, text=True, timeout=5)
        out = exec_proc.stdout + exec_proc.stderr
        notes += f"exec_returncode={exec_proc.returncode}; output={out.strip()}"
        state['qa'] = {
            'passed': bool(state.get('qa', {}).get('passed')) and (exec_proc.returncode == 0),
            'notes': notes,
        }
    except Exception as e:
        state['qa'] = {'passed': False, 'notes': notes + f"exec_error={e}"}

    state['artifact'] = artifact
    return state


def main():
    llm_proc = start_llm_process()
    try:
        res = run_graph()
        print('Graph result:')
        print(res)
    finally:
        stop_process(llm_proc)


if __name__ == '__main__':
    main()
