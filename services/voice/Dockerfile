FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
ENV WHISPER_MODEL=${WHISPER_MODEL:-base}

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

RUN pip install --no-cache-dir fastapi uvicorn python-multipart openai-whisper numpy

RUN python -c "import whisper; whisper.load_model('tiny')" && rm -rf /root/.cache/whisper

WORKDIR /app

COPY app.py .

EXPOSE 8081

CMD ["python", "app.py"]
