---
name: jarvis-python
description: Python development with Django, FastAPI, type safety, async patterns, and testing.
license: MIT
metadata:
  domain: engineering
  complexity: medium
---

# Python Development

## What I do

- Python project structure
- Django web applications
- FastAPI REST APIs
- Async Python patterns
- Type hints and mypy
- Testing with pytest

## When to use me

Use this skill for Python development, Django, FastAPI, async patterns, or Python testing.

## Patterns

### FastAPI
```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class User(BaseModel):
    name: str
    email: str

@app.post("/users")
async def create_user(user: User):
    return {"id": 1, **user.dict()}
```

### Django Model
```python
from django.db import models

class User(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    
    class Meta:
        ordering = ['-created_at']
```

### Async Pattern
```python
import asyncio

async def fetch_data():
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()
```

## Anti-patterns

- Don't use `*` imports
- Don't skip type hints
- Don't ignore virtual environments
- Don't use mutable default arguments

---
*Source: Extracted from wshobson python-development agents*
