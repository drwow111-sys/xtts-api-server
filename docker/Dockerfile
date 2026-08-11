# Use an official NVIDIA base image with CUDA support
FROM nvidia/cuda:12.1.1-cudnn8-devel-ubuntu22.04

# Set label for the docker image description
LABEL description="Docker image for xtts-api-server (VozDub fork - built from local source, not PyPI, so our /ping and /upload_reference additions are included)"

# Install required packages (avoid cache to reduce image size)
RUN apt-get update && \
    apt-get install --no-install-recommends -y \
    python3-dev portaudio19-dev libportaudio2 libasound2-dev libportaudiocpp0 \
    git python3 python3-pip make g++ ffmpeg && \
    rm -rf /var/lib/apt/lists/*

# Upgrade pip and install virtualenv
RUN python3 -m pip install --upgrade pip setuptools wheel ninja virtualenv

# Copy the application source code (the VozDub fork, with the added routes)
# and install it as a local package instead of pulling xtts-api-server from
# PyPI - otherwise our /ping + /upload_reference additions would never
# actually ship in the image.
COPY . /app
WORKDIR /app

# Install Python dependencies. CUDA-specific torch/torchaudio first, then the
# PINNED versions from requirements.txt (coqui-tts==0.24.1, transformers==
# 4.36.2, etc.) - these pins matter: `pip install .` alone resolves against
# pyproject.toml's looser ranges, which pulled a newer coqui-tts/coqpit
# combo that crashes on startup (TypeError: issubclass() arg 1 must be a
# class, inside coqpit's config deserializer - a known break in newer
# coqpit against this TTS version). Finally install our local package
# WITHOUT letting it re-resolve/upgrade the deps we just pinned.
RUN pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121
RUN pip install deepspeed
RUN pip install -r requirements.txt
RUN pip install --no-deps .

# Expose the container port (RunPod Load Balancer PORT/PORT_HEALTH env vars
# must be set to match this in the endpoint configuration).
EXPOSE 8020

# PORT is injected by RunPod ; default 8020 matches this server's own default
# for local/manual runs. --listen binds 0.0.0.0 (required for RunPod).
CMD ["bash", "-c", "python3 -m xtts_api_server --listen -p ${PORT:-8020} -t \"http://localhost:${PORT:-8020}\" -sf 'xtts-server/speakers' -o 'xtts-server/output' -mf 'xtts-server/models' --deepspeed"]
