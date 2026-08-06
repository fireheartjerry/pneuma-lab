# Step 7B validates the sealed worker role boundary, not a benchmark episode.
# The same image contains the separately gated real benchmark adapter; the
# qualification protocols remain explicit and never produce official evidence.
FROM vllm/vllm-openai@sha256:7a0f0fdd2771464b6976625c2b2d5dd46f566aa00fbc53eceab86ef50883da90
ARG SOURCE_DATE_EPOCH=0
ENV PYTHONHASHSEED=0 TZ=UTC PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/opt/pneuma
WORKDIR /opt/pneuma
COPY infra/docker/benchmark-worker/benchmark-worker.lock /opt/pneuma/benchmark-worker.lock
COPY src/pneuma_lab/__init__.py /opt/pneuma/pneuma_lab/__init__.py
COPY src/pneuma_lab/cloud /opt/pneuma/pneuma_lab/cloud
COPY src/pneuma_lab/foundation/__init__.py /opt/pneuma/pneuma_lab/foundation/__init__.py
COPY src/pneuma_lab/foundation/artifacts.py /opt/pneuma/pneuma_lab/foundation/artifacts.py
COPY src/pneuma_lab/foundation/specs.py /opt/pneuma/pneuma_lab/foundation/specs.py
COPY src/pneuma_lab/resampling_null /opt/pneuma/pneuma_lab/resampling_null
COPY src/pneuma_lab/schemas/__init__.py /opt/pneuma/pneuma_lab/schemas/__init__.py
COPY schemas /opt/schemas
# Fail the image build rather than discovering a missing verifier dependency
# only after the separately authorized production launch.
RUN python3 -c "import cryptography, jsonschema"
# Normalize build-owned mtimes for reproducibility on the pinned BuildKit.
RUN find /opt/pneuma -xdev -exec touch --date="@${SOURCE_DATE_EPOCH}" --no-dereference {} + \
    && touch --date="@${SOURCE_DATE_EPOCH}" --no-dereference /opt
ENTRYPOINT ["python3", "-m", "pneuma_lab.cloud.production_runtime", "benchmark-worker"]
