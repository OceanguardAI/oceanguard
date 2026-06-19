# YOLO SAR inference service — kept separate from the slim API so the heavy
# torch/ultralytics stack (and its cold start) only loads when an officer
# actually runs an on-demand check. Scales to zero between requests.
FROM python:3.11-slim

WORKDIR /app

# CPU torch + ultralytics (opencv) need libgl/libglib for image decoding and
# libgomp for OpenMP. These are the standard runtime libs on a slim base.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Install CPU-only torch AND torchvision as an EXACT, matched pair from the
# PyTorch CPU index (much smaller than the default CUDA build). The versions are
# pinned because letting pip pick "latest" can resolve a torch/torchvision pair
# whose compiled ABIs don't match — torchvision's C++ ops then fail to load
# ("operator torchvision::nms does not exist") at inference time. 2.5.1/0.20.1
# is a known-compatible release pair.
RUN pip install --no-cache-dir torch==2.5.1 torchvision==0.20.1 --index-url https://download.pytorch.org/whl/cpu

# Install the rest from PyPI. torch/torchvision are already satisfied above, so
# ultralytics will reuse them and pip won't pull a mismatched build.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY models ./models

# Headless: no GUI, no font/plot downloads at inference time.
ENV MPLBACKEND=Agg \
    YOLO_CONFIG_DIR=/tmp/Ultralytics \
    PORT=8080
EXPOSE 8080

CMD exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT}
