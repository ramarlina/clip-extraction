FROM python:3.9-slim-buster

WORKDIR /app

RUN apt-get update && \
    apt-get install -y ffmpeg && \
    apt-get install -y git && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY .env .
COPY transcription/ transcription/

WORKDIR /app/transcription
RUN pip install --no-cache-dir -r requirements.txt

RUN chmod +x entrypoint.sh

ENTRYPOINT ["./entrypoint.sh"]