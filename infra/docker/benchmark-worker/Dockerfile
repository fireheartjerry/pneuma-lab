# Step 7B validates the sealed worker role boundary, not a benchmark episode.
FROM vllm/vllm-openai@sha256:7a0f0fdd2771464b6976625c2b2d5dd46f566aa00fbc53eceab86ef50883da90
ARG SOURCE_DATE_EPOCH=0
ENV PYTHONHASHSEED=0 TZ=UTC PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/opt/pneuma
WORKDIR /opt/pneuma
COPY infra/docker/benchmark-worker/benchmark-worker.lock /opt/pneuma/benchmark-worker.lock
COPY src/pneuma_lab/__init__.py /opt/pneuma/pneuma_lab/__init__.py
COPY src/pneuma_lab/cloud/production_runtime.py /opt/pneuma/pneuma_lab/cloud/production_runtime.py
ENTRYPOINT ["python", "-m", "pneuma_lab.cloud.production_runtime", "benchmark-worker"]
