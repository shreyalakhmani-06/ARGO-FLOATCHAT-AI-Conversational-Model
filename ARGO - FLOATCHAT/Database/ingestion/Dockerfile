FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the ingestion code
COPY . .

# Make wait-for-it.sh executable
RUN chmod +x wait-for-it.sh

# Command to wait for DB and then run ingestion
CMD ["./wait-for-it.sh", "db:5432", "--", "python", "ingest.py"]
