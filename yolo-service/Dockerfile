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

# Install CPU-only torch first (much smaller than the default CUDA build),
# then the rest. ultralytics will reuse the already-installed torch.
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

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
