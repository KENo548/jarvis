# OLLAMA Runbook (minimal)

Install & run

1. Install Ollama per project instructions for your OS.
2. Run the server locally and note the HTTP endpoint (e.g., `http://localhost:11434`).

Auth & endpoints

- Use API keys where available. Store keys in your secret store and never commit them.
- Configure `LLMClient(endpoint=..., api_key=...)` in `jarvis/tools/llm_client.py`.

Model management

- Pin model versions for production runs. Record model name + SHA/version in prompts and replay snapshots.
- Use prompt versioning and a controlled rollout (canary -> full) with rollback on regressions.

Rate limits & timeouts

- Set a conservative request timeout (e.g., 20–60s). Implement retries with exponential backoff (3 attempts recommended).
- Monitor 429 rates and set alerts if they increase.

Troubleshooting

- 401: check API key and key rotation.
- 429: implement spikes throttling and backoff.
- 5xx: treat as transient, retry with backoff and alert on sustained failures.

Observability

- Record model_name, model_version, prompt_version, token usage, latency_ms and cost_usd per call.
- Keep a local canary test suite of 5–10 calls to validate a deployed model version.

Security

- Redact PII before writing to logs. Rotate keys and enforce RBAC around logs and exports.
# Ollama Operations Runbook

## Installation

### Windows
```powershell
# Download from https://ollama.com/download/windows
# Or use winget:
winget install Ollama.Ollama
```

### macOS
```bash
brew install ollama
# Or download from https://ollama.com/download/mac
```

### Linux
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

## Model Management

```bash
# Pull a model
ollama pull llama3.2
ollama pull nomic-embed-text

# List installed models
ollama list

# Remove a model
ollama rm llama3.2

# Check model size
ollama show llama3.2
```

## Models for SAGE

| Model | Purpose | Size |
|-------|---------|------|
| `llama3.2` | General reasoning, chat, instruction following | ~2 GB |
| `nomic-embed-text` | Text embeddings for memory retrieval | ~274 MB |

## Endpoint Reference

All endpoints run on `localhost:11434` by default.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/generate` | POST | Single-turn text generation |
| `/api/chat` | POST | Multi-turn chat completion |
| `/api/tags` | GET | List installed models |
| `/api/show` | POST | Show model info |
| `/api/pull` | POST | Pull a model |
| `/api/embeddings` | POST | Generate embeddings |

### Example: Generate
```bash
curl http://localhost:11434/api/generate -d '{
  "model": "llama3.2",
  "prompt": "What is 2+2?",
  "stream": false
}'
```

### Example: Chat
```bash
curl http://localhost:11434/api/chat -d '{
  "model": "llama3.2",
  "messages": [{"role": "user", "content": "Hello"}],
  "stream": false
}'
```

## Authentication

Local Ollama requires **no authentication**. The server binds to `localhost:11434` and is only accessible from the local machine by default.

To expose it on the network (not recommended for production):
```bash
OLLAMA_HOST=0.0.0.0:11434 ollama serve
```

## Rate Limits

Local Ollama has **no rate limits**. However, response latency depends on:
- Model size vs available VRAM/RAM
- Concurrent request count
- Context length

For production use, implement application-level throttling if needed.

## Troubleshooting

### Ollama not running
```bash
# Check if the service is up
curl http://localhost:11434/api/tags

# Start the server
ollama serve
```

### Model not found
```bash
# List installed models
ollama list

# Pull the missing model
ollama pull llama3.2
```

### Slow responses
- Check GPU availability: `nvidia-smi` (NVIDIA) or `rocm-smi` (AMD)
- Reduce context length in requests
- Use a smaller model (e.g., `llama3.2:1b` instead of `llama3.2`)
- Ensure sufficient RAM/VRAM for the model size

### Out of memory
```bash
# Check available memory
free -h  # Linux
vm_stat  # macOS

# Use a quantized or smaller model variant
ollama pull llama3.2:1b
```

## Model Upgrade Procedure

1. Pull the new version:
   ```bash
   ollama pull llama3.2
   ```
2. Verify it's available:
   ```bash
   ollama list
   ```
3. Test with a simple prompt:
   ```bash
   curl http://localhost:11434/api/generate -d '{"model":"llama3.2","prompt":"test","stream":false}'
   ```
4. Update `llm_client.py` provider config if the model tag changed
5. Remove the old version:
   ```bash
   ollama rm llama3.2:old-tag
   ```

## Health Check Commands

```bash
# Quick health check
curl -s http://localhost:11434/api/tags | python -m json.tool

# Check specific model
curl -s http://localhost:11434/api/show -d '{"name":"llama3.2"}' | python -m json.tool

# Test generation
curl -s http://localhost:11434/api/generate -d '{"model":"llama3.2","prompt":"ping","stream":false}' | python -m json.tool
```
