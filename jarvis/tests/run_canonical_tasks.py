import os
import json
from jarvis.tools.llm_integration import call_llm

TASKS_PATH = os.path.join(os.path.dirname(__file__), 'canonical_tasks.jsonl')


def run_all(mock=True):
    with open(TASKS_PATH, encoding='utf-8') as f:
        lines = f.read().splitlines()
    results = []
    for line in lines:
        task = json.loads(line)
        instruction = task.get('instruction')
        expected = task.get('expected_contains')
        # force mock mode by not resolving to an external endpoint
        out = call_llm('verifier', instruction, model_name=None, prompt_version=None, capture_replay=True)
        label = 'pass' if expected and expected in out['response']['text'] else 'warn'
        results.append({'id': task.get('id'), 'name': task.get('name'), 'label': label, 'eval': out['eval']})
    return results


if __name__ == '__main__':
    res = run_all()
    for r in res:
        print(r)
