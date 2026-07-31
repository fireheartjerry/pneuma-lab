# Fixture-only base digest: Step 5B must replace it with a retrieved receipt.
FROM registry.invalid/pneuma/model-server@sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
ARG SOURCE_DATE_EPOCH=0
ENV PYTHONHASHSEED=0 TZ=UTC PIP_DISABLE_PIP_VERSION_CHECK=1 VLLM_VERSION=0.19.0
COPY model-server.lock /tmp/model-server.lock
RUN pip install --require-hashes -r /tmp/model-server.lock
