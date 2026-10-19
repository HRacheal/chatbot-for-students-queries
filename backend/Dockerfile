# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Disable Python stdout buffering (IMPORTANT for logs)
ENV PYTHONUNBUFFERED=1

# Set the working directory in the container
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt ./

# Install dependencies
RUN pip install --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# Copy the rest of the backend code
COPY . .

# Expose the port Flask runs on
EXPOSE 8080

# Start Gunicorn
CMD ["gunicorn", "--workers=1", "--threads=1", "--timeout=300", "--bind=0.0.0.0:8080", "app:app"]