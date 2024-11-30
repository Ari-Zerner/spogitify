# Use a Python base image
FROM gcr.io/google-appengine/python

# Update apt package manager
RUN apt-get update && apt-get install -y \
    software-properties-common

# Add the deadsnakes PPA to get the latest Python versions
RUN add-apt-repository ppa:deadsnakes/ppa && apt-get update

# Install Python 3.x
RUN apt-get install -y python3.11 python3.11-venv python3.11-distutils

# Update symlink to use the new Python version
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1
RUN update-alternatives --config python3 --force
RUN python3 --version

# # Install git
# RUN apt-get update && \
#     apt-get install -y git && \
#     apt-get clean && \
#     rm -rf /var/lib/apt/lists/*

# # Copy local code to the container image.
# WORKDIR /app
# COPY . .

# # Install dependencies
# RUN pip3 install --upgrade pip && \
#     pip3 install --no-cache-dir -r requirements.txt

# # Command to run the app
# CMD ["gunicorn", "--bind", ":$PORT", "--workers", "1", "--threads", "8", "--timeout", "0", "main:app"]
