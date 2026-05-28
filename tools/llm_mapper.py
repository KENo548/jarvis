"""
LLM Mapper

Maps abstract model names in agent configs to local runner identifiers
or command lines. Agents should use the abstract `model` field (e.g.
"local/llama.cpp") and this mapper resolves it to an executable or
endpoint.

Usage:
    from tools.llm_mapper import resolve_model
    runner = resolve_model('local/llama.cpp')
    # runner -> {"type": "local", "runner": "llama.cpp", ...}

This file is intentionally simple and local-only.
"""
MAPPER = {
    "local/llama.cpp": {
        "type": "local",
        "runner": "llama.cpp",
        "endpoint": "http://localhost:7860",  # text-generation-webui default
        "notes": "Run text-generation-webui or a llama.cpp HTTP bridge locally"
    },
    "local/text-generation-webui": {
        "type": "local",
        "runner": "text-generation-webui",
        "endpoint": "http://localhost:7860"
    },
    "local/default": {
        "type": "local",
        "runner": "text-generation-webui",
        "endpoint": "http://localhost:7860"
    }
}

def resolve_model(model_name: str):
    return MAPPER.get(model_name, MAPPER['local/default'])

if __name__ == '__main__':
    import sys, json
    m = sys.argv[1] if len(sys.argv) > 1 else 'local/default'
    print(json.dumps(resolve_model(m), indent=2))
