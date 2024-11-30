# Use a Python base image
FROM gcr.io/google-appengine/python

# Install git
RUN apt-get update && \
    apt-get install -y git && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy local code to the container image.
WORKDIR /app
COPY . .

# Install dependencies
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Command to run the app
CMD ["python", "main.py"]
