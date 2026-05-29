import os
import json
from jarvis.tools.llm_client import LLMClient
from jarvis.tools.interaction_logger import pii_redact, log_interaction
from jarvis.tools.prompt_store.prompt_registry import register_prompt, get_prompt, diff_versions
from jarvis.tools.replay.snapshot import capture_snapshot
from jarvis.tools.export_pipeline import validate_jsonl, create_correction_pairs


def test_pii_redaction():
    s = "Contact me at a@b.com or +1 555-123-4567. SSN 123-45-6789."
    r = pii_redact(s)
    assert "REDACTED" in r


def test_prompt_registry(tmp_path):
    name = "testprompt"
    v1 = register_prompt(name, "first version")
    v2 = register_prompt(name, "second version")
    p = get_prompt(name)
    assert "second version" in p
    # diff must run
    files = __import__("jarvis.tools.prompt_store.prompt_registry", fromlist=["*"]).list_versions(name)
    if len(files) >= 2:
        d = diff_versions(name, files[-2], files[-1])
        assert isinstance(d, str)


def test_llm_client_and_logging():
    client = LLMClient(endpoint=None)
    res = client.send("hello world")
    assert "MOCK RESPONSE" in res["text"]
    rowid = log_interaction(
        interaction_id="i1",
        session_id="s1",
        workflow_id="w1",
        agent_name="tester",
        model_name="mock",
        input_text="hello",
        output_text=res["text"],
        latency_ms=res["latency_ms"],
        tokens=res["tokens"],
        cost_usd=res["cost_usd"],
    )
    assert rowid > 0


def test_snapshot_and_export(tmp_path):
    snap = capture_snapshot("s1", "w1", "v1", {"a": 1}, {"tool": "0.1"})
    assert os.path.exists(snap)
    # test export validation on a small jsonl
    src = tmp_path / "src.jsonl"
    src.write_text(json.dumps({"instruction": "do","input": "x","output": "y","correction": "z"}) + "\n")
    report = validate_jsonl(str(src))
    assert report["count"] == 1
    out = tmp_path / "out.jsonl"
    written = create_correction_pairs(str(src), str(out))
    assert written == 1


if __name__ == "__main__":
    test_pii_redaction()
    test_prompt_registry(None)
    test_llm_client_and_logging()
    import pathlib
    p = pathlib.Path.cwd()
    print("OK", p)
