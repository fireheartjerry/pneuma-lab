# Step 7B validates the sealed model-server role boundary, not model loading.
# The exact vLLM base is already bound by the Step 5B input lock.
FROM vllm/vllm-openai@sha256:7a0f0fdd2771464b6976625c2b2d5dd46f566aa00fbc53eceab86ef50883da90
ARG SOURCE_DATE_EPOCH=0
ENV PYTHONHASHSEED=0 TZ=UTC PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/opt/pneuma
WORKDIR /opt/pneuma
COPY infra/docker/model-server/model-server.lock /opt/pneuma/model-server.lock
COPY src/pneuma_lab/__init__.py /opt/pneuma/pneuma_lab/__init__.py
COPY src/pneuma_lab/cloud/production_runtime.py /opt/pneuma/pneuma_lab/cloud/production_runtime.py
ENTRYPOINT ["python3", "-m", "pneuma_lab.cloud.production_runtime", "model-server"]
