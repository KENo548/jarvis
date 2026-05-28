#!/usr/bin/env python3
"""
JARVIS Rate Limiter — In-Memory Request Throttling
====================================================
Token bucket rate limiter for API endpoints and agent actions.
Configurable per-agent and per-action-type limits.

Usage (as library):
    from rate_limiter import RateLimiter
    limiter = RateLimiter(max_requests=10, window_seconds=60)
    if limiter.allow("coder_agent"):
        proceed()
    else:
        wait_or_reject()

Usage (standalone):
    python rate_limiter.py check <agent_id> [max_requests] [window_seconds]
    python rate_limiter.py status
"""

import json
import sys
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

STATE_PATH = Path(__file__).resolve().parent.parent / "memory" / "rate-limiter-state.json"


@dataclass
class TokenBucket:
    max_tokens: int
    refill_rate: float  # tokens per second
    tokens: float = field(init=False)
    last_refill: float = field(init=False)

    def __post_init__(self):
        self.tokens = float(self.max_tokens)
        self.last_refill = time.time()

    def allow(self) -> bool:
        now = time.time()
        elapsed = now - self.last_refill
        self.tokens = min(self.max_tokens, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now

        if self.tokens >= 1:
            self.tokens -= 1
            return True
        return False


class RateLimiter:
    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.refill_rate = max_requests / window_seconds
        self.buckets: dict[str, TokenBucket] = defaultdict(
            lambda: TokenBucket(max_requests, self.refill_rate)
        )
        self._load_state()

    def allow(self, key: str) -> bool:
        allowed = self.buckets[key].allow()
        self._save_state()
        return allowed

    def status(self) -> dict:
        return {
            key: {
                "tokens_remaining": int(b.tokens),
                "max_tokens": b.max_tokens,
            }
            for key, b in self.buckets.items()
        }

    def _save_state(self) -> None:
        state = {}
        for key, bucket in self.buckets.items():
            state[key] = {
                "tokens": bucket.tokens,
                "last_refill": bucket.last_refill,
                "max_tokens": bucket.max_tokens,
            }
        STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        STATE_PATH.write_text(json.dumps(state))

    def _load_state(self) -> None:
        if STATE_PATH.exists():
            try:
                state = json.loads(STATE_PATH.read_text())
                for key, data in state.items():
                    bucket = TokenBucket(
                        max_tokens=data["max_tokens"],
                        refill_rate=self.refill_rate,
                    )
                    bucket.tokens = data["tokens"]
                    bucket.last_refill = data["last_refill"]
                    self.buckets[key] = bucket
            except (json.JSONDecodeError, KeyError):
                pass


# Default limiter instance
_default = RateLimiter()


def check_rate(agent_id: str, max_requests: int = 10, window: int = 60) -> dict:
    limiter = RateLimiter(max_requests, window)
    allowed = limiter.allow(agent_id)
    return {
        "agent_id": agent_id,
        "allowed": allowed,
        "max_requests": max_requests,
        "window_seconds": window,
        "status": limiter.status().get(agent_id, {})
    }


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1]

    if command == "check":
        agent_id = sys.argv[2] if len(sys.argv) > 2 else "default"
        max_req = int(sys.argv[3]) if len(sys.argv) > 3 else 10
        window = int(sys.argv[4]) if len(sys.argv) > 4 else 60
        result = check_rate(agent_id, max_req, window)
        print(json.dumps(result, indent=2))
        sys.exit(0 if result["allowed"] else 1)

    elif command == "status":
        print(json.dumps(_default.status(), indent=2))

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
