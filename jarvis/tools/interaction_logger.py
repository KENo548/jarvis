import os
import re
import json
import sqlite3
import datetime
from typing import Optional


DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'logs', 'interactions.db')


def _ensure_db():
    db_dir = os.path.dirname(DB_PATH)
    os.makedirs(db_dir, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('''
    CREATE TABLE IF NOT EXISTS interactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        interaction_id TEXT,
        session_id TEXT,
        workflow_id TEXT,
        timestamp TEXT,
        agent_name TEXT,
        model_name TEXT,
        input_text TEXT,
        assembled_context TEXT,
        retrieved_memories TEXT,
        tool_calls TEXT,
        tool_outputs TEXT,
        reasoning_trace TEXT,
        output_text TEXT,
        latency_ms INTEGER,
        tokens INTEGER,
        cost_usd REAL,
        auto_eval TEXT,
        human_feedback TEXT,
        correction TEXT,
        retry_count INTEGER,
        was_edited INTEGER,
        was_abandoned INTEGER,
        followup_prompt TEXT,
        success_score REAL
    )
    ''')
    conn.commit()
    conn.close()


PII_PATTERNS = [
    (re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"), "<REDACTED_EMAIL>"),
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "<REDACTED_SSN>"),
    (re.compile(r"\b(?:\d[ -]*?){13,16}\b"), "<REDACTED_CARD>"),
    (re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"), "<REDACTED_IP>"),
    (re.compile(r"\b\+?\d[\d ()-]{7,}\d\b"), "<REDACTED_PHONE>"),
    (re.compile(r"(?i)api[_-]?key\s*[:=]\s*[A-Za-z0-9\-_.]+"), "<REDACTED_API_KEY>")
]


def pii_redact(text: Optional[str]) -> Optional[str]:
    if text is None:
        return None
    s = text
    for pattern, repl in PII_PATTERNS:
        s = pattern.sub(repl, s)
    return s


def log_interaction(
    interaction_id: str,
    session_id: str,
    workflow_id: str,
    agent_name: str,
    model_name: str,
    input_text: str,
    output_text: str,
    latency_ms: int,
    tokens: int,
    cost_usd: float,
    assembled_context: Optional[dict] = None,
    retrieved_memories: Optional[list] = None,
    tool_calls: Optional[list] = None,
    tool_outputs: Optional[list] = None,
    reasoning_trace: Optional[str] = None,
    auto_eval: Optional[dict] = None,
    human_feedback: Optional[dict] = None,
    correction: Optional[str] = None,
    retry_count: int = 0,
    was_edited: bool = False,
    was_abandoned: bool = False,
    followup_prompt: Optional[str] = None,
    success_score: Optional[float] = None,
):
    _ensure_db()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    ts = datetime.datetime.utcnow().isoformat() + 'Z'
    cur.execute(
        '''INSERT INTO interactions (
           interaction_id, session_id, workflow_id, timestamp, agent_name, model_name,
           input_text, assembled_context, retrieved_memories, tool_calls, tool_outputs,
           reasoning_trace, output_text, latency_ms, tokens, cost_usd, auto_eval,
           human_feedback, correction, retry_count, was_edited, was_abandoned,
           followup_prompt, success_score)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
        (
            interaction_id,
            session_id,
            workflow_id,
            ts,
            agent_name,
            model_name,
            pii_redact(input_text),
            json.dumps(assembled_context or {}),
            json.dumps(retrieved_memories or []),
            json.dumps(tool_calls or []),
            json.dumps(tool_outputs or []),
            pii_redact(reasoning_trace),
            pii_redact(output_text),
            int(latency_ms),
            int(tokens),
            float(cost_usd),
            json.dumps(auto_eval or {}),
            json.dumps(human_feedback or {}),
            pii_redact(correction),
            int(retry_count),
            int(bool(was_edited)),
            int(bool(was_abandoned)),
            pii_redact(followup_prompt),
            float(success_score) if success_score is not None else None,
        ),
    )
    conn.commit()
    rowid = cur.lastrowid
    conn.close()
    return rowid
