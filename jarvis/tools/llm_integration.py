from .llm_client import LLMClient
from .interaction_logger import log_interaction
from .auto_eval import score_output
from ..tools.prompt_store.prompt_registry import get_prompt
from .replay.snapshot import capture_snapshot
from tools.llm_mapper import resolve_model
import uuid
import os


def call_llm(agent_name: str, prompt_template: str, model_name: str = None, session_id: str = None, workflow_id: str = None, prompt_version: str = None, capture_replay: bool = False):
    session_id = session_id or str(uuid.uuid4())
    workflow_id = workflow_id or "default"
    # resolve model
    resolved = resolve_model(model_name or 'local/default')
    endpoint = resolved.get('endpoint')
    model_tag = resolved.get('model') or resolved.get('runner')

    # instantiate client
    client = LLMClient(provider=resolved.get('runner', 'ollama'), endpoint=endpoint)

    # if prompt_version references a registered prompt, fetch it
    try:
        if prompt_version:
            registered = get_prompt(prompt_version.split('/')[0], prompt_version.split('/')[-1])
            prompt = registered + "\n\n" + prompt_template
        else:
            prompt = prompt_template
    except Exception:
        prompt = prompt_template

    # call LLM
    res = client.send(prompt, model=model_tag)

    # log interaction
    interaction_id = str(uuid.uuid4())
    rowid = log_interaction(
        interaction_id=interaction_id,
        session_id=session_id,
        workflow_id=workflow_id,
        agent_name=agent_name,
        model_name=model_tag,
        input_text=prompt,
        output_text=res.get('text'),
        latency_ms=res.get('latency_ms', 0),
        tokens=res.get('tokens', 0),
        cost_usd=res.get('cost_usd', 0.0),
    )

    # auto-eval
    eval_result = score_output(res.get('text', ''))

    # optional replay capture
    if capture_replay:
        try:
            tool_versions = {"llm": model_tag}
            capture_snapshot(session_id, workflow_id, prompt_version or 'v1', {"prompt": prompt}, tool_versions, orchestration_state={})
        except Exception:
            pass

    return {"interaction_id": interaction_id, "rowid": rowid, "response": res, "eval": eval_result}
