# Use an official NVIDIA base image with CUDA support
FROM nvidia/cuda:12.1.1-cudnn8-devel-ubuntu22.04

# Set label for the docker image description
LABEL description="Docker image for xtts-api-server (VozDub fork - built from local source, not PyPI, so our /ping and /upload_reference additions are included)"

# Install required packages (avoid cache to reduce image size)
RUN apt-get update && \
    apt-get install --no-install-recommends -y \
    python3-dev portaudio19-dev libportaudio2 libasound2-dev libportaudiocpp0 \
    git python3 python3-pip make g++ ffmpeg curl && \
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
# combo. Finally install our local package WITHOUT letting it re-resolve/
# upgrade the deps we just pinned.
#
# Note: even with these pins, the installed coqpit still crashes on this
# Python version with "TypeError: issubclass() arg 1 must be a class" while
# loading the XTTS model config (known bug, see
# daswer123/xtts-api-server#94 - no fixed coqpit release exists yet). Fixed
# via a runtime monkey-patch in server.py itself.
RUN pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121
RUN pip install deepspeed
RUN pip install -r requirements.txt
RUN pip install --no-deps .

# Pre-download the XTTS v2 model weights INTO THE IMAGE at build time,
# instead of letting the server download them on first request. RunPod's
# serverless workers were getting killed and replaced (health-check timeout)
# before the ~2GB runtime download + model init ever finished, creating an
# infinite cold-start loop where no worker ever became ready. Baking the
# weights into the image means a fresh worker only has to load local files,
# which takes seconds. Path/filenames must match modeldownloader.py exactly
# (xtts-server/models/<version>/...) and the version must match the
# server's default (-v flag, v2.0.2 unless overridden in the CMD below).
RUN mkdir -p xtts-server/models/v2.0.2 && \
    curl -L --fail -o xtts-server/models/v2.0.2/config.json "https://huggingface.co/coqui/XTTS-v2/raw/v2.0.2/config.json" && \
    curl -L --fail -o xtts-server/models/v2.0.2/vocab.json "https://huggingface.co/coqui/XTTS-v2/raw/v2.0.2/vocab.json" && \
    curl -L --fail -o xtts-server/models/v2.0.2/model.pth "https://huggingface.co/coqui/XTTS-v2/resolve/v2.0.2/model.pth?download=true" && \
    curl -L --fail -o xtts-server/models/v2.0.2/speakers_xtts.pth "https://huggingface.co/coqui/XTTS-v2/resolve/main/speakers_xtts.pth?download=true"

# Expose the container port (RunPod Load Balancer PORT/PORT_HEALTH env vars
# must be set to match this in the endpoint configuration).
EXPOSE 8020

# PORT is injected by RunPod ; default 8020 matches this server's own default
# for local/manual runs. --listen binds 0.0.0.0 (required for RunPod).
#
# --deepspeed intentionally dropped: it JIT-compiles custom CUDA kernels from
# source on first request/first boot, which reliably takes 5-15+ minutes and
# was causing cold starts to time out before the server ever finished coming
# up. The synthesis speed win isn't worth that startup fragility here.
#
# -sf points at /runpod-volume/speakers (a RunPod Network Volume mounted on
# every worker) instead of a path inside the container. Load Balancer
# endpoints scale to several workers behind the same URL, each with its own
# local disk: a reference voice uploaded via /upload_reference landed on
# whichever worker happened to handle that request, so a later
# /tts_to_audio/ call routed to a DIFFERENT worker got "Failed to open the
# input" (file not found) and fell back to silence in the client's dubbed
# output. Putting the speaker folder on the shared volume makes uploaded
# references visible to every worker regardless of which one handles which
# request. -o (per-request output, consumed immediately by the caller) and
# -mf (model weights, already baked into every worker's image above) stay
# local - only the speaker folder needs cross-worker consistency.
CMD ["bash", "-c", "mkdir -p /runpod-volume/speakers && python3 -m xtts_api_server --listen -p ${PORT:-8020} -t \"http://localhost:${PORT:-8020}\" -sf '/runpod-volume/speakers' -o 'xtts-server/output' -mf 'xtts-server/models'"]
