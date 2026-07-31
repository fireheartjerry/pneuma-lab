# Fixture-only base digest: Step 5B must replace it with a retrieved receipt.
FROM registry.invalid/pneuma/benchmark-worker@sha256:cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc
ARG SOURCE_DATE_EPOCH=0
ENV PYTHONHASHSEED=0 TZ=UTC PIP_DISABLE_PIP_VERSION_CHECK=1
COPY benchmark-worker.lock /tmp/benchmark-worker.lock
RUN pip install --require-hashes -r /tmp/benchmark-worker.lock
