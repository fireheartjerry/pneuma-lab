# Step 7B base is bound by the real Step 5B input lock.  This image deliberately
# contains only the sealed standard-library role probe: it does not download a
# model, execute a benchmark, or require a GPU.
FROM vllm/vllm-openai@sha256:7a0f0fdd2771464b6976625c2b2d5dd46f566aa00fbc53eceab86ef50883da90
ARG SOURCE_DATE_EPOCH=0
ENV PYTHONHASHSEED=0 TZ=UTC PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/opt/pneuma
WORKDIR /opt/pneuma
COPY controller.lock /opt/pneuma/controller.lock
COPY src/pneuma_lab/__init__.py /opt/pneuma/pneuma_lab/__init__.py
COPY src/pneuma_lab/cloud/production_runtime.py /opt/pneuma/pneuma_lab/cloud/production_runtime.py
ENTRYPOINT ["python", "-m", "pneuma_lab.cloud.production_runtime", "controller"]
