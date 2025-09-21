# Use a Python base image.
FROM python:3.9-slim

# Set working directory.
WORKDIR /app

# Expose the ports. Cloud Run will route traffic to $PORT.
# The backend will run on a separate, internal port.
ENV PORT 8080
EXPOSE $PORT
EXPOSE 8000

# Copy and install dependencies first for caching.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all your application files into the container.
COPY . .

# Run both the backend and Streamlit app.
# The backend runs on port 8000 and is accessible from within the container.
# The Streamlit app runs on the port provided by Cloud Run.
CMD ["sh", "-c", "python backend.py --host 0.0.0.0 --port 8000 & streamlit run app.py --server.port=$PORT --server.address=0.0.0.0"]