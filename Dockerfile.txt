# Use a base image with Python pre-installed.
FROM python:3.9-slim

# Set environment variables to configure Streamlit.
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0

# Expose the port where the backend will listen.
EXPOSE 8080

# Expose the port where Streamlit will run.
EXPOSE 8501

# Set the working directory inside the container.
WORKDIR /app

# Copy the requirements.txt file and install dependencies.
# This is a key step to ensure that all necessary libraries are installed.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all the application files (your Streamlit app, backend, etc.) into the container.
COPY . .

# Command to run both the backend and Streamlit app.
# The `sh -c` command allows you to run multiple commands in the background.
CMD ["sh", "-c", "python backend.py & streamlit run app.py --server.port=$STREAMLIT_SERVER_PORT --server.address=$STREAMLIT_SERVER_ADDRESS"]