FROM python:3.9-slim

WORKDIR /app

RUN apt-get update && apt-get install -y ffmpeg
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY .env .
COPY download/ download/

WORKDIR /app/download

RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "main.py"]