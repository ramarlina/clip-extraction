# Use a slim Python 3.9 image as the base
FROM python:3.9-slim-buster

# Set the working directory in the container
WORKDIR /app

# Install system dependencies, including FFmpeg
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    apt-get install -y build-essential cmake && \
    rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container
COPY requirements.txt .
# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install dlib
# Copy the clip_generation directory content into the container
COPY .env .
COPY clip_generation/ clip_generation/

# Set the working directory to the clip_generation folder
WORKDIR /app/clip_generation
RUN pip install --no-cache-dir -r requirements.txt

# Run the main Python script
CMD ["python", "main.py"]