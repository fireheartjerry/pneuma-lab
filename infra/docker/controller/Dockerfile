# Fixture-only base digest: Step 5B must replace it with a retrieved receipt.
FROM registry.invalid/pneuma/controller@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
ARG SOURCE_DATE_EPOCH=0
ENV PYTHONHASHSEED=0 TZ=UTC PIP_DISABLE_PIP_VERSION_CHECK=1
COPY controller.lock /tmp/controller.lock
RUN pip install --require-hashes -r /tmp/controller.lock
