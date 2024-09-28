FROM python:3.9-slim

WORKDIR /app

RUN apt-get update && apt-get install -y ffmpeg
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY .env .
COPY api/ api/

WORKDIR /app/api

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 28000

CMD ["python", "main.py"]