FROM python:3.10-slim

# Install system dependencies including ngspice for PySpice and libgomp1 for PaddleOCR
RUN apt-get update && apt-get install -y \
    ngspice \
    libgomp1 \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY . .

# Expose port (Render uses the PORT environment variable, usually defaults to 10000)
EXPOSE 8001

# Command to run the FastAPI app using Render's dynamic PORT (defaults to 8001)
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8001}"]
