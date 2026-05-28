FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN pip install --no-cache-dir fastapi uvicorn python-multipart openai-whisper numpy

COPY app.py .

EXPOSE 8081

CMD ["python", "app.py"]
