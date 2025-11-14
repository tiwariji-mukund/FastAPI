FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

COPY deployer/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code (excluding deployer folder and unnecessary files)
COPY common/ ./common/
COPY server/ ./server/
COPY services/ ./services/
COPY main.py .
COPY run.py .

# Expose the port (default from config is 8080)
EXPOSE 8080

# Run the application
CMD ["python", "run.py", "--log-level", "warning"]

