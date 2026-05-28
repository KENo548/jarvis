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
    "ollama/llama3.2": {
        "type": "ollama",
        "runner": "ollama",
        "endpoint": "http://localhost:11434",
        "model": "llama3.2:latest",
        "notes": "Local LLM via Ollama. Free, private, runs offline."
    },
    "ollama/nomic-embed-text": {
        "type": "ollama",
        "runner": "ollama",
        "endpoint": "http://localhost:11434",
        "model": "nomic-embed-text:latest",
        "notes": "Local embedding model via Ollama."
    },
    "openai/gpt-4o": {
        "type": "cloud",
        "runner": "openai",
        "endpoint": "https://api.openai.com/v1",
        "model": "gpt-4o",
        "notes": "OpenAI GPT-4o. Requires OPENAI_API_KEY."
    },
    "openai/gpt-4o-mini": {
        "type": "cloud",
        "runner": "openai",
        "endpoint": "https://api.openai.com/v1",
        "model": "gpt-4o-mini",
        "notes": "OpenAI GPT-4o Mini. Cheaper fallback."
    },
    "local/llama.cpp": {
        "type": "local",
        "runner": "llama.cpp",
        "endpoint": "http://localhost:7860",
        "notes": "Run text-generation-webui or a llama.cpp HTTP bridge locally"
    },
    "local/default": {
        "type": "local",
        "runner": "ollama",
        "endpoint": "http://localhost:11434",
        "model": "llama3.2:latest"
    }
}

def resolve_model(model_name: str):
    return MAPPER.get(model_name, MAPPER['local/default'])

if __name__ == '__main__':
    import sys, json
    m = sys.argv[1] if len(sys.argv) > 1 else 'local/default'
    print(json.dumps(resolve_model(m), indent=2))
