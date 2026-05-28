#!/usr/bin/env python3
import re
from pathlib import Path

ROOT = Path('c:/jarvis')
PAT = re.compile(r"(anthropic/[\w\-\.]+|google/gemini[\w\-\.]*|claude[-_/\w\.]+|openai/[\w\-\.]+)")

changed = []
for p in (ROOT / '_opencode').rglob('*.md'):
    s = p.read_text(encoding='utf-8')
    if PAT.search(s):
        new = PAT.sub('local/llama.cpp', s)
        p.write_text(new, encoding='utf-8')
        changed.append(str(p))

print('Replaced model strings in', len(changed), 'files')
for c in changed:
    print(c)
