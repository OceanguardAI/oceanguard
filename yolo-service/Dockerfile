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

# Install CPU-only torch AND torchvision together from the same index (much
# smaller than the default CUDA build). They MUST come from the same index in
# one command so their versions match — otherwise ultralytics pulls a PyPI
# torchvision built against a different torch and its C++ ops fail to load
# ("operator torchvision::nms does not exist") at inference time.
RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu

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
