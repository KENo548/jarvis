import time
import json
import requests


class LLMError(Exception):
    pass


class TimeoutError(LLMError):
    pass


class RateLimitError(LLMError):
    pass


class InvalidResponseError(LLMError):
    pass


class AuthenticationError(LLMError):
    pass


# Minimal cost table (USD per 1k tokens) — extend per-provider
COST_TABLE = {
    "ollama": 0.0001,
}


class LLMClient:
    def __init__(self, provider="ollama", endpoint=None, api_key=None, timeout=30):
        self.provider = provider
        self.endpoint = endpoint
        self.api_key = api_key
        self.timeout = timeout

    def _estimate_cost(self, tokens: int) -> float:
        per_k = COST_TABLE.get(self.provider, 0.0)
        return (tokens / 1000.0) * per_k

    def send(self, prompt: str, model: str = "default", max_retries: int = 3, backoff_base: float = 0.5):
        """Send a prompt to the configured LLM provider with retry/backoff.

        Returns a dict: { text, tokens, latency_ms, cost_usd }
        """
        attempt = 0
        start = time.time()
        while True:
            try:
                attempt += 1
                if not self.endpoint:
                    # Offline / mock mode — deterministic lightweight reply
                    text = f"[MOCK RESPONSE] received {len(prompt)} chars"
                    tokens = max(1, len(prompt) // 4)
                    latency_ms = int((time.time() - start) * 1000)
                    cost = self._estimate_cost(tokens)
                    return {"text": text, "tokens": tokens, "latency_ms": latency_ms, "cost_usd": cost}

                headers = {"Content-Type": "application/json"}
                if self.api_key:
                    headers["Authorization"] = f"Bearer {self.api_key}"

                payload = {"model": model, "prompt": prompt}
                resp = requests.post(self.endpoint, headers=headers, json=payload, timeout=self.timeout)

                if resp.status_code == 401:
                    raise AuthenticationError("authentication failed")
                if resp.status_code == 429:
                    raise RateLimitError("rate limited")
                if resp.status_code >= 500:
                    raise LLMError(f"server error {resp.status_code}")

                try:
                    data = resp.json()
                except Exception:
                    raise InvalidResponseError("invalid json in response")

                text = data.get("text") or data.get("output") or ""
                tokens = int(data.get("tokens", max(1, len(text) // 4)))
                latency_ms = int((time.time() - start) * 1000)
                cost = self._estimate_cost(tokens)
                return {"text": text, "tokens": tokens, "latency_ms": latency_ms, "cost_usd": cost}

            except requests.Timeout as e:
                if attempt >= max_retries:
                    raise TimeoutError(str(e))
            except RateLimitError:
                if attempt >= max_retries:
                    raise
            except AuthenticationError:
                raise
            except Exception:
                if attempt >= max_retries:
                    raise

            # exponential backoff
            sleep = backoff_base * (2 ** (attempt - 1)) + (0.1 * (attempt - 1))
            time.sleep(sleep)
