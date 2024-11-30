# Use a Python base image
FROM gcr.io/google-appengine/python

# Install git
RUN apt-get update && \
    apt-get install -y git && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    export GIT_PYTHON_GIT_EXECUTABLE=$(which git)



# Copy local code to the container image.
WORKDIR /app
COPY . .

# Install dependencies
RUN pip3 install --upgrade pip && \
    pip3 install --no-cache-dir -r requirements.txt

# Command to run the app
CMD ["gunicorn", "--bind", ":$PORT", "--workers", "1", "--threads", "8", "--timeout", "0", "main:app"]
