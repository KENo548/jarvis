import os
import json
import difflib
import datetime

BASE = os.path.join(os.path.dirname(__file__))


def _ensure_dir(name: str):
    d = os.path.join(BASE, name)
    os.makedirs(d, exist_ok=True)
    return d


def register_prompt(name: str, content: str) -> str:
    d = _ensure_dir(name)
    ts = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    filename = os.path.join(d, f"{ts}.md")
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)
    return ts


def list_versions(name: str):
    d = os.path.join(BASE, name)
    if not os.path.exists(d):
        return []
    files = sorted(os.listdir(d))
    return files


def get_prompt(name: str, version: str = None) -> str:
    d = os.path.join(BASE, name)
    if not os.path.exists(d):
        raise FileNotFoundError("prompt not found")
    files = sorted(os.listdir(d))
    if not files:
        raise FileNotFoundError("no versions")
    if version is None:
        filename = files[-1]
    else:
        filename = version if version in files else None
        if filename is None:
            raise FileNotFoundError("version not found")
    path = os.path.join(d, filename)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def diff_versions(name: str, v1: str, v2: str) -> str:
    d = os.path.join(BASE, name)
    p1 = os.path.join(d, v1)
    p2 = os.path.join(d, v2)
    if not os.path.exists(p1) or not os.path.exists(p2):
        raise FileNotFoundError("version missing")
    a = open(p1, encoding="utf-8").read().splitlines()
    b = open(p2, encoding="utf-8").read().splitlines()
    return "\n".join(difflib.unified_diff(a, b, fromfile=v1, tofile=v2))


def rollback(name: str, version: str) -> str:
    # create a new version identical to chosen version, marking as rollback
    content = get_prompt(name, version)
    ts = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    d = _ensure_dir(name)
    filename = os.path.join(d, f"rollback-{ts}.md")
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)
    return filename
