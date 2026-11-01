# syntax=docker/dockerfile:1.4
FROM python:3.15-slim

# Set the working directory
WORKDIR /app

# Install uv with BuildKit cache mount and retry
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --timeout=300 --retries 5 uv

# Install system dependencies for pyvips (required by requirements.txt)
# libvips42 provides libvips.so.42 shared library
# libvips-dev provides development headers for building pyvips
# build-essential provides gcc, g++, make for compiling Python C extensions
RUN apt-get update -qq && \
    apt-get install --no-install-recommends -y \
      libvips42 \
      libvips-dev \
      build-essential \
    && rm -rf /var/lib/apt/lists /var/cache/apt/archives

# Copy only requirements first (optimize layer caching)
COPY ./requirements.txt ./

# Install dependencies with BuildKit cache mounts
# Cache both pip and uv caches across builds
# Note: uv doesn't support --timeout or --retry flags
RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=cache,target=/root/.cache/uv \
    uv pip install \
      --system \
      -r requirements.txt

# Copy application code AFTER dependencies (separate layer)
COPY ./app ./

# Expose the port the app runs on
EXPOSE 8000

# download model
# RUN python model_init.py

# Command to run the application
CMD ["python", "app.py"]
