# Use a slim Python 3.9 image as the base
FROM python:3.9-slim-buster

# Set the working directory in the container
WORKDIR /app

COPY requirements.txt .
# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the analysis directory content into the container
COPY .env .
COPY analysis/ analysis/

# Set the working directory to the analysis folder
WORKDIR /app/analysis
RUN pip install --no-cache-dir -r requirements.txt

# Run the main Python script
CMD ["python", "main.py"]